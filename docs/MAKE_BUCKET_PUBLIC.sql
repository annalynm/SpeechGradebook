-- Make the evaluation-media bucket public
-- Run this in Supabase SQL Editor if you can't find the UI toggle

-- First, check current status
SELECT name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
WHERE name = 'evaluation-media';

-- If public is false, update it (requires appropriate permissions)
UPDATE storage.buckets
SET public = true
WHERE name = 'evaluation-media';

-- Verify it worked
SELECT name, public
FROM storage.buckets
WHERE name = 'evaluation-media';

-- Also ensure there's a public read policy
-- Check existing policies
SELECT * FROM storage.policies
WHERE definition::text LIKE '%evaluation-media%';

-- Create a public read policy if one doesn't exist
-- This allows anyone to read files from the bucket
CREATE POLICY IF NOT EXISTS "Public read access for evaluation-media"
ON storage.objects
FOR SELECT
USING (bucket_id = 'evaluation-media');

-- If you prefer authenticated users only, use this instead:
-- CREATE POLICY IF NOT EXISTS "Authenticated read access for evaluation-media"
-- ON storage.objects
-- FOR SELECT
-- USING (
--   bucket_id = 'evaluation-media' 
--   AND auth.role() = 'authenticated'
-- );
