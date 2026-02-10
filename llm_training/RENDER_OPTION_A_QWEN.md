# Option A: Run Qwen on Render (Set URL Once, No Tunnel)

Run Qwen as a **second Render Web Service**. You set **QWEN_API_URL** on your main app once and never change it. No Cloudflare, no tunnel, no script to run — just use the app.

---

## Step-by-step directions

### 1. Open Render and add a new Web Service

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in.
2. Click **New +** (top right) → **Web Service**.
3. If asked, **connect your repository** (the same one that has your main SpeechGradebook app). Authorize Render if needed and select the repo.

### 2. Configure the Qwen service

Use these settings. Replace your actual main app URL if it’s different.

| Field | Value |
|--------|--------|
| **Name** | `qwen-speechgradebook` (or any name; this becomes part of the URL) |
| **Region** | Same as your main app (e.g. Oregon) |
| **Branch** | `main` (or the branch you deploy from) |
| **Root Directory** | `llm_training` |
| **Runtime** / **Environment** | **Docker** |
| **Dockerfile path** | `Dockerfile.qwen` (relative to Root Directory, so full path is `llm_training/Dockerfile.qwen`) |
| **Instance type** | **Free** for now, or **Starter** / **Standard** when you move off free tier (more memory = fewer timeouts) |

If Render shows **Docker Command** or **Docker Context**, leave defaults (it will use the Dockerfile in the Root Directory).

### 3. Add environment variables (Qwen service)

In the **Environment** or **Environment Variables** section for this new service, add:

| Key | Value |
|-----|--------|
| **ALLOWED_ORIGINS** | `https://speechgradebook.onrender.com` (your main app’s URL; no trailing slash; use your real URL if different) |

Render usually sets **PORT** automatically. If you see a PORT field, you can leave it blank or set it to `10000` (Render will override with its own port in production).

### 4. Create the service and wait for deploy

1. Click **Create Web Service** (or **Deploy**).
2. Wait for the first deploy to finish (build can take several minutes; the Qwen image is large). If the build fails, check the build logs (often a path or Dockerfile issue).
3. When the service is **Live**, open its URL from the dashboard (e.g. `https://qwen-speechgradebook.onrender.com`). You should see a **404** or similar for the root path; that’s fine. Try:
   - `https://your-qwen-service.onrender.com/health`  
   You should get JSON like `{"status":"ok","model":"Qwen2.5-VL-7B"}`.

### 5. Set QWEN_API_URL on your main app

1. In the Render dashboard, open your **main** SpeechGradebook service (the one that serves the app).
2. Go to **Environment** (left sidebar).
3. Add or edit **QWEN_API_URL**:
   - **Key:** `QWEN_API_URL`
   - **Value:** the Qwen service URL from step 4 (e.g. `https://qwen-speechgradebook.onrender.com`) — **no trailing slash**.
4. Click **Save Changes**. Render will redeploy the main app.

### 6. Test in the app

1. When the main app finishes redeploying, open it and go to **Evaluate Speech**.
2. Upload a short video or audio, pick a rubric, and choose **SpeechGradebook Text + Video Model (Qwen)** as the provider.
3. Run the evaluation. The first request may be slow (cold start on free tier); later ones may be faster while the instance is warm.

---

## Paid tier: does it change anything?

**Staying on Render (paid):**  
Moving off the free tier (e.g. to Starter or Standard) **does not change this setup**. Same two services (main app + Qwen). What improves:

- **No spin-down** — both services stay up, so no long cold starts.
- **More memory/CPU** — the Qwen service can use more RAM, which can reduce timeouts or OOM on larger videos.
- **No 15‑minute idle spin-down** on the free tier.

You do **not** need to redo Option A when you go paid; you just upgrade the instance type for one or both services if you want.

**Switching to another host (e.g. Fly.io, Railway, AWS, GCP):**  
If you move the **main app** off Render, you’d:

- Deploy the main app on the new host.
- Either deploy Qwen there too (same idea: second service/container with a URL) or run Qwen on ISAAC/GPU and use a tunnel. **QWEN_API_URL** would point to wherever Qwen is (second service or tunnel URL).

Option A is “Qwen as a second web service with a stable URL.” That pattern works on any platform (Render, Fly, Railway, etc.); only the deploy steps differ.

**When to consider not using Render for Qwen:**  
- If you need **GPU** for Qwen (faster inference), Render doesn’t offer GPU. Use Option B (ISAAC + tunnel) or a GPU host (RunPod, Lambda, etc.) for Qwen and keep the main app on Render.
- If you move the whole project to another provider, you can run both the app and Qwen there; Option A’s idea (two services, one URL for Qwen) still applies.

---

## Summary

| Step | What you did |
|------|----------------|
| 1 | New Web Service on Render, same repo |
| 2 | Root Directory: `llm_training`, Runtime: Docker, Dockerfile: `Dockerfile.qwen` |
| 3 | Env: **ALLOWED_ORIGINS** = your main app URL |
| 4 | Deploy, then test `/health` on the Qwen service URL |
| 5 | Main app → Environment → **QWEN_API_URL** = Qwen service URL → Save |
| 6 | Use the app and evaluate with “SpeechGradebook Text + Video Model (Qwen)” |

After this, you never change the Qwen URL again. Going to a paid tier on Render only improves reliability and resources; the setup stays the same.
