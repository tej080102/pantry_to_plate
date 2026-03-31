# Backend Environment Setup

This backend already uses a real [`backend/.env`](/Users/somyapathak/Desktop/Masters/spring%202026/BDA/pantry_to_plate/backend/.env) file for connectivity. That file may contain live local or Cloud SQL connection settings and should not be deleted or casually rewritten.

## Local development

For local development, the backend can run with SQLite:

```env
ENVIRONMENT=local
PROJECT_NAME=Pantry to Plate
DATABASE_URL=sqlite:///./pantry_to_plate.db
LOG_LEVEL=INFO
```

Other variables can stay unset until the related platform features are implemented.

## Cloud SQL / GCP deployment shape

For Cloud Run + Cloud SQL, the same `backend/.env` pattern can be used locally for testing, while production values should be injected by the deployment platform or secret manager.

Typical Cloud SQL connection shape:

```env
ENVIRONMENT=production
PROJECT_NAME=Pantry to Plate
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@127.0.0.1:5432/pantry_to_plate
GCP_PROJECT_ID=your-gcp-project
GCP_REGION=us-central1
GCS_UPLOAD_BUCKET=your-project-user-uploads
GCS_RAW_BUCKET=your-project-etl-raw
GCS_CLEAN_BUCKET=your-project-etl-clean
VISION_PROVIDER=gemini
VISION_MODEL=gemini-vision-placeholder
RECIPE_MODEL=recipe-model-placeholder
LOG_LEVEL=INFO
```

## Expected environment variables

- `ENVIRONMENT`: runtime name such as `local`, `staging`, or `production`
- `PROJECT_NAME`: human-readable service name
- `DATABASE_URL`: SQLite for local work or PostgreSQL for Cloud SQL
- `GCP_PROJECT_ID`: GCP project identifier
- `GCP_REGION`: deployment region
- `GCS_UPLOAD_BUCKET`: user upload bucket
- `GCS_RAW_BUCKET`: raw ETL artifact bucket
- `GCS_CLEAN_BUCKET`: clean ETL artifact bucket
- `VISION_PROVIDER`: computer-vision provider name
- `VISION_MODEL`: ingredient detection model identifier
- `RECIPE_MODEL`: recipe generation model identifier
- `LOG_LEVEL`: application logging level

## Current repository state

- The backend currently reads `DATABASE_URL` from `backend/.env`
- SQLite local development is supported now
- Cloud SQL connection strings are supported by SQLAlchemy configuration
- Most GCP-related variables are documented here but not yet wired into app config

## Safe usage note

Do not commit real secrets. If Cloud SQL credentials or API keys are needed, keep them in your real `backend/.env` for local work and move them to Secret Manager or deployment configuration for production.
