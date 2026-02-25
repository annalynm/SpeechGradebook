"""
Deploy Qwen2.5-VL evaluation service on Modal (pay-per-use GPU).

Usage (from repo root):
  modal deploy llm_training/qwen_modal.py       # Deploy → permanent URL
  modal serve llm_training/qwen_modal.py        # Dev mode → temporary URL

After deploy, set QWEN_API_URL on Render to the Modal URL (e.g. https://annalynm--qwen-speechgradebook.modal.run).

**RECOMMENDED: RunPod Alternative (80% cost savings)**
For cost-effective deployment, consider using RunPod instead:
- RunPod A100: $0.39-0.79/hour vs Modal $4-5/hour
- Cost per evaluation: $0.01-0.03 (RunPod) vs $0.05-0.15 (Modal)
- See llm_training/qwen_runpod.py for RunPod deployment (if created)

Textbook RAG: Disabled on Modal by default (DISABLE_TEXTBOOK_RAG=1) to avoid OOM.
To enable: remove DISABLE_TEXTBOOK_RAG from .env() above, create secret, then deploy.

**Cost Tracking:**
- Modal A100: ~$0.00125/second ($4-5/hour)
- RunPod A100: ~$0.000165/second ($0.39-0.79/hour)
- Cost is automatically tracked in app.py based on QWEN_API_URL provider
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
    # Using A100 GPU for sufficient memory (40GB VRAM)
    # T4 (14GB VRAM) was causing OOM errors with larger videos
    # A100 costs ~$4-5/hour vs ~$0.80/hour for T4, but provides reliable evaluations
    # Cost per evaluation: ~$0.05-0.15 with A100 (vs ~$0.01-0.03 with T4, but OOM failures)
    gpu="A100",  # Switched from T4 due to OOM errors - A100 has 40GB VRAM
    scaledown_window=600,  # Increased from 300s to 600s (10 min) to prevent scale-down during bulk uploads
    timeout=600,
    secrets=[
        modal.Secret.from_name("hf-token"),  # HF_TOKEN for faster Hugging Face downloads
        # modal.Secret.from_name("supabase-db"),  # Uncomment to enable textbook RAG; create secret first
    ],
)
@modal.concurrent(max_inputs=2)  # Increased from 1 to 2 to allow concurrent processing for bulk uploads
# With A100 40GB VRAM and 4-bit quantization, we can safely handle 2 concurrent video evaluations
class QwenService:
    """Load Qwen2.5-VL on GPU and serve the FastAPI app."""

    @modal.enter()
    def load_model(self):
        import sys
        sys.path.insert(0, "/app")
        from llm_training import qwen_serve
        self.qwen_serve = qwen_serve
        # A100 has 40GB VRAM, so we can use 4-bit quantization for cost savings
        # or load in full precision. 4-bit is fine and saves memory.
        print("[Modal] Starting model load...")
        qwen_serve._load_model("Qwen/Qwen2.5-VL-7B-Instruct", load_in_4bit=True)
        # Ensure model is fully loaded by accessing it
        # This forces synchronization and ensures weights are loaded
        if qwen_serve.model is not None:
            try:
                # Access model parameters to ensure they're loaded
                _ = next(qwen_serve.model.parameters(), None)
                print("[Modal] Model loaded and ready")
            except Exception as e:
                print(f"[Modal] Warning: Model loading check failed: {e}")
        else:
            print("[Modal] Warning: Model is None after loading")

    @modal.asgi_app(label="qwen-speechgradebook")
    def web(self):
        return self.qwen_serve.app
