#!/bin/bash
#SBATCH --job-name=qwen-speech-lora
#SBATCH --partition=PARTITION_PLACEHOLDER
#SBATCH --account=ACCOUNT_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=logs/train_qwen_%j.out
#SBATCH --error=logs/train_qwen_%j.err

# Train Qwen2.5-VL for the video tier. Requires train_qwen_vl.py and train_qwen.jsonl (manifest).
# See DUAL_MODEL_TRAINING.md for data format and two-tier setup.

if [ -n "$HF_TOKEN" ]; then
  export HF_TOKEN
elif [ -f "$(dirname "$0")/.env_isaac" ]; then
  set -a
  source "$(dirname "$0")/.env_isaac"
  set +a
fi

module load anaconda3 2>/dev/null || true
conda activate speechgradebook 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p logs

# When train_qwen_vl.py is available and train_qwen.jsonl exists:
# python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora ...

if [ -f "train_qwen_vl.py" ] && [ -f "train_qwen.jsonl" ]; then
  python train_qwen_vl.py \
    --manifest train_qwen.jsonl \
    --output_dir ./qwen2.5vl-speech-lora \
    --num_epochs 2 \
    --batch_size 1 \
    --lr 2e-5
else
  echo "Missing train_qwen_vl.py or train_qwen.jsonl. See DUAL_MODEL_TRAINING.md."
  echo "Prepare train_qwen.jsonl with one JSON per line: video_path, rubric, scores."
  exit 1
fi
