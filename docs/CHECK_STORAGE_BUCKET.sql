-- Check if the evaluation-media bucket exists and is public
-- Run this in Supabase SQL Editor

-- Check bucket existence and settings
SELECT 
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
FROM storage.buckets
WHERE name = 'evaluation-media';

-- If the bucket doesn't exist or isn't public, you'll need to:
-- 1. Go to Supabase Dashboard → Storage
-- 2. Create the bucket "evaluation-media" if it doesn't exist
-- 3. Make sure it's set to "Public bucket" (not private)
-- 4. Set CORS policies if needed

-- Check if files are accessible (this will show file count)
SELECT COUNT(*) as file_count
FROM storage.objects
WHERE bucket_id = 'evaluation-media';
