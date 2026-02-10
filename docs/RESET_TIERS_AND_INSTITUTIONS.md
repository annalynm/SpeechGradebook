# Resetting Account Tiers and Institutions

If **everyone sees the demo banner, SpeechGradebook default theme, and no tier-appropriate dashboards**, the app is treating all accounts as **demo** because it isn’t getting valid tier and institution data from the database.

## Why this happens

1. **Tier and institution** come from the **`user_profiles`** table: `account_tier`, `institution_id`, `is_admin`, `is_super_admin`.
2. On login, the app calls `loadUserTier()`, which:
   - Reads `user_profiles` for the current user (`id = auth.uid()`).
   - If the query **fails** (e.g. RLS, missing row) or **`account_tier` is null/empty**, it falls back to **`userTier = 'demo'`**.
3. When `userTier === 'demo'`:
   - The **demo banner** is shown.
   - **Theme** stays at the default (no institutional theme), because `loadInstitutionalTheme()` is only called when `currentUser.institution_id` is set from the profile.
   - **Dashboards** are the demo interface (no real instructor/admin/super_admin panels), because `routeToInterface()` only shows real dashboards for `instructor`, `admin`, or `super_admin`.

So: **fixing `user_profiles` so each user has the correct `account_tier` and `institution_id`** (and flags like `is_admin` / `is_super_admin`) restores the right tier, theme, and dashboards.

## What to fix in the database

- **`user_profiles.account_tier`** – One of: `'instructor'`, `'admin'`, `'super_admin'`. Never leave null for real users.
- **`user_profiles.institution_id`** – UUID of the row in **`institutions`** for that user’s institution. Required for institutional theme and (for admin/super_admin) scope.
- **`user_profiles.is_admin`** – `true` only for admins.
- **`user_profiles.is_super_admin`** – `true` only for super admins.
- **`user_profiles.approval_status`** – Should be `'approved'` for active users (otherwise they may see “pending approval” or be blocked).

If a user has **no row** in `user_profiles`, the app will always treat them as demo until a row is inserted with the correct tier and institution.

## Steps to reset

1. **Inspect current state**  
   Run the diagnostic query in **`docs/RESET_TIERS_AND_INSTITUTIONS.sql`** (in Supabase SQL Editor) to list all users and their current profile: tier, institution_id, is_admin, is_super_admin, approval_status. That shows who is missing a profile or has null/wrong tier or institution.

2. **List institutions**  
   Run the “List institutions” query in that same file to get `id` and `name` for each institution. You’ll need the correct `institution_id` (UUID) for each user when updating.

3. **Fix or create profiles**  
   - For users who **already have** a `user_profiles` row: run **UPDATE**s to set `account_tier`, `institution_id`, and (for admins) `is_admin` / `is_super_admin` to the correct values. Examples are in **`RESET_TIERS_AND_INSTITUTIONS.sql`**; replace the placeholder UUIDs and user IDs with your real values.
   - For users who **do not have** a row: **INSERT** a row into `user_profiles` with `id = auth.users.id`, `account_tier`, `institution_id`, and optionally `approval_status = 'approved'`, `is_admin`, `is_super_admin`. The SQL file includes an example; run it (or adapt it) with the correct user and institution IDs.

4. **Re-run after changes**  
   After saving changes in Supabase, have users **log out and log back in** (or refresh and log in again). The app will re-run `loadUserTier()`, read the updated profile, and then:
   - Remove the demo banner for non-demo tiers
   - Load the institutional theme when `institution_id` is set
   - Show the correct dashboards for instructor / admin / super_admin

## Theme and dashboards (no extra “reset”)

- **Theme:** Loaded from **`institution_themes`** using `institution_id` from `user_profiles`. Once `institution_id` is correct and `institution_themes` has a row for that institution, the app will apply the right theme automatically on next login.
- **Dashboards:** Built in the app based only on `userTier` (and `is_admin` / `is_super_admin`). There is no separate “dashboard tier” in the database to reset; fixing `account_tier` (and admin flags) is enough to restore the correct dashboards.

## If you use RLS on `user_profiles`

- Users must be able to **SELECT** their own row (`id = auth.uid()`). If they can’t, the profile fetch fails and the app falls back to demo.
- Super admins need to be able to **SELECT** and **UPDATE** all rows so they can fix tiers and institutions from the app or via SQL run as a privileged role.

See **`docs/SIGNUP_APPROVAL_RLS.sql`** for the intended RLS policies on `user_profiles`.
