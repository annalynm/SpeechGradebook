# Using Comparison Pairs and Instructor Corrections to Train the Model

Yes. You can use **AI vs instructor** correction pairs and **same-student comparison pairs** (e.g. Persuasive 1 vs Persuasive 2) so the model learns from instructor feedback and from how improvement looks across multiple speeches with the same rubric.

---

## 1. What the app stores (and exports)

- **Final scores and feedback**  
  When an instructor saves an evaluation (including after editing), we store the **final** rubric scores, feedback, and timeline markers. Exports use this final state, so the model learns from **instructor-approved** outcomes.

- **Original AI output (for correction pairs)**  
  On **first save**, the app stores the **initial** AI analysis in `evaluation_data.model_output_original` (sections + timeline_markers). If the instructor then edits and saves again, we keep that original. So each evaluation can have both:
  - **scores_original** = what the AI first returned  
  - **scores_final** = what the instructor approved (possibly after edits)  
  That gives you **AI vs instructor** pairs so the model can learn to correct itself from instructor feedback.

- **Instructor corrections log**  
  Each evaluation can store a `corrections` log and an `edited` flag so you know which evals were refined by an instructor.

- **Comparison pairs (same student, two speeches)**  
  For the same student and course, multiple speeches (e.g. Persuasive 1 and Persuasive 2) with the same or compatible rubric form natural pairs: (video_1, scores_1) and (video_2, scores_2). The **delta** between them encodes what improvement (or change) looks like.

- **Multiple assessments with the same rubric**  
  When many students (or the same student over time) are assessed with the **same speech type and same rubric**, the single-eval export already includes all of them. The model sees many (video, rubric, scores) examples for that rubric and learns how you apply it. No extra pairing is required for that. The **comparison pairs** and **correction pairs** exports add explicit pair structure when you want the model to learn from deltas (improvement) or from instructor overrides.

---

## 2. Two kinds of "pair" exports

### A. AI vs instructor (correction pairs)

- **Idea:** Treat the **initial AI analysis** and the **corrected instructor version** as a pair. The model learns: "when I said X, the instructor changed it to Y" and improves over time.
- **How it works:**  
  - When you run an evaluation, the app captures the AI's first output. When you **save** (even without editing), we store that as `model_output_original`.  
  - If you **edit** scores or markers and save again, we keep the same `model_output_original` and update the final sections/markers.  
  - **Export:** Use **Export correction pairs (download JSONL)** in Settings → Admin or Platform Analytics → LLM Export. That builds one line per evaluation that has both `model_output_original` and `video_url` (with consent where applicable).
- **Format (train_qwen_correction_pairs.jsonl):**
  ```json
  {
    "video_path": "https://.../eval.mp4",
    "rubric": { "name": "...", "categories": [...] },
    "scores_original": { "Content": {...}, "Delivery": {...} },
    "scores_final": { "Content": {...}, "Delivery": {...} },
    "evaluation_id": "uuid"
  }
  ```
- **Training use:** Target = `scores_final`. You can train the model so that, given (video, rubric), it predicts the **instructor-approved** scores. Optionally use `scores_original` as auxiliary input or for a "correction" loss (predict the delta from original to final).

### B. Same student, two speeches (comparison pairs)

- **Idea:** You have multiple speeches of the **same type** with the **same rubric** (e.g. Persuasive 1 and Persuasive 2). Comparing their assessments helps the model learn consistency and what "improvement" looks like.
- **How it works:**  
  - **Export:** Use **Export comparison pairs (download JSONL)**. That finds, per student per course, evaluations with video, orders by date, and pairs them (1st vs 2nd, 2nd vs 3rd, etc.).
- **Format (train_qwen_pairs.jsonl):**
  ```json
  {
    "video_path_1": "https://.../eval1.mp4",
    "video_path_2": "https://.../eval2.mp4",
    "rubric": { "name": "...", "categories": [...] },
    "scores_1": { "Content": {...}, "Delivery": {...} },
    "scores_2": { "Content": {...}, "Delivery": {...} },
    "evaluation_id_1": "uuid",
    "evaluation_id_2": "uuid"
  }
  ```
- **Training use:** Extend your script to accept this format. For each line, you can train on (video_1, rubric) → scores_1 and (video_2, rubric) → scores_2, or on (video_1, video_2, rubric) → (scores_1, scores_2) / delta so the model learns consistency and improvement patterns.

---

## 3. Multiple assessments of the same speech type / same rubric

- **Your situation:** Multiple speech videos of the same type, same rubric.
- **Already in place:** The **single-eval** export (used for "Train SpeechGradebook Text + Video Model (Qwen) on ISAAC") includes **every** consented evaluation with video. So all assessments that use the same rubric already appear as many (video, rubric, scores) examples. The model is trained on that rubric from many speeches; no extra "comparison" step is required for that.
- **Extra signal from pairs:**  
  - **Correction pairs** add the "AI vs instructor" signal so the model learns from your edits.  
  - **Comparison pairs** add explicit (speech 1, speech 2) pairs so the model can learn improvement and consistency across consecutive speeches (e.g. Persuasive 1 vs 2).

So: **same rubric, many assessments** = already used in single-eval export. **Same student, two speeches** = use comparison pairs. **AI output vs your edits** = use correction pairs.

---

## 4. Using this in your training pipeline

- **Single-video training (current)**  
  Keep using `train_qwen.jsonl` with one (video_path, rubric, scores) per line. Scores and markers already reflect instructor corrections.

- **Correction pairs (AI vs instructor)**  
  Use `train_qwen_correction_pairs.jsonl`. Train so that given (video, rubric), the model predicts **scores_final**. Optionally use **scores_original** to emphasize learning from instructor overrides (e.g. loss that rewards matching the delta or the final more when original ≠ final).

- **Comparison pairs (two speeches, same student)**  
  Use `train_qwen_pairs.jsonl` when your script supports it: (video_1, video_2, rubric) → (scores_1, scores_2) or delta, so the model learns improvement and consistency.

- **Instructor-edited examples**  
  You can still **weight** or **filter** by `edited === true` (or presence of `corrections`) in any export so the model sees more instructor-refined examples.

---

## 5. Summary

| Data type                | What it teaches the model                          | Export / use                                                |
|--------------------------|----------------------------------------------------|-------------------------------------------------------------|
| Final scores + markers   | Instructor-approved rubric and timeline behavior  | Single-eval export (`train_qwen.jsonl`)                    |
| AI vs instructor         | Learn from instructor feedback / overrides        | **Export correction pairs** → `train_qwen_correction_pairs.jsonl` |
| Same student, 2 speeches | Improvement and consistency (e.g. Persuasive 1 vs 2) | **Export comparison pairs** → `train_qwen_pairs.jsonl`     |
| Many assessments, same rubric | How you apply that rubric across speeches      | Already in single-eval export; no extra step                |

Your logic is sound: treating **initial AI analysis vs corrected instructor version** as comparison pairs lets the model improve from instructor feedback; and **comparing assessments of multiple speeches with the same rubric** (via single evals + comparison pairs) trains the model more effectively. The app now stores the original AI output on first save and offers both correction-pair and comparison-pair exports.
