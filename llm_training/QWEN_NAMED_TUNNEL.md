# Qwen: Stable URL with a Cloudflare Named Tunnel

Use a **Cloudflare Named Tunnel** so the Qwen service has a **fixed URL** (e.g. `https://qwen.speechgradebook.com`). You set **`QWEN_API_URL`** on Render once; when you start Qwen on ISAAC, the same URL works every time.

**You need:** A domain you control and add to Cloudflare (e.g. a subdomain like `qwen.yourdomain.com`).

---

## 1. One-time setup in Cloudflare

### 1.1 Add your domain to Cloudflare

1. Sign in at [dash.cloudflare.com](https://dash.cloudflare.com).
2. Click **Add a site** and enter your domain (e.g. `yourdomain.com`).
3. Follow the steps to change your domain’s nameservers to Cloudflare’s (or add the domain as a CNAME target if you only use a subdomain).

### 1.2 Create a tunnel

1. In the Cloudflare dashboard, go to **Zero Trust** (or **Networks** → **Tunnels**).
2. Open **Networks** → **Tunnels** (or **Access** → **Tunnels**).
3. Click **Create a tunnel**.
4. Choose **Cloudflared** as the connector type.
5. Enter a name, e.g. **`qwen-speechgradebook`**, and click **Save tunnel**.

### 1.3 Configure the tunnel’s public hostname

1. Under **Public Hostname**, click **Add a public hostname**.
2. **Subdomain:** e.g. **`qwen`** (your URL will be `https://qwen.yourdomain.com`).
3. **Domain:** Select the domain you added (e.g. `yourdomain.com`).
4. **Service type:** **HTTP**.
5. **URL:** **`localhost:8001`** (Qwen runs on port 8001 on the machine where cloudflared runs).
6. Save.

### 1.4 Install cloudflared and log in (one-time, on your laptop)

1. Install cloudflared: [developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. Run:
   ```bash
   cloudflared tunnel login
   ```
   Complete the browser login so Cloudflare can write a cert to `~/.cloudflared/`.

### 1.5 Create the tunnel and get the credentials (one-time)

On your laptop (with cloudflared installed and logged in):

```bash
cloudflared tunnel create qwen-speechgradebook
```

This creates a tunnel and writes credentials to `~/.cloudflared/<TUNNEL_ID>.json`. Note the **Tunnel ID** (e.g. from `ls ~/.cloudflared/` or the command output).

Create a config file so the tunnel knows what to expose. Create **`~/.cloudflared/config.yml`** (or a file you’ll copy to ISAAC) with:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /path/to/<TUNNEL_ID>.json

ingress:
  - hostname: qwen.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
```

Replace `<TUNNEL_ID>` and `qwen.yourdomain.com` with your tunnel ID and the hostname you chose in step 1.3. Use a single path for the credentials file (e.g. on ISAAC: `~/llm_training/.cloudflared/<TUNNEL_ID>.json`).

---

## 2. Copy tunnel files to ISAAC

You need the tunnel credentials and config on the machine where Qwen runs (e.g. an ISAAC compute node).

1. On your laptop, create a folder and copy the credential file:
   ```bash
   mkdir -p ~/qwen-tunnel
   cp ~/.cloudflared/<TUNNEL_ID>.json ~/qwen-tunnel/
   ```
2. Create **`~/qwen-tunnel/config.yml`** with the same content as above, but set `credentials-file` to the path you’ll use on ISAAC (e.g. `~/llm_training/.cloudflared/<TUNNEL_ID>.json`).
3. Copy to ISAAC (from your laptop):
   ```bash
   scp -r ~/qwen-tunnel amcclu12@login.isaac.utk.edu:~/llm_training/.cloudflared
   ```
   Or copy the single credential file and then create `config.yml` on ISAAC in `~/llm_training/.cloudflared/`.

---

## 3. Run Qwen and the named tunnel on ISAAC

On the **ISAAC compute node** (interactive GPU session):

```bash
cd ~/llm_training
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com

# Use your Python 3.10 env (full path so it works without conda activate)
/nfs/home/amcclu12/.conda/envs/qwen/bin/python qwen_serve.py --port 8001 &
sleep 60

# Run the named tunnel (use the config you copied)
cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook
```

If cloudflared isn’t installed on the node, download it once:

```bash
cd ~/llm_training
curl -sL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
./cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook
```

Your stable URL is **`https://qwen.yourdomain.com`** (or whatever hostname you set in the dashboard).

---

## 4. Set the stable URL on Render

1. In **Render** → your SpeechGradebook service → **Environment**.
2. Set **`QWEN_API_URL`** = **`https://qwen.yourdomain.com`** (your actual hostname).
3. Save. You do **not** need to change this again when you restart Qwen; the same URL will work whenever the tunnel is running.

---

## 5. When you restart Qwen

Each time you start a new GPU session on ISAAC:

1. Start Qwen (with `ALLOWED_ORIGINS` set).
2. Start the named tunnel with the same config:  
   `cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook`

No need to update Render; the URL stays the same.

---

## Summary

| Step | Where | Action |
|------|--------|--------|
| 1 | Cloudflare | Add domain, create tunnel, add public hostname (e.g. `qwen.yourdomain.com` → `localhost:8001`). |
| 2 | Laptop | `cloudflared tunnel login`, `cloudflared tunnel create qwen-speechgradebook`, create `config.yml`. |
| 3 | ISAAC | Copy `.json` and `config.yml` to `~/llm_training/.cloudflared/`. |
| 4 | ISAAC | Start Qwen, then run `cloudflared tunnel --config ... run qwen-speechgradebook`. |
| 5 | Render | Set **`QWEN_API_URL`** = `https://qwen.yourdomain.com` once. |

For more detail, see [Cloudflare: Create a tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/).
