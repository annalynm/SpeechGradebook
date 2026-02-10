# Using Example Videos to Train and Guide the SpeechGradebook Text Model (Mistral)

The **SpeechGradebook Text Model (Mistral)** uses **video notes** (a text description of visual delivery from Qwen or Gemini) plus the transcript when scoring. The **SpeechGradebook Text + Video Model (Qwen)** assesses the video directly (and text). You can use your example videos in two ways: **(1) reference examples** so the model knows what to look for (e.g. swaying, purpose statement), and **(2) training data** so it learns your scoring standards.

You can use example videos of verbal and nonverbal communication behaviors as **additional training data**. The model learns to associate descriptions of those behaviors (in the “video notes” and transcript) with the scores you assign, so it scores real assessments more consistently with your standards.

---

## 1. Reference examples (what to look for when scoring)

Reference examples are short descriptions of behaviors you want the model to **identify** in student videos (e.g. swaying, purpose statement, strong eye contact). They are injected into every evaluation prompt so the model uses them when scoring.

- **Create** a file `reference_examples.json` in the `llm_training` folder (or set env `REFERENCE_EXAMPLES_PATH` to your file).
- **Format**: JSON array of objects. Copy from `reference_examples.template.json`. Each object can have: `label`, `type` (delivery/content), `description`, `scoring_guidance`, and optional `example_excerpt`.
- After you add the file, restart the SpeechGradebook Text Model (Mistral) server. The model will use these when evaluating every submission (transcript + video notes).

---

## 2. Training data (how to score)

### How it fits the pipeline

Training data is **one record per evaluation**: transcript + (optional) video notes + rubric → scores.  
For each example video you add a **synthetic** record:

1. **Transcript** – what was said (from the video).
2. **Video notes** – description of nonverbal/verbal behaviors you want the model to learn (e.g. eye contact, posture, gestures, vocal variety).
3. **Rubric** – same rubric name and structure you use in assessments.
4. **Scores** – the scores you want the model to learn for this example (e.g. “this is strong eye contact” → full points for that subcategory).

Those records use the **same format** as the app’s export, so you merge them with your normal export and run the usual `export_to_jsonl.js` → `train_lora.py` pipeline.

---

## Step-by-step

### 1. Prepare one record per example video

For each example video, you need:

| Field | How to get it | Example |
|-------|----------------|--------|
| **transcript** | Whisper on the video, or type it manually | `"First I'll cover the main points..."` |
| **video_notes** | Qwen (video description) or write it yourself | `"Strong eye contact with camera. Relaxed posture. Occasional hand gestures. Steady pacing."` |
| **rubric** | Rubric name from your app | `"Informative Speech"` |
| **rubric_structure** | Same categories/subcategories as in the app (optional but helps) | `{ "categories": [ { "name": "Delivery", "subcategories": ["Eye contact", "Vocal delivery"] } ] }` |
| **scores** | The scores you want the model to learn for this example | `{ "Delivery": { "score": 28, "maxScore": 30, "subcategories": [ { "name": "Eye contact", "points": 15, "maxPoints": 15 }, ... ] } }` |

- **Transcript**  
  - Option A: Run Whisper on the video (e.g. `whisper video.mp4 --model base`), then paste the transcript.  
  - Option B: Type or edit the transcript manually.

- **Video notes (behavior description)**  
  - Option A: Use Qwen: run the video through your Qwen service (e.g. “Describe the speaker’s nonverbal delivery: eye contact, posture, gestures, use of space”) and use that text as `video_notes`.  
  - Option B: Write it yourself: a short paragraph describing what you see (e.g. “Strong eye contact, minimal notes, clear gestures, good energy”).

- **Rubric and scores**  
  - Use the **exact same** rubric name and structure as in SpeechGradebook.  
  - Assign scores that match what you want the model to learn (e.g. “this clip is our example of excellent eye contact” → give full points for Eye contact).

### 2. Format as JSON (same as app export)

Each example is one object in a JSON **array**. Required keys: `transcript`, `rubric`, `scores`. Optional but recommended: `video_notes`, `rubric_structure`.

See `example_videos_export.template.json` in this folder. Structure:

```json
[
  {
    "transcript": "Full text of what was said in the video.",
    "video_notes": "Description of nonverbal/verbal behaviors: eye contact, posture, gestures, vocal delivery, etc.",
    "rubric": "Informative Speech",
    "rubric_structure": {
      "categories": [
        { "name": "Content", "subcategories": ["Organization", "Supporting Material", "Conclusion"] },
        { "name": "Delivery", "subcategories": ["Eye contact", "Vocal delivery"] }
      ]
    },
    "scores": {
      "Content": { "score": 38, "maxScore": 40, "subcategories": [ ... ] },
      "Delivery": { "score": 28, "maxScore": 30, "subcategories": [ ... ] }
    }
  }
]
```

You can add optional keys like `student_hash` or `institution_hash` if you use them for splitting; the converter ignores unknown keys.

### 3. Merge with your existing export and convert to JSONL

- If you already have `exported.json` from the app:
  - Combine the two arrays (e.g. in a script or by hand):  
    `combined = [ ...exported_from_app, ...example_video_records ]`  
  - Save as one JSON file (e.g. `combined_export.json`).

- If you **only** use example videos for this run:
  - Use your example-videos JSON file as the single export.

Then run the same converter as for normal export:

```bash
cd llm_training
node export_to_jsonl.js combined_export.json --split 0.9
```

This produces `train.jsonl` and `validation.jsonl` (or a single `train.jsonl` if you don’t use `--split`).

### 4. Train as usual

```bash
python train_lora.py --train_file train.jsonl --validation_file validation.jsonl --output_dir ./mistral7b-speech-lora --load_in_8bit
```

Or submit to ISAAC using your existing training workflow; the data format is unchanged.

---

## Tips

- **Label clearly in video_notes**  
  The model learns from the text. Phrases like “consistent eye contact,” “read from notes often,” “monotone,” “effective gestures” help it tie behaviors to the scores you give.

- **Use the same rubrics as in the app**  
  Rubric name and structure should match so the model sees the same category/subcategory names at training and inference.

- **Mix with real evaluations**  
  Example videos are most useful when combined with real exported evaluations. That way the model sees both your “ideal” examples and real student variation.

- **Balance**  
  A few strong examples per behavior (e.g. 2–3 “excellent eye contact” and 2–3 “needs improvement”) can be enough to steer the model; you don’t need hundreds of example clips.

---

## Quick checklist

1. For each example video: get or write **transcript** and **video_notes** (behaviors).
2. Choose the **rubric** and assign **scores** that match what you want the model to learn.
3. Put all examples in one JSON array (same shape as `example_videos_export.template.json`).
4. Merge that array with `exported.json` from the app (if you have it).
5. Run `node export_to_jsonl.js <your_combined.json> [--split 0.9]`.
6. Train with `train_lora.py` (or your ISAAC job) on the resulting `train.jsonl` (and optional `validation.jsonl`).
