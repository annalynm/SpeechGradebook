# Instructions: Link Evaluation Videos to Database

## Quick Method: Run the Shell Script

```bash
cd /Users/annamcclure/SpeechGradebook
./scripts/link_evaluation_videos.sh
```

The script has your credentials hardcoded, so it should work immediately.

## Alternative: Manual Command

If you prefer to run it manually:

```bash
cd /Users/annamcclure/SpeechGradebook
export SUPABASE_URL="https://mqhbfefylpfqsbtrshpu.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xaGJmZWZ5bHBmcXNidHJzaHB1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTI4MDMyMywiZXhwIjoyMDg0ODU2MzIzfQ.51mD4OnICMCJgiIM1GfffN1ZefObO-pJqaVH_JYkf_U"
python3 scripts/link_evaluation_videos_simple.py
```

## Fix .env File (Optional)

If you want to add these to your `.env` file for future use, add them **without quotes**:

```bash
SUPABASE_URL=https://mqhbfefylpfqsbtrshpu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xaGJmZWZ5bHBmcXNidHJzaHB1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTI4MDMyMywiZXhwIjoyMDg0ODU2MzIzfQ.51mD4OnICMCJgiIM1GfffN1ZefObO-pJqaVH_JYkf_U
```

**Important:** 
- No quotes around the values
- No spaces around the `=` sign
- Each on its own line

## What the Script Does

1. Lists all files in the `evaluation-media` storage bucket
2. Extracts evaluation IDs from file paths (format: `{user_id}/{evaluation_id}/{filename}`)
3. Updates the `evaluations` table with `video_url` or `audio_url` for matching files
4. Shows a summary of what was updated

## Troubleshooting

If you get permission errors:
- Make sure you're using the **Service Role Key** (not the anon key)
- The Service Role Key has admin access to storage and database

If files aren't found:
- Check that the `evaluation-media` bucket exists in Supabase Storage
- Verify files are in the expected path format: `{user_id}/{evaluation_id}/{filename}`
