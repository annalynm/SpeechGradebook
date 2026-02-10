#!/bin/bash
# Submit Qwen (video) training to ISAAC. Expects train_qwen.jsonl in this directory (written by /llm-export-qwen).
# Usage: ./run_qwen_training.sh
# Prerequisites: run_config.env with ISAAC_HOST, ISAAC_USER, ISAAC_REMOTE_DIR (optional: ISAAC_SSH_PRIVATE_KEY, ISAAC_PARTITION, ISAAC_ACCOUNT).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/run_config.env" ]; then
  set -a
  source "$SCRIPT_DIR/run_config.env"
  set +a
fi
# Normalize ISAAC_HOST (same as run_training.sh)
_h="${ISAAC_HOST:-}"
_h="$(echo "$_h" | tr '[:upper:]' '[:lower:]')"
case "$_h" in
  ""|*issac*|*tennessee.edu*) export ISAAC_HOST=login.isaac.utk.edu ;;
esac

MANIFEST="$SCRIPT_DIR/train_qwen.jsonl"
if [ ! -f "$MANIFEST" ]; then
  echo "Error: train_qwen.jsonl not found. Export from the app (Train video model on ISAAC) first." >&2
  exit 1
fi

for v in ISAAC_HOST ISAAC_USER ISAAC_REMOTE_DIR; do
  if [ -z "${!v}" ]; then
    echo "Error: $v not set. Copy run_config.env.example to run_config.env and set ISAAC_*." >&2
    exit 1
  fi
done

SSH_OPTS=""
if [ -n "$SSH_KEY_PATH" ] && [ -f "$SSH_KEY_PATH" ]; then
  SSH_OPTS="-i $SSH_KEY_PATH -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"
fi

echo "Transferring to ISAAC and submitting Qwen training job..."
if [ -n "$SSH_OPTS" ]; then
  rsync -avz -e "ssh $SSH_OPTS" --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'qwen2.5vl-speech-lora' --exclude 'mistral7b-speech-lora' --exclude 'logs' \
    "$SCRIPT_DIR/" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/"
  rsync -avz -e "ssh $SSH_OPTS" "$MANIFEST" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/train_qwen.jsonl"
  ssh $SSH_OPTS "$ISAAC_USER@$ISAAC_HOST" "cd $ISAAC_REMOTE_DIR && ISAAC_PARTITION=${ISAAC_PARTITION:-campus-gpu} ISAAC_ACCOUNT=${ISAAC_ACCOUNT:-} bash scripts/run_on_isaac_qwen.sh"
else
  rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'qwen2.5vl-speech-lora' --exclude 'mistral7b-speech-lora' --exclude 'logs' \
    "$SCRIPT_DIR/" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/"
  rsync -avz "$MANIFEST" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/train_qwen.jsonl"
  ssh "$ISAAC_USER@$ISAAC_HOST" "cd $ISAAC_REMOTE_DIR && ISAAC_PARTITION=${ISAAC_PARTITION:-campus-gpu} ISAAC_ACCOUNT=${ISAAC_ACCOUNT:-} bash scripts/run_on_isaac_qwen.sh"
fi
echo "Job submitted on ISAAC. Check logs: ssh $ISAAC_USER@$ISAAC_HOST 'cd $ISAAC_REMOTE_DIR && tail -f logs/train_qwen_*.out'"
