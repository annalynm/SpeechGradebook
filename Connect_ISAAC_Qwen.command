#!/bin/bash
# Double-click this file on your Mac to open Terminal and connect to ISAAC + launch Qwen.
# First time: run "ssh amcclu12@login.isaac.utk.edu" in Terminal and type 'yes' to accept the host key, then use this.

cd "$(dirname "$0")"
chmod +x scripts/connect_isaac_qwen.sh 2>/dev/null
exec ./scripts/connect_isaac_qwen.sh
