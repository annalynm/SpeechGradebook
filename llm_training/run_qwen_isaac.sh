#!/usr/bin/env bash
# Submit the Qwen service job to ISAAC (GPU). Run from your laptop.
# Prerequisites: llm_training copied to ISAAC, conda env + requirements-qwen.txt installed on ISAAC.
# See ISAAC_QWEN_SETUP.md for one-time setup and tunnel instructions.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/run_config.env" ]; then
  set -a
  source "$SCRIPT_DIR/run_config.env"
  set +a
fi

ISAAC_USER="${ISAAC_USER:-$USER}"
ISAAC_HOST="${ISAAC_HOST:-login.isaac.utk.edu}"
ISAAC_REMOTE_DIR="${ISAAC_REMOTE_DIR:-~/llm_training}"
ISAAC_PARTITION="${ISAAC_PARTITION:-campus-gpu}"
ISAAC_ACCOUNT="${ISAAC_ACCOUNT:-}"

if [ -z "$ISAAC_USER" ]; then
  echo "Error: ISAAC_USER not set. Create run_config.env (see run_config.env.example) and set ISAAC_USER (your NetID)." >&2
  exit 1
fi

mkdir -p logs
sed -e "s/PARTITION_PLACEHOLDER/$ISAAC_PARTITION/" \
    -e "s/ACCOUNT_PLACEHOLDER/$ISAAC_ACCOUNT/" \
    run_qwen_isaac.slurm > logs/run_qwen_isaac_$$.slurm

echo "Copying SLURM script to ISAAC and submitting..."
scp -q logs/run_qwen_isaac_$$.slurm "$ISAAC_USER@$ISAAC_HOST:$ISAAC_REMOTE_DIR/run_qwen_isaac.slurm"
ssh "$ISAAC_USER@$ISAAC_HOST" "cd $ISAAC_REMOTE_DIR && mkdir -p logs && sbatch run_qwen_isaac.slurm"

echo "Job submitted. Check status: ssh $ISAAC_USER@$ISAAC_HOST 'squeue -u \$USER'"
echo "Logs: ssh $ISAAC_USER@$ISAAC_HOST 'tail -f $ISAAC_REMOTE_DIR/logs/qwen_serve_*.out'"
echo "Then create SSH tunnel from your laptop (see ISAAC_QWEN_SETUP.md)."
