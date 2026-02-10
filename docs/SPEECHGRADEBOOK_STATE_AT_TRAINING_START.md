# SpeechGradebook State at Training Start

This document describes the **current version and configuration of SpeechGradebook** at the time model training was begun. Use it as a reference for how the app was set up, what data shapes were in use, and how evaluations and timeline markers worked.

**Document date:** February 2025  
**App version (UI):** v3.0 (Supabase Edition)

---

## 1. High-level architecture

- **Frontend:** Single-page app in `index.html` (static HTML/JS/CSS). Served by a Python backend.
- **Backend:** FastAPI in `app.py` (uvicorn). Serves static files and `/api/*` routes (health, evaluate, compress_video, etc.).
- **Data:** Supabase for auth, courses, students, rubrics, and evaluations. Config injected via `/config.js` from env (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `QWEN_API_URL`).
- **Deployment:** Render (Docker). Main service runs the FastAPI app; optional separate Qwen service or tunnel (e.g. Cloudflare, Render, ISAAC) for video evaluation.

---

## 2. Configuration

### 2.1 Environment (see `.env.example`)

| Variable | Purpose |
|--------|----------|
| `SUPABASE_URL` | Supabase project URL (required for auth/data). |
| `SUPABASE_ANON_KEY` | Supabase anon key (required). |
| `ALLOWED_ORIGINS` | Optional CORS origins. |
| `QWEN_API_URL` | Optional. Base URL of Qwen video-evaluation service (e.g. `http://localhost:8001` or Render/Cloudflare URL). |
| `SLACK_SIGNUP_WEBHOOK_URL` | Optional. Notify Super Admin on new signup requests. |
| `RENDER_LLM_EXPORT_SECRET` | Optional. Secret for “Submit Mistral/Qwen training to ISAAC” in Platform Analytics → LLM Export. |
| `ISAAC_USER`, `ISAAC_HOST`, `ISAAC_REMOTE_DIR`, `ISAAC_SSH_PRIVATE_KEY` | Optional. Used when submitting training jobs to ISAAC from the app. |

### 2.2 Frontend config

- **Config source:** `config.js` is overridden by the dynamic `/config.js` endpoint when using the Python server, which injects `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `QWEN_API_URL` from the environment.
- **Qwen URL in UI:** Users can also set “Qwen Service URL” in Settings → General (stored in `localStorage` as `qwen_api_url`). The app uses `localStorage.getItem('qwen_api_url') || window.QWEN_API_URL` for Qwen requests.

---

## 3. Evaluation flow

### 3.1 Evaluation providers (step 3: Evaluate)

- **SpeechGradebook Text + Video Model (Qwen)** – Optional. Calls external Qwen service at `baseUrl + '/evaluate_video'` with video file + rubric JSON. Returns `sections`, `overallComments`, `transcript`, `timeline_markers`.
- **Demo (mock scores)** – No external API. Generates fake sections and timeline markers for testing.
- **Anthropic Claude** – Sends audio (extracted from video if needed) to Claude API; no timeline markers from Claude in the same shape as Qwen.

### 3.2 Qwen service (`llm_training/qwen_serve.py`)

- **Endpoint:** `POST /evaluate_video` with `file` (video) and `rubric` (JSON string).
- **Prompt:** Built from `EVALUATE_VIDEO_PROMPT` plus rubric structure and a behavior block from `qwen_behavior_references.json` (see below).
- **Expected model output:** A single JSON object with:
  - `sections`: category names → `{ score, maxScore, subcategories: [{ name, points, maxPoints }] }`.
  - `timeline_markers`: array of `{ seconds, label, observation, severity, category }`.
- **Normalization:** The service maps model output to the UI shape: `timestamp` (e.g. `"1:23"`), `seconds`, `category`, `issue` (from `label`), `note` (from `observation`), `severity`. It does **not** set a `behavior` field; the frontend sets that when `issue` matches a predefined behavior label.

---

## 4. Timeline markers (current behavior)

### 4.1 Marker object (in `evaluation_data.timeline_markers` and UI)

Each marker has (or can have):

| Field | Type | Notes |
|-------|------|------|
| `id` | string | Unique (e.g. `m_<timestamp>_<random>`). Added by frontend if missing (`ensureMarkerIds`). |
| `timestamp` | string | e.g. `"1:23"`. |
| `seconds` | number | Approximate time in video. |
| `category` | string | e.g. `"Content"`, `"Delivery"`. |
| `issue` | string | Short label (e.g. “Swaying”, “Hands in pockets”). |
| `note` | string | Longer observation. |
| `severity` | string | `"positive"` \| `"minor"` \| `"moderate"` \| `"major"`. |
| `behavior` | string | Optional. Predefined behavior label when this marker matches one of the example-video behaviors; used for tagging and grouping. |

### 4.2 Predefined behavior labels (example videos)

Source of truth: `llm_training/qwen_behavior_references.json`.  
In the UI, the same list is hardcoded as `BEHAVIOR_LABELS` in `index.html`:

1. Hands in pockets  
2. Hands clasped (in front)  
3. Hands clasped behind  
4. Swaying  
5. Tapping hands  
6. Vocalized pause  
7. Purpose statement  

- **Edit Markers:** Instructors can choose one of these in a “Behavior (from examples)” dropdown or “Other (Custom)” and type a custom issue.
- **Auto-tagging:** If the AI returns a marker whose `issue` exactly matches one of these labels, the frontend sets `marker.behavior = marker.issue` (`normalizeMarkerBehaviors`) so the behavior pill appears without instructor action.
- **Recurrence:** Markers are grouped by a recurrence key (`behavior` or trimmed `issue`, case-insensitive). The results view shows “(N times)” for recurring issues; the Edit Markers modal shows “In this video: Swaying (2), Vocalized pause (1)” and a “Duplicate (new time)” (+) button to add another occurrence.

---

## 5. Stored evaluation data

### 5.1 Supabase `evaluations` table (relevant columns)

- `id`, `instructor_id`, `course_id`, `student_id`, `rubric_id`, `created_at`
- `evaluation_data` (JSONB) – see below
- `video_url`, `audio_url`, `transcript`, `ai_provider`, `total_score`, `letter_grade`, `status`

### 5.2 `evaluation_data` payload (saved on “Save Evaluation”)

| Key | Description |
|-----|-------------|
| `sections` | Category scores and subcategories (from AI or demo). |
| `studentName`, `speechDate`, `assignmentType`, `speechTime`, `rubricUsed` | Metadata. |
| `totalScore`, `maxScore`, `percentage`, `letterGrade` | Computed grades. |
| `gradeScale` | Letter-grade bands (with min/max points if enriched). |
| `overallComments` | Overall feedback text. |
| `timeline_markers` | Array of marker objects (with `id`, `behavior`, etc., if set). |
| `video_notes` | Optional instructor notes. |
| `corrections` | Array of correction-log entries (field, timestamp, ai_value, instructor_value, etc.) for training. |
| `edited` | Boolean: true if any corrections were made. |
| `model_output_original` | **Set on first save only.** Snapshot of AI output: `{ sections, timeline_markers }` before any instructor edits. Used for training (AI vs instructor comparison). |
| `rubric_structure` | Optional snapshot: `{ categories, totalPoints }` at evaluation time for training/export. |

---

## 6. Training-related behavior

- **Correction log:** Every instructor edit (scores, comments, markers add/edit/delete, etc.) is appended to `correctionLog` in memory and saved in `evaluation_data.corrections`.
- **Model output original:** Captured when the evaluation result is first received (before the user edits) and stored once in `evaluation_data.model_output_original` on first save.
- **Export (Platform Analytics → LLM Export):** Qwen manifest export, comparison pairs, and correction pairs (JSONL) use evaluations that have `model_output_original` and (where applicable) `video_url` to build training data.

---

## 7. Files to reference for this snapshot

| Area | File(s) |
|------|--------|
| Config | `config.js`, `.env.example` |
| Backend | `app.py`, `render.yaml` |
| Qwen service | `llm_training/qwen_serve.py` |
| Behavior definitions | `llm_training/qwen_behavior_references.json` |
| Frontend constants (behaviors, markers) | `index.html` (BEHAVIOR_LABELS, timeline marker logic, evaluation_data payload) |
| Deploy | `RENDER_DEPLOY.md`, `render.yaml` |

---

## 8. Summary

- **Version:** SpeechGradebook v3.0 (Supabase Edition).
- **Evaluation:** Optional Qwen video model (external service), Demo mode, and Claude for audio.
- **Timeline markers:** Have `id`, `issue`, `note`, `severity`, `category`, `timestamp`, `seconds`, and optional `behavior`; recurring markers are grouped and summarized; instructors can tag with predefined behaviors or “Other (Custom)” and duplicate a marker to add another time.
- **Training readiness:** Evaluations store `model_output_original` and `corrections`; export and “Submit to ISAAC” use these for Qwen (and Mistral) training. This document reflects the app state at the start of that training process.
