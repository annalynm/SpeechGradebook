# Evaluations vs Training: Using ISAAC Only Where It Helps

Your setup currently ties **running evaluations** (Mistral/Qwen inference) to being connected to ISAAC, which has been unreliable. Training (batch jobs on ISAAC) can work **without** you being connected if the app server (Render) can reach ISAAC. This doc separates the two and gives concrete recommendations.

---

## Two different things

| What | Where it runs | Who needs to connect |
|------|----------------|----------------------|
| **Evaluations** (score a speech with Qwen or Mistral) | Qwen today: ISAAC (you start tunnel from your laptop). Mistral: can be Render or ISAAC. | You must start Qwen on ISAAC and keep the tunnel up, so you’re tied to ISAAC connectivity. |
| **Training** (run `train_lora.py` or Qwen training) | ISAAC (SLURM batch job). | **Render** (or the machine that runs “Submit to ISAAC”) must reach ISAAC. You do **not** need to be on ISAAC or connected from your laptop. |

So: **evaluations** are what require you to be “connected to ISAAC” (for Qwen). **Training** can be triggered from the SpeechGradebook app on Render and run entirely on ISAAC as long as Render can SSH there.

---

## Recommendation 1: Don’t depend on ISAAC for day‑to‑day evaluations

**Problem:** If Qwen (and optionally Mistral) run only on ISAAC and you start them from your laptop (e.g. `connect_isaac_qwen.sh`), then whenever you’re not connected or ISAAC is flaky, you can’t run evaluations or collect new data (including behavior examples).

**Recommendation:** Run **evaluations** on a service that doesn’t require your laptop or ISAAC:

- **Qwen:** Deploy the Qwen (video) service somewhere always-on:
  - **Second Render web service** (Docker, with GPU if Render offers it, or CPU and accept slower runs), and set **QWEN_API_URL** on the main app to that service’s URL; or
  - **Another cloud** (e.g. Modal, RunPod, or a small VM) with a stable URL, and point **QWEN_API_URL** there.
- **Mistral:** If you use the SpeechGradebook Text Model (Mistral), run it on Render (same app or a separate service) or on the same always-on host as Qwen, not on ISAAC.

Use **ISAAC only for training** (batch jobs): submit when you have enough data; the job runs on the cluster without you staying connected.

**Result:** You can run evaluations and build exports (including behavior examples) anytime. When you’re ready to train, you trigger training from the app (or manually) and ISAAC runs the job in the background.

---

## Recommendation 2: Make “Submit to ISAAC” work from the app (no need for you to be on ISAAC)

**How it works today:** When you click **Export and submit to ISAAC** (or **Submit Qwen training to ISAAC**) in Platform Analytics → LLM Export, the **Render** server runs `run_training.sh` (or `run_qwen_training.sh`). That script **from Render** rsyncs the export to ISAAC and runs `sbatch` there. So **Render** must be able to SSH to ISAAC; **you** do not need to be connected to ISAAC.

**What to configure on Render:**

In Render Dashboard → your SpeechGradebook service → **Environment**, set:

| Key | Value | Notes |
|-----|--------|--------|
| `ISAAC_USER` | Your UT NetID | e.g. `amcclu12` |
| `ISAAC_HOST` | `login.isaac.utk.edu` | Use this hostname (see [OIT ISAAC-NG](https://oit.utk.edu/hpsc/isaac-open-enclave-new-kpb/running-jobs-new-cluster-kpb/)) |
| `ISAAC_REMOTE_DIR` | `~/llm_training` | Path on ISAAC where the repo and export go |
| `ISAAC_SSH_PRIVATE_KEY` | Full contents of your SSH **private** key | The matching **public** key must be in `~/.ssh/authorized_keys` on ISAAC for `ISAAC_USER` |
| `RENDER_LLM_EXPORT_SECRET` | A secret string | Same value as in the app’s “API secret” field when submitting |

Optional but recommended for SLURM (matches [ISAAC-NG partitions and QOS](https://oit.utk.edu/hpsc/isaac-open-enclave-new-kpb/running-jobs-new-cluster-kpb/)):

| Key | Example | Notes |
|-----|---------|--------|
| `ISAAC_ACCOUNT` | `ACF-UTK0011` | UTK institutional account for campus partitions |
| `ISAAC_PARTITION` | `campus-gpu` | For GPU training jobs |
| `ISAAC_QOS` | `campus-gpu` | QOS for campus-gpu partition |
| `ISAAC_TIME` | `04:00:00` | Wall time (campus-gpu limit 24h) |
| `ISAAC_GPU_COUNT` | `1` | GPUs per job |

**Check:** After saving env and redeploying, use **Export and submit to ISAAC** from the app. If it succeeds, the job is submitted on ISAAC and you can monitor it with `squeue -u $USER` when you next log in. You do **not** need to be connected to ISAAC at the moment you click Submit.

If Render **cannot** reach ISAAC (e.g. firewall or SSH not allowed from Render’s IP), see “Manual training workflow” below.

---

## Recommendation 3: One-time setup on ISAAC (so training jobs run)

Training runs **on** ISAAC; the code and data must be there. Do this once per account:

1. **Copy `llm_training` to ISAAC** (from a machine that can SSH to ISAAC, e.g. when you have VPN or campus access):
   ```bash
   scp -r llm_training $ISAAC_USER@login.isaac.utk.edu:~/
   ```
2. **On ISAAC:** Create conda env, install deps, set `HF_TOKEN` (see `llm_training/ISAAC_SETUP.md`).
3. **Node.js on ISAAC:** The script converts `exported.json` → `train.jsonl` on ISAAC. If `node` isn’t available, run the convert step locally and transfer `train.jsonl` + `validation.jsonl` instead (see “No Node on ISAAC” in ISAAC_SETUP.md).

After that, “Submit to ISAAC” from Render will rsync the **current** export and scripts and submit the job; you only need to re-copy the repo if you change training scripts or add new dependencies.

---

## Manual training workflow (when Render can’t reach ISAAC)

If Render cannot SSH to ISAAC (e.g. network policy), you can still train on ISAAC without being “connected” for the whole job:

1. **Export from the app** (anywhere): Platform Analytics → LLM Export → export the data (and, if you use it, add behavior examples to the export or merge them into the JSON). Download the exported file (e.g. `exported.json` or the Qwen manifest).
2. **When you have ISAAC access** (or use a machine that can reach ISAAC): Upload the export to ISAAC, e.g.:
   - **Open OnDemand** (login.isaac.utk.edu): Files → upload to `~/llm_training/exported.json` (or the path your script expects).
   - **scp** from a machine with ISAAC access:  
     `scp exported.json $ISAAC_USER@login.isaac.utk.edu:~/llm_training/`
3. **On ISAAC** (SSH or OnDemand shell): Run convert and submit:
   ```bash
   cd ~/llm_training
   node export_to_jsonl.js exported.json --split 0.9   # if you have Node
   # If no Node: run the convert step on your laptop and upload train.jsonl + validation.jsonl instead, then:
   sbatch train_speechgradebook.slurm   # or use the script that substitutes partition/account
   ```
   For **Qwen** training, upload the Qwen manifest as expected by `run_qwen_training.sh` and run that script (or the equivalent sbatch) on ISAAC.

You don’t need to stay connected; the SLURM job runs on the cluster. Check status later with `squeue` and logs in `~/llm_training/logs/`.

---

## Training with behavior examples

- **Mistral:** Add behavior-example records (transcript, video_notes, rubric, scores) to your export JSON, then export and submit as usual (from Render or manually). See `llm_training/BEHAVIOR_EXAMPLES_NEXT_STEPS.md` and `EXAMPLE_VIDEOS_TRAINING.md`.
- **Qwen:** Add one manifest line per behavior-example video (video_path = Supabase URL, rubric, scores). Merge with your main Qwen export if you have one, then submit to ISAAC (from Render or manually). Same doc references.

No need to run evaluations on ISAAC for this; you only need the export (and optional merge) and then run the training job on ISAAC.

---

## ISAAC references (partitions and QOS)

For partition, account, and QOS details (e.g. `campus-gpu`, `ACF-UTK0011`, wall limits), use the official docs:

- **Running jobs on ISAAC-NG:**  
  [Running Jobs on ISAAC-NG | OIT](https://oit.utk.edu/hpsc/isaac-open-enclave-new-kpb/running-jobs-new-cluster-kpb/)

Use the same partition/account in your SLURM scripts (or in `ISAAC_PARTITION` / `ISAAC_ACCOUNT` on Render) so jobs are scheduled correctly. No need to reconfigure the repo for that unless you switch to a different partition or account.

---

## Summary

| Goal | Action |
|------|--------|
| **Run evaluations without depending on ISAAC** | Run Qwen (and Mistral) on Render or another always-on host; set QWEN_API_URL (and Mistral URL if used). Use ISAAC only for training. |
| **Submit training without being on ISAAC** | Set ISAAC_* and RENDER_LLM_EXPORT_SECRET on Render so “Export and submit to ISAAC” works. Render does rsync + sbatch; you don’t need to be connected. |
| **If Render can’t reach ISAAC** | Export from the app, download the file, upload to ISAAC when you have access, then run convert + sbatch on ISAAC. |
| **Train with behavior examples** | Add behavior-example records (Mistral) or manifest lines (Qwen) to your export, then submit to ISAAC as above. |
| **Keep SLURM valid** | Use partition/account from [ISAAC-NG Running Jobs](https://oit.utk.edu/hpsc/isaac-open-enclave-new-kpb/running-jobs-new-cluster-kpb/) (e.g. `campus-gpu`, `ACF-UTK0011`). |
