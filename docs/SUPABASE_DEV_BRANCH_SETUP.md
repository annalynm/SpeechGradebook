# Supabase Dev Branch Setup Guide

This guide helps you set up a Supabase development branch/project and configure your development environment and Render service.

## Option 1: Supabase Database Branches (Recommended if Available)

Supabase offers **Database Branches** which allow you to create isolated copies of your database for development.

### Step 1: Create a Database Branch

1. Go to your **production Supabase project** dashboard
2. Navigate to **Database** → **Branches** (or look for "Branches" in the left sidebar)
3. Click **Create Branch** or **New Branch**
4. Name it `dev` or `development`
5. Choose to copy from your main branch/production database
6. Wait for the branch to be created

### Step 2: Get Dev Branch Credentials

1. In your Supabase dashboard, switch to or select your **dev branch**
2. Go to **Settings** → **API**
3. Copy:
   - **Project URL** (e.g., `https://xxxx-dev.supabase.co`)
   - **anon public** key (NOT the service_role key)
   - **service_role** key (if needed for backend operations)

**Note:** If Database Branches aren't available in your Supabase plan, use Option 2 below.

## Option 2: Separate Supabase Project (Alternative)

If Database Branches aren't available, create a separate Supabase project:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Click **New Project**
3. Name it `speechgradebook-dev` or `speechgradebook-development`
4. Choose a region and set a database password
5. Wait for the project to be created
6. Go to **Settings** → **API** and copy:
   - **Project URL** (e.g., `https://xxxx-dev.supabase.co`)
   - **anon public** key
   - **service_role** key (if needed)

### Copy Production Schema to Dev Project

After creating the dev project, you need to copy your production schema and optionally data:

**See `MIGRATE_PRODUCTION_TO_DEV.md` for complete migration instructions.**

Quick options:

1. **Using pg_dump (Recommended):**
   - Export from production: `pg_dump --schema-only ...`
   - Import to development: `psql ... -f export.sql`

2. **Using Migration Files:**
   - Run all SQL files from `docs/*.sql` in your dev Supabase SQL Editor
   - See `MIGRATE_PRODUCTION_TO_DEV.md` for the recommended order

3. **Complete Migration (Schema + Data):**
   - See `MIGRATE_PRODUCTION_TO_DEV.md` for full instructions

## Step 3: Update Local Development Environment

### Update `.env` File

1. Open your `.env` file in the project root (or create it from `.env.development`):
   ```bash
   cp .env.development .env
   ```

2. Update with your **development** Supabase credentials:
   ```bash
   SUPABASE_URL=https://your-dev-project.supabase.co
   SUPABASE_ANON_KEY=your-dev-anon-key-here
   SUPABASE_SERVICE_ROLE_KEY=your-dev-service-role-key-here
   ```

3. **Important:** Make sure these point to your **development** project/branch, NOT production!

### Verify Local Setup

Test your local setup:
```bash
./run_local_dev.sh
```

The app should connect to your development Supabase project.

## Step 4: Update Render Development Service Environment Variables

### Access Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Find your **development service** (e.g., `speechgradebook-dev`)
   - If you don't have one, see `DEVELOPMENT_SETUP.md` for how to create it

### Update Environment Variables

1. Click on your development service
2. Go to **Environment** (left sidebar)
3. Update or add these variables:

   **Required:**
   ```
   SUPABASE_URL=https://your-dev-project.supabase.co
   SUPABASE_ANON_KEY=your-dev-anon-key-here
   SUPABASE_SERVICE_ROLE_KEY=your-dev-service-role-key-here
   ```

   **Recommended:**
   ```
   SENTRY_ENVIRONMENT=development
   ALLOWED_ORIGINS=http://localhost:8000,https://speechgradebook-dev.onrender.com
   ```

   **Optional (if using):**
   ```
   QWEN_API_URL=your-qwen-service-url
   SENTRY_DSN=your-sentry-dsn
   ```

4. Click **Save Changes**
5. Render will automatically redeploy with the new environment variables

### Verify Render Deployment

1. Check the **Logs** tab in Render to ensure the deployment succeeded
2. Visit your development site URL (e.g., `https://speechgradebook-dev.onrender.com`)
3. Test login - it should connect to your development Supabase project

## Step 5: Verify Everything Works

### Checklist

- [ ] Dev Supabase project/branch created
- [ ] Production schema copied to dev (if using separate project)
- [ ] `.env` file updated with dev credentials
- [ ] Local development works (`./run_local_dev.sh`)
- [ ] Render dev service environment variables updated
- [ ] Render deployment successful
- [ ] Can log in to dev site
- [ ] Dev site uses dev Supabase (check by creating test data - it shouldn't appear in production)

## Important Notes

1. **Never mix production and development credentials:**
   - Production Render service → Production Supabase
   - Development Render service → Development Supabase
   - Local development → Development Supabase (via `.env`)

2. **Database Branches vs Separate Projects:**
   - **Branches:** Easier to manage, automatically synced structure, may have plan limitations
   - **Separate Projects:** More isolation, full control, requires manual schema sync

3. **Schema Changes:**
   - When you add new migrations (like `USAGE_QUOTA_SYSTEM.sql`), run them in **both** production and development
   - Or use a migration tool to keep them in sync

4. **Service Role Key:**
   - The `SUPABASE_SERVICE_ROLE_KEY` is needed for backend operations (quota checking, cost tracking)
   - Make sure it's set in both `.env` (for local) and Render environment variables

## Troubleshooting

### "Invalid API key" Error

- **Cause:** Wrong Supabase credentials or missing environment variables
- **Fix:** 
  - Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env` (local) or Render (deployed)
  - Make sure you're using **development** credentials, not production
  - Check that the keys are the **anon** key, not service_role (for frontend)

### Local Development Not Connecting

- **Cause:** `.env` file missing or incorrect
- **Fix:**
  - Ensure `.env` exists in project root
  - Run `./run_local_dev.sh` which will help set it up
  - Verify credentials point to development Supabase

### Render Deployment Failing

- **Cause:** Missing or incorrect environment variables
- **Fix:**
  - Check Render **Logs** tab for specific errors
  - Verify all required environment variables are set
  - Ensure `SUPABASE_SERVICE_ROLE_KEY` is set if using quota system

### Data Appearing in Wrong Environment

- **Cause:** Wrong Supabase credentials in environment
- **Fix:**
  - Double-check `.env` uses development credentials
  - Verify Render dev service uses development credentials
  - Test by creating test data and checking it doesn't appear in production

## Quick Reference

### Local Development
```bash
# Update .env with dev Supabase credentials
SUPABASE_URL=https://your-dev-project.supabase.co
SUPABASE_ANON_KEY=your-dev-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-dev-service-role-key

# Run locally
./run_local_dev.sh
```

### Render Development Service
1. Go to Render Dashboard → Your Dev Service → Environment
2. Update:
   - `SUPABASE_URL` → Dev project URL
   - `SUPABASE_ANON_KEY` → Dev anon key
   - `SUPABASE_SERVICE_ROLE_KEY` → Dev service role key
3. Save Changes (auto-deploys)

### Run Migrations in Dev
1. Go to Dev Supabase → SQL Editor
2. Run migration files from `docs/*.sql`
3. Start with `USAGE_QUOTA_SYSTEM.sql` if you just created it

## Next Steps

After setting up the dev environment:

1. **Run the usage quota migration** in your dev Supabase:
   - Go to Dev Supabase → SQL Editor
   - Copy and run `docs/USAGE_QUOTA_SYSTEM.sql`
   - This creates all the quota tracking tables

2. **Test the quota system** in development:
   - Create a test user quota
   - Test evaluation with quota checking
   - Verify usage tracking works

3. **When ready for production:**
   - Run the same migrations in production Supabase
   - Update production Render service if needed
