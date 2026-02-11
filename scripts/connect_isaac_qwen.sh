#!/usr/bin/env bash
# Connect to ISAAC, request a GPU node, and launch Qwen + Cloudflare tunnel.
# NOTE: This script is for using ISAAC (UT's cluster) for Qwen evaluations.
# For production, use Modal instead (see llm_training/QWEN_MODAL_SETUP.md).
# This script is kept for reference or if you need ISAAC for training/testing.
#
# Run from your Mac (e.g. double-click or: ./scripts/connect_isaac_qwen.sh).
# You will be prompted for password and Duo. After the GPU job starts, Qwen and the tunnel run;
# copy the https://....trycloudflare.com URL and set QWEN_API_URL on Render if it changed.

set -e
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

ISAAC_USER="${ISAAC_USER:-amcclu12}"
ISAAC_HOST="${ISAAC_HOST:-login.isaac.utk.edu}"
REMOTE_SCRIPT='cd ~/llm_training && export ALLOWED_ORIGINS=https://speechgradebook.onrender.com && export PATH=$HOME/.conda/envs/qwen/bin:$PATH && ./run_qwen_with_public_url.sh'

echo "Connecting to ISAAC and launching Qwen (GPU job + tunnel)..."
echo "You may be prompted for password and Duo."
echo "After the GPU job starts, wait ~1–2 minutes. A banner will print: COPY THIS URL → ..."
echo "Copy that https://....trycloudflare.com URL and set QWEN_API_URL on Render (Environment)."
echo ""

ssh -t "$ISAAC_USER@$ISAAC_HOST" "srun --pty -p campus-gpu --account=ACF-UTK0011 --qos=campus-gpu --gres=gpu:1 -t 4:00:00 --mem=24G bash -c 'module load anaconda3 2>/dev/null; $REMOTE_SCRIPT'"
