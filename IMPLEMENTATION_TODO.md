# Pantry to Plate Implementation Audit and Roadmap

Last reviewed: 2026-04-02

This document is the current source of truth for project status and the remaining work to reach a production-ready GCP deployment.

## Executive Summary

Pantry to Plate already has a working local MVP:

- FastAPI backend with ingredient, pantry, recipe catalog, health, and perception routes
- React + Vite frontend that exercises the current backend
- Pantry ranking and lifecycle management
- USDA Foundation Foods ETL pipeline
- Basic backend containerization and deployment notes

Current completion estimate:

- Application MVP: 65-75% complete
- Production GCP readiness: 20-30% complete

The main remaining work is not basic app scaffolding. It is production hardening:

- reconcile schema drift between SQL and ORM
- add migrations
- wire real production configuration
- provision GCP services
- add deployment automation
- complete the missing AI recipe generation path

## Implemented Today

### Backend API

Implemented routes in `backend/app/api/routes`:

- `GET /health`
- `GET /ingredients`
- `POST /ingredients`
- `GET /recipes`
- `GET /recipes/{id}`
- `GET /pantry`
- `POST /pantry/ingest`
- `PATCH /pantry/{id}`
- `DELETE /pantry/{id}`
- `POST /pantry/{id}/consume`
- `POST /pantry/archive-expired`
- `POST /perception/detect`

Notes:

- The backend is a FastAPI app in `backend/app/main.py`.
- SQLite is supported for local development.
- PostgreSQL is the intended production database target.
- Swagger/OpenAPI docs are available through FastAPI.

### Pantry and Spoilage Logic

Implemented in `backend/app/services`:

- pantry ingest from confirmed detections
- canonical ingredient matching with optional manual corrections
- expiry estimation from ingredient shelf life and category fallback
- FIFO-style spoilage ranking
- pantry update, delete, consume, archive, and false-positive handling

### Perception MVP

Implemented in `backend/app/api/routes/perception.py` and `backend/app/services/perception.py`:

- multipart image upload handling
- file size and type validation
- image decoding with Pillow
- structured ingredient detection output with confidence scores

Current limitation:

- this is a local heuristic detector based on image color signatures
- it is not yet a Gemini, YOLO, or other production vision integration

### Recipes

Implemented today:

- recipe catalog retrieval
- recipe detail retrieval with ingredient joins
- frontend recipe suggestion fallback based on pantry overlap and existing catalog

Not implemented today:

- `POST /recipes/generate`
- LLM-backed structured recipe generation

### ETL Pipeline

Implemented in `backend/app/etl`:

- USDA Foundation Foods transform flow
- normalized clean CSV output
- database load flow
- ETL run tracking
- ingredient deduplication and nutrition normalization

### Frontend

Implemented in `frontend/src`:

- image upload UI
- detection review and manual correction flow
- pantry dashboard
- pantry lifecycle actions
- recipe suggestion UI using current catalog data
- configurable backend base URL via `VITE_API_BASE_URL`

### Existing Deployment Support

Present in the repository:

- backend container definition in `backend/Dockerfile`
- environment setup notes in `backend/env_setup.md`
- Cloud SQL guidance in `backend/cloud_sql_setup.md`
- infrastructure overview in `infra/README.md`

## Known Gaps and Deployment Blockers

### 1. README and doc drift

Some docs no longer match the codebase:

- `README.md` and `frontend/README.md` still describe `/perception/detect` as missing
- the route already exists and is wired in the backend

This needs to be corrected to avoid planning and deployment mistakes.

### 2. Schema drift between SQL and ORM

This is the highest-risk backend blocker for Cloud SQL deployment.

`backend/db/schema.sql` does not match the current ORM models. In particular, the `pantry_items` table definition is behind `backend/app/models/pantry_item.py`.

The ORM expects these fields that are missing from `backend/db/schema.sql`:

- `source_detected_name`
- `is_archived`
- `is_false_positive`

Impact:

- a manual Cloud SQL bootstrap from `backend/db/schema.sql` will create the wrong schema
- the running app will then disagree with the deployed database shape

### 3. No migration system

The app still relies on local bootstrap logic in `backend/app/main.py`:

- `Base.metadata.create_all(bind=engine)`
- `ensure_pantry_item_schema_compatibility(engine)`

This is acceptable for local SQLite development, but not for production schema evolution.

Required fix:

- add Alembic
- make migrations the source of truth for schema changes
- stop depending on `create_all()` for deployed environments

### 4. Config is not production-ready

`backend/app/core/config.py` currently wires only:

- `PROJECT_NAME`
- `DATABASE_URL`

Documented GCP-related settings are not yet loaded into runtime config, including:

- environment name
- CORS origins
- GCP project and region
- GCS bucket names
- vision provider/model
- recipe model
- logging level

### 5. CORS is localhost-only

`backend/app/main.py` currently allows local Vite and localhost origins only.

Impact:

- the current backend is not ready for a hosted frontend origin
- production deployment needs environment-driven CORS configuration

### 6. Container hygiene is incomplete

The backend container exists, but there is no `.dockerignore`.

Current risk:

- `backend/Dockerfile` copies the full backend context into the image
- local database files in `backend/` can be included in image builds unintentionally

### 7. No CI/CD or IaC

Missing from the repo today:

- `.github/` workflows
- `cloudbuild.yaml`
- Terraform or other infrastructure-as-code
- deployment scripts for repeatable environment setup

### 8. GCS storage is planned, not implemented

The intended architecture uses GCS for:

- user image uploads
- raw ETL artifacts
- clean ETL artifacts

Current state:

- ETL tracks path-like fields in the database
- image uploads are processed in memory
- no real GCS integration exists yet

### 9. Recipe generation is still missing

The top-level product vision expects a DB-first plus LLM recipe flow.

Current state:

- recipe catalog browsing exists
- frontend demo fallback exists
- true generation endpoint does not exist yet

## Recommended Hosting Defaults

Unless requirements change, the default production target should be:

- frontend: Firebase Hosting
- backend: Cloud Run
- database: Cloud SQL for PostgreSQL
- object storage: Google Cloud Storage
- secrets: Secret Manager
- container registry: Artifact Registry
- deployment pipeline: Cloud Build
- default region: `us-central1`

This keeps the stack fully on GCP while staying simple for an MVP deployment.

## Remaining Work in Execution Order

### 0. Platform Hardening

Complete this before infrastructure rollout.

Tasks:

- add Alembic under `backend/`
- reconcile ORM models with SQL bootstrap artifacts
- make migrations authoritative for schema changes
- update `backend/db/schema.sql` or retire it in favor of migrations
- expand `backend/app/core/config.py` into real environment-aware settings
- add production-safe CORS configuration
- add `.dockerignore`
- pin Python dependencies more explicitly
- define separate local, test, staging, and production config behavior

Acceptance criteria:

- local backend still runs cleanly
- PostgreSQL schema matches ORM via migrations
- production config shape is explicit
- container builds do not include accidental local artifacts

### 1. GCP Foundation

Provision the base platform.

Tasks:

- create a dedicated GCP project
- enable billing
- enable required APIs:
  - Cloud Run Admin API
  - Cloud SQL Admin API
  - Cloud Build API
  - Artifact Registry API
  - Secret Manager API
  - Cloud Storage API
  - IAM API
  - Service Usage API
  - Logging API
  - Monitoring API
- create Artifact Registry repository
- create Cloud SQL PostgreSQL instance and `pantry_to_plate` database
- create GCS buckets for uploads, ETL raw, and ETL clean data
- define lifecycle policies for buckets
- create runtime and deploy service accounts
- assign least-privilege IAM roles
- define separate staging and production environments

Acceptance criteria:

- project and APIs exist
- Cloud SQL, Artifact Registry, and buckets exist
- service accounts and IAM are configured
- staging and production separation is documented

### 2. Backend Production Deployment

Deploy the FastAPI service to Cloud Run.

Tasks:

- build the backend image through Cloud Build
- push the image to Artifact Registry
- deploy the backend to Cloud Run
- attach the Cloud SQL connection
- inject non-secret config as environment variables
- inject secrets from Secret Manager
- configure request timeout, CPU, memory, concurrency, and min instances
- define health-check and smoke-check expectations

Acceptance criteria:

- Cloud Run service starts successfully
- `GET /health` returns healthy status
- backend can connect to Cloud SQL
- deployed service is reachable from the hosted frontend origin

### 3. Frontend Hosting on GCP

Host the Vite SPA on GCP.

Tasks:

- define the production frontend build process
- host the frontend with Firebase Hosting
- set `VITE_API_BASE_URL` to the Cloud Run backend URL
- verify SPA routing and static asset delivery
- verify browser-to-API requests and CORS behavior

Acceptance criteria:

- hosted frontend loads successfully
- frontend can call deployed backend routes
- upload, pantry, and recipe catalog flows work from the hosted site

### 4. Product Completion Work

Finish the missing user-facing capabilities.

### 4.1 Recipe generation

Tasks:

- add `POST /recipes/generate`
- define strict request and response schemas
- implement DB-first candidate selection
- add LLM-backed structured recipe generation or stitching
- validate and surface generated recipe structure safely

Acceptance criteria:

- frontend no longer needs catalog-only generation fallback
- generated recipes are structured and grounded in pantry and catalog data

### 4.2 Perception production path

Tasks:

- decide whether to keep the current local heuristic as demo-only
- choose Gemini Vision, YOLO, or a hybrid approach
- optionally store uploads in GCS before or after inference
- preserve the current editable confirmation flow before pantry ingest

Acceptance criteria:

- perception behavior is intentionally defined for production
- output contract remains stable for the frontend

### 4.3 GCS integration

Tasks:

- wire upload bucket usage for image files
- wire raw and clean ETL artifact storage as real GCS paths
- define retention and cleanup policy for uploaded images

Acceptance criteria:

- storage usage matches the intended architecture
- artifact paths in the database correspond to real GCS objects

### 5. CI/CD and Operations

Automate delivery and add basic production operations.

Tasks:

- add Cloud Build pipeline configuration
- add repeatable deploy steps for backend and frontend
- add backend test execution in CI
- add frontend build verification in CI
- add smoke tests after deploy
- define logging and monitoring expectations
- document rollback steps for failed deploys

Acceptance criteria:

- deployments are repeatable
- test and build failures block bad releases
- production health can be monitored after release

## Required Environment Variables

These should be supported explicitly by application config.

- `ENVIRONMENT`
- `PROJECT_NAME`
- `DATABASE_URL`
- `CORS_ALLOW_ORIGINS`
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCS_UPLOAD_BUCKET`
- `GCS_RAW_BUCKET`
- `GCS_CLEAN_BUCKET`
- `VISION_PROVIDER`
- `VISION_MODEL`
- `RECIPE_MODEL`
- `LOG_LEVEL`

Secrets should not be committed. Use:

- local `.env` for development
- Secret Manager for deployed environments

Examples of secret values:

- database password
- LLM provider API key
- vision provider API key

## Verification Checklist

Before calling the system production-ready, verify all of the following:

- backend dependencies install successfully
- backend tests pass from `backend/tests`
- frontend dependencies install successfully
- frontend production build succeeds
- migrations apply cleanly to PostgreSQL
- Cloud SQL schema matches the current ORM and API expectations
- Cloud Run backend responds correctly to:
  - `GET /health`
  - `GET /ingredients`
  - `POST /perception/detect`
  - `POST /pantry/ingest`
  - `GET /pantry`
  - `GET /recipes`
- hosted frontend can reach the deployed backend without CORS failures
- pantry ingest, pantry lifecycle actions, and recipe catalog flows work end-to-end in the hosted environment

## Current Reality Check

What is genuinely done:

- local MVP application
- local ETL pipeline
- demo-safe frontend
- partial deployment preparation docs

What is not done yet:

- production schema migration strategy
- production GCP provisioning
- deployment automation
- GCS integration
- production-ready vision integration
- recipe generation API

The project is beyond the scaffold stage, but not yet ready for a reliable GCP production launch.
