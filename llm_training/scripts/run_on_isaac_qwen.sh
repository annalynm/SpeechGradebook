#!/bin/bash
# Run on ISAAC after transfer: submit Qwen (video) training SLURM job.
# Expects train_qwen.jsonl in current dir (llm_training). Called by run_qwen_training.sh via ssh.

set -e
cd "$(dirname "$0")/.."
mkdir -p logs

if [ ! -f "train_qwen.jsonl" ]; then
  echo "Error: train_qwen.jsonl not found in $(pwd)" >&2
  exit 1
fi

PARTITION="${ISAAC_PARTITION:-campus-gpu}"
ACCOUNT="${ISAAC_ACCOUNT:-}"

sed -e "s/PARTITION_PLACEHOLDER/$PARTITION/" \
    -e "s/ACCOUNT_PLACEHOLDER/$ACCOUNT/" \
    train_qwen_speechgradebook.slurm > logs/train_qwen_speechgradebook_$$.slurm

echo "Submitting Qwen training SLURM job..."
JOBID=$(sbatch logs/train_qwen_speechgradebook_$$.slurm | awk '{print $4}')
echo "Submitted job $JOBID. Monitor: squeue -u \$USER"
echo "Logs: logs/train_qwen_${JOBID}.out and logs/train_qwen_${JOBID}.err"
