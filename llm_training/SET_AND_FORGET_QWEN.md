# Set Qwen URL Once — Then Just Start Qwen and Evaluate

You have two ways to **set the Qwen URL once on Render** and never change it. After that, you only start Qwen when you want to evaluate (or it’s always on).

---

## Option A: Qwen on Render (no tunnel, no URL changes ever)

**Idea:** Run Qwen as a **second Render Web Service**. It gets a **permanent URL**. You set that URL on your main app once and never touch it again. You don’t “start” Qwen manually — it’s always available when the app calls it.

**One-time setup:**

1. In the **Render Dashboard** ([dashboard.render.com](https://dashboard.render.com)), click **New +** → **Web Service**.
2. Connect the same repo as your main SpeechGradebook app.
3. Configure the new service:
   - **Name:** e.g. `qwen-speechgradebook`
   - **Root Directory:** `llm_training` (if your repo has an `llm_training` folder at the top level)
   - **Environment:** **Docker**
   - **Dockerfile path:** `llm_training/Dockerfile.qwen` (or `Dockerfile.qwen` if Root Directory is already `llm_training`)
   - **Instance type:** Free or paid (your choice)
4. **Environment variables** for this Qwen service:
   - **ALLOWED_ORIGINS** = `https://speechgradebook.onrender.com` (your main app’s URL, no trailing slash)
   - **PORT** is usually set by Render; if not, set **PORT** = `10000` (or whatever Render shows).
5. Create the service. Wait for the first deploy to finish.
6. Copy the new service’s URL (e.g. `https://qwen-speechgradebook.onrender.com`).
7. On your **main** SpeechGradebook service → **Environment** → set **QWEN_API_URL** = that URL (e.g. `https://qwen-speechgradebook.onrender.com`) → Save. Render will redeploy the main app.

**From now on:** You don’t start Qwen. Open the app, choose “SpeechGradebook Text + Video Model (Qwen),” and evaluate. The URL never changes.

**Tradeoff:** Render has no GPU. Qwen runs on CPU and can be slow (minutes per video on free tier). Fine for light use or testing; for heavy use you may want Option B.

---

## Option B: Stable URL when Qwen runs on ISAAC (one-time tunnel, one script each time)

**Idea:** Do the **tunnel setup once** (Cloudflare Named Tunnel or Tailscale Funnel) so Qwen has a **fixed URL**. Set that URL on Render once. Each time you want to evaluate, you run **one script on ISAAC** that starts Qwen and the tunnel; you never change the URL on Render.

**One-time setup (pick one):**

- **Cloudflare Named Tunnel:** Follow **QWEN_NAMED_TUNNEL_WALKTHROUGH.md** (add domain, create tunnel, add public hostname, copy credentials + config to ISAAC). Then set **QWEN_API_URL** on Render to your stable URL (e.g. `https://qwen.yourdomain.com`).
- **Tailscale Funnel:** Install Tailscale on the machine that will run Qwen (e.g. a small always-on VM or your laptop when you evaluate). Enable Funnel for port 8001 and note the stable URL. Set that as **QWEN_API_URL** on Render.

**Each time you want to evaluate:**

On ISAAC (in an interactive GPU session), run a single script that starts Qwen and the tunnel. No dashboard, no URL change.

**If you use the Cloudflare Named Tunnel**, use the script below. Save it on ISAAC as `~/llm_training/start_qwen_stable.sh` and run it each time:

```bash
#!/usr/bin/env bash
# Run this on the ISAAC compute node. Starts Qwen, then the named tunnel.
# One-time: set up the named tunnel and copy .cloudflared/ to ~/llm_training/.cloudflared/
# Set QWEN_API_URL on Render to your stable URL once.

set -e
cd ~/llm_training
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com

# Start Qwen
module load anaconda3 2>/dev/null || true
conda activate speechgradebook 2>/dev/null || true
python qwen_serve.py --port 8001 &
sleep 90

# Start the named tunnel (uses config in .cloudflared/)
if [ -f .cloudflared/config.yml ] && [ -d .cloudflared ]; then
  ./cloudflared tunnel --config .cloudflared/config.yml run qwen-speechgradebook
else
  echo "Missing .cloudflared/config.yml or tunnel credentials. Do the one-time Named Tunnel setup first (see QWEN_NAMED_TUNNEL_WALKTHROUGH.md)."
  exit 1
fi
```

Make it executable once: `chmod +x ~/llm_training/start_qwen_stable.sh`.  
Each time: get a GPU node, then run `~/llm_training/start_qwen_stable.sh`. Leave the terminal open while you evaluate. The URL on Render stays the same.

**Tradeoff:** You do the tunnel setup once (or use Tailscale). After that, “start Qwen” = run one script on ISAAC. Qwen runs on GPU so evaluations are much faster than Option A.

---

## Summary

| Goal | Use |
|------|-----|
| **Never touch the URL again, never start Qwen manually** | **Option A** — Qwen as second Render service. Set QWEN_API_URL once. Slower (CPU). |
| **Stable URL, fast (GPU), run one script when you want to evaluate** | **Option B** — One-time tunnel (Named Tunnel or Tailscale), then run `start_qwen_stable.sh` on ISAAC each time. |

Both options: **set the Qwen URL once on Render; no changing it every time.**
