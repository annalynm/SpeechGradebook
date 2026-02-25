# Render Development Environment Variables

Quick reference for setting up environment variables in your Render development service.

## Required Variables (MUST SET)

These are **required** for the app to work. Without them, login will fail.

| Variable | Description | Where to Get It | Example |
|----------|-------------|-----------------|---------|
| `SUPABASE_URL` | **Development** Supabase project URL | Development Supabase Dashboard → Settings → API → Project URL | `https://xxxx-dev.supabase.co` |
| `SUPABASE_ANON_KEY` | **Development** Supabase anon/public key | Development Supabase Dashboard → Settings → API → anon public key | `eyJhbGc...` |
| `SUPABASE_SERVICE_ROLE_KEY` | **Development** Supabase service role key | Development Supabase Dashboard → Settings → API → service_role key | `eyJhbGc...` |

**⚠️ CRITICAL:** Use your **DEVELOPMENT** Supabase project credentials, NOT production!

**Note:** `SUPABASE_SERVICE_ROLE_KEY` is required for backend operations like quota checking and cost tracking. Make sure to use the **service_role** key from your **development** project, not production.

## Recommended Optional Variables

These are recommended for a better development experience.

| Variable | Description | Development Value |
|----------|-------------|-------------------|
| `SENTRY_ENVIRONMENT` | Error tracking environment | `development` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:8000,https://speechgradebook-dev.onrender.com` |
| `QWEN_API_URL` | Qwen video evaluation service URL | Your Qwen service URL (can share with production or use separate instance) |

## Optional Variables (Only if Needed)

Only set these if you use the corresponding features.

### Qwen Service (Video Evaluation)

| Variable | Description | Notes |
|----------|-------------|-------|
| `QWEN_API_URL` | Qwen service URL | Can be same as production or separate dev instance |

### Sentry Error Monitoring

| Variable | Description | Notes |
|----------|-------------|-------|
| `SENTRY_DSN` | Sentry project DSN | Use separate Sentry project for dev (recommended) |
| `SENTRY_ENVIRONMENT` | Environment name | Set to `development` |

### ISAAC Integration (Training Job Submission)

Only needed if you use "Submit to ISAAC" feature in Platform Analytics.

| Variable | Description | Example |
|----------|-------------|---------|
| `ISAAC_USER` | UT NetID | `amcclu12` |
| `ISAAC_HOST` | ISAAC hostname | `login.isaac.utk.edu` |
| `ISAAC_REMOTE_DIR` | Remote directory path | `~/llm_training` |
| `ISAAC_SSH_PRIVATE_KEY` | Full SSH private key | `-----BEGIN RSA PRIVATE KEY-----...` |
| `RENDER_LLM_EXPORT_SECRET` | Secret for API authentication | Any secret string |

**Optional SLURM configuration:**
- `ISAAC_PARTITION` (e.g., `campus-gpu`)
- `ISAAC_ACCOUNT` (e.g., `ACF-UTK0011`)
- `ISAAC_TIME` (e.g., `04:00:00`)
- `ISAAC_GPU_COUNT` (e.g., `1`)

### Slack Notifications

| Variable | Description |
|----------|-------------|
| `SLACK_SIGNUP_WEBHOOK_URL` | Slack webhook URL for signup notifications |

### Model Configuration (Optional)

Only needed if you serve the Mistral model on this service.

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PATH` | Path to model adapter | `./llm_training/mistral7b-speech-lora` |
| `BASE_MODEL` | Base model name | `mistralai/Mistral-7B-Instruct-v0.2` |
| `LOAD_IN_8BIT` | Load in 8-bit mode | `1`, `true`, or `yes` |

## Minimum Setup

For a basic working development site, you need:

```
SUPABASE_URL=https://your-dev-project.supabase.co
SUPABASE_ANON_KEY=your-dev-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-dev-service-role-key-here
```

**Note:** `SUPABASE_SERVICE_ROLE_KEY` is required for the quota system and cost tracking features.

## How to Set in Render

1. Go to your **speechgradebook-dev** service in Render Dashboard
2. Click **Environment** (left sidebar)
3. Click **Add Environment Variable** for each variable
4. Enter the **Key** and **Value**
5. Click **Save Changes** (Render will automatically redeploy)

## Quick Checklist

- [ ] `SUPABASE_URL` - Set to **development** project URL
- [ ] `SUPABASE_ANON_KEY` - Set to **development** anon key
- [ ] `SUPABASE_SERVICE_ROLE_KEY` - Set to **development** service role key (required for quota system)
- [ ] `SENTRY_ENVIRONMENT=development` (if using Sentry)
- [ ] `ALLOWED_ORIGINS` - Include dev site URL (if needed for CORS)
- [ ] `QWEN_API_URL` - If using Qwen service
- [ ] Any ISAAC variables (if using ISAAC integration)

## Important Notes

1. **Never use production Supabase credentials** in the development service
2. **Always verify** you're using the development Supabase project URL and key
3. After setting variables, Render will automatically redeploy
4. Check the deploy logs if the app doesn't work after setting variables
