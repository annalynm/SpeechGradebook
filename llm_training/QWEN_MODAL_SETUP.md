# Deploy Qwen on Modal (Pay-Per-Use GPU)

Use Modal's serverless GPU to run the Qwen video evaluation service. Pay only for GPU seconds; ~$30/month free credits on Starter.

## Prerequisites

1. **Modal CLI** – Installed via pipx (see main README or Modal docs).
2. **Modal setup** – `modal setup` (authenticate in browser).
3. **Working directory** – Run commands from the **SpeechGradebook repo root**.

## 1. Deploy Qwen to Modal

From the repo root:

```bash
modal deploy llm_training/qwen_modal.py
```

This builds the image (Python deps + your code), loads Qwen2.5-VL on a T4 GPU, and deploys the service. On first run, image build and model download can take 5–10 minutes.

When deploy finishes, Modal prints a URL, e.g.:

```
https://annalynm--qwen-speechgradebook.modal.run
```

Copy this URL.

## 2. Set QWEN_API_URL on Render

1. Open [Render Dashboard](https://dashboard.render.com) → your SpeechGradebook service → **Environment**.
2. Add (or update): **QWEN_API_URL** = `https://annalynm--qwen-speechgradebook.modal.run` (your Modal URL).
3. **Save**. Render will redeploy the main app.

## 3. Use Qwen in SpeechGradebook

CORS is preconfigured for `speechgradebook.onrender.com`, `www.speechgradebook.com`, and `localhost:8000`. If you use a different domain, edit `ALLOWED_ORIGINS` in `llm_training/qwen_modal.py` and redeploy.

1. Open SpeechGradebook.
2. Go to **Evaluate Speech**.
3. In **Evaluation provider**, choose **SpeechGradebook Text + Video Model (Qwen)**.
4. Upload a video and run the evaluation.

The first request after idle may take 30–90 seconds (cold start). Later requests are faster while the container stays warm.

## Dev Mode (Temporary URL)

For testing without a permanent deployment:

```bash
modal serve llm_training/qwen_modal.py
```

You get a temporary URL (e.g. `https://....modal.run`) that works while the command is running. Add it to `ALLOWED_ORIGINS` and set it as `QWEN_API_URL` for testing. Stop with Ctrl+C.

## Check Deployment

- **Modal Dashboard:** [modal.com/apps](https://modal.com/apps) – view logs, usage, credits.
- **Health check:** `curl https://YOUR-MODAL-URL/health` → should return `{"status":"ok","model":"Qwen2.5-VL-7B"}`.

## Costs

- **T4 GPU:** ~$0.000222/sec (Modal L4) or similar for T4 – about $0.01–0.03 per video evaluation.
- **Free credits:** $30/month on Starter – enough for many evaluations during testing.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS error when evaluating | Add your domain to `ALLOWED_ORIGINS` in `qwen_modal.py` and redeploy. |
| 503 / timeout | First request (cold start) can take 1–2 min. Retry or wait. |
| `modal: command not found` | Run `pipx ensurepath` and `source ~/.zshrc`, or use `~/.local/bin/modal`. |
| Image build fails | Run from repo root. Ensure `llm_training/` and `qwen_serve.py` exist. |
