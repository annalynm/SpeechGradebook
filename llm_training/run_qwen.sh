#!/usr/bin/env bash
# Run Qwen2.5-VL service for rubric extraction and video analysis.
# Usage: ./run_qwen.sh   (from this directory or from SpeechGradebook/)
# Uses the same venv as the main app.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# ROOT = SpeechGradebook directory (parent of llm_training)
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find venv (SpeechGradebook/venv)
if [ -d "$ROOT/venv" ]; then
  VENV="$ROOT/venv"
else
  echo "No venv found. Run SpeechGradebook's run_local.sh first to create it."
  echo "Or: cd SpeechGradebook && python3 -m venv venv && source venv/bin/activate"
  exit 1
fi

source "$VENV/bin/activate"
cd "$ROOT"

if ! python -c "import torch; import transformers" 2>/dev/null; then
  echo "Installing Qwen dependencies..."
  pip install -r llm_training/requirements-qwen.txt
fi

echo "Starting Qwen2.5-VL service on port 8001..."
echo "Add QWEN_API_URL=http://localhost:8001 to .env"
exec python llm_training/qwen_serve.py --port 8001
