# Cloudflare Named Tunnel for Qwen — Easy Step-by-Step

This gives Qwen a **permanent URL** (e.g. `https://qwen.yourdomain.com`). You set it once on Render and never change it when you restart Qwen on ISAAC.

**Before you start you need:**
- A **domain** you control (e.g. `yourdomain.com`) — you’ll add it to Cloudflare.
- Your **ISAAC login** (e.g. NetID) and **Render app URL** (e.g. `https://speechgradebook.onrender.com`).

**You’ll do 4 things:** Cloudflare (browser) → Laptop (terminal) → ISAAC (copy files + run Qwen + tunnel) → Render (one env var).

---

## Part A: Cloudflare (in your browser)

### Step A1: Add your domain to Cloudflare

1. Go to **[dash.cloudflare.com](https://dash.cloudflare.com)** and sign in.
2. Click **“Add a site”** (or **“Add site”**).
3. Enter your domain (e.g. `yourdomain.com`) and continue.
4. Pick a plan (Free is enough).
5. Cloudflare will show **nameservers** (e.g. `ns1.cloudflare.com`, `ns2.cloudflare.com`). In your **domain registrar** (where you bought the domain), change the domain’s **nameservers** to these two. Save.
6. Back in Cloudflare, click **“Done, check nameservers.”** It may take a few minutes to turn green (Active). You can continue once the site is added.

*If you only have a subdomain:* You can add the root domain to Cloudflare and use a subdomain for Qwen (e.g. `qwen.yourdomain.com`), or use Cloudflare for Teams with a hostname that points to your tunnel.

### Step A2: Create a tunnel

1. In the Cloudflare dashboard, open **Zero Trust** (left sidebar).  
   - *If you don’t see Zero Trust:* Try **Networks** → **Tunnels**, or **Access** → **Tunnels**, depending on your account.
2. Go to **Networks** → **Tunnels** (or **Access** → **Tunnels**).
3. Click **“Create a tunnel”** (or **“Create tunnel”**).
4. Choose **“Cloudflared”** as the connector.
5. **Tunnel name:** e.g. `qwen-speechgradebook` → **Save tunnel**.

### Step A3: Add the public hostname (your permanent URL)

1. On the tunnel’s page, find **“Public Hostname”** (or **“Public hostnames”**).
2. Click **“Add a public hostname”** (or **“Add hostname”**).
3. Fill in:
   - **Subdomain:** `qwen` (or any name you like). Your URL will be `https://qwen.yourdomain.com`.
   - **Domain:** Choose the domain you added (e.g. `yourdomain.com`).
   - **Service type:** **HTTP**.
   - **URL:** **`localhost:8001`** (no `http://` needed in some UIs; if it asks for host and port, use `localhost` and `8001`).
4. **Save**.

Write down your URL: **`https://qwen.yourdomain.com`** (replace with your real subdomain + domain). You’ll use it on Render later.

---

## Part B: Laptop — install cloudflared and create tunnel credentials

### Step B1: Install cloudflared

- **Mac (Homebrew):**  
  `brew install cloudflared`
- **Mac (manual):** Download from [Cloudflare: cloudflared downloads](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) and put the binary in your PATH.
- **Windows:** Download the Windows build from the same page and run it from a folder in your PATH.

Check:

```bash
cloudflared --version
```

### Step B2: Log in (one-time)

In Terminal (or PowerShell):

```bash
cloudflared tunnel login
```

A browser window opens. Pick the domain you added (e.g. `yourdomain.com`) and allow. This saves a cert under `~/.cloudflared/`.

### Step B3: Create the tunnel and get the credential file

Use the **exact same tunnel name** you used in Cloudflare (e.g. `qwen-speechgradebook`):

```bash
cloudflared tunnel create qwen-speechgradebook
```

The output will show a **Tunnel ID** (long hex string). List the credential file:

```bash
ls ~/.cloudflared/*.json
```

You’ll see something like `~/.cloudflared/abcd1234-5678-90ab-cdef-1234567890ab.json`. **Note this filename** (the ID part) — you’ll use it in the config and when copying to ISAAC.

### Step B4: Create the config file on your laptop

Create a config that points your hostname to `localhost:8001`. Replace:
- `TUNNEL_ID` → the tunnel ID from the `.json` filename (e.g. `abcd1234-5678-90ab-cdef-1234567890ab`).
- `qwen.yourdomain.com` → the hostname you set in Step A3.

**On Mac/Linux**, create the file:

```bash
nano ~/.cloudflared/config.yml
```

Paste this (with your values):

```yaml
tunnel: TUNNEL_ID
credentials-file: /nfs/home/YOUR_NETID/llm_training/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: qwen.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
```

- Replace **`TUNNEL_ID`** in both places with your actual tunnel ID.
- Replace **`YOUR_NETID`** with your ISAAC/UTK NetID (the path will be used on ISAAC).
- Replace **`qwen.yourdomain.com`** with your real hostname.

Save (in nano: Ctrl+O, Enter, then Ctrl+X).

---

## Part C: Copy tunnel files to ISAAC

You’ll put the credential and config on ISAAC so the tunnel can run next to Qwen.

### Step C1: Create a folder and copy the credential file

On your **laptop** (use your real tunnel ID and NetID):

```bash
mkdir -p ~/qwen-tunnel
cp ~/.cloudflared/<TUNNEL_ID>.json ~/qwen-tunnel/
```

Example (fake ID):

```bash
cp ~/.cloudflared/abcd1234-5678-90ab-cdef-1234567890ab.json ~/qwen-tunnel/
```

### Step C2: Copy config for ISAAC

Create a config that uses the path **on ISAAC** (so the credentials-file path must be the ISAAC path):

```bash
nano ~/qwen-tunnel/config.yml
```

Paste (replace TUNNEL_ID, YOUR_NETID, and hostname):

```yaml
tunnel: TUNNEL_ID
credentials-file: /nfs/home/YOUR_NETID/llm_training/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: qwen.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
```

Save.

### Step C3: Copy the folder to ISAAC

From your **laptop** (replace `YOUR_NETID` with your ISAAC username and `login.isaac.utk.edu` if your cluster uses a different host):

```bash
scp -r ~/qwen-tunnel YOUR_NETID@login.isaac.utk.edu:~/llm_training/.cloudflared
```

Example:

```bash
scp -r ~/qwen-tunnel amcclu12@login.isaac.utk.edu:~/llm_training/.cloudflared
```

So on ISAAC you’ll have:
- `~/llm_training/.cloudflared/<TUNNEL_ID>.json`
- `~/llm_training/.cloudflared/config.yml`

---

## Part D: Run Qwen and the tunnel on ISAAC

Do this **on ISAAC** in an **interactive GPU session** (same way you usually run Qwen).

### Step D1: SSH and get a GPU node

```bash
ssh YOUR_NETID@login.isaac.utk.edu
srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
```

Use your partition/account/QOS if different (see START_QWEN_FOR_RENDER.md if you get “Invalid qos specification”).

### Step D2: Load environment and go to llm_training

```bash
module load anaconda3
conda activate speechgradebook
cd ~/llm_training
```

### Step D3: Set CORS for your Render app

Use your **actual** Render app URL:

```bash
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
```

### Step D4: Start Qwen in the background

```bash
python qwen_serve.py --port 8001 &
```

Wait for the model to load (about 1–2 minutes). You can check with:

```bash
curl -s http://localhost:8001/health
```

You should see something like `{"status":"ok",...}`.

### Step D5: Run the named tunnel

If **cloudflared** is already on the node (or in your PATH):

```bash
cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook
```

If **cloudflared is not installed** on the compute node, download it once in the same session:

```bash
cd ~/llm_training
curl -sL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
./cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook
```

Leave this terminal open. While this is running, **`https://qwen.yourdomain.com`** will point at Qwen on this node.

Test from your laptop (use your real hostname):

```bash
curl -s https://qwen.yourdomain.com/health
```

You should get the same health JSON.

---

## Part E: Set the permanent URL on Render

1. Open **[Render Dashboard](https://dashboard.render.com)** → your **SpeechGradebook** service.
2. Go to **Environment**.
3. Add or edit **`QWEN_API_URL`** and set it to your **stable URL** (no trailing slash):
   - **Value:** `https://qwen.yourdomain.com`  
   (use the exact hostname you set in Cloudflare and used in the config.)
4. **Save Changes.** Render will redeploy. After deploy, the app will use this URL for Qwen.

You **do not** need to change this again when you restart Qwen; the URL is permanent.

---

## When you restart Qwen later

Each time you start a **new** ISAAC GPU session:

1. Start Qwen (with `ALLOWED_ORIGINS` set):  
   `python qwen_serve.py --port 8001 &`  
   (and wait for it to load).
2. Start the tunnel:  
   `cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook`

You do **not** need to change anything on Render; the same URL keeps working.

---

## Quick checklist

| # | Where | What you did |
|---|--------|----------------|
| A | Cloudflare | Added domain, created tunnel, added hostname `qwen.yourdomain.com` → `localhost:8001`. |
| B | Laptop | Installed cloudflared, `tunnel login`, `tunnel create`, created `config.yml`. |
| C | Laptop → ISAAC | Copied `.json` and `config.yml` to `~/llm_training/.cloudflared/` on ISAAC. |
| D | ISAAC | Started Qwen on port 8001, then ran `cloudflared tunnel ... run qwen-speechgradebook`. |
| E | Render | Set **`QWEN_API_URL`** = `https://qwen.yourdomain.com`. |

**Permanent URL:** `https://qwen.yourdomain.com` — set once on Render, reuse every time you run Qwen + tunnel on ISAAC.

For more detail, see **QWEN_NAMED_TUNNEL.md** and [Cloudflare: Create a tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/).

---

## Optional: Use a path-based URL (e.g. speechgradebook.com/qwen)

If you get the domain **speechgradebook.com** and want Qwen at **https://speechgradebook.com/qwen** (instead of a subdomain like qwen.speechgradebook.com), you can.

**1. Cloudflare — public hostname**

When you add the tunnel’s public hostname (Part A, Step A3), use:

- **Subdomain:** leave **empty** (or use `www` if you want the main site at www.speechgradebook.com).
- **Domain:** `speechgradebook.com`
- **Path:** `qwen` or `qwen/*` (so only `https://speechgradebook.com/qwen` and below go to the tunnel.)
- **Service type:** HTTP  
- **URL:** `localhost:8001`

So the main site (e.g. your app on Render) can live at **speechgradebook.com** and Qwen at **speechgradebook.com/qwen**. You may need a separate DNS record or Cloudflare route for the root (speechgradebook.com) pointing to Render; the tunnel only handles `/qwen`.

**2. Start Qwen with a root path**

The Qwen server must serve under `/qwen` so that `/qwen/health`, `/qwen/evaluate_video`, etc. work. On ISAAC (Part D), start Qwen with:

```bash
python qwen_serve.py --port 8001 --root-path qwen &
```

Then start the tunnel as before. Requests to `https://speechgradebook.com/qwen/health` will hit the tunnel and reach Qwen at `/qwen/health` on localhost.

**3. Render**

Set **`QWEN_API_URL`** = **`https://speechgradebook.com/qwen`** (no trailing slash). The app and proxy will call `https://speechgradebook.com/qwen/health`, `https://speechgradebook.com/qwen/evaluate_video`, etc., and the Qwen server will respond because it’s mounted at `/qwen`.
