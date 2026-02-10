-- Fix: "infinite recursion detected in policy for relation user_profiles"
--
-- The super_admin SELECT and UPDATE policies were checking is_super_admin by querying
-- user_profiles inside the policy. That triggers RLS on user_profiles again → infinite recursion.
--
-- Solution: a SECURITY DEFINER function that reads user_profiles with owner privileges
-- (bypassing RLS), so the policy only calls the function and does not query user_profiles itself.
--
-- Run this in Supabase → SQL Editor. Then re-run SIGNUP_APPROVAL_RLS.sql (or just the policy
-- parts) using the helper function, or apply the policy changes below.

-- 1) Create a function that returns whether the current user is a super admin.
--    It runs with definer rights so it does not trigger RLS when reading user_profiles.
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

COMMENT ON FUNCTION public.current_user_is_super_admin() IS 'Used by RLS on user_profiles to avoid recursion; returns true if auth.uid() has is_super_admin in user_profiles.';

-- 2) Drop the policies that cause recursion
DROP POLICY IF EXISTS "user_profiles_select_super_admin" ON user_profiles;
DROP POLICY IF EXISTS "user_profiles_update_super_admin" ON user_profiles;

-- 3) Recreate them using the function instead of a subquery on user_profiles
CREATE POLICY "user_profiles_select_super_admin"
  ON user_profiles FOR SELECT
  USING (public.current_user_is_super_admin());

CREATE POLICY "user_profiles_update_super_admin"
  ON user_profiles FOR UPDATE
  USING (public.current_user_is_super_admin())
  WITH CHECK (true);
