#!/usr/bin/env bash
# Trigger a test signup notification in Slack.
# Run from anywhere. Usage:
#   bash scripts/trigger_signup_slack_notification.sh [BASE_URL]
# Examples:
#   bash scripts/trigger_signup_slack_notification.sh
#   bash scripts/trigger_signup_slack_notification.sh http://localhost:8000
#   bash scripts/trigger_signup_slack_notification.sh https://speechgradebook.onrender.com

BASE_URL="${1:-http://localhost:8000}"
# Use root path /notify-signup-request (avoids /api mount 404 issues)
ENDPOINT="${BASE_URL}/notify-signup-request"
JSON='{"email":"test-instructor@university.edu","full_name":"Test Instructor (script)","requested_role":"instructor"}'

echo "POST ${ENDPOINT}"
echo ""

RESP=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "${JSON}")

# Portable: get all but last line (macOS head doesn't support head -n -1)
BODY=$(echo "$RESP" | sed '$d')
CODE=$(echo "$RESP" | tail -n 1)

echo "HTTP status: ${CODE}"
echo "Response: ${BODY}"
echo ""

if [ "$CODE" = "200" ]; then
  echo "OK. Check your Slack channel for the message."
elif [ "$CODE" = "503" ]; then
  echo "Server returned 503: SLACK_SIGNUP_WEBHOOK_URL is not set on the server. Add it to .env (local) or Render Environment, then restart."
elif [ "$CODE" = "000" ] || [ -z "$CODE" ]; then
  echo "Could not reach server (connection refused or no network). Is the app running at ${BASE_URL}?"
else
  echo "Unexpected status. Check the response above."
fi
