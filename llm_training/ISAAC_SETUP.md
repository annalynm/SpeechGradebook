# Running Training on ISAAC (or Locally)

Training runs **on ISAAC by default**. Use `--local` to run on your machine instead.

---

## Complete these steps in order

### Step 1: Make the scripts executable (on your computer, once)

Open Terminal (or Command Prompt / PowerShell). Go to the `llm_training` folder and run:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training"
chmod +x run_training.sh
chmod +x scripts/run_on_isaac.sh
```

(If your repo is elsewhere, use that path instead.)

Your config (`run_config.env`) is already set with your NetID and account.

---

### Step 2: One-time setup on ISAAC

You only do this once per ISAAC account.

**2a. Copy the `llm_training` folder to ISAAC** (from your computer)

Open Terminal. Go to your SpeechGradebook folder and copy the whole `llm_training` directory to ISAAC:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
scp -r llm_training amcclu12@login.isaac.utk.edu:~/
```

(Use VPN if UT requires it for off-campus access.)

**2b. Log in to ISAAC**

```bash
ssh amcclu12@login.isaac.utk.edu
cd ~/llm_training
```

**2c. Load Anaconda and create the Python environment**

Run these one at a time:

```bash
module load anaconda3
conda create -n speechgradebook python=3.10 -y
conda activate speechgradebook
pip install -r requirements-train.txt
```

If `module load anaconda3` fails, try `module avail` and use the anaconda module name OIT lists. If there is no anaconda module, ask OIT how to get Python 3.10 and pip on ISAAC.

**2d. Set your Hugging Face token**

You need a Hugging Face account and a token so ISAAC can download the Mistral model.

1. In a browser, go to https://huggingface.co/settings/tokens  
2. Sign in (or create an account).  
3. Click **Create new token**, name it (e.g. `isaac`), leave permissions as **Read**, and create it.  
4. Copy the token (it starts with `hf_...`).

On ISAAC, create a small file that will hold the token (do not share this file):

```bash
echo 'HF_TOKEN=paste_your_token_here' > ~/llm_training/.env_isaac
nano ~/llm_training/.env_isaac
```

Replace `paste_your_token_here` with your real token (e.g. `HF_TOKEN=hf_xxxxxxxxxxxx`). Save and exit (in nano: Ctrl+O, Enter, then Ctrl+X).

**2e. Check for Node.js** (needed to convert `exported.json` to JSONL on ISAAC)

```bash
module avail node
```

If you see a `node` or `nodejs` module, note its name (e.g. `nodejs`). You’ll load it in the job or in your shell when you run the convert step. If there is no Node module, see the “No Node on ISAAC” note at the end of this section.

**2f. Log out of ISAAC**

```bash
exit
```

**If Node.js is not available on ISAAC:** You can run the convert step on your own computer and only use ISAAC for training. On your computer (in `llm_training`), run:  
`node export_to_jsonl.js exported.json --split 0.9`  
Then in `run_training.sh` we’d need to transfer `train.jsonl` and `validation.jsonl` instead of `exported.json`, and skip the convert step on ISAAC. The current script assumes Node is on ISAAC; if you hit “node: command not found” when the job runs, say so and we can adjust the steps.

---

### Step 3: Export data from SpeechGradebook (each time you want to train)

1. Open SpeechGradebook in your browser and log in as a **Super Admin**.  
2. Go to **Platform Analytics** → **LLM Export** tab.  
3. Click **Export new training data**.  
4. Save the file as **`exported.json`** inside your **`llm_training`** folder (e.g. `SpeechGradebook/llm_training/exported.json`).

---

### Step 4: Run training on ISAAC (from your computer)

Open Terminal. Go to `llm_training` and run:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training"
./run_training.sh
```

This will:

- Copy the `llm_training` project and `exported.json` to ISAAC.  
- SSH to ISAAC and run the convert step (exported.json → train.jsonl + validation.jsonl).  
- Submit a SLURM job to train the model on a GPU.

You should see a message like “Job submitted on ISAAC” and instructions for checking the job.

**To run training on your own machine instead of ISAAC:**

```bash
./run_training.sh --local
```

---

### Step 5: Check job status on ISAAC (optional)

From your computer:

```bash
ssh amcclu12@login.isaac.utk.edu 'squeue -u $USER'
```

You’ll see your job (e.g. `speechgradebook-lora`) and its state (PENDING, RUNNING, etc.). When it no longer appears, it has finished (or failed).

To watch the log while it runs:

```bash
ssh amcclu12@login.isaac.utk.edu 'cd ~/llm_training && tail -f logs/train_*.out'
```

(Ctrl+C to stop tail.)

---

### Step 6: When the job has finished — get the model back

After the SLURM job completes, copy the trained model to your computer. From your computer (not on ISAAC), in a new terminal:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training"
scp -r amcclu12@login.isaac.utk.edu:~/llm_training/mistral7b-speech-lora ./
```

You’ll then have a `mistral7b-speech-lora` folder locally. Use it with `serve_model.py` and point SpeechGradebook at that server (see README or IMPLEMENTATION_GUIDE for serving).

---

## Reference: What you need to do (one-time)

### 1. Create your config from the example

*(You already have `run_config.env` filled in with amcclu12 and ACF-UTK0011.)*

If you ever need to recreate it:

From the `llm_training` directory:

```bash
cp run_config.env.example run_config.env
```

Edit `run_config.env` and set:

| Variable | What to put |
|----------|-------------|
| **ISAAC_USER** | Your UT NetID (e.g. `jsmith2`). **Required for ISAAC.** |
| **ISAAC_ACCOUNT** | Your SLURM account/project name on ISAAC. Get this from OIT or your allocation email. If you don't have one, leave as `YOUR_ACCOUNT` and remove the `#SBATCH --account=...` line from `train_speechgradebook.slurm` if the job fails. |
| **ISAAC_PARTITION** | GPU partition name. Default is `campus-gpu` for ISAAC-NG; other options include `long-gpu` (6 days), `ai-tenn` (H100s). |
| **ISAAC_HOST** | Leave as `login.isaac.utk.edu` unless OIT gives you a different login host. |

You can leave **ISAAC_REMOTE_DIR**, **ISAAC_TIME**, and **ISAAC_GPU_COUNT** as-is unless you want a different directory or longer/shorter jobs.

### 2. (ISAAC only) Set up your environment on the cluster

Once, on ISAAC (after SSH in):

1. **Create a conda env and install dependencies:**
   ```bash
   module load anaconda3
   conda create -n speechgradebook python=3.10 -y
   conda activate speechgradebook
   cd ~/llm_training
   pip install -r requirements-train.txt
   ```

2. **Set your Hugging Face token** (required to download Mistral):
   - Option A: In your `~/.bashrc` on ISAAC add:  
     `export HF_TOKEN=your_token_here`  
     (Get a token at https://huggingface.co/settings/tokens)
   - Option B: In `llm_training` on ISAAC create a file `.env_isaac` with one line:  
     `HF_TOKEN=your_token_here`  
     (Do not commit this file; it is gitignored.)

3. **Install Node.js** on ISAAC if needed for `export_to_jsonl.js` (or run the convert step locally and transfer only `train.jsonl` / `validation.jsonl`). Check with `module avail node` or OIT "Available Software."

### 3. (Optional) Make the runner executable

```bash
chmod +x run_training.sh
chmod +x scripts/run_on_isaac.sh
```

---

## How to run

1. **Export data from the app**  
   SpeechGradebook → Platform Analytics → LLM Export → "Export new training data". Save as `exported.json` in the `llm_training` folder (or note the path).

2. **Run training (default: on ISAAC)**  
   From `llm_training`:
   ```bash
   ./run_training.sh
   ```
   Or with a specific export file:
   ```bash
   ./run_training.sh "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training/exported.json"
   ```
   This transfers the project and `exported.json` to ISAAC, converts to JSONL, and submits the SLURM job. Check status on ISAAC with:
   ```bash
   ssh amcclu12@login.isaac.utk.edu 'squeue -u $USER'
   ```

3. **Run training locally instead**  
   ```bash
   ./run_training.sh --local
   ```
   Or set `RUN_BACKEND=local` in `run_config.env` to make local the default.

4. **After the job finishes on ISAAC**  
   Copy the trained model back to your machine:
   ```bash
   scp -r amcclu12@login.isaac.utk.edu:~/llm_training/mistral7b-speech-lora ./
   ```
   Then run `serve_model.py` locally or on your server and point SpeechGradebook at it.

---

## Automation (no terminal every time)

### Weekly scheduled training

1. Add Supabase credentials to `run_config.env` (for server-side export):
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```
   Get the service role key from Supabase Dashboard → Settings → API (use only on a secure machine).

2. Run the weekly script via cron (e.g. every Sunday at 2am):
   ```bash
   crontab -e
   ```
   Add:
   ```
   0 2 * * 0 "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training/weekly_export_and_train.sh"
   ```
   The script exports new consented evaluations (only those not yet exported) and runs training on ISAAC (or locally if `RUN_BACKEND=local`). Your machine must be on and have network/SSH access at that time.

### Export and submit from the dashboard (when you click)

1. On your machine, start the webhook server (in a terminal, leave it running):
   ```bash
   cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training"
   node receive_export_server.js
   ```
   It listens on `http://localhost:3131/export` by default.

2. In SpeechGradebook: Platform Analytics → LLM Export. Set **Webhook URL** to `http://localhost:3131/export` (or `http://YOUR_IP:3131/export` if the app runs on another device). Click **Export and submit to ISAAC**. The app sends the export JSON to the server; the server saves it and runs `run_training.sh` (transfer + ISAAC job). No manual download or terminal needed.

---

## Troubleshooting

- **"ISAAC_USER not set"** — You didn’t create `run_config.env` or didn’t set `ISAAC_USER` (your NetID).
- **Job won’t submit / "Invalid account"** — Set `ISAAC_ACCOUNT` in `run_config.env` to your SLURM account, or edit `train_speechgradebook.slurm` and remove the `#SBATCH --account=...` line if your cluster doesn’t require it.
- **"HF_TOKEN" / model download fails on ISAAC** — Set `HF_TOKEN` in `~/.bashrc` or in `llm_training/.env_isaac` on ISAAC (see step 2 above).
- **"node: command not found" on ISAAC** — Load a Node module (`module load nodejs` or similar) or run the convert step locally and transfer only `train.jsonl` and `validation.jsonl`.
