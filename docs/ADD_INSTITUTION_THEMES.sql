-- Institution Themes table and RLS for Speech Gradebook
-- Run in Supabase → SQL Editor. REQUIRED for themes to stick: without this migration,
-- theme customizer saves will fail and University of Tennessee institution theme will not load.
-- If institution_themes already exists, skip the CREATE TABLE and run only the RLS section.
--
-- Ensures:
-- (a) Admins and instructors can SELECT/INSERT/UPDATE themes for their own institution.
-- (b) Super Admins can manage themes for any institution.

-- =============================================================================
-- 1) Create institution_themes table (if not exists)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.institution_themes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL UNIQUE REFERENCES public.institutions(id) ON DELETE CASCADE,
  primary_color text DEFAULT '#1e3a5f',
  header_bg_color text DEFAULT '#142940',
  secondary_color text DEFAULT '#8b9dc3',
  text_primary text DEFAULT '#2c3e50',
  text_secondary text DEFAULT '#2c3e50',
  font_heading text,
  font_body text,
  logo_url text,
  custom_fonts jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- =============================================================================
-- 2) RLS policies
-- =============================================================================
-- Requires public.current_user_is_super_admin() from docs/SIGNUP_APPROVAL_RLS.sql
-- Run that file first if you haven't.

ALTER TABLE public.institution_themes ENABLE ROW LEVEL SECURITY;

-- SELECT: admins/instructors can read themes for their institution; super_admin reads all
DROP POLICY IF EXISTS "institution_themes_select_own_institution" ON public.institution_themes;
CREATE POLICY "institution_themes_select_own_institution"
  ON public.institution_themes FOR SELECT
  USING (
    public.current_user_is_super_admin()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND institution_id IS NOT NULL
    )
  );

-- INSERT: admins/instructors can insert themes for their institution; super_admin inserts any
DROP POLICY IF EXISTS "institution_themes_insert_own_institution" ON public.institution_themes;
CREATE POLICY "institution_themes_insert_own_institution"
  ON public.institution_themes FOR INSERT
  WITH CHECK (
    public.current_user_is_super_admin()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND institution_id IS NOT NULL
    )
  );

-- UPDATE: admins/instructors can update themes for their institution; super_admin updates any
DROP POLICY IF EXISTS "institution_themes_update_own_institution" ON public.institution_themes;
CREATE POLICY "institution_themes_update_own_institution"
  ON public.institution_themes FOR UPDATE
  USING (
    public.current_user_is_super_admin()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND institution_id IS NOT NULL
    )
  )
  WITH CHECK (
    public.current_user_is_super_admin()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND institution_id IS NOT NULL
    )
  );

-- =============================================================================
-- 3) Seed "University of Tennessee, Knoxville" theme for UT institution (optional)
-- =============================================================================
-- Ensures users at "University of Tennessee" institution get the same look as
-- the dropdown option "University of Tennessee, Knoxville": orange T logo,
-- dark grey header, orange accents, Montserrat/Source Sans 3.
INSERT INTO public.institution_themes (
  institution_id,
  primary_color,
  header_bg_color,
  secondary_color,
  text_primary,
  text_secondary,
  font_heading,
  font_body,
  logo_url,
  updated_at
)
SELECT
  i.id,
  '#FF8200',
  '#4B4B4B',
  '#1a73c5',
  '#4B4B4B',
  '#4B4B4B',
  '''Montserrat'', sans-serif',
  '''Source Sans 3'', -apple-system, sans-serif',
  'assets/utk-logo.png',
  now()
FROM public.institutions i
WHERE i.name ILIKE '%Tennessee%'
ON CONFLICT (institution_id) DO UPDATE SET
  primary_color = EXCLUDED.primary_color,
  header_bg_color = EXCLUDED.header_bg_color,
  secondary_color = EXCLUDED.secondary_color,
  text_primary = EXCLUDED.text_primary,
  text_secondary = EXCLUDED.text_secondary,
  font_heading = EXCLUDED.font_heading,
  font_body = EXCLUDED.font_body,
  logo_url = EXCLUDED.logo_url,
  updated_at = EXCLUDED.updated_at;
