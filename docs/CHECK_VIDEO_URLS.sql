-- Check what video URLs look like in the database
-- Run this in Supabase SQL Editor to see the format of video_url values

SELECT 
    id,
    instructor_id,
    video_url,
    audio_url,
    created_at,
    CASE 
        WHEN video_url IS NULL AND audio_url IS NULL THEN 'No media'
        WHEN video_url LIKE 'http%' THEN 'Full URL'
        WHEN video_url LIKE '/%' THEN 'Relative path'
        WHEN video_url NOT LIKE '%/%' THEN 'Filename only'
        ELSE 'Partial path'
    END as url_type,
    LENGTH(video_url) as url_length
FROM evaluations
WHERE video_url IS NOT NULL OR audio_url IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
