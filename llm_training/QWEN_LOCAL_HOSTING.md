# Running Qwen Locally (Instead of ISAAC + Tunnel)

You can run the SpeechGradebook Text + Video Model (Qwen) on your own machine and point the app at it. This avoids ISAAC, Cloudflare tunnels, and CORS issues.

## When local hosting works well

- **You run the SpeechGradebook app locally** (e.g. `./run_local.sh` or `python app.py`).
- Your browser and Qwen are on the same machine: set the Qwen Service URL to `http://localhost:8001` in Settings.
- No tunnel, no Render env, no proxy needed. Evaluations (video + rubric) and rubric extraction use Qwen on your machine.

## Downsides of local hosting

| Downside | Details |
|----------|---------|
| **Hardware** | Qwen2.5-VL-7B needs a capable machine: **~16GB+ RAM** and ideally a **GPU with 8GB+ VRAM**. On CPU-only it can be slow (minutes per video). |
| **Availability** | Your computer must be on and `qwen_serve.py` must be running. If you close the laptop or stop the process, Qwen evaluations stop. |
| **Only for local app use** | If the **app** is on **Render**, the browser runs on users’ machines and cannot reach `http://localhost:8001` on your laptop. So “Qwen on my laptop” only works when the **app** is also run locally (same machine). |
| **Stability** | Sleep, network drops, or out-of-memory can stop the service; you have to restart it. |

## If the app is on Render

When the app is hosted on Render, the browser runs elsewhere and cannot access your laptop’s `localhost`. So you must expose Qwen with a **public URL**:

- **ISAAC + Cloudflare (quick or named tunnel)** – what you’ve been using; the app now uses a **backend proxy** on Render so the browser talks to Render and Render forwards to your tunnel URL (no CORS).
- **Qwen on a VPS** – run Qwen and the app (or just Qwen) on a server with a public URL.
- **Stable Cloudflare named tunnel** – one URL that doesn’t change each run; see `QWEN_NAMED_TUNNEL.md`.

## Quick local setup (app + Qwen on your machine)

1. **Conda (recommended):**
   ```bash
   conda create -n qwen python=3.10 -y
   conda activate qwen
   cd /path/to/SpeechGradebook\ Repo/llm_training
   pip install -r requirements-qwen.txt
   ```

2. **Start Qwen:**
   ```bash
   python qwen_serve.py --port 8001
   ```
   Leave this terminal open.

3. **Start the app** (in another terminal):
   ```bash
   cd /path/to/SpeechGradebook\ Repo
   ./run_local.sh
   ```

4. In the app: **Settings → General** → set **SpeechGradebook Text + Video Model (Qwen) Service URL** to `http://localhost:8001` → Save.

5. Use **SpeechGradebook Text + Video Model (Qwen)** as the evaluator for video assignments.

No tunnel, no Render env, no proxy: the browser and Qwen are both on localhost.
