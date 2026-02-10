#!/bin/bash
# Run SpeechGradebook LLM training: by default on ISAAC, or locally with --local.
# Usage: ./run_training.sh [path_to_exported.json] [--local]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

EXPORTED_JSON=""
FORCE_LOCAL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --local) FORCE_LOCAL=1; shift ;;
    --help)
      echo "Usage: $0 [path_to_exported.json] [--local]"
      echo "  Default: run on ISAAC (transfer + submit SLURM job)."
      echo "  --local: run convert + train locally instead."
      exit 0
      ;;
    *) EXPORTED_JSON="$1"; shift ;;
  esac
done

if [ -z "$EXPORTED_JSON" ]; then
  EXPORTED_JSON="$SCRIPT_DIR/exported.json"
fi
if [ ! -f "$EXPORTED_JSON" ]; then
  echo "Error: $EXPORTED_JSON not found. Export from the app first or pass a path." >&2
  exit 1
fi

# Load config (default: ISAAC)
if [ -f "$SCRIPT_DIR/run_config.env" ]; then
  set -a
  source "$SCRIPT_DIR/run_config.env"
  set +a
fi
# Normalize ISAAC_HOST: correct typos/wrong hostnames (e.g. login.issac.tennessee.edu -> login.isaac.utk.edu)
_h="${ISAAC_HOST:-}"
_h="$(echo "$_h" | tr '[:upper:]' '[:lower:]')"
case "$_h" in
  ""|*issac*|*tennessee.edu*) export ISAAC_HOST=login.isaac.utk.edu ;;
esac
RUN_BACKEND="${RUN_BACKEND:-isaac}"

if [ -n "$FORCE_LOCAL" ] || [ "$RUN_BACKEND" = "local" ]; then
  echo "Running locally (convert + train)..."
  node export_to_jsonl.js "$EXPORTED_JSON" --split 0.9
  python train_lora.py \
    --train_file train.jsonl \
    --validation_file validation.jsonl \
    --output_dir ./mistral7b-speech-lora \
    --num_epochs 3 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --load_in_8bit
  echo "Done. Model in ./mistral7b-speech-lora"
  exit 0
fi

# ISAAC: require connection vars
for v in ISAAC_HOST ISAAC_USER ISAAC_REMOTE_DIR; do
  if [ -z "${!v}" ]; then
    echo "Error: $v not set. Copy run_config.env.example to run_config.env and set ISAAC_*." >&2
    exit 1
  fi
done

# Optional: use SSH key from env (e.g. on Render: ISAAC_SSH_PRIVATE_KEY)
SSH_OPTS=""
if [ -n "$SSH_KEY_PATH" ] && [ -f "$SSH_KEY_PATH" ]; then
  SSH_OPTS="-i $SSH_KEY_PATH -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"
fi

echo "Transferring to ISAAC and submitting job..."
if [ -n "$SSH_OPTS" ]; then
  rsync -avz -e "ssh $SSH_OPTS" --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'mistral7b-speech-lora' --exclude 'logs' \
    "$SCRIPT_DIR/" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/"
  rsync -avz -e "ssh $SSH_OPTS" "$EXPORTED_JSON" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/exported.json"
  ssh $SSH_OPTS "$ISAAC_USER@$ISAAC_HOST" "cd $ISAAC_REMOTE_DIR && ISAAC_PARTITION=${ISAAC_PARTITION:-campus-gpu} ISAAC_ACCOUNT=${ISAAC_ACCOUNT:-} ISAAC_GPU_COUNT=${ISAAC_GPU_COUNT:-1} ISAAC_TIME=${ISAAC_TIME:-04:00:00} bash scripts/run_on_isaac.sh"
else
  rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude 'mistral7b-speech-lora' --exclude 'logs' \
    "$SCRIPT_DIR/" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/"
  rsync -avz "$EXPORTED_JSON" "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/exported.json"
  ssh "$ISAAC_USER@$ISAAC_HOST" "cd $ISAAC_REMOTE_DIR && ISAAC_PARTITION=${ISAAC_PARTITION:-campus-gpu} ISAAC_ACCOUNT=${ISAAC_ACCOUNT:-} ISAAC_GPU_COUNT=${ISAAC_GPU_COUNT:-1} ISAAC_TIME=${ISAAC_TIME:-04:00:00} bash scripts/run_on_isaac.sh"
fi
echo "Job submitted on ISAAC. Check logs on the cluster with: ssh $ISAAC_USER@$ISAAC_HOST 'cd $ISAAC_REMOTE_DIR && tail -f logs/train_*.out'"
