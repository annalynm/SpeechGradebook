# LLM Training for SpeechGradebook

This folder holds the pipeline to export consented, anonymized evaluation data and convert it to a format suitable for fine-tuning an LLM for speech evaluation.

See **../LLM_TRAINING_IMPLEMENTATION_PLAN.md** for the full plan (model choice, phases, integration).

**→ For steps to complete initial training (Phase A + Phase B in one place), see [INITIAL_TRAINING_STEPS.md](INITIAL_TRAINING_STEPS.md).**

**→ For a step-by-step walkthrough (environment, data, train, serve), see [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md).**

**→ To run training on ISAAC by default (or locally with `--local`), see [ISAAC_SETUP.md](ISAAC_SETUP.md).**

## Quick start

### 1. Export data from the app (Super Admin only)

In SpeechGradebook, use the Super Admin export that returns consented LLM training data (see `FERPA_IMPLEMENTATION_GUIDE.md` — `exportLLMTrainingData()`). Save the result as a JSON file, e.g. `exported.json`.

Expected shape per item:

- `transcript` (string, anonymized)
- `rubric` (string, rubric name)
- `scores` (object, same shape as `evaluation_data.sections`)
- `markers` (optional, timeline markers)
- `student_hash`, `institution_hash` (optional, for dedup/splits)

### 2. Convert to JSONL (training format)

```bash
node export_to_jsonl.js exported.json > train.jsonl
```

Optional: create a validation split (e.g. 10%):

```bash
node export_to_jsonl.js exported.json --split 0.9
# Writes train.jsonl and validation.jsonl
```

### 3. Train (Phase 2 – Mistral 7B + LoRA)

After installing Python deps:

```bash
pip install -r requirements-train.txt
export HF_TOKEN=your_huggingface_token   # required for mistralai/Mistral-7B-Instruct-v0.2
python train_lora.py --train_file train.jsonl [--validation_file validation.jsonl] --output_dir ./mistral7b-speech-lora
```

Uses **Mistral 7B Instruct v0.2** with LoRA (~16GB GPU; use `--load_in_8bit` for ~10GB). See `train_lora.py --help` for options.

### 4. Evaluate (holdout set)

```bash
python eval_model.py --model_path ./mistral7b-speech-lora --validation_file validation.jsonl
```

Prints sample predictions vs expected and optional MAE on section scores.

### 5. Serve and use in the app

**Start the API server** (loads adapter + base Mistral; optional Whisper for file upload):

```bash
pip install -r requirements-train.txt   # includes fastapi, uvicorn
# Optional, for file upload from app: pip install openai-whisper
python serve_model.py --model_path ./mistral7b-speech-lora [--port 8000] [--load_in_8bit]
```

**In SpeechGradebook:** Choose **SpeechGradebook Text Model (Mistral)** as AI Provider, enter the server URL (e.g. `http://localhost:8000`), then run an evaluation as usual. The app sends the file + rubric to `POST /evaluate_with_file`; the server transcribes (Whisper) and runs the fine-tuned model, then returns sections. If Whisper is not installed on the server, the app will show an error—install with `pip install openai-whisper` for file upload.

**Transcript-only (no Whisper):** You can call `POST /evaluate` with JSON `{ "transcript", "rubric_name", "rubric" }` to get `{ "sections", "overallComments" }` without uploading a file.

## Files

| File | Purpose |
|------|--------|
| `export_to_jsonl.js` | Converts app export JSON → JSONL with `messages` (system/user/assistant) for instruction tuning |
| `train_lora.py` | Mistral 7B LoRA fine-tuning (Hugging Face PEFT + trl SFTTrainer) |
| `eval_model.py` | Evaluate adapter on validation.jsonl (sample preds + MAE) |
| `serve_model.py` | FastAPI server: `/evaluate` (transcript+rubric), `/evaluate_with_file` (file+rubric, needs Whisper) |
| `example_train.jsonl` | Example lines so you can inspect the format |
| `requirements-train.txt` | Python dependencies for training and serving |
| `README.md` | This file |

## Data format (JSONL)

Each line is a single JSON object:

```json
{
  "messages": [
    { "role": "system", "content": "You are a speech evaluator. Apply the rubric and output scores and comments as JSON." },
    { "role": "user", "content": "Rubric: Informative Speech\n\nTranscript:\n[transcript text...]" },
    { "role": "assistant", "content": "{\"Content\": {\"score\": 32, \"maxScore\": 40, ...}, \"Delivery\": {...}}" }
  ]
}
```

The training script (Phase 2) will consume this format with Hugging Face `datasets` or a custom Dataset.
