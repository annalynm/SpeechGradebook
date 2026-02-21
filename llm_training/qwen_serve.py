#!/usr/bin/env python3
"""
Qwen2.5-VL-7B service for SpeechGradebook video analysis and rubric extraction.

Endpoints:
  GET  /health              -> { "status": "ok", "model": "Qwen2.5-VL-7B" }
  POST /analyze_video       -> multipart: file (video). Returns { "video_notes": "..." }
  POST /evaluate_video      -> multipart: file (video), rubric (JSON). Returns { "sections", "overallComments", "transcript" } (same as SpeechGradebook Model)
  POST /extract_rubric      -> multipart: file (image/PDF). Returns rubric JSON

Usage:
  pip install transformers>=4.45.0 torch accelerate
  python qwen_serve.py [--port 8001] [--model Qwen/Qwen2.5-VL-7B-Instruct]

To avoid ~/.cache permission issues, uses ./cache in the llm_training dir by default.
"""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

# Use local cache inside project (avoids ~/.cache permission issues)
_script_dir = Path(__file__).resolve().parent
_cache_dir = _script_dir / "cache"
_cache_dir.mkdir(exist_ok=True)
if "HF_HOME" not in os.environ and "HF_HUB_CACHE" not in os.environ:
    os.environ["HF_HOME"] = str(_cache_dir)
    os.environ["HF_HUB_CACHE"] = str(_cache_dir / "hub")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SpeechGradebook Qwen2.5-VL Service")

_allowed = os.environ.get("ALLOWED_ORIGINS", "").strip()
_origins = [o.strip() for o in _allowed.split(",") if o.strip()] if _allowed else [
    "http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000",
    "http://127.0.0.1:8000", "http://localhost:5000", "http://127.0.0.1:5000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

model = None
processor = None
DEVICE = "cuda"


def _load_model(model_name: str, load_in_8bit: bool = False, load_in_4bit: bool = False):
    global model, processor
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration, Qwen2_5_VLProcessor  # requires transformers>=4.50

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    # Use Qwen2_5_VLProcessor directly to avoid AutoProcessor video_processing bug (TypeError: NoneType)
    processor = Qwen2_5_VLProcessor.from_pretrained(model_name, trust_remote_code=True)

    if device == "cuda" and (load_in_4bit or load_in_8bit):
        from transformers import BitsAndBytesConfig
        if load_in_4bit:
            qconfig = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
        else:
            qconfig = BitsAndBytesConfig(load_in_8bit=True)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=qconfig,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
        )
        if device == "cpu":
            model = model.to(device)
    model.eval()
    return model_name


@app.get("/health")
def health():
    """Check if model is loaded and ready for inference."""
    if model is None or processor is None:
        return {
            "status": "model_not_loaded",
            "model": None,
        }
    
    # Verify model is actually ready by checking if it has parameters loaded
    # During loading, model exists but parameters might still be loading
    try:
        import torch
        # Check if model has parameters and they're on the correct device
        if hasattr(model, 'parameters'):
            # Try to access a parameter to ensure it's loaded
            next(model.parameters(), None)
            # Check if model is in eval mode (set after loading completes)
            if hasattr(model, 'training'):
                is_ready = not model.training  # Should be False (eval mode)
            else:
                is_ready = True
        else:
            is_ready = False
    except Exception as e:
        # If we can't check parameters, assume not ready
        # This can happen during loading
        is_ready = False
    
    return {
        "status": "ok" if is_ready else "model_not_loaded",
        "model": "Qwen2.5-VL-7B" if is_ready else None,
    }


def _pdf_to_image(pdf_path: str) -> str | None:
    """Convert first PDF page to image. Returns path to temp image or None."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_path = pdf_path.replace(".pdf", "_page0.png")
        pix.save(img_path)
        doc.close()
        return img_path
    except Exception:
        return None


@app.post("/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    """Analyze video and return visual delivery notes (body movement, eye contact, etc.)."""
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Qwen model not loaded")

    content_type = file.content_type or ""
    if "video" not in content_type and not file.filename.lower().endswith(
        (".mp4", ".webm", ".mov", ".avi", ".mkv")
    ):
        raise HTTPException(status_code=400, detail="Expected video file (MP4, WebM, etc.)")

    suffix = Path(file.filename or "video").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        import torch
        import gc
        
        # Clear memory before processing to free up space from previous requests
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "video", "path": tmp_path},
                    {
                        "type": "text",
                        "text": (
                            "Watch this video and write ONE paragraph (3-5 sentences) describing ONLY the visual delivery. "
                            "Include: body movement, eye contact, gestures, posture, use of presentation slides if visible, "
                            "facial expressions, and professional appearance. Be specific and observational. "
                            "Do not summarize what was said. Output only the paragraph, no JSON or labels."
                        ),
                    },
                ],
            }
        ]

        # Reduced fps from 0.25 to 0.15 to use fewer video frames and save memory
        inputs = processor.apply_chat_template(
            conversation,
            fps=0.15,  # Reduced from 0.25 to save memory (fewer frames processed)
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}

        # Clear cache again after moving inputs to GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=512, do_sample=False)

        gen_ids = [o[len(i) :] for i, o in zip(inputs["input_ids"], out)]
        text = processor.batch_decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        video_notes = (text[0] or "").strip()

        return {"video_notes": video_notes}
    finally:
        # Memory cleanup to prevent OOM on subsequent requests
        try:
            import gc
            import torch
            # Clear PyTorch cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            # Force garbage collection
            gc.collect()
        except Exception as cleanup_error:
            print(f"[analyze_video] Memory cleanup warning: {cleanup_error!s}", flush=True)
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _load_behavior_references() -> list:
    """Load behavior references (what to look for: hands in pockets, purpose statement, etc.)."""
    path = os.environ.get("QWEN_BEHAVIOR_REFERENCES_PATH", "")
    if not path:
        path = _script_dir / "qwen_behavior_references.json"
    else:
        path = Path(path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


BEHAVIOR_REFERENCES: list = _load_behavior_references()


def _format_behavior_references_block(behaviors: list) -> str:
    if not behaviors:
        return ""
    lines = [
        "Identify and timestamp these behaviors when you see or hear them (use for scoring and timeline_markers):"
    ]
    for b in behaviors:
        label = b.get("label", "Behavior")
        btype = b.get("type", "delivery")
        desc = b.get("description", "")
        guidance = b.get("scoring_guidance", "")
        lines.append(f"- {label} ({btype}): {desc} Scoring: {guidance}")
    return "\n".join(lines)


def _get_textbook_chunks_block(rubric: dict) -> str:
    """Retrieve relevant textbook chunks for RAG. Returns empty string if no textbook or retrieval fails."""
    if os.environ.get("DISABLE_TEXTBOOK_RAG", "").strip().lower() in ("1", "true", "yes"):
        return ""
    textbook_id = rubric.get("textbook_id") or rubric.get("textbookId")
    if not textbook_id:
        return ""
    try:
        from llm_training import textbook_rag
        queries = []
        for cat in rubric.get("categories") or []:
            if isinstance(cat, dict):
                if cat.get("name"):
                    queries.append(cat["name"])
                for s in cat.get("subcategories") or []:
                    n = s.get("name", s) if isinstance(s, dict) else s
                    if n:
                        queries.append(str(n))
            elif cat:
                queries.append(str(cat))
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


def _rubric_to_eval_prompt(rubric: dict) -> str:
    """Build the rubric description for the evaluation prompt (with point values and subcategory descriptions)."""
    if not rubric or not isinstance(rubric.get("categories"), list):
        return "Categories: Content, Delivery. Subcategories: score each as appropriate."
    dist = _rubric_point_distribution(rubric)
    lines = []
    for cat in rubric["categories"]:
        name = cat.get("name", "Category") if isinstance(cat, dict) else str(cat)
        cat_desc = (cat.get("description") or "").strip() if isinstance(cat, dict) else ""
        subs = cat.get("subcategories", []) if isinstance(cat, dict) else []
        cat_info = dist.get(name, {})
        max_score = cat_info.get("maxScore")
        sub_lines = []
        for i, s in enumerate(subs):
            if isinstance(s, dict):
                sub_name = s.get("name", "")
                pts = s.get("points", "")
                desc = (s.get("description") or "").strip()
                sub_max = (cat_info.get("subcategories") or [{}])[i].get("maxPoints") if i < len(cat_info.get("subcategories") or []) else None
                pts = sub_max if sub_max is not None else pts
                if pts not in (None, ""):
                    sub_str = f"{sub_name} (max {pts} pts)"
                else:
                    sub_str = sub_name
                if desc:
                    sub_str += f" — {desc}"
                sub_lines.append(sub_str)
            else:
                sub_name = str(s)
                sub_max = (cat_info.get("subcategories") or [{}])[i].get("maxPoints") if i < len(cat_info.get("subcategories") or []) else None
                sub_str = f"{sub_name} (max {sub_max} pts)" if sub_max is not None else sub_name
                sub_lines.append(sub_str)
        if sub_lines:
            header = f"- {name}"
            if max_score is not None:
                header += f" [category maxScore: {max_score}]"
            if cat_desc:
                header += f" — {cat_desc}"
            lines.append(header)
            for sl in sub_lines:
                lines.append(f"  • {sl}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines) if lines else "Score each category and subcategory."


def _rubric_point_block(rubric: dict) -> str:
    """Build explicit point-values block for prompt so model uses correct math."""
    dist = _rubric_point_distribution(rubric)
    if not dist:
        return ""
    total = rubric.get("totalPoints") or 50
    lines = [f"CRITICAL: Total = {total} points. Each category has a fixed maxScore; use these exact values:"]
    for name, info in dist.items():
        max_cat = info.get("maxScore")
        subs = info.get("subcategories", [])
        if max_cat is not None:
            sub_pts = ", ".join(f'{s.get("name","")}({s.get("maxPoints","")})' for s in subs if s.get("maxPoints") is not None)
            lines.append(f'  "{name}" maxScore={max_cat} | subcategories: {sub_pts}')
    return "\n".join(lines)


def _rubric_point_distribution(rubric: dict) -> dict:
    """Return correct maxScore per category and maxPoints per subcategory from rubric. Used to enforce correct math."""
    if not rubric or not isinstance(rubric.get("categories"), list):
        return {}
    total = rubric.get("totalPoints") or 50
    cats = rubric["categories"]
    total_subs = sum(
        len(c.get("subcategories", [])) if isinstance(c, dict) else 0
        for c in cats
    )
    points_per_sub = total / total_subs if total_subs else 0
    out = {}
    for c in cats:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not name:
            continue
        subs = c.get("subcategories", [])
        sub_list = []
        max_cat = 0
        for s in subs:
            if isinstance(s, dict):
                sub_name = s.get("name", "Item")
                pts = s.get("points")
                try:
                    pts = float(pts) if pts not in (None, "") else points_per_sub
                except (TypeError, ValueError):
                    pts = points_per_sub
            else:
                sub_name = str(s)
                pts = points_per_sub
            max_cat += pts
            sub_list.append({"name": sub_name, "maxPoints": round(pts, 2)})
        out[name] = {"maxScore": round(max_cat, 2), "subcategories": sub_list}
    return out


def _rubric_section_keys(rubric: dict) -> str:
    """Exact category names to use as keys in 'sections' (so the model matches the frontend)."""
    if not rubric or not isinstance(rubric.get("categories"), list):
        return "Content, Delivery"
    names = []
    for cat in rubric["categories"]:
        name = cat.get("name", "") if isinstance(cat, dict) else str(cat)
        if name:
            names.append(name)
    return ", ".join(names) if names else "Content, Delivery"


def _placeholder_sections_from_rubric(rubric: dict) -> dict:
    """Build minimal sections (0 points) from rubric when the model didn't return scores. Keeps UI from being blank."""
    dist = _rubric_point_distribution(rubric)
    if not dist:
        return {}
    sections = {}
    for name, info in dist.items():
        sub_list = [{"name": s.get("name", ""), "points": 0, "maxPoints": s.get("maxPoints", 0)} for s in info.get("subcategories", [])]
        sections[name] = {"score": 0, "maxScore": info.get("maxScore", 0), "subcategories": sub_list}
    return sections


def _normalize_sections_to_rubric(sections: dict, rubric: dict) -> dict:
    """Enforce rubric point distribution: override maxScore/maxPoints and scale model scores proportionally."""
    dist = _rubric_point_distribution(rubric)
    if not dist or not sections:
        return sections
    out = {}
    for cat_name, sec in sections.items():
        if not isinstance(sec, dict):
            out[cat_name] = sec
            continue
        info = dist.get(cat_name)
        if not info:
            out[cat_name] = sec
            continue
        rubric_max = info.get("maxScore")
        rubric_subs = {s.get("name", "").strip().lower(): s.get("maxPoints") for s in info.get("subcategories", []) if s.get("name")}
        model_max = sec.get("maxScore")
        model_score = sec.get("score", 0) or 0
        # Scale category score if model used wrong max
        if rubric_max is not None:
            if model_max and model_max > 0:
                pct = min(1.0, model_score / model_max)
                new_score = round(pct * rubric_max, 2)
            else:
                new_score = 0.0
            sec = dict(sec)
            sec["maxScore"] = rubric_max
            sec["score"] = min(new_score, rubric_max)
        # Normalize subcategories
        subs = sec.get("subcategories") or []
        new_subs = []
        for i, sub in enumerate(subs):
            if not isinstance(sub, dict):
                new_subs.append(sub)
                continue
            sub_name = (sub.get("name") or "").strip()
            sub_lower = sub_name.lower()
            rubric_mp = rubric_subs.get(sub_lower)
            if rubric_mp is None and info.get("subcategories"):
                by_idx = info["subcategories"]
                if i < len(by_idx):
                    rubric_mp = by_idx[i].get("maxPoints")
            model_mp = sub.get("maxPoints")
            model_pts = sub.get("points", 0) or 0
            sub = dict(sub)
            if rubric_mp is not None:
                sub["maxPoints"] = rubric_mp
                if model_mp and model_mp > 0:
                    pct = min(1.0, model_pts / model_mp)
                    sub["points"] = round(pct * rubric_mp, 2)
                else:
                    sub["points"] = 0.0
            new_subs.append(sub)
        sec["subcategories"] = new_subs
        # Recompute category score from subcategories if we have them
        if new_subs and rubric_max is not None:
            sub_sum = sum(s.get("points", 0) or 0 for s in new_subs if isinstance(s, dict))
            sec["score"] = min(round(sub_sum, 2), rubric_max)
        out[cat_name] = sec
    return out


def _feedback_from_timeline(timeline_markers: list, section_key: str) -> str:
    """Build feedback text from timeline markers for a given category when model didn't provide it."""
    if not timeline_markers or not section_key:
        return "See timeline for observed behaviors."
    key_lower = section_key.lower()
    key_parts = [p.strip().lower() for p in key_lower.split("-") if p.strip()]
    relevant = []
    for m in timeline_markers:
        if not isinstance(m, dict):
            continue
        cat = (m.get("category") or "").lower()
        issue = m.get("issue") or m.get("label") or m.get("observation") or ""
        note = m.get("observation") or m.get("note") or m.get("label") or ""
        ts = m.get("timestamp") or ""
        if not (issue or note):
            continue
        if not cat:
            continue
        if cat in key_lower or any(p in cat for p in key_parts):
            relevant.append((ts, issue or note, note if issue else ""))
    if not relevant:
        return "See timeline for observed behaviors."
    parts = [f"[{ts}] {issue}" if ts else issue for ts, issue, _ in relevant[:5]]
    return "Observations: " + "; ".join(parts) + "."


def _scrape_scores_from_raw(raw: str, rubric: dict, placeholder_sections: dict) -> dict:
    """Try to extract numeric scores from raw model output and fill into placeholder sections. Returns copy with scores updated where found."""
    import re
    if not placeholder_sections or not raw:
        return dict(placeholder_sections) if placeholder_sections else {}
    out = json.loads(json.dumps(placeholder_sections))  # deep copy
    for cat_name in list(out.keys()):
        cat = out[cat_name]
        if not isinstance(cat, dict):
            continue
        max_score = cat.get("maxScore", 0)
        search_key = cat_name
        idx = raw.find(search_key)
        if idx == -1:
            # try last part of key (e.g. "Introduction" from "Content - Introduction")
            search_key = cat_name.split(" - ")[-1].strip() if " - " in cat_name else cat_name
            idx = raw.find(search_key)
        if idx == -1:
            idx = 0
        chunk = raw[idx : idx + 280]
        # Prefer "score": N then "points": N then bare N
        m = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', chunk)
        if m:
            try:
                n = float(m.group(1))
                cat["score"] = min(max(n, 0), max_score) if max_score else n
            except (ValueError, TypeError):
                pass
        else:
            m = re.search(r'"points"\s*:\s*(\d+(?:\.\d+)?)', chunk)
            if m:
                try:
                    n = float(m.group(1))
                    cat["score"] = min(max(n, 0), max_score) if max_score else n
                except (ValueError, TypeError):
                    pass
        # Subcategory points if we see "name": "Sub" ... "points": N
        for sub in cat.get("subcategories", []):
            if not isinstance(sub, dict):
                continue
            sub_name = sub.get("name", "")
            if not sub_name:
                continue
            sub_idx = raw.find(sub_name)
            if sub_idx == -1:
                continue
            sub_chunk = raw[sub_idx : sub_idx + 120]
            sm = re.search(r'"points"\s*:\s*(\d+(?:\.\d+)?)', sub_chunk)
            if sm:
                try:
                    sub_max = sub.get("maxPoints", 0)
                    n = float(sm.group(1))
                    sub["points"] = min(max(n, 0), sub_max) if sub_max else n
                except (ValueError, TypeError):
                    pass
    return out


EVALUATE_VIDEO_PROMPT = """Watch and listen to this speech video. Evaluate it using the rubric below.

How to assess:
- **Content and verbal delivery**: Use the speech (what is said and how it is said)—main ideas, organization, purpose statement, evidence, vocal delivery, pacing, vocalized pauses, clarity. Score content and verbal-delivery categories from the speaker's words and voice.
- **Non-verbal delivery**: Use the video (what you see)—eye contact with camera or audience, posture, gestures, hands (in pockets, clasped, tapping), movement or swaying, professional setup. Score non-verbal-delivery categories from the visual.
- **Timeline markers**: For each specific behavior you observe, record the approximate time (seconds from the start) and note what occurred, so the evaluation shows when behaviors happened.

Rubric categories and subcategories to score:
{rubric_structure}
{point_block}
{example_videos_block}
{behavior_block}
{textbook_block}

IMPORTANT: The "sections" object must use exactly these keys (category names): {section_keys}. Use the exact maxScore and maxPoints from the point values above—do not invent your own (e.g. do not use 10 for every category).

Context: The video may be an in-person presentation or an online/remote presentation (e.g. webcam, video call). If it appears to be online (head and shoulders only): focus on eye contact with camera, vocal delivery, vocalized pauses, purpose statement, and professional setup. Body-focused behaviors (hands in pockets, swaying, hands clasped) may not be visible—only mark them if clearly visible. If full body is visible, apply all behaviors as appropriate.

Output ONLY a single valid JSON object (no markdown, no explanation). You MUST include both keys. Put "sections" first so scores are not cut off:
1) "sections": an object where each key is one of the category names above (exactly: {section_keys}) and each value has "score", "maxScore", "feedback" (a 1–2 sentence explanation of the category score based on observations), and "subcategories" (array of {{"name", "points", "maxPoints", "feedback"}}). Use the rubric's point values. You MUST include every category and assign a real numeric score (between 0 and maxScore) for each—do not leave scores at 0 unless the speaker truly earned zero. Include "feedback" for each category AND for each subcategory (brief 1-sentence explanation of what you observed for that subcategory). Base category scores on content/verbal delivery when the rubric refers to what is said or how it is said, and on non-verbal delivery when the rubric refers to what is seen (eye contact, posture, gestures, etc.).
2) "timeline_markers": an array of objects for each behavior you observe, with approximate time and impact. Each object: {{"seconds": number (approximate time in video), "label": "short behavior name", "observation": "brief note", "severity": "positive" or "minor" or "moderate" or "major", "category": "Content" or "Delivery"}}. Include markers for the behaviors listed above. Estimate seconds from the start of the video.

Examples of the exact JSON structure (use the rubric's category names, not these placeholders):

Example 1 (real rubric):
{{"sections": {{"Content": {{"score": 35, "maxScore": 40, "feedback": "Strong organization and clear purpose. Main points were well supported.", "subcategories": [{{"name": "Organization", "points": 12, "maxPoints": 15, "feedback": "Clear structure with logical flow."}}]}}, "Delivery": {{"score": 28, "maxScore": 30, "feedback": "Good eye contact with occasional hands in pockets. Vocal delivery was clear.", "subcategories": [{{"name": "Eye contact", "points": 14, "maxPoints": 15, "feedback": "Generally good, a few glances away."}}]}}}}, "timeline_markers": [{{"seconds": 15, "label": "Purpose statement", "observation": "Clear goal stated", "severity": "positive", "category": "Content"}}, {{"seconds": 83, "label": "Hands in pockets", "observation": "Hands in pockets briefly", "severity": "moderate", "category": "Delivery"}}]}}

Example 2 (structure only—use YOUR rubric's category names):
{{"sections": {{"Category A": {{"score": 8, "maxScore": 10, "feedback": "Brief explanation of what you observed.", "subcategories": [{{"name": "Subcategory 1", "points": 4, "maxPoints": 5, "feedback": "Brief note for this subcategory."}}]}}, "Category B": {{"score": 7, "maxScore": 10, "feedback": "Brief explanation of what you observed.", "subcategories": [{{"name": "Subcategory 1", "points": 3, "maxPoints": 5, "feedback": "Brief note for this subcategory."}}]}}}}, "timeline_markers": [{{"seconds": 30, "label": "Behavior name", "observation": "What occurred", "severity": "minor", "category": "Category A"}}]}}

Output only the JSON object. Do not wrap in markdown. Use the exact category and subcategory names from the rubric above."""


def _strip_markdown_json(text: str) -> str:
    """Remove markdown code fence so we can parse JSON inside ```json ... ``` or ``` ... (handles truncated output with no closing fence)."""
    s = text.strip()
    # Strip opening fence (```json or ```, case-insensitive)
    m = re.match(r"^```(?:json)?\s*\n?", s, re.IGNORECASE)
    if m:
        s = s[m.end() :].lstrip()
    # Strip closing fence if present (truncated output may not have it)
    if s.endswith("```"):
        s = s[:-3].rstrip()
    return s


def _extract_sections_from_raw(raw: str) -> dict | None:
    """Try to find and parse a 'sections' object when it appears as a key in raw text (e.g. model output sections in a different block)."""
    idx = raw.find('"sections"')
    if idx == -1:
        idx = raw.find("'sections'")
    if idx == -1:
        return None
    # Find the next ':' then skip whitespace and '{'
    after_key = raw[idx:].find(":")
    if after_key == -1:
        return None
    start = idx + after_key + 1
    while start < len(raw) and raw[start] in " \t\n\r":
        start += 1
    if start >= len(raw) or raw[start] != "{":
        return None
    depth = 0
    end = -1
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        # Truncated: strip trailing comma, close braces, and parse
        fragment = raw[start:].rstrip()
        while fragment.endswith(","):
            fragment = fragment[:-1].rstrip()
        if depth > 0:
            try:
                closed = fragment + ("}" * depth)
                return json.loads(closed)
            except json.JSONDecodeError:
                pass
        return None
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return None


def _extract_json_from_response(text: str) -> dict | None:
    """Parse one or more JSON objects from model output and merge. Handles ```json fences and truncated output."""
    text = _strip_markdown_json(text)
    merged: dict = {}
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
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
            # Truncated JSON: strip trailing comma, close braces, and parse
            fragment = text[start:].rstrip()
            while fragment.endswith(","):
                fragment = fragment[:-1].rstrip()
            if depth > 0:
                try:
                    closed = fragment + ("}" * depth)
                    obj = json.loads(closed)
                    if isinstance(obj, dict):
                        if obj.get("sections"):
                            merged["sections"] = obj["sections"]
                        if obj.get("timeline_markers") is not None:
                            merged["timeline_markers"] = obj["timeline_markers"]
                        if obj.get("overallComments") or obj.get("overall_comments"):
                            merged["overallComments"] = obj.get("overallComments") or obj.get("overall_comments")
                        if obj.get("transcript") is not None:
                            merged["transcript"] = obj["transcript"]
                except json.JSONDecodeError:
                    pass
            break
        try:
            obj = json.loads(text[start:end])
            if isinstance(obj, dict):
                if obj.get("sections"):
                    merged["sections"] = obj["sections"]
                if obj.get("timeline_markers") is not None:
                    merged["timeline_markers"] = obj["timeline_markers"]
                if obj.get("overallComments") or obj.get("overall_comments"):
                    merged["overallComments"] = obj.get("overallComments") or obj.get("overall_comments")
                if obj.get("transcript") is not None:
                    merged["transcript"] = obj["transcript"]
        except json.JSONDecodeError:
            pass
        pos = end
    # If we have markers but no sections, try to find "sections" elsewhere in raw text
    if merged.get("timeline_markers") is not None and not merged.get("sections"):
        sections = _extract_sections_from_raw(text)
        if sections:
            merged["sections"] = sections
    # If still no sections but raw has a truncated "sections" object, try extracting it
    if not merged.get("sections"):
        sections = _extract_sections_from_raw(text)
        if sections:
            merged["sections"] = sections
    return merged if merged else None


@app.post("/evaluate_video")
async def evaluate_video(
    file: UploadFile = File(None),
    rubric: str = Form(...),
    storage_url: str = Form(None),
):
    """
    Evaluate a speech video using the rubric. Returns same shape as SpeechGradebook Model: sections, overallComments, transcript.
    
    Accepts either:
    - file: Direct file upload (traditional method)
    - storage_url: URL to video in Supabase Storage (direct upload path - bypasses Render memory)
    """
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Qwen model not loaded")
    
    # Verify model is actually ready (not just that the object exists)
    # During loading, model object exists but parameters might still be loading
    try:
        import torch
        if hasattr(model, 'parameters'):
            # Try to access parameters to ensure they're loaded
            param = next(model.parameters(), None)
            if param is None:
                raise HTTPException(status_code=503, detail="Qwen model parameters not loaded yet")
            # Check if model is in eval mode (set after loading completes)
            if hasattr(model, 'training') and model.training:
                raise HTTPException(status_code=503, detail="Qwen model still loading (not in eval mode)")
    except HTTPException:
        raise
    except Exception as e:
        # If we can't verify, assume not ready to be safe
        raise HTTPException(status_code=503, detail=f"Qwen model not ready: {str(e)}")

    # Support both file upload and storage URL
    tmp_path = None
    if storage_url:
        # Fetch video from storage URL
        print(f"[evaluate_video] Using storage URL: {storage_url}", flush=True)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=300.0) as client:
                video_response = await client.get(storage_url)
                if video_response.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch video from storage URL: {video_response.status_code}")
                
                # Save to temp file
                suffix = Path(storage_url).suffix or ".mp4"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(video_response.content)
                    tmp_path = tmp.name
        except Exception as e:
            print(f"[evaluate_video] Failed to fetch from storage URL: {e!s}", flush=True)
            raise HTTPException(status_code=400, detail=f"Failed to fetch video from storage URL: {str(e)}")
    elif file:
        # Traditional file upload
        content_type = file.content_type or ""
        fname = (file.filename or "").lower()
        if "video" not in content_type and not fname.endswith((".mp4", ".webm", ".mov", ".avi", ".mkv")):
            print(f"[evaluate_video] 400: bad file type content_type={content_type!r} filename={file.filename!r}", flush=True)
            raise HTTPException(status_code=400, detail="Expected video file (MP4, WebM, etc.)")
        
        suffix = Path(file.filename or "video").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
    else:
        raise HTTPException(status_code=400, detail="Either 'file' or 'storage_url' must be provided")

    try:
        rubric_obj = json.loads(rubric)
    except json.JSONDecodeError as e:
        print(f"[evaluate_video] 400: invalid rubric JSON: {e!s}, rubric_len={len(rubric)}, rubric_preview={rubric[:200]!r}", flush=True)
        raise HTTPException(status_code=400, detail=f"Invalid rubric JSON: {e}")

    rubric_structure = _rubric_to_eval_prompt(rubric_obj)
    behavior_block = _format_behavior_references_block(BEHAVIOR_REFERENCES)
    if not behavior_block:
        behavior_block = ""
    section_keys = _rubric_section_keys(rubric_obj)
    point_block = _rubric_point_block(rubric_obj)
    example_videos = rubric_obj.get("exampleVideos") or rubric_obj.get("example_videos") or []
    if example_videos and isinstance(example_videos, list):
        lines = ["Reference example videos (instructor-provided URLs for context):"]
        for ev in example_videos:
            if isinstance(ev, dict) and ev.get("url"):
                label = ev.get("label", "").strip()
                lines.append(f"- {ev['url']}" + (f" ({label})" if label else ""))
        example_videos_block = "\n".join(lines)
    else:
        example_videos_block = ""
    try:
        textbook_block = _get_textbook_chunks_block(rubric_obj)
    except Exception as e:
        print(f"[evaluate_video] textbook RAG skipped: {e!s}", flush=True)
        textbook_block = ""
    prompt_text = EVALUATE_VIDEO_PROMPT.format(
        rubric_structure=rubric_structure,
        point_block=point_block,
        example_videos_block=example_videos_block,
        behavior_block=behavior_block,
        textbook_block=textbook_block,
        section_keys=section_keys,
    )

    try:
        import torch
        import gc
        
        # Clear memory before processing to free up space from previous requests
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "video", "path": tmp_path},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]

        # Reduced fps from 0.25 to 0.15 to use fewer video frames and save memory
        inputs = processor.apply_chat_template(
            conversation,
            fps=0.15,  # Reduced from 0.25 to save memory (fewer frames processed)
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}

        # Clear cache again after moving inputs to GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        with torch.no_grad():
            # Reduced max_new_tokens from 4096 to 3072 to save memory
            out = model.generate(**inputs, max_new_tokens=3072, do_sample=False)

        gen_ids = [o[len(i):] for i, o in zip(inputs["input_ids"], out)]
        text = processor.batch_decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        raw = (text[0] or "").strip()

        parsed = _extract_json_from_response(raw)
        sections = parsed.get("sections") if parsed else None
        print(f"[evaluate_video] raw_len={len(raw)} parsed_keys={list(parsed.keys()) if parsed else None} has_sections={bool(sections)} section_keys={list(sections.keys()) if isinstance(sections, dict) else None}", flush=True)
        if parsed is None:
            return {
                "sections": {},
                "overallComments": "Qwen could not return valid JSON. Raw output: " + raw[:500],
                "transcript": "",
                "timeline_markers": [],
            }

        # New format: {"sections": {...}, "timeline_markers": [...], "overallComments": "..." }
        if sections is None:
            # Fallback: whole object is sections (old format), no timeline_markers
            sections = {k: v for k, v in parsed.items() if isinstance(v, dict) and ("score" in v or "subcategories" in v)}
        raw_markers = parsed.get("timeline_markers")
        if not isinstance(raw_markers, list):
            raw_markers = []
        overall_comments = parsed.get("overallComments") or parsed.get("overall_comments") or ""

        # Normalize to UI shape: timestamp, seconds, category, issue, severity, note
        timeline_markers = []
        for m in raw_markers:
            if not isinstance(m, dict):
                continue
            sec = m.get("seconds", 0)
            mins = int(sec // 60)
            secs = int(sec % 60)
            timestamp = f"{mins}:{secs:02d}"
            timeline_markers.append({
                "timestamp": timestamp,
                "seconds": sec,
                "category": m.get("category", "Delivery"),
                "issue": m.get("label", m.get("observation", "Observation")),
                "severity": m.get("severity", "minor"),
                "note": m.get("observation", m.get("label", "")),
            })

        # When model returns no section scores, build from rubric and try to scrape any scores from raw text
        if (not sections or len(sections) == 0) and rubric_obj:
            placeholder = _placeholder_sections_from_rubric(rubric_obj)
            sections = _scrape_scores_from_raw(raw, rubric_obj, placeholder)
            if timeline_markers and sections and not overall_comments.strip():
                has_any_score = any(
                    (s.get("score") or 0) > 0
                    for s in (sections or {}).values()
                    if isinstance(s, dict)
                )
                if not has_any_score:
                    overall_comments = "Scores were not returned by the model; see timeline for observed behaviors."
        # If model returned sections but all scores are 0, try to scrape scores from raw text (e.g. model wrote numbers in prose)
        elif sections and rubric_obj and raw:
            all_zero = all(
                (s.get("score") or 0) == 0
                for s in sections.values()
                if isinstance(s, dict)
            )
            if all_zero:
                sections = _scrape_scores_from_raw(raw, rubric_obj, sections)

        # Fill missing feedback from timeline markers so "No feedback provided" is avoided
        sections = sections or {}
        for key, sec in list(sections.items()):
            if isinstance(sec, dict) and not (sec.get("feedback") or "").strip():
                sec["feedback"] = _feedback_from_timeline(timeline_markers, key)

        # Enforce rubric point distribution so section/sub maxes and totals match
        if sections and rubric_obj:
            sections = _normalize_sections_to_rubric(sections, rubric_obj)

        return {
            "sections": sections,
            "overallComments": overall_comments,
            "transcript": parsed.get("transcript") or "",
            "timeline_markers": timeline_markers,
        }
    except Exception as e:
        print(f"[evaluate_video] 500: {e!s}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Memory cleanup to prevent OOM on subsequent requests
        try:
            import gc
            import torch
            # Clear PyTorch cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            # Force garbage collection
            gc.collect()
        except Exception as cleanup_error:
            print(f"[evaluate_video] Memory cleanup warning: {cleanup_error!s}", flush=True)
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


RUBRIC_EXTRACT_PROMPT = """You are analyzing a rubric document. Extract ALL the information and return ONLY a valid JSON object (no markdown, no explanation, no preamble).

The JSON must have this exact structure:
{
  "speechType": "type of speech if mentioned, or 'General'",
  "totalPoints": total possible points as a number,
  "categories": [
    {
      "name": "Category Name",
      "subcategories": [
        {
          "name": "Subcategory Name",
          "points": point value as number,
          "description": "criteria description"
        }
      ]
    }
  ],
  "gradeScale": {
    "A": {"min": 90, "label": "Excellent"},
    "B": {"min": 80, "label": "Good"},
    "C": {"min": 70, "label": "Satisfactory"},
    "D": {"min": 60, "label": "Needs Improvement"},
    "F": {"min": 0, "label": "Unsatisfactory"}
  }
}

Extract every category, subcategory, point value, and grading criterion you can find. If the grading scale is specified in the rubric, use those values instead of the defaults shown above.

IMPORTANT: Keep each description to a SHORT phrase (max 40 chars). Use abbreviations if needed. This prevents output truncation.

Return ONLY the JSON object, nothing else."""


@app.post("/extract_rubric")
async def extract_rubric(file: UploadFile = File(...)):
    """Extract rubric structure from image or PDF."""
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Qwen model not loaded")

    fn = file.filename or "file"
    content = await file.read()
    content_type = file.content_type or ""

    # Determine if PDF (convert to image) or image
    is_pdf = content_type == "application/pdf" or fn.lower().endswith(".pdf")
    img_path = None

    if is_pdf:
        suffix = ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            pdf_path = tmp.name
        img_path = _pdf_to_image(pdf_path)
        try:
            os.unlink(pdf_path)
        except OSError:
            pass
        if not img_path:
            raise HTTPException(
                status_code=400,
                detail="PDF conversion failed. Install PyMuPDF: pip install pymupdf. Or use an image (PNG, JPG) of the rubric.",
            )
    else:
        ext = Path(fn).suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            img_path = tmp.name

    try:
        import torch
        import gc
        
        # Clear memory before processing to free up space from previous requests
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img_path},
                    {"type": "text", "text": RUBRIC_EXTRACT_PROMPT},
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}

        # Clear cache again after moving inputs to GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        with torch.no_grad():
            # Reduced max_new_tokens from 4096 to 3072 to save memory
            out = model.generate(**inputs, max_new_tokens=3072, do_sample=False)

        gen_ids = [o[len(i) :] for i, o in zip(inputs["input_ids"], out)]
        text = processor.batch_decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        raw = (text[0] or "").strip()

        # Parse JSON (handle markdown fences and truncation)
        import re
        if "```" in raw:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                raw = m.group(1).strip()
        start = raw.find("{")
        if start >= 0:
            raw = raw[start:]
        raw = raw.rstrip().rstrip(",")
        rubric = None
        for _ in range(20):
            try:
                rubric = json.loads(raw)
                break
            except json.JSONDecodeError:
                if raw.count("[") > raw.count("]"):
                    raw += "]"
                elif raw.count("{") > raw.count("}"):
                    raw += "}"
                else:
                    raise
        if rubric is None:
            rubric = json.loads(raw)
        return rubric
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse rubric JSON: {e}")
    finally:
        # Memory cleanup to prevent OOM on subsequent requests
        try:
            import gc
            import torch
            # Clear PyTorch cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            # Force garbage collection
            gc.collect()
        except Exception as cleanup_error:
            print(f"[extract_rubric] Memory cleanup warning: {cleanup_error!s}", flush=True)
        # Clean up temp file
        try:
            if img_path and os.path.exists(img_path):
                os.unlink(img_path)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser()
    default_port = int(os.environ.get("PORT", "8001"))
    parser.add_argument("--port", type=int, default=default_port, help=f"Port to bind (default: {default_port}, or PORT env)")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-VL-7B-Instruct")
    parser.add_argument("--root-path", type=str, default="", help="Serve app under this path (e.g. /qwen so routes are /qwen/health, /qwen/evaluate_video). Use when tunnel or proxy uses path-based URL like https://speechgradebook.com/qwen")
    args = parser.parse_args()

    print("Loading Qwen2.5-VL...")
    _load_model(args.model)
    print("Model loaded.")

    import uvicorn

    root_path = (args.root_path or "").strip().rstrip("/")
    if root_path:
        root_path = "/" + root_path.lstrip("/")
        root_app = FastAPI(title="Qwen root")
        root_app.mount(root_path, app)
        print(f"Serving under {root_path} (e.g. {root_path}/health)")
        uvicorn.run(root_app, host="0.0.0.0", port=args.port)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
