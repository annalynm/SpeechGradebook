#!/bin/bash
# Simple shell script to link evaluation videos
# This avoids .env file issues by using environment variables directly

cd "$(dirname "$0")/.."

# Set your Supabase credentials here
export SUPABASE_URL="https://mqhbfefylpfqsbtrshpu.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xaGJmZWZ5bHBmcXNidHJzaHB1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTI4MDMyMywiZXhwIjoyMDg0ODU2MzIzfQ.51mD4OnICMCJgiIM1GfffN1ZefObO-pJqaVH_JYkf_U"

# Run the Python script
python3 scripts/link_evaluation_videos_simple.py
