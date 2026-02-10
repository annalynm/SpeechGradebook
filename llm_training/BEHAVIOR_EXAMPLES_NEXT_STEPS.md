# What to do now: use behavior examples (inference + optional training)

You’ve uploaded the behavior-example videos to Supabase and set the URLs in `qwen_behavior_references.json`. Here’s what to do next.

**Quick checklist:** See **BEHAVIOR_EXAMPLES_SETUP_CHECKLIST.md** for a step-by-step list (reference use + training use).

---

## 1. Use behavior examples at evaluation time (no training)

The **Qwen (video) model** already uses your behavior examples **when it runs an evaluation**: it loads `qwen_behavior_references.json` and adds those behaviors (and optional `media_url`) to the prompt so the model knows what to look for and how to score.

**What you do:**

1. **Restart the Qwen service** (wherever it runs: Render, ISAAC, local) so it reloads `qwen_behavior_references.json` with the new Supabase URLs.
2. In SpeechGradebook, run evaluations with **SpeechGradebook Text + Video Model (Qwen)**. The model will use your behavior definitions and timeline markers for those behaviors.

No training step is required for this. The behavior examples are **reference data at inference**, not fine-tuning.

---

## 2. Optional: train the models *with* behavior examples

If you want the models to **learn** from your behavior clips (better scoring on similar behaviors), add them as **training data** and run your usual training pipeline.

### A. SpeechGradebook Text Model (Mistral)

Mistral is trained on **text**: transcript + video_notes + rubric → scores. For each behavior-example video you add one **synthetic** record: transcript (or “N/A”), **video_notes** (description of what the clip shows and how it should be scored), rubric name/structure, and the **scores** you want the model to learn for that example.

**Steps:**

1. **Generate Mistral records**  
   Run:  
   `python llm_training/scripts/build_behavior_examples_manifests.py`  
   This creates `behavior_examples_export.json` with one record per behavior (transcript "N/A", video_notes from description + scoring_guidance, placeholder rubric/scores). Edit the file to use your real rubric and scores if needed.

2. **One record per behavior clip (alternative: manual)**  
   For each of your behavior-example videos (e.g. hands-in-pockets, purpose-statement), create one JSON object with:
   - `transcript`: what was said (from Whisper or type “N/A” if it’s mostly nonverbal).
   - `video_notes`: short description of what the clip shows and how it should be scored (e.g. “Hands in pockets throughout; dock in Delivery for body/professionalism.”).
   - `rubric`: same rubric name you use in the app (e.g. `"Informative Speech"`).
   - `rubric_structure`: (optional) same categories/subcategories as in the app.
   - `scores`: the scores you want the model to learn for this example (e.g. deduct in Delivery for “hands in pockets” clip).

2. **Merge with your main export (optional)**  
   If you have `exported.json` from the app, combine:  
   `combined = [ ...exported_from_app, ...behavior_example_records ]`  
   Save as e.g. `combined_export.json`. If you’re only adding behavior examples for this run, use `behavior_examples_export.json` as the single file.

3. **Convert to JSONL and train**  
   ```bash
   cd llm_training
   node export_to_jsonl.js combined_export.json --split 0.9
   python train_lora.py --train_file train.jsonl --validation_file validation.jsonl --output_dir ./mistral7b-speech-lora --load_in_8bit
   ```  
   (Or use your existing ISAAC/SLURM workflow; the format is the same.)

See **BEHAVIOR_EXAMPLES_SETUP_CHECKLIST.md** for a concise checklist and **EXAMPLE_VIDEOS_TRAINING.md** for the exact JSON shape.

### B. SpeechGradebook Text + Video Model (Qwen)

Qwen is trained on **video + rubric → scores**. To include your behavior-example **videos** in training, add one line per clip to your Qwen training manifest (e.g. `train_qwen.jsonl`).

**Per line:**

- **video_path**: public URL of the behavior-example video in Supabase, e.g.  
  `https://mqhbfefylpfqsbtrshpu.supabase.co/storage/v1/object/public/evaluation-media/behavior-examples/hands-in-pockets.mp4`
- **rubric**: full rubric object (name, categories, subcategories, points) matching the app.
- **scores**: target scores for that clip in the same shape the model outputs (e.g. deduct in Delivery for “hands in-pockets” clip).

**Steps:**

1. **Build the manifest**  
   Run:  
   `python llm_training/scripts/build_behavior_examples_manifests.py`  
   This creates `behavior_examples_qwen.jsonl` (one line per behavior with `video_path`, placeholder `rubric` and `scores`). Edit the file to use your real rubric structure and scores if needed.

2. **Merge with your main Qwen manifest (if any)**  
   If you already have `train_qwen.jsonl` from Platform Analytics → LLM Export (evaluations with video), append these lines (or concatenate the files). Otherwise use `behavior_examples_qwen.jsonl` as the training manifest.

3. **Run Qwen training**  
   Use your existing Qwen-VL training pipeline (e.g. on ISAAC with the script that loads a video manifest and runs LoRA on Qwen2.5-VL). The manifest format is the same; the behavior-example lines just add extra (video_path, rubric, scores) examples.

See **DUAL_MODEL_TRAINING.md** for the Qwen manifest format and training overview.

---

## Summary

| Goal | Action |
|------|--------|
| **Use behavior examples when evaluating (no training)** | Restart the Qwen service; run evaluations with Qwen. Behavior refs are loaded from `qwen_behavior_references.json`. |
| **Train Mistral with behavior examples** | Add one text record per clip (transcript, video_notes, rubric, scores) → merge with export → `export_to_jsonl.js` → `train_lora.py` (or ISAAC). |
| **Train Qwen with behavior examples** | Add one manifest line per clip (video_path = Supabase URL, rubric, scores) → merge with `train_qwen.jsonl` → run Qwen-VL training. |
