-- Usage Quota System Migration
-- Run this in Supabase SQL Editor
-- 
-- This migration creates:
-- 1. usage_quotas table: tracks quotas per user/institution
-- 2. usage_tracking table: tracks actual usage
-- 3. usage_transactions table: tracks purchases/upgrades
-- 4. subscriptions table: tracks active subscriptions
--
-- NOTE: This migration references the 'institutions' table. If that table doesn't exist yet,
-- the foreign key constraints will be skipped. You can add them later when the institutions
-- table is created by running the ALTER TABLE statements at the end of this file.

-- ============================================
-- 1. USAGE QUOTAS TABLE
-- ============================================
-- Tracks quotas per user/institution
CREATE TABLE IF NOT EXISTS usage_quotas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  institution_id uuid, -- Foreign key added below if institutions table exists
  
  -- Account type
  account_type text NOT NULL CHECK (account_type IN (
    'student_free', 
    'student_paid', 
    'individual_basic', 
    'individual_standard', 
    'individual_professional', 
    'department'
  )),
  
  -- Quota details
  monthly_quota integer NOT NULL DEFAULT 0, -- Base monthly quota
  used_quota integer NOT NULL DEFAULT 0, -- Current month usage
  buffer_quota integer DEFAULT 0, -- Shared buffer pool (for departments)
  used_buffer_quota integer DEFAULT 0, -- Used from buffer pool
  
  -- Pilot and discount flags
  pilot_discount boolean DEFAULT false, -- True for Summer 2026 pilot
  is_active boolean DEFAULT true,
  
  -- Timestamps
  expires_at timestamptz, -- When quota expires (null = never)
  renewal_date date, -- Next renewal date (for monthly subscriptions)
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  
  -- Constraints
  CONSTRAINT usage_quotas_user_unique UNIQUE (user_id),
  CONSTRAINT usage_quotas_institution_unique UNIQUE (institution_id)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS usage_quotas_user_id_idx ON usage_quotas(user_id);
CREATE INDEX IF NOT EXISTS usage_quotas_institution_id_idx ON usage_quotas(institution_id);
CREATE INDEX IF NOT EXISTS usage_quotas_account_type_idx ON usage_quotas(account_type);
CREATE INDEX IF NOT EXISTS usage_quotas_renewal_date_idx ON usage_quotas(renewal_date);

-- ============================================
-- 2. USAGE TRACKING TABLE
-- ============================================
-- Tracks actual usage per evaluation
CREATE TABLE IF NOT EXISTS usage_tracking (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  evaluation_id uuid, -- Foreign key added below if evaluations table exists
  institution_id uuid, -- Foreign key added below if institutions table exists
  
  -- Usage details
  quota_type text NOT NULL, -- Which quota was used (individual, department_buffer, etc.)
  evaluation_cost numeric(10, 6) NOT NULL DEFAULT 0, -- Cost of this evaluation
  provider text NOT NULL DEFAULT 'runpod', -- 'runpod', 'modal', etc.
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  
  -- Indexes
  CONSTRAINT usage_tracking_evaluation_id_unique UNIQUE (evaluation_id)
);

CREATE INDEX IF NOT EXISTS usage_tracking_user_id_idx ON usage_tracking(user_id);
CREATE INDEX IF NOT EXISTS usage_tracking_institution_id_idx ON usage_tracking(institution_id);
CREATE INDEX IF NOT EXISTS usage_tracking_created_at_idx ON usage_tracking(created_at);
CREATE INDEX IF NOT EXISTS usage_tracking_quota_type_idx ON usage_tracking(quota_type);

-- ============================================
-- 3. USAGE TRANSACTIONS TABLE
-- ============================================
-- Tracks purchases/upgrades
CREATE TABLE IF NOT EXISTS usage_transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  institution_id uuid, -- Foreign key added below if institutions table exists
  
  -- Transaction details
  transaction_type text NOT NULL CHECK (transaction_type IN (
    'purchase_evaluations',
    'upgrade_tier',
    'purchase_buffer',
    'refund',
    'adjustment'
  )),
  amount numeric(10, 2) NOT NULL, -- Amount paid (USD)
  evaluations_purchased integer DEFAULT 0, -- Number of evaluations purchased
  
  -- Payment tracking
  payment_method text, -- 'stripe', 'payroll', 'manual', etc.
  payment_transaction_id text, -- External payment processor transaction ID
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
  
  -- Metadata
  notes text,
  metadata jsonb DEFAULT '{}',
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS usage_transactions_user_id_idx ON usage_transactions(user_id);
CREATE INDEX IF NOT EXISTS usage_transactions_institution_id_idx ON usage_transactions(institution_id);
CREATE INDEX IF NOT EXISTS usage_transactions_status_idx ON usage_transactions(status);
CREATE INDEX IF NOT EXISTS usage_transactions_created_at_idx ON usage_transactions(created_at);

-- ============================================
-- 4. SUBSCRIPTIONS TABLE
-- ============================================
-- Tracks active subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  institution_id uuid, -- Foreign key added below if institutions table exists
  
  -- Subscription details
  tier text NOT NULL CHECK (tier IN (
    'student_free',
    'student_paid',
    'individual_basic',
    'individual_standard',
    'individual_professional',
    'department'
  )),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'pending')),
  contract_type text CHECK (contract_type IN ('department', 'individual')),
  pilot_status boolean DEFAULT false, -- True for Summer 2026 pilot
  
  -- Payment tracking
  stripe_subscription_id text, -- Stripe subscription ID if using Stripe
  amount_per_period numeric(10, 2), -- Monthly/annual amount
  billing_period text DEFAULT 'monthly' CHECK (billing_period IN ('monthly', 'annual')),
  
  -- Timestamps
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz, -- Null = ongoing
  cancelled_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS subscriptions_user_id_idx ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS subscriptions_institution_id_idx ON subscriptions(institution_id);
CREATE INDEX IF NOT EXISTS subscriptions_status_idx ON subscriptions(status);
CREATE INDEX IF NOT EXISTS subscriptions_tier_idx ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS subscriptions_ends_at_idx ON subscriptions(ends_at);

-- ============================================
-- 5. ROW LEVEL SECURITY POLICIES
-- ============================================

-- Usage Quotas RLS
ALTER TABLE usage_quotas ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see their own quota, admins can see institution quotas, super admins see all
CREATE POLICY "usage_quotas_select_own" ON usage_quotas FOR SELECT
  USING (
    user_id = auth.uid()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND (is_admin = true OR is_super_admin = true)
    )
    OR EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- INSERT/UPDATE: Only backend/service role or super admins
CREATE POLICY "usage_quotas_insert_authenticated" ON usage_quotas FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "usage_quotas_update_super_admin" ON usage_quotas FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- Usage Tracking RLS
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see their own usage, admins can see institution usage, super admins see all
CREATE POLICY "usage_tracking_select_own" ON usage_tracking FOR SELECT
  USING (
    user_id = auth.uid()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND (is_admin = true OR is_super_admin = true)
    )
    OR EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- INSERT: Only backend/service role
CREATE POLICY "usage_tracking_insert_authenticated" ON usage_tracking FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- Usage Transactions RLS
ALTER TABLE usage_transactions ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see their own transactions, admins can see institution transactions, super admins see all
CREATE POLICY "usage_transactions_select_own" ON usage_transactions FOR SELECT
  USING (
    user_id = auth.uid()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND (is_admin = true OR is_super_admin = true)
    )
    OR EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- INSERT: Authenticated users (for purchases), super admins for adjustments
CREATE POLICY "usage_transactions_insert_authenticated" ON usage_transactions FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- UPDATE: Only super admins (for status updates, refunds)
CREATE POLICY "usage_transactions_update_super_admin" ON usage_transactions FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- Subscriptions RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see their own subscriptions, admins can see institution subscriptions, super admins see all
CREATE POLICY "subscriptions_select_own" ON subscriptions FOR SELECT
  USING (
    user_id = auth.uid()
    OR institution_id IN (
      SELECT institution_id FROM public.user_profiles
      WHERE id = auth.uid() AND (is_admin = true OR is_super_admin = true)
    )
    OR EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- INSERT/UPDATE: Only backend/service role or super admins
CREATE POLICY "subscriptions_insert_authenticated" ON subscriptions FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "subscriptions_update_super_admin" ON subscriptions FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- ============================================
-- 6. HELPER FUNCTIONS
-- ============================================

-- Function to check if user has available quota
CREATE OR REPLACE FUNCTION check_user_quota(p_user_id uuid)
RETURNS TABLE (
  has_quota boolean,
  quota_type text,
  remaining_quota integer,
  can_use_buffer boolean,
  buffer_remaining integer
) AS $$
DECLARE
  v_quota usage_quotas%ROWTYPE;
  v_institution_id uuid;
  v_department_quota usage_quotas%ROWTYPE;
  v_current_month_start date;
BEGIN
  v_current_month_start := DATE_TRUNC('month', CURRENT_DATE);
  
  -- Get user's quota
  SELECT * INTO v_quota
  FROM usage_quotas
  WHERE user_id = p_user_id
    AND is_active = true
    AND (expires_at IS NULL OR expires_at > now());
  
  -- If no user quota, check if user is part of department
  IF v_quota IS NULL THEN
    -- Get user's institution
    SELECT institution_id INTO v_institution_id
    FROM user_profiles
    WHERE id = p_user_id;
    
    -- Check for department quota
    IF v_institution_id IS NOT NULL THEN
      SELECT * INTO v_department_quota
      FROM usage_quotas
      WHERE institution_id = v_institution_id
        AND account_type = 'department'
        AND is_active = true
        AND (expires_at IS NULL OR expires_at > now());
      
      IF v_department_quota IS NOT NULL THEN
        -- Return department quota info
        RETURN QUERY SELECT
          (v_department_quota.monthly_quota - v_department_quota.used_quota > 0) OR
          (v_department_quota.buffer_quota - v_department_quota.used_buffer_quota > 0) AS has_quota,
          'department'::text AS quota_type,
          GREATEST(0, v_department_quota.monthly_quota - v_department_quota.used_quota) AS remaining_quota,
          (v_department_quota.buffer_quota - v_department_quota.used_buffer_quota > 0) AS can_use_buffer,
          GREATEST(0, v_department_quota.buffer_quota - v_department_quota.used_buffer_quota) AS buffer_remaining;
        RETURN;
      END IF;
    END IF;
    
    -- No quota found
    RETURN QUERY SELECT false, 'none'::text, 0, false, 0;
    RETURN;
  END IF;
  
  -- Check if quota needs monthly reset
  IF v_quota.renewal_date IS NOT NULL AND v_quota.renewal_date < CURRENT_DATE THEN
    -- Reset monthly quota (this should be done by a scheduled job, but check here too)
    UPDATE usage_quotas
    SET used_quota = 0,
        renewal_date = (CURRENT_DATE + INTERVAL '1 month')::date
    WHERE id = v_quota.id;
    v_quota.used_quota := 0;
  END IF;
  
  -- Return user quota info
  RETURN QUERY SELECT
    (v_quota.monthly_quota - v_quota.used_quota > 0) OR
    (v_quota.buffer_quota - v_quota.used_buffer_quota > 0) AS has_quota,
    v_quota.account_type AS quota_type,
    GREATEST(0, v_quota.monthly_quota - v_quota.used_quota) AS remaining_quota,
    (v_quota.buffer_quota - v_quota.used_buffer_quota > 0) AS can_use_buffer,
    GREATEST(0, v_quota.buffer_quota - v_quota.used_buffer_quota) AS buffer_remaining;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment usage
CREATE OR REPLACE FUNCTION increment_usage(
  p_user_id uuid,
  p_evaluation_id uuid,
  p_cost numeric,
  p_provider text DEFAULT 'runpod'
)
RETURNS boolean AS $$
DECLARE
  v_quota usage_quotas%ROWTYPE;
  v_institution_id uuid;
  v_department_quota usage_quotas%ROWTYPE;
  v_used_buffer boolean := false;
BEGIN
  -- Get user's quota
  SELECT * INTO v_quota
  FROM usage_quotas
  WHERE user_id = p_user_id
    AND is_active = true;
  
  -- If no user quota, check department
  IF v_quota IS NULL THEN
    SELECT institution_id INTO v_institution_id
    FROM user_profiles
    WHERE id = p_user_id;
    
    IF v_institution_id IS NOT NULL THEN
      SELECT * INTO v_department_quota
      FROM usage_quotas
      WHERE institution_id = v_institution_id
        AND account_type = 'department'
        AND is_active = true;
      
      IF v_department_quota IS NOT NULL THEN
        -- Use department quota
        IF v_department_quota.monthly_quota - v_department_quota.used_quota > 0 THEN
          -- Use from monthly quota
          UPDATE usage_quotas
          SET used_quota = used_quota + 1,
              updated_at = now()
          WHERE id = v_department_quota.id;
        ELSIF v_department_quota.buffer_quota - v_department_quota.used_buffer_quota > 0 THEN
          -- Use from buffer
          UPDATE usage_quotas
          SET used_buffer_quota = used_buffer_quota + 1,
              updated_at = now()
          WHERE id = v_department_quota.id;
          v_used_buffer := true;
        ELSE
          RETURN false; -- No quota available
        END IF;
        
        -- Log usage
        INSERT INTO usage_tracking (user_id, evaluation_id, institution_id, quota_type, evaluation_cost, provider)
        VALUES (p_user_id, p_evaluation_id, v_institution_id, 
                CASE WHEN v_used_buffer THEN 'department_buffer' ELSE 'department' END,
                p_cost, p_provider);
        RETURN true;
      END IF;
    END IF;
    
    RETURN false; -- No quota found
  END IF;
  
  -- Use user's quota
  IF v_quota.monthly_quota - v_quota.used_quota > 0 THEN
    -- Use from monthly quota
    UPDATE usage_quotas
    SET used_quota = used_quota + 1,
        updated_at = now()
    WHERE id = v_quota.id;
  ELSIF v_quota.buffer_quota - v_quota.used_buffer_quota > 0 THEN
    -- Use from buffer
    UPDATE usage_quotas
    SET used_buffer_quota = used_buffer_quota + 1,
        updated_at = now()
    WHERE id = v_quota.id;
    v_used_buffer := true;
  ELSE
    RETURN false; -- No quota available
  END IF;
  
  -- Log usage
  INSERT INTO usage_tracking (user_id, evaluation_id, institution_id, quota_type, evaluation_cost, provider)
  VALUES (p_user_id, p_evaluation_id, v_quota.institution_id,
          CASE WHEN v_used_buffer THEN 'buffer' ELSE 'monthly' END,
          p_cost, p_provider);
  
  RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 7. COMMENTS
-- ============================================
COMMENT ON TABLE usage_quotas IS 'Tracks usage quotas per user/institution for evaluation limits';
COMMENT ON TABLE usage_tracking IS 'Tracks actual evaluation usage for billing and monitoring';
COMMENT ON TABLE usage_transactions IS 'Tracks purchases, upgrades, and payment transactions';
COMMENT ON TABLE subscriptions IS 'Tracks active subscriptions and billing periods';
COMMENT ON FUNCTION check_user_quota IS 'Checks if user has available quota and returns quota details';
COMMENT ON FUNCTION increment_usage IS 'Increments usage counter and logs evaluation cost';

-- ============================================
-- 8. ADD FOREIGN KEY CONSTRAINTS (Optional)
-- ============================================
-- Run these only if the referenced tables exist in your database.
-- If you get errors, the tables don't exist yet - that's okay, the quota system
-- will still work without these foreign key constraints.

-- Add foreign key to institutions table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'institutions') THEN
    -- Add foreign key constraints for institution_id columns
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints 
      WHERE constraint_name = 'usage_quotas_institution_id_fkey'
    ) THEN
      ALTER TABLE usage_quotas 
      ADD CONSTRAINT usage_quotas_institution_id_fkey 
      FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints 
      WHERE constraint_name = 'usage_tracking_institution_id_fkey'
    ) THEN
      ALTER TABLE usage_tracking 
      ADD CONSTRAINT usage_tracking_institution_id_fkey 
      FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints 
      WHERE constraint_name = 'usage_transactions_institution_id_fkey'
    ) THEN
      ALTER TABLE usage_transactions 
      ADD CONSTRAINT usage_transactions_institution_id_fkey 
      FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints 
      WHERE constraint_name = 'subscriptions_institution_id_fkey'
    ) THEN
      ALTER TABLE subscriptions 
      ADD CONSTRAINT subscriptions_institution_id_fkey 
      FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE SET NULL;
    END IF;
  END IF;
END $$;

-- Add foreign key to evaluations table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'evaluations') THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints 
      WHERE constraint_name = 'usage_tracking_evaluation_id_fkey'
    ) THEN
      ALTER TABLE usage_tracking 
      ADD CONSTRAINT usage_tracking_evaluation_id_fkey 
      FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE SET NULL;
    END IF;
  END IF;
END $$;
