# Fixed hostname + Qwen on ISAAC — Full walkthrough

**Goal:** One URL you set on Render and never change. All Qwen computation runs on ISAAC (GPU).

**You need:** A domain you control (e.g. `yourdomain.com`) to add to Cloudflare. Your ISAAC login (e.g. NetID). Your main app URL (e.g. `https://speechgradebook.onrender.com`).

Do the steps in order. At the end you’ll set one env var on Render and, when you want to evaluate, run one script on ISAAC.

---

## Part 1: Cloudflare (browser)

### 1.1 Add your domain

1. Go to **[dash.cloudflare.com](https://dash.cloudflare.com)** and sign in.
2. Click **Add a site** and enter your domain (e.g. `yourdomain.com`).
3. Choose the **Free** plan and continue.
4. Cloudflare will show two **nameservers** (e.g. `ns1.cloudflare.com`, `ns2.cloudflare.com`).
5. Log in to your **domain registrar** (where you bought the domain) and find the **nameservers** setting for this domain. Replace the existing nameservers with the two from Cloudflare. Save.
6. Back in Cloudflare, click **Done, check nameservers**. Wait until the status is **Active** (can take a few minutes).

### 1.2 Open Zero Trust and create a tunnel

1. Go to **[one.dash.cloudflare.com](https://one.dash.cloudflare.com)** (Cloudflare Zero Trust). Sign in with the same account.
2. In the **left sidebar**, click **Networks** → **Connectors** → **Cloudflare Tunnels** (or **Networks** → **Tunnels**).
3. Click **Create a tunnel** (or **Create tunnel**).
4. Choose **Cloudflared** → **Next**.
5. **Tunnel name:** type `qwen-speechgradebook` (or any name — you’ll use this exact name later). Click **Save tunnel**.

### 1.3 Add the public hostname (your fixed URL)

1. On the tunnel’s page, find **Public Hostname** (or **Public hostnames**). Click **Add a public hostname** (or **Add hostname**).
2. Set:
   - **Subdomain:** `qwen`  
     (Your URL will be `https://qwen.yourdomain.com` — use your real domain.)
   - **Domain:** Select the domain you added (e.g. `yourdomain.com`).
   - **Service type:** **HTTP**.
   - **URL:** `localhost:8001`  
     (If it asks for Host and Port separately: Host `localhost`, Port `8001`.)
3. Click **Save**.

**Write this down:** Your fixed URL is **`https://qwen.yourdomain.com`** (replace with your real subdomain and domain). You’ll use it on Render in Part 4.

---

## Part 2: Laptop — cloudflared and tunnel credentials

### 2.1 Install cloudflared

**Mac (Homebrew):**
```bash
brew install cloudflared
```

**Mac (no Homebrew):** Download the Mac build from [Cloudflare cloudflared downloads](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) and put `cloudflared` in your PATH.

**Windows:** Download the Windows build from the same page and put `cloudflared.exe` in a folder in your PATH.

Check:
```bash
cloudflared --version
```

### 2.2 Log in to Cloudflare (one-time)

In Terminal (Mac/Linux) or PowerShell (Windows):

```bash
cloudflared tunnel login
```

A browser window opens. Select the **same domain** you added in Part 1 (e.g. `yourdomain.com`) and allow. This saves a certificate under `~/.cloudflared/`.

### 2.3 Create the tunnel and get the credential file

Use the **exact same tunnel name** you used in step 1.2 (e.g. `qwen-speechgradebook`):

```bash
cloudflared tunnel create qwen-speechgradebook
```

The output shows a **Tunnel ID** (a long hex string like `abcd1234-5678-90ab-cdef-1234567890ab`). List the credential file:

```bash
ls ~/.cloudflared/*.json
```

You’ll see one file like `abcd1234-5678-90ab-cdef-1234567890ab.json`. **Note the tunnel ID** (the filename without `.json`). You’ll need it in the next step and when copying to ISAAC.

### 2.4 Create the config file for ISAAC

Create a config that will run **on ISAAC**. The `credentials-file` path must be the path **on ISAAC**, not on your laptop.

Replace in the block below:
- **TUNNEL_ID** → the tunnel ID from the `.json` filename (e.g. `abcd1234-5678-90ab-cdef-1234567890ab`).
- **YOUR_NETID** → your ISAAC username (e.g. `amcclu12`).
- **qwen.yourdomain.com** → the hostname you set in step 1.3 (your real subdomain + domain).

**On your laptop**, create a folder and the config:

```bash
mkdir -p ~/qwen-tunnel
nano ~/qwen-tunnel/config.yml
```

Paste this (with your values substituted):

```yaml
tunnel: TUNNEL_ID
credentials-file: /nfs/home/YOUR_NETID/llm_training/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: qwen.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
```

Save (in nano: Ctrl+O, Enter, Ctrl+X).

Copy the credential file into the same folder (use your real tunnel ID):

```bash
cp ~/.cloudflared/TUNNEL_ID.json ~/qwen-tunnel/
```

Example:
```bash
cp ~/.cloudflared/abcd1234-5678-90ab-cdef-1234567890ab.json ~/qwen-tunnel/
```

---

## Part 3: Copy tunnel files to ISAAC and get the script

### 3.1 Copy the folder to ISAAC

From your **laptop**, run (replace **YOUR_NETID** with your ISAAC username; use your cluster host if not `login.isaac.utk.edu`):

```bash
scp -r ~/qwen-tunnel YOUR_NETID@login.isaac.utk.edu:~/llm_training/.cloudflared
```

Example:
```bash
scp -r ~/qwen-tunnel amcclu12@login.isaac.utk.edu:~/llm_training/.cloudflared
```

After this, on ISAAC you should have:
- `~/llm_training/.cloudflared/config.yml`
- `~/llm_training/.cloudflared/<TUNNEL_ID>.json`

### 3.2 Copy the start script to ISAAC (if not already there)

If your repo (with `llm_training/start_qwen_stable.sh`) is already on ISAAC (e.g. you cloned or rsync the repo), you’re set. Otherwise, copy the script from your repo into `~/llm_training/start_qwen_stable.sh` on ISAAC and run:

```bash
chmod +x ~/llm_training/start_qwen_stable.sh
```

---

## Part 4: Set the fixed URL on Render

1. Open **[dashboard.render.com](https://dashboard.render.com)** and select your **main** SpeechGradebook service (the one that serves the app).
2. Go to **Environment** in the left sidebar.
3. Add or edit **QWEN_API_URL**:
   - **Key:** `QWEN_API_URL`
   - **Value:** your fixed URL from step 1.3, e.g. **`https://qwen.yourdomain.com`** (no trailing slash; use your real hostname).
4. Click **Save Changes**. Render will redeploy. Wait for the deploy to finish.

You will not need to change this again when you start or stop Qwen on ISAAC.

---

## Part 5: Run Qwen + tunnel on ISAAC (each time you want to evaluate)

When you want to run evaluations with Qwen:

1. **SSH to ISAAC** and start an interactive GPU session (use your partition/account; adjust if your cluster is different):

   ```bash
   ssh YOUR_NETID@login.isaac.utk.edu
   srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
   ```

2. **Load the environment and run the script:**

   ```bash
   cd ~/llm_training
   module load anaconda3
   conda activate speechgradebook
   ./start_qwen_stable.sh
   ```

3. Leave that terminal open. The script starts Qwen, then the tunnel. Your fixed URL (`https://qwen.yourdomain.com`) will point at Qwen on this node.

4. In the SpeechGradebook app, run an evaluation and choose **SpeechGradebook Text + Video Model (Qwen)**. The request goes: Render app → your fixed URL → tunnel → ISAAC (GPU).

5. When you’re done evaluating, you can close the SSH session (that stops Qwen and the tunnel). Next time, repeat from step 1; the URL on Render stays the same.

---

## Checklist

| Part | What you did |
|------|----------------|
| 1 | Added domain to Cloudflare; created tunnel; added public hostname `qwen.yourdomain.com` → `localhost:8001`. |
| 2 | Installed cloudflared; ran `tunnel login` and `tunnel create`; created `config.yml` and copied credential to `~/qwen-tunnel/`. |
| 3 | Copied `~/qwen-tunnel` to ISAAC as `~/llm_training/.cloudflared/`; ensured `start_qwen_stable.sh` is on ISAAC and executable. |
| 4 | Set **QWEN_API_URL** on Render to `https://qwen.yourdomain.com` (your real hostname). |
| 5 | Each time: SSH → GPU session → `cd ~/llm_training && ./start_qwen_stable.sh`; then use the app to evaluate with Qwen. |

**Result:** One URL set on Render; computing stays on ISAAC; no changing the URL when you restart.
