-- Reset account tiers and institutions (SpeechGradebook)
-- Run in Supabase → SQL Editor. Use these to diagnose and fix users who see demo banner, default theme, and no dashboards.
-- See docs/RESET_TIERS_AND_INSTITUTIONS.md for full explanation.

-- =============================================================================
-- 1) DIAGNOSTIC: List all auth users and their current profile (tier, institution)
-- =============================================================================
-- Run this first to see who has missing/wrong tier or institution_id.
SELECT
  u.id AS user_id,
  u.email,
  p.account_tier,
  p.institution_id,
  p.is_admin,
  p.is_super_admin,
  p.approval_status,
  i.name AS institution_name
FROM auth.users u
LEFT JOIN public.user_profiles p ON p.id = u.id
LEFT JOIN public.institutions i ON i.id = p.institution_id
ORDER BY u.email;

-- =============================================================================
-- 2) List institutions (use these IDs when setting institution_id below)
-- =============================================================================
SELECT id, name FROM public.institutions ORDER BY name;

-- =============================================================================
-- 3) EXAMPLE UPDATES: Set correct tier and institution for existing profiles
-- =============================================================================
-- Replace the placeholder UUIDs and user ids with real values from your (1) and (2) results.
-- Run one or more of these as needed.

-- Example: set one user as instructor at a specific institution
-- UPDATE public.user_profiles
-- SET account_tier = 'instructor',
--     institution_id = '<institution_uuid>',
--     is_admin = false,
--     is_super_admin = false,
--     approval_status = 'approved'
-- WHERE id = '<user_uuid>';

-- Example: set one user as admin at a specific institution
-- UPDATE public.user_profiles
-- SET account_tier = 'admin',
--     institution_id = '<institution_uuid>',
--     is_admin = true,
--     is_super_admin = false,
--     approval_status = 'approved'
-- WHERE id = '<user_uuid>';

-- Example: set one user as super_admin (institution_id can be null or your main org)
-- UPDATE public.user_profiles
-- SET account_tier = 'super_admin',
--     institution_id = '<institution_uuid>',  -- optional
--     is_admin = true,
--     is_super_admin = true,
--     approval_status = 'approved'
-- WHERE id = '<user_uuid>';

-- Example: fix all users at an institution to instructor (batch)
-- UPDATE public.user_profiles
-- SET account_tier = 'instructor',
--     institution_id = '<institution_uuid>',
--     is_admin = false,
--     is_super_admin = false,
--     approval_status = 'approved'
-- WHERE institution_id = '<institution_uuid>' AND (account_tier IS NULL OR account_tier = 'demo');

-- =============================================================================
-- 4) INSERT missing user_profiles rows (if a user has no row at all)
-- =============================================================================
-- If the diagnostic (1) shows users with NULL account_tier and no row, they may actually be missing
-- a user_profiles row. Some setups use a trigger on auth.users to create the row; if that didn’t run,
-- insert one. Replace <user_uuid> and <institution_uuid> with real values.

-- INSERT INTO public.user_profiles (
--   id,
--   account_tier,
--   institution_id,
--   is_admin,
--   is_super_admin,
--   approval_status,
--   full_name
-- )
-- VALUES (
--   '<user_uuid>',
--   'instructor',           -- or 'admin', 'super_admin'
--   '<institution_uuid>',   -- or NULL for super_admin if you prefer
--   false,                  -- true for admin/super_admin
--   false,                  -- true only for super_admin
--   'approved',
--   NULL                    -- optional; or set from auth.users.raw_user_meta_data
-- )
-- ON CONFLICT (id) DO UPDATE SET
--   account_tier = EXCLUDED.account_tier,
--   institution_id = EXCLUDED.institution_id,
--   is_admin = EXCLUDED.is_admin,
--   is_super_admin = EXCLUDED.is_super_admin,
--   approval_status = EXCLUDED.approval_status;

-- =============================================================================
-- 5) Optional: Ensure all existing profile rows have a non-demo tier
-- =============================================================================
-- Use with caution: only run if you want every user who has a profile to be at least instructor.
-- UPDATE public.user_profiles
-- SET account_tier = 'instructor',
--     is_admin = false,
--     is_super_admin = false
-- WHERE account_tier IS NULL OR account_tier = 'demo';
