# Migration Checklist: Production → Development

Quick checklist for migrating from production to development Supabase.

## Pre-Migration

- [ ] Development Supabase project created
- [ ] Development database connection string obtained
- [ ] Production database connection string obtained
- [ ] Decided: Schema only OR Schema + Data

## Migration Method

Choose one:

- [ ] **Method 1:** pg_dump (complete export/import)
- [ ] **Method 2:** Run migration files from `docs/*.sql`
- [ ] **Method 3:** Supabase CLI
- [ ] **Method 4:** Manual via SQL Editor

## Migration Steps

### If Using pg_dump:

- [ ] Exported production database
- [ ] Verified export file created
- [ ] Imported to development database
- [ ] Verified import completed

### If Using Migration Files:

Run in this order:

- [ ] `SIGNUP_APPROVAL_MIGRATION.sql`
- [ ] `SIGNUP_APPROVAL_RLS.sql`
- [ ] `ADD_INSTITUTION_THEMES.sql`
- [ ] `ADD_TEXTBOOK_RAG.sql`
- [ ] `COST_TRACKING_MIGRATION.sql`
- [ ] `ENERGY_TRACKING_AND_DONATIONS.sql`
- [ ] `USAGE_QUOTA_SYSTEM.sql`
- [ ] `ADD_RUBRIC_DESCRIPTION_AND_COURSE_IDS.sql`
- [ ] `ADD_RUBRIC_EXAMPLE_VIDEOS.sql`
- [ ] Any other migration files

## Post-Migration Verification

- [ ] All tables exist (check with `\dt` in psql or SQL Editor)
- [ ] RLS policies applied
- [ ] Functions created (check_user_quota, increment_usage, etc.)
- [ ] Indexes created
- [ ] Can log in to dev site
- [ ] Can create test data
- [ ] Quota system works
- [ ] Cost tracking works

## Environment Updates

- [ ] Updated `.env` with dev Supabase credentials
- [ ] Updated Render dev service environment variables
- [ ] Tested local development (`./run_local_dev.sh`)
- [ ] Tested dev site on Render

## Data Cleanup (Optional)

- [ ] Removed sensitive production data
- [ ] Created test users
- [ ] Added sample data for testing
- [ ] Documented any manual steps needed

## Notes

Document any issues or special steps taken:

_________________________________________________
_________________________________________________
_________________________________________________
