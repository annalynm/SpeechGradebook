#!/bin/bash
#SBATCH --job-name=speechgradebook-serve
#SBATCH --partition=PARTITION_PLACEHOLDER
#SBATCH --account=ACCOUNT_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=logs/serve_model_%j.out
#SBATCH --error=logs/serve_model_%j.err

# Run SpeechGradebook Model (fine-tuned Mistral 7B) on ISAAC GPU for evaluations.
# After the job starts, create an SSH tunnel from your laptop so SpeechGradebook can use it.
# See ISAAC_SPEECHGRADEBOOK_MODEL.md for full instructions.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p logs

MODEL_PATH="${MODEL_PATH:-$SCRIPT_DIR/mistral7b-speech-lora}"
PORT="${PORT:-8000}"
ISAAC_LOGIN="${ISAAC_LOGIN:-login.isaac.utk.edu}"

module load anaconda3 2>/dev/null || true
conda activate speechgradebook 2>/dev/null || true

NODE=$(hostname)
echo "Node: $NODE"
echo "Port: $PORT"
echo "Model: $MODEL_PATH"
echo "From your laptop run: ssh -L ${PORT}:localhost:${PORT} -J $USER@$ISAAC_LOGIN $USER@$NODE"
echo "Then set Evaluation server URL to http://localhost:${PORT} in SpeechGradebook."

python serve_model.py --model_path "$MODEL_PATH" --port "$PORT" --load_in_8bit
