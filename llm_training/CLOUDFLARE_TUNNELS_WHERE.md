# Where to find Cloudflare Tunnels

Cloudflare has two dashboards. **Tunnels** are in **Zero Trust**, not the main Cloudflare dashboard.

---

## Direct link (bookmark this)

**https://one.dash.cloudflare.com**

(Sign in with your Cloudflare account if asked.)

---

## After you're in Zero Trust

1. In the **left sidebar**, look for **Networks** (or **Access**).
2. Click **Networks**.
3. Under it, click **Tunnels** (or **Connectors** → **Cloudflare Tunnels**).

You should see a list of your tunnels (e.g. **qwen-speechgradebook**).

---

## If you don't see "Networks" or "Tunnels"

- Some accounts show **Connectors** in the sidebar; click it, then **Cloudflare Tunnels**.
- Or use the **search** at the top of the Zero Trust dashboard and type **tunnels**.
- The URL might look like:  
  `https://one.dash.cloudflare.com/<your-account-id>/networks/tunnels`

---

## Not the same as dash.cloudflare.com

- **dash.cloudflare.com** = main Cloudflare (DNS, domains, etc.). Tunnels are **not** here.
- **one.dash.cloudflare.com** = Zero Trust (Access, Tunnels, etc.). Tunnels **are** here.
