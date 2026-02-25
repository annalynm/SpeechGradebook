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
from datetime import datetime, timedelta
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

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import base64

# Import the evaluation API app (model loaded on startup if MODEL_PATH exists)
try:
    from llm_training import serve_model
except ImportError as e:
    print(f"Warning: Could not import serve_model: {e}")
    print("API endpoints /api/evaluate* will not be available.")
    # Create a dummy serve_model object to prevent crashes
    class DummyServeModel:
        app = None
        @staticmethod
        def load_model_and_tokenizer(*args, **kwargs):
            pass
    serve_model = DummyServeModel()

# Initialize Sentry for error monitoring (optional, requires SENTRY_DSN env var)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    
    sentry_dsn = _get_env("SENTRY_DSN", "")
    sentry_environment = _get_env("SENTRY_ENVIRONMENT", "production")
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=sentry_environment,
            integrations=[
                FastApiIntegration(),
                AsyncioIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% of transactions for profiling
            send_default_pii=False,  # Don't send PII by default
        )
        print(f"Sentry initialized for environment: {sentry_environment}")
    else:
        print("Sentry DSN not set; error monitoring disabled")
except ImportError:
    print("sentry-sdk not installed; error monitoring disabled")
except Exception as e:
    print(f"Failed to initialize Sentry: {e}")

app = FastAPI(title="SpeechGradebook")

# Rate limiting setup
def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key: user ID from Supabase auth token if available, otherwise IP address.
    This allows 200 requests/hour per user (supports bulk uploads), with IP fallback for unauthenticated requests.
    """
    # Try to extract user ID from Authorization header (Supabase JWT)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        try:
            # Decode JWT payload (no verification needed for rate limiting key extraction)
            # JWT format: header.payload.signature
            parts = token.split(".")
            if len(parts) >= 2:
                # Decode payload (base64url)
                payload = parts[1]
                # Add padding if needed
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                import json
                claims = json.loads(decoded)
                user_id = claims.get("sub")  # Supabase uses "sub" for user ID
                if user_id:
                    return f"user:{user_id}"
        except Exception:
            # If token parsing fails, fall back to IP
            pass
    
    # Fallback to IP address
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
        return Response(status_code=503, content=json.dumps({"status": "error", "detail": "QWEN_API_URL not set on Render"}))
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base}/health")
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.TimeoutException:
        return Response(
            status_code=503,
            content=json.dumps({"status": "error", "detail": "Modal service timeout. The service may be starting up (cold start) or unavailable."})
        )
    except httpx.ConnectError as e:
        return Response(
            status_code=503,
            content=json.dumps({"status": "error", "detail": f"Cannot connect to Modal service at {base}. Check if the service is deployed and QWEN_API_URL is correct."})
        )
    except Exception as e:
        return Response(
            status_code=503,
            content=json.dumps({"status": "error", "detail": f"Qwen proxy error: {e!s}"})
        )


@qwen_router.post("/evaluate_video")
@limiter.limit("200/hour")  # Increased from 50/hour to support bulk uploads (e.g. 30-50 videos per class)
async def qwen_proxy_evaluate_video(request: Request, file: UploadFile = File(...), rubric: str = Form(...)):
    base = _qwen_base()
    if not base:
        return Response(status_code=503, content="QWEN_API_URL not set")
    try:
        body = await file.read()
        files = {"file": (file.filename or "video", body, file.content_type or "application/octet-stream")}
        data = {"rubric": rubric}
        # Match Modal timeout (600s) to avoid premature timeouts
        async with httpx.AsyncClient(timeout=600.0) as client:
            r = await client.post(f"{base}/evaluate_video", files=files, data=data)
            # Handle 503 responses with better error messages
            if r.status_code == 503:
                error_detail = "Service Unavailable"
                try:
                    error_json = r.json()
                    error_detail = error_json.get("detail", "Service Unavailable") if isinstance(error_json, dict) else str(error_json)
                except:
                    # If JSON parsing fails, try to get text
                    try:
                        error_text = r.text[:500]  # First 500 chars
                        if error_text:
                            error_detail = error_text
                    except:
                        pass
                
                # Log the actual error from Modal for debugging
                print(f"[ERROR] Modal returned 503: {error_detail}")
                print(f"[ERROR] Response headers: {dict(r.headers)}")
                print(f"[ERROR] This may indicate: cold start, service unavailable, or Modal infrastructure issue.")
                print(f"[ERROR] Check Modal logs at https://modal.com/apps for detailed error information.")
                
                if "model not loaded" in error_detail.lower():
                    return Response(
                        status_code=503,
                        content=json.dumps({"detail": "Qwen model is still loading (cold start). Please wait 30-90 seconds and try again."}),
                        media_type="application/json"
                    )
                else:
                    # Return the actual error detail from Modal
                    return Response(
                        status_code=503,
                        content=json.dumps({"detail": f"Modal service unavailable: {error_detail}"}),
                        media_type="application/json"
                    )
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.TimeoutException:
        return Response(
            status_code=503,
            content=json.dumps({"detail": "Modal service timeout. The evaluation may be taking longer than expected, or the service may be unavailable."})
        )
    except httpx.ConnectError as e:
        return Response(
            status_code=503,
            content=json.dumps({"detail": f"Cannot connect to Modal service at {base}. Check if the service is deployed: run 'modal deploy llm_training/qwen_modal.py' and verify QWEN_API_URL is correct."})
        )
    except Exception as e:
        return Response(status_code=503, content=json.dumps({"detail": f"Qwen proxy error: {e!s}"}))


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
                storage_url = form.get("storage_url")  # Alternative to file upload
                rubric_part = form.get("rubric") if path == "/qwen-api/evaluate_video" else None
                if path == "/qwen-api/evaluate_video":
                    # Set Sentry user context
                    _set_sentry_user_context(request)
                    
                    # Check user quota before proceeding
                    user_id, institution_id = _get_user_info_from_token(request)
                    if user_id:
                        quota_check = await _check_user_quota(user_id)
                        if not quota_check.get("bypass", False) and not quota_check.get("has_quota", False):
                            # No quota available
                            remaining = quota_check.get("remaining_quota", 0)
                            buffer_remaining = quota_check.get("buffer_remaining", 0)
                            error_msg = f"Quota exhausted. You have {remaining} evaluations remaining in your monthly quota"
                            if buffer_remaining > 0:
                                error_msg += f" and {buffer_remaining} in the shared buffer pool."
                            else:
                                error_msg += ". Please upgrade your plan or purchase additional evaluations."
                            return JSONResponse(
                                status_code=402,
                                content={"detail": error_msg, "quota_info": quota_check}
                            )
                    
                    # Rate limiting is now handled by the @limiter.limit() decorator on the endpoint
                    # No need to check here in middleware
                    
                    import time
                    start_time = time.time()
                    evaluation_start = time.time()
                    
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
                    
                    # Support both file upload and storage URL
                    if storage_url:
                        # Use storage URL (direct upload path - bypasses Render memory)
                        data = {"rubric": rubric_str, "storage_url": storage_url}
                        files = None
                        file_size_mb = 0  # Unknown when using URL
                    elif file_part and hasattr(file_part, "read"):
                        # Traditional file upload (fallback)
                        body = await file_part.read()
                        files = {"file": (getattr(file_part, "filename", None) or "video", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                        data = {"rubric": rubric_str}
                        file_size_mb = len(body) / (1024 * 1024)
                    else:
                        return JSONResponse(status_code=400, content={"detail": "Missing file or storage_url"})
                    
                    # Log evaluation start for cost tracking
                    if not storage_url:
                        print(f"[COST_TRACKING] Evaluation started - File size: {file_size_mb:.2f} MB, Timestamp: {time.time()}")
                    else:
                        print(f"[COST_TRACKING] Evaluation started - Using storage URL: {storage_url}, Timestamp: {time.time()}")
                    
                    # Match Modal timeout (600s) to avoid premature timeouts
                    async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
                        try:
                            if files:
                                # Traditional file upload
                                r = await client.post(f"{base}/evaluate_video", files=files, data=data)
                            else:
                                # Storage URL (Qwen API needs to support this)
                                r = await client.post(f"{base}/evaluate_video", json=data, headers={"Content-Type": "application/json"})
                        except httpx.TimeoutException as e:
                            elapsed_time = time.time() - start_time
                            error_msg = f"Qwen service timeout after {elapsed_time:.1f}s. The evaluation may be taking too long or the service may be unavailable."
                            print(f"[COST_TRACKING] Evaluation failed - Timeout: {elapsed_time:.2f}s")
                            print(f"[ERROR] {error_msg}")
                            return JSONResponse(status_code=504, content={"detail": error_msg})
                        except httpx.RequestError as e:
                            elapsed_time = time.time() - start_time
                            error_msg = f"Failed to connect to Qwen service: {str(e)}. Check QWEN_API_URL and ensure the Modal service is running."
                            print(f"[COST_TRACKING] Evaluation failed - Connection error: {elapsed_time:.2f}s")
                            print(f"[ERROR] {error_msg}")
                            return JSONResponse(status_code=503, content={"detail": error_msg})
                    
                    # Calculate and log cost metrics
                    elapsed_time = time.time() - start_time
                    # RunPod A100 GPU cost: ~$0.00011-0.00022/second (using average of $0.000165)
                    # Modal A100 GPU cost: ~$0.0011-0.0014/second (using average of $0.00125)
                    # Check provider from QWEN_API_URL to determine cost
                    base = _qwen_base()
                    if base and "modal" in base.lower():
                        estimated_cost = elapsed_time * 0.00125  # Modal pricing
                        provider = "modal"
                    else:
                        estimated_cost = elapsed_time * 0.000165  # RunPod pricing
                        provider = "runpod"
                    
                    print(f"[COST_TRACKING] Evaluation completed - Duration: {elapsed_time:.2f}s, Estimated cost: ${estimated_cost:.4f}, Provider: {provider}, Status: {r.status_code}")
                    
                    # Log cost to database and increment usage if evaluation was successful
                    if r.status_code == 200:
                        user_id, institution_id = _get_user_info_from_token(request)
                        # Note: evaluation_id will be None here since it's created in frontend after save
                        # Frontend can update cost_tracking record later with evaluation_id if needed
                        await _log_cost_to_database(
                            user_id=user_id,
                            institution_id=institution_id,
                            evaluation_id=None,  # Will be set when evaluation is saved in frontend
                            gpu_seconds=elapsed_time,
                            estimated_cost=estimated_cost,
                            provider=provider,
                            model_name="qwen",
                            file_size_mb=file_size_mb,
                            processing_time_seconds=elapsed_time
                        )
                        # Increment usage quota
                        if user_id:
                            await _increment_usage(user_id, None, estimated_cost, provider)
                    
                    if 300 <= r.status_code < 400:
                        return JSONResponse(status_code=502, content={"detail": "Qwen service returned redirect (3xx). Check QWEN_API_URL—use https, no trailing slash. Ensure the Qwen tunnel/URL is correct."})
                    
                    # If 503 error, check if it's a model loading issue
                    if r.status_code == 503:
                        error_detail = "Service Unavailable"
                        try:
                            error_json = r.json()
                            if isinstance(error_json, dict) and "detail" in error_json:
                                error_detail = error_json["detail"]
                            elif isinstance(error_json, dict) and "error" in error_json:
                                error_detail = error_json["error"]
                        except:
                            try:
                                error_text = r.text[:500]
                                if error_text:
                                    error_detail = error_text
                            except:
                                pass
                        
                        # Check if it's a model loading issue
                        if "model not loaded" in error_detail.lower() or "model_not_loaded" in error_detail.lower():
                            print(f"[ERROR] Qwen model not loaded. Service may be cold starting. Wait 30-90 seconds and retry.")
                            return JSONResponse(
                                status_code=503, 
                                content={"detail": "Qwen model is still loading (cold start). Please wait 30-90 seconds and try again. The service is starting up."}
                            )
                        
                        print(f"[ERROR] Qwen service returned 503: {error_detail}")
                        return JSONResponse(
                            status_code=503, 
                            content={"detail": f"Qwen service temporarily unavailable: {error_detail}. The service may be starting up or experiencing issues. Please try again in a few moments."}
                        )
                    
                    # If 500 error, try to extract more details from response
                    if r.status_code == 500:
                        error_detail = "Internal Server Error"
                        try:
                            error_json = r.json()
                            if isinstance(error_json, dict) and "detail" in error_json:
                                error_detail = error_json["detail"]
                            elif isinstance(error_json, dict) and "error" in error_json:
                                error_detail = error_json["error"]
                        except:
                            # If JSON parsing fails, try to get text
                            try:
                                error_text = r.text[:500]  # First 500 chars
                                if error_text:
                                    error_detail = error_text
                            except:
                                pass
                        
                        print(f"[ERROR] Qwen service returned 500: {error_detail}")
                        print(f"[ERROR] This may indicate: OOM (Out of Memory) error, model loading issue, or video processing failure.")
                        print(f"[ERROR] Check Modal logs at https://modal.com/apps for detailed error information.")
                        
                        # Log to Sentry
                        try:
                            import sentry_sdk
                            sentry_sdk.capture_message(
                                f"Qwen evaluation failed: {error_detail}",
                                level="error",
                                contexts={
                                    "evaluation": {
                                        "file_size_mb": file_size_mb,
                                        "elapsed_time": elapsed_time,
                                        "status_code": 500
                                    }
                                }
                            )
                        except Exception:
                            pass
                        
                        # Provide more helpful error message
                        if "OOM" in error_detail or "out of memory" in error_detail.lower() or "CUDA" in error_detail:
                            error_detail = f"Out of Memory error: {error_detail}. T4 GPU may not have enough memory for this video. Consider using a smaller video or switching to A100 GPU."
                        elif "model" in error_detail.lower() and ("not loaded" in error_detail.lower() or "load" in error_detail.lower()):
                            error_detail = f"Model loading error: {error_detail}. The Qwen model may not have loaded correctly on Modal. Check Modal deployment logs."
                        
                        return JSONResponse(status_code=500, content={"detail": f"Qwen evaluation failed: {error_detail}"})
                    
                    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
                if path == "/qwen-api/analyze_video" and file_part and hasattr(file_part, "read"):
                    start_time = time.time()
                    body = await file_part.read()
                    files = {"file": (getattr(file_part, "filename", None) or "video", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        r = await client.post(f"{base}/analyze_video", files=files)
                    elapsed_time = time.time() - start_time
                    estimated_cost = elapsed_time * 0.000222
                    print(f"[COST_TRACKING] Video analysis - Duration: {elapsed_time:.2f}s, Estimated cost: ${estimated_cost:.4f}, Status: {r.status_code}")
                    
                    # Log cost to database if successful
                    if r.status_code == 200:
                        user_id, institution_id = _get_user_info_from_token(request)
                        await _log_cost_to_database(
                            user_id=user_id,
                            institution_id=institution_id,
                            gpu_seconds=elapsed_time,
                            estimated_cost=estimated_cost,
                            provider="modal",
                            model_name="qwen",
                            file_size_mb=len(body) / (1024 * 1024) if body else None,
                            processing_time_seconds=elapsed_time
                        )
                    
                    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
                if path == "/qwen-api/extract_rubric" and file_part and hasattr(file_part, "read"):
                    start_time = time.time()
                    body = await file_part.read()
                    files = {"file": (getattr(file_part, "filename", None) or "rubric", body, getattr(file_part, "content_type", None) or "application/octet-stream")}
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        r = await client.post(f"{base}/extract_rubric", files=files)
                    elapsed_time = time.time() - start_time
                    estimated_cost = elapsed_time * 0.000222
                    print(f"[COST_TRACKING] Rubric extraction - Duration: {elapsed_time:.2f}s, Estimated cost: ${estimated_cost:.4f}, Status: {r.status_code}")
                    
                    # Log cost to database if successful
                    if r.status_code == 200:
                        user_id, institution_id = _get_user_info_from_token(request)
                        await _log_cost_to_database(
                            user_id=user_id,
                            institution_id=institution_id,
                            gpu_seconds=elapsed_time,
                            estimated_cost=estimated_cost,
                            provider="modal",
                            model_name="qwen",
                            file_size_mb=len(body) / (1024 * 1024) if body else None,
                            processing_time_seconds=elapsed_time
                        )
                    
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


# Helper to set Sentry user context from request
def _set_sentry_user_context(request: Request):
    """Extract user ID from auth token and set Sentry user context."""
    try:
        import sentry_sdk
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += "=" * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    import json
                    claims = json.loads(decoded)
                    user_id = claims.get("sub")
                    if user_id:
                        sentry_sdk.set_user({"id": user_id})
            except Exception:
                pass
    except Exception:
        pass


# Helper to extract user info from auth token
def _get_user_info_from_token(request: Request):
    """Extract user_id and institution_id from Supabase JWT token."""
    user_id = None
    institution_id = None
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            parts = token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                import json
                claims = json.loads(decoded)
                user_id = claims.get("sub")
                # Note: institution_id is not in JWT, would need to query user_profiles
                # For now, we'll insert cost record and let it be NULL, or query it
        except Exception:
            pass
    
    return user_id, institution_id


# Helper to check user quota before evaluation
async def _check_user_quota(user_id: str) -> dict:
    """Check if user has available quota. Returns dict with has_quota, quota_type, remaining_quota, etc."""
    if not user_id:
        return {"has_quota": False, "error": "User not authenticated"}
    
    try:
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            print("[QUOTA_CHECK] Cannot check quota: SUPABASE_SERVICE_ROLE_KEY not set")
            return {"has_quota": True, "bypass": True}  # Bypass if not configured
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # Call the check_user_quota function
        result = supabase_client.rpc("check_user_quota", {"p_user_id": user_id}).execute()
        
        if result.data and len(result.data) > 0:
            quota_info = result.data[0]
            return {
                "has_quota": quota_info.get("has_quota", False),
                "quota_type": quota_info.get("quota_type", "none"),
                "remaining_quota": quota_info.get("remaining_quota", 0),
                "can_use_buffer": quota_info.get("can_use_buffer", False),
                "buffer_remaining": quota_info.get("buffer_remaining", 0)
            }
        else:
            return {"has_quota": False, "error": "No quota found"}
            
    except ImportError:
        print("[QUOTA_CHECK] Cannot check quota: supabase package not installed")
        return {"has_quota": True, "bypass": True}  # Bypass if package not available
    except Exception as e:
        print(f"[QUOTA_CHECK] Failed to check quota: {e}")
        return {"has_quota": True, "bypass": True}  # Bypass on error to avoid blocking


# Helper to increment usage after evaluation
async def _increment_usage(user_id: str, evaluation_id: str = None, cost: float = 0, provider: str = "runpod"):
    """Increment usage counter after successful evaluation."""
    if not user_id:
        return
    
    try:
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            print("[USAGE_TRACKING] Cannot increment usage: SUPABASE_SERVICE_ROLE_KEY not set")
            return
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # Call the increment_usage function
        result = supabase_client.rpc("increment_usage", {
            "p_user_id": user_id,
            "p_evaluation_id": evaluation_id,
            "p_cost": cost,
            "p_provider": provider
        }).execute()
        
        if result.data:
            print(f"[USAGE_TRACKING] Usage incremented for user {user_id}")
        else:
            print(f"[USAGE_TRACKING] Failed to increment usage (no quota available)")
            
    except ImportError:
        print("[USAGE_TRACKING] Cannot increment usage: supabase package not installed")
    except Exception as e:
        print(f"[USAGE_TRACKING] Failed to increment usage: {e}")


# Helper to log cost to database
async def _log_cost_to_database(
    user_id: str = None,
    institution_id: str = None,
    evaluation_id: str = None,
    gpu_seconds: float = 0,
    estimated_cost: float = 0,
    provider: str = "modal",
    model_name: str = None,
    file_size_mb: float = None,
    processing_time_seconds: float = None
):
    """Log evaluation cost to cost_tracking table."""
    try:
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            print("[COST_TRACKING] Cannot log to database: SUPABASE_SERVICE_ROLE_KEY not set")
            return
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # If we have user_id but not institution_id, try to get it from user_profiles
        if user_id and not institution_id:
            try:
                profile = supabase_client.table("user_profiles").select("institution_id").eq("id", user_id).limit(1).execute()
                if profile.data and len(profile.data) > 0:
                    institution_id = profile.data[0].get("institution_id")
            except Exception:
                pass
        
        # Insert cost record
        cost_record = {
            "instructor_id": user_id,
            "institution_id": institution_id,
            "evaluation_id": evaluation_id,
            "gpu_seconds": float(gpu_seconds),
            "estimated_cost": float(estimated_cost),
            "provider": provider,
            "model_name": model_name,
            "file_size_mb": float(file_size_mb) if file_size_mb else None,
            "processing_time_seconds": float(processing_time_seconds) if processing_time_seconds else None
        }
        
        # Remove None values
        cost_record = {k: v for k, v in cost_record.items() if v is not None}
        
        result = supabase_client.table("cost_tracking").insert(cost_record).execute()
        print(f"[COST_TRACKING] Logged to database: {estimated_cost:.4f} USD")
        
    except ImportError:
        print("[COST_TRACKING] Cannot log to database: supabase package not installed")
    except Exception as e:
        print(f"[COST_TRACKING] Failed to log to database: {e}")
        # Don't fail the request if cost logging fails


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
        "hint": "Use the anon PUBLIC key from Supabase (Settings → API), not the service_role key.",
        "files_check": {
            "index.html": (_this_dir / "index.html").exists(),
            "landing.html": (_this_dir / "landing.html").exists(),
            "config.js": (_this_dir / "config.js").exists(),
            "assets": (_this_dir / "assets").exists(),
            "working_dir": str(_this_dir)
        }
    }

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "app": "SpeechGradebook",
        "files": {
            "index.html": (_this_dir / "index.html").exists(),
            "landing.html": (_this_dir / "landing.html").exists(),
        }
    }


@app.on_event("startup")
def startup():
    """Load the Fine-tuned model if MODEL_PATH is set and exists."""
    try:
        url = _get_env("SUPABASE_URL")
        key = _get_env("SUPABASE_ANON_KEY")
        print(f"Supabase config: SUPABASE_URL set={bool(url)}, SUPABASE_ANON_KEY set={bool(key)} (len={len(key)})")
        
        # Verify critical files exist
        print(f"Working directory: {_this_dir}")
        print(f"index.html exists: {(_this_dir / 'index.html').exists()}")
        print(f"landing.html exists: {(_this_dir / 'landing.html').exists()}")
        print(f"config.js exists: {(_this_dir / 'config.js').exists()}")
        print(f"assets directory exists: {(_this_dir / 'assets').exists()}")
        
        model_path = os.environ.get("MODEL_PATH", "./llm_training/mistral7b-speech-lora")
        base_model = os.environ.get("BASE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        load_8bit = os.environ.get("LOAD_IN_8BIT", "").lower() in ("1", "true", "yes")
        if Path(model_path).exists():
            try:
                serve_model.load_model_and_tokenizer(model_path, base_model, load_8bit)
                print("Model loaded.")
            except Exception as e:
                print(f"Model load failed: {e}")
        else:
            print("MODEL_PATH not set or path missing; /api/evaluate* will return 503 until model is available.")
    except Exception as e:
        print(f"Startup error: {e}")
        import traceback
        traceback.print_exc()


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
if serve_model.app is not None:
    app.mount("/api", serve_model.app)
else:
    # Fallback if serve_model is not available
    @app.get("/api/health")
    def api_health_fallback():
        return {"status": "error", "detail": "API module not available"}


# Direct video upload endpoints (presigned URLs for Supabase Storage)
@app.post("/api/generate-upload-url")
async def generate_upload_url(request: Request):
    """
    Generate a presigned URL for direct video upload to Supabase Storage.
    This bypasses Render's memory constraints by uploading directly from browser to Supabase.
    
    Requires:
    - Authorization header with Supabase JWT token
    - JSON body with: filename, content_type (optional), file_size (optional)
    
    Returns:
    - upload_url: Presigned PUT URL for direct upload
    - file_path: Path where file will be stored
    - expires_at: When the URL expires
    """
    try:
        # Extract user ID from auth token for file path
        auth_header = request.headers.get("Authorization", "")
        user_id = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += "=" * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    import json
                    claims = json.loads(decoded)
                    user_id = claims.get("sub")
            except Exception:
                pass
        
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Please provide a valid Supabase JWT token."}
            )
        
        # Get request body
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})
        
        filename = body.get("filename", "video.mp4")
        content_type = body.get("content_type", "video/mp4")
        file_size = body.get("file_size")  # Optional, for validation
        
        # Generate unique file path: {user_id}/{timestamp}_{filename}
        import uuid
        timestamp = int(time.time())
        file_id = str(uuid.uuid4())[:8]
        file_path = f"{user_id}/{timestamp}_{file_id}_{filename}"
        
        # Create Supabase client with service role key for presigned URL generation
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            return JSONResponse(
                status_code=503,
                content={"detail": "Supabase configuration missing. SUPABASE_SERVICE_ROLE_KEY required for presigned URLs."}
            )
        
        try:
            from supabase import create_client
            supabase_client = create_client(supabase_url, supabase_service_key)
            
            bucket_name = "evaluation-media"
            expires_in = 900  # 15 minutes in seconds
            
            # Supabase Storage doesn't use traditional presigned URLs like S3.
            # Instead, we return the file path and the frontend uses Supabase JS client
            # to upload directly. The JS client handles authentication automatically.
            
            # Return file path for frontend to use with Supabase JS client
            return JSONResponse(
                status_code=200,
                content={
                    "file_path": file_path,
                    "bucket": bucket_name,
                    "expires_in": expires_in,
                    "upload_instructions": "Use Supabase JS client: supabase.storage.from(bucket).upload(path, file)"
                }
            )
        except ImportError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Supabase Python client not installed. Add 'supabase>=2.0.0' to requirements.txt"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to generate upload URL: {str(e)}"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error generating upload URL: {str(e)}"}
        )


# Subscription Management API Endpoints
@app.post("/api/subscriptions/create")
async def create_subscription(request: Request):
    """
    Create a new subscription for a user.
    Requires: tier (student_free, student_paid, individual_basic, individual_standard, individual_professional, department)
    """
    try:
        user_id, institution_id = _get_user_info_from_token(request)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        
        body = await request.json()
        tier = body.get("tier")
        contract_type = body.get("contract_type", "individual")  # 'individual' or 'department'
        pilot_status = body.get("pilot_status", False)
        
        if not tier or tier not in ['student_free', 'student_paid', 'individual_basic', 'individual_standard', 'individual_professional', 'department']:
            return JSONResponse(status_code=400, content={"detail": "Invalid tier"})
        
        # Pricing and quota from plan
        tier_config = {
            'student_free': {'quota': 3, 'price': 0},
            'student_paid': {'quota': 10, 'price': 5},
            'individual_basic': {'quota': 25, 'price': 15},
            'individual_standard': {'quota': 50, 'price': 25},
            'individual_professional': {'quota': 100, 'price': 40},
            'department': {'quota': 1500, 'buffer_quota': 500, 'price': 600}
        }
        
        config = tier_config.get(tier, {})
        
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            return JSONResponse(status_code=503, content={"detail": "Supabase configuration missing"})
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # Create subscription
        subscription_data = {
            "user_id": user_id,
            "institution_id": institution_id if contract_type == 'department' else None,
            "tier": tier,
            "status": "active",
            "contract_type": contract_type,
            "pilot_status": pilot_status,
            "amount_per_period": config.get('price', 0),
            "billing_period": "monthly"
        }
        
        subscription_result = supabase_client.table("subscriptions").insert(subscription_data).execute()
        
        if not subscription_result.data:
            return JSONResponse(status_code=500, content={"detail": "Failed to create subscription"})
        
        subscription_id = subscription_result.data[0]['id']
        
        # Create or update usage quota
        quota_data = {
            "user_id": user_id if contract_type == 'individual' else None,
            "institution_id": institution_id if contract_type == 'department' else None,
            "account_type": tier,
            "monthly_quota": config.get('quota', 0),
            "buffer_quota": config.get('buffer_quota', 0),
            "pilot_discount": pilot_status,
            "is_active": True,
            "renewal_date": (datetime.utcnow() + timedelta(days=30)).date() if tier != 'student_free' else None
        }
        
        # Check if quota already exists
        existing_quota = supabase_client.table("usage_quotas").select("*")
        if contract_type == 'department' and institution_id:
            existing_quota = existing_quota.eq("institution_id", institution_id).eq("account_type", tier)
        else:
            existing_quota = existing_quota.eq("user_id", user_id)
        existing_quota = existing_quota.execute()
        
        if existing_quota.data and len(existing_quota.data) > 0:
            # Update existing quota
            quota_result = supabase_client.table("usage_quotas").update(quota_data).eq("id", existing_quota.data[0]['id']).execute()
        else:
            # Create new quota
            quota_result = supabase_client.table("usage_quotas").insert(quota_data).execute()
        
        return JSONResponse(status_code=200, content={
            "subscription": subscription_result.data[0],
            "quota": quota_result.data[0] if quota_result.data else None
        })
        
    except Exception as e:
        print(f"[SUBSCRIPTION] Error creating subscription: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error creating subscription: {str(e)}"})


@app.post("/api/subscriptions/upgrade")
async def upgrade_subscription(request: Request):
    """
    Upgrade an existing subscription to a higher tier.
    """
    try:
        user_id, institution_id = _get_user_info_from_token(request)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        
        body = await request.json()
        new_tier = body.get("tier")
        
        if not new_tier:
            return JSONResponse(status_code=400, content={"detail": "Missing tier"})
        
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            return JSONResponse(status_code=503, content={"detail": "Supabase configuration missing"})
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # Get current subscription
        current_sub = supabase_client.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").limit(1).execute()
        
        if not current_sub.data or len(current_sub.data) == 0:
            return JSONResponse(status_code=404, content={"detail": "No active subscription found"})
        
        # Update subscription and quota (similar to create_subscription)
        # For now, return a message that payment integration is needed
        return JSONResponse(status_code=200, content={
            "message": "Upgrade functionality requires payment integration. Please contact support.",
            "current_tier": current_sub.data[0]['tier'],
            "requested_tier": new_tier
        })
        
    except Exception as e:
        print(f"[SUBSCRIPTION] Error upgrading subscription: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error upgrading subscription: {str(e)}"})


@app.get("/api/subscriptions/current")
async def get_current_subscription(request: Request):
    """
    Get the current subscription and quota for the authenticated user.
    """
    try:
        user_id, institution_id = _get_user_info_from_token(request)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        
        supabase_url = _get_env("SUPABASE_URL")
        supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            return JSONResponse(status_code=503, content={"detail": "Supabase configuration missing"})
        
        from supabase import create_client
        supabase_client = create_client(supabase_url, supabase_service_key)
        
        # Get subscription
        subscription = supabase_client.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").limit(1).execute()
        
        # Get quota
        quota = supabase_client.table("usage_quotas").select("*").eq("user_id", user_id).eq("is_active", True).limit(1).execute()
        
        return JSONResponse(status_code=200, content={
            "subscription": subscription.data[0] if subscription.data and len(subscription.data) > 0 else None,
            "quota": quota.data[0] if quota.data and len(quota.data) > 0 else None
        })
        
    except Exception as e:
        print(f"[SUBSCRIPTION] Error getting subscription: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error getting subscription: {str(e)}"})


# Stripe Webhook Endpoints (for payment processing)
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for subscription management.
    Requires: STRIPE_WEBHOOK_SECRET environment variable
    """
    try:
        stripe_webhook_secret = _get_env("STRIPE_WEBHOOK_SECRET", "")
        if not stripe_webhook_secret:
            return JSONResponse(status_code=503, content={"detail": "Stripe webhook secret not configured"})
        
        # Get the raw body for signature verification
        body = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        # TODO: Verify webhook signature using Stripe SDK
        # import stripe
        # stripe.api_key = _get_env("STRIPE_SECRET_KEY", "")
        # event = stripe.Webhook.construct_event(body, sig_header, stripe_webhook_secret)
        
        # For now, return a placeholder response
        return JSONResponse(status_code=200, content={"received": True, "message": "Stripe webhook endpoint ready (integration pending)"})
        
    except Exception as e:
        print(f"[STRIPE] Webhook error: {e}")
        return JSONResponse(status_code=400, content={"detail": f"Webhook error: {str(e)}"})


@app.post("/api/stripe/create-checkout-session")
async def create_stripe_checkout_session(request: Request):
    """
    Create a Stripe Checkout session for subscription purchase.
    Requires: STRIPE_SECRET_KEY environment variable
    """
    try:
        user_id, institution_id = _get_user_info_from_token(request)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        
        body = await request.json()
        tier = body.get("tier")
        contract_type = body.get("contract_type", "individual")
        
        if not tier:
            return JSONResponse(status_code=400, content={"detail": "Missing tier"})
        
        stripe_secret_key = _get_env("STRIPE_SECRET_KEY", "")
        if not stripe_secret_key:
            return JSONResponse(status_code=503, content={"detail": "Stripe not configured. Please contact support to set up payment."})
        
        # Pricing from plan
        tier_pricing = {
            'student_paid': 5,
            'individual_basic': 15,
            'individual_standard': 25,
            'individual_professional': 40,
            'department': 600
        }
        
        price = tier_pricing.get(tier)
        if price is None:
            return JSONResponse(status_code=400, content={"detail": "Invalid tier"})
        
        # TODO: Create Stripe Checkout Session
        # import stripe
        # stripe.api_key = stripe_secret_key
        # session = stripe.checkout.Session.create(
        #     customer_email=user_email,  # Get from user profile
        #     payment_method_types=['card'],
        #     line_items=[{
        #         'price_data': {
        #             'currency': 'usd',
        #             'product_data': {'name': f'SpeechGradebook {tier}'},
        #             'unit_amount': price * 100,  # Stripe uses cents
        #             'recurring': {'interval': 'month'}
        #         },
        #         'quantity': 1,
        #     }],
        #     mode='subscription',
        #     success_url=f'{request.base_url}/settings?success=true',
        #     cancel_url=f'{request.base_url}/settings?canceled=true',
        #     metadata={'user_id': user_id, 'tier': tier, 'contract_type': contract_type}
        # )
        # return JSONResponse(status_code=200, content={"checkout_url": session.url})
        
        # Placeholder response
        return JSONResponse(status_code=200, content={
            "message": "Stripe checkout integration pending. Please contact support to set up payment.",
            "tier": tier,
            "price": price
        })
        
    except Exception as e:
        print(f"[STRIPE] Checkout error: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error creating checkout session: {str(e)}"})


@app.post("/api/confirm-upload")
async def confirm_upload(request: Request):
    """
    Confirm that a file was successfully uploaded to Supabase Storage.
    Returns the public URL for the uploaded file.
    
    Requires:
    - Authorization header with Supabase JWT token
    - JSON body with: file_path (path returned from generate-upload-url)
    
    Returns:
    - storage_url: Public URL to access the uploaded file
    - file_path: Confirmed file path
    """
    try:
        # Extract user ID from auth token
        auth_header = request.headers.get("Authorization", "")
        user_id = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += "=" * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    import json
                    claims = json.loads(decoded)
                    user_id = claims.get("sub")
            except Exception:
                pass
        
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required."}
            )
        
        # Get request body
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})
        
        file_path = body.get("file_path")
        if not file_path:
            return JSONResponse(status_code=400, content={"detail": "Missing file_path"})
        
        # Verify file path belongs to this user (security check)
        if not file_path.startswith(f"{user_id}/"):
            return JSONResponse(
                status_code=403,
                content={"detail": "File path does not belong to authenticated user"}
            )
        
        # Construct public URL
        supabase_url = _get_env("SUPABASE_URL").rstrip("/")
        bucket_name = "evaluation-media"
        storage_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
        
        return JSONResponse(
            status_code=200,
            content={
                "storage_url": storage_url,
                "file_path": file_path,
                "bucket": bucket_name
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error confirming upload: {str(e)}"}
        )


@app.get("/")
def serve_root():
    """Serve landing.html for new users finding SpeechGradebook via search."""
    path = _this_dir / "landing.html"
    if not path.exists():
        # Fallback to index.html if landing.html doesn't exist
        path = _this_dir / "index.html"
        if not path.exists():
            return Response(
                status_code=500,
                content=f"Error: Neither landing.html nor index.html found in {_this_dir}",
                media_type="text/plain"
            )
    return FileResponse(
        path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/login")
def serve_login():
    """Serve index.html (login page) for returning users."""
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

@app.get("/app")
@app.get("/index.html")
def serve_index():
    """Serve index.html (app) for authenticated users."""
    path = _this_dir / "index.html"
    if not path.exists():
        return Response(
            status_code=500,
            content=f"Error: index.html not found in {_this_dir}",
            media_type="text/plain"
        )
    return FileResponse(
        path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Explicit routes for common SPA paths (these will be matched before the catch-all)
@app.get("/dashboard")
def serve_dashboard():
    """Serve index.html for dashboard route."""
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

@app.get("/evaluate")
@app.get("/settings")
@app.get("/help")
@app.get("/analytics")
def serve_spa_page():
    """Serve index.html for common SPA routes."""
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


@app.get("/landing")
@app.get("/learn-more")
@app.get("/landing.html")
def serve_landing():
    """Serve landing.html for new users to learn about the product."""
    path = _this_dir / "landing.html"
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


@app.get("/contact")
@app.get("/contact.html")
def serve_contact():
    """Serve contact.html for contact form."""
    path = _this_dir / "contact.html"
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


@app.get("/accessibility")
@app.get("/accessibility.html")
def serve_accessibility():
    """Serve accessibility.html for accessibility statement."""
    path = _this_dir / "accessibility.html"
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


@app.get("/help")
@app.get("/help.html")
def serve_help():
    """Serve help.html for help center documentation."""
    path = _this_dir / "help.html"
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


@app.post("/api/contact")
@limiter.limit("10/hour")  # Rate limit contact form submissions
async def handle_contact(request: Request):
    """Handle contact form submissions and send email to speechgradebook@proton.me"""
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        email = (body.get("email") or "").strip()
        subject_type = (body.get("subject") or "").strip()
        message = (body.get("message") or "").strip()

        # Validate required fields
        if not name or not email or not subject_type or not message:
            return JSONResponse(
                status_code=400,
                content={"detail": "All fields are required"}
            )

        # Validate email format
        if "@" not in email or "." not in email.split("@")[1]:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid email address"}
            )

        # Subject mapping
        subject_map = {
            "sales": "Sales Inquiry",
            "support": "Support Request",
            "general": "General Question",
            "enterprise": "Enterprise Inquiry",
            "other": "Other"
        }
        subject_label = subject_map.get(subject_type, "Contact Form Submission")

        # Format email content
        email_subject = f"SpeechGradebook Contact: {subject_label}"
        email_body = f"""New contact form submission from SpeechGradebook website:

Name: {name}
Email: {email}
Subject: {subject_label}
Message:
{message}

---
This message was sent from the SpeechGradebook contact form.
"""

        # Try to send email using SMTP if configured
        email_sent = False
        smtp_host = _get_env("SMTP_HOST", "")
        smtp_port = _get_env("SMTP_PORT", "587")
        smtp_user = _get_env("SMTP_USER", "")
        smtp_password = _get_env("SMTP_PASSWORD", "")
        smtp_from = _get_env("SMTP_FROM", smtp_user or "noreply@speechgradebook.com")
        recipient_email = "speechgradebook@proton.me"

        if smtp_host and smtp_user and smtp_password:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                msg = MIMEMultipart()
                msg["From"] = smtp_from
                msg["To"] = recipient_email
                msg["Subject"] = email_subject
                msg["Reply-To"] = email  # Set reply-to to the sender's email

                msg.attach(MIMEText(email_body, "plain"))

                # Try TLS first, fall back to SSL
                try:
                    server = smtplib.SMTP(smtp_host, int(smtp_port))
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                    server.quit()
                    email_sent = True
                except Exception:
                    # Try SSL if TLS fails
                    server = smtplib.SMTP_SSL(smtp_host, int(smtp_port))
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                    server.quit()
                    email_sent = True

            except Exception as e:
                # Log error but don't fail the request
                print(f"[ERROR] Failed to send contact email via SMTP: {e}")
                email_sent = False

        # If SMTP not configured or failed, log the message
        if not email_sent:
            print(f"\n{'='*60}")
            print(f"CONTACT FORM SUBMISSION (Email not configured)")
            print(f"{'='*60}")
            print(f"To: {recipient_email}")
            print(f"Subject: {email_subject}")
            print(f"\n{email_body}")
            print(f"{'='*60}\n")
            # Still return success so the form works, but log a warning
            print("[WARNING] SMTP not configured. Contact form submission logged above.")
            print("[INFO] To enable email sending, set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD environment variables.")

        return JSONResponse(
            status_code=200,
            content={"message": "Your message has been sent successfully. We'll get back to you soon!"}
        )

    except Exception as e:
        print(f"[ERROR] Contact form error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An error occurred while processing your request. Please try again later."}
        )


# Catch-all route for client-side routing (must be after all API routes)
# This allows paths like /courses/123 to serve index.html for client-side routing
# Note: FastAPI will match explicit routes (like @app.get("/")) before this catch-all
@app.get("/{full_path:path}")
def serve_spa_routes(full_path: str):
    """
    Serve index.html for all routes to support client-side routing.
    First checks if the requested path is an actual file, if so serves it.
    Otherwise serves index.html for SPA routing.
    """
    # Don't handle API routes
    if (full_path.startswith("api/") or 
        full_path.startswith("qwen-api/")):
        return Response(status_code=404)
    
    # Normalize the path (remove leading slash if present)
    normalized_path = full_path.lstrip("/")
    
    # Skip empty paths (should be handled by explicit "/" route which serves landing.html)
    if not normalized_path:
        landing_path = _this_dir / "landing.html"
        if not landing_path.exists():
            return Response(status_code=404)
        return FileResponse(
            landing_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    
    # Check if the requested path is an actual file that exists
    file_path = _this_dir / normalized_path
    if file_path.exists() and file_path.is_file():
        # Serve the actual file
        return FileResponse(file_path)
    
    # Don't handle files with extensions (they should have been caught above)
    # But allow .html files to be served
    last_segment = normalized_path.split("/")[-1]
    if "." in last_segment and not last_segment.endswith(".html"):
        return Response(status_code=404)
    
    # Serve index.html for all other routes (client-side routing)
    index_path = _this_dir / "index.html"
    if not index_path.exists():
        return Response(status_code=404)
    return FileResponse(
        index_path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Static files (assets, etc.) - mounted after catch-all for specific paths
app.mount("/assets", StaticFiles(directory=str(_this_dir / "assets"), html=False))
