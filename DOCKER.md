# Running SpeechGradebook with Docker

The image includes **ffmpeg** so the **video compression** feature (`/api/compress_video`) works: videos over 50 MB are compressed automatically when users upload.

## Build

```bash
docker build -t speechgradebook .
```

## Run

Set Supabase credentials (required for login and data):

```bash
docker run -p 8000:8000 \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_ANON_KEY=your-anon-key \
  speechgradebook
```

Then open **http://localhost:8000**.

### Optional environment variables

- **ALLOWED_ORIGINS** – CORS origins (default allows localhost).
- **MODEL_PATH** – Path to the fine-tuned Mistral adapter inside the container (default `./llm_training/mistral7b-speech-lora`). If the path exists at startup, `/api/evaluate` and `/api/evaluate_with_file` are enabled.
- **LOAD_IN_8BIT** – Set to `1` or `true` to load the model in 8-bit (less VRAM).
- **QWEN_API_URL** – URL of the Qwen service for video evaluation / rubric extraction (if running separately).

### Using a trained model

Either copy the adapter into the image (edit `Dockerfile`, uncomment the `COPY mistral7b-speech-lora` line and rebuild), or mount it at run time:

```bash
docker run -p 8000:8000 \
  -v /path/on/host/mistral7b-speech-lora:/app/llm_training/mistral7b-speech-lora:ro \
  -e SUPABASE_URL=... -e SUPABASE_ANON_KEY=... \
  speechgradebook
```

## Docker Compose (local)

Using a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
# Edit .env and set SUPABASE_URL and SUPABASE_ANON_KEY

docker compose up --build
```

Open **http://localhost:8000**. To use the SpeechGradebook model, uncomment the `volumes` section in `docker-compose.yml` and point it at your local adapter directory.

## Deploying with Docker (e.g. Render)

Render can use this Dockerfile: create a **Web Service**, connect the repo, set **Docker** as the environment, and add `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the dashboard. The start command is already in the Dockerfile (`uvicorn app:app ...`). Ensure the plan allows enough memory if you load the model.
