# Steps to Complete Initial Training of the SpeechGradebook LLM

This document is the single checklist for going from **no trained model** to **a working fine-tuned model** in the app. It covers both getting training data (Phase A) and running the training pipeline (Phase B).

**Where more detail lives:**
- **Phase A (get data):** [FASTER_PATH_TO_TRAINABLE_MODEL.md](FASTER_PATH_TO_TRAINABLE_MODEL.md) — step-by-step for API evaluation, correcting, and saving.
- **Phase B (technical steps):** [STEPS_TO_REAL_EVALUATIONS.md](STEPS_TO_REAL_EVALUATIONS.md) — exact commands, paths, and options.
- **Alternative flow:** [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) — environment setup, sample data, and serving.

---

## Overview

| Phase | Goal | Outcome |
|-------|------|--------|
| **A** | Get 30–100+ evaluations (transcript + rubric + corrected scores, and optionally video_notes) | Data in Supabase ready for export |
| **B** | Export → convert to JSONL → train LoRA → serve | SpeechGradebook Text Model (Mistral) loaded; app uses it for evaluations |

---

## Step 1: Get training data (Phase A)

You need evaluations in Supabase that have **transcript** and **evaluation_data.sections** (and optionally **evaluation_data.video_notes** for video-aware training).

### Option A — Use the app with an API (recommended)

1. **Get a Gemini API key** (for video) or OpenAI/Claude key. Add it in **Settings** in the app.
2. **Run 30–100+ evaluations:** Choose **Evaluation provider** (e.g. Gemini), upload video/audio, select rubric, click Evaluate.
3. **Correct** any wrong scores or feedback in the app (Edit → change points/feedback → Reason for change → Save).
4. **Save** each evaluation (Save evaluation / Add to gradebook). Each save stores transcript, sections, and (for Gemini) video_notes in Supabase.

**Detailed Phase A instructions:** See [FASTER_PATH_TO_TRAINABLE_MODEL.md — Phase A: Working evaluations](FASTER_PATH_TO_TRAINABLE_MODEL.md#phase-a-working-evaluations-fast).

### Option B — You already have evaluations in Supabase

If you already have evaluations with `transcript` and `evaluation_data.sections`, skip to Step 2.

### Option C — Test the pipeline with sample data (no real data)

Use the included sample so you can run the rest of the steps and confirm the pipeline works:

- File: `llm_training/sample_exported.json`
- Use it in place of `exported.json` in Step 2 (and skip the export in Step 2; the “export” is already done).

---

## Step 2: Export from Supabase to JSON

From your project root or `SpeechGradebook/llm_training/`:

```bash
cd "SpeechGradebook/llm_training"
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
node export_from_supabase.js
```

- Writes **exported.json** in `llm_training/`.
- Optional: `node export_from_supabase.js --consent` to restrict to consented students only (for first batch you can omit `--consent`).
- Optional: `node export_from_supabase.js --output "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training/exported.json"`

**If you used Option C (sample data):** Skip this step and use `sample_exported.json` as your export in Step 3.

---

## Step 3: Convert export to JSONL (training format)

```bash
cd SpeechGradebook/llm_training
node export_to_jsonl.js exported.json > train.jsonl
```

- If using sample: `node export_to_jsonl.js sample_exported.json > train.jsonl`
- Optional train/validation split: `node export_to_jsonl.js exported.json --split 0.9` (creates `train.jsonl` and `validation.jsonl`).

Check: `head -1 train.jsonl | python3 -m json.tool` should show one object with a `messages` array.

---

## Step 4: Set up Python environment for training

Use the same venv the app uses (e.g. `SpeechGradebook/venv`) or one in `llm_training/`:

```bash
cd SpeechGradebook
source venv/bin/activate
pip install -r llm_training/requirements-train.txt
export HF_TOKEN=your_huggingface_token
```

- **HF_TOKEN** is required to download the base model (Mistral 7B). Get it from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
- Accept the Mistral model terms on the [model page](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2) if prompted.

---

## Step 5: Train the LoRA adapter

From `SpeechGradebook/` with venv activated and `HF_TOKEN` set:

```bash
cd SpeechGradebook
source venv/bin/activate
export HF_TOKEN=your_token_here

python llm_training/train_lora.py \
  --train_file llm_training/train.jsonl \
  --output_dir llm_training/mistral7b-speech-lora \
  --num_epochs 3
```

- If you created a validation split: add `--validation_file llm_training/validation.jsonl`.
- **Limited VRAM (~10GB):** add `--load_in_8bit`.
- **OOM errors:** try `--per_device_train_batch_size 1` and/or `--load_in_8bit`.

Training writes the adapter to **llm_training/mistral7b-speech-lora**. This can take from minutes to hours depending on data size and hardware.

---

## Step 6: (Optional) Evaluate the adapter on holdout data

If you have `validation.jsonl`:

```bash
cd SpeechGradebook
source venv/bin/activate
python llm_training/eval_model.py \
  --model_path llm_training/mistral7b-speech-lora \
  --validation_file llm_training/validation.jsonl \
  --num_samples 5
```

Use this to sanity-check predictions before serving.

---

## Step 7: (Optional) Install Whisper for file upload in the app

The app can send **audio/video files** to the server; the server needs Whisper to transcribe them:

```bash
cd SpeechGradebook
source venv/bin/activate
pip install openai-whisper
```

Without Whisper, `/evaluate_with_file` returns 501 and the app will show that file upload is not supported (transcript-only `/evaluate` still works if you send transcript from elsewhere).

---

## Step 8: Restart the server so it loads the adapter

The app (e.g. `run_local.sh`) loads the model on startup only if the adapter path exists. After training, the adapter is at **llm_training/mistral7b-speech-lora**, which is the default.

1. **Stop** any running server (e.g. Ctrl+C on `./run_local.sh`).
2. **Start again** from the repo root:

   ```bash
   ./run_local.sh
   ```

   Or: `bash "/Users/annamcclure/SpeechGradebook Repo/run_local.sh"`

On startup you should see “Model loaded.” in the terminal.

**If you need 8-bit to save memory:**  
`LOAD_IN_8BIT=1 uvicorn app:app --host 0.0.0.0 --port 8000` (from `SpeechGradebook/` with venv activated).

---

## Step 9: Run a real evaluation in the app

1. Open **http://localhost:8000** (or your app URL).
2. Log in and go to the evaluation flow (upload file or use transcript, select rubric).
3. Set **Evaluation provider** to **SpeechGradebook Text Model (Mistral)** and ensure the evaluation server URL is **http://localhost:8000/api** (or your server URL).
4. Run the evaluation. The app calls the server; the server transcribes (if Whisper is installed) and runs the fine-tuned model, then returns sections; the app displays scores and feedback.

**Quick check:** `curl http://localhost:8000/api/health` should return `{"status":"ok","model_loaded":true}`.

---

## Summary checklist

| Step | Action |
|------|--------|
| 1 | Get 30–100+ evaluations: use Gemini (or API) in the app, correct, save **or** use existing Supabase data **or** use `sample_exported.json` to test. |
| 2 | Export: `node export_from_supabase.js` → **exported.json** (skip if using sample). |
| 3 | Convert: `node export_to_jsonl.js exported.json > train.jsonl` (optional: `--split 0.9`). |
| 4 | Environment: venv, `pip install -r llm_training/requirements-train.txt`, set `HF_TOKEN`. |
| 5 | Train: `python llm_training/train_lora.py --train_file llm_training/train.jsonl --output_dir llm_training/mistral7b-speech-lora --num_epochs 3`. |
| 6 | (Optional) Run `eval_model.py` on validation.jsonl. |
| 7 | (Optional) `pip install openai-whisper` for file upload. |
| 8 | Restart server (`./run_local.sh`) so it loads the adapter. |
| 9 | In the app, run an evaluation with **SpeechGradebook Text Model (Mistral)**. |

Once these are done, you have completed **initial training** and the app is using your fine-tuned model for evaluations.

---

## Where to find more detail

| Topic | Document |
|-------|----------|
| Phase A: API evaluation, correcting, saving, video_notes | [FASTER_PATH_TO_TRAINABLE_MODEL.md](FASTER_PATH_TO_TRAINABLE_MODEL.md) |
| Phase B: Exact commands, paths, OOM/8-bit, Whisper | [STEPS_TO_REAL_EVALUATIONS.md](STEPS_TO_REAL_EVALUATIONS.md) |
| Environment, sample data, serving, transcript-only | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) |
| Export script usage, consent, automation | [FASTER_PATH_TO_TRAINABLE_MODEL.md — Automating export](FASTER_PATH_TO_TRAINABLE_MODEL.md#automating-export-and-optionally-the-full-retrain) |
| Video content evaluation (Gemini + trained model) | [FASTER_PATH_TO_TRAINABLE_MODEL.md — Video content evaluation](FASTER_PATH_TO_TRAINABLE_MODEL.md#video-content-evaluation-body-movement-eye-contact-slides-etc) |
