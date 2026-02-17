-- Backfill Energy Data for Historical Evaluations
-- Run this in Supabase SQL Editor to calculate energy usage for past evaluations
--
-- This script:
-- 1. Finds all evaluations that don't have energy_usage records
-- 2. Calculates energy based on ai_provider and available metadata
-- 3. Inserts energy_usage records for historical data
--
-- Note: This uses estimates since we don't have exact processing times or tokens
-- for historical evaluations. The estimates are conservative and based on
-- typical evaluation characteristics.

-- ============================================
-- BACKFILL FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION backfill_energy_usage_for_evaluation(
  p_evaluation_id uuid
)
RETURNS void AS $$
DECLARE
  v_eval_record RECORD;
  v_energy_record RECORD;
  v_has_energy BOOLEAN;
BEGIN
  -- Check if energy record already exists
  SELECT EXISTS(SELECT 1 FROM energy_usage WHERE evaluation_id = p_evaluation_id) INTO v_has_energy;
  IF v_has_energy THEN
    RETURN; -- Skip if already has energy data
  END IF;
  
  -- Get evaluation details
  SELECT 
    e.id,
    e.instructor_id,
    e.ai_provider,
    e.created_at,
    up.institution_id,
    e.video_url,
    e.audio_url,
    e.transcript
  INTO v_eval_record
  FROM evaluations e
  LEFT JOIN user_profiles up ON e.instructor_id = up.id
  WHERE e.id = p_evaluation_id;
  
  IF NOT FOUND THEN
    RETURN; -- Evaluation doesn't exist
  END IF;
  
  -- Calculate energy using the existing function
  -- Use default estimates since we don't have processing time for historical data
  SELECT * INTO v_energy_record
  FROM calculate_evaluation_energy(
    p_evaluation_id := p_evaluation_id,
    p_ai_provider := COALESCE(v_eval_record.ai_provider, 'unknown'),
    p_file_size_bytes := NULL, -- Unknown for historical
    p_processing_time_seconds := NULL, -- Unknown for historical
    p_video_duration_seconds := NULL, -- Unknown for historical
    p_provider_metadata := '{}'::jsonb -- No metadata for historical
  );
  
  -- Insert energy usage record
  INSERT INTO energy_usage (
    evaluation_id,
    instructor_id,
    institution_id,
    ai_provider,
    energy_kwh,
    co2_kg,
    scope,
    scope_category,
    provider_metadata,
    file_size_bytes,
    processing_time_seconds,
    video_duration_seconds,
    created_at
  ) VALUES (
    v_eval_record.id,
    v_eval_record.instructor_id,
    v_eval_record.institution_id,
    COALESCE(v_eval_record.ai_provider, 'unknown'),
    v_energy_record.energy_kwh,
    v_energy_record.co2_kg,
    v_energy_record.scope,
    v_energy_record.scope_category,
    '{}'::jsonb,
    NULL,
    NULL,
    NULL,
    v_eval_record.created_at -- Use evaluation's original created_at
  )
  ON CONFLICT (evaluation_id) DO NOTHING; -- Skip if somehow already exists
  
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- BACKFILL ALL HISTORICAL EVALUATIONS
-- ============================================

-- This will process all evaluations that don't have energy_usage records
-- Run this to backfill all historical data at once
DO $$
DECLARE
  v_eval_id uuid;
  v_count integer := 0;
  v_total integer;
BEGIN
  -- Count evaluations without energy data
  SELECT COUNT(*) INTO v_total
  FROM evaluations e
  WHERE NOT EXISTS (
    SELECT 1 FROM energy_usage eu WHERE eu.evaluation_id = e.id
  );
  
  RAISE NOTICE 'Found % evaluations without energy data. Starting backfill...', v_total;
  
  -- Process each evaluation
  FOR v_eval_id IN 
    SELECT e.id
    FROM evaluations e
    WHERE NOT EXISTS (
      SELECT 1 FROM energy_usage eu WHERE eu.evaluation_id = e.id
    )
    ORDER BY e.created_at ASC -- Process oldest first
  LOOP
    BEGIN
      PERFORM backfill_energy_usage_for_evaluation(v_eval_id);
      v_count := v_count + 1;
      
      -- Progress update every 100 records
      IF v_count % 100 = 0 THEN
        RAISE NOTICE 'Processed % of % evaluations...', v_count, v_total;
      END IF;
    EXCEPTION
      WHEN OTHERS THEN
        RAISE WARNING 'Error processing evaluation %: %', v_eval_id, SQLERRM;
        -- Continue with next evaluation
    END;
  END LOOP;
  
  RAISE NOTICE 'Backfill complete! Processed % evaluations.', v_count;
END $$;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check how many evaluations now have energy data
-- SELECT 
--   COUNT(*) as total_evaluations,
--   COUNT(eu.id) as evaluations_with_energy,
--   COUNT(*) - COUNT(eu.id) as missing_energy
-- FROM evaluations e
-- LEFT JOIN energy_usage eu ON e.id = eu.evaluation_id;

-- View summary of backfilled data
-- SELECT 
--   ai_provider,
--   COUNT(*) as count,
--   SUM(energy_kwh) as total_energy_kwh,
--   SUM(co2_kg) as total_co2_kg,
--   AVG(energy_kwh) as avg_energy_kwh
-- FROM energy_usage
-- GROUP BY ai_provider
-- ORDER BY count DESC;
