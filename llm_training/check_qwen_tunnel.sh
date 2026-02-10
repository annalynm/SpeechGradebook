#!/usr/bin/env bash
# Run this ON ISAAC (on the same node where Qwen and the tunnel run).
# It checks if Qwen is responding locally and prints your tunnel ID for Cloudflare.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== 1. Tunnel config (this ID must have the hostname in Cloudflare) ==="
if [ -f ".cloudflared/config.yml" ]; then
  TUNNEL_ID=$(grep -E '^tunnel:' .cloudflared/config.yml | sed 's/tunnel:[[:space:]]*//')
  echo "Tunnel ID in config: $TUNNEL_ID"
  echo "In Cloudflare Zero Trust → Tunnels, the tunnel with this ID must have:"
  echo "  Public hostname: qwen.speechgradebook.com → http://localhost:8001"
else
  echo "ERROR: .cloudflared/config.yml not found"
  exit 1
fi

echo ""
echo "=== 2. Qwen local health (must succeed for the URL to work) ==="
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://localhost:8001/health | grep -q 200; then
  echo "OK - Qwen is responding on localhost:8001"
  curl -s http://localhost:8001/health
else
  echo "FAIL - Qwen is not responding on localhost:8001. Start it with: ./start_qwen_stable.sh"
fi

echo ""
echo "=== 3. Fix 1033 in Cloudflare ==="
echo "See: llm_training/FIX_1033.md"
