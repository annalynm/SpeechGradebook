-- Fix incomplete video URLs in the database
-- This updates video_urls that are just filenames or relative paths to full URLs
-- Run this in Supabase SQL Editor

-- Replace YOUR-PROJECT-REF with your actual Supabase project reference
-- You can find this in your Supabase URL: https://YOUR-PROJECT-REF.supabase.co

UPDATE evaluations
SET video_url = 'https://mqhbfefylpfqsbtrshpu.supabase.co/storage/v1/object/public/evaluation-media/' || 
    instructor_id || '/' || id || '/' || video_url
WHERE video_url IS NOT NULL
  AND video_url NOT LIKE 'http%'
  AND video_url NOT LIKE '/%'
  AND video_url NOT LIKE '%/%'
  AND video_url ~ '^[A-Za-z0-9_\-\.]+\.(mp4|webm|mov|avi|mkv|quicktime)$';

-- Fix audio URLs similarly
UPDATE evaluations
SET audio_url = 'https://mqhbfefylpfqsbtrshpu.supabase.co/storage/v1/object/public/evaluation-media/' || 
    instructor_id || '/' || id || '/' || audio_url
WHERE audio_url IS NOT NULL
  AND audio_url NOT LIKE 'http%'
  AND audio_url NOT LIKE '/%'
  AND audio_url NOT LIKE '%/%'
  AND audio_url ~ '^[A-Za-z0-9_\-\.]+\.(mp3|wav|m4a|aac|ogg|flac)$';

-- Show what was updated
SELECT 
    id,
    video_url,
    audio_url,
    'Updated' as status
FROM evaluations
WHERE (video_url LIKE 'http%' AND video_url LIKE '%evaluation-media%')
   OR (audio_url LIKE 'http%' AND audio_url LIKE '%evaluation-media%')
ORDER BY updated_at DESC
LIMIT 10;
