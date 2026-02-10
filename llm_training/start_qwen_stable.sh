#!/usr/bin/env bash
# Start Qwen and the Cloudflare NAMED tunnel so the URL never changes.
# Run this on the ISAAC compute node (inside your interactive GPU session).
#
# One-time first:
#   1. Do the Named Tunnel setup (QWEN_NAMED_TUNNEL_WALKTHROUGH.md): create tunnel,
#      add public hostname, copy .cloudflared/ (config.yml + TUNNEL_ID.json) to this dir.
#   2. Set QWEN_API_URL on Render to your stable URL (e.g. https://qwen.yourdomain.com).
#
# Each time you want to evaluate:
#   srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
#   cd ~/llm_training && ./start_qwen_stable.sh
# Leave the terminal open; then use the app to evaluate with Qwen.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-https://speechgradebook.onrender.com}"

if [ ! -f ".cloudflared/config.yml" ] || [ -z "$(ls -A .cloudflared/*.json 2>/dev/null)" ]; then
  echo "ERROR: Named tunnel not set up. Put config.yml and TUNNEL_ID.json in $SCRIPT_DIR/.cloudflared/"
  echo "See: QWEN_NAMED_TUNNEL_WALKTHROUGH.md"
  exit 1
fi

# On ISAAC: load anaconda3 and activate speechgradebook so the right python is used
if command -v module >/dev/null 2>&1; then
  module load anaconda3 2>/dev/null || true
fi
if [ -f "$HOME/.conda/etc/profile.d/conda.sh" ]; then
  source "$HOME/.conda/etc/profile.d/conda.sh" 2>/dev/null || true
elif [ -n "$CONDA_ROOT" ] && [ -f "$CONDA_ROOT/etc/profile.d/conda.sh" ]; then
  source "$CONDA_ROOT/etc/profile.d/conda.sh" 2>/dev/null || true
fi
conda activate speechgradebook 2>/dev/null || true

# Python for Qwen
if [ -x "$HOME/.conda/envs/qwen/bin/python" ]; then
  PYTHON_CMD="$HOME/.conda/envs/qwen/bin/python"
elif [ -n "$CONDA_PREFIX" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
  PYTHON_CMD="$CONDA_PREFIX/bin/python"
else
  PYTHON_CMD="python"
fi

# Download cloudflared if missing
if [ ! -x "$SCRIPT_DIR/cloudflared" ]; then
  echo "Downloading cloudflared..."
  curl -sL -o "$SCRIPT_DIR/cloudflared" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
  chmod +x "$SCRIPT_DIR/cloudflared"
fi

# Tunnel name must match the one you created in the dashboard
TUNNEL_NAME="${TUNNEL_NAME:-qwen-speechgradebook}"

echo "Starting Qwen on port 8001..."
"$PYTHON_CMD" qwen_serve.py --port 8001 &
sleep 60
echo "Starting named tunnel ($TUNNEL_NAME)..."
"$SCRIPT_DIR/cloudflared" tunnel --protocol http2 --config "$SCRIPT_DIR/.cloudflared/config.yml" run "$TUNNEL_NAME"
