# SpeechGradebook model integration

The app can use your trained **SpeechGradebook Text Model (Mistral)** adapter and the **SpeechGradebook Text + Video Model (Qwen)** as AI providers alongside Demo, OpenAI, Gemini, and Claude.

## App changes

- **AI Provider dropdown:** **SpeechGradebook Text Model (Mistral)** (trained Mistral 7B) and **SpeechGradebook Text + Video Model (Qwen)** (evaluates video directly; analyzes both video and text).
- **URL field:** When SpeechGradebook Text Model (Mistral) is selected, the URL field is the evaluation server (e.g. `http://localhost:8000`). The value is stored in `localStorage` as `finetuned_api_url` when you run an evaluation.
- **Evaluation flow:** When you run an evaluation with SpeechGradebook Text Model (Mistral) selected, the app:
  1. Sends the uploaded file and selected rubric to `POST {apiUrl}/evaluate_with_file` (multipart: `file`, `rubric` JSON).
  2. The server transcribes with Whisper and runs the fine-tuned model; returns `{ sections, overallComments, transcript }`.
  3. The app maps the returned `sections` to the same result shape as other providers (score, maxScore, feedback, subcategories with grade/gradeLabel from rubric) and displays results as usual.

## Server requirements

- **Endpoints:** `GET /health`, `POST /evaluate` (JSON: transcript + rubric), `POST /evaluate_with_file` (multipart: file + rubric).
- **File upload:** `POST /evaluate_with_file` requires Whisper on the server (`pip install openai-whisper`). If Whisper is not installed, the server returns 501 and the app shows an error.
- **CORS:** The server enables CORS for all origins so the browser can call it from the app.

## Running the server

```bash
cd SpeechGradebook/llm_training
pip install -r requirements-train.txt
pip install openai-whisper   # for file upload from the app
python serve_model.py --model_path ./mistral7b-speech-lora --port 8000
```

Then in the app: select **SpeechGradebook Text Model (Mistral)**, enter `http://localhost:8000`, and run an evaluation.

## Transcript-only (no file)

If you have a transcript already, you can call the API directly:

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"transcript": "...", "rubric_name": "Informative Speech", "rubric": { ... }}'
```

Response: `{ "sections": { ... }, "overallComments": "", "transcript": "" }`. The app’s **SpeechGradebook Text Model (Mistral)** provider uses the file endpoint; for transcript-only you’d need a separate flow or a small script.
