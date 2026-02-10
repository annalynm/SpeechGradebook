# Detailed Steps: Process 2 (Config + ISAAC) and Process 3 (Dashboard + Render)

You have the tunnel created from the terminal and the credential file in `~/.cloudflared/`. Follow these for the rest.

---

# Process 2: Config file, credential copy, and copy to ISAAC

## Step 2.1 — Get your tunnel ID

In Terminal:

```bash
ls ~/.cloudflared/*.json
```

You’ll see one file like:  
`/Users/annamcclure/.cloudflared/1a074498-b288-4470-9c7b-37291e8d7bdd.json`

The **tunnel ID** is the filename without `.json`. Example: **`1a074498-b288-4470-9c7b-37291e8d7bdd`**  
Write it down; you’ll use it in the next step.

---

## Step 2.2 — Create the folder and config file

In Terminal:

```bash
mkdir -p ~/qwen-tunnel
nano ~/qwen-tunnel/config.yml
```

`nano` will open. Paste the block below, but first replace:

- **TUNNEL_ID** → the tunnel ID from step 2.1 (e.g. `1a074498-b288-4470-9c7b-37291e8d7bdd`)
- **YOUR_NETID** → your ISAAC username (e.g. `amcclu12`)

Paste this (with your values):

```yaml
tunnel: TUNNEL_ID
credentials-file: /nfs/home/YOUR_NETID/llm_training/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: qwen.speechgradebook.com
    service: http://localhost:8001
  - service: http_status:404
```

Example (tunnel ID `1a074498-b288-4470-9c7b-37291e8d7bdd`, NetID `amcclu12`):

```yaml
tunnel: 1a074498-b288-4470-9c7b-37291e8d7bdd
credentials-file: /nfs/home/amcclu12/llm_training/.cloudflared/1a074498-b288-4470-9c7b-37291e8d7bdd.json

ingress:
  - hostname: qwen.speechgradebook.com
    service: http://localhost:8001
  - service: http_status:404
```

Save and exit nano: **Ctrl+O**, **Enter**, then **Ctrl+X**.

---

## Step 2.3 — Copy the credential file into the folder

Replace **TUNNEL_ID** with your actual tunnel ID from step 2.1:

```bash
cp ~/.cloudflared/TUNNEL_ID.json ~/qwen-tunnel/
```

Example:

```bash
cp ~/.cloudflared/1a074498-b288-4470-9c7b-37291e8d7bdd.json ~/qwen-tunnel/
```

Check that both files are there:

```bash
ls ~/qwen-tunnel/
```

You should see: `config.yml` and `TUNNEL_ID.json`.

---

## Step 2.4 — Copy the folder to ISAAC

From your **laptop**, in Terminal, run (replace **YOUR_NETID** with your ISAAC username):

```bash
scp -r ~/qwen-tunnel YOUR_NETID@login.isaac.utk.edu:~/llm_training/.cloudflared
```

Example (NetID `amcclu12`):

```bash
scp -r ~/qwen-tunnel amcclu12@login.isaac.utk.edu:~/llm_training/.cloudflared
```

- You may be asked for your ISAAC password (or it may use SSH key).
- If `~/llm_training` doesn’t exist on ISAAC yet, create it first:  
  `ssh YOUR_NETID@login.isaac.utk.edu "mkdir -p ~/llm_training"`  
  then run the `scp` again.
- After this, on ISAAC you should have:  
  `~/llm_training/.cloudflared/config.yml`  
  `~/llm_training/.cloudflared/TUNNEL_ID.json`

---

## Step 2.5 — Put the start script on ISAAC and make it executable

The script **start_qwen_stable.sh** must be in `~/llm_training/` on ISAAC.

**Option A — Repo already on ISAAC**

If you’ve already copied or cloned the SpeechGradebook repo to ISAAC so that `~/llm_training/start_qwen_stable.sh` exists:

```bash
ssh YOUR_NETID@login.isaac.utk.edu "chmod +x ~/llm_training/start_qwen_stable.sh"
```

**Option B — Repo not on ISAAC**

From your laptop, copy the script (and the rest of `llm_training` if needed):

```bash
scp /path/to/your/SpeechGradebook\ Repo/llm_training/start_qwen_stable.sh YOUR_NETID@login.isaac.utk.edu:~/llm_training/
ssh YOUR_NETID@login.isaac.utk.edu "chmod +x ~/llm_training/start_qwen_stable.sh"
```

Use the real path to your repo if different (e.g. `"/Users/annamcclure/SpeechGradebook Repo/llm_training/start_qwen_stable.sh"`).

---

# Process 3: Dashboard (public hostname) and Render (QWEN_API_URL)

## Step 3.1 — Confirm or add the public hostname in Cloudflare

1. Go to **[one.dash.cloudflare.com](https://one.dash.cloudflare.com)** and sign in.
2. Left sidebar: **Networks** → **Tunnels** (or **Connectors** → **Cloudflare Tunnels**).
3. Click the tunnel **qwen-speechgradebook**.
4. Look for **Public Hostname** or **Route traffic** / **Published applications**.

**If you already see a hostname** `qwen.speechgradebook.com` → `localhost:8001` (Type HTTP):  
You’re done with the dashboard; go to step 3.2.

**If there is no hostname or it’s wrong:**

1. Click **Add a public hostname** (or **Add hostname** / **Route traffic**).
2. Set:
   - **Subdomain:** `qwen`
   - **Domain:** `speechgradebook.com`
   - **Path:** leave empty
   - **Type:** **HTTP**
   - **URL:** `localhost:8001`
3. Save.

Your fixed URL is **https://qwen.speechgradebook.com**.

---

## Step 3.2 — Set QWEN_API_URL on Render

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in.
2. Click your **main** SpeechGradebook web service (the one that serves the app at speechgradebook.onrender.com or your custom domain).
3. In the left sidebar, click **Environment**.
4. In **Environment Variables**:
   - If **QWEN_API_URL** already exists, click **Edit** and set its value to:  
     **`https://qwen.speechgradebook.com`**
   - If it doesn’t exist, click **Add Environment Variable**:
     - **Key:** `QWEN_API_URL`
     - **Value:** `https://qwen.speechgradebook.com`
5. Important: **no trailing slash** in the value.
6. Click **Save Changes**. Render will redeploy the service; wait for the deploy to finish.

---

## Step 3.3 — (Optional) Test the URL

After the tunnel is running on ISAAC (see “When you want to evaluate” below), from your laptop you can test:

```bash
curl -s https://qwen.speechgradebook.com/health
```

You should get JSON like `{"status":"ok","model":"Qwen2.5-VL-7B"}`.

---

# When you want to evaluate (each time)

1. SSH to ISAAC and start an interactive GPU session, e.g.:  
   `ssh YOUR_NETID@login.isaac.utk.edu`  
   then:  
   `srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash`
2. Run:
   ```bash
   cd ~/llm_training
   module load anaconda3
   conda activate speechgradebook
   ./start_qwen_stable.sh
   ```
3. Leave that terminal open. In the SpeechGradebook app, choose **SpeechGradebook Text + Video Model (Qwen)** and run an evaluation. Traffic goes: app → **https://qwen.speechgradebook.com** → tunnel → Qwen on ISAAC.

You do **not** change QWEN_API_URL on Render again; it stays **https://qwen.speechgradebook.com**.
