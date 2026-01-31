# LLM Training Implementation Plan

**Purpose:** Train (or fine-tune) an LLM for speech evaluation using consented, anonymized data from SpeechGradebook, so the app can use a dedicated model for scoring and comments aligned to your rubrics.

**Prerequisites (already in place):**
- `llm_training_data` table (or export from `evaluations` + consent)
- Student and instructor consent workflows
- Anonymization and audit logging

---

## 1. Model and approach

### Chosen: Mistral 7B + LoRA fine-tuning

- **Base model:** **Mistral 7B Instruct** – `mistralai/Mistral-7B-Instruct-v0.2` (instruction-tuned for chat; best fit for our system/user/assistant format).
- **Why Mistral 7B:** Strong instruction following and structured output; Apache 2.0 license; well supported in Hugging Face and LoRA tutorials. Needs ~16GB GPU (or 8-bit quantized on ~10GB).
- **Method:** Fine-tune with **LoRA** (Low-Rank Adaptation) via Hugging Face PEFT + Transformers. Train only a small number of parameters (faster, cheaper, less overfitting). Typical LoRA targets for Mistral: `q_proj`, `v_proj`, `k_proj`, `o_proj`.

### Alternative A: OpenAI fine-tuning

- **Why:** Same API ecosystem you already use (GPT-4o-mini); no GPU to manage.
- **Model:** e.g. `gpt-4o-mini` fine-tuned on your export format.
- **Trade-off:** Data sent to OpenAI; ongoing API cost; less control over model.

### Alternative B: RAG (no training)

- **Why:** Use existing evaluations as a retrieval corpus; general LLM generates scores/comments conditioned on “similar” past evaluations.
- **Trade-off:** No dedicated “speech grader” model; quality depends on retrieval and prompt design.

**Default for this plan:** Proceed with **Mistral 7B + LoRA** (see `llm_training/train_lora.py`).

---

## 2. Training task and data shape

- **Input:** Anonymized transcript + rubric definition (category names, max scores, subcategories).
- **Output:** Structured scores and comments per rubric section (same shape as `evaluation_data.sections`).
- **Format:** Instruction-tuning / chat style so the model sees:
  - **System:** Rubric and instructions (e.g. “You are a speech evaluator. Score and comment per category.”).
  - **User:** Transcript (and optional timeline markers).
  - **Assistant:** JSON or plain text for sections (scores + comments).

Your existing `evaluation_data.sections` is an object like:

```json
{
  "Content": { "score": 32, "maxScore": 40, "subcategories": [{ "name": "Organization", "points": 12, "maxPoints": 15 }, ...] },
  "Delivery": { "score": 24, "maxScore": 30, "subcategories": [...] }
}
```

Training examples will map: **(transcript, rubric) → sections (+ optional comments per subcategory)**.

---

## 3. Implementation phases

### Phase 1: Export pipeline (data → training format)

- [ ] **1.1** Super-admin export of consented data  
  - From `llm_training_data` if populated, **or** from `evaluations` joined with `consent_forms` (consent_type = `llm_training`) and anonymize on export.
- [ ] **1.2** Convert each row to a single training example:
  - **System:** Rubric text (from `rubrics` or stored rubric JSON).
  - **User:** `anonymized_transcript` (and optionally `timeline_markers`).
  - **Assistant:** JSON string of `evaluation_scores` / `evaluation_data.sections` (and comments if present).
- [ ] **1.3** Write **JSONL** file: one line per example, e.g. `{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}`.
- [ ] **1.4** Optional: split into `train.jsonl` and `validation.jsonl` (e.g. 90/10 by hash of `student_hash` or `source_evaluation_id` to avoid leakage).

**Deliverable:** Script or app action that produces `train.jsonl` (and optionally `validation.jsonl`) plus a small example file for inspection.

---

### Phase 2: Training environment and LoRA fine-tuning

- [ ] **2.1** Environment: Python 3.10+, PyTorch, `transformers`, `peft`, `datasets`, `trl` (or `axolotl` if you prefer a YAML-driven setup).
- [ ] **2.2** Load base model **Mistral 7B Instruct** (`mistralai/Mistral-7B-Instruct-v0.2`); load JSONL via `datasets` or custom Dataset.
- [ ] **2.3** Tokenizer: use the model’s tokenizer; set max length to cover rubric + transcript + response (e.g. 2048–4096).
- [ ] **2.4** LoRA config: `r=8–16`, `lora_alpha=16–32`, target modules = `q_proj`, `v_proj`, `k_proj`, `o_proj` (Mistral). Train only LoRA parameters.
- [ ] **2.5** Training: 2–5 epochs, batch size 1–4 (gradient accumulation if needed), learning rate 1e-5–5e-5. Save checkpoints and best model by validation loss.

**Deliverable:** Single script or notebook that: loads JSONL → loads base model → applies LoRA → trains → saves adapter (and optionally merged model).

---

### Phase 3: Evaluation and quality checks

- [ ] **3.1** Holdout set: keep a portion of exported data (e.g. 10%) never seen during training; report loss and simple metrics (exact match on section scores, or MAE per section).
- [ ] **3.2** Qualitative: run model on 20–50 holdout transcripts; compare scores and comments to human evaluations (agreement, reasonableness).
- [ ] **3.3** Guardrails: ensure output is valid JSON and scores stay within rubric bounds; add retry or fallback to general LLM if parsing fails.

**Deliverable:** Eval script + short report (metrics + 2–3 example comparisons).

---

### Phase 4: Integration into SpeechGradebook

- [ ] **4.1** **Option A (local/self-hosted):** Serve the fine-tuned **Mistral 7B** adapter via a small API (e.g. FastAPI + Hugging Face `pipeline` or vLLM). SpeechGradebook calls this API instead of (or in addition to) OpenAI/Gemini/Claude.
- [ ] **4.2** **Option B (OpenAI fine-tuned):** Use your fine-tuned model name in existing OpenAI integration; no new backend.
- [ ] **4.3** In the app: add “SpeechGradebook model” or “Fine-tuned” as a provider; map API response back to `evaluation_data.sections` so the rest of the UI stays unchanged.
- [ ] **4.4** Logging: log which model was used (base vs fine-tuned) in evaluations for future analysis.

**Deliverable:** Working path in the app that uses the trained model for at least one rubric.

---

## 4. File and repo layout (suggested)

```
SpeechGradebook/
  llm_training/
    README.md                 # How to run export + train
    export_training_data.js  # Or .ts / Supabase Edge; produces JSONL
    train.jsonl              # Generated; do not commit large files
    validation.jsonl
    train_lora.py            # LoRA fine-tuning script
    eval_model.py            # Holdout evaluation script
    requirements-train.txt   # Python deps for training
```

Keep raw exports and large JSONL out of git (e.g. `.gitignore`: `*.jsonl`, `llm_training/exports/`).

---

## 5. Next steps (what we do first)

1. **Implement Phase 1:** Export pipeline that reads consented data and writes JSONL in the messages format above (script or in-app export). Include a small example and document the schema.
2. **Add `llm_training/` and `requirements-train.txt`** so the training environment is one `pip install -r requirements-train.txt` away.
3. **Implement Phase 2:** Minimal `train_lora.py` for **Mistral 7B** so you can run “export → train” locally or in the cloud.

**Model locked:** **Mistral 7B** + LoRA. See `llm_training/train_lora.py` for the training script.
