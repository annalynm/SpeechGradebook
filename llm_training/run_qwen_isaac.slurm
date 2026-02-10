#!/bin/bash
#SBATCH --job-name=qwen-serve
#SBATCH --partition=PARTITION_PLACEHOLDER
#SBATCH --account=ACCOUNT_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=logs/qwen_serve_%j.out
#SBATCH --error=logs/qwen_serve_%j.err

# Run Qwen2.5-VL service on ISAAC GPU for faster rubric extraction and video analysis.
# After the job starts, create an SSH tunnel from your laptop so SpeechGradebook can use it.
# See ISAAC_QWEN_SETUP.md for full instructions.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p logs

if [ -n "$HF_TOKEN" ]; then
  export HF_TOKEN
elif [ -f "$SCRIPT_DIR/.env_isaac" ]; then
  set -a
  source "$SCRIPT_DIR/.env_isaac"
  set +a
fi

module load anaconda3 2>/dev/null || true
conda activate speechgradebook 2>/dev/null || true

NODE=$(hostname)
ISAAC_LOGIN="${ISAAC_LOGIN:-login.isaac.utk.edu}"
echo "Node: $NODE"
echo "Port: 8001"
echo "From your laptop run: ssh -L 8001:localhost:8001 -J $USER@$ISAAC_LOGIN $USER@$NODE"
echo "Then set QWEN_API_URL=http://localhost:8001 and run SpeechGradebook."

# Optional: reverse tunnel so login node forwards to this node (if your cluster allows SSH from compute to login)

# Run Qwen server (binding to all interfaces so reverse tunnel can use it)
python qwen_serve.py --port 8001 &
QWEN_PID=$!

# Wait for server to be ready
sleep 30

# Try to create reverse tunnel so that from login node, port 8001 forwards here (then laptop can use -L 8001:localhost:8001 to login only)
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -f -N -R 8001:localhost:8001 "$ISAAC_LOGIN" 2>/dev/null || echo "Reverse tunnel skipped (optional). Use the ssh -L command above from your laptop."

wait $QWEN_PID
