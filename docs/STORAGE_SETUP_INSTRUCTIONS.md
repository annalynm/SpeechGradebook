# Supabase Storage Setup for Video Playback

## Step 1: Make the Bucket Public (Most Important)

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Click **Storage** in the left sidebar
4. Find the **`evaluation-media`** bucket in the list
5. Click on the bucket name to open it
6. Look for a toggle or setting that says **"Public bucket"** or **"Public"**
7. **Enable it** (toggle it ON)
8. Save/Apply the changes

If you don't see a "Public bucket" toggle:
- The bucket might already be public
- Or you might need to check the bucket settings/policies

## Step 2: Verify Bucket is Public (SQL Check)

Run this in Supabase SQL Editor to verify:

```sql
SELECT name, public, file_size_limit
FROM storage.buckets
WHERE name = 'evaluation-media';
```

If `public` is `true`, the bucket is public. If `false`, you need to make it public.

## Step 3: Check/Set RLS Policies (If Needed)

If videos still don't load, check Row Level Security policies:

1. Go to **Storage** → **Policies** (or **Storage** → **evaluation-media** → **Policies**)
2. Make sure there's a policy that allows public read access, like:

```sql
-- Allow public read access to evaluation-media bucket
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING (bucket_id = 'evaluation-media');
```

Or if you want authenticated users only:

```sql
-- Allow authenticated users to read
CREATE POLICY "Authenticated users can view"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'evaluation-media' 
  AND auth.role() = 'authenticated'
);
```

## Step 4: CORS Configuration

Supabase Storage CORS is typically configured automatically for public buckets. However, if you're still having issues:

### Option A: Check API Settings
1. Go to **Settings** → **API**
2. Look for CORS or Storage settings
3. Make sure your domain is allowed (or use `*` for development)

### Option B: Set via SQL (Advanced)
CORS for Supabase Storage is usually handled automatically, but you can check:

```sql
-- Check if there are any CORS restrictions
SELECT * FROM storage.buckets WHERE name = 'evaluation-media';
```

## Step 5: Test Direct URL Access

Test if a video URL works directly in your browser:

```
https://mqhbfefylpfqsbtrshpu.supabase.co/storage/v1/object/public/evaluation-media/67762a09-6823-42a2-84b9-f64bae5298bd/2e4f8182-3a15-4485-8b91-ee3192a45d96/I_Self_Intro.mp4
```

- **If it downloads/plays**: Bucket is public, issue is in the video element
- **If you get 400/403 error**: Bucket is not public or RLS policy is blocking

## Common Issues

1. **Bucket not public**: Most common issue - make sure "Public bucket" is enabled
2. **RLS policies too restrictive**: Check Storage → Policies
3. **File doesn't exist**: Verify the file path matches what's in the database
4. **CORS issues**: Usually auto-configured for public buckets, but check API settings

## Quick Fix: Make Bucket Public via SQL

If you can't find the UI toggle, you can make it public via SQL:

```sql
UPDATE storage.buckets
SET public = true
WHERE name = 'evaluation-media';
```

**Note**: This requires appropriate permissions. If it doesn't work, use the Dashboard UI instead.
