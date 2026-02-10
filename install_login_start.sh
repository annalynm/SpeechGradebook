#!/usr/bin/env bash
# Install LaunchAgent so SpeechGradebook runs at login only for user annamcclure.
# Run once from the SpeechGradebook folder: ./install_login_start.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$ROOT/launchd/com.speechgradebook.local.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.speechgradebook.local.plist"

mkdir -p "$(dirname "$PLIST_DEST")"
sed "s|REPLACE_WITH_SPEECHGRADEBOOK_ROOT|$ROOT|g" "$PLIST_SRC" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "Installed. SpeechGradebook will start at login only for user annamcclure."
echo "Plist: $PLIST_DEST"
echo "To remove: launchctl unload $PLIST_DEST"
echo "Logs: /tmp/speechgradebook.out.log and /tmp/speechgradebook.err.log"
