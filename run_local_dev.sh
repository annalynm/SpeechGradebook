#!/usr/bin/env bash
# Run SpeechGradebook locally with DEVELOPMENT environment variables.
# Usage: ./run_local_dev.sh   or   bash run_local_dev.sh
# 
# This script uses .env.development (or .env if it exists) for development testing.
# It connects to a separate Supabase project to avoid affecting production data.
#
# Prerequisites:
#   1. Copy .env.development to .env and fill in your DEVELOPMENT Supabase credentials
#   2. Or create .env manually with your development Supabase project URL and key
#
# Uses a venv to avoid system Python "externally-managed-environment" errors.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Check if .env exists, if not suggest copying from .env.development
if [ ! -f ".env" ]; then
    if [ -f ".env.development" ]; then
        echo "=============================================="
        echo "  Setting up development environment"
        echo "=============================================="
        echo "  .env not found. Copying .env.development to .env..."
        cp .env.development .env
        echo "  ✓ Created .env from .env.development"
        echo ""
        echo "  IMPORTANT: Edit .env and add your DEVELOPMENT Supabase credentials:"
        echo "    - SUPABASE_URL (from your dev Supabase project)"
        echo "    - SUPABASE_ANON_KEY (from your dev Supabase project)"
        echo ""
        echo "  Press Enter to continue (or Ctrl+C to edit .env first)..."
        read
    else
        echo "Error: .env not found and .env.development template not found." >&2
        echo "Please create .env with your development Supabase credentials." >&2
        echo "You can copy .env.development as a starting point." >&2
        exit 1
    fi
fi

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
echo "  SpeechGradebook (DEVELOPMENT MODE)"
echo "=============================================="
echo "  Environment: Development"
echo "  Supabase: Using DEVELOPMENT project (from .env)"
echo "  Open this in your browser: $URL"
echo "  API: $URL/api"
echo ""
echo "  For rubric extraction & video analysis: in another terminal, from this dir:"
echo "    cd llm_training && pip install -r requirements-qwen.txt && python qwen_serve.py --port 8001"
echo "  Then add QWEN_API_URL=http://localhost:8001 to .env"
echo ""
echo "  ⚠️  This connects to your DEVELOPMENT Supabase project."
echo "  Production data will NOT be affected."
echo "=============================================="
echo "Press Ctrl+C to stop."
echo ""

# Open browser after server is up (run in background; don't fail if open fails)
( sleep 4 && ( command -v open >/dev/null 2>&1 && open "$URL" ) || true ) &

exec "$PYTHON" -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
