#!/usr/bin/env python3
"""
Serve the fine-tuned Mistral 7B adapter as an API for SpeechGradebook.

Endpoints:
  GET  /health              -> { "status": "ok" }
  POST /evaluate            -> body: { "transcript": "...", "rubric_name": "...", "rubric": { ... }, "video_notes": "..." (optional) }
                              response: { "sections": { ... }, "overallComments": "..." }
  POST /evaluate_with_file  -> multipart: file, rubric (JSON string), video_notes (optional). Requires whisper.

Usage:
  pip install -r requirements-train.txt fastapi uvicorn
  python serve_model.py --model_path ./mistral7b-speech-lora [--port 8000] [--load_in_8bit]
"""

import argparse
import json
import tempfile
import time
from pathlib import Path

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

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI(title="SpeechGradebook Fine-tuned Evaluator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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


def build_messages(transcript: str, rubric_name: str, rubric: dict, video_notes: str = "") -> list:
    """Same prompt shape as in training (system + user). Include video_notes when present for video-aware evaluation."""
    system = (
        "You are a speech evaluator. Apply the given rubric and output scores and comments as a single JSON object. "
        "The JSON must match the rubric structure: for each category, include \"score\", \"maxScore\", and \"subcategories\" "
        "(array of { \"name\", \"points\", \"maxPoints\" }). Do not include any explanation outside the JSON."
    )
    user = f"Rubric: {rubric_name}\n\nTranscript:\n{transcript}"
    if video_notes and video_notes.strip():
        user += f"\n\nVideo notes (visual delivery):\n{video_notes.strip()}"
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


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
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
async def evaluate_with_file(
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
