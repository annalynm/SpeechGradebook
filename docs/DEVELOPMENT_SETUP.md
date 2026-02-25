# Development Environment Setup Guide

This guide explains how to set up and use the development environment for SpeechGradebook, allowing you to test changes safely without affecting the production site.

## Overview

The development environment consists of three deployment targets:

1. **Localhost** - Run on your local machine for quick testing
2. **Development Render Service** - Deploy to a separate Render service for realistic testing
3. **Production Render Service** - The live site (deployed from `main` branch)

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Production    │         │   Development   │         │    Localhost     │
│   (Render)      │         │   (Render)      │         │   (localhost)    │
│                 │         │                 │         │                 │
│ Branch: main    │         │ Branch: develop │         │ Any branch      │
│ Supabase: Prod  │         │ Supabase: Dev   │         │ Supabase: Dev   │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

## Prerequisites

- Git repository access
- Python 3.11+ installed
- Docker and Docker Compose (optional, for containerized local testing)
- Render account (for development site deployment)
- **Separate Supabase project for development** (recommended)

## Step 1: Create Development Supabase Project/Branch

**IMPORTANT:** Use a separate Supabase project or database branch for development to avoid affecting production data.

### Option A: Database Branch (Recommended if Available)

Supabase offers **Database Branches** which create isolated copies of your database:

1. Go to your **production Supabase project** dashboard
2. Navigate to **Database** → **Branches** (or look for "Branches" in the sidebar)
3. Click **Create Branch** or **New Branch**
4. Name it `dev` or `development`
5. Choose to copy from your main branch/production database
6. Wait for the branch to be created
7. Switch to the dev branch and go to **Settings → API** to get credentials

**Note:** Database Branches may require a paid Supabase plan. If not available, use Option B.

### Option B: Separate Supabase Project (Alternative)

If Database Branches aren't available, create a separate project:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Click **New Project**
3. Name it something like `speechgradebook-dev` or `speechgradebook-development`
4. Choose a region and set a database password
5. Wait for the project to be created
6. Go to **Settings → API** and copy:
   - **Project URL** (e.g., `https://xxxx-dev.supabase.co`)
   - **anon public** key (NOT the service_role key)
   - **service_role** key (needed for backend operations like quota checking)

**See `SUPABASE_DEV_BRANCH_SETUP.md` for detailed setup instructions.**

### Copy Production Schema (Optional)

If you want to replicate the production database structure, you have several options:

#### Method 1: Using Supabase Dashboard (Easiest)

1. **In production Supabase:**
   - Go to **SQL Editor** (left sidebar)
   - Click **New Query**
   - Run this query to generate schema SQL:
     ```sql
     -- Export table structures (without data)
     SELECT 
       'CREATE TABLE IF NOT EXISTS ' || schemaname || '.' || tablename || ' (' ||
       string_agg(column_name || ' ' || data_type || 
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
     GROUP BY schemaname, tablename;
     ```
   - Or use the **Database** → **Tables** view to see structure
   - For a complete export, use Method 2 or 3 below

2. **In development Supabase:**
   - Go to **SQL Editor**
   - Paste and run the schema SQL

#### Method 2: Using pg_dump (Most Complete)

This exports the complete schema including tables, functions, triggers, RLS policies, etc.

1. **Get your database connection string:**
   - In production Supabase: **Settings** → **Database** → **Connection string** → **URI**
   - Copy the connection string (looks like: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`)

2. **Export schema only (no data):**
   ```bash
   pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
     --schema-only \
     --no-owner \
     --no-acl \
     -f schema_export.sql
   ```

3. **Or export schema with specific tables:**
   ```bash
   pg_dump "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" \
     --schema-only \
     --table=public.courses \
     --table=public.evaluations \
     --table=public.user_profiles \
     # ... add other tables
     -f schema_export.sql
   ```

4. **Import into development Supabase:**
   - In development Supabase: **SQL Editor** → **New Query**
   - Open `schema_export.sql` and paste the contents
   - Run the query

#### Method 3: Using Supabase CLI (Recommended for Advanced Users)

1. **Install Supabase CLI:**
   ```bash
   npm install -g supabase
   # Or: brew install supabase/tap/supabase
   ```

2. **Link to your project:**
   ```bash
   supabase link --project-ref your-project-ref
   # Project ref is in your Supabase dashboard URL
   ```

3. **Generate migration from production:**
   ```bash
   supabase db dump -f schema_export.sql --schema public
   ```

4. **Apply to development:**
   ```bash
   # Switch to dev project
   supabase link --project-ref your-dev-project-ref
   supabase db reset  # WARNING: This resets the database
   # Or apply migration:
   supabase migration up
   ```

#### Method 4: Manual Copy via SQL Editor

If you have existing SQL migration files in your repo (like in `docs/*.sql`):

1. Review the SQL files in `docs/` folder
2. Run them in order in your development Supabase **SQL Editor**
3. This ensures you have the same structure as production

**Note:** 
- You may want to skip copying actual data to keep the dev database clean
- RLS (Row Level Security) policies are important - make sure they're included in your export
- Functions, triggers, and stored procedures should also be exported if you use them

## Step 2: Set Up Local Development

### 2.1 Configure Environment Variables

1. Copy the development environment template:
   ```bash
   cp .env.development .env
   ```

2. Edit `.env` and add your **development** Supabase credentials:
   ```bash
   SUPABASE_URL=https://your-dev-project.supabase.co
   SUPABASE_ANON_KEY=your-dev-anon-key-here
   ```

3. (Optional) Add other variables as needed:
   - `QWEN_API_URL` - For video evaluation (can use `http://localhost:8001` for local Qwen service)
   - `SENTRY_ENVIRONMENT=development` - For error tracking
   - `ALLOWED_ORIGINS` - Include `http://localhost:8000` if needed

### 2.2 Run Locally

**Option A: Using the development script (recommended)**
```bash
./run_local_dev.sh
```

This script:
- Automatically uses `.env` (or copies from `.env.development` if missing)
- Creates a virtual environment if needed
- Installs dependencies automatically
- Runs the server on `http://localhost:8000`

**Option B: Using Docker Compose**
```bash
# Using .env file
docker compose up --build

# Or explicitly use .env.development
docker compose --env-file .env.development up --build
```

**Option C: Manual Python**
```bash
# Create venv if needed
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run server
uvicorn app:app --host 0.0.0.0 --port 8000
```

The app will be available at `http://localhost:8000`

### 2.3 Running Qwen Service Locally (Optional)

If you want to test video evaluation locally:

1. In a separate terminal:
   ```bash
   cd llm_training
   pip install -r requirements-qwen.txt
   python qwen_serve.py --port 8001
   ```

2. Add to your `.env`:
   ```bash
   QWEN_API_URL=http://localhost:8001
   ```

3. Restart the main server

## Step 3: Set Up Development Render Service

You have two options: **duplicate the existing service** (easier) or **create a new service** (more control).

### Option A: Duplicate Existing Service (Recommended)

This is the easiest way - it copies all your configuration automatically!

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Open your existing **speechgradebook** service
3. Click the **Settings** tab (left sidebar)
4. Scroll down and click **Duplicate Service** (or look for a "Duplicate" button/option)
5. Render will create a copy with a new name (e.g., `speechgradebook-copy`)
6. **IMPORTANT - Update these settings:**
   - **Name**: Change to `speechgradebook-dev`
   - **Branch**: Change from `main` to `develop` (CRITICAL!)
   - **Environment Variables**: Update to use development Supabase (see Step 3.2 below)

**Note:** If you don't see a "Duplicate" option in Settings, Render may not support it for your service type, or you may need to use Option B below.

### Option B: Create New Service Manually

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your repository
4. Configure the service:
   - **Name**: `speechgradebook-dev` (or similar)
   - **Branch**: `develop` (IMPORTANT: use develop branch, not main)
   - **Runtime**: `Docker`
   - **Build Command**: (leave empty, Dockerfile handles it)
   - **Start Command**: (leave empty, Dockerfile handles it)

### 3.2 Set Environment Variables

**If you duplicated the service (Option A):** You'll need to update the environment variables that were copied from production.

**If you created a new service (Option B):** You'll need to add all environment variables.

In the Render service dashboard, go to **Environment** and set:

**Required (MUST be updated if duplicated):**
- `SUPABASE_URL` - Change to your **development** Supabase project URL (NOT production!)
- `SUPABASE_ANON_KEY` - Change to your **development** Supabase anon key (NOT production!)

**⚠️ CRITICAL:** If you duplicated the service, these will still point to production. You MUST update them to your development Supabase project!

**Optional (recommended):**
- `SENTRY_ENVIRONMENT=development` - Separate dev errors from production
- `ALLOWED_ORIGINS` - Include your dev site URL (e.g., `https://speechgradebook-dev.onrender.com`)
- `QWEN_API_URL` - If using Qwen service (can share with production or use separate instance)

**Optional (if using ISAAC integration):**
- `ISAAC_USER`, `ISAAC_HOST`, `ISAAC_REMOTE_DIR`, `ISAAC_SSH_PRIVATE_KEY`
- `RENDER_LLM_EXPORT_SECRET`
- See `RENDER_DEPLOY.md` for full ISAAC setup

### 3.3 Deploy

1. Click **Save Changes**
2. Render will automatically deploy from the `develop` branch
3. Your development site will be available at `https://speechgradebook-dev.onrender.com` (or your custom domain)

**Note:** You can also use `render-dev.yaml` as a Blueprint, but you'll still need to manually set the branch to `develop` in the Render dashboard.

## Step 4: Development Workflow

### Daily Development

1. **Switch to develop branch:**
   ```bash
   git checkout develop
   ```

2. **Make your changes**

3. **Test locally:**
   ```bash
   ./run_local_dev.sh
   # Test at http://localhost:8000
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin develop
   ```

5. **Test on development site:**
   - Render will automatically deploy from `develop` branch
   - Test at `https://speechgradebook-dev.onrender.com`

6. **When ready for production:**
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```
   - Production will automatically deploy from `main` branch

### Branch Strategy

- **`main`** branch → Production Render service → Production Supabase
- **`develop`** branch → Development Render service → Development Supabase
- **Local development** → Any branch → Development Supabase (via `.env`)

## Environment Variables Reference

See `.env.example` for a complete list of all available environment variables.

### Required for Development

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Development Supabase project URL | `https://xxxx-dev.supabase.co` |
| `SUPABASE_ANON_KEY` | Development Supabase anon key | `eyJhbGc...` |

### Commonly Used Optional Variables

| Variable | Description | Development Value |
|----------|-------------|-------------------|
| `QWEN_API_URL` | Qwen service URL | `http://localhost:8001` (local) or Modal URL |
| `SENTRY_ENVIRONMENT` | Error tracking environment | `development` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:8000,https://speechgradebook-dev.onrender.com` |
| `PORT` | Server port | `8000` |

## Troubleshooting

### "Invalid API key" Error

- **Cause:** `SUPABASE_URL` or `SUPABASE_ANON_KEY` not set or incorrect
- **Fix:** 
  - Check your `.env` file has the correct development Supabase credentials
  - On Render, verify environment variables are set correctly
  - Make sure you're using the **anon** key, not the service_role key

### Localhost Not Connecting to Supabase

- **Cause:** `.env` file missing or incorrect
- **Fix:**
  - Ensure `.env` exists in the project root
  - Run `./run_local_dev.sh` which will help set it up
  - Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct

### Development Site Not Updating

- **Cause:** Wrong branch or deployment not triggered
- **Fix:**
  - Verify Render service is set to deploy from `develop` branch
  - Check that you pushed to `develop`, not `main`
  - Manually trigger a deploy in Render dashboard if needed

### Accidentally Using Production Supabase

- **Cause:** Wrong credentials in `.env` or Render environment
- **Fix:**
  - Double-check your `.env` uses development Supabase credentials
  - Verify Render dev service environment variables point to dev Supabase
  - Consider using different project names to avoid confusion

## Best Practices

1. **Always use development Supabase for local and dev site testing**
   - Never use production Supabase credentials in `.env` or dev Render service

2. **Test thoroughly before merging to main**
   - Test locally first
   - Test on development site
   - Only merge to `main` when confident

3. **Keep environments separate**
   - Production: `main` branch → Production Supabase
   - Development: `develop` branch → Development Supabase
   - Local: Any branch → Development Supabase (via `.env`)

4. **Use descriptive commit messages**
   - Makes it easier to track changes and roll back if needed

5. **Regularly sync develop with main**
   - Merge `main` → `develop` periodically to keep dev branch up to date
   ```bash
   git checkout develop
   git merge main
   git push origin develop
   ```

## Quick Reference

### Local Development
```bash
# Set up environment
cp .env.development .env
# Edit .env with your dev Supabase credentials

# Run locally
./run_local_dev.sh
# Or: docker compose up --build
```

### Deploy to Development Site
```bash
git checkout develop
git add .
git commit -m "Your changes"
git push origin develop
# Render automatically deploys from develop branch
```

### Deploy to Production
```bash
git checkout main
git merge develop
git push origin main
# Render automatically deploys from main branch
```

## Additional Resources

- `RENDER_DEPLOY.md` - Detailed Render deployment guide
- `.env.example` - Complete environment variables reference
- `render-dev.yaml` - Development Render service configuration
- `render.yaml` - Production Render service configuration
