# What You Need to Train Qwen and Mistral on Evaluations

This document spells out **consent**, **export flow**, **data formats**, **scripts**, and **environment** so you can train both the text-based model (Mistral) and the video-based model (Qwen) on your SpeechGradebook evaluations.

---

## 1. Consent (required for export)

The app only includes evaluations in LLM training exports when **both** of the following are satisfied:

| Who | What | Where in the app / DB |
|-----|------|------------------------|
| **Student** | Data-use consent for the course | `consent_forms`: `consent_type = 'data_collection'`, `consent_given = true` (same consent used for grading, platform improvement, research). |
| **Instructor** | LLM training consent | `user_profiles`: `llm_training_consent_given = true` (instructor opts in via Settings or consent prompt). |

- Export filters out evaluations from courses where the student has not given data-use consent and from instructors who have not given LLM training consent.
- Demo-tier accounts are excluded from training exports.

---

## 2. Export flow (Super Admin only)

- **Where:** Analytics → **Evaluations** (or the **LLM Export** tab). Super Admin only.
- **Main export:** Click **Download for LLM training** → saves `exported.json` with consented evaluations in the format expected by the training pipeline.

**Export types:**

| Export | File / use | Purpose |
|--------|------------|--------|
| **Download for LLM training** | `exported.json` | Single format for both Mistral (after conversion) and Qwen. Contains transcript, rubric, scores, markers, optional video_url. |
| **Convert to JSONL** | Run `node export_to_jsonl.js exported.json [--split 0.9]` | Produces `train.jsonl` (and optional `validation.jsonl`) for **Mistral**. |
| **Qwen single-eval manifest** | From same export or **Train Qwen on ISAAC** flow | Build `train_qwen.jsonl` (one line per evaluation: video_path/URL, rubric, scores). |
| **Correction pairs** | **Export correction pairs (download JSONL)** | `train_qwen_correction_pairs.jsonl`: AI vs instructor (scores_original, scores_final). |
| **Comparison pairs** | **Export comparison pairs (download JSONL)** | `train_qwen_pairs.jsonl`: same student, two speeches (video_path_1, video_path_2, rubric, scores). |

See **COMPARISON_AND_CORRECTIONS_TRAINING.md** for when to use correction vs comparison pairs.

---

## 3. Data formats

### Mistral (text tier)

- **Input to convert:** `exported.json` (from “Download for LLM training”).
- **After convert:** `train.jsonl` (and optionally `validation.jsonl`). Each line is one JSON object with a `messages` array (system / user / assistant) for instruction tuning:
  - **User:** rubric + transcript (and optional video_notes).
  - **Assistant:** JSON scores/comments in the same shape as `evaluation_data.sections`.

See `llm_training/README.md` and `example_train.jsonl` for the exact structure.

### Qwen (video tier)

- **Manifest:** `train_qwen.jsonl`. One JSON object per line:
  - `video_path` or `image_path`: URL or path to video/image.
  - `rubric`: full rubric object (name, categories, subcategories).
  - `scores`: target scores in the same shape the model should output (e.g. `{"Content": {"score": 35, "maxScore": 40, "subcategories": [...]}, "Delivery": {...}}`).

Optional exports for advanced training:

- **Correction pairs:** `train_qwen_correction_pairs.jsonl` — `video_path`, `rubric`, `scores_original`, `scores_final` (and optional `evaluation_id`). Use when you want the model to learn from instructor overrides.
- **Comparison pairs:** `train_qwen_pairs.jsonl` — `video_path_1`, `video_path_2`, `rubric`, scores for both. Use for “same student, two speeches” (e.g. Persuasive 1 vs 2).

Your training script must support these formats; the in-repo `train_qwen_vl.py` currently expects the single-eval manifest format and validates it (see Scripts below).

---

## 4. Scripts

| Script | Model | Purpose |
|--------|--------|--------|
| `export_to_jsonl.js` | Mistral | Converts `exported.json` → `train.jsonl` (and optional `validation.jsonl`). Run: `node export_to_jsonl.js exported.json [--split 0.9]`. |
| `train_lora.py` | Mistral | LoRA fine-tuning on Mistral 7B. Needs `train.jsonl` (and optionally `validation.jsonl`). Run: `python train_lora.py --train_file train.jsonl [--validation_file validation.jsonl] --output_dir ./mistral7b-speech-lora`. Use `--load_in_8bit` for ~10GB VRAM. |
| `train_qwen_vl.py` | Qwen | Validates `train_qwen.jsonl` manifest; `--validate_only` checks format and paths. A full training loop (Dataset + Qwen2.5-VL + LoRA) is not yet implemented in this repo—see **DUAL_MODEL_TRAINING.md** for options (LLaMA-Factory or extend this script). |
| `train_speechgradebook.slurm` | Mistral | ISAAC SLURM job for Mistral training. |
| `train_qwen_speechgradebook.slurm` | Qwen | ISAAC SLURM job for Qwen; runs `train_qwen_vl.py` when manifest exists (e.g. validate or future training step). |

**Python dependencies:** Install once (e.g. in a venv or conda env on ISAAC):

```bash
pip install -r llm_training/requirements-train.txt
```

You also need a Hugging Face token for Mistral: `export HF_TOKEN=your_token`.

---

## 5. Environment (where to run training)

| Option | Notes |
|--------|--------|
| **ISAAC (campus HPC)** | Recommended: free GPU access (e.g. `campus-gpu`, V100/A40). Use your account (e.g. `acf-utk0011`) and `--qos=campus-gpu`. Copy `llm_training/` and your export/manifest files, then `sbatch train_speechgradebook.slurm` or `train_qwen_speechgradebook.slurm`. See **ISAAC_SETUP.md**, **ISAAC_QUICK_FIXES.md**. |
| **RunPod / Lambda Labs / other cloud GPU** | Same scripts; ensure enough VRAM (Mistral ~10–16 GB with 8-bit; Qwen-VL typically ≥24 GB). |
| **Local machine** | Only if you have a suitable GPU; same commands, often with `--load_in_8bit` for Mistral. |

---

## Quick reference: Mistral vs Qwen

| Step | Mistral (text) | Qwen (video) |
|------|-----------------|--------------|
| 1. Consent | Student `data_collection` + instructor `llm_training_consent_given` | Same |
| 2. Export | Super Admin → **Download for LLM training** → `exported.json` | Same export; use video_url / paths for Qwen manifest |
| 3. Convert | `node export_to_jsonl.js exported.json [--split 0.9]` → `train.jsonl` | Build `train_qwen.jsonl` (or use correction/comparison exports) |
| 4. Train | `python train_lora.py --train_file train.jsonl --output_dir ./mistral7b-speech-lora` | `python train_qwen_vl.py --manifest train_qwen.jsonl --validate_only` (validation only; full training via LLaMA-Factory or extended script) |
| 5. Serve | `serve_model.py` for text-tier API | Qwen service (e.g. `qwen_serve.py`) when you want video-tier evaluations |

For more detail: **README.md**, **DUAL_MODEL_TRAINING.md**, **STEPS_TO_REAL_EVALUATIONS.md**, **COMPARISON_AND_CORRECTIONS_TRAINING.md**.
