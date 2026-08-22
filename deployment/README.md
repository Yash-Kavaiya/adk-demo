# Deploying BookForge

BookForge is a **long-running batch pipeline** (minutes to hours per channel).
That drives the deployment choice: prefer a *job* runtime over a request-driven
HTTP service.

## Prereqs

- GCP project with billing, `gcloud` authenticated
- APIs: `run`, `artifactregistry`, `secretmanager` (+ `aiplatform` if using Vertex AI)
- A Gemini credential: AI Studio `GOOGLE_API_KEY`, or Vertex AI
  (`GOOGLE_GENAI_USE_VERTEXAI=TRUE` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`)

## Option A — Cloud Run Job (recommended)

```bash
export PROJECT_ID=<your-project> REGION=us-central1
gcloud config set project $PROJECT_ID

# 1) Secret for the API key (never in the image or logs)
printf '%s' "$GOOGLE_API_KEY" | gcloud secrets create bookforge-google-api-key --data-file=-

# 2) Build & push
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/bookforge/bookforge:latest .

# 3) Create the job (generous timeout: whole channels take a while)
gcloud run jobs create bookforge \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/bookforge/bookforge:latest \
  --region $REGION --cpu 2 --memory 4Gi --task-timeout 4h --max-retries 1 \
  --set-secrets GOOGLE_API_KEY=bookforge-google-api-key:latest \
  --set-env-vars BOOKFORGE_WORKSPACE_ROOT=/data

# 4) Run a channel
gcloud run jobs execute bookforge --region $REGION \
  --update-env-vars CHANNEL_URL=https://www.youtube.com/@TargetChannel
```

The job entrypoint is `python -m bookforge.main`; pass the URL by overriding
args (`--args`) or make the container read `$CHANNEL_URL` via a wrapper script.
Mount a **GCS bucket as a volume** (Cloud Run volume mounts) at `/data` so the
workspace (manifest, chapters, `book/book.pdf`) survives the task.

Scale-to-zero is inherent: jobs bill only while executing.

## Option B — Vertex AI Agent Engine (managed agent runtime)

For interactive/managed use instead of batch:

```bash
adk deploy agent_engine --project=$PROJECT_ID --region=$REGION bookforge
```

Agent Engine manages sessions for you; trigger a run with a user message
containing the channel URL. Long channels still favor the job runtime.

## Option C — local / VM

```bash
pip install .
export GOOGLE_API_KEY=...
bookforge "https://www.youtube.com/@TargetChannel"   # or: python -m bookforge.main <url>
```

## Observability

- The CLI prints one line per agent event; Cloud Run captures stdout/stderr in
  Cloud Logging automatically.
- Each video's checkpoint lives in `data/<channel>/manifest.json` — inspect it
  to see per-video status (`verified / written / failed`) after any run.

## Security notes

- No credentials in the image; Secret Manager only.
- The container runs as a non-root user.
- Process only content you have rights to (own channel / licensed).
