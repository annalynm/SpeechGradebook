# Migrate Production Database to Development

This guide helps you migrate all content (schema and data) from your production Supabase database to your development database.

## ⚠️ Important Considerations

**Before migrating:**

1. **Data Privacy**: Production data may contain real user information. Consider:
   - Anonymizing sensitive data before migration
   - Only migrating test/sample data
   - Using schema-only migration for a clean dev environment

2. **What to Migrate:**
   - **Schema**: Tables, functions, triggers, RLS policies, indexes (always needed)
   - **Data**: User data, evaluations, courses (optional - depends on your needs)

3. **Migration Order**: Run migrations in the correct order to avoid foreign key errors

## Method 1: Complete Migration with pg_dump (Recommended)

This method exports everything from production and imports it to development.

### Step 1: Export from Production

1. **Get Production Database Connection String:**
   - Go to **Production Supabase Dashboard**
   - Navigate to **Settings** → **Database**
   - Under **Connection string**, select **URI**
   - Copy the connection string (looks like: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`)
   - Replace `[PASSWORD]` with your actual database password

2. **Export Complete Database (Schema + Data):**
   ```bash
   # Export everything
   pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
     --no-owner \
     --no-acl \
     -f production_export.sql
   ```

3. **Or Export Schema Only (No Data):**
   ```bash
   # Export schema only (recommended for clean dev environment)
   pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
     --schema-only \
     --no-owner \
     --no-acl \
     -f production_schema_only.sql
   ```

4. **Or Export Specific Tables with Data:**
   ```bash
   # Export specific tables with data
   pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
     --no-owner \
     --no-acl \
     --table=public.institutions \
     --table=public.user_profiles \
     --table=public.courses \
     -f production_selected_tables.sql
   ```

### Step 2: Import to Development

1. **Get Development Database Connection String:**
   - Go to **Development Supabase Dashboard**
   - Navigate to **Settings** → **Database**
   - Under **Connection string**, select **URI**
   - Copy the connection string

2. **Import the Export File:**
   ```bash
   # Import complete export
   psql "postgresql://postgres:[PASSWORD]@[DEV-HOST]:5432/postgres" \
     -f production_export.sql
   ```

   **Or use Supabase SQL Editor:**
   - Open the exported SQL file
   - Copy its contents
   - Go to **Development Supabase** → **SQL Editor**
   - Paste and run

### Step 3: Verify Migration

1. Check that all tables exist:
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   ORDER BY table_name;
   ```

2. Check table row counts:
   ```sql
   SELECT 
     schemaname,
     tablename,
     n_live_tup as row_count
   FROM pg_stat_user_tables
   ORDER BY tablename;
   ```

3. Test RLS policies:
   - Try logging in with a test user
   - Verify data access works correctly

## Method 2: Run All Migration Files (Schema Only)

If you have all your migration files in `docs/*.sql`, you can run them in order:

### Step 1: List Migration Files in Order

Run these migrations in order (check file creation dates or dependencies):

1. Core tables (if they exist):
   - `SIGNUP_APPROVAL_MIGRATION.sql`
   - `ADD_INSTITUTION_THEMES.sql`
   - `ADD_TEXTBOOK_RAG.sql`
   - `COST_TRACKING_MIGRATION.sql`
   - `ENERGY_TRACKING_AND_DONATIONS.sql`
   - `USAGE_QUOTA_SYSTEM.sql` (the one we just created)

2. Additional migrations:
   - `ADD_RUBRIC_DESCRIPTION_AND_COURSE_IDS.sql`
   - `ADD_RUBRIC_EXAMPLE_VIDEOS.sql`
   - Any other migration files

### Step 2: Run Migrations in Development

1. Go to **Development Supabase** → **SQL Editor**
2. For each migration file:
   - Open the file from `docs/`
   - Copy its contents
   - Paste into SQL Editor
   - Run the query
   - Verify no errors

### Step 3: Copy Data (Optional)

If you want to copy specific data:

```sql
-- Example: Copy institutions
INSERT INTO institutions (id, name, created_at)
SELECT id, name, created_at
FROM production_institutions; -- You'd need to set up a connection

-- Or manually insert test data
INSERT INTO institutions (name) VALUES ('Test University');
```

## Method 3: Using Supabase CLI (Advanced)

### Step 1: Install Supabase CLI

```bash
npm install -g supabase
# Or: brew install supabase/tap/supabase
```

### Step 2: Export from Production

```bash
# Link to production project
supabase link --project-ref your-production-project-ref

# Export database
supabase db dump -f production_export.sql
```

### Step 3: Import to Development

```bash
# Link to development project
supabase link --project-ref your-dev-project-ref

# Import (WARNING: This will reset the database)
supabase db reset

# Or apply the dump
psql "postgresql://postgres:[PASSWORD]@[DEV-HOST]:5432/postgres" \
  -f production_export.sql
```

## Method 4: Manual Migration via Supabase Dashboard

### Step 1: Export Schema from Production

1. Go to **Production Supabase** → **SQL Editor**
2. Run this query to get all table structures:
   ```sql
   SELECT 
     'CREATE TABLE IF NOT EXISTS ' || table_name || ' (' ||
     string_agg(
       column_name || ' ' || 
       data_type || 
       CASE 
         WHEN character_maximum_length IS NOT NULL 
         THEN '(' || character_maximum_length || ')'
         ELSE ''
       END ||
       CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
       ', '
     ) || ');'
   FROM information_schema.columns
   WHERE table_schema = 'public'
   GROUP BY table_name;
   ```

3. Copy the results

### Step 2: Import to Development

1. Go to **Development Supabase** → **SQL Editor**
2. Paste and run the CREATE TABLE statements
3. Run all your migration files from `docs/*.sql` to add functions, RLS policies, etc.

## Recommended Migration Order

If using migration files, run them in this order:

1. **Core Infrastructure:**
   - `SIGNUP_APPROVAL_MIGRATION.sql` (creates user_profiles structure)
   - `SIGNUP_APPROVAL_RLS.sql` (RLS policies)

2. **Institutions & Themes:**
   - `ADD_INSTITUTION_THEMES.sql` (requires institutions table)

3. **Features:**
   - `ADD_TEXTBOOK_RAG.sql` (textbook RAG system)
   - `COST_TRACKING_MIGRATION.sql` (cost tracking)
   - `ENERGY_TRACKING_AND_DONATIONS.sql` (energy tracking)
   - `USAGE_QUOTA_SYSTEM.sql` (quota system - we just created this)

4. **Rubrics:**
   - `ADD_RUBRIC_DESCRIPTION_AND_COURSE_IDS.sql`
   - `ADD_RUBRIC_EXAMPLE_VIDEOS.sql`

5. **Data Fixes (if needed):**
   - `FIX_USER_PROFILES_RLS_RECURSION.sql`
   - `FIX_VIDEO_URLS.sql`
   - `LINK_EVALUATION_VIDEOS.sql`

## Post-Migration Checklist

After migrating:

- [ ] All tables created successfully
- [ ] RLS policies applied
- [ ] Functions created (check_user_quota, increment_usage, etc.)
- [ ] Indexes created
- [ ] Test login works
- [ ] Can create test data
- [ ] Quota system works (if migrated)
- [ ] Cost tracking works (if migrated)

## Troubleshooting

### Foreign Key Errors

If you get foreign key errors:
- The migration files handle this by checking if tables exist
- Run migrations in the order listed above
- If a table is missing, create it first or skip that foreign key constraint

### RLS Policy Errors

If RLS policies fail:
- Make sure `user_profiles` table exists first
- Check that required functions exist (like `current_user_is_super_admin`)
- Run `SIGNUP_APPROVAL_RLS.sql` before other RLS migrations

### Missing Functions

If functions are missing:
- Check that all migration files have been run
- Look for function dependencies in error messages
- Run dependent migrations first

### Data Import Issues

If data import fails:
- Check for constraint violations (unique keys, foreign keys)
- Verify data types match
- Check for NULL values in NOT NULL columns

## Quick Reference

### Export Production (Schema + Data)
```bash
pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
  --no-owner --no-acl -f production_export.sql
```

### Export Production (Schema Only)
```bash
pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
  --schema-only --no-owner --no-acl -f production_schema.sql
```

### Import to Development
```bash
psql "postgresql://postgres:[PASSWORD]@[DEV-HOST]:5432/postgres" \
  -f production_export.sql
```

### Or via Supabase SQL Editor
1. Open exported SQL file
2. Copy contents
3. Paste into Dev Supabase → SQL Editor
4. Run query

## Next Steps

After migration:

1. **Update Environment Variables:**
   - Update `.env` with dev Supabase credentials
   - Update Render dev service environment variables

2. **Test the System:**
   - Test login/authentication
   - Test quota system
   - Test evaluation creation
   - Test all major features

3. **Clean Up Data (Optional):**
   - Remove sensitive production data
   - Create test users
   - Add sample data for testing

4. **Document Differences:**
   - Note any differences between prod and dev
   - Document any manual steps needed
