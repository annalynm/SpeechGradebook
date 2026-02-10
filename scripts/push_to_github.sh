#!/usr/bin/env bash
# Push local changes to the SpeechGradebook GitHub repo.
# Run from repo root: ./scripts/push_to_github.sh [commit message]
# If no message is given, you'll be prompted or a default is used.

set -e
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "Not inside a git repository." >&2
  exit 1
fi

BRANCH=$(git branch --show-current)
echo "Branch: $BRANCH"

# Status
git status -sb
echo ""

# Add all changes
git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit. Working tree clean."
  exit 0
fi

# Commit message
MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "Enter commit message (or press Enter for 'Updates to SpeechGradebook'):"
  read -r MSG
  MSG="${MSG:-Updates to SpeechGradebook}"
fi

git commit -m "$MSG"
echo ""
echo "Pushing to origin/$BRANCH..."
git push origin "$BRANCH"
echo "Done."
