# Qwen2.5-VL Setup for SpeechGradebook

SpeechGradebook uses **Qwen2.5-VL-7B** for video analysis and rubric extraction when configured. This provides an open-source (Apache 2.0) alternative to Gemini for body movement, eye contact, professional appearance, and rubric extraction from PDFs/images.

## Prerequisites

- Python 3.10+
- GPU with ~16GB VRAM recommended (or ~24GB for full precision)
- `pip install -r requirements-qwen.txt`

## Run the Qwen Service

```bash
cd SpeechGradebook/llm_training
pip install -r requirements-qwen.txt
python qwen_serve.py --port 8001
```

The service will:
1. Download Qwen2.5-VL-7B-Instruct from Hugging Face (first run only)
2. Listen on http://localhost:8001
3. Expose:
   - `GET /health` – health check
   - `POST /analyze_video` – video file → visual delivery notes
   - `POST /extract_rubric` – image/PDF file → rubric JSON

## Configure SpeechGradebook

**Local development:** Set `QWEN_API_URL` in `.env`:
```
QWEN_API_URL=http://localhost:8001
```

**Production (Render):** Add environment variable:
```
QWEN_API_URL=https://your-qwen-service.onrender.com
```

**Super Admin override:** Super Admins can set the Qwen Service URL in Settings → General (API Keys section).

---

## Running the Qwen service for all users (not locally)

To make the Text + Video Model (Qwen) available to everyone (e.g. when SpeechGradebook is deployed on Render), run the Qwen service on a host that has a **public URL**, then point the main app at it.

### 1. Deploy the Qwen service

Run the service on a server or PaaS that is reachable from the internet. Options:

| Option | Notes |
|--------|--------|
| **Render (Docker)** | Add a **second** Web Service in the same (or linked) repo. Set **Root Directory** to `llm_training`, **Dockerfile path** to `Dockerfile.qwen`. No GPU on standard Render; inference will be slow (CPU-only). |
| **Cloud GPU** | Run on a GPU instance (e.g. RunPod, Lambda Labs, Vast.ai, or AWS/GCP/Azure GPU VM). Use the same Dockerfile or run `python qwen_serve.py --port 8001` with the repo and `requirements-qwen.txt`. Expose port 8001 (or use a reverse proxy with HTTPS). |
| **ISAAC (campus cluster)** | See `ISAAC_QWEN_SETUP.md`. Run Qwen on a GPU node and expose it via SSH tunnel or a public URL if your institution provides one. |

### 2. Set CORS so the browser can call Qwen

The SpeechGradebook frontend runs in users’ browsers and calls the Qwen service directly. The Qwen server must allow your app’s origin.

Set the **ALLOWED_ORIGINS** environment variable on the **Qwen** service (not the main app):

- **Single origin:** `ALLOWED_ORIGINS=https://speechgradebook.onrender.com`
- **Multiple (e.g. staging + prod):** `ALLOWED_ORIGINS=https://speechgradebook.onrender.com,https://staging.onrender.com`

Use your actual SpeechGradebook URL(s); no trailing slash. Without this, browser requests to Qwen will be blocked by CORS.

### 3. Point SpeechGradebook at the Qwen URL

So that **all users** use the same Qwen service:

- **Recommended:** On the **main** SpeechGradebook service (e.g. on Render), add an environment variable:  
  **`QWEN_API_URL`** = your Qwen service URL (e.g. `https://qwen-speechgradebook.onrender.com`).  
  The app serves this to the browser via `/config.js`, so no per-user setup is needed.

- **Alternative:** A Super Admin can set **SpeechGradebook Text + Video Model (Qwen) Service URL** in **Settings → General** (API Keys). That value is stored in the browser (localStorage) for that user only.

### 4. Optional: Docker build and run

From the repo root:

```bash
cd llm_training
docker build -f Dockerfile.qwen -t qwen-speechgradebook .
docker run -p 8001:8001 -e PORT=8001 -e ALLOWED_ORIGINS=https://speechgradebook.onrender.com qwen-speechgradebook
```

Use a CUDA base image in the Dockerfile if you run on a GPU host (see comments in `Dockerfile.qwen`).

## API Keys (Super Admin Only)

Only Super Admins can configure API keys (Gemini, OpenAI, Anthropic) and the Qwen Service URL. Other users use the system-configured Qwen model for rubric extraction and video analysis.

## Rubric Extraction

- **Supported formats:** PDF, PNG, JPG, JPEG, WebP
- **PDF:** Requires PyMuPDF (`pip install pymupdf`) to convert first page to image
- **Excel/Word:** Not directly supported; convert to PDF or take a screenshot

## Video Analysis

When evaluating with the SpeechGradebook Text Model (Mistral) provider and a video file, the app uses Qwen (when configured) to extract visual delivery notes (body movement, eye contact, gestures, posture, professional appearance). These notes are sent to the SpeechGradebook Text Model (Mistral) for scoring. You can also select **SpeechGradebook Text + Video Model (Qwen)** to evaluate video directly (Qwen analyzes both video and text).
