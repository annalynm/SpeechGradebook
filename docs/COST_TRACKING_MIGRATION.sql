-- Cost Tracking Migration
-- Run this in Supabase SQL Editor
-- 
-- This migration creates the cost_tracking table to store evaluation costs
-- for monitoring and budgeting purposes.

-- ============================================
-- 1. COST TRACKING TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS cost_tracking (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id uuid REFERENCES evaluations(id) ON DELETE CASCADE,
  instructor_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  institution_id uuid REFERENCES institutions(id) ON DELETE SET NULL,
  
  -- Cost metrics
  gpu_seconds numeric(10, 3) NOT NULL,
  estimated_cost numeric(10, 6) NOT NULL,  -- USD
  actual_cost numeric(10, 6),  -- If available from provider
  
  -- Metadata
  provider text NOT NULL DEFAULT 'modal',  -- 'modal', 'qwen', etc.
  model_name text,
  file_size_mb numeric(10, 2),
  processing_time_seconds numeric(10, 3),
  
  -- Timestamps
  created_at timestamptz DEFAULT now()
);

-- ============================================
-- 2. INDEXES FOR EFFICIENT QUERIES
-- ============================================
CREATE INDEX IF NOT EXISTS cost_tracking_evaluation_id_idx ON cost_tracking(evaluation_id);
CREATE INDEX IF NOT EXISTS cost_tracking_instructor_id_idx ON cost_tracking(instructor_id);
CREATE INDEX IF NOT EXISTS cost_tracking_institution_id_idx ON cost_tracking(institution_id);
CREATE INDEX IF NOT EXISTS cost_tracking_created_at_idx ON cost_tracking(created_at);
CREATE INDEX IF NOT EXISTS cost_tracking_provider_idx ON cost_tracking(provider);

-- ============================================
-- 3. RLS POLICIES
-- ============================================
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;

-- SELECT: Instructors can see their own costs, admins can see institution costs, super admins see all
CREATE POLICY "cost_tracking_select_own" ON cost_tracking FOR SELECT
  USING (
    instructor_id = auth.uid()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND (is_admin = true OR is_super_admin = true)
    )
    OR EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- INSERT: Only backend/service role can insert (via API)
-- This is typically done server-side, so we allow authenticated users
-- but in practice, only the backend will insert
CREATE POLICY "cost_tracking_insert_authenticated" ON cost_tracking FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- UPDATE/DELETE: Only super admins can modify (for corrections)
CREATE POLICY "cost_tracking_update_super_admin" ON cost_tracking FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

CREATE POLICY "cost_tracking_delete_super_admin" ON cost_tracking FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- ============================================
-- 4. COMMENTS
-- ============================================
COMMENT ON TABLE cost_tracking IS 'Tracks GPU costs for each evaluation to monitor spending and optimize usage';
COMMENT ON COLUMN cost_tracking.gpu_seconds IS 'GPU compute time in seconds';
COMMENT ON COLUMN cost_tracking.estimated_cost IS 'Estimated cost in USD based on provider pricing';
COMMENT ON COLUMN cost_tracking.actual_cost IS 'Actual cost from provider billing (if available)';
COMMENT ON COLUMN cost_tracking.provider IS 'AI provider: modal, qwen, etc.';

-- ============================================
-- 5. HELPER VIEWS FOR REPORTING
-- ============================================

-- Monthly cost summary by institution
CREATE OR REPLACE VIEW cost_tracking_monthly_summary AS
SELECT 
  institution_id,
  DATE_TRUNC('month', created_at) AS month,
  COUNT(*) AS evaluation_count,
  SUM(estimated_cost) AS total_cost,
  AVG(estimated_cost) AS avg_cost_per_evaluation,
  SUM(gpu_seconds) AS total_gpu_seconds,
  AVG(processing_time_seconds) AS avg_processing_time
FROM cost_tracking
WHERE institution_id IS NOT NULL
GROUP BY institution_id, DATE_TRUNC('month', created_at)
ORDER BY month DESC, institution_id;

-- Cost by instructor (current month)
CREATE OR REPLACE VIEW cost_tracking_instructor_current_month AS
SELECT 
  instructor_id,
  COUNT(*) AS evaluation_count,
  SUM(estimated_cost) AS total_cost,
  AVG(estimated_cost) AS avg_cost_per_evaluation
FROM cost_tracking
WHERE instructor_id IS NOT NULL
  AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY instructor_id
ORDER BY total_cost DESC;

COMMENT ON VIEW cost_tracking_monthly_summary IS 'Monthly cost summary by institution for budgeting and reporting';
COMMENT ON VIEW cost_tracking_instructor_current_month IS 'Current month costs by instructor for monitoring';
