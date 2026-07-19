# Karigar — single container: API + orchestrator + agents + static frontends.
# Deploy: Cloud Run with --min-instances=1 --no-cpu-throttling (background jobs
# must keep CPU after the webhook returns 200 — see README deployment section).
FROM python:3.12-slim

# ffmpeg: audio container safety net (WhatsApp OGG/Opus edge cases)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the rembg background-removal model at build time so the first
# photo doesn't pay a ~170MB cold download.
RUN python -c "from rembg import new_session; new_session('u2net')" || true

COPY app ./app
COPY web ./web
COPY web_v2 ./web_v2

ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
