#!/bin/bash
#SBATCH --job-name=speechgradebook-lora
#SBATCH --partition=PARTITION_PLACEHOLDER
#SBATCH --account=ACCOUNT_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:GPU_COUNT_PLACEHOLDER
#SBATCH --mem=32G
#SBATCH --time=TIME_PLACEHOLDER
#SBATCH --output=logs/train_%j.out
#SBATCH --error=logs/train_%j.err

if [ -z "$HF_TOKEN" ] && [ -f "$(dirname "$0")/.env_isaac" ]; then
  set -a
  source "$(dirname "$0")/.env_isaac"
  set +a
fi

module load anaconda3 2>/dev/null || true
source activate speechgradebook 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python train_lora.py \
  --train_file train.jsonl \
  --validation_file validation.jsonl \
  --output_dir ./mistral7b-speech-lora \
  --num_epochs 3 \
  --per_device_train_batch_size 2 \
  --gradient_accumulation_steps 4 \
  --load_in_8bit
