#!/bin/bash
# Run on ISAAC after transfer: convert exported.json to JSONL and submit SLURM job.
# Called by run_training.sh via ssh. Expects to run in ISAAC_REMOTE_DIR (llm_training).

set -e
cd "$(dirname "$0")/.."
mkdir -p logs

if [ ! -f "exported.json" ]; then
  echo "Error: exported.json not found in $(pwd)" >&2
  exit 1
fi

echo "Converting exported.json to train.jsonl and validation.jsonl..."
node export_to_jsonl.js exported.json --split 0.9

if [ ! -f "train.jsonl" ]; then
  echo "Error: export_to_jsonl.js did not produce train.jsonl" >&2
  exit 1
fi

# Substitute placeholders in SLURM script from env (set by run_training.sh or run_config.env)
PARTITION="${ISAAC_PARTITION:-campus-gpu}"
ACCOUNT="${ISAAC_ACCOUNT:-}"
GPU_COUNT="${ISAAC_GPU_COUNT:-1}"
TIME="${ISAAC_TIME:-04:00:00}"

sed -e "s/PARTITION_PLACEHOLDER/$PARTITION/" \
    -e "s/ACCOUNT_PLACEHOLDER/$ACCOUNT/" \
    -e "s/GPU_COUNT_PLACEHOLDER/$GPU_COUNT/" \
    -e "s|TIME_PLACEHOLDER|$TIME|" \
    train_speechgradebook.slurm > logs/train_speechgradebook_$$.slurm

echo "Submitting SLURM job..."
JOBID=$(sbatch logs/train_speechgradebook_$$.slurm | awk '{print $4}')
echo "Submitted job $JOBID. Monitor with: squeue -u \$USER"
echo "Logs: logs/train_${JOBID}.out and logs/train_${JOBID}.err"
