# Database Backup Setup

This document describes how to set up automated database backups for SpeechGradebook.

## Overview

Two backup methods are recommended:
1. **Supabase Pro daily backups** (primary, automated)
2. **pg_dump cron job** (secondary, manual setup)

---

## Method 1: Supabase Pro Daily Backups

### Prerequisites
- Supabase Pro plan ($25/month)
- Admin access to Supabase dashboard

### Setup Steps

1. **Upgrade to Pro Plan**
   - Go to Supabase Dashboard → Settings → Billing
   - Upgrade to Pro plan
   - Verify plan is active

2. **Enable Daily Backups**
   - Go to Settings → Database → Backups
   - Daily backups are automatically enabled on Pro plan
   - Verify backup schedule (typically daily at 00:00 UTC)

3. **Configure Backup Retention**
   - Default: 7 days of daily backups
   - Can be extended with higher tier plans
   - Review retention policy

4. **Verify Backups**
   - Check that backups are being created
   - Test restore procedure (see RESTORE.md)
   - Document backup schedule

### Backup Details
- **Frequency**: Daily
- **Retention**: 7 days (Pro plan)
- **Location**: Managed by Supabase
- **Restore**: Via Supabase dashboard

---

## Method 2: pg_dump Automated Backups

### Prerequisites
- Database connection string (from Supabase)
- Server/machine with cron access (or Render cron job)
- Storage location (R2, S3, or local)

### Setup Steps

1. **Get Database Connection String**
   - Go to Supabase Dashboard → Settings → Database
   - Copy "Connection string" → "URI"
   - Format: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`
   - Store securely (environment variable, not in code)

2. **Install Backup Script**
   - Copy `scripts/backup_database.sh` to your server
   - Make executable: `chmod +x scripts/backup_database.sh`
   - Set environment variables:
     ```bash
     export SUPABASE_DB_URL="postgresql://..."
     export BACKUP_STORAGE_TYPE="r2"  # or "s3" or "local"
     export R2_ACCOUNT_ID="..."
     export R2_ACCESS_KEY_ID="..."
     export R2_SECRET_ACCESS_KEY="..."
     export R2_BUCKET_NAME="speechgradebook-backups"
     ```

3. **Set Up Cron Job**
   ```bash
   # Edit crontab
   crontab -e
   
   # Add daily backup at 2 AM UTC
   0 2 * * * /path/to/scripts/backup_database.sh >> /var/log/backup.log 2>&1
   
   # Or use Render cron (if available)
   # Add cron job in Render dashboard
   ```

4. **Test Backup Script**
   ```bash
   # Run manually to test
   ./scripts/backup_database.sh
   
   # Verify backup file is created
   # Check backup location (R2/S3/local)
   ```

5. **Set Up Backup Rotation**
   - Script automatically rotates backups:
     - Keep 7 daily backups
     - Keep 4 weekly backups (Sunday backups)
     - Keep 12 monthly backups (first of month)
   - Old backups are automatically deleted

6. **Monitor Backups**
   - Check backup logs regularly
   - Set up alerts for backup failures
   - Verify backups are being created

### Backup Script Configuration

Edit `scripts/backup_database.sh` to configure:
- Backup location (R2, S3, or local)
- Retention policy
- Notification settings
- Encryption (optional)

---

## Backup Storage Options

### Option A: Cloudflare R2 (Recommended)
- **Cost**: Free egress, low storage costs
- **Setup**: Create R2 bucket, generate API keys
- **Pros**: Cost-effective, S3-compatible
- **Cons**: Requires R2 account

### Option B: AWS S3
- **Cost**: Storage + egress costs
- **Setup**: Create S3 bucket, configure IAM
- **Pros**: Widely used, reliable
- **Cons**: Higher costs, especially egress

### Option C: Local Storage
- **Cost**: Free (uses server disk)
- **Setup**: Specify local path in script
- **Pros**: Simple, no external dependencies
- **Cons**: Not redundant, lost if server fails

---

## Backup Encryption (Optional)

For sensitive data, encrypt backups:

1. **Generate Encryption Key**
   ```bash
   openssl rand -base64 32 > backup_key.txt
   # Store securely, not in repository
   ```

2. **Update Backup Script**
   - Add encryption step using `gpg` or `openssl`
   - Encrypt before uploading to storage
   - Decrypt during restore

---

## Monitoring and Alerts

### Set Up Alerts

1. **Backup Failure Alerts**
   - Monitor backup script exit codes
   - Send email/Slack on failure
   - Check backup logs daily

2. **Backup Size Monitoring**
   - Alert if backup size changes significantly
   - May indicate data issues or backup problems

3. **Storage Quota Alerts**
   - Monitor storage usage
   - Alert before quota is reached

### Manual Verification

- **Weekly**: Check that backups are being created
- **Monthly**: Test restore procedure
- **Quarterly**: Review backup retention policy

---

## Backup Retention Policy

Recommended retention:
- **Daily backups**: 7 days
- **Weekly backups**: 4 weeks (Sunday backups)
- **Monthly backups**: 12 months (first of month)

Adjust based on:
- Storage costs
- Compliance requirements
- Recovery needs

---

## Troubleshooting

### Backup Script Fails

1. **Check Database Connection**
   - Verify `SUPABASE_DB_URL` is correct
   - Test connection: `psql "$SUPABASE_DB_URL" -c "SELECT 1"`

2. **Check Storage Access**
   - Verify R2/S3 credentials
   - Test upload manually
   - Check bucket permissions

3. **Check Disk Space**
   - Ensure sufficient space for backup
   - Clean up old backups if needed

4. **Check Logs**
   - Review backup script logs
   - Check for error messages
   - Verify cron job is running

### Backup Not Created

- Verify cron job is scheduled correctly
- Check cron job has proper permissions
- Verify environment variables are set
- Test script manually

---

## Best Practices

1. **Test Restores Regularly**
   - Test restore procedure monthly
   - Verify backups are usable
   - Document any issues

2. **Monitor Backup Size**
   - Unexpected size changes may indicate problems
   - Track backup size over time

3. **Document Backup Schedule**
   - Keep record of backup times
   - Note any skipped backups
   - Document retention policy

4. **Secure Backup Storage**
   - Encrypt backups if sensitive
   - Use secure access credentials
   - Limit access to backup storage

5. **Multiple Backup Locations**
   - Use both Supabase Pro and pg_dump
   - Store pg_dump backups in multiple locations
   - Test restore from each location

---

## Environment Variables

Required for pg_dump backup script:

```bash
# Database connection
SUPABASE_DB_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"

# Storage configuration (choose one)
BACKUP_STORAGE_TYPE="r2"  # or "s3" or "local"

# R2 configuration (if using R2)
R2_ACCOUNT_ID="..."
R2_ACCESS_KEY_ID="..."
R2_SECRET_ACCESS_KEY="..."
R2_BUCKET_NAME="speechgradebook-backups"

# S3 configuration (if using S3)
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
AWS_S3_BUCKET="speechgradebook-backups"
AWS_REGION="us-east-1"

# Local storage (if using local)
BACKUP_LOCAL_PATH="/path/to/backups"

# Notification (optional)
BACKUP_NOTIFICATION_EMAIL="admin@example.com"
SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
```

---

**Last Updated**: 2026-02-XX  
**Next Review**: Quarterly or after backup issues
