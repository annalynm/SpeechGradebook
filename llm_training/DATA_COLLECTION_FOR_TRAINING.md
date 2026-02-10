# Data to Collect and Preserve for Current and Future Training

This note summarizes what the app **already stores** for training and what you might **add or ensure** for current and future model work. A key goal: **collect data once** and be able to **retrain later** with a different model or on additional aspects without re-collecting. Nothing here is required for the existing pipeline; these are recommendations so you don’t miss signals you might want later.

---

## 1. What you already collect (and preserve)

| Data | Where | Use for training |
|------|--------|-------------------|
| **Video / audio** | `video_url` or `audio_url` (Supabase Storage) | Qwen (video/audio) and replay |
| **Transcript** | `evaluations.transcript` | Mistral (text), Qwen (multimodal), exports |
| **Final scores + feedback** | `evaluation_data.sections` (categories, subcategories, points, feedback) | All training; instructor-approved target |
| **Timeline markers** | `evaluation_data.timeline_markers` | Qwen behavior / timeline learning; instructor-corrected when edited |
| **Video notes** | `evaluation_data.video_notes` | Text-tier training (visual delivery) when no video in manifest |
| **Rubric at eval time** | `evaluation_data.rubric_structure` (categories, totalPoints), `rubricUsed` | Consistent input format; category alignment |
| **Grade scale (with point values)** | `evaluation_data.gradeScale` (label, percentage, range, **minPoints**, **maxPoints**, **pointRange** per letter) | Letter-grade cutoffs; point bounds per grade for training or reporting |
| **Original AI output** | `evaluation_data.model_output_original` (sections + timeline_markers) | Correction-pair export (AI vs instructor) |
| **Instructor corrections** | `evaluation_data.corrections`, `edited` | Strong labels; filter/weight by edited |
| **Assignment type** | `evaluation_data.assignmentType` | Filtering (e.g. “Persuasive 1”), pairing, analytics |
| **Speech duration** | `evaluation_data.speechTime` | Curriculum (short vs long), analytics |
| **Provider** | `evaluations.ai_provider` | Filtering, provider-specific analysis |
| **Course / student / instructor** | `course_id`, `student_id`, `instructor_id` | Consent, pairing (same student), per-instructor tuning |
| **Consent** | `consent_forms` | Export filtering (data_collection, llm_training) |
| **Export tracking** | `exported_for_llm_at` (if used) | Avoid re-export duplicates; audit |

You are already in good shape for:

- Single-eval training (video/audio + rubric + final scores).
- Comparison pairs (same student, two speeches).
- Correction pairs (AI vs instructor).
- Consistency and “improvement” across same-rubric assessments.

---

## 2. Optional additions (worth considering)

These are **not** required for current training but can help future work and reproducibility.

| Addition | Why | Effort |
|----------|-----|--------|
| **Grade scale in evaluation_data** | Done. The app saves `gradeScale` on first save and **enriches it with point values**: each letter gets `minPoints`, `maxPoints`, and `pointRange` (e.g. A = 50–45.5 for a 50-point rubric) derived from the rubric’s percentage range and total points. So each evaluation has both percentage and point cutoffs for letter grades. | Already implemented. |
| **Model / API version** | Knowing “this eval was from Qwen v1 adapter” vs “v2” or “Gemini 1.5” helps when you mix multiple model versions in one dataset (e.g. filter or weight by version). | Low: add optional `model_version` or `api_model_id` to evaluation (or inside `evaluation_data`) when calling the API. |
| **Stable assignment identifier** | If you have “Persuasive 1” vs “Persuasive 2” (or rubric + sequence), a small structured field (e.g. `assignment_key`: `"persuasive_1"`) makes pairing and filtering easier than parsing free-text `assignmentType`. | Low: derive from assignment type or add a dropdown that sets a canonical key. |
| **Language / locale** | If you ever support multiple languages (speech or rubric), storing language (e.g. `en`, `es`) per eval helps for language-specific models or filtering. | Only if you add i18n. |

---

## 3. What to avoid (or minimize)

- **PII beyond what you need**  
  You already store course/student/instructor IDs and consent. Avoid storing raw identifiers in free text (e.g. in comments) if you can; use IDs and let consent/audit handle access.

- **Storing every failed or abandoned run**  
  Failed runs can be useful for debugging or negative examples, but they add complexity and storage. Only add if you have a clear use (e.g. “model failed on this input” analysis).

- **Duplicating large blobs**  
  Keep media in Storage (URLs in DB); keep transcripts and scores in the evaluation record. Avoid storing the same transcript or audio in multiple places.

---

## 4. Quick checklist for “am I ready to train?”

- [ ] Evaluations saved **with video or audio** (for Qwen/video training) and/or **with transcript** (for Mistral/text).
- [ ] **Consent** in place where required; export uses consented evals only.
- [ ] **Rubric structure** present in exports (you have this via `rubric_structure`).
- [ ] For **correction pairs**: run evaluations, then **save** (so `model_output_original` is stored); optionally edit and save again so final = instructor version.
- [ ] For **comparison pairs**: at least two evaluations **per student per course** with video (and consent) so the export can form pairs.

If all of the above are true, you have what you need for current single-eval, comparison-pair, and correction-pair training. The optional fields in section 2 are for future flexibility and reproducibility, not for today’s pipeline.

---

## 5. Collect once, retrain later

You can **collect evaluation data once** and use it for **multiple future training runs** without re-collecting:

- **Same data, different model**  
  Exports (single-eval, comparison pairs, correction pairs) are model-agnostic. You can train a new Qwen adapter, switch to a different base model, or train a text-only model from the same exported JSONL. The stored fields (transcript, video_url, rubric_structure, sections, timeline_markers, video_notes, gradeScale with point values, model_output_original, corrections) give you everything needed to rebuild inputs and targets.

- **Same data, additional aspects**  
  If you later want to train on something new (e.g. instructor reasoning, or a new rubric dimension), you only need that new label or structure where applicable. The existing fields (media, transcript, rubric, scores, markers, corrections) remain the source of truth; you can add new export columns or new JSONL keys when you define the new task.

- **What to do now**  
  Keep saving evaluations with the usual workflow (video/audio when possible, transcript, rubric, correct and save so that `model_output_original` and final scores are stored). Ensure consent and export filters are set as you need. The app's stored snapshot (including gradeScale with point values) is designed so that one collection supports current training and future retraining or new objectives.
