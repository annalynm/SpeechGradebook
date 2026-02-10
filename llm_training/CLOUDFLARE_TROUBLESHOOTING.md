# Cloudflare Tunnel Troubleshooting (Qwen)

Common issues and fixes when setting up a Cloudflare tunnel for the Qwen service.

---

## 1. "I can't find where to create a tunnel"

Cloudflare’s UI has changed. Tunnels are in **Cloudflare Zero Trust** (Cloudflare One), not the main DNS dashboard.

**Do this:**

1. Go to **[one.dash.cloudflare.com](https://one.dash.cloudflare.com)** and sign in with your Cloudflare account.
2. In the left sidebar, open **Networks** → **Connectors** → **Cloudflare Tunnels**  
   (or **Networks** → **Tunnels**).
3. Click **Create a tunnel** (or **Create tunnel**).
4. Choose **Cloudflared** → Next → enter a name (e.g. `qwen-speechgradebook`) → **Save tunnel**.

If you don’t see **Zero Trust** or **Networks**:

- You may need to open the **same account** that has your domain. Check the account/team switcher (top left or top bar).
- Some accounts see **Zero Trust** under the main [dash.cloudflare.com](https://dash.cloudflare.com) → left menu. Try **Zero Trust** → **Networks** → **Tunnels**.

Docs: [Create a tunnel (dashboard)](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/).

---

## 2. "I don't have a domain / I haven't added a domain"

Named tunnels need a **domain in Cloudflare**. If you haven’t added one:

- Add a site at [dash.cloudflare.com](https://dash.cloudflare.com) → **Add a site** → enter your domain (e.g. `yourdomain.com`) and follow the steps (including changing nameservers at your registrar).
- Or use the **Quick Tunnel** instead of a named tunnel: no domain needed. On ISAAC, run Qwen, then run:
  ```bash
  cloudflared tunnel --url http://localhost:8001
  ```
  Copy the `https://….trycloudflare.com` URL and set it as **QWEN_API_URL** on Render. The URL changes each time you start the tunnel; see **START_QWEN_FOR_RENDER.md**.

---

## 3. "cloudflared tunnel login" — browser doesn't open or fails

- **Mac:** Make sure you’re not in a restricted environment; try running `cloudflared tunnel login` from a normal Terminal (not from inside an IDE or script that might block the browser).
- **Windows:** Allow the browser to open; if it doesn’t, the command may print a URL — open that URL manually in your browser.
- **Wrong domain:** When the browser opens, choose the **exact domain** you added in Cloudflare (the one you’ll use for the tunnel hostname). If you pick the wrong domain, the tunnel won’t match and public hostnames will fail.

---

## 4. "tunnel create" says tunnel already exists or name in use

- Use a **unique name** (e.g. `qwen-speechgradebook-2` or include your initials).
- Or in the Zero Trust dashboard, **Networks** → **Tunnels**, check if a tunnel with that name already exists. You can use it and add a public hostname, or delete it and create again with `cloudflared tunnel create <name>`.

---

## 5. "Could not find tunnel" or tunnel doesn't connect when running on ISAAC

- The **tunnel name** in the command must match **exactly** what you created (in the dashboard and in `cloudflared tunnel create <name>`). For example:
  ```bash
  cloudflared tunnel --config ~/llm_training/.cloudflared/config.yml run qwen-speechgradebook
  ```
  Here `qwen-speechgradebook` must be the same name you used when creating the tunnel.
- The **credentials file** in `config.yml` must be the path to the **correct** `.json` file (the one for this tunnel) on the machine where you run cloudflared (e.g. ISAAC). Check:
  ```bash
  ls ~/llm_training/.cloudflared/
  ```
  You should see `<TUNNEL_ID>.json` and `config.yml`. The `credentials-file` in `config.yml` must point to that `.json` (and the path must be valid on ISAAC, e.g. `/nfs/home/YOUR_NETID/llm_training/.cloudflared/<TUNNEL_ID>.json`).

---

## 6. Public hostname / "This site can't be reached" or 404

- In Zero Trust → **Networks** → **Tunnels** → your tunnel → **Public Hostname** (or **Public hostnames**):
  - **Subdomain** + **Domain** must match the URL you’re opening (e.g. subdomain `qwen`, domain `yourdomain.com` → `https://qwen.yourdomain.com`).
  - **Service type** = **HTTP**, **URL** = **localhost:8001** (or **Host** = `localhost`, **Port** = `8001`).
- **Qwen must be running** on the same machine where you run cloudflared (e.g. on the ISAAC node), on port 8001. Test on that machine:
  ```bash
  curl -s http://localhost:8001/health
  ```
  You should get JSON like `{"status":"ok",...}`. If not, start Qwen first (`python qwen_serve.py --port 8001 &`), wait for it to load, then start the tunnel.

---

## 7. CORS or "blocked by CORS" when the app calls Qwen

If the **browser** is calling the Qwen URL directly (not via the Render proxy), the Qwen service must allow your app’s origin.

- On the machine where Qwen runs (e.g. ISAAC), set before starting Qwen:
  ```bash
  export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
  ```
  (Use your real Render URL; add multiple origins comma-separated if needed.)
- If you use the **Render proxy** (recommended), the browser only talks to your Render app; Render then calls QWEN_API_URL. In that case CORS on Qwen is less critical, but keeping ALLOWED_ORIGINS set is still good practice.

---

## 8. Quick reference: where things are

| Goal | Where |
|------|--------|
| Add domain | [dash.cloudflare.com](https://dash.cloudflare.com) → Add a site |
| Create tunnel / public hostname | [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → Networks → Connectors → Cloudflare Tunnels |
| Install cloudflared | [Cloudflare: cloudflared downloads](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) or `brew install cloudflared` (Mac) |
| Full named-tunnel steps | **QWEN_NAMED_TUNNEL_WALKTHROUGH.md** |
| Quick tunnel (no domain) | **START_QWEN_FOR_RENDER.md** |

---

If you tell me the **exact step** (e.g. “creating the tunnel in the dashboard,” “cloudflared tunnel login,” “running the tunnel on ISAAC”) and the **error message or what you see**, I can give step-by-step fixes for that part.
