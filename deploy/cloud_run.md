# Deploying Karigar to Google Cloud Run

One container, one URL. Supabase is external (DB + storage), OpenAI is external.

## One-time setup

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

## Deploy (from repo root)

```bash
gcloud run deploy karigar \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --no-cpu-throttling \
  --memory 1Gi \
  --set-env-vars OPENAI_API_KEY=...,SUPABASE_URL=...,SUPABASE_SERVICE_KEY=...,WHATSAPP_TOKEN=...,WHATSAPP_PHONE_NUMBER_ID=...,WHATSAPP_VERIFY_TOKEN=...
```

Why these flags (architecture-critical, not optional):

| Flag | Reason |
|---|---|
| `--no-cpu-throttling` | The async webhook pattern returns 200 immediately and runs the 10–12s agent chain in a background task. With default throttling, Cloud Run cuts CPU when the response is sent and the job freezes mid-pipeline. |
| `--min-instances 1` | No cold starts during a live judging session; keeps the in-process job queue and photo-batch debouncer alive. |
| `--max-instances 1` | The photo-batch debouncer and console outbox are in-process. Single instance is correct at prototype scale; the production path is Cloud Tasks + Redis (documented in README). |

## After deploy

1. Set the WhatsApp webhook in the Meta developer console:
   `https://<cloud-run-url>/webhook/whatsapp`, verify token = `WHATSAPP_VERIFY_TOKEN`.
2. (Optional) Twilio sandbox webhook: `https://<cloud-run-url>/webhook/twilio`.
3. Judges: Demo Console at `https://<cloud-run-url>/`, shop at `/shop`.
