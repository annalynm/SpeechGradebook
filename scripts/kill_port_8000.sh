#!/usr/bin/env bash
# Kill whatever is using port 8000 so you can start ./run_local.sh
# Usage: bash scripts/kill_port_8000.sh

PORT=8000
PID=$(lsof -ti :"$PORT" 2>/dev/null)
if [ -z "$PID" ]; then
  echo "Nothing is using port $PORT."
  exit 0
fi
echo "Killing process(es) on port $PORT: $PID"
kill $PID 2>/dev/null || true
sleep 1
if lsof -ti :"$PORT" >/dev/null 2>&1; then
  echo "Still in use. Forcing kill."
  kill -9 $(lsof -ti :"$PORT") 2>/dev/null || true
fi
echo "Done. You can now run: ./run_local.sh"
