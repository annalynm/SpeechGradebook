#!/usr/bin/env python3
"""
Single Render service: serves SpeechGradebook frontend (static) and Fine-tuned API at /api.

Run from SpeechGradebook/:
  uvicorn app:app --host 0.0.0.0 --port $PORT

- Frontend: / and /index.html, /consent.html, etc.
- API: /api/health, /api/evaluate, /api/evaluate_with_file

Set Evaluation server URL in the app to: https://speechgradebook.onrender.com/api

Required environment variables:
  SUPABASE_URL        - Your Supabase project URL
  SUPABASE_ANON_KEY   - Your Supabase anon/public key (not the service role key)

Optional:
  ALLOWED_ORIGINS     - Comma-separated list of allowed CORS origins (default: same origin only)
  MODEL_PATH          - Path to fine-tuned model adapter
  BASE_MODEL          - Base model name (default: mistralai/Mistral-7B-Instruct-v0.2)
  LOAD_IN_8BIT        - Load model in 8-bit mode (1/true/yes)

Local development: Create a .env file with SUPABASE_URL and SUPABASE_ANON_KEY, then run ./run_local.sh
"""

import json
import os
import time
from pathlib import Path

# Load .env for local development (optional)
_this_dir = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    # Load from project root (next to app.py) so it works no matter where uvicorn is started
    load_dotenv(_this_dir / ".env", override=True)
except ImportError:
    pass
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


# Ensure RENDER_LLM_EXPORT_SECRET is set from .env if present (sub-app may run in context where env wasn't loaded)
if not os.environ.get("RENDER_LLM_EXPORT_SECRET"):
    _val = _read_llm_export_secret_from_env_file(_this_dir / ".env")
    if _val:
        os.environ["RENDER_LLM_EXPORT_SECRET"] = _val

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRouter
import httpx

# Import the evaluation API app (model loaded on startup if MODEL_PATH exists)
from llm_training import serve_model

app = FastAPI(title="SpeechGradebook")

# CORS so OPTIONS preflight succeeds for /qwen-api/* (e.g. when origin is speechgradebook.com and API is www.speechgradebook.com)
_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] if _origins_env else [
    "https://www.speechgradebook.com", "https://speechgradebook.com",
    "https://speechgradebook.onrender.com", "http://localhost:8000", "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ----- Qwen proxy router: registered first so /qwen-api/* is never shadowed by StaticFiles mount at / -----
def _qwen_base():
    base = _get_env("QWEN_API_URL", "").strip().rstrip("/")
    return base if base else None


qwen_router = APIRouter(prefix="/qwen-api", tags=["qwen"])


@qwen_router.get("/health")
async def qwen_proxy_health():
    base = _qwen_base()
    if not base:
        return Response(status_code=503, content="QWEN_API_URL not set")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base}/health")
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except Exception as e:
        return Response(status_code=503, content=f"Qwen proxy error: {e!s}")


@qwen_router.post("/evaluate_video")
async def qwen_proxy_evaluate_video(file: UploadFile = File(...), rubric: str = Form(...)):
    base = _qwen_base()
    if not base:
        return Response(status_code=503, content="QWEN_API_URL not set")
    try:
        body = await file.read()
        files = {"file": (file.filename or "video", body, file.content_type or "application/octet-stream")}
        data = {"rubric": rubric}
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{base}/evaluate_video", files=files, data=data)
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except Exception as e:
        return Response(status_code=503, content=f"Qwen proxy error: {e!s}")


@qwen_router.post("/analyze_video")
async def qwen_proxy_analyze_video(file: UploadFile = File(...)):
    base = _qwen_base()
    if not base:
        return Response(status_code=503, content="QWEN_API_URL not set")
    try:
        body = await file.read()
        files = {"file": (file.filename or "video", body, file.content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base}/analyze_video", files=files)
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except Exception as e:
        return Response(status_code=503, content=f"Qwen proxy error: {e!s}")


@qwen_router.post("/extract_rubric")
async def qwen_proxy_extract_rubric(file: UploadFile = File(...)):
    base = _qwen_base()
    if not base:
        return Response(status_code=503, content="QWEN_API_URL not set")
    try:
        body = await file.read()
        files = {"file": (file.filename or "rubric", body, file.content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{base}/extract_rubric", files=files)
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except Exception as e:
        return Response(status_code=503, content=f"Qwen proxy error: {e!s}")


app.include_router(qwen_router)


@app.middleware("http")
async def log_llm_export_requests(request, call_next):
    # Handle /qwen-api in middleware so nothing downstream (router/StaticFiles) can return 405
    path = (request.url.path or "").strip().rstrip("/") or "/"
    if path.startswith("/qwen-api"):
        if request.method == "OPTIONS":
            return Response(status_code=200, headers={"Allow": "GET, POST, OPTIONS"})
        if request.method == "POST" and path in ("/qwen-api/evaluate_video", "/qwen-api/analyze_video", "/qwen-api/extract_rubric"):
            base = _qwen_base()
            if not base:
                return Response(status_code=503, content="QWEN_API_URL not set")
            try:
                form = await request.form()
                file_part = form.get("file")
                rubric_part = form.get("rubric") if path == "/qwen-api/evaluate_video" else None
                if path == "/qwen-api/evaluate_video":
                    if not file_part or not hasattr(file_part, "read"):
                        return JSONResponse(status_code=400, content={"detail": "Missing or invalid file"})
                    if rubric_part is None:
                        return JSONResponse(status_code=400, content={"detail": "Missing rubric"})
                    if isinstance(rubric_part, str):
                        rubric_str = rubric_part
                    elif hasattr(rubric_part, "read"):
                        try:
                            raw = await rubric_part.read()
                        except TypeError:
                            raw = rubric_part.read()
                        rubric_str = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                    else:
                        rubric_str = rubric_part.decode("utf-8", errors="replace") if hasattr(rubric_part, "decode") else str(rubric_part)
                    body = await file_part.read()
                    files = {"file": (getattr(file_part, "filename", None) or "video", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                    data = {"rubric": rubric_str}
                    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                        r = await client.post(f"{base}/evaluate_video", files=files, data=data)
                    if 300 <= r.status_code < 400:
                        return JSONResponse(status_code=502, content={"detail": "Qwen service returned redirect (3xx). Check QWEN_API_URL—use https, no trailing slash. Ensure the Qwen tunnel/URL is correct."})
                    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
                if path == "/qwen-api/analyze_video" and file_part and hasattr(file_part, "read"):
                    body = await file_part.read()
                    files = {"file": (getattr(file_part, "filename", None) or "video", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        r = await client.post(f"{base}/analyze_video", files=files)
                    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
                if path == "/qwen-api/extract_rubric" and file_part and hasattr(file_part, "read"):
                    body = await file_part.read()
                    files = {"file": (getattr(file_part, "filename", None) or "rubric", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        r = await client.post(f"{base}/extract_rubric", files=files)
                    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
            except Exception as e:
                return JSONResponse(status_code=503, content={"detail": f"Qwen proxy error: {e!s}"}, media_type="application/json")
        if request.method == "GET" and path == "/qwen-api/health":
            base = _qwen_base()
            if not base:
                return Response(status_code=503, content="QWEN_API_URL not set")
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(f"{base}/health")
                return Response(content=r.content, status_code=r.status_code, media_type="application/json")
            except Exception as e:
                return Response(status_code=503, content=f"Qwen proxy error: {e!s}")
    # Handle notify-signup-request in middleware so it's never shadowed by the /api mount
    if path == "/api/notify-signup-request":
        if request.method == "POST":
            return await _handle_notify_signup_request(request)
        if request.method == "GET":
            return JSONResponse(status_code=200, content={"message": "Use POST with JSON: email, full_name, requested_role"})
    # #region agent log
    if request.url.path == "/api/llm-export":
        try:
            _log = _this_dir / ".cursor" / "debug.log"
            _log.parent.mkdir(parents=True, exist_ok=True)
            with open(_log, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"timestamp": int(time.time() * 1000), "location": "app.middleware", "message": "POST /api/llm-export reached main app", "data": {"path": request.url.path}, "hypothesisId": "H4", "sessionId": "debug-session"}) + "\n")
                _f.flush()
        except Exception as e:
            try:
                with open(_this_dir / "debug_llm_fallback.log", "a", encoding="utf-8") as _f:
                    _f.write(json.dumps({"error": str(e), "path": str(_log)}) + "\n")
            except Exception:
                pass
    # #endregion
    return await call_next(request)


def _get_env(key: str, default: str = "") -> str:
    """Get env var, strip whitespace and surrounding quotes (e.g. from Render)."""
    v = (os.environ.get(key) or default).strip()
    if len(v) >= 2 and (v[0], v[-1]) in (('"', '"'), ("'", "'")):
        v = v[1:-1].strip()
    return v


def _slack_webhook_url() -> str:
    """SLACK_SIGNUP_WEBHOOK_URL for new signup notifications (optional). Accepts uppercase or lowercase key."""
    return _get_env("SLACK_SIGNUP_WEBHOOK_URL", "") or _get_env("slack_signup_webhook_url", "")


async def _handle_notify_signup_request(request: Request):
    """Handle POST /api/notify-signup-request (called from middleware so it's never shadowed by mount)."""
    webhook_url = _slack_webhook_url()
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
        "• Email: {}\n• Name: {}\n• Requested role: {}\n"
        "Please approve or reject in Settings → Admin → User management."
    ).format(email, full_name or "—", requested_role)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(webhook_url, json={"text": text})
            if r.status_code >= 400:
                return JSONResponse(status_code=502, content={"detail": "Slack webhook returned {}".format(r.status_code), "body": r.text[:500]})
    except Exception as e:
        return JSONResponse(status_code=502, content={"detail": "Slack request failed: {}".format(e)})
    return JSONResponse(status_code=200, content={"ok": True})


@app.get("/config.js")
def get_config_js():
    """
    Return JavaScript that sets Supabase credentials from environment variables.
    This must be loaded before the main app script runs.
    """
    supabase_url = _get_env("SUPABASE_URL")
    supabase_anon_key = _get_env("SUPABASE_ANON_KEY")
    qwen_api_url = _get_env("QWEN_API_URL")
    
    # Generate JavaScript that sets window variables
    js_content = f"""// Auto-generated config from environment variables
window.SUPABASE_URL = {repr(supabase_url)};
window.SUPABASE_ANON_KEY = {repr(supabase_anon_key)};
window.QWEN_API_URL = {repr(qwen_api_url)};  // Used when on localhost; on production, app uses same-origin /qwen-api
"""
    return Response(
        content=js_content,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


@app.get("/config-check")
def config_check():
    """
    Confirm whether Supabase env vars reach the server (no secrets returned).
    Helps debug "Invalid API key" when using Render env groups.
    """
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_ANON_KEY")
    return {
        "SUPABASE_URL_set": bool(url),
        "SUPABASE_URL_starts_with": url[:30] + "..." if len(url) > 30 else url,
        "SUPABASE_ANON_KEY_set": bool(key),
        "SUPABASE_ANON_KEY_length": len(key),
        "hint": "Use the anon PUBLIC key from Supabase (Settings → API), not the service_role key."
    }


@app.on_event("startup")
def startup():
    """Load the Fine-tuned model if MODEL_PATH is set and exists."""
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_ANON_KEY")
    print(f"Supabase config: SUPABASE_URL set={bool(url)}, SUPABASE_ANON_KEY set={bool(key)} (len={len(key)})")
    model_path = os.environ.get("MODEL_PATH", "./llm_training/mistral7b-speech-lora")
    base_model = os.environ.get("BASE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    load_8bit = os.environ.get("LOAD_IN_8BIT", "").lower() in ("1", "true", "yes")
    if Path(model_path).exists():
        try:
            serve_model.load_model_and_tokenizer(model_path, base_model, load_8bit)
            print("Model loaded.")
        except Exception as e:
            print("Model load failed:", e)
    else:
        print("MODEL_PATH not set or path missing; /api/evaluate* will return 503 until model is available.")


# Notify signup (root path so it's never shadowed by /api mount)
@app.get("/notify-signup-request")
async def notify_signup_get():
    return JSONResponse(status_code=200, content={"message": "Use POST with JSON: email, full_name, requested_role"})

@app.post("/notify-signup-request")
async def notify_signup_post(request: Request):
    return await _handle_notify_signup_request(request)


# LLM export status at root path so it's always reachable (not under /api mount)
@app.get("/llm-export-status")
def api_llm_export_status():
    """Confirm whether RENDER_LLM_EXPORT_SECRET is visible (no secret value revealed)."""
    secret = (os.environ.get("RENDER_LLM_EXPORT_SECRET") or "").strip()
    if not secret:
        secret = _read_llm_export_secret_from_env_file(_this_dir / ".env")
        if secret:
            os.environ["RENDER_LLM_EXPORT_SECRET"] = secret
    return {
        "secret_configured": bool(secret),
        "env_file_exists": (_this_dir / ".env").exists(),
        "env_file_path": str(_this_dir / ".env"),
    }


# API under /api (must be before static so /api/* is handled by the sub-app)
app.mount("/api", serve_model.app)


@app.get("/")
@app.get("/index.html")
def serve_index():
    """Serve index.html with no-cache so browser always gets latest (fixes stale UI after edits)."""
    path = _this_dir / "index.html"
    if not path.exists():
        return Response(status_code=404)
    return FileResponse(
        path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Other static files (assets, consent.html, etc.)
app.mount("/", StaticFiles(directory=str(_this_dir), html=True))
