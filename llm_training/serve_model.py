#!/usr/bin/env python3
"""
Serve the fine-tuned Mistral 7B adapter as an API for SpeechGradebook.

Endpoints:
  GET  /health              -> { "status": "ok" }
  POST /evaluate            -> body: { "transcript": "...", "rubric_name": "...", "rubric": { ... }, "video_notes": "..." (optional) }
                              response: { "sections": { ... }, "overallComments": "..." }
  POST /evaluate_with_file  -> multipart: file, rubric (JSON string), video_notes (optional). Requires whisper.
  POST /llm-export          -> body: JSON array (export from dashboard). Saves to exported.json and runs run_training.sh (ISAAC). Optional header X-LLM-Export-Secret.

Usage:
  pip install -r requirements-train.txt fastapi uvicorn
  python serve_model.py --model_path ./mistral7b-speech-lora [--port 8000] [--load_in_8bit]
"""

import argparse
import base64
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

# Load .env from repo root so RENDER_LLM_EXPORT_SECRET is set when this module handles /api/llm-export
try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parent.parent
    _env_file = _repo_root / ".env"
    load_dotenv(_env_file, override=True)
    if not os.environ.get("RENDER_LLM_EXPORT_SECRET"):
        print("LLM export: RENDER_LLM_EXPORT_SECRET is not set. Add it to .env for Submit to ISAAC.")
    else:
        print("LLM export: RENDER_LLM_EXPORT_SECRET is set (Submit to ISAAC will work if API secret matches).")
except ImportError:
    pass

import torch

# #region agent log
DEBUG_LOG_PATH = "/Users/annamcclure/SpeechGradebook Repo/.cursor/debug.log"
def _dbg(msg, data=None, hypothesis_id=None):
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({"timestamp": int(time.time() * 1000), "message": msg, "data": data or {}, "hypothesisId": hypothesis_id, "location": "serve_model.py", "sessionId": "debug-session"}) + "\n")
    except Exception:
        pass
# #endregion

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="SpeechGradebook Fine-tuned Evaluator")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: Read allowed origins from ALLOWED_ORIGINS env var (comma-separated).
# Default allows localhost for development. In production, set to your actual domain(s).
# Example: ALLOWED_ORIGINS=https://speechgradebook.onrender.com,https://yourdomain.com
_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _allowed_origins_env:
    _allowed_origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
else:
    # Default: allow localhost for development only
    _allowed_origins = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-LLM-Export-Secret"],
)

# Global model/tokenizer (loaded at startup)
model = None
tokenizer = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass


class EvaluateRequest(BaseModel):
    transcript: str
    rubric_name: str
    rubric: dict  # Full rubric: categories, gradeScale, totalPoints, etc.
    video_notes: str = ""  # Optional: text description of visual delivery (body movement, eye contact, slides)


class EvaluateResponse(BaseModel):
    sections: dict
    overallComments: str = ""
    transcript: str = ""  # Set when using /evaluate_with_file


def load_model_and_tokenizer(model_path: str, base_model: str, load_in_8bit: bool):
    global model, tokenizer
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model path not found: {path}")

    tokenizer = AutoTokenizer.from_pretrained(str(path), trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"torch_dtype": torch.bfloat16 if DEVICE == "cuda" else torch.float32}
    if load_in_8bit:
        from transformers import BitsAndBytesConfig
        model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)

    base = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    model = PeftModel.from_pretrained(base, str(path))
    model.to(DEVICE)
    model.eval()


def _format_rubric_structure(rubric: dict) -> str | None:
    """Format rubric categories and subcategories for the prompt so the model knows exactly what to output."""
    if not rubric:
        return None
    categories = rubric.get("categories")
    if not categories or not isinstance(categories, list):
        return None
    lines = []
    for cat in categories:
        if isinstance(cat, dict):
            name = cat.get("name", "")
            subs = cat.get("subcategories") or []
            sub_list = [s if isinstance(s, str) else (s.get("name", "") if isinstance(s, dict) else "") for s in subs]
            sub_list = [s for s in sub_list if s]
            if sub_list:
                lines.append(f"- {name}: {', '.join(sub_list)}")
            else:
                lines.append(f"- {name}")
        else:
            lines.append(f"- {cat}")
    return "\n".join(lines) if lines else None


def _load_reference_examples() -> list:
    """Load reference examples from JSON (from example videos) so the model can identify behaviors like swaying, purpose statement."""
    path = os.environ.get("REFERENCE_EXAMPLES_PATH", "").strip()
    if not path:
        default = Path(__file__).resolve().parent / "reference_examples.json"
        path = str(default)
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


REFERENCE_EXAMPLES: list = _load_reference_examples()


def _get_rubric_category_names(rubric: dict) -> list[str]:
    """Extract category and subcategory names for textbook RAG queries."""
    if not rubric:
        return []
    cats = rubric.get("categories") or []
    names = []
    for c in cats:
        if isinstance(c, dict):
            n = c.get("name", "")
            if n:
                names.append(str(n))
            for s in c.get("subcategories") or []:
                sn = s.get("name", s) if isinstance(s, dict) else s
                if sn:
                    names.append(str(sn))
        elif c:
            names.append(str(c))
    return names


def _get_textbook_chunks_block(rubric: dict) -> str:
    """Retrieve relevant textbook chunks and format for prompt. Returns empty string if no textbook or retrieval fails."""
    textbook_id = rubric.get("textbook_id") or rubric.get("textbookId")
    if not textbook_id:
        return ""
    try:
        from llm_training import textbook_rag
        queries = _get_rubric_category_names(rubric)
        if not queries:
            queries = [rubric.get("name", ""), rubric.get("speechType", "")]
            queries = [q for q in queries if q]
        chunks = textbook_rag.get_relevant_chunks(textbook_id, queries, top_k=5)
        if not chunks:
            return ""
        lines = ["Textbook excerpts (use these to inform your evaluation):"]
        for i, c in enumerate(chunks, 1):
            lines.append(f"[{i}] {c[:1200]}{'...' if len(c) > 1200 else ''}")
        return "\n\n".join(lines)
    except Exception:
        return ""


def _format_reference_examples_block(examples: list) -> str:
    """Format reference examples for the user prompt."""
    if not examples:
        return ""
    lines = [
        "Reference examples (use these when identifying behaviors in the transcript and video notes above):"
    ]
    for ex in examples:
        label = ex.get("label", "Behavior")
        btype = ex.get("type", "delivery")
        desc = ex.get("description", "")
        guidance = ex.get("scoring_guidance", "")
        excerpt = ex.get("example_excerpt", "")
        parts = [f"• {label} ({btype}): {desc}".strip()]
        if guidance:
            parts.append(guidance)
        if excerpt:
            parts.append(f'Example: "{excerpt}"')
        lines.append(" ".join(parts))
    return "\n".join(lines)


def build_messages(
    transcript: str, rubric_name: str, rubric: dict, video_notes: str = ""
) -> list:
    """Same prompt shape as in training (system + user). Include full rubric structure, video_notes, and optional reference examples."""
    system = (
        "You are a speech evaluator. You must assess both (1) the transcript (verbal content: e.g. purpose statement, organization, evidence) "
        "and (2) the video notes (visual delivery: e.g. eye contact, posture, swaying, gestures). "
        "Apply the given rubric and output scores and comments as a single JSON object. "
        "The JSON must match the rubric structure: for each category, include \"score\", \"maxScore\", and \"subcategories\" "
        "(array of { \"name\", \"points\", \"maxPoints\" }). Do not include any explanation outside the JSON."
    )
    if REFERENCE_EXAMPLES:
        system += (
            " Use the reference examples provided in the user message to identify specific behaviors (e.g. swaying, purpose statement) and score accordingly."
        )
    user = f"Rubric: {rubric_name}\n"
    structure_text = _format_rubric_structure(rubric)
    if structure_text:
        user += "Categories and subcategories to score:\n" + structure_text + "\n\n"
    user += f"Transcript:\n{transcript}"
    if video_notes and video_notes.strip():
        user += f"\n\nVideo notes (visual delivery):\n{video_notes.strip()}"
    ref_block = _format_reference_examples_block(REFERENCE_EXAMPLES)
    if ref_block:
        user += "\n\n" + ref_block
    textbook_block = _get_textbook_chunks_block(rubric)
    if textbook_block:
        user += "\n\n" + textbook_block
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def extract_json_from_response(text: str) -> dict | None:
    text = text.strip()
    start = text.rfind("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def run_inference(
    transcript: str, rubric_name: str, rubric: dict, video_notes: str = "", max_new_tokens: int = 1024
) -> dict:
    messages = build_messages(transcript, rubric_name, rubric, video_notes)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    sections = extract_json_from_response(gen)
    if sections is None:
        return {"sections": {}, "overallComments": "Model output could not be parsed as JSON."}
    return {"sections": sections, "overallComments": ""}


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


class SuggestDescriptionsRequest(BaseModel):
    textbook_id: str = ""
    names: list[str] = []


@app.post("/suggest-rubric-descriptions")
@limiter.limit("20/minute")
def suggest_rubric_descriptions(request: Request, req: SuggestDescriptionsRequest):
    """
    Suggest descriptions for rubric categories/subcategories from textbook RAG.
    Body: { "textbook_id": "uuid", "names": ["Verbal Citation", "Eye Contact", ...] }
    Returns: { "suggestions": { "Verbal Citation": "text...", ... } }
    """
    textbook_id = (req.textbook_id or "").strip()
    names = req.names or []
    if not textbook_id or not names:
        return JSONResponse(status_code=400, content={"detail": "textbook_id and names required"})
    if not isinstance(names, list):
        names = [str(names)]
    names = [str(n).strip() for n in names if n]
    if not names:
        return JSONResponse(status_code=400, content={"detail": "At least one name required"})
    try:
        from llm_training import textbook_rag
    except ImportError:
        return JSONResponse(status_code=503, content={"detail": "Textbook RAG not available (install sentence-transformers, psycopg2-binary)"})
    suggestions = {}
    max_desc_len = 600
    for name in names:
        chunks = textbook_rag.get_relevant_chunks(textbook_id, [name], top_k=2)
        text = "\n\n".join(chunks).strip() if chunks else ""
        if text and len(text) > max_desc_len:
            text = text[:max_desc_len].rsplit(" ", 1)[0] + "..."
        suggestions[name] = text
    return {"suggestions": suggestions}


@app.post("/evaluate", response_model=EvaluateResponse)
@limiter.limit("30/minute")  # 30 evaluations per minute per IP
def evaluate(request: Request, req: EvaluateRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        result = run_inference(
            req.transcript,
            req.rubric_name,
            req.rubric,
            req.video_notes or "",
        )
        return EvaluateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate_with_file", response_model=EvaluateResponse)
@limiter.limit("10/minute")  # 10 file uploads per minute per IP (more expensive: transcription + inference)
async def evaluate_with_file(
    request: Request,
    file: UploadFile = File(...),
    rubric: str = Form(...),
    video_notes: str = Form(""),
):
    """Accept audio/video file + rubric JSON; transcribe with Whisper then run model. Optional video_notes for visual delivery. Requires: pip install openai-whisper."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not WHISPER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Transcription not available. Install with: pip install openai-whisper",
        )
    try:
        rubric_obj = json.loads(rubric)
        rubric_name = rubric_obj.get("name", "Rubric")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid rubric JSON: {e}")
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename or "audio").suffix or ".webm", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        whisper_model = whisper.load_model("base")
        result = whisper_model.transcribe(tmp_path, fp16=(DEVICE == "cuda"))
        transcript = (result.get("text") or "").strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcription returned empty. Check file format (audio/video).")
    eval_result = run_inference(transcript, rubric_name, rubric_obj, video_notes=(video_notes or "").strip())
    return EvaluateResponse(**eval_result, transcript=transcript)


# Target max size for compressed video (Supabase free tier limit)
COMPRESS_VIDEO_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
TARGET_SIZE_BYTES = int(COMPRESS_VIDEO_MAX_BYTES * 0.85)  # ~42.5 MB to stay under 50 MB
AUDIO_BITRATE_K = 96
VIDEO_BITRATE_MIN_K = 200
VIDEO_BITRATE_MAX_K = 2000


def _probe_duration(path: str) -> float:
    """Get video duration in seconds via ffprobe. Returns 60.0 if probe fails."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0 and r.stdout and r.stdout.strip():
            return max(1.0, float(r.stdout.strip()))
    except Exception:
        pass
    return 60.0


def _compute_video_bitrate_k(duration_sec: float, target_bytes: int) -> int:
    """Compute target video bitrate (kbps) from duration and target size. Leaves ~15% for container/audio."""
    total_kbps = (target_bytes * 8) / duration_sec
    video_kbps = total_kbps - AUDIO_BITRATE_K
    return int(max(VIDEO_BITRATE_MIN_K, min(VIDEO_BITRATE_MAX_K, video_kbps)))


@app.post("/compress_video")
@limiter.limit("10/minute")
async def compress_video(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Compress a video file to under 50 MB (H.264/AAC MP4) for storage compatibility.
    Uses duration-based bitrate, resolution scaling (max 1080p), and 30 fps cap.
    Requires ffmpeg on the server.
    """
    fn = (file.filename or "video").lower()
    ct = (file.content_type or "").lower()
    if "video/" not in ct and not any(fn.endswith(ext) for ext in (".mov", ".mp4", ".webm", ".mkv", ".avi", ".m4v")):
        raise HTTPException(status_code=400, detail="Expected a video file (e.g. MP4, MOV, WebM).")
    if file.size is not None and file.size <= COMPRESS_VIDEO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is already under 50 MB; no compression needed.")
    tmp_in = None
    tmp_out = None
    try:
        suffix = Path(file.filename or "video").suffix or ".mov"
        if not suffix.startswith("."):
            suffix = "." + suffix
        tmp_in = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp_out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_in.close()
        tmp_out.close()
        # Stream upload to disk to support large files
        with open(tmp_in.name, "wb") as f:
            size = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > 600 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="File too large (max 600 MB for compression).")
                f.write(chunk)

        duration_sec = _probe_duration(tmp_in.name)
        bitrate_k = _compute_video_bitrate_k(duration_sec, TARGET_SIZE_BYTES)
        maxrate_k = min(int(bitrate_k * 1.2), VIDEO_BITRATE_MAX_K + 200)
        bufsize_k = max(1000, bitrate_k * 2)

        # Scale to max 1080p, cap at 30 fps (sufficient for speech)
        vf = "scale=-2:min(1080,ih)"
        cmd = [
            "ffmpeg", "-y", "-i", tmp_in.name,
            "-vf", vf, "-r", "30",
            "-c:v", "libx264", "-b:v", f"{bitrate_k}k", "-maxrate", f"{maxrate_k}k", "-bufsize", f"{bufsize_k}k",
            "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE_K}k",
            "-movflags", "+faststart",
            tmp_out.name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise HTTPException(
                status_code=502,
                detail=f"ffmpeg failed. Install ffmpeg on the server. stderr: {(result.stderr or '')[-500:]}",
            )
        out_size = Path(tmp_out.name).stat().st_size
        if out_size > COMPRESS_VIDEO_MAX_BYTES:
            # Retry with lower bitrate (target ~35 MB)
            Path(tmp_out.name).unlink(missing_ok=True)
            retry_target = int(COMPRESS_VIDEO_MAX_BYTES * 0.7)
            bitrate_k = _compute_video_bitrate_k(duration_sec, retry_target)
            maxrate_k = min(int(bitrate_k * 1.2), bitrate_k + 150)
            bufsize_k = max(1000, bitrate_k * 2)
            cmd = [
                "ffmpeg", "-y", "-i", tmp_in.name,
                "-vf", vf, "-r", "30",
                "-c:v", "libx264", "-b:v", f"{bitrate_k}k", "-maxrate", f"{maxrate_k}k", "-bufsize", f"{bufsize_k}k",
                "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE_K}k",
                "-movflags", "+faststart",
                tmp_out.name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0 or not Path(tmp_out.name).exists():
                raise HTTPException(status_code=502, detail="ffmpeg second pass failed.")
            out_size = Path(tmp_out.name).stat().st_size
        out_name = Path(file.filename or "video").stem + ".mp4"
        out_path = tmp_out.name
        background_tasks.add_task(lambda: Path(out_path).unlink(missing_ok=True))
        return FileResponse(
            out_path,
            media_type="video/mp4",
            filename=out_name,
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression failed: {e}")
    finally:
        if tmp_in and tmp_in.name and Path(tmp_in.name).exists():
            Path(tmp_in.name).unlink(missing_ok=True)


def _normalize_ssh_private_key(raw: str) -> bytes:
    """Produce valid OpenSSH private key bytes from env value (PEM with \\n or base64-encoded key)."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("ISAAC_SSH_PRIVATE_KEY is empty")
    # PEM-style: may have literal \n in the string
    if "-----BEGIN" in raw:
        text = raw.replace("\\n", "\n")
        return text.encode("utf-8")
    # Base64-encoded key (e.g. entire key file or binary payload from Render)
    # Strip whitespace/newlines so multi-line paste or env wrapping still decodes
    b64_clean = "".join(raw.split())
    try:
        decoded = base64.b64decode(b64_clean, validate=True)
    except Exception:
        return raw.encode("utf-8")
    if decoded.startswith(b"-----BEGIN"):
        return decoded
    if decoded.startswith(b"openssh-key-v1\x00"):
        # Binary OpenSSH key: wrap in PEM armor for ssh
        b64 = base64.b64encode(decoded).decode("ascii")
        lines = [b64[i : i + 70] for i in range(0, len(b64), 70)]
        pem = "-----BEGIN OPENSSH PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END OPENSSH PRIVATE KEY-----\n"
        return pem.encode("utf-8")
    return decoded


# Validation limits for /llm-export
MAX_EXPORT_PAYLOAD_BYTES = 50 * 1024 * 1024  # 50 MB max payload
MAX_EXPORT_ITEMS = 10000  # Max 10,000 evaluations per export


def _read_llm_export_secret_from_env_file(env_path: Path) -> str:
    """Parse .env for RENDER_LLM_EXPORT_SECRET. Supports KEY=val and KEY = val; strips quotes."""
    if not env_path.exists():
        return ""
    try:
        for _line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#"):
                continue
            if "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            if _key.strip() != "RENDER_LLM_EXPORT_SECRET":
                continue
            _val = _val.strip().strip("'\"")
            if _val:
                return _val
    except Exception:
        pass
    return ""


def _strip_quotes(s: str) -> str:
    """Strip surrounding single/double quotes so env and header compare correctly (e.g. Render may inject quotes)."""
    s = (s or "").strip()
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        return s[1:-1].strip()
    return s


def _get_llm_export_secret():
    """Get RENDER_LLM_EXPORT_SECRET from env or by reading .env file. Used for /llm-export and /llm-export-status."""
    secret = _strip_quotes(os.environ.get("RENDER_LLM_EXPORT_SECRET") or "")
    if secret:
        return secret
    try:
        from dotenv import load_dotenv
        _repo = Path(__file__).resolve().parent.parent
        _env_file = _repo / ".env"
        load_dotenv(_env_file, override=True)
        secret = _strip_quotes(os.environ.get("RENDER_LLM_EXPORT_SECRET") or "")
        if secret:
            return secret
    except Exception:
        pass
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    secret = _read_llm_export_secret_from_env_file(_env_path)
    if secret:
        os.environ["RENDER_LLM_EXPORT_SECRET"] = secret
    return secret


@app.get("/llm-export-status")
async def llm_export_status():
    """Debug: confirm whether RENDER_LLM_EXPORT_SECRET is visible to the server (no secret value revealed)."""
    _repo = Path(__file__).resolve().parent.parent
    _env_path = _repo / ".env"
    return {
        "secret_configured": bool(_get_llm_export_secret()),
        "env_file_exists": _env_path.exists(),
        "env_file_path": str(_env_path),
    }


def _get_slack_signup_webhook_url() -> str:
    """SLACK_SIGNUP_WEBHOOK_URL for new signup notifications. Accepts uppercase or lowercase key."""
    def _get(k):
        return (os.environ.get(k) or "").strip().strip("'\"")
    url = _get("SLACK_SIGNUP_WEBHOOK_URL") or _get("slack_signup_webhook_url")
    if url:
        return url
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
        return _get("SLACK_SIGNUP_WEBHOOK_URL") or _get("slack_signup_webhook_url")
    except Exception:
        return ""


@app.post("/notify-signup-request")
async def notify_signup_request(request: Request):
    """
    Notify Super Admin of a new signup request via Slack.
    Called by the frontend after a non-invited user registers, or by Supabase Database Webhook.
    Full path when mounted at /api: POST /api/notify-signup-request
    """
    webhook_url = _get_slack_signup_webhook_url()
    if not webhook_url:
        return JSONResponse(
            status_code=503,
            content={"detail": "SLACK_SIGNUP_WEBHOOK_URL not configured. Set it in environment to enable notifications."},
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

    record = body.get("record") if isinstance(body.get("record"), dict) else None
    if record and body.get("table") == "user_profiles":
        if (record.get("approval_status") or "").strip() != "pending_approval":
            return JSONResponse(status_code=200, content={"ok": True, "skipped": "not pending_approval"})
        email = (record.get("email") or "").strip()
        full_name = (record.get("full_name") or "").strip()
        requested_role = (record.get("requested_role") or "instructor").strip()
    else:
        email = (body.get("email") or "").strip()
        full_name = (body.get("full_name") or "").strip()
        requested_role = (body.get("requested_role") or "instructor").strip()

    if not email:
        return JSONResponse(status_code=400, content={"detail": "Missing email"})

    text = (
        "*New SpeechGradebook signup request*\n"
        "• Email: {}\n"
        "• Name: {}\n"
        "• Requested role: {}\n"
        "Please approve or reject in Settings → Admin → User management."
    ).format(email, full_name or "—", requested_role)
    payload = {"text": text}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(webhook_url, json=payload)
            if r.status_code >= 400:
                return JSONResponse(
                    status_code=502,
                    content={"detail": "Slack webhook returned {}".format(r.status_code), "body": r.text[:500]},
                )
    except Exception as e:
        return JSONResponse(status_code=502, content={"detail": "Slack request failed: {}".format(e)})

    return JSONResponse(status_code=200, content={"ok": True})


@app.post("/llm-export")
@limiter.limit("5/minute")  # 5 exports per minute per IP (triggers training job)
async def llm_export(request: Request, x_llm_export_secret: str = Header(None, alias="X-LLM-Export-Secret")):
    """
    Receive export JSON from the dashboard and run training on ISAAC (or locally).
    Used when the app is hosted on Render: no local terminal needed.
    Set ISAAC_HOST, ISAAC_USER, ISAAC_REMOTE_DIR (and optionally ISAAC_SSH_PRIVATE_KEY) on Render.
    Set RENDER_LLM_EXPORT_SECRET and require it via X-LLM-Export-Secret header for security.
    """
    # #region agent log
    _log_path = Path(__file__).resolve().parent.parent / ".cursor" / "debug.log"
    def _log(msg, data=None, hid="H1"):
        try:
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_log_path, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"timestamp": int(time.time() * 1000), "location": "serve_model.llm_export", "message": msg, "data": data or {}, "hypothesisId": hid, "sessionId": "debug-session"}) + "\n")
        except Exception:
            pass
    # #endregion
    origin = request.headers.get("origin")
    header_val = _strip_quotes(x_llm_export_secret or "")
    secret = _get_llm_export_secret()
    # #region agent log
    _log("entry", {"header_present": x_llm_export_secret is not None, "header_len": len(header_val), "secret_len": len(secret), "origin": origin}, "H1")
    # #endregion
    # Last-resort: if main app didn't set env (e.g. import order), read .env directly
    if not secret:
        _env_path = Path(__file__).resolve().parent.parent / ".env"
        secret = _read_llm_export_secret_from_env_file(_env_path)
        if secret:
            os.environ["RENDER_LLM_EXPORT_SECRET"] = secret
    if origin:
        # Browser request - require secret to prevent CSRF
        if not secret:
            raise HTTPException(
                status_code=403,
                detail="RENDER_LLM_EXPORT_SECRET not configured on server. Set this environment variable to enable exports.",
            )
        if header_val != secret:
            # #region agent log
            _log("401 branch", {"header_len": len(header_val), "secret_len": len(secret), "match": header_val == secret}, "H2")
            # #endregion
            print("llm-export 401: header_len=%s secret_len=%s" % (len(header_val), len(secret)), flush=True)
            raise HTTPException(status_code=401, detail="Invalid or missing X-LLM-Export-Secret header")
        # Validate Origin matches allowed origins
        if origin not in _allowed_origins and "*" not in _allowed_origins:
            _dbg("branch: 403 origin not allowed", {"origin": origin}, "H5")
            raise HTTPException(status_code=403, detail=f"Origin {origin} not allowed")
    elif secret:
        # Non-browser request but secret is configured - still require it
        if header_val != secret:
            print("llm-export 401: header_len=%s secret_len=%s" % (len(header_val), len(secret)), flush=True)
            raise HTTPException(status_code=401, detail="Invalid or missing X-LLM-Export-Secret header")
    
    # Validate payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_EXPORT_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Payload too large. Max {MAX_EXPORT_PAYLOAD_BYTES // (1024 * 1024)} MB.",
        )
    
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # Validate structure
    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Body must be a JSON array")
    if len(body) == 0:
        return {"ok": True, "count": 0, "message": "No data to export"}
    if len(body) > MAX_EXPORT_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many items. Max {MAX_EXPORT_ITEMS} evaluations per export.",
        )
    
    # Validate each item has required fields (basic schema validation)
    for i, item in enumerate(body):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"Item {i} must be an object")
        if "transcript" not in item:
            raise HTTPException(status_code=400, detail=f"Item {i} missing 'transcript' field")
        if "scores" not in item:
            raise HTTPException(status_code=400, detail=f"Item {i} missing 'scores' field")
    llm_dir = Path(__file__).resolve().parent
    exported_path = llm_dir / "exported.json"
    try:
        with open(exported_path, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write exported.json: {e}")
    env = dict(os.environ)
    # Normalize ISAAC_HOST: correct common typos/wrong hostnames so Submit to ISAAC works
    _h = (env.get("ISAAC_HOST") or "").strip().lower()
    if not _h or "issac" in _h or "tennessee.edu" in _h or _h == "isaac-login.tennessee.edu":
        env["ISAAC_HOST"] = "login.isaac.utk.edu"
    ssh_key_path = None
    if os.environ.get("ISAAC_SSH_PRIVATE_KEY"):
        try:
            fd, ssh_key_path = tempfile.mkstemp(prefix="isaac_key_", suffix="")
            os.close(fd)
            key_content = _normalize_ssh_private_key(os.environ["ISAAC_SSH_PRIVATE_KEY"])
            with open(ssh_key_path, "wb") as f:
                f.write(key_content)
            os.chmod(ssh_key_path, stat.S_IRUSR | stat.S_IWUSR)
            env["SSH_KEY_PATH"] = ssh_key_path
        except Exception as e:
            if ssh_key_path and os.path.exists(ssh_key_path):
                try:
                    os.unlink(ssh_key_path)
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to write SSH key: {e}")
    try:
        proc = subprocess.run(
            [os.path.join(llm_dir, "run_training.sh")],
            cwd=str(llm_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            err = proc.stderr or proc.stdout or "unknown"
            detail = f"run_training.sh failed: {err}"
            if "Permission denied" in err or "permission denied" in err.lower():
                detail += " Ensure the public key for ISAAC_SSH_PRIVATE_KEY is in ~/.ssh/authorized_keys on ISAAC for user " + os.environ.get("ISAAC_USER", "ISAAC_USER") + "."
            raise HTTPException(status_code=502, detail=detail)
    finally:
        if ssh_key_path and os.path.exists(ssh_key_path):
            try:
                os.unlink(ssh_key_path)
            except Exception:
                pass
    return {"ok": True, "count": len(body), "message": "Export saved; training submitted."}


@app.post("/llm-export-qwen")
@limiter.limit("5/minute")
async def llm_export_qwen(request: Request, x_llm_export_secret: str = Header(None, alias="X-LLM-Export-Secret")):
    """
    Receive Qwen (video) training manifest from the dashboard and submit training on ISAAC.
    Body: JSON array of { "video_path" or "image_path": url or path, "rubric": {...}, "scores": {...} }.
    Each item must have at least one of video_path or image_path (for coding example videos or images).
    Writes train_qwen.jsonl and runs run_qwen_training.sh (same auth as /llm-export).
    """
    origin = request.headers.get("origin")
    header_val = _strip_quotes(x_llm_export_secret or "")
    secret = _get_llm_export_secret()
    if origin:
        if not secret:
            raise HTTPException(status_code=403, detail="RENDER_LLM_EXPORT_SECRET not configured.")
        if header_val != secret:
            raise HTTPException(status_code=401, detail="Invalid or missing X-LLM-Export-Secret header")
        _ao = os.environ.get("ALLOWED_ORIGINS", "").strip().split(",")
        if _ao and "*" not in _ao and origin not in _ao:
            raise HTTPException(status_code=403, detail="Origin not allowed")
    elif secret and header_val != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-LLM-Export-Secret header")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Body must be a JSON array")
    if len(body) == 0:
        return {"ok": True, "count": 0, "message": "No data to export"}
    if len(body) > MAX_EXPORT_ITEMS:
        raise HTTPException(status_code=400, detail=f"Too many items. Max {MAX_EXPORT_ITEMS}.")

    for i, item in enumerate(body):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"Item {i} must be an object")
        if "video_path" not in item and "image_path" not in item:
            raise HTTPException(status_code=400, detail=f"Item {i} must have 'video_path' or 'image_path'")
        if "rubric" not in item:
            raise HTTPException(status_code=400, detail=f"Item {i} missing 'rubric'")
        if "scores" not in item:
            raise HTTPException(status_code=400, detail=f"Item {i} missing 'scores'")

    llm_dir = Path(__file__).resolve().parent
    manifest_path = llm_dir / "train_qwen.jsonl"
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            for item in body:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write train_qwen.jsonl: {e}")

    ssh_key_path = None
    if os.environ.get("ISAAC_SSH_PRIVATE_KEY"):
        try:
            fd, ssh_key_path = tempfile.mkstemp(prefix="isaac_key_", suffix="")
            os.close(fd)
            key_content = _normalize_ssh_private_key(os.environ["ISAAC_SSH_PRIVATE_KEY"])
            with open(ssh_key_path, "wb") as f:
                f.write(key_content)
            os.chmod(ssh_key_path, stat.S_IRUSR | stat.S_IWUSR)
            env = dict(os.environ)
            env["SSH_KEY_PATH"] = ssh_key_path
        except Exception as e:
            if ssh_key_path and os.path.exists(ssh_key_path):
                try:
                    os.unlink(ssh_key_path)
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to write SSH key: {e}")
    else:
        env = dict(os.environ)
    # Normalize ISAAC_HOST (same as Mistral path)
    _h = (env.get("ISAAC_HOST") or "").strip().lower()
    if not _h or "issac" in _h or "tennessee.edu" in _h or _h == "isaac-login.tennessee.edu":
        env["ISAAC_HOST"] = "login.isaac.utk.edu"

    run_qwen_sh = llm_dir / "run_qwen_training.sh"
    if not run_qwen_sh.exists():
        raise HTTPException(status_code=501, detail="run_qwen_training.sh not found in llm_training.")
    try:
        proc = subprocess.run(
            [str(run_qwen_sh)],
            cwd=str(llm_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise HTTPException(
                status_code=502,
                detail=f"run_qwen_training.sh failed: {proc.stderr or proc.stdout or 'unknown'}",
            )
    finally:
        if ssh_key_path and os.path.exists(ssh_key_path):
            try:
                os.unlink(ssh_key_path)
            except Exception:
                pass
    return {"ok": True, "count": len(body), "message": "Qwen manifest saved; training submitted to ISAAC."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model_path", default="./mistral7b-speech-lora")
    p.add_argument("--base_model", default="mistralai/Mistral-7B-Instruct-v0.2")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--load_in_8bit", action="store_true")
    args = p.parse_args()

    # #region agent log
    _dbg("main() started", {"model_path": str(args.model_path), "port": args.port}, "H1")
    path = Path(args.model_path)
    path_exists = path.exists()
    _dbg("model_path exists", {"exists": path_exists}, "H4")
    # #endregion
    if path_exists:
        print("Loading model and tokenizer...")
        # #region agent log
        _dbg("about to load_model_and_tokenizer", {}, "H2")
        # #endregion
        try:
            load_model_and_tokenizer(args.model_path, args.base_model, args.load_in_8bit)
            # #region agent log
            _dbg("load_model_and_tokenizer succeeded", {}, "H2")
            # #endregion
            print("Model loaded.")
        except Exception as e:
            # #region agent log
            _dbg("load_model_and_tokenizer failed", {"error": str(e)}, "H2")
            # #endregion
            raise
    else:
        print("Model path not found:", path.resolve())
        print("Server will start but /evaluate and /evaluate_with_file will return 503 until you train and pass a valid --model_path.")
    print("Starting server on port", args.port)
    # #region agent log
    _dbg("about to uvicorn.run", {"port": args.port}, "H3")
    # #endregion
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
