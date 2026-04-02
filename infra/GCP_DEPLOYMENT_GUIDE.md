# Pantry to Plate GCP Deployment Guide

This guide explains how to host the current project on Google Cloud Platform in a way that is realistic for this repository today.

Target deployment:

- frontend on Firebase Hosting
- backend on Cloud Run
- database on Cloud SQL for PostgreSQL
- image and ETL storage on Google Cloud Storage
- image perception with Gemini on Vertex AI
- secrets in Secret Manager

This guide is written for beginners and assumes:

- you have a Google account
- you can use a terminal
- you want a manual deployment first, not Terraform or CI/CD

## 1. Understand the current repo state first

Before deploying, you should know what is already implemented and what is not.

What works now:

- frontend React app
- backend FastAPI app
- pantry, ingredients, perception, and recipe catalog APIs
- Gemini on Vertex AI as the primary perception provider
- local fallback perception if Gemini is unavailable

What is not finished yet:

- `POST /recipes/generate`
- GCS-backed upload persistence
- CI/CD automation
- database migrations

Important warning for this branch:

- Do not initialize Cloud SQL with `backend/db/schema.sql`.
- That SQL file is behind the current ORM models.
- For this branch, the safest path is to let the backend create tables on first startup against an empty database.

## 2. Install the tools you need locally

Install these tools on your machine:

- Google Cloud CLI: `gcloud`
- Docker Desktop or Docker Engine
- Firebase CLI: `firebase`
- Python 3.12 or close to it
- Node.js and npm

Official references:

- Cloud SDK: https://cloud.google.com/sdk/docs/install
- Firebase CLI: https://firebase.google.com/docs/cli
- Docker: https://docs.docker.com/get-docker/

## 3. Create or choose a GCP project

1. Open the Google Cloud Console.
2. Create a new project just for this app.
3. Enable billing for that project.
4. Pick a single region and use it consistently.

Recommended region for this repo:

- `us-central1`

Set the project in your terminal:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region us-central1
```

## 4. Enable the required Google Cloud APIs

Run:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

Why these APIs matter:

- Cloud Run hosts the backend container
- Cloud SQL hosts PostgreSQL
- Artifact Registry stores the backend image
- Secret Manager stores secrets
- Cloud Storage stores app files later
- Vertex AI powers Gemini perception
- Cloud Build can build and push the image

## 5. Create the Cloud SQL PostgreSQL instance

Create a PostgreSQL instance in the same region as Cloud Run.

Example:

```bash
gcloud sql instances create pantry-to-plate-db \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MiB \
  --region=us-central1
```

Create the application database:

```bash
gcloud sql databases create pantry_to_plate \
  --instance=pantry-to-plate-db
```

Create a database user:

```bash
gcloud sql users create pantry_app \
  --instance=pantry-to-plate-db \
  --password=CHOOSE_A_STRONG_PASSWORD
```

Get the instance connection name:

```bash
gcloud sql instances describe pantry-to-plate-db \
  --format="value(connectionName)"
```

Save that value. It looks like:

```text
PROJECT_ID:us-central1:pantry-to-plate-db
```

## 6. Create the Cloud Storage buckets

Create three buckets:

- one for future user uploads
- one for ETL raw files
- one for ETL clean files

Example:

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-user-uploads --location=us-central1
gcloud storage buckets create gs://YOUR_PROJECT_ID-etl-raw --location=us-central1
gcloud storage buckets create gs://YOUR_PROJECT_ID-etl-clean --location=us-central1
```

Optional but recommended:

- enable lifecycle policies later for cleanup
- keep bucket names simple and region-aligned

## 7. Create the Cloud Run service account

Create a dedicated runtime service account for the backend:

```bash
gcloud iam service-accounts create pantry-backend-sa \
  --display-name="Pantry Backend Service Account"
```

Grant the roles it needs:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:pantry-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:pantry-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:pantry-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

If you want the backend to access GCS now or later, also grant:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:pantry-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

## 8. Store secrets in Secret Manager

At minimum, store the database password.

Example:

```bash
printf "CHOOSE_A_STRONG_PASSWORD" | \
gcloud secrets create db-password --data-file=-
```

If you later add other secrets, store them the same way.

Note:

- Gemini on Vertex AI does not need a separate Gemini API key when using Cloud Run with a service account.
- The service account and Vertex AI IAM role handle access.

## 9. Prepare local authentication for testing Gemini

If you want to test the backend locally against Vertex AI before deploying:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

This gives your local machine Application Default Credentials.

## 10. Create the backend environment file for local testing

Create `backend/.env` with values like these:

```env
ENVIRONMENT=production
PROJECT_NAME=Pantry to Plate
DATABASE_URL=postgresql+psycopg2://pantry_app:YOUR_DB_PASSWORD@127.0.0.1:5432/pantry_to_plate
GCP_PROJECT_ID=YOUR_PROJECT_ID
GCP_REGION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
VISION_PROVIDER=gemini_vertex
VISION_MODEL=gemini-2.5-flash
PERCEPTION_ALLOW_LOCAL_FALLBACK=false
CORS_ALLOW_ORIGINS=https://YOUR_PROJECT_ID.web.app,https://YOUR_PROJECT_ID.firebaseapp.com
GCS_UPLOAD_BUCKET=YOUR_PROJECT_ID-user-uploads
GCS_RAW_BUCKET=YOUR_PROJECT_ID-etl-raw
GCS_CLEAN_BUCKET=YOUR_PROJECT_ID-etl-clean
LOG_LEVEL=INFO
```

For pure local development, you can still use SQLite and `VISION_PROVIDER=local_heuristic`.

## 11. Build the backend container image

From the `backend/` directory, build the image:

```bash
cd backend
docker build -t pantry-to-plate-backend .
```

The repo now includes `backend/.dockerignore`, so local DB files and generated data are less likely to get copied into the image.

## 12. Create an Artifact Registry repository

Create a Docker repository:

```bash
gcloud artifacts repositories create pantry-to-plate \
  --repository-format=docker \
  --location=us-central1 \
  --description="Pantry to Plate backend images"
```

Configure Docker authentication:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

Tag the image:

```bash
docker tag pantry-to-plate-backend \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/pantry-to-plate/backend:latest
```

Push the image:

```bash
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/pantry-to-plate/backend:latest
```

## 13. Deploy the backend to Cloud Run

Because this repo currently expects `DATABASE_URL` directly, the easiest practical beginner path is:

1. create a temporary strong password
2. place the full `DATABASE_URL` value directly in Secret Manager
3. inject `DATABASE_URL` as a secret

Recommended command for this repo as-is:

```bash
printf "postgresql+psycopg2://pantry_app:YOUR_DB_PASSWORD@/pantry_to_plate?host=/cloudsql/YOUR_PROJECT_ID:us-central1:pantry-to-plate-db" | \
gcloud secrets create database-url --data-file=-
```

Then deploy like this:

```bash
gcloud run deploy pantry-to-plate-backend \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/pantry-to-plate/backend:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=pantry-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:pantry-to-plate-db \
  --set-env-vars=ENVIRONMENT=production,PROJECT_NAME="Pantry to Plate",GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_REGION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true,VISION_PROVIDER=gemini_vertex,VISION_MODEL=gemini-2.5-flash,PERCEPTION_ALLOW_LOCAL_FALLBACK=false,CORS_ALLOW_ORIGINS=https://YOUR_PROJECT_ID.web.app\\,https://YOUR_PROJECT_ID.firebaseapp.com,GCS_UPLOAD_BUCKET=YOUR_PROJECT_ID-user-uploads,GCS_RAW_BUCKET=YOUR_PROJECT_ID-etl-raw,GCS_CLEAN_BUCKET=YOUR_PROJECT_ID-etl-clean,LOG_LEVEL=INFO \
  --set-secrets=DATABASE_URL=database-url:latest
```

After deploy, copy the backend URL. It will look like:

```text
https://pantry-to-plate-backend-xxxxx-uc.a.run.app
```

## 14. Let the backend initialize the empty database

Because this branch still uses `Base.metadata.create_all()` on startup, the first successful backend start against an empty Cloud SQL database should create the tables automatically.

For this branch:

- start with an empty `pantry_to_plate` database
- do not apply `backend/db/schema.sql` manually

If Cloud Run starts successfully, visit:

```text
https://YOUR_CLOUD_RUN_URL/health
```

You should get a healthy response.

## 15. Test Gemini perception directly

Use the deployed backend first before hosting the frontend.

Test:

- `GET /health`
- `GET /ingredients`
- `POST /perception/detect`
- `GET /recipes`

You can test `/perception/detect` using the Swagger UI at:

```text
https://YOUR_CLOUD_RUN_URL/docs
```

If perception fails, check:

- Cloud Run logs
- service account permissions
- Vertex AI API enabled
- correct project and region
- `VISION_PROVIDER=gemini_vertex`
- `GCP_PROJECT_ID` set correctly

## 16. Host the frontend on Firebase Hosting

From the repo root or `frontend/` directory:

1. Build the frontend.
2. Initialize Firebase Hosting.
3. Point Hosting to the built output directory.

First install dependencies and build:

```bash
cd frontend
npm install
VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL npm run build
```

Now log in to Firebase:

```bash
firebase login
```

Initialize hosting inside the `frontend/` directory:

```bash
firebase init hosting
```

When prompted:

- choose your Firebase project that maps to the same GCP project
- set the public directory to `dist`
- configure as a single-page app: `Yes`
- overwrite `index.html`: `No`

Deploy the frontend:

```bash
firebase deploy --only hosting
```

After deploy, you will get a URL like:

```text
https://YOUR_PROJECT_ID.web.app
```

## 17. Update backend CORS if needed

If the frontend cannot call the backend because of CORS:

1. Add the actual Firebase Hosting domain to `CORS_ALLOW_ORIGINS`.
2. Deploy a new Cloud Run revision.

Expected values:

```text
https://YOUR_PROJECT_ID.web.app
https://YOUR_PROJECT_ID.firebaseapp.com
```

If you use a custom domain later, add that too.

## 18. End-to-end testing checklist

After both frontend and backend are deployed, test this exact flow:

1. Open the hosted frontend.
2. Confirm the ingredients list loads.
3. Upload an image and run detection.
4. Confirm detected ingredients appear with confidence scores.
5. Confirm pantry ingest works.
6. Confirm pantry update, consume, dismiss, and archive actions work.
7. Confirm recipe catalog suggestions load.

Also test the backend directly:

- `GET /health`
- `GET /ingredients`
- `POST /perception/detect`
- `GET /recipes`

## 19. How to troubleshoot common beginner issues

### Backend deploy succeeds but `/perception/detect` fails

Check:

- Vertex AI API is enabled
- Cloud Run service account has `roles/aiplatform.user`
- `GCP_PROJECT_ID` is correct
- `GCP_REGION` is valid
- `VISION_PROVIDER=gemini_vertex`

### Backend cannot connect to the database

Check:

- Cloud SQL instance name in `--add-cloudsql-instances`
- `DATABASE_URL` secret value
- database name is `pantry_to_plate`
- DB user and password are correct
- Cloud Run service account has `roles/cloudsql.client`

### Frontend loads but API calls fail

Check:

- `VITE_API_BASE_URL` used during frontend build
- backend is publicly reachable
- `CORS_ALLOW_ORIGINS` includes the Firebase domain

### Cloud Run starts but database tables are missing

Check:

- database is empty on first startup
- app startup completed successfully
- you did not manually initialize with the outdated `backend/db/schema.sql`

## 20. What to improve after the first successful deployment

Once the first manual deployment works, the next improvements should be:

- add Alembic migrations
- fix or retire `backend/db/schema.sql`
- create a Cloud Build pipeline
- automate Firebase Hosting deploys
- store repeatable setup in scripts or Terraform
- add Cloud Build automation
- store full deployment config in scripts or IaC
- add GCS-backed image persistence
- implement `POST /recipes/generate`

## Official References

These are the main Google docs that match this deployment flow:

- Cloud Run quickstart:
  - https://cloud.google.com/run/docs/quickstarts/deploy-container
- Cloud Run to Cloud SQL:
  - https://cloud.google.com/sql/docs/postgres/connect-run
- Artifact Registry Docker quickstart:
  - https://cloud.google.com/artifact-registry/docs/quickstarts
- Vertex AI Gemini authentication:
  - https://cloud.google.com/vertex-ai/generative-ai/docs/start/gcp-auth
- Vertex AI Gemini quickstart:
  - https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart
- Firebase Hosting quickstart:
  - https://firebase.google.com/docs/hosting/quickstart
