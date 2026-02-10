-- RLS policies for signup approval (Step 4).
-- Run this in Supabase → SQL Editor after running SIGNUP_APPROVAL_MIGRATION.sql.
--
-- Ensures:
-- (a) Users can read their own user_profiles row (so pending users see "Account pending approval").
-- (b) Super Admins can read and update all user_profiles (so they can approve/reject in the app).
--
-- IMPORTANT: Super-admin policies use a SECURITY DEFINER function so they do not query
-- user_profiles inside the policy (which would cause "infinite recursion detected in policy").

-- 0) Helper: returns true if current user is super admin (avoids RLS recursion)
CREATE OR REPLACE FUNCTION public.current_user_is_super_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
  SELECT COALESCE(
    (SELECT is_super_admin FROM public.user_profiles WHERE id = auth.uid()),
    false
  );
$$;

-- 1) Enable RLS on user_profiles if not already
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- 2) SELECT: allow read own row
DROP POLICY IF EXISTS "user_profiles_select_own" ON user_profiles;
CREATE POLICY "user_profiles_select_own"
  ON user_profiles FOR SELECT
  USING (id = auth.uid());

-- 3) SELECT: allow super admins to read all rows (for User management list + pending section)
DROP POLICY IF EXISTS "user_profiles_select_super_admin" ON user_profiles;
CREATE POLICY "user_profiles_select_super_admin"
  ON user_profiles FOR SELECT
  USING (public.current_user_is_super_admin());

-- 4) UPDATE: allow users to update their own row (e.g. full_name, consent)
DROP POLICY IF EXISTS "user_profiles_update_own" ON user_profiles;
CREATE POLICY "user_profiles_update_own"
  ON user_profiles FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- 5) UPDATE: allow super admins to update any row (approve/reject, tier, etc.)
DROP POLICY IF EXISTS "user_profiles_update_super_admin" ON user_profiles;
CREATE POLICY "user_profiles_update_super_admin"
  ON user_profiles FOR UPDATE
  USING (public.current_user_is_super_admin())
  WITH CHECK (true);

-- 6) INSERT: if your app or triggers insert user_profiles, ensure the creating user or service role can insert.
--    (Often a trigger on auth.users creates the row; that runs as the database owner, so RLS may not apply.)
--    If the client never inserts into user_profiles, you can skip INSERT policies.
