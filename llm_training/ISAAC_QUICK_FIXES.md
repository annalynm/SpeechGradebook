# ISAAC quick fixes

## 1. Fix tunnel config YAML (run on ISAAC)

The config on ISAAC must have `credentials-file:` and the path on **one line**. SSH to ISAAC, then run this whole block:

```bash
cat > ~/llm_training/.cloudflared/config.yml << 'EOF'
tunnel: bc473029-6b8b-421e-bb46-b3d77084b35c
credentials-file: /nfs/home/amcclu12/llm_training/.cloudflared/bc473029-6b8b-421e-bb46-b3d77084b35c.json

ingress:
  - hostname: qwen.speechgradebook.com
    service: http://localhost:8001
  - service: http_status:404
EOF
```

Check it: `cat ~/llm_training/.cloudflared/config.yml` — line 2 should be one long line with no line break before `.json`.

---

## 2. Copy tunnel files from laptop (no subfolder, no permission errors)

Copy the **two files** into `.cloudflared/` (not the folder). From your **laptop**:

```bash
scp ~/qwen-tunnel/config.yml ~/qwen-tunnel/bc473029-6b8b-421e-bb46-b3d77084b35c.json amcclu12@login.isaac.utk.edu:~/llm_training/.cloudflared/
```

If your laptop config is still broken (line 3 error), fix it on the laptop first with the same `cat > ~/qwen-tunnel/config.yml << 'EOF'` content (use the same YAML as above but keep `credentials-file` on one line), then scp.

---

## 3. Conda “not configured” on ISAAC

If you see `Your shell has not been properly configured to use 'conda activate'`:

**Option A (recommended once):** Run once on ISAAC, then log out and back in:

```bash
module load anaconda3
conda init bash
```

Log out of ISAAC and SSH back in; then `conda activate speechgradebook` will work.

**Option B:** Use `source` before activate in the same session:

```bash
module load anaconda3
source $(dirname $(which conda))/../etc/profile.d/conda.sh
conda activate speechgradebook
```

The updated `start_qwen_stable.sh` tries to load the module and activate for you; if your conda is in a different path, Option A or B ensures the script finds the right Python.

---

## 4. srun “Invalid qos specification”

The partition or account may be different on your cluster. On ISAAC run:

```bash
sinfo -s
```

Use a partition that has GPUs (e.g. `gpu`, `campus-gpu`, `volta`). Then try, for example:

```bash
srun --pty -p gpu --gres=gpu:1 -t 4:00:00 bash
```

If an account is required, check with:

```bash
sacctmgr show assoc format=account,partition -p | grep amcclu12
```

Use the partition and account from that output in `srun`. Your Research Computing docs will have the exact command.

---

## 5. Two tunnels with the same name

You may see two tunnels named `qwen-speechgradebook` (e.g. one from the Mac `cloudflared service install`, one from `tunnel create`). We use tunnel ID **bc473029-6b8b-421e-bb46-b3d77084b35c** (config and credential on ISAAC).

- To avoid confusion, you can **stop the Mac tunnel** so only ISAAC serves:  
  `sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist`  
  (To start again: `sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist`.)
- Or leave it; when you run `./start_qwen_stable.sh` on ISAAC with the bc47... config, that tunnel connects and your URL will use it.

---

## 6. After fixes: run on ISAAC

1. Get a GPU session (with the correct partition/account from step 4).
2. Run:

```bash
cd ~/llm_training
./start_qwen_stable.sh
```

3. Leave the terminal open. From your laptop: `curl -s https://qwen.speechgradebook.com/health` should return JSON with `"status":"ok"` or `"model_not_loaded"` once the model is loaded.
