#!/bin/bash
# Weekly (or scheduled) automation: export new consented evaluations from Supabase,
# then run training on ISAAC (or locally). Run via cron or Task Scheduler.
#
# Requires: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in run_config.env or environment.
# Optional: run_config.env with ISAAC_* for ISAAC; otherwise set RUN_BACKEND=local to train locally.
#
# Example cron (every Sunday at 2am):
#   0 2 * * 0 /Users/annamcclure/SpeechGradebook\ Repo/SpeechGradebook/llm_training/weekly_export_and_train.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/run_config.env" ]; then
  set -a
  source "$SCRIPT_DIR/run_config.env"
  set +a
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  echo "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in run_config.env or the environment." >&2
  echo "Get the service role key from Supabase Dashboard → Settings → API (use only on a secure machine)." >&2
  exit 1
fi

export SUPABASE_URL
export SUPABASE_SERVICE_ROLE_KEY

echo "Exporting new consented evaluations (--consent --new-only)..."
node export_from_supabase.js --consent --new-only --output "$SCRIPT_DIR/exported.json"

if [ ! -f "$SCRIPT_DIR/exported.json" ]; then
  echo "No exported.json produced. Exiting."
  exit 0
fi

# Check if we have any data (more than "[]")
SIZE=$(wc -c < "$SCRIPT_DIR/exported.json")
if [ "$SIZE" -le 10 ]; then
  echo "No new evaluations to train. Exiting."
  exit 0
fi

echo "Running training (backend: ${RUN_BACKEND:-isaac})..."
"$SCRIPT_DIR/run_training.sh"
