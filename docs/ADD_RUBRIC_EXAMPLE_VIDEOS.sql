-- Add example_videos column to rubrics table for storing reference video URLs
--
-- Run in Supabase → SQL Editor
-- Example videos help the AI know what good/poor performances look like when scoring

ALTER TABLE rubrics
ADD COLUMN IF NOT EXISTS example_videos jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN rubrics.example_videos IS 'Array of {url, label} for reference example videos (YouTube, Vimeo, direct links)';
