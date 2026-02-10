#!/usr/bin/env bash
# Run SpeechGradebook at login only when the logged-in macOS user is annamcclure.
# Used by the LaunchAgent; you can also run ./run_local.sh directly anytime.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Only start for user annamcclure
if [ "$USER" != "annamcclure" ]; then
  exit 0
fi

exec "$ROOT/run_local.sh"
