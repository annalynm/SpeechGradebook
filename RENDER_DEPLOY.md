# Deploying SpeechGradebook on Render

## Why login shows "Invalid API key"

The app loads Supabase credentials from **environment variables** via the dynamic `/config.js` endpoint. If `SUPABASE_URL` or `SUPABASE_ANON_KEY` are not set on Render, the browser gets empty values and Supabase returns **Invalid API key** — so login cannot work.

## Fix: Set environment variables on Render

1. Open [Render Dashboard](https://dashboard.render.com) and select your **speechgradebook** web service.
2. Go to **Environment** (left sidebar).
3. Add these variables (use your real values from Supabase):

   | Key | Value |
   |-----|--------|
   | `SUPABASE_URL` | Your Supabase project URL, e.g. `https://xxxxxxxx.supabase.co` |
   | `SUPABASE_ANON_KEY` | Your Supabase **anon** (public) key from Supabase Dashboard → **Settings** → **API** → "Project API keys" → **anon public** |

   Do **not** use the `service_role` key in the browser; use only the **anon** key.

4. Click **Save Changes**. Render will redeploy the service so the new env vars are used.
5. After the deploy finishes, reload your app and try logging in again.

## Optional env vars

- **ALLOWED_ORIGINS** – Comma-separated origins for CORS (default: same origin).
- **QWEN_API_URL** – If you use the SpeechGradebook Text + Video Model (Qwen) service for video/rubric analysis. To run Qwen for all users (not locally), deploy the Qwen service separately and set this to its public URL. See **llm_training/QWEN_SETUP.md** (section “Running the Qwen service for all users”).
- **MODEL_PATH** / **LOAD_IN_8BIT** – For serving the SpeechGradebook Text Model (Mistral) on the same service (optional).

## Qwen evaluations on Render (what to set for QWEN_API_URL)

**Do not use** `http://0.0.0.0:8001` for **QWEN_API_URL**. `0.0.0.0` is a bind address (the Qwen *server* listens on that); it is not a URL the main app can use to *reach* Qwen. The main app needs a **public URL** that points to where Qwen is actually running.

**Set QWEN_API_URL to one of these:**

| Where Qwen runs | QWEN_API_URL value |
|-----------------|---------------------|
| **Second Render Web Service** (Qwen deployed on Render) | Your Qwen service’s URL, e.g. `https://qwen-speechgradebook.onrender.com` (no port; use HTTPS). Find it in the Render dashboard on that service’s page. |
| **ISAAC + Cloudflare Quick Tunnel** | The tunnel URL, e.g. `https://xxxx.trycloudflare.com`. Update this each time you start a new tunnel (see **llm_training/START_QWEN_FOR_RENDER.md**). |
| **ISAAC + Cloudflare Named Tunnel** (fixed hostname) | Your stable URL, e.g. `https://qwen.yourdomain.com` (see **llm_training/QWEN_NAMED_TUNNEL.md**). |

After changing **QWEN_API_URL** on the **main** SpeechGradebook service, save the environment and let Render redeploy. The app proxies requests to Qwen via `/qwen-api/*`, so the main service must be able to reach the URL you set.

## Video compression returns 502

When an instructor uploads a **video over 50 MB**, the app asks the server to compress it so it can be stored in Supabase. On Render’s **default Python runtime**, **ffmpeg is not installed**, so the `/api/compress_video` endpoint fails and the browser may see a **502 Bad Gateway**.

**Options:**

1. **Use Docker on Render** (recommended if you need server-side compression)  
   When creating or configuring the web service, set **Language** to **Docker** (not Python). Render will build from your repo’s `Dockerfile`, which installs ffmpeg. Redeploy so the new runtime is used.

2. **Keep Python and ask users to upload smaller videos**  
   If you stay on the Python runtime, do not rely on server compression. Instruct users to upload videos **under 50 MB** (e.g. shorten the clip or compress with a local tool). The app will show a clear message when compression fails and still allow **Continue** so they can run the evaluation; the video just won’t be saved to storage or used for training.

The in-app message when compression fails (502/5xx) explains this and lets the user continue to evaluate.

## Custom domain (e.g. speechgradebook.com)

Yes. You can set your Render service to use **speechgradebook.com** (or any domain you own).

1. In the **Render Dashboard**, open your **SpeechGradebook** web service.
2. Go to **Settings** (left sidebar) and find **Custom Domains**.
3. Click **Add Custom Domain** and enter **speechgradebook.com** (and optionally **www.speechgradebook.com**).
4. Render will show the DNS records you need (usually a **CNAME** for `www` and an **A** or **CNAME** for the root).
5. In your **domain registrar** (or DNS provider, e.g. Cloudflare), add those records so they point to the host Render gives you (e.g. `your-service.onrender.com`).
6. Wait for DNS to propagate; Render will issue SSL for the custom domain.

After that, the app will be reachable at **https://speechgradebook.com** (and **https://www.speechgradebook.com** if you added it). No code changes are required.

## 403 on Fonts (css2)

The app uses Bunny Fonts (`fonts.bunny.net`) instead of Google Fonts to reduce 403s from ad-blockers. If you still see font-load errors, the app falls back to system fonts and continues to work.

## Submit to ISAAC returns 502 (Permission denied)

When you click **Submit Mistral training to ISAAC** (or **Submit Qwen training to ISAAC**) in Platform Analytics → LLM Export, the server runs `run_training.sh` which rsyncs to UT ISAAC and submits a SLURM job. If you see **502** with `Permission denied (gssapi-keyex,gssapi-with-mic,keyboard-interactive,hostbased)` and `rsync: connection unexpectedly closed`:

**Cause:** The Render server cannot SSH to ISAAC. On Render, `run_config.env` is not present (it is gitignored), so all ISAAC connection settings must come from Render **Environment** variables.

**Fix:** In Render Dashboard → your service → **Environment**, add:

| Key | Value |
|-----|--------|
| `ISAAC_USER` | Your UT NetID, e.g. `amcclu12` |
| `ISAAC_HOST` | `login.isaac.utk.edu` |
| `ISAAC_REMOTE_DIR` | Remote path, e.g. `~/llm_training` |
| `ISAAC_SSH_PRIVATE_KEY` | **Full contents** of your SSH private key (the one whose public key is in `~/.ssh/authorized_keys` on ISAAC) |
| `RENDER_LLM_EXPORT_SECRET` | Any secret string; enter the same value in the app's "API secret" field when submitting |

**Optional** (for SLURM job):

| Key | Value |
|-----|--------|
| `ISAAC_PARTITION` | e.g. `campus-gpu` |
| `ISAAC_ACCOUNT` | e.g. `ACF-UTK0011` |
| `ISAAC_TIME` | e.g. `04:00:00` |
| `ISAAC_GPU_COUNT` | e.g. `1` |

**Important:**

1. **ISAAC_SSH_PRIVATE_KEY** — Paste the **entire** private key, including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`. Render will use this for SSH/rsync to ISAAC. Do not use your normal password-based login; use key-based auth.

2. **Public key on ISAAC** — Ensure the matching public key is in `~/.ssh/authorized_keys` on ISAAC for `ISAAC_USER`. Test locally: `ssh -i /path/to/your/key ISAAC_USER@login.isaac.utk.edu`.

3. **ISAAC_USER** — Verify your NetID (e.g. `amcclu12`) is correct. If unsure, log in to ISAAC via OIT and confirm.

After adding these variables, save the environment and let Render redeploy. Then try **Submit to ISAAC** again.
