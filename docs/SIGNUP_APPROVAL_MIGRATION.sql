-- Signup approval flow: run this in Supabase SQL Editor.
-- Requires: user_profiles table (from auth trigger or existing schema).

-- 1) Add columns to user_profiles (idempotent)
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS approval_status text DEFAULT 'approved'
    CHECK (approval_status IN ('approved', 'pending_approval', 'rejected'));

ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS requested_role text
    CHECK (requested_role IS NULL OR requested_role IN ('instructor', 'admin'));

COMMENT ON COLUMN user_profiles.approval_status IS 'approved = can use app; pending_approval = waiting for super admin; rejected = signup rejected';
COMMENT ON COLUMN user_profiles.requested_role IS 'For pending signups: requested role (instructor or admin). Set by super admin on approve.';

-- 2) Ensure existing rows are approved
UPDATE user_profiles SET approval_status = 'approved' WHERE approval_status IS NULL;

-- 3) users table: allow status 'pending_approval' (if you use status on users)
-- If your users table has a status column, ensure it accepts 'pending_approval'.
-- Example (run only if your schema has users.status):
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS users_status_check;
-- ALTER TABLE users ADD CONSTRAINT users_status_check CHECK (status IN ('active', 'pending_approval', 'rejected'));
