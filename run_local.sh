#!/usr/bin/env bash
# Run SpeechGradebook from repo root. Jumps into SpeechGradebook/ and runs the real script.
# You must run this from the repo root (the folder that contains the SpeechGradebook folder).
ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$ROOT/SpeechGradebook/run_local.sh"
if [ ! -f "$SCRIPT" ]; then
  echo "SpeechGradebook/run_local.sh not found."
  echo "Run this from the repo root (the folder that contains 'SpeechGradebook')."
  echo "Example: cd '/Users/annamcclure/SpeechGradebook Repo'"
  echo "Then: ./run_local.sh"
  exit 1
fi
if [ ! -x "$SCRIPT" ]; then
  chmod +x "$SCRIPT"
fi
cd "$ROOT/SpeechGradebook" || exit 1
echo "Starting from repo root..."
exec ./run_local.sh
