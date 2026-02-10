# Running Qwen on ISAAC (GPU) for Faster Rubric & Video Analysis

Running the Qwen2.5-VL service on ISAAC’s GPU makes rubric extraction and video analysis much faster than on a laptop CPU (often 10–30x).

---

## Accessing ISAAC (first time)

- **What is ISAAC?** UT’s high-performance computing cluster. You get a GPU node to run the Qwen model.
- **Get access:** If you don’t have an account yet, request one via [OIT – Isaac / HPC](https://oit.utk.edu/hpsc/isaac-open-enclave-new-kpb/) (or your department’s HPC contact). You’ll need your **NetID** and a **SLURM account** (and partition, e.g. `campus-gpu`).
- **SSH:** From your laptop, use VPN if you’re off-campus, then:
  ```bash
  ssh amcclu12@login.isaac.utk.edu
  ```
- **Partition and account:** Check OIT’s “Running Jobs” or your allocation email for the correct `--partition` (e.g. `campus-gpu`) and `--account` name. You’ll use these in the SLURM script or in `run_config.env`.

---

## Quick checklist

**For local use (laptop + tunnel):**

| # | Where | What to do |
|---|--------|------------|
| 1 | Your machine | Copy `llm_training` to ISAAC (one-time) |
| 2 | ISAAC | One-time: create conda env, `pip install -r requirements-qwen.txt` |
| 3 | ISAAC | Edit SLURM script: set partition & account (or use `run_config.env`) |
| 4 | ISAAC or laptop | Start Qwen: **interactive** (Option A) or **batch** (Option C) |
| 5 | Your laptop | Open SSH tunnel: `ssh -L 8001:localhost:8001 ...` |
| 6 | Your machine | Set `QWEN_API_URL=http://localhost:8001` and run SpeechGradebook |

**For Render (all users):** Do steps 1–3, then see **[Exposing Qwen for Render (all users)](#exposing-qwen-for-render-all-users)** below: start Qwen on ISAAC, run a Cloudflare Quick Tunnel (or use a stable URL), set `ALLOWED_ORIGINS` and Render’s `QWEN_API_URL`.

---

## One-time setup on ISAAC

### 1. Copy `llm_training` to ISAAC

From your computer, in the **repo root** (the folder that contains `llm_training`):

```bash
cd "/Users/annamcclure/SpeechGradebook Repo"
scp -r llm_training amcclu12@login.isaac.utk.edu:~/
```

Use VPN if required for off-campus access.

### 2. Log in to ISAAC and create the environment

```bash
ssh amcclu12@login.isaac.utk.edu
cd ~/llm_training
```

### 3. Load Conda and install Qwen dependencies

```bash
module load anaconda3
conda create -n speechgradebook python=3.10 -y
conda activate speechgradebook
pip install -r requirements-qwen.txt
```

This installs `torch`, `torchvision`, `transformers`, `qwen_serve.py` dependencies, etc. The first time you run the service, the Qwen model (~16 GB) will be downloaded into `~/llm_training/cache/`.

### 4. (Optional) Hugging Face token

If you hit rate limits downloading the model:

1. Create a token at https://huggingface.co/settings/tokens  
2. On ISAAC: `echo 'HF_TOKEN=hf_xxxx' > ~/llm_training/.env_isaac`

### 5. Create logs directory and config for SLURM

```bash
mkdir -p ~/llm_training/logs
```

Copy the SLURM config from your training setup (same partition/account as `train_speechgradebook.slurm`). Edit `run_qwen_isaac.slurm` and replace:

- `PARTITION_PLACEHOLDER` → your GPU partition (e.g. `campus-gpu`)
- `ACCOUNT_PLACEHOLDER` → your SLURM account

If you already use ISAAC for training (e.g. `run_training.sh`), reuse the same `run_config.env`; it already has `ISAAC_PARTITION` and `ISAAC_ACCOUNT`. If not, create `run_config.env` in `llm_training` from `run_config.env.example` and set at least:

- **ISAAC_USER** – your UT NetID  
- **ISAAC_HOST** – `login.isaac.utk.edu`  
- **ISAAC_PARTITION** – e.g. `campus-gpu`  
- **ISAAC_ACCOUNT** – your SLURM account name  

---

## Running Qwen on ISAAC

You can run the Qwen service in two ways: **interactive** (recommended the first time) or **batch**.

### Option A: Interactive GPU session (recommended first)

1. **Request an interactive GPU job**

   On ISAAC:

   ```bash
   cd ~/llm_training
   srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 --mem=24G bash
   ```

   If you get **“Invalid qos specification”**, run `sacctmgr show user $USER withassoc format=user,account,partition,qos` to see allowed QOS, then add `--qos=YOUR_QOS` to the command, or ask OIT for the correct partition/account/QOS.

   You’ll get a shell on a compute node (e.g. `clrv0701`).

2. **Start the Qwen service on that node**

   In that same shell:

   ```bash
   module load anaconda3
   conda activate speechgradebook
   cd ~/llm_training
   python qwen_serve.py --port 8001
   ```

   Leave this running. Note the **hostname** (e.g. `clrv0701`) shown in your prompt.

3. **Create an SSH tunnel from your laptop**

   On your **laptop** (new terminal):

   ```bash
   ssh -L 8001:localhost:8001 -J amcclu12@login.isaac.utk.edu amcclu12@NODE_NAME
   ```

   Example (replace `clrv0701` with the node name from your prompt):

   ```bash
   ssh -L 8001:localhost:8001 -J amcclu12@login.isaac.utk.edu amcclu12@clrv0701
   ```

   If your cluster does not allow SSH from the login node to the compute node by name, use the **reverse tunnel** method below instead.

4. **Use SpeechGradebook**

   - Keep the interactive job and the SSH tunnel running.
   - In `.env` (or SpeechGradebook config) set: `QWEN_API_URL=http://localhost:8001`
   - Run SpeechGradebook locally; rubric upload and video analysis will use Qwen on ISAAC’s GPU.

### Option B: Reverse tunnel (when you can’t SSH from login to compute node)

From the **compute node** (inside your interactive job, in another shell or background):

```bash
ssh -f -N -R 8001:localhost:8001 login.isaac.utk.edu
```

Then on your **laptop**:

```bash
ssh -L 8001:localhost:8001 amcclu12@login.isaac.utk.edu
```

SpeechGradebook with `QWEN_API_URL=http://localhost:8001` will then use Qwen on ISAAC.

### Option C: Batch job (run_qwen_isaac.slurm)

1. **From your laptop (recommended)** — use the same ISAAC config as training:

   In **`llm_training`** on your computer, create `run_config.env` from the example (if you don’t have it yet):

   ```bash
   cd "/Users/annamcclure/SpeechGradebook Repo/llm_training"
   cp run_config.env.example run_config.env
   # Edit run_config.env: set ISAAC_USER (your NetID), ISAAC_ACCOUNT, ISAAC_PARTITION, ISAAC_HOST
   ```

   Then run:

   ```bash
   chmod +x run_qwen_isaac.sh
   ./run_qwen_isaac.sh
   ```

   This copies the SLURM script to ISAAC, substitutes partition/account from `run_config.env`, and submits the job.

   **Or submit from ISAAC:** edit `run_qwen_isaac.slurm` on ISAAC (replace `PARTITION_PLACEHOLDER` and `ACCOUNT_PLACEHOLDER`), then `cd ~/llm_training && sbatch run_qwen_isaac.slurm`.

3. **Wait for the job to start**

   From your laptop:
   ```bash
   ssh amcclu12@login.isaac.utk.edu 'squeue -u $USER'
   ```

   When the job is `RUNNING`, check the output file (replace `JOBID` with the actual job ID from squeue):
   ```bash
   ssh amcclu12@login.isaac.utk.edu 'tail -f ~/llm_training/logs/qwen_serve_JOBID.out'
   ```

   You’ll see the compute node name and a reminder for the tunnel command.

4. **Create the tunnel from your laptop**

   Use the command printed in the log (same as in Option A step 3), with the actual node name. If the script set up a reverse tunnel successfully, you can instead use:

   ```bash
   ssh -L 8001:localhost:8001 amcclu12@login.isaac.utk.edu
   ```

5. **Use SpeechGradebook** as in Option A step 4.

---

## Summary

| Step | Where | Action |
|------|--------|--------|
| 1 | Your machine | Copy `llm_training` to ISAAC |
| 2 | ISAAC | Conda env + `pip install -r requirements-qwen.txt` |
| 3 | ISAAC | Run Qwen (interactive or batch) |
| 4 | Your laptop | `ssh -L 8001:localhost:8001 ...` (and optionally reverse tunnel) |
| 5 | Your laptop | `QWEN_API_URL=http://localhost:8001` and run SpeechGradebook |

Once the tunnel is up and Qwen is running on ISAAC, rubric uploads and video analysis that use Qwen will run on the GPU and complete much faster than on a laptop CPU.

---

## Exposing Qwen for Render (all users)

When SpeechGradebook runs on **Render**, the app and users’ browsers need to reach the Qwen service over the **public internet**. ISAAC nodes are only reachable from your laptop via SSH tunnel, so you must expose Qwen with a **public URL**. Two practical options:

### Option 1: Cloudflare Quick Tunnel (no account, URL changes each run)

This gives you a public HTTPS URL (e.g. `https://xxxx.trycloudflare.com`) so Render and all users can call Qwen. The URL is **new every time** the job starts, so you’ll update `QWEN_API_URL` on Render each time you start Qwen on ISAAC (good for scheduled or occasional use).

**1. Install cloudflared on the ISAAC compute node**

In an **interactive GPU session** on ISAAC (after `srun ... bash` and `conda activate speechgradebook`):

```bash
# One-time: download cloudflared (Linux x86_64; adjust if your node is different)
cd ~/llm_training
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
```

**2. Start Qwen and the tunnel (one command)**

In the same interactive session you can use the helper script (it starts Qwen, then cloudflared):

```bash
cd ~/llm_training
chmod +x run_qwen_with_public_url.sh
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com   # required so Render can call Qwen
./run_qwen_with_public_url.sh
```

The script downloads `cloudflared` if needed, starts Qwen, then prints a **https://….trycloudflare.com** URL. Copy that URL.

Or do it manually:

```bash
cd ~/llm_training
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
python qwen_serve.py --port 8001 &
sleep 30
./cloudflared tunnel --url http://localhost:8001
```

Cloudflared will print a line like: `Your quick Tunnel has been created! Visit https://xxxx-xx-xx-xx.trycloudflare.com`  
Copy that **https** URL.

**3. Configure Render**

- In **Render Dashboard** → your **SpeechGradebook** service → **Environment**:
  - Set **`QWEN_API_URL`** = the URL from step 2 (e.g. `https://xxxx.trycloudflare.com`).
- Save. Render will redeploy so the app serves this URL to the browser.

**4. Allow CORS from your Render app**

The Qwen server must allow requests from your Render origin. When you start `qwen_serve.py` on ISAAC, set the environment variable **before** starting Python (in the same shell where you run `python qwen_serve.py`):

```bash
export ALLOWED_ORIGINS=https://speechgradebook.onrender.com
python qwen_serve.py --port 8001
```

If you use both a staging and production URL, use a comma-separated list, e.g.:  
`ALLOWED_ORIGINS=https://speechgradebook.onrender.com,https://staging.onrender.com`

**5. When you start a new Qwen job**

Each time you start a new interactive job (or a new batch job), you’ll get a **new** trycloudflare.com URL. Update **`QWEN_API_URL`** in Render to that new URL so all users keep using the correct Qwen endpoint.

---

### Option 2: Stable public URL (Cloudflare Named Tunnel or VPS)

If you need a **fixed** URL so you don’t have to update Render every time:

- **Cloudflare Named Tunnel:** See **`llm_training/QWEN_NAMED_TUNNEL.md`** for step-by-step: add your domain to Cloudflare, create a tunnel, add a public hostname (e.g. `qwen.yourdomain.com` → `localhost:8001`), copy credentials and config to ISAAC, then on the compute node run Qwen and `cloudflared tunnel --config ... run <tunnel-name>`. Set **`QWEN_API_URL`** on Render to that URL once.
- **VPS + reverse SSH:** From the ISAAC node where Qwen runs, open a reverse tunnel to a small VPS you control:  
  `ssh -f -N -R 8001:localhost:8001 user@your-vps`. On the VPS, run nginx or Caddy to proxy port 8001 to HTTPS (e.g. `https://qwen.yourdomain.com`). Set **`QWEN_API_URL`** on Render to that URL and **`ALLOWED_ORIGINS`** on Qwen to your Render origin.

In all cases, set **`ALLOWED_ORIGINS`** on the Qwen side to your Render app origin(s) so the browser can call Qwen.

---

### Checklist for “Qwen on ISAAC for all users on Render”

| Step | Where | Action |
|------|--------|--------|
| 1 | ISAAC | One-time setup: copy `llm_training`, conda env, install deps (see above). |
| 2 | ISAAC | Start Qwen (interactive or batch); optionally install and run **cloudflared** to get a public URL. |
| 3 | ISAAC | When starting Qwen, set **`ALLOWED_ORIGINS`** to your Render app URL (e.g. `https://speechgradebook.onrender.com`). |
| 4 | Render | Set **`QWEN_API_URL`** to the public URL of Qwen (trycloudflare.com URL or your stable URL). |
| 5 | Render | Redeploy / save env so the app picks up the new **`QWEN_API_URL`**. |

Then everyone using SpeechGradebook on Render can use the Text + Video Model (Qwen) without any local tunnel.
