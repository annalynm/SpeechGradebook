-- Energy Tracking and Carbon Offset Donations
-- Run this in Supabase SQL Editor
-- 
-- This migration creates:
-- 1. energy_usage table: tracks energy consumption per evaluation
-- 2. carbon_offset_donations table: tracks user donations for carbon offsets
-- 3. RLS policies for proper access control

-- ============================================
-- 1. ENERGY USAGE TABLE
-- ============================================
-- Tracks energy consumption for each evaluation
CREATE TABLE IF NOT EXISTS energy_usage (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id uuid NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
  instructor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  institution_id uuid REFERENCES institutions(id) ON DELETE SET NULL,
  
  -- Provider information
  ai_provider text NOT NULL, -- 'qwen', 'gpt4o', 'gemini', 'claude', 'finetuned', 'demo'
  
  -- Energy metrics (in kWh)
  energy_kwh numeric(12, 6) NOT NULL DEFAULT 0,
  
  -- Carbon emissions (in kg CO2 equivalent)
  co2_kg numeric(12, 6) NOT NULL DEFAULT 0,
  
  -- Scope classification (for GHG Protocol)
  scope text NOT NULL DEFAULT 'scope_2', -- 'scope_1', 'scope_2', 'scope_3'
  scope_category text, -- e.g., 'cloud_compute', 'api_call', 'local_gpu'
  
  -- Provider-specific metadata
  provider_metadata jsonb DEFAULT '{}', -- e.g., {"model": "gpt-4o", "tokens": 5000, "region": "us-east-1"}
  
  -- File and processing metadata
  file_size_bytes bigint, -- Size of uploaded file
  processing_time_seconds numeric(10, 3), -- Time taken for evaluation
  video_duration_seconds numeric(10, 3), -- Duration of video/audio if available
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  
  -- Indexes
  CONSTRAINT energy_usage_evaluation_id_unique UNIQUE (evaluation_id)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS energy_usage_instructor_id_idx ON energy_usage(instructor_id);
CREATE INDEX IF NOT EXISTS energy_usage_institution_id_idx ON energy_usage(institution_id);
CREATE INDEX IF NOT EXISTS energy_usage_ai_provider_idx ON energy_usage(ai_provider);
CREATE INDEX IF NOT EXISTS energy_usage_created_at_idx ON energy_usage(created_at);
CREATE INDEX IF NOT EXISTS energy_usage_scope_idx ON energy_usage(scope);

COMMENT ON TABLE energy_usage IS 'Tracks energy consumption and carbon emissions for each evaluation';
COMMENT ON COLUMN energy_usage.energy_kwh IS 'Energy consumption in kilowatt-hours';
COMMENT ON COLUMN energy_usage.co2_kg IS 'Carbon dioxide equivalent emissions in kilograms';
COMMENT ON COLUMN energy_usage.scope IS 'GHG Protocol scope: scope_1 (direct), scope_2 (indirect from purchased energy), scope_3 (other indirect)';
COMMENT ON COLUMN energy_usage.scope_category IS 'Detailed category within scope (e.g., cloud_compute, api_call, local_gpu)';
COMMENT ON COLUMN energy_usage.provider_metadata IS 'Provider-specific data (model version, tokens, region, etc.)';

-- ============================================
-- 2. CARBON OFFSET DONATIONS TABLE
-- ============================================
-- Tracks donations made by users for carbon offsets
CREATE TABLE IF NOT EXISTS carbon_offset_donations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  institution_id uuid REFERENCES institutions(id) ON DELETE SET NULL,
  
  -- Donation details
  amount_usd numeric(10, 2) NOT NULL,
  donation_date date NOT NULL DEFAULT CURRENT_DATE,
  
  -- Offset calculation
  co2_offset_kg numeric(12, 6) NOT NULL, -- Amount of CO2 offset by this donation
  offset_rate_usd_per_ton numeric(10, 2), -- Rate used: USD per metric ton of CO2
  
  -- Donation recipient/organization
  recipient_organization text, -- e.g., 'Gold Standard', 'Verra', 'Cool Effect'
  recipient_project_id text, -- Project identifier if applicable
  
  -- Status
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'completed', 'cancelled')),
  
  -- Payment tracking (for tax purposes)
  payment_method text, -- 'round_up', 'direct_donation', 'subscription_addon'
  payment_transaction_id text, -- External payment processor transaction ID
  
  -- Tax/accounting fields (for owner)
  is_owner_collected boolean DEFAULT false, -- True if owner collected money and will make donation
  owner_donation_date date, -- Date when owner actually makes the donation
  owner_tax_documentation text, -- Reference to tax documentation
  
  -- Metadata
  notes text,
  metadata jsonb DEFAULT '{}',
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS carbon_offset_donations_user_id_idx ON carbon_offset_donations(user_id);
CREATE INDEX IF NOT EXISTS carbon_offset_donations_institution_id_idx ON carbon_offset_donations(institution_id);
CREATE INDEX IF NOT EXISTS carbon_offset_donations_donation_date_idx ON carbon_offset_donations(donation_date);
CREATE INDEX IF NOT EXISTS carbon_offset_donations_status_idx ON carbon_offset_donations(status);
CREATE INDEX IF NOT EXISTS carbon_offset_donations_owner_collected_idx ON carbon_offset_donations(is_owner_collected);

COMMENT ON TABLE carbon_offset_donations IS 'Tracks carbon offset donations from users';
COMMENT ON COLUMN carbon_offset_donations.co2_offset_kg IS 'Amount of CO2 offset in kilograms based on donation amount and offset rate';
COMMENT ON COLUMN carbon_offset_donations.is_owner_collected IS 'True if the platform owner collected the money and will make the donation themselves (for tax write-off)';
COMMENT ON COLUMN carbon_offset_donations.owner_tax_documentation IS 'Reference to tax documentation when owner makes the donation';

-- ============================================
-- 3. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS
ALTER TABLE energy_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE carbon_offset_donations ENABLE ROW LEVEL SECURITY;

-- Helper function to check if user is super admin (avoids RLS recursion)
-- (Reuse existing function if it exists, otherwise create it)
DO $func$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'current_user_is_super_admin') THEN
    CREATE OR REPLACE FUNCTION public.current_user_is_super_admin()
    RETURNS boolean
    LANGUAGE sql
    SECURITY DEFINER
    SET search_path = public
    STABLE
    AS $body$
      SELECT COALESCE(
        (SELECT is_super_admin FROM public.user_profiles WHERE id = auth.uid()),
        false
      );
    $body$;
  END IF;
END $func$;

-- Helper function to check if user is admin
CREATE OR REPLACE FUNCTION public.current_user_is_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
  SELECT COALESCE(
    (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()),
    false
  );
$$;

-- Helper function to get user's institution_id
CREATE OR REPLACE FUNCTION public.current_user_institution_id()
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
  SELECT institution_id FROM public.user_profiles WHERE id = auth.uid();
$$;

-- ENERGY_USAGE POLICIES

-- SELECT: Instructors can see their own energy usage
CREATE POLICY "energy_usage_select_own"
  ON energy_usage FOR SELECT
  USING (instructor_id = auth.uid());

-- SELECT: Admins can see energy usage for their institution
CREATE POLICY "energy_usage_select_institution"
  ON energy_usage FOR SELECT
  USING (
    public.current_user_is_admin() AND
    institution_id = public.current_user_institution_id()
  );

-- SELECT: Super admins can see all energy usage
CREATE POLICY "energy_usage_select_super_admin"
  ON energy_usage FOR SELECT
  USING (public.current_user_is_super_admin());

-- INSERT: Anyone can insert energy usage (system will insert after evaluation)
CREATE POLICY "energy_usage_insert_all"
  ON energy_usage FOR INSERT
  WITH CHECK (true);

-- UPDATE: Only super admins can update (for corrections)
CREATE POLICY "energy_usage_update_super_admin"
  ON energy_usage FOR UPDATE
  USING (public.current_user_is_super_admin())
  WITH CHECK (public.current_user_is_super_admin());

-- CARBON_OFFSET_DONATIONS POLICIES

-- SELECT: Users can see their own donations
CREATE POLICY "carbon_offset_donations_select_own"
  ON carbon_offset_donations FOR SELECT
  USING (user_id = auth.uid());

-- SELECT: Admins can see donations for their institution
CREATE POLICY "carbon_offset_donations_select_institution"
  ON carbon_offset_donations FOR SELECT
  USING (
    public.current_user_is_admin() AND
    institution_id = public.current_user_institution_id()
  );

-- SELECT: Super admins can see all donations
CREATE POLICY "carbon_offset_donations_select_super_admin"
  ON carbon_offset_donations FOR SELECT
  USING (public.current_user_is_super_admin());

-- INSERT: Users can create their own donations
CREATE POLICY "carbon_offset_donations_insert_own"
  ON carbon_offset_donations FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- UPDATE: Users can update their own pending donations
CREATE POLICY "carbon_offset_donations_update_own"
  ON carbon_offset_donations FOR UPDATE
  USING (user_id = auth.uid() AND status = 'pending')
  WITH CHECK (user_id = auth.uid());

-- UPDATE: Super admins can update any donation (for processing, owner collection, etc.)
CREATE POLICY "carbon_offset_donations_update_super_admin"
  ON carbon_offset_donations FOR UPDATE
  USING (public.current_user_is_super_admin())
  WITH CHECK (public.current_user_is_super_admin());

-- ============================================
-- 4. VIEWS FOR REPORTING
-- ============================================

-- View: Energy usage summary by instructor
CREATE OR REPLACE VIEW energy_usage_by_instructor AS
SELECT 
  eu.instructor_id,
  up.full_name as instructor_name,
  up.institution_id,
  i.name as institution_name,
  COUNT(*) as total_evaluations,
  SUM(eu.energy_kwh) as total_energy_kwh,
  SUM(eu.co2_kg) as total_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_1' THEN eu.co2_kg ELSE 0 END) as scope_1_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_2' THEN eu.co2_kg ELSE 0 END) as scope_2_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_3' THEN eu.co2_kg ELSE 0 END) as scope_3_co2_kg,
  AVG(eu.energy_kwh) as avg_energy_kwh_per_eval,
  AVG(eu.co2_kg) as avg_co2_kg_per_eval,
  MIN(eu.created_at) as first_evaluation_at,
  MAX(eu.created_at) as last_evaluation_at
FROM energy_usage eu
LEFT JOIN user_profiles up ON eu.instructor_id = up.id
LEFT JOIN institutions i ON eu.institution_id = i.id
GROUP BY eu.instructor_id, up.full_name, up.institution_id, i.name;

-- View: Energy usage summary by institution
CREATE OR REPLACE VIEW energy_usage_by_institution AS
SELECT 
  eu.institution_id,
  i.name as institution_name,
  COUNT(DISTINCT eu.instructor_id) as total_instructors,
  COUNT(*) as total_evaluations,
  SUM(eu.energy_kwh) as total_energy_kwh,
  SUM(eu.co2_kg) as total_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_1' THEN eu.co2_kg ELSE 0 END) as scope_1_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_2' THEN eu.co2_kg ELSE 0 END) as scope_2_co2_kg,
  SUM(CASE WHEN eu.scope = 'scope_3' THEN eu.co2_kg ELSE 0 END) as scope_3_co2_kg,
  AVG(eu.energy_kwh) as avg_energy_kwh_per_eval,
  AVG(eu.co2_kg) as avg_co2_kg_per_eval
FROM energy_usage eu
LEFT JOIN institutions i ON eu.institution_id = i.id
WHERE eu.institution_id IS NOT NULL
GROUP BY eu.institution_id, i.name;

-- View: Donations summary by user
CREATE OR REPLACE VIEW carbon_offset_donations_by_user AS
SELECT 
  cod.user_id,
  up.full_name as user_name,
  up.institution_id,
  i.name as institution_name,
  COUNT(*) as total_donations,
  SUM(cod.amount_usd) as total_donated_usd,
  SUM(cod.co2_offset_kg) as total_co2_offset_kg,
  SUM(cod.co2_offset_kg) / 1000.0 as total_co2_offset_tons,
  MIN(cod.donation_date) as first_donation_date,
  MAX(cod.donation_date) as last_donation_date
FROM carbon_offset_donations cod
LEFT JOIN user_profiles up ON cod.user_id = up.id
LEFT JOIN institutions i ON cod.institution_id = i.id
WHERE cod.status IN ('processed', 'completed')
GROUP BY cod.user_id, up.full_name, up.institution_id, i.name;

-- View: Net carbon impact (emissions - offsets) by user
CREATE OR REPLACE VIEW net_carbon_impact_by_user AS
SELECT 
  COALESCE(eu_summary.instructor_id, cod_summary.user_id) as user_id,
  COALESCE(eu_summary.instructor_name, cod_summary.user_name) as user_name,
  COALESCE(eu_summary.institution_id, cod_summary.institution_id) as institution_id,
  COALESCE(eu_summary.institution_name, cod_summary.institution_name) as institution_name,
  COALESCE(eu_summary.total_co2_kg, 0) as total_emissions_kg,
  COALESCE(cod_summary.total_co2_offset_kg, 0) as total_offsets_kg,
  COALESCE(eu_summary.total_co2_kg, 0) - COALESCE(cod_summary.total_co2_offset_kg, 0) as net_emissions_kg,
  CASE 
    WHEN COALESCE(eu_summary.total_co2_kg, 0) > 0 
    THEN (COALESCE(cod_summary.total_co2_offset_kg, 0) / eu_summary.total_co2_kg * 100)
    ELSE 0 
  END as offset_percentage
FROM energy_usage_by_instructor eu_summary
FULL OUTER JOIN carbon_offset_donations_by_user cod_summary 
  ON eu_summary.instructor_id = cod_summary.user_id;

-- ============================================
-- 5. FUNCTIONS FOR ENERGY CALCULATION
-- ============================================

-- Function to calculate energy and CO2 for an evaluation
-- This will be called from the application after an evaluation completes
CREATE OR REPLACE FUNCTION calculate_evaluation_energy(
  p_evaluation_id uuid,
  p_ai_provider text,
  p_file_size_bytes bigint DEFAULT NULL,
  p_processing_time_seconds numeric DEFAULT NULL,
  p_video_duration_seconds numeric DEFAULT NULL,
  p_provider_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  energy_kwh numeric,
  co2_kg numeric,
  scope text,
  scope_category text
) AS $$
DECLARE
  v_energy_kwh numeric;
  v_co2_kg numeric;
  v_scope text;
  v_scope_category text;
  v_tokens integer;
  v_model text;
BEGIN
  -- Default values
  v_energy_kwh := 0;
  v_co2_kg := 0;
  v_scope := 'scope_3';
  v_scope_category := 'api_call';
  
  -- Extract metadata
  v_tokens := COALESCE((p_provider_metadata->>'tokens')::integer, 0);
  v_model := COALESCE(p_provider_metadata->>'model', '');
  
  -- Calculate based on provider
  CASE p_ai_provider
    WHEN 'qwen' THEN
      -- Qwen (GPU-based, typically on Modal or cloud GPU)
      -- Estimate: ~0.01-0.03 kWh per evaluation (GPU compute)
      -- CO2: ~0.5 kg CO2/kWh (US grid average)
      v_energy_kwh := COALESCE(p_processing_time_seconds, 30) / 3600.0 * 0.5; -- Assume 0.5 kW average power
      v_co2_kg := v_energy_kwh * 0.5; -- 0.5 kg CO2/kWh
      v_scope := 'scope_2';
      v_scope_category := 'cloud_compute';
      
    WHEN 'gpt4o' THEN
      -- GPT-4o (OpenAI API)
      -- Estimate: ~0.001-0.005 kWh per 1K tokens
      -- CO2: ~0.4 kg CO2/kWh (OpenAI's grid mix)
      IF v_tokens > 0 THEN
        v_energy_kwh := (v_tokens / 1000.0) * 0.003;
      ELSE
        v_energy_kwh := 0.002; -- Default for typical evaluation
      END IF;
      v_co2_kg := v_energy_kwh * 0.4;
      v_scope := 'scope_3';
      v_scope_category := 'api_call';
      
    WHEN 'gemini' THEN
      -- Gemini (Google API)
      -- Estimate: Similar to GPT-4o
      IF v_tokens > 0 THEN
        v_energy_kwh := (v_tokens / 1000.0) * 0.003;
      ELSE
        v_energy_kwh := 0.002;
      END IF;
      v_co2_kg := v_energy_kwh * 0.4;
      v_scope := 'scope_3';
      v_scope_category := 'api_call';
      
    WHEN 'claude' THEN
      -- Claude (Anthropic API)
      -- Estimate: Similar to GPT-4o
      IF v_tokens > 0 THEN
        v_energy_kwh := (v_tokens / 1000.0) * 0.003;
      ELSE
        v_energy_kwh := 0.002;
      END IF;
      v_co2_kg := v_energy_kwh * 0.4;
      v_scope := 'scope_3';
      v_scope_category := 'api_call';
      
    WHEN 'finetuned' THEN
      -- Finetuned model (Mistral, local or cloud server)
      -- Estimate: ~0.005-0.01 kWh per evaluation
      v_energy_kwh := COALESCE(p_processing_time_seconds, 20) / 3600.0 * 0.3;
      v_co2_kg := v_energy_kwh * 0.5;
      v_scope := 'scope_2';
      v_scope_category := 'cloud_compute';
      
    WHEN 'demo' THEN
      -- Demo mode (no actual computation)
      v_energy_kwh := 0;
      v_co2_kg := 0;
      v_scope := 'scope_3';
      v_scope_category := 'local_compute';
      
    ELSE
      -- Unknown provider, use conservative estimate
      v_energy_kwh := 0.002;
      v_co2_kg := v_energy_kwh * 0.5;
      v_scope := 'scope_3';
      v_scope_category := 'api_call';
  END CASE;
  
  RETURN QUERY SELECT v_energy_kwh, v_co2_kg, v_scope, v_scope_category;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_evaluation_energy IS 'Calculates energy consumption and CO2 emissions for an evaluation based on provider and metadata';
