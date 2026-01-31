# Faster Path to a Working, Trainable Model

If you already have speech videos and can provide feedback on evaluations, you can get to a working model faster by (1) getting evaluations **now** with an API LLM, (2) correcting and saving in SpeechGradebook, and (3) using those saved evaluations as your **only** training set. No separate data-collection phase.

---

## Pre-existing API evaluation architecture

The app **already contains** full support for API-based evaluations:

- **OpenAI (GPT-4o)**, **Google Gemini**, and **Anthropic Claude** evaluation paths are implemented: `evaluateWithGPT4o`, `evaluateWithGemini`, `evaluateWithClaude` (and helpers like `transcribeSpeech`, `evaluateWithClaudeAI`, `formatEvaluationResults`, etc.).
- **Settings** still have API key inputs for Gemini, OpenAI, and Claude; keys are stored in `localStorage`.
- **evaluateSpeech()** routes by provider (`finetuned`, `gpt4o`, `gemini`, `claude`, `demo`). Right now the **evaluation flow** is hardcoded to `apiProvider = 'finetuned'` and only uses the Fine-tuned server URL, so the API providers are not reachable from the current evaluation UI.
- **Reinstating** API evaluation means: add back a provider choice in the evaluation flow (e.g. a dropdown or toggle) and, when the user selects Gemini/OpenAI/Claude, pass that provider and the corresponding API key into `evaluateSpeech()` instead of always using `finetuned`. No new evaluation logic is required; the existing API code paths already handle upload → transcribe (where applicable) → evaluate → return sections + transcript.

When you save an evaluation after an API run, the app already stores **transcript** (at the top level of the evaluation record) and **evaluation_data** (sections, corrections, edited flag). So corrected API evaluations are suitable as training examples once you have an export from Supabase.

---

## Two phases

| Phase | Goal | Time |
|-------|------|------|
| **A. Working evaluations** | Evaluate your videos and get scores/feedback you can correct. | Days (once API + export are wired). |
| **B. Trainable model** | Use your corrected evaluations as training data; train LoRA; switch to your own model. | After you have ~30–100+ corrected evals. |

---

## Phase A: Working evaluations (fast)

**Idea:** Use an **existing LLM via API** (Gemini, OpenAI, or Claude) so you get real evaluations immediately. You correct in the app; the app stores **transcript**, **evaluation_data** (sections, corrections), and **video_notes** (when using Gemini or Fine-tuned + video) when you save. Each saved evaluation becomes a training example.

---

### Phase A — Step-by-step (detailed)

#### 1. Get an API key (choose one provider)

- **For video content (body movement, eye contact, slides): use Gemini.**
  - Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
  - Create or copy a Gemini API key (starts with `AIza`).
- **Optional alternatives:**
  - **OpenAI (GPT-4o):** [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — key starts with `sk-`.
  - **Claude:** [console.anthropic.com](https://console.anthropic.com) — key from API settings.
- Note: Claude uses **audio only**; GPT-4o uses a single video frame. For full video analysis (delivery, eye contact, slides), use **Gemini**.

#### 2. Add the key in SpeechGradebook Settings

- Open the app (e.g. `index.html` or your deployed URL).
- Go to **Settings** (gear icon or Settings in the menu).
- Find **API keys** (Gemini, OpenAI, Claude).
- Paste your **Gemini** key into the Gemini API key field and save.
- (Optional) Add OpenAI or Claude keys if you want to switch providers later.
- Keys are stored in your browser (localStorage); they are not sent to any server except the provider’s API when you run an evaluation.

#### 3. Run an evaluation (one video = one evaluation)

- Go to the **Evaluate** or **New evaluation** flow (e.g. “Evaluate speech” or “Add evaluation”).
- **Step 1 — Basic info:**
  - Select **Course** and **Student** (or the equivalent in your UI).
  - Choose **Assignment type** and **Speech date**.
- **Step 2 — File and rubric:**
  - **Upload** a video or audio file (e.g. MP4, WebM, MP3).
  - Select the **Rubric** you want the AI to use (e.g. “Informative speech”, “Persuasive”).
  - In **Evaluation provider**, choose:
    - **Gemini** — for full video analysis (content + delivery, eye contact, gestures, slides).
    - **Fine-tuned (SpeechGradebook)** — for your own model (requires a trained model and, for video, a Gemini key for video notes).
    - **GPT-4o** or **Claude** — if you prefer those (Claude = audio only).
  - Click **Evaluate** (or “Run evaluation”).
- **Step 3 — Wait:**
  - The app sends the file to the chosen provider (Gemini gets the full video; Claude transcribes then evaluates; etc.).
  - Progress text may say “Processing video file…”, “Analyzing speech…”, “Calculating final scores…”.
- **Step 4 — Results:**
  - You see **sections** (categories and subcategories), **scores**, **feedback**, and **overall comments**.
  - For Gemini, a **transcript** summary and **video_notes** (visual delivery) are also captured and will be saved when you save.

#### 4. Correct the AI feedback (important for training)

- Review each **section** (e.g. Content, Delivery).
- If a score or comment is wrong:
  - Click **Edit** (or the section) to open the edit modal.
  - Change **points** and/or **feedback** (and subcategory points if shown).
  - Fill in **Reason for change** (e.g. “Score was too harsh; student had strong eye contact”).
  - Save the edit.
- Repeat for every section you want to correct.
- Corrections are stored in `evaluation_data.corrections`; the **final** scores/comments you leave are stored in `evaluation_data.sections`. The model will be trained on these **corrected** sections.

#### 5. Save the evaluation

- When you’re satisfied with the scores and comments (after any edits), click **Save evaluation** (or “Save” / “Add to gradebook”).
- You may be asked to confirm **Course** and **Student** if not already set.
- On save, the app stores:
  - **transcript** (from the provider or transcription step),
  - **evaluation_data**: `sections` (final scores/comments), `video_notes` (if Gemini or Fine-tuned + video), `corrections`, `overallComments`, etc.,
  - **rubric_id** (which rubric was used),
  - **ai_provider** (e.g. `gemini`),
  - and other metadata (student, course, date, etc.).
- Saving writes to **Supabase** (and optionally localStorage). Each saved row is one training example for Phase B.

#### 6. Repeat for many speeches

- **Target:** At least **30–100+** saved evaluations (more is better).
- Use a mix of students and speeches if possible.
- Prefer **Gemini** for video speeches so **video_notes** are stored and your future model can learn visual delivery (body movement, eye contact, slides).
- You can switch providers per evaluation (e.g. Gemini for some, Claude for audio-only) if you like; just correct and save each one.

#### 7. Check that data is ready for export

- Evaluations must have:
  - **transcript** not null, and
  - **evaluation_data.sections** present (the rubric categories and scores).
- If you used Gemini (or Fine-tuned + video with a Gemini key), **evaluation_data.video_notes** will be set; the export script and training pipeline will include it so the model learns from video content too.

---

### Phase A — What you need (summary)

| Requirement | Details |
|-------------|--------|
| API key | At least one: **Gemini** (recommended for video), or OpenAI, or Claude. |
| Rubrics | Create or select rubrics in the app so the AI (and later the trained model) knows categories and point values. |
| Videos/audio | Upload one file per evaluation; format supported by the chosen provider (e.g. MP4, WebM for Gemini). |
| Corrections | Edit wrong scores/feedback and add a reason; the **final** sections are what get exported for training. |
| Save | Click Save after each evaluation so it’s stored in Supabase with transcript, sections, and video_notes (when available). |

**Result:** You can evaluate as many videos as you want, correct in the app, and save. Each save is one training example (transcript + rubric + corrected sections + video_notes when present). When you have 30–100+, proceed to Phase B (export from Supabase → JSONL → train LoRA).

---

### Phase A — Original “what you need” (reference)

1. **Transcription for your videos**  
   - Either: run the **Fine-tuned** server with **Whisper** installed (no model loaded). Today the server returns 503 when no model is loaded, so this would require a small change: when no model is loaded, the server could still run Whisper and return transcript + placeholder sections (or 503 only on “evaluate” and a separate “transcribe only” endpoint).  
   - Or: use an external transcription (e.g. Whisper API, or paste transcript manually).  
   - Or: add an **API-based evaluation** path in the app (see below).

2. **API-based evaluation path in the app**  
   - Add (or re-enable) an option to call **OpenAI** or **Claude** with: system prompt = “You are a speech evaluator…”, user = rubric + transcript, and parse the response into `sections`.  
   - Flow: upload file → transcribe (Whisper locally or API) → send transcript + rubric to API LLM → show results → you correct and save.  
   - Then every saved evaluation has: **transcript** (already stored at top level), **rubric** (via rubric_id), and **evaluation_data.sections** (your corrected scores). That is exactly the shape needed for training.

3. **Ensure transcript is stored**  
   - When you save after a Fine-tuned evaluation, the app already saves `evaluation.transcript`. For an API-based flow, the app must set `evaluation.transcript` from the transcription step before save so it’s in the DB.

**Result:** You can evaluate as many videos as you want, correct in the app, and save. Each save is one training example (transcript + rubric + corrected sections).

---

## Phase B: Export and train (same as today, different data source)

**Idea:** Your **training set** = evaluations you created and corrected in the app. No need for a separate “export from Super Admin” of other people’s data.

**What you need:**

1. **Export from Supabase**  
   - Query evaluations that have:
     - `transcript` not null  
     - `evaluation_data` with `sections`  
   - Join with **rubrics** to get the full rubric (name + structure).  
   - Output one object per evaluation in the shape `export_to_jsonl` expects:
     - `transcript`
     - `rubric` (full rubric object or at least name + structure for the prompt)
     - `scores` = **evaluation_data.sections** (the saved, corrected sections)
   - Optional: anonymize (e.g. strip PII, use hashes) and respect consent (e.g. only export where consent for LLM training is given).  
   - Write to a file, e.g. `exported.json`, in the same format as `sample_exported.json` (array of `{ transcript, rubric, scores, ... }`).

2. **Run the existing pipeline**  
   - `node export_to_jsonl.js exported.json > train.jsonl` (optional: `--split 0.9`).  
   - `python llm_training/train_lora.py --train_file llm_training/train.jsonl --output_dir llm_training/mistral7b-speech-lora ...`  
   - Restart the server; it loads the adapter.  
   - Use the app at http://localhost:8000; evaluations now go through your fine-tuned model.

**Result:** A model trained only on **your** feedback. You can repeat export → train as you add more corrected evaluations.

---

## Minimal “fastest” path (what to build)

1. **API-based evaluation in the app**  
   - One evaluation path that calls OpenAI or Claude with rubric + transcript, parses response to `sections`, and displays like Fine-tuned.  
   - Store `transcript` and final `evaluation_data.sections` (after your edits) on save.

2. **Export from Supabase**  
   - Script or Super Admin action: export evaluations (with transcript + evaluation_data.sections + rubric) to `exported.json` in the format expected by `export_to_jsonl.js` (see `sample_exported.json`).  
   - Apply consent/anonymization as required.

3. **Use existing tooling**  
   - `export_to_jsonl.js` → `train.jsonl`  
   - `train_lora.py` → adapter  
   - Current app + server for Fine-tuned model

No demo model on the server; “working” comes from the API LLM, and “trainable” comes from your corrected data and the same LoRA pipeline.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Add API-based evaluation (OpenAI/Claude) in the app so you can evaluate videos (with transcript) and get scores immediately. |
| 2 | Correct and save in SpeechGradebook; transcript and corrected sections are stored. |
| 3 | Build “Export for training” from Supabase → `exported.json` (transcript + rubric + evaluation_data.sections). |
| 4 | Run `export_to_jsonl.js` → `train_lora.py` as in STEPS_TO_REAL_EVALUATIONS.md. |
| 5 | After 30–100+ corrected evals, train; then switch to your Fine-tuned server for future evaluations. |

This gives you **working evaluations quickly** (API) and a **trainable model** from your own feedback, without needing a pre-existing large dataset.

---

## If API evaluation is reinstated: your workflow

**Yes.** If the evaluation flow again lets you choose an API provider (Gemini, OpenAI, or Claude):

1. **Upload existing videos** – You can run evaluations with that provider (e.g. Claude: transcribe → evaluate; Gemini: full video analysis). The app already supports video upload and, for Claude, stores the **transcript** when you save.
2. **Correct the AI-generated feedback** – You edit scores and comments in the app; corrections are stored in `evaluation_data.corrections` and the saved `evaluation_data.sections` reflect your final scores.
3. **After 30–100 speeches** – Export those evaluations (transcript + rubric + corrected sections) from Supabase, convert to JSONL, and run LoRA training. You get a **viable fine-tuned model** (adapter) that you then serve and use in the app instead of (or in addition to) the API.

**“Continues to learn as users upload speeches”** – The system improves **iteratively**, not in real time:

- There is **no** built-in “online learning” where each new evaluation updates the model automatically.
- **Continues to learn** means: as more users (or you) upload speeches and correct evaluations, you **periodically** (e.g. every 50–100 new corrected evals) **export** from Supabase → **retrain** (run `train_lora.py` again, optionally with the previous adapter as a starting point) → **redeploy** the new adapter. Each retrain cycle produces an updated model that has seen more of your corrected data.
- So the model keeps improving as long as you keep collecting corrected evaluations and rerunning the export → train → deploy pipeline on a schedule (e.g. monthly or when you hit a target number of new corrections).

---

## Automating export (and optionally the full retrain)

Yes. You can automate exporting evaluations from Supabase so the model can be updated regularly.

### Export script: `export_from_supabase.js`

A Node.js script in `llm_training/` does the export (no extra npm install; uses built-in `fetch`).

**What it does:**

1. Queries Supabase for evaluations with `transcript` not null and `evaluation_data` containing `sections`.
2. Optionally (with `--consent`) keeps only evaluations where the student has LLM training consent (`consent_forms.consent_type = 'llm_training'`, `consent_given = true`).
3. Maps each row to the shape expected by `export_to_jsonl.js`: `transcript`, `rubric` (name from `evaluation_data.rubricUsed` or `rubric_id`), `scores` = `evaluation_data.sections`, plus `source_evaluation_id` and `student_hash` for splits.
4. Writes to `exported.json` (or `--output path.json`).

**Usage:**

```bash
cd SpeechGradebook/llm_training
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
node export_from_supabase.js
# Optional: node export_from_supabase.js --consent
# Optional: node export_from_supabase.js --output /path/to/exported.json
```

Then run `node export_to_jsonl.js exported.json > train.jsonl` (or `--split 0.9`) and train as usual. Use the **service role key** so the script can read all evaluations; keep it in secrets (e.g. GitHub Secrets, env vars) and never commit it.

**Consent type used by the app:** The app uses **`data_collection`** for student consent in `consent_forms` (consent links, department export). There is no student-facing **`llm_training`** consent in the app; instructors have `user_profiles.llm_training_consent_given` separately. The export script’s `--consent` flag uses **`data_collection`** by default so it matches the app; you can pass `--consent=llm_training` if you add that consent type later.

**First batch (no consent filter):** For the first batch of training you can **omit `--consent`**. Then every evaluation that has a transcript and sections is exported, regardless of consent. Run: `node export_from_supabase.js` (no `--consent`). That gives you all eligible evaluations for initial training.

**Alternative: one student “Initial Training”:** You could create one student (e.g. “Initial Training”), attach evaluations to that student/course, and sign off consent for that student so `--consent` includes them. That’s more setup (reassigning evaluations, creating consent) and doesn’t simplify the first batch; the simpler path is to run without `--consent` for the first batch, then use `--consent` when you want to restrict to consented students only.

### How to run it on a schedule

| Option | How | Best for |
|--------|-----|-----------|
| **Cron (macOS/Linux)** | `0 2 * * 0` run script weekly (e.g. Sunday 2am). Script writes `exported.json` under `llm_training/`. | Your own machine or a server you control. |
| **GitHub Actions** | Scheduled workflow (e.g. `schedule: cron('0 2 * * 0')`) that checks out repo, runs export script with `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (secrets), writes `exported.json`, and either commits it or uploads as an artifact. | Repo in GitHub; no server to maintain. |
| **Supabase Edge Function + pg_cron or external cron** | Edge Function (or a small HTTP-triggered job) that queries Supabase, builds the export, and writes to Storage or returns the file. An external cron (e.g. cron-job.org) or Supabase pg_cron can call it on a schedule. | Keeping everything inside Supabase. |
| **Render / Vercel / Cloud Scheduler** | Scheduled job that runs the same export script (Node or Python) with env vars for Supabase; output can be written to a volume or pushed to storage. | You already use one of these for the app. |

Important: store **Supabase URL** and **service role key** in secrets (e.g. GitHub Secrets, env vars) and never commit them.

### Automating the full pipeline (export → train → updated model)

- **Export only (automated)** – Run the export script on a schedule so `exported.json` (or `train.jsonl`) is always up to date. You then run `train_lora.py` and deploy manually when you want a new model.
- **Export + train (automated)** – After the scheduled export, run `node export_to_jsonl.js exported.json > train.jsonl` and then `python train_lora.py ...`. Training needs **GPU** (or a lot of CPU time). Options:
  - **GitHub Actions** with a GPU runner (e.g. a larger runner or a self-hosted GPU runner) – possible but more setup.
  - **Cloud job** (e.g. Modal, RunPod, or a VM with a GPU) that is triggered by the same schedule or by “export complete” (e.g. artifact uploaded); the job downloads the export, runs training, and uploads the new adapter.
  - **Manual train** – Keep export automated; you run training locally or on a GPU machine when you have enough new data (e.g. every 50–100 new corrected evals).

So: **yes, you can automate the export** so the model can be updated regularly; you can also automate the full export → train → deploy cycle if you have a scheduled GPU job or accept manual training steps.

---

## Video content evaluation (body movement, eye contact, slides, etc.)

**Initial evaluations (Phase A)**  
If you want evaluations that consider **video** (body movement, eye contact, presentation slides, etc.), use **Gemini** as your evaluation provider. In the app, Gemini is the API that receives and analyzes the **full video**. Claude uses audio only; GPT-4o uses a single video frame. So for “transcript + video” feedback during data collection, **Gemini is the right choice**. When you use Gemini, the app now also captures **video_notes** (a paragraph of visual-only observations) and stores them in `evaluation_data.video_notes` so they can be used for training.

**Trained model (Phase B) — video-aware pipeline (implemented)**  
The fine-tuned Mistral model can now evaluate **both** transcript and video-style criteria when **video notes** are provided:

1. **At inference:** When you use the **Fine-tuned** provider with a **video** file and have a **Gemini API key** set in Settings, the app calls Gemini to get a short “video notes” paragraph (body movement, eye contact, gestures, slides, etc.), then sends **transcript + video_notes** to your Fine-tuned server. The server builds the prompt as `Transcript: … Video notes: …` + Rubric and runs the model.
2. **Training data:** Export from Supabase includes `video_notes` when present. `export_to_jsonl.js` appends `Video notes: …` to the user prompt for those examples. After training on corrected Gemini (or Fine-tuned + video) evaluations that include video_notes, the model learns to use visual delivery in its scores and feedback.

**Summary:** Use **Gemini** for initial video evaluations (and correct/save); video_notes are stored automatically. For **Fine-tuned** with video, set a Gemini API key so the app can fetch video notes and send them to your model. Export → train as usual; the pipeline includes video_notes in training when available.
