# Steps to Get to Real Evaluations

From the current state (app + server running, no trained model → 503 “Model not loaded”) to real evaluations using your fine-tuned Mistral 7B.

---

## Next step to get a functional SpeechGradebook LLM

**If you don’t have evaluations with transcripts in Supabase yet:**

1. **Get training data.** Either:
   - **Reinstate API evaluation** (Gemini/Claude/OpenAI) in the app so you can evaluate videos, correct the AI feedback, and save (transcript + sections are stored). Run 30–100+ evaluations and correct them.  
   - Or **export from Supabase** if you already have evaluations that have a `transcript` and `evaluation_data.sections` (e.g. from a previous flow).
2. Then follow “If you already have training data” below.

**If you already have evaluations with transcript + sections in Supabase (or a local `exported.json`):**

1. **Export** (if from Supabase):  
   `cd SpeechGradebook/llm_training` then  
   `SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node export_from_supabase.js`  
   (no `--consent` for first batch).
2. **Convert to JSONL:**  
   `node export_to_jsonl.js exported.json > train.jsonl`  
   (or use `sample_exported.json` to test the pipeline.)
3. **Train the adapter:**  
   From `SpeechGradebook/`, with venv activated and `HF_TOKEN` set:  
   `python llm_training/train_lora.py --train_file llm_training/train.jsonl --output_dir llm_training/mistral7b-speech-lora --num_epochs 3`
4. **Restart the server:**  
   Stop `./run_local.sh` (Ctrl+C), then run it again. The app loads the adapter from `llm_training/mistral7b-speech-lora` and evaluations will use the fine-tuned model.

**Quick test path (no real data):** Use `sample_exported.json` → `export_to_jsonl.js` → `train_lora.py` to confirm the pipeline runs; the resulting model will be weak but you’ll have a functional LLM. Replace with real exported data when ready.

---

## Where you are now

- App and API run locally via `./run_local.sh` (venv, uvicorn, frontend + `/api`).
- Evaluation server URL defaults to `http://localhost:8000/api`.
- No adapter on disk → server returns 503 “Model not loaded” on evaluate.
- No demo/mock when model is missing.

---

## Step 1: Get training data

You need a JSON export of evaluations: transcript + rubric + scores (and optionally markers, hashes).

**Option A – Export from the app (Super Admin)**

1. Sign in as **Super Admin**.
2. Use the LLM training export (see `FERPA_IMPLEMENTATION_GUIDE.md` – e.g. `exportLLMTrainingData()` or a “Download for training” flow if wired).
3. Save the response as a JSON file, e.g. `exported.json`, in `SpeechGradebook/llm_training/`.

**Option B – Test with sample data**

Use the included sample to validate the pipeline:

- File: `SpeechGradebook/llm_training/sample_exported.json`
- Use it in place of `exported.json` in the next step.

---

## Step 2: Convert to JSONL (training format)

From `SpeechGradebook/llm_training/`:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training"
node export_to_jsonl.js exported.json > train.jsonl
```

(If using sample: `node export_to_jsonl.js sample_exported.json > train.jsonl`.)

**Optional – train/validation split:**

```bash
node export_to_jsonl.js exported.json --split 0.9
# Creates train.jsonl and validation.jsonl
```

Check: `head -1 train.jsonl | python3 -m json.tool` should show one object with a `messages` array.

---

## Step 3: Set up Python environment for training

Use the same venv the app uses, or a dedicated one in `llm_training/`:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
source venv/bin/activate
# Or: cd llm_training && python3 -m venv venv && source venv/bin/activate
pip install -r llm_training/requirements-train.txt
```

Set your Hugging Face token (required to download Mistral):

```bash
export HF_TOKEN=your_token_here
# Or: huggingface-cli login
```

Accept the Mistral model terms on the Hugging Face model page if prompted.

---

## Step 4: Train the model (LoRA adapter)

From `SpeechGradebook/` (with venv activated):

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
source venv/bin/activate
export HF_TOKEN=your_token_here

python llm_training/train_lora.py \
  --train_file llm_training/train.jsonl \
  --output_dir llm_training/mistral7b-speech-lora \
  --num_epochs 3
```

If you created a validation split:

```bash
python llm_training/train_lora.py \
  --train_file llm_training/train.jsonl \
  --validation_file llm_training/validation.jsonl \
  --output_dir llm_training/mistral7b-speech-lora \
  --num_epochs 3
```

**If you have limited VRAM (~10GB):** add `--load_in_8bit`.

**If you hit OOM:** use `--per_device_train_batch_size 1` and/or `--load_in_8bit`.

Training writes the adapter to `llm_training/mistral7b-speech-lora` (adapter config, safetensors, tokenizer files). This can take from minutes to hours depending on data size and hardware.

---

## Step 5: (Optional) Check the adapter on holdout data

If you have `validation.jsonl`:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
source venv/bin/activate
python llm_training/eval_model.py \
  --model_path llm_training/mistral7b-speech-lora \
  --validation_file llm_training/validation.jsonl \
  --num_samples 5
```

Use this to sanity-check predictions before serving.

---

## Step 6: (Optional) Install Whisper for file upload

The app sends **audio/video files** to `POST /evaluate_with_file`. The server needs Whisper to transcribe them:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
source venv/bin/activate
pip install openai-whisper
```

Without Whisper, `/evaluate_with_file` returns 501 and the app shows that file upload is not supported.

---

## Step 7: Start the server with the model

`app.py` (used by `run_local.sh`) loads the model on startup **only if** the path exists. After training, the adapter is at `llm_training/mistral7b-speech-lora`, which is the default `MODEL_PATH`. So:

1. **Stop** any running `./run_local.sh` (Ctrl+C).
2. **Start again** from the repo root:

   ```bash
   bash "/Users/annamcclure/SpeechGradebook Repo/run_local.sh"
   ```

   Or from repo root: `./run_local.sh`

On startup you should see “Model loaded.” in the terminal. If you use 8-bit to save memory:

```bash
cd "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook"
source venv/bin/activate
LOAD_IN_8BIT=1 uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Step 8: Run a real evaluation in the app

1. Open **http://localhost:8000** in your browser (use the app from this URL).
2. Log in and go to the evaluation flow (upload a file, select a rubric).
3. Evaluation server URL should already be **http://localhost:8000/api** (default). Change it in Settings if needed.
4. Run the evaluation. The app will call `POST http://localhost:8000/api/evaluate_with_file`; the server will transcribe (if Whisper is installed) and run the fine-tuned model, then return sections; the app will display scores and feedback.

**Quick check:** `curl http://localhost:8000/api/health` should return `{"status":"ok","model_loaded":true}`.

---

## Summary checklist

| Step | Action |
|------|--------|
| 1 | Get `exported.json` (Super Admin export or `sample_exported.json`) in `llm_training/`. |
| 2 | Run `node export_to_jsonl.js exported.json > train.jsonl` (optional: `--split 0.9`). |
| 3 | Venv + `pip install -r llm_training/requirements-train.txt`; set `HF_TOKEN`. |
| 4 | Run `train_lora.py` → adapter in `llm_training/mistral7b-speech-lora`. |
| 5 | (Optional) Run `eval_model.py` on validation.jsonl. |
| 6 | (Optional) `pip install openai-whisper` for file upload. |
| 7 | Restart server (`./run_local.sh`) so it loads the adapter. |
| 8 | In the app at http://localhost:8000, run an evaluation. |

Once these are done, you have real evaluations from transcript + rubric (and from file if Whisper is installed).
