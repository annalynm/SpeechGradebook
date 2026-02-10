#!/usr/bin/env bash
# Run Qwen on port 8001 and expose it via Cloudflare Quick Tunnel so Render (and all users) can use it.
# Run this script *on the ISAAC compute node* (inside your interactive GPU job), e.g.:
#   srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
#   module load anaconda3 && conda activate speechgradebook
#   cd ~/llm_training && ./run_qwen_with_public_url.sh
#
# Before running, set ALLOWED_ORIGINS so the Render app can call Qwen:
#   export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
#
# Then set QWEN_API_URL on Render to the https://xxxx.trycloudflare.com URL printed by cloudflared.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use Python 3.10+ for Qwen (transformers 4.50+). Prefer PYTHON_QWEN or conda env by path.
if [ -n "$PYTHON_QWEN" ] && [ -x "$PYTHON_QWEN" ]; then
  PYTHON_CMD="$PYTHON_QWEN"
elif [ -x "$HOME/.conda/envs/qwen/bin/python" ]; then
  PYTHON_CMD="$HOME/.conda/envs/qwen/bin/python"
elif [ -n "$CONDA_PREFIX" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
  PYTHON_CMD="$CONDA_PREFIX/bin/python"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
else
  PYTHON_CMD=""
fi
if [ -z "$PYTHON_CMD" ] || ! "$PYTHON_CMD" -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
  if [ -x "$HOME/.conda/envs/qwen/bin/python" ]; then
    PYTHON_CMD="$HOME/.conda/envs/qwen/bin/python"
  else
    echo "ERROR: Need Python 3.10+. Create env and set PYTHON_QWEN, e.g.:"
    echo "  conda create -n qwen python=3.10 -y -c conda-forge"
    echo "  export PYTHON_QWEN=\$HOME/.conda/envs/qwen/bin/python"
    echo "  ./run_qwen_with_public_url.sh"
    exit 1
  fi
fi

if [ -z "$ALLOWED_ORIGINS" ]; then
  echo "WARNING: ALLOWED_ORIGINS is not set. Set it so the browser can call Qwen:"
  echo "  export ALLOWED_ORIGINS=https://speechgradebook.onrender.com"
  echo ""
fi

# Ensure cloudflared exists (one-time download on the node)
if [ ! -x "$SCRIPT_DIR/cloudflared" ]; then
  echo "Downloading cloudflared..."
  curl -sL -o "$SCRIPT_DIR/cloudflared" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
  chmod +x "$SCRIPT_DIR/cloudflared"
fi

echo "Starting Qwen on port 8001 (using $PYTHON_CMD)..."
"$PYTHON_CMD" qwen_serve.py --port 8001 &
sleep 30
echo "Starting Cloudflare Quick Tunnel..."
echo ""

# Capture cloudflared output so we can detect and re-print the URL prominently
CF_LOG=$(mktemp)
trap "rm -f '$CF_LOG'" EXIT
# Use --protocol http2 to avoid QUIC CRYPTO_ERROR 0x178 (tls: no application protocol) on some networks (e.g. ISAAC)
"$SCRIPT_DIR/cloudflared" tunnel --url http://localhost:8001 --protocol http2 2>&1 | tee "$CF_LOG" &
TEE_PID=$!

# Wait for the URL to appear (cloudflared usually prints it within 5–15 seconds)
echo "Waiting for tunnel URL (check back in a few seconds)..."
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  sleep 1
  if grep -qE 'https://[^[:space:]]+\.trycloudflare\.com' "$CF_LOG" 2>/dev/null; then
    break
  fi
done

# Extract and print the URL in a banner so it's impossible to miss
TUNNEL_URL=$(grep -oE 'https://[^[:space:]]+\.trycloudflare\.com' "$CF_LOG" 2>/dev/null | head -1)
if [ -n "$TUNNEL_URL" ]; then
  echo ""
  echo "================================================================================"
  echo "  COPY THIS URL → Set it as QWEN_API_URL on Render (Environment) and Save"
  echo "================================================================================"
  echo ""
  echo "  $TUNNEL_URL"
  echo ""
  echo "================================================================================"
  echo ""
else
  echo ""
  echo "  (If no URL appeared above, look for a line like https://....trycloudflare.com in the cloudflared output and use that for QWEN_API_URL on Render.)"
  echo ""
fi

wait $TEE_PID
