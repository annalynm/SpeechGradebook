# Recommended setup: SpeechGradebook Text + Video Model (Qwen via Modal) for evaluations

This setup uses **SpeechGradebook Text + Video Model (Qwen)** deployed on **Modal** (pay-per-use GPU) as the default evaluation provider. Users get full video analysis (content + delivery, eye contact, gestures, slides) with no local GPU required.

---

## 1. Evaluations (users)

- **Default:** The app uses **SpeechGradebook Text + Video Model (Qwen)** for speech/video evaluations.
- **Deployment:** Qwen runs on **Modal** (serverless GPU). Pay only for GPU seconds used (~$0.01–0.03 per evaluation).
- **Setup:** 
  1. Deploy Qwen to Modal: `modal deploy llm_training/qwen_modal.py` (see `llm_training/QWEN_MODAL_SETUP.md`)
  2. Set `QWEN_API_URL` on Render to your Modal URL (e.g. `https://yourname--qwen-speechgradebook.modal.run`)
  3. Users select "SpeechGradebook Text + Video Model (Qwen)" in the evaluation provider dropdown (default)
- **Result:** Instructors and students get comprehensive video analysis without any local setup or API keys.
- **Alternative providers:** Gemini, OpenAI GPT-4o, or Claude can be used as fallbacks (set API keys in Settings → General → API Keys).

---

## 2. Export data for LLM training

- **Who:** Super Admin only.
- **Where:** **Analytics → Evaluations** (or the **LLM Export** tab). Use **Download for LLM training** to get consented evaluations as `exported.json`.
- **What it does:** Downloads evaluations that have student consent and instructor LLM consent in the format needed for fine-tuning. You can use this with the training scripts in `llm_training/` (e.g. `export_to_jsonl.js`, then `train_lora.py` or the Qwen training pipeline).
- **No GPU required for export:** Export works without any GPU infrastructure. You're just downloading data from the app.

---

## 3. Train the LLM (when you're ready)

- **Where:** On a cloud GPU (RunPod, Lambda Labs, Vast.ai, etc.), or locally if you have a suitable GPU.
- **Steps:**  
  1. Export data (step 2 above).  
  2. Convert to training format (e.g. `node export_to_jsonl.js exported.json > train.jsonl`).  
  3. Run training (e.g. `train_lora.py` for Mistral, or the Qwen training scripts in `llm_training/`).  
- **Docs:** For a single place that covers consent, export flow, data formats, scripts, and environment for **both** Mistral and Qwen, see **`llm_training/TRAINING_REQUIREMENTS.md`**. See also `llm_training/README.md`, `llm_training/STEPS_TO_REAL_EVALUATIONS.md`, and `llm_training/DUAL_MODEL_TRAINING.md` for your chosen model and GPU provider.

---

## 4. Alternative evaluation providers (optional)

- **Google Gemini:** Free tier available. Good for testing or as a fallback. Set API key in Settings → General → API Keys.
- **OpenAI GPT-4o:** Paid API. Video analysis (single frame). Set API key in Settings.
- **Anthropic Claude:** Paid API. Audio-only (transcribes then evaluates). Set API key in Settings.
- **SpeechGradebook Text Model (Mistral):** Your own fine-tuned model. Requires training and hosting separately.

---

## Summary

| Goal | What to do |
|------|------------|
| **Users evaluate speeches** | Use **SpeechGradebook Text + Video Model (Qwen)** (default via Modal). Deploy to Modal and set `QWEN_API_URL` on Render. |
| **Export data for training** | Super Admin → **Download for LLM training** (Analytics / LLM Export). |
| **Train the LLM** | Use exported data with scripts in `llm_training/` on a cloud GPU (RunPod, Lambda, etc.) or local GPU. |
| **Use alternative providers** | Optional; set API keys in Settings → General → API Keys for Gemini, OpenAI, or Claude. |
