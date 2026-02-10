# Training Both Models: Two-Tier Evaluation

You can train **both** the text-based model (Mistral) and the video-based model (Qwen) on ISAAC and use them as two tiers: a cheaper text-only tier (e.g. for students) and a premium video tier (e.g. for departments/instructors).

---

## Two-tier idea

| Tier | Model | Input | Use case |
|------|--------|--------|----------|
| **Text / student** | SpeechGradebook Text Model (Mistral + LoRA) | Transcript (+ optional video notes) | Lower-cost evaluations; transcript-only or with brief video notes. |
| **Video / instructor** | SpeechGradebook Text + Video Model (Qwen2.5-VL + LoRA) | Video + rubric | Full video analysis: content and delivery from the actual video (analyzes both video and text). |

- **Mistral** is already set up: you train with `train_lora.py` on exported (transcript, video_notes, rubric) → scores. Run it on ISAAC with your existing SLURM job.
- **Qwen** training uses your **video files** plus a manifest (video path, rubric, scores). That produces a second model you serve for the video tier.

The app can later choose which model to call based on tier (e.g. student vs instructor) or feature (e.g. “Quick evaluate” = Mistral, “Full video evaluate” = Qwen).

---

## Can ISAAC run both?

**Yes.** ISAAC gives you GPU nodes (e.g. `campus-gpu` with V100/A40). There’s no per-job dollar cost to you.

- **Mistral training** (current): 1 GPU, ~16 GB VRAM with 8-bit, a few hours depending on data size. You already have `train_speechgradebook.slurm`.
- **Qwen-VL training**: 1 GPU with ≥24 GB VRAM (e.g. A40 or V100 32GB). LoRA on Qwen2.5-VL-7B fits on these. Run as a **separate** SLURM job (same or different partition).

You can run them **one after the other** (submit Mistral, when it finishes submit Qwen) or **in parallel** if your allocation allows two GPU jobs at once. Both use the same ISAAC login and project; only the scripts and conda env differ.

---

## 1. Training Mistral (text tier) – already in place

- Export from the app (or merge with example-video records) → `exported.json`.
- Convert: `node export_to_jsonl.js exported.json --split 0.9` → `train.jsonl`, `validation.jsonl`.
- On ISAAC: upload `llm_training/`, then submit:
  ```bash
  sbatch train_speechgradebook.slurm
  ```
- Output: `mistral7b-speech-lora/`. Use with `serve_model.py` for the **text-based** (cheaper) tier.

---

## 2. Training Qwen (video tier) – what you need

### Storing video from the UI

When you **save an evaluation** in SpeechGradebook after evaluating a speech with a **video file** (or audio file), the app uploads that file to **Supabase Storage** and stores the URL in the evaluation record. That way you can train the Qwen video model from the same workflow you already use.

- Create a Supabase Storage bucket named **`evaluation-media`** in your project (Dashboard → Storage → New bucket). Set RLS so that your app’s authenticated users can upload and read.
- After saving evaluations with video, use **Settings → Admin** or **Platform Analytics → LLM Export tab** and click **Train SpeechGradebook Text + Video Model (Qwen) on ISAAC** to export a manifest of all consented evaluations that have `video_url` set. The manifest uses those storage URLs so the training job can download videos (or you can point the script at local paths instead).

### Data (manual or from UI)

You need **videos** plus **labels** (rubric + scores) for each:

- **Videos**: From the UI they are stored in Supabase (`evaluation-media` bucket) and the export uses their URLs. Alternatively, store files in a folder ISAAC can see (e.g. under `~/llm_training/data/videos/`), or on Lustre.
- **Manifest**: One JSONL file, e.g. `train_qwen.jsonl`, where **each line** is a JSON object:
  - `video_path` or `image_path`: path or URL to the video file (MOV, MP4, etc.) or image (PNG, etc.). Each line must have at least one (for coding examples that are videos or still images).
  - `rubric`: full rubric object (same as in the app: name, categories, subcategories, points).
  - `scores`: target scores in the same shape the model should output (e.g. `{"Content": {"score": 35, "maxScore": 40, "subcategories": [...]}, "Delivery": {...}}`).

Example line:

```json
{"video_path": "videos/speech_001.mp4", "rubric": {"name": "Informative Speech", "categories": [...]}, "scores": {"Content": {"score": 32, "maxScore": 40, "subcategories": [{"name": "Organization", "points": 12, "maxPoints": 15}, ...]}, "Delivery": {...}}}
```

You can generate this from your existing exports if you still have the original videos and can match them (e.g. by evaluation id). For “example” videos you’re labeling by hand, create one manifest line per video with the rubric and the scores you want the model to learn.

### Training script (Qwen-VL LoRA)

A **Qwen-VL training script** would:

1. Load a manifest (e.g. `train_qwen.jsonl`) and optionally split for validation.
2. Build a dataset that, for each item, loads the video and rubric and uses the Qwen2.5-VL processor to build the input (video + “Score this speech with the given rubric…” etc.), with the target output = the scores JSON.
3. Run LoRA (or PEFT) training on Qwen2.5-VL-7B (e.g. with `transformers` + `peft`, or a framework like LLaMA-Factory that supports Qwen2.5-VL).

This is a separate codebase from `train_lora.py` (which is Mistral-only). Options:

- **LLaMA-Factory**: Official Qwen docs mention it for Qwen2.5-VL SFT/LoRA. You’d add a dataset adapter that reads your manifest and outputs the conversation format they expect.
- **Custom script**: A `train_qwen_vl.py` in `llm_training/` that reads `train_qwen.jsonl`, uses `Qwen2_5_VLProcessor` + `Qwen2_5_VLForConditionalGeneration`, and trains with PEFT/LoRA. Needs a Dataset that returns (input_ids, labels) from (video_path, rubric, scores).

A starter SLURM script for ISAAC, `train_qwen_speechgradebook.slurm`, is provided below. You’ll point it at your Qwen training script and env once that script exists.

### ISAAC job for Qwen

Example SLURM script (save as `llm_training/train_qwen_speechgradebook.slurm` and adjust partition/account/time):

```bash
#!/bin/bash
#SBATCH --job-name=qwen-speech-lora
#SBATCH --partition=campus-gpu
#SBATCH --account=ACCOUNT_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=logs/train_qwen_%j.out
#SBATCH --error=logs/train_qwen_%j.err

# Load env (same as qwen_serve: conda + requirements-qwen.txt; add peft, datasets for training)
module load anaconda3 2>/dev/null || true
conda activate speechgradebook 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# When train_qwen_vl.py exists and train_qwen.jsonl is ready:
# python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora ...

echo "Qwen-VL training: add train_qwen_vl.py and manifest, then uncomment the python line above."
```

Until `train_qwen_vl.py` is implemented, you can use this as a template and run Mistral training as usual.

---

## 3. Running “both at once” on ISAAC

- **Sequential**: Submit Mistral first (`sbatch train_speechgradebook.slurm`). After it finishes, submit Qwen (`sbatch train_qwen_speechgradebook.slurm`) if you have the Qwen script and manifest ready.
- **Parallel**: If your allocation allows two GPU jobs, submit both; they’ll queue and run when nodes are free. No extra cost.

So yes: you can **train both models on ISAAC** (Mistral now; Qwen once the training script and manifest exist), and use them as **text tier** (Mistral) and **video tier** (Qwen).

---

## 4. Next steps

1. **Mistral (text tier)**  
   Keep using your current pipeline and ISAAC job. Add example-video records to `exported.json` (transcript + video_notes + scores) if you want the text model to learn from those too.

2. **Prepare Qwen (video tier) data**  
   - Put your “lots of videos” in a directory (e.g. `llm_training/data/videos/`).  
   - Build `train_qwen.jsonl` (and optionally `validation_qwen.jsonl`) with one JSON object per line: `video_path`, `rubric`, `scores`.  
   - Use the same rubric structure as in the app so the model’s output format matches.

3. **Qwen training script**  
   - Either integrate with **LLaMA-Factory** (or another Qwen2.5-VL–capable framework) and a custom dataset that reads your manifest, or  
   - Add a custom **train_qwen_vl.py** in this repo that: reads the manifest, builds a PyTorch Dataset (video + rubric → scores), and runs LoRA training with the Qwen2.5-VL processor/model.  
   Then wire that script into `train_qwen_speechgradebook.slurm` and run it on ISAAC.

4. **App tier logic (later)**  
   When both models are trained and deployed, the app can call:  
   - **Text tier**: SpeechGradebook Text Model (Mistral) for transcript-only or transcript + video_notes.  
   - **Video tier**: SpeechGradebook Text + Video Model (Qwen) for full video + rubric evaluation (analyzes both video and text).

5. **Comparison pairs and instructor corrections**  
   To train the model in greater depth (e.g. “improvement” between Persuasive 1 and 2, and instructor edits), see **COMPARISON_AND_CORRECTIONS_TRAINING.md**. The UI can export **comparison pairs** (same student, two speeches) as `train_qwen_pairs.jsonl`; extend your training script to accept this format when ready.

If you want, the next concrete step can be adding a minimal `train_qwen_vl.py` (and manifest format) in this repo so you can run both trainings on ISAAC with the two-tier setup in mind.
