-- Link Existing Videos/Audio to Evaluations
-- Run this in Supabase SQL Editor
--
-- This script finds videos/audio files in the evaluation-media bucket
-- and links them to evaluations based on the storage path structure:
-- {user_id}/{evaluation_id}/{filename}
--
-- Note: This requires the storage.objects table to be accessible.
-- If you get permission errors, you may need to run this as a database function
-- with SECURITY DEFINER privileges, or use the Supabase Storage API instead.

-- ============================================
-- OPTION 1: Manual Update (if you know the paths)
-- ============================================
-- If you know specific evaluation IDs and their video URLs, you can update manually:
-- UPDATE evaluations 
-- SET video_url = 'https://your-project.supabase.co/storage/v1/object/public/evaluation-media/path/to/video.mp4'
-- WHERE id = 'evaluation-uuid-here';

-- ============================================
-- OPTION 2: Function to Link Videos from Storage
-- ============================================
-- This function attempts to match storage objects to evaluations
-- based on the path pattern: {instructor_id}/{evaluation_id}/{filename}

CREATE OR REPLACE FUNCTION link_evaluation_media_from_storage()
RETURNS TABLE (
  evaluation_id uuid,
  video_url text,
  audio_url text,
  updated_count integer
) AS $$
DECLARE
  v_updated_count integer := 0;
  v_storage_record RECORD;
  v_eval_record RECORD;
  v_public_url text;
  v_bucket_name text := 'evaluation-media';
BEGIN
  -- Note: This requires access to storage.objects table
  -- If you get permission errors, you'll need to use the Storage API instead
  
  -- Loop through storage objects in the evaluation-media bucket
  FOR v_storage_record IN
    SELECT 
      name as object_path,
      bucket_id,
      metadata
    FROM storage.objects
    WHERE bucket_id = v_bucket_name
      AND (name LIKE '%/%/%') -- Pattern: user_id/evaluation_id/filename
  LOOP
    -- Extract evaluation ID from path (second segment)
    -- Path format: {instructor_id}/{evaluation_id}/{filename}
    DECLARE
      v_path_parts text[];
      v_eval_id uuid;
      v_filename text;
      v_is_video boolean;
      v_is_audio boolean;
    BEGIN
      v_path_parts := string_to_array(v_storage_record.object_path, '/');
      
      -- Need at least 3 parts: user_id, evaluation_id, filename
      IF array_length(v_path_parts, 1) >= 3 THEN
        BEGIN
          v_eval_id := v_path_parts[2]::uuid;
          v_filename := v_path_parts[3];
          
          -- Determine if it's video or audio based on extension
          v_is_video := v_filename ~* '\.(mp4|webm|mov|avi|mkv|quicktime)$';
          v_is_audio := v_filename ~* '\.(mp3|wav|m4a|aac|ogg|flac)$';
          
          -- Check if evaluation exists
          SELECT id INTO v_eval_record
          FROM evaluations
          WHERE id = v_eval_id;
          
          IF FOUND THEN
            -- Construct public URL
            -- Format: https://{project_ref}.supabase.co/storage/v1/object/public/{bucket}/{path}
            v_public_url := 'https://' || current_setting('app.settings.supabase_url', true) || '/storage/v1/object/public/' || v_bucket_name || '/' || v_storage_record.object_path;
            
            -- If we can't get the URL from settings, use a placeholder that you'll need to replace
            IF v_public_url IS NULL OR v_public_url = '' THEN
              -- Use a pattern that you can replace with your actual Supabase URL
              v_public_url := 'https://YOUR-PROJECT-REF.supabase.co/storage/v1/object/public/' || v_bucket_name || '/' || v_storage_record.object_path;
            END IF;
            
            -- Update evaluation with media URL
            IF v_is_video THEN
              UPDATE evaluations
              SET video_url = v_public_url
              WHERE id = v_eval_id
                AND (video_url IS NULL OR video_url = '');
              
              IF FOUND THEN
                v_updated_count := v_updated_count + 1;
                evaluation_id := v_eval_id;
                video_url := v_public_url;
                audio_url := NULL;
                updated_count := v_updated_count;
                RETURN NEXT;
              END IF;
            ELSIF v_is_audio THEN
              UPDATE evaluations
              SET audio_url = v_public_url
              WHERE id = v_eval_id
                AND (audio_url IS NULL OR audio_url = '');
              
              IF FOUND THEN
                v_updated_count := v_updated_count + 1;
                evaluation_id := v_eval_id;
                video_url := NULL;
                audio_url := v_public_url;
                updated_count := v_updated_count;
                RETURN NEXT;
              END IF;
            END IF;
          END IF;
        EXCEPTION
          WHEN OTHERS THEN
            -- Skip invalid UUIDs or other errors
            CONTINUE;
        END;
      END IF;
    END;
  END LOOP;
  
  RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- OPTION 3: Manual Query to Find Storage Objects
-- ============================================
-- If the function above doesn't work due to permissions, use this query
-- to see what files exist in storage, then manually update:

-- SELECT 
--   name as object_path,
--   bucket_id,
--   created_at,
--   metadata
-- FROM storage.objects
-- WHERE bucket_id = 'evaluation-media'
-- ORDER BY created_at DESC;

-- ============================================
-- OPTION 4: Update Using Storage API (Recommended)
-- ============================================
-- Since storage.objects might not be accessible via SQL, the best approach is:
-- 1. List files in the evaluation-media bucket using Supabase Storage API
-- 2. Match paths to evaluations
-- 3. Update evaluations table

-- Here's a helper query to see which evaluations are missing media URLs:

SELECT 
  e.id as evaluation_id,
  e.instructor_id,
  e.created_at,
  e.video_url,
  e.audio_url,
  CASE 
    WHEN e.video_url IS NULL AND e.audio_url IS NULL THEN 'Missing media'
    WHEN e.video_url IS NOT NULL THEN 'Has video'
    WHEN e.audio_url IS NOT NULL THEN 'Has audio'
  END as media_status
FROM evaluations e
WHERE e.video_url IS NULL 
  AND e.audio_url IS NULL
ORDER BY e.created_at DESC;

-- ============================================
-- OPTION 5: Python Script Alternative
-- ============================================
-- If SQL doesn't work, you can use the Supabase Storage API from Python/JavaScript
-- to list files and update the database. See the Python script below this SQL file.

COMMENT ON FUNCTION link_evaluation_media_from_storage() IS 'Attempts to link storage objects to evaluations based on path pattern. May require SECURITY DEFINER or Storage API access.';
