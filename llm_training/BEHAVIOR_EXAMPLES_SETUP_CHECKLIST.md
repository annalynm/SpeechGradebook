# Behavior example videos: setup checklist

Use this checklist so your **uploaded example videos** work both **(A) as reference during evaluations** and **(B) as optional training data**.

---

## Part A: Use example videos as reference when evaluating (no training)

So the Qwen (video) model uses your behavior definitions and optional media URLs **when it runs an evaluation**.

| Step | Action |
|------|--------|
| 1 | **Upload files** to Supabase: Storage → `evaluation-media` → folder **`behavior-examples`**. Use the **exact filenames** in `BEHAVIOR_EXAMPLES_UPLOAD.md` (e.g. `hands-in-pockets.mp4`, `purpose-statement.mp4`). |
| 2 | **Public read:** Ensure the `evaluation-media` bucket (or at least `behavior-examples/`) is publicly readable so Qwen can load the URLs. |
| 3 | **URLs in JSON:** In `qwen_behavior_references.json`, each entry’s `media_url` must point to your Supabase project (e.g. `https://YOUR_PROJECT_REF.supabase.co/storage/.../behavior-examples/filename.mp4`). Replace `YOUR_PROJECT_REF` with your project ref if needed. |
| 4 | **Restart Qwen:** Restart the Qwen service (local, ISAAC, or Render) so it reloads `qwen_behavior_references.json` with the new URLs. |
| 5 | **Evaluate:** In SpeechGradebook, run evaluations with **SpeechGradebook Text + Video Model (Qwen)**. The model will use your behavior definitions and timeline markers. |

No training step is required for Part A.

---

## Part B: Use example videos as training data (optional)

To have Mistral or Qwen **learn** from your behavior clips, generate manifests and merge with your main export.

### One-time: generate behavior-example manifests

From the repo root or from `llm_training/`:

```bash
python llm_training/scripts/build_behavior_examples_manifests.py
```

This reads `qwen_behavior_references.json` and writes:

- **`behavior_examples_qwen.jsonl`** — one line per behavior with `video_path` (or `image_path`), placeholder `rubric` and `scores`. For **Qwen-VL** training.
- **`behavior_examples_export.json`** — array of records with `transcript`, `video_notes` (from description + scoring_guidance), `rubric`, `scores`. For **Mistral** (merge with `exported.json` → `export_to_jsonl.js` → `train_lora.py`).

Edit the generated files to replace placeholder rubric/scores with your real rubric structure and desired scores for each behavior, then:

### Qwen

- Merge with your main Qwen manifest (e.g. append lines to `train_qwen.jsonl`) or use `behavior_examples_qwen.jsonl` alone.
- Run your Qwen-VL training pipeline (e.g. `train_qwen_vl.py` or ISAAC).

### Mistral

- Merge: `combined = [ ...exported_from_app, ...behavior_examples_export_records ]` into one JSON file.
- Run: `node export_to_jsonl.js combined_export.json --split 0.9` then `python train_lora.py --train_file train.jsonl --validation_file validation.jsonl ...`

See **BEHAVIOR_EXAMPLES_NEXT_STEPS.md** and **EXAMPLE_VIDEOS_TRAINING.md** for full details.

---

## Summary

| Goal | What to do |
|------|------------|
| **Reference only (evaluate with Qwen)** | Complete Part A: upload with correct filenames, public bucket, correct URLs in JSON, restart Qwen. |
| **Train Qwen with behavior clips** | Run `build_behavior_examples_manifests.py`, edit rubric/scores in `behavior_examples_qwen.jsonl`, merge with `train_qwen.jsonl` or use alone, run Qwen training. |
| **Train Mistral with behavior clips** | Run `build_behavior_examples_manifests.py`, edit rubric/scores in `behavior_examples_export.json`, merge with `exported.json`, run `export_to_jsonl.js` and `train_lora.py`. |
