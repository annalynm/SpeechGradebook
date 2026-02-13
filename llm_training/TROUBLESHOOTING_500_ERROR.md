# Troubleshooting 500 Internal Server Error with Qwen on Modal

If you're getting a `500: Internal Server Error` when evaluating with Qwen on Modal, follow these steps:

## Step 1: Check Modal Logs (Most Important)

1. Go to **https://modal.com/apps**
2. Select your `qwen-speechgradebook` app
3. Click on **Logs** tab
4. Look for the most recent error messages

**What to look for:**
- `CUDA out of memory` or `OOM` → T4 GPU doesn't have enough memory
- `Model not loaded` → Model loading failed
- `Timeout` → Evaluation took too long
- `TypeError` or `AttributeError` → Code error

## Step 2: Check Render Logs

1. Go to **https://dashboard.render.com**
2. Select your SpeechGradebook service
3. Click **Logs** tab
4. Look for `[ERROR]` or `[COST_TRACKING]` entries

The improved error handling will now show more details about what went wrong.

## Step 3: Common Causes and Fixes

### Cause 1: Out of Memory (OOM) Error

**Symptoms:**
- Error mentions "CUDA", "out of memory", or "OOM"
- Works with small videos but fails with large ones
- Error occurs during model generation

**Solutions:**

**Option A: Switch back to A100 GPU** (more memory, higher cost)
```python
# In llm_training/qwen_modal.py, change:
gpu="A100",  # Instead of "T4"
```
Then redeploy:
```bash
modal deploy llm_training/qwen_modal.py
```

**Option B: Reduce video size**
- Compress videos before uploading
- Use shorter video clips for testing
- Consider splitting long videos

**Option C: Optimize model loading** (already using 4-bit quantization)

### Cause 2: Model Not Loaded

**Symptoms:**
- Error mentions "model" and "not loaded" or "None"
- Health check fails: `curl https://YOUR-MODAL-URL/health`

**Solutions:**
1. Check Modal logs for model loading errors
2. Redeploy the service:
   ```bash
   modal deploy llm_training/qwen_modal.py
   ```
3. Wait for model to fully load (first request can take 1-2 minutes)

### Cause 3: Video Processing Error

**Symptoms:**
- Error occurs early in the request
- Mentions video codec, format, or processing

**Solutions:**
1. Try a different video format (MP4, MOV)
2. Check video file size (very large files may cause issues)
3. Verify video is not corrupted

### Cause 4: Timeout

**Symptoms:**
- Request takes >5 minutes
- Error mentions "timeout"

**Solutions:**
1. Check if video is unusually long
2. Verify Modal service is running (check Modal dashboard)
3. Try again (cold starts can be slow)

## Step 4: Test with Health Check

Before running evaluations, verify the service is up:

```bash
curl https://YOUR-MODAL-URL/health
```

Should return:
```json
{"status":"ok","model":"Qwen2.5-VL-7B"}
```

If it returns `{"status":"model_not_loaded"}`, wait a minute and try again (model is still loading).

## Step 5: Verify Deployment

Make sure you deployed the T4 configuration:

```bash
# Check current deployment
modal app list

# Redeploy if needed
modal deploy llm_training/qwen_modal.py
```

## Step 6: Check QWEN_API_URL

Verify your Render environment variable is set correctly:

1. Go to **Render Dashboard** → Your service → **Environment**
2. Check `QWEN_API_URL` matches your Modal URL
3. Should be: `https://YOUR-USERNAME--qwen-speechgradebook.modal.run`
4. **No trailing slash!**

## Quick Diagnostic Commands

```bash
# Check Modal app status
modal app list

# View Modal logs
modal app logs qwen-speechgradebook

# Test health endpoint
curl https://YOUR-MODAL-URL/health

# Check Render logs (via dashboard)
# https://dashboard.render.com → Your service → Logs
```

## If Nothing Works

1. **Check Modal dashboard** for detailed error logs
2. **Try switching to A100** temporarily to see if it's a memory issue
3. **Test with a very small video** (30 seconds, low resolution)
4. **Contact Modal support** if the issue persists

## Next Steps After Fixing

Once you identify the issue:
- If it's OOM → Consider A100 or optimize video sizes
- If it's model loading → Check Modal deployment logs
- If it's timeout → Check video length and Modal service status
