# Step-by-Step Implementation Guide: Fine-Tuned Mistral 7B for SpeechGradebook

This guide walks you through implementing the full pipeline: exporting data → training → evaluating → serving → using in the app.

---

## Prerequisites

- **Node.js** (for `export_to_jsonl.js`) – already used if you run the app.
- **Python 3.10+** with `pip`.
- **GPU (recommended):** ~16GB VRAM for full Mistral 7B, or ~10GB with 8-bit. CPU-only training is very slow.
- **Hugging Face account** and token (for downloading `mistralai/Mistral-7B-Instruct-v0.2`).
- **SpeechGradebook** with consent and evaluations in place (for real data export).

---

## Step 1: Prepare Your Environment

### 1.1 Create a Python environment (recommended)

```bash
cd SpeechGradebook/llm_training
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements-train.txt
```

### 1.2 Set your Hugging Face token

Required for downloading the base model:

```bash
export HF_TOKEN=your_token_here
# Or: pip install huggingface_hub && huggingface-cli login
```

### 1.3 (Optional) Install Whisper for file upload in the app later

```bash
pip install openai-whisper
```

---

## Step 2: Get Training Data

You need a JSON array of evaluations: each item has `transcript`, `rubric`, `scores`, and optionally `markers`, `student_hash`, `institution_hash`.

### Option A: Export from the app (Super Admin only)

1. In SpeechGradebook, sign in as **Super Admin**.
2. Use the LLM training export (see `FERPA_IMPLEMENTATION_GUIDE.md` – `exportLLMTrainingData()`).
3. Save the response as a JSON file, e.g. `exported.json`, in `SpeechGradebook/llm_training/`.

**If this export is not yet wired in the UI:** Call the export logic from the browser console or add a “Download for training” button that runs it and downloads `exported.json`.

### Option B: Use sample data to test the pipeline

A small sample file is included:

```bash
# sample_exported.json is already in llm_training/
ls sample_exported.json
```

Use it to verify the rest of the steps; replace with real `exported.json` when ready.

---

## Step 3: Convert to Training Format (JSONL)

Convert your JSON export into one line per example in “messages” format (system / user / assistant).

```bash
cd SpeechGradebook/llm_training
node export_to_jsonl.js exported.json > train.jsonl
# Or use sample:
node export_to_jsonl.js sample_exported.json > train.jsonl
```

**Optional: create a train/validation split (e.g. 90% / 10%)**

```bash
node export_to_jsonl.js exported.json --split 0.9
# Creates train.jsonl and validation.jsonl
```

**Check the output**

```bash
head -1 train.jsonl | python3 -m json.tool
```

You should see one JSON object with a `messages` array (system, user, assistant).

---

## Step 4: Train the Model (LoRA on Mistral 7B)

### 4.1 Run training

```bash
cd SpeechGradebook/llm_training
source venv/bin/activate   # if using venv
export HF_TOKEN=your_token_here

python train_lora.py \
  --train_file train.jsonl \
  --validation_file validation.jsonl \
  --output_dir ./mistral7b-speech-lora \
  --num_epochs 3
```

**If you have limited VRAM (~10GB):**

```bash
python train_lora.py \
  --train_file train.jsonl \
  --output_dir ./mistral7b-speech-lora \
  --load_in_8bit
```

**Other useful options**

- `--max_seq_length 2048` (default) – increase if your rubric + transcript are long.
- `--per_device_train_batch_size 2` – reduce to 1 if OOM.
- `--learning_rate 2e-5` – default; try 1e-5 if loss is unstable.

Training writes checkpoints and the final adapter to `--output_dir`. Expect several minutes to hours depending on data size and GPU.

### 4.2 Confirm outputs

```bash
ls mistral7b-speech-lora
# Expect: adapter_config.json, adapter_model.safetensors, tokenizer files, etc.
```

---

## Step 5: Evaluate on Holdout Data

If you created `validation.jsonl`, run:

```bash
python eval_model.py \
  --model_path ./mistral7b-speech-lora \
  --validation_file validation.jsonl \
  --num_samples 5
```

This prints a few example predictions vs expected and, when applicable, MAE on section scores. Use it to sanity-check before serving.

---

## Step 6: Serve the Model

Start the API so the app can call your fine-tuned model.

### 6.1 Start the server

```bash
cd SpeechGradebook/llm_training
source venv/bin/activate
python serve_model.py \
  --model_path ./mistral7b-speech-lora \
  --port 8000
```

**With 8-bit to save VRAM:**

```bash
python serve_model.py --model_path ./mistral7b-speech-lora --port 8000 --load_in_8bit
```

Leave this terminal running. You should see “Model loaded. Starting server on port 8000”.

### 6.2 (Optional) Enable file upload from the app

If you want to upload audio/video from the app (not just transcript), the server must transcribe with Whisper:

```bash
pip install openai-whisper
# Restart serve_model.py
```

Then `POST /evaluate_with_file` will work; without Whisper it returns 501.

### 6.3 Quick test

```bash
curl http://localhost:8000/health
# Expect: {"status":"ok","model_loaded":true}
```

---

## Step 7: Use the Fine-Tuned Model in the App

1. Open SpeechGradebook (e.g. `index.html` or your hosted app).
2. Go to the evaluation flow (upload a file, etc.).
3. In **AI Provider**, select **“SpeechGradebook Text Model (Mistral)”**.
4. In the field below (normally “API Key”), enter your server URL, e.g. **`http://localhost:8000`** (no trailing slash).
5. Select a rubric and run the evaluation as usual.

The app will send the file (and rubric) to `POST {url}/evaluate_with_file`. If Whisper is installed on the server, you get transcription + scoring in one step. The app then displays results in the same way as for other providers.

**If the app and server are on different machines:** Use the server’s IP or hostname (e.g. `http://192.168.1.10:8000`) and ensure the server is reachable and CORS is enabled (the provided server allows all origins).

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| `FileNotFoundError: train.jsonl` | Run from `SpeechGradebook/llm_training` or pass full path: `--train_file "/Users/annamcclure/SpeechGradebook Repo/SpeechGradebook/llm_training/train.jsonl"`. |
| Out of memory (OOM) during training | Use `--load_in_8bit` or `--use_4bit`; reduce `--per_device_train_batch_size` to 1; reduce `--max_seq_length`. |
| `HF_TOKEN` / gated model | Export `HF_TOKEN` or run `huggingface-cli login` and accept the Mistral model terms on Hugging Face. |
| Server returns 501 for file upload | Install Whisper: `pip install openai-whisper`, then restart `serve_model.py`. |
| App says “SpeechGradebook Text Model (Mistral) server error” | Check server is running (`curl http://localhost:8000/health`), URL has no trailing slash, and CORS is allowed. |
| CORS errors in browser | The provided server uses `allow_origins=["*"]`. If you changed it, ensure your app’s origin is allowed. |

---

## Checklist Summary

- [ ] Python 3.10+ and venv (optional) set up in `llm_training/`
- [ ] `pip install -r requirements-train.txt` and `HF_TOKEN` set
- [ ] Training data: `exported.json` (or `sample_exported.json`) in `llm_training/`
- [ ] `node export_to_jsonl.js exported.json > train.jsonl` (and optional `--split 0.9`)
- [ ] `python train_lora.py ...` → adapter in `./mistral7b-speech-lora`
- [ ] (Optional) `python eval_model.py ...` to check holdout performance
- [ ] `python serve_model.py ...` running on port 8000
- [ ] (Optional) `pip install openai-whisper` for file upload from app
- [ ] In app: provider = SpeechGradebook Text Model (Mistral), URL = `http://localhost:8000`, run evaluation

Once these are done, you have a working path from data export → training → serving → use in the app.
