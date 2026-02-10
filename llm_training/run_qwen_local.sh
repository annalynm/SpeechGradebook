#!/usr/bin/env bash
# Run Qwen service using the venv in this directory.
# One-time: python3 -m venv venv && source venv/bin/activate && pip install -r requirements-qwen.txt

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
  echo "No venv found. Create it and install deps first:"
  echo "  cd \"$SCRIPT_DIR\""
  echo "  python3 -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r requirements-qwen.txt"
  exit 1
fi

source venv/bin/activate
exec python qwen_serve.py --port "${PORT:-8001}" "$@"
