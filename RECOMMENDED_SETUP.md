# Recommended setup: Gemini for evaluations, export & train when ready

This is the simplest path: **users evaluate speeches with Google Gemini**, and you **export data and train the LLM** when you’re ready. No need to run or fix the Qwen connection for normal use.

---

## 1. Evaluations (users)

- **Default:** The app uses **Google Gemini** for speech/video evaluations.
- **What you need:** A Gemini API key. Set it in **Settings → General → API Keys** (or have an admin set an institution key in **Settings → Admin**).
- **Get a key:** [Google AI Studio](https://aistudio.google.com/app/apikey) (free tier available).
- **Result:** Instructors and students can run evaluations without any Qwen or tunnel setup.

---

## 2. Export data for LLM training

- **Who:** Super Admin only.
- **Where:** **Analytics → Evaluations** (or the **LLM Export** tab). Use **Download for LLM training** to get consented evaluations as `exported.json`.
- **What it does:** Downloads evaluations that have student consent and instructor LLM consent in the format needed for fine-tuning. You can use this with the training scripts in `llm_training/` (e.g. `export_to_jsonl.js`, then `train_lora.py` or the Qwen training pipeline).
- **No Qwen required:** Export works without a live Qwen service. You’re just downloading data from the app.

---

## 3. Train the LLM (when you’re ready)

- **Where:** On ISAAC (your campus cluster), or on a cloud GPU (RunPod, Lambda, etc.), or locally if you have a suitable GPU.
- **Steps:**  
  1. Export data (step 2 above).  
  2. Convert to training format (e.g. `node export_to_jsonl.js exported.json > train.jsonl`).  
  3. Run training (e.g. `train_lora.py` for Mistral, or the Qwen training scripts in `llm_training/`).  
- **Docs:** For a single place that covers consent, export flow, data formats, scripts, and environment for **both** Mistral and Qwen, see **`llm_training/TRAINING_REQUIREMENTS.md`**. See also `llm_training/README.md`, `llm_training/STEPS_TO_REAL_EVALUATIONS.md`, and `llm_training/DUAL_MODEL_TRAINING.md` for your chosen model and cluster.

---

## 4. Qwen (optional)

- **Use:** Video analysis and rubric extraction via the “SpeechGradebook Text + Video Model (Qwen)” provider. Requires running the Qwen service (e.g. on ISAAC or a cloud GPU) and exposing it (e.g. Cloudflare tunnel).
- **When:** Only if you want to use Qwen for evaluations or rubric extraction. Most users can ignore this and use Gemini only.
- **Docs:** `llm_training/QWEN_NAMED_TUNNEL.md`, `llm_training/START_QWEN_FOR_RENDER.md`, etc. Revisit these if you later set up an always-on Qwen instance (e.g. RunPod or Lambda).

---

## Summary

| Goal | What to do |
|------|------------|
| **Users evaluate speeches** | Use **Google Gemini** (default). Set Gemini API key in Settings. |
| **Export data for training** | Super Admin → **Download for LLM training** (Analytics / LLM Export). |
| **Train the LLM** | Use exported data with scripts in `llm_training/` on ISAAC or a GPU host. |
| **Use Qwen for evaluations** | Optional; set up Qwen service + tunnel when you need it (see `llm_training/` docs). |
