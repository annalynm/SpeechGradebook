# Start Qwen on ISAAC and set it on Render

Follow these steps in order. Your Render app URL: **https://speechgradebook.onrender.com**

---

## Part 1: Start Qwen on ISAAC and get a public URL

### Step 1. SSH to ISAAC and request a GPU session

On your laptop, run:

```bash
ssh amcclu12@login.isaac.utk.edu
```

Then on ISAAC, request an interactive GPU session. **If you get “Invalid qos specification”**, see the troubleshooting box below.

**Option A – try this first (simpler request):**

```bash
srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
```

**Option B – if your cluster requires a specific QOS**, ask OIT or run this to see your allowed partition/account/QOS:

```bash
sacctmgr show user $USER withassoc format=user,account,partition,qos
```

Then use the QOS from that output, for example:

```bash
srun --pty -p campus-gpu --account=ACF-UTK0011 --qos=YOUR_QOS --gres=gpu:1 -t 4:00:00 --mem=24G bash
```

Wait until you get a shell on a compute node (your prompt will show a node name like `clrv0701`).

**Troubleshooting “Invalid qos specification”**

- The partition/account combination may require a **QOS** that you have access to. Run:  
  `sacctmgr show user $USER withassoc format=user,account,partition,qos`  
  and use a `--qos=...` value that appears there (replace `YOUR_QOS` in Option B).
- If you don’t see a suitable QOS, contact **OIT** (or your HPC support) and ask: “What partition, account, and QOS should I use for an interactive GPU job on ISAAC?”
- You can also try **sbatch** with the same options (see `run_qwen_isaac.slurm`) and check the job output; sometimes the batch system gives a clearer error.

### Step 2. Load conda and go to llm_training

In that same shell:

```bash
module load anaconda3
conda activate speechgradebook
cd ~/llm_training
```

### Step 3. Set your Render app URL (required for CORS)

```bash
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
```

### Step 4. Run the script that starts Qwen + public tunnel

Make sure the script is there (if you just copied `llm_training` to ISAAC, it should be). Then run:

```bash
chmod +x run_qwen_with_public_url.sh
./run_qwen_with_public_url.sh
```

- The script will start Qwen (may take a minute), then start a Cloudflare tunnel.
- In the output you’ll see a line like: **`Your quick Tunnel has been created! Visit https://xxxx-xx-xx-xx.trycloudflare.com`**
- **Copy that full `https://….trycloudflare.com` URL** — you’ll paste it into Render in Part 2.

Leave this terminal/session running. If you close it, Qwen and the tunnel stop and the URL will no longer work.

---

## Part 2: Set the URL on Render

1. Open **[Render Dashboard](https://dashboard.render.com)** and sign in.
2. Click your **SpeechGradebook** web service (the one that serves the app).
3. In the left sidebar, click **Environment**.
4. Under **Environment Variables**:
   - If **QWEN_API_URL** already exists, click **Edit** and set its value to the URL you copied (e.g. `https://xxxx-xx-xx-xx.trycloudflare.com`).
   - If it doesn’t exist, click **Add Environment Variable**, set **Key** to `QWEN_API_URL` and **Value** to that same URL.
5. Click **Save Changes**. Render will redeploy your service; wait for the deploy to finish.

After the deploy, everyone using your app on Render can use the **SpeechGradebook Text + Video Model (Qwen)** evaluator.

---

## If you restart Qwen later

Each time you start a new ISAAC session and run `run_qwen_with_public_url.sh`, you’ll get a **new** trycloudflare.com URL. When that happens, repeat **Part 2** and update **QWEN_API_URL** on Render to the new URL.
