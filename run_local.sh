#!/usr/bin/env bash
# Run SpeechGradebook locally (frontend + API at /api).
# Usage: ./run_local.sh   or   bash run_local.sh
# Uses a venv to avoid system Python "externally-managed-environment" errors.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Create venv if missing (avoids pip "externally-managed-environment" on macOS/Homebrew)
if [ ! -d "venv" ]; then
  echo "Creating virtual environment (one-time)..."
  python3 -m venv venv
fi
# Use venv Python by path so we don't depend on activate or PATH
PYTHON="$ROOT/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$ROOT/venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
  echo "Error: no venv Python at venv/bin/python or venv/bin/python3" >&2
  exit 1
fi

# Install dependencies into venv if uvicorn, torch, or dotenv missing
if ! "$PYTHON" -c "import uvicorn; import torch; import dotenv; import slowapi" 2>/dev/null; then
  echo "Installing dependencies into venv (one-time, can take several minutes for torch)..."
  "$PYTHON" -m pip install -r requirements.txt
fi

PORT="${PORT:-8000}"
URL="http://localhost:$PORT"
echo "=============================================="
echo "  SpeechGradebook"
echo "=============================================="
echo "  Open this in your browser: $URL"
echo "  API: $URL/api"
echo ""
echo "  For rubric extraction & video analysis: in another terminal, from this dir:"
echo "    cd llm_training && pip install -r requirements-qwen.txt && python qwen_serve.py --port 8001"
echo "  Then add QWEN_API_URL=http://localhost:8001 to .env"
echo "=============================================="
echo "Press Ctrl+C to stop."
echo ""

# Open browser after server is up (run in background; don't fail if open fails)
( sleep 4 && ( command -v open >/dev/null 2>&1 && open "$URL" ) || true ) &

exec "$PYTHON" -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
