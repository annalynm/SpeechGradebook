# SpeechGradebook: frontend + API (evaluate, compress_video, llm-export).
# Requires ffmpeg for /api/compress_video (video under 50 MB for Supabase storage).
# Build: docker build -t speechgradebook .
# Run:   docker run -p 8000:8000 -e SUPABASE_URL=... -e SUPABASE_ANON_KEY=... speechgradebook

FROM python:3.11-slim

# Install ffmpeg for video compression (compress_video endpoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (torch/transformers make the image large; required for /api/evaluate)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY config.js .
COPY index.html .
COPY landing.html .
COPY consent.html .
COPY privacy.html .
COPY terms.html .
COPY contact.html .
COPY help.html .
COPY accessibility.html .
COPY assets/ ./assets/
COPY llm_training/ ./llm_training/

# Optional: copy trained model at build time (or mount at run time)
# COPY mistral7b-speech-lora ./llm_training/mistral7b-speech-lora

EXPOSE 8000

ENV PORT=8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
