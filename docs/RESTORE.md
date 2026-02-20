# Database Restore Procedure

This document describes how to restore the SpeechGradebook database from backups.

## Prerequisites

- Access to Supabase dashboard (admin)
- Database connection string (for pg_dump backups)
- Backup file (from Supabase Pro or pg_dump)

---

## Method 1: Restore from Supabase Pro Backup

Supabase Pro plan provides daily automated backups that can be restored through the dashboard.

### Steps

1. **Access Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project
   - Navigate to **Settings** → **Database** → **Backups**

2. **Select Backup**
   - View available backups (daily backups retained per your plan)
   - Select the backup point you want to restore to
   - Note the backup timestamp

3. **Restore Backup**
   - Click **Restore** on the selected backup
   - Confirm the restore operation
   - **Warning**: This will overwrite the current database
   - Restore typically takes 5-30 minutes depending on database size

4. **Verify Restoration**
   - Check that data is restored correctly
   - Verify critical tables: `evaluations`, `user_profiles`, `courses`, etc.
   - Test application functionality
   - Check that recent data (after backup) is missing (expected)

5. **Post-Restore**
   - Update application if needed
   - Notify users if data was lost
   - Document what was restored and what was lost

---

## Method 2: Restore from pg_dump Backup

If you have a pg_dump backup file (from the backup script), restore it as follows:

### Steps

1. **Prepare Environment**
   ```bash
   # Set environment variables
   export SUPABASE_DB_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
   # Or use connection string from Supabase dashboard:
   # Settings → Database → Connection string → URI
   ```

2. **Restore Backup**
   ```bash
   # Restore from backup file
   pg_restore -d "$SUPABASE_DB_URL" --clean --if-exists backup_YYYY-MM-DD_HH-MM-SS.dump
   
   # Or if backup is in SQL format:
   psql "$SUPABASE_DB_URL" < backup_YYYY-MM-DD_HH-MM-SS.sql
   ```

3. **Verify Restoration**
   - Connect to database and check tables
   - Verify row counts match expected values
   - Test application functionality

4. **Re-apply Migrations (if needed)**
   - If backup is from before recent migrations, re-run migration files
   - Check `docs/` directory for migration SQL files
   - Run migrations in order

---

## Method 3: Point-in-Time Recovery (Supabase Pro)

Supabase Pro supports point-in-time recovery (PITR) for more granular restores.

### Steps

1. **Access PITR**
   - Go to Supabase Dashboard → Settings → Database → Backups
   - Look for "Point-in-Time Recovery" option

2. **Select Recovery Point**
   - Choose the exact timestamp to restore to
   - This allows restoring to any point within the retention period

3. **Restore**
   - Follow Supabase's PITR restore process
   - This creates a new database instance
   - You can then migrate data or switch to the restored instance

---

## Testing Restore Procedure

**Important**: Test restore procedure before you need it in production.

### Test Environment Setup

1. **Create Test Database**
   - Use Supabase staging project, or
   - Create a new Supabase project for testing

2. **Test Restore**
   - Create a backup
   - Make some test changes
   - Restore from backup
   - Verify changes are reverted

3. **Document Issues**
   - Note any problems encountered
   - Update this document with solutions
   - Improve restore procedure

---

## Recovery Time Objectives (RTO)

- **Supabase Pro Backup**: 5-30 minutes (automated)
- **pg_dump Backup**: 10-60 minutes (manual, depends on size)
- **PITR**: 5-30 minutes (automated, more granular)

---

## Data Loss Considerations

- **Daily Backups**: Maximum data loss = 24 hours
- **Point-in-Time Recovery**: Maximum data loss = minutes (depends on backup frequency)
- **pg_dump Backups**: Maximum data loss = time since last backup

**Recommendation**: Use both Supabase Pro backups (automated) and pg_dump backups (redundancy).

---

## Post-Restore Checklist

- [ ] Verify all critical tables restored
- [ ] Check row counts match expectations
- [ ] Test user authentication
- [ ] Test evaluation creation
- [ ] Verify file storage links still work
- [ ] Check RLS policies are intact
- [ ] Verify application functionality
- [ ] Notify users if data was lost
- [ ] Document what was restored
- [ ] Update backup procedures if needed

---

## Emergency Contacts

- **Supabase Support**: https://supabase.com/support
- **Database Issues**: Check Supabase status page first

---

**Last Updated**: 2026-02-XX  
**Next Review**: After each restore or quarterly
