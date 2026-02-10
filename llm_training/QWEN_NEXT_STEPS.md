# Qwen: Simple Next Steps (Evaluate + Train)

Short path to **use Qwen to evaluate speeches** and **train your own Qwen video model**.

---

## Part 1: Use Qwen to evaluate speeches

Qwen (SpeechGradebook Text + Video Model) evaluates **video + transcript** together (body movement, eye contact, delivery, content).

### 1. Install and run the Qwen service

macOS (and many Linux setups) use an **externally-managed** Python, so install into a **virtual environment** instead of system-wide.

**One-time setup (create venv and install deps):**

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/llm_training"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-qwen.txt
```

If you see **SSL certificate errors** when running `pip install`, fix certificates (e.g. open Keychain Access and ensure your root certs are trusted, or run the Install Certificates command from your Python installer), then run the `pip install` again.

**Every time you want to run Qwen:**

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/llm_training"
source venv/bin/activate
python qwen_serve.py --port 8001
```

Or use the helper script (activates venv and starts the server):

```bash
"/Users/annamcclure/SpeechGradebook Repo/llm_training/run_qwen_local.sh"
```

First run downloads the model (~16GB). Use a machine with **~16GB GPU VRAM** (or expect slower CPU inference).

### 2. Point the app at Qwen

- **Local:** In the repo root, create or edit `.env` and add:
  ```bash
  QWEN_API_URL=http://localhost:8001
  ```
- **Or (Super Admin):** In the app go to **Settings → General** (API Keys) and set **SpeechGradebook Text + Video Model (Qwen) Service URL** to `http://localhost:8001`.

### 3. Run an evaluation

1. **Evaluate Speech** → choose Course & Student → upload a **video** → pick a rubric.
2. For **Evaluation provider** choose **SpeechGradebook Text + Video Model (Qwen)**.
3. Click **Evaluate**, then correct scores if needed and **Save** (Add to gradebook).

Saving with video stores the file in Supabase (bucket `evaluation-media`) so you can use it later for training.

---

## Part 2: Train your own Qwen model

Training teaches Qwen your rubrics and scoring style using **videos + corrected scores**.

### 1. Collect training data (in the app)

- Run **30–100+** evaluations with **video** using Qwen (or Gemini), correct scores, and **Save**.
- Ensure students have granted **data-use consent** (for LLM training) where required.
- Videos must be saved with evaluations (Supabase bucket **`evaluation-media`**).

### 2. Export training data for Qwen

- As **Super Admin**, open **Dashboard → Evaluations** (or the **LLM Export** tab if visible).
- Use **Export new training data** or the **Train SpeechGradebook Text + Video Model (Qwen) on ISAAC** flow.
- That produces **`train_qwen.jsonl`** (one line per evaluation: video URL/path, rubric, scores). If your app uses an API, it may call `/api/llm-export-qwen` to generate this file.

Alternatively, from the app’s **LLM Training Data Export** card, download the export and then build `train_qwen.jsonl` manually (see `DUAL_MODEL_TRAINING.md` for the exact JSONL format: `video_path`, `rubric`, `scores` per line).

### 3. Validate the manifest (optional)

From `llm_training/`:

```bash
python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora --validate_only
```

Fixes any paths/format issues before training.

### 4. Train on a GPU (ISAAC or local)

- **On ISAAC (recommended):**  
  - Copy `llm_training/` and `train_qwen.jsonl` to ISAAC.  
  - Configure `run_config.env` (see `run_config.env.example`) with `ISAAC_USER`, `ISAAC_HOST`, `ISAAC_REMOTE_DIR`, and optionally partition/account.  
  - From your laptop:
    ```bash
    cd llm_training
    ./run_qwen_training.sh
    ```
  - Or on ISAAC, use the Qwen SLURM script:
    ```bash
    sbatch train_qwen_speechgradebook.slurm
    ```
  - Requires **train_qwen.jsonl** in `llm_training/` and `train_qwen_vl.py` (and a full training loop in that script if not yet implemented).

- **Local (single GPU, ≥24GB VRAM):**  
  ```bash
  cd llm_training
  python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora --num_epochs 2
  ```
  (Exact args depend on `train_qwen_vl.py`; see `python train_qwen_vl.py --help`.)

### 5. Serve the trained model

After training you get an adapter (e.g. `./qwen2.5vl-speech-lora`). To serve it:

- Use **`qwen_serve.py`** with a `--model_path` or adapter path if your codebase supports it, **or**
- Keep using the **base Qwen service** (`python qwen_serve.py --port 8001`) for evaluation and reserve the trained adapter for a future “custom Qwen” endpoint.

(Check `qwen_serve.py` and `START_QWEN_FOR_RENDER.md` for production/deployment.)

---

## Quick reference

| Goal | Action |
|------|--------|
| **Evaluate with Qwen** | Run `python qwen_serve.py --port 8001`, set `QWEN_API_URL` or Super Admin Qwen URL, then in the app choose **SpeechGradebook Text + Video Model (Qwen)** and evaluate with video. |
| **Get training data** | Save 30–100+ video evaluations (correct scores); use Super Admin **Export / Train Qwen on ISAAC** (or equivalent) to get `train_qwen.jsonl`. |
| **Train Qwen** | Put `train_qwen.jsonl` in `llm_training/`, then run `./run_qwen_training.sh` (ISAAC) or `python train_qwen_vl.py ...` (local GPU). |
| **More detail** | `QWEN_SETUP.md` (service), `ISAAC_QWEN_SETUP.md` (ISAAC), `DUAL_MODEL_TRAINING.md` (data format + two-tier setup). |
