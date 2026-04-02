# Backend Environment Setup

This backend reads configuration from `backend/.env` for local work. Production values should be injected by Cloud Run and Secret Manager rather than committed.

## Local development

For local development with SQLite and the heuristic perception fallback:

```env
ENVIRONMENT=local
PROJECT_NAME=Pantry to Plate
DATABASE_URL=sqlite:///./pantry_to_plate.db
VISION_PROVIDER=local_heuristic
VISION_MODEL=gemini-2.5-flash
PERCEPTION_ALLOW_LOCAL_FALLBACK=true
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LOG_LEVEL=INFO
```

This setup keeps the backend runnable even without GCP credentials.

## Vertex AI Gemini configuration

For local testing against Vertex AI Gemini or for deployed Cloud Run runtime:

```env
ENVIRONMENT=production
PROJECT_NAME=Pantry to Plate
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@127.0.0.1:5432/pantry_to_plate
GCP_PROJECT_ID=your-gcp-project
GCP_REGION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
VISION_PROVIDER=gemini_vertex
VISION_MODEL=gemini-2.5-flash
PERCEPTION_ALLOW_LOCAL_FALLBACK=false
CORS_ALLOW_ORIGINS=https://your-frontend.web.app
GCS_UPLOAD_BUCKET=your-project-user-uploads
GCS_RAW_BUCKET=your-project-etl-raw
GCS_CLEAN_BUCKET=your-project-etl-clean
RECIPE_MODEL=recipe-model-placeholder
LOG_LEVEL=INFO
```

## Authentication for Vertex AI Gemini

### Local development

Use Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project your-gcp-project
```

The backend uses the `google-genai` SDK with Vertex AI enabled when:

- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `VISION_PROVIDER=gemini_vertex`

### Cloud Run

Use the Cloud Run service account instead of service account keys. The runtime service account should have access to Vertex AI and any other required GCP services.

Recommended permissions at minimum:

- Vertex AI user access for Gemini inference
- Cloud SQL access if using Cloud SQL
- Secret Manager access for injected secrets
- Storage access for any configured GCS buckets

## Expected environment variables

- `ENVIRONMENT`: runtime name such as `local`, `staging`, or `production`
- `PROJECT_NAME`: service display name
- `DATABASE_URL`: SQLite for local work or PostgreSQL for Cloud SQL
- `CORS_ALLOW_ORIGINS`: comma-separated allowed frontend origins
- `GCP_PROJECT_ID`: GCP project identifier
- `GCP_REGION`: deployment region, for example `us-central1`
- `GOOGLE_GENAI_USE_VERTEXAI`: whether to call Gemini through Vertex AI
- `VISION_PROVIDER`: `gemini_vertex` or `local_heuristic`
- `VISION_MODEL`: Gemini model name, for example `gemini-2.5-flash`
- `PERCEPTION_ALLOW_LOCAL_FALLBACK`: whether to fall back to the local detector if Gemini is unavailable
- `GCS_UPLOAD_BUCKET`: upload bucket name
- `GCS_RAW_BUCKET`: raw ETL artifact bucket name
- `GCS_CLEAN_BUCKET`: clean ETL artifact bucket name
- `RECIPE_MODEL`: future recipe-generation model identifier
- `LOG_LEVEL`: application logging level

## Current repository state

- `DATABASE_URL`, `VISION_PROVIDER`, `VISION_MODEL`, `PERCEPTION_ALLOW_LOCAL_FALLBACK`, and GCP project/region settings are now read by application config
- CORS origins are now configurable through environment variables
- Gemini on Vertex AI is the primary perception provider
- The local heuristic detector still exists as a dev/test fallback
- GCS bucket names are documented for future storage integration but are not yet fully wired into the app

## Safe usage note

Do not commit real secrets. Keep local credentials in your real `.env` only when needed, and use Secret Manager or Cloud Run environment injection for deployed environments.
