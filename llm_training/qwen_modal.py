"""
Deploy Qwen2.5-VL evaluation service on Modal (pay-per-use GPU).

Usage (from repo root):
  modal deploy llm_training/qwen_modal.py       # Deploy → permanent URL
  modal serve llm_training/qwen_modal.py        # Dev mode → temporary URL

After deploy, set QWEN_API_URL on Render to the Modal URL (e.g. https://annalynm--qwen-speechgradebook.modal.run).

Textbook RAG: Disabled on Modal by default (DISABLE_TEXTBOOK_RAG=1) to avoid OOM.
To enable: remove DISABLE_TEXTBOOK_RAG from .env() above, create secret, then deploy.
"""

from pathlib import Path

import modal

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent

# Image: Python deps + your code (add_local_dir last per Modal best practice)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0",
        "torchvision>=0.15",
        "transformers>=4.50",
        "accelerate>=0.25",
        "bitsandbytes>=0.41",  # 8-bit model loading to avoid CUDA OOM on A10G
        "fastapi>=0.100",
        "uvicorn[standard]>=0.22",
        "python-multipart>=0.0.6",
        "pillow>=10.0",
        "pymupdf>=1.23",
        "av",  # PyAV – required by torchvision for video decode in Qwen2.5-VL
        # Textbook RAG (when rubric has textbook_id)
        "sentence-transformers>=2.2",
        "psycopg2-binary>=2.9",
    )
    .env({
        "PYTHONPATH": "/app",
        "ALLOWED_ORIGINS": "https://speechgradebook.onrender.com,https://www.speechgradebook.com,http://localhost:8000,http://127.0.0.1:8000",
        "PYTORCH_ALLOC_CONF": "expandable_segments:True",
        # Disable textbook RAG on Modal to avoid OOM (sentence-transformers + Qwen + video can exceed memory)
        "DISABLE_TEXTBOOK_RAG": "1",
    })
    .add_local_dir(_this_dir, remote_path="/app/llm_training")
)

app = modal.App("qwen-speechgradebook", image=image)


@app.cls(
    # Using T4 GPU for cost efficiency (~$0.01-0.03 per evaluation vs ~$0.60 with A100)
    # T4 has 16GB VRAM; 4-bit quantization (load_in_4bit=True) helps fit the model
    # If you encounter OOM errors with large videos, consider switching back to A100
    gpu="T4",  # Cost-effective option: ~$0.80/hour vs ~$4-5/hour for A100
    container_idle_timeout=300,
    timeout=600,
    allow_concurrent_inputs=1,
    # secrets=[modal.Secret.from_name("supabase-db")],  # Uncomment to enable textbook RAG; create secret first
)
class QwenService:
    """Load Qwen2.5-VL on GPU and serve the FastAPI app."""

    @modal.enter()
    def load_model(self):
        import sys
        sys.path.insert(0, "/app")
        from llm_training import qwen_serve
        self.qwen_serve = qwen_serve
        qwen_serve._load_model("Qwen/Qwen2.5-VL-7B-Instruct", load_in_4bit=True)

    @modal.asgi_app(label="qwen-speechgradebook")
    def web(self):
        return self.qwen_serve.app
