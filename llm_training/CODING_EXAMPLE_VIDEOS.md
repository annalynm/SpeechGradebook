# Using Coding Example Videos and Images with the SpeechGradebook Text + Video Model (Qwen)

Your **SpeechGradebook Coding Examples** can be **videos** (e.g. MOV, QuickTime, MP4) or **still images** (e.g. PNG) that show what a behavior looks like. For example, you might have 8 short video clips and 4 images (e.g. “hands in pockets,” “purpose statement”). You use these so the **SpeechGradebook Text + Video Model (Qwen)** knows what to look for, when to dock or award points, and how to mark the video timeline for instructor review.

---

## Goals

1. **Reference behaviors** – The model looks for the behaviors you defined (hands in pockets, vocalized pause, purpose statement, etc.) and scores the rubric accordingly (dock points for delivery issues, award points for content like purpose statement).
2. **Varying degrees** – The model can treat behaviors by severity (e.g. brief hands clasped = small deduction; prolonged = larger deduction). This is encoded in **behavior references** and in the rubric.
3. **Timeline markers** – For each behavior observed, the model outputs an approximate **timestamp** (e.g. 1:23) and a short note. These appear as **Timeline Markers** in the evaluation so the student (and instructor) can jump to that moment in the video.
4. **Instructor review** – After the model runs, the instructor sees the timeline markers. They can **add** (model missed something), **delete** (model was wrong), or **edit** (refine). If the instructor doesn’t change a marker, it is treated as correct.

---

## Step 1: Define behaviors (from your coding example videos and images)

The app uses a **behavior reference file** so Qwen knows what to look for and how to score. That file is:

**`llm_training/qwen_behavior_references.json`**

A template is provided with entries that match your coding example names (whether each example is a video or a still image), for example:

- **Hands in pockets** – Dock in Delivery; more frequent = larger deduction.
- **Hands clasped (in front)** / **Hands clasped behind** – Dock if prolonged; mild = small or no deduction.
- **Swaying** – Dock in Delivery (posture); severe = significant deduction.
- **Tapping hands** – Dock in Delivery (distracting mannerism).
- **Vocalized pause** – Dock in Delivery (um, uh, like); many = larger deduction.
- **Purpose statement** – Credit in Content (organization/introduction); strong = full points, missing = deduct.

Each entry has:

- **label** – Short name (matches your video/image names where possible).
- **type** – `"delivery"` or `"content"`.
- **description** – What to look for in the video, audio, or image.
- **scoring_guidance** – How to apply points (dock in Delivery, credit in Content, etc.).
- **severity_default** – Optional: `"positive"`, `"minor"`, `"moderate"`, `"major"` for timeline display.
- **media_url** – Optional: URL to the coding example video or image (e.g. from SpeechGradebook uploads to Supabase). Used for reference; the model still gets the text description in the prompt.
- **media_type** – Optional: `"video"` or `"image"` when `media_url` is set.

You can edit this file after reviewing your coding example clips and images so the descriptions and scoring guidance match how you use them in class.

---

## Step 2: Align your rubric with these behaviors

**Blank rubrics:** If your rubrics are in PNG, PDF, Google Sheets, or Excel, you can (1) use **Import Rubric from File** in the app (Dashboard → Rubrics → Import from File) and **Extract & Create Rubric**, or (2) create the rubric manually in Dashboard → Rubrics. For Google Sheets, export as XLSX or CSV first, then upload.

Your rubric categories should reflect what you want the model to score:

- **Delivery** – Subcategories such as posture/body control, gestures, vocal delivery (so the model can dock for hands in pockets, swaying, tapping, vocalized pauses, etc.).
- **Content** – Subcategories such as organization or introduction (so the model can award points for a clear purpose statement).

The model uses the rubric’s point values and the behavior references together: when it sees “hands in pockets” it docks in the relevant Delivery subcategory; when it hears a purpose statement it credits the relevant Content subcategory.

---

## Step 3: Run a video evaluation

1. In SpeechGradebook, choose **SpeechGradebook Text + Video Model (Qwen)** as the evaluation provider.
2. Upload a **video** of a student speech and select the appropriate rubric.
3. Run the evaluation.

The Qwen service will:

- Load **qwen_behavior_references.json** (if present) and add those behaviors to the prompt.
- Watch and listen to the video, score the rubric (including docking/awarding for the reference behaviors).
- Output **timeline_markers**: a list of approximate timestamps with a label and short observation (e.g. `1:23 – Hands in pockets`, `2:45 – Vocalized pause`, `0:15 – Purpose statement`).

The app displays these markers on the results page so the student can seek to those times in their video.

---

## Step 4: Instructor review (confirm or correct)

After the evaluation loads:

1. Open the **Timeline Markers** section.
2. For each marker you can:
   - **Leave it** – If the model is correct, do nothing.
   - **Edit** – Change the time, label, or note if the model was close but not quite right.
   - **Delete** – Remove a marker that is wrong (e.g. model misidentified a behavior).
   - **Add** – Insert a new marker where the model missed something (e.g. “At 3:10 – Hands in pockets”).

If the instructor doesn’t change a marker, it is treated as correct. When you save the evaluation, the (possibly corrected) timeline markers are stored with the evaluation so the student sees the final list.

---

## Step 5 (optional): Train Qwen on your coding example clips and images

To improve recognition over time, you can use the same clips and images as **training data** for the SpeechGradebook Text + Video Model (Qwen):

1. Upload your coding example **videos** (MOV, QuickTime, MP4, etc.) or **images** (PNG) through the SpeechGradebook UI when you run evaluations; they are stored in Supabase and get `video_url` (or you can add manifest lines manually for image examples).
2. For each coding example, create a **minimal rubric** and a **score** that reflects the behavior (e.g. “Hands in Pockets Example” → Delivery docked by X points; “Purpose Statement Example” → Content credited).
3. Build a **manifest** (e.g. `train_qwen.jsonl`) with one line per example. Each line must have **either** `video_path` **or** `image_path` (URL or path), plus `rubric` and `scores`:
   - Video: `{"video_path": "https://.../HandsInPockets.mov", "rubric": {...}, "scores": {...}}`
   - Image: `{"image_path": "https://.../purpose_statement.png", "rubric": {...}, "scores": {...}}`
4. Run **Train SpeechGradebook Text + Video Model (Qwen) on ISAAC** (or your training pipeline) so the model learns what those behaviors look (and sound like, for video).

This is separate from the **reference** use above: references tell the model what to look for at inference time; training makes the model better at spotting those behaviors. See **DUAL_MODEL_TRAINING.md** and **EXAMPLE_VIDEOS_TRAINING.md** for training details.

---

## Summary

| Step | What you do |
|------|-------------|
| 1 | Edit **qwen_behavior_references.json** so labels and scoring match your coding example videos/images and rubric. |
| 2 | Bring in blank rubrics (PNG, PDF, Sheets/Excel) via **Import Rubric from File** or create manually. Ensure the rubric has Delivery (and Content) subcategories that match the behaviors. |
| 3 | Run evaluations with **SpeechGradebook Text + Video Model (Qwen)**; the model uses the behavior references and outputs timeline markers. |
| 4 | Review timeline markers in the app: add, edit, or delete as needed; unchanged markers count as correct. |
| 5 (optional) | Use coding example videos and images as training data: build `train_qwen.jsonl` with `video_path` or `image_path` per line, then run Qwen training on ISAAC. |

The behavior reference file is the link between your **SpeechGradebook Coding Examples** (videos and images) and what the model looks for and how it scores. Timeline markers make it easy for you and the instructor to confirm or correct the model’s timestamps before the student sees the evaluation.
