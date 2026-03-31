# Pantry to Plate Implementation TODO

This document describes how to proceed from the current repository state to a production-ready Pantry to Plate system.

Current repository status:
- Backend foundation exists in `backend/app`
- Core database models exist for ingredients, nutrition, recipes, pantry items, and ETL runs
- Basic FastAPI routes exist for `/ingredients`, `/recipes`, `/pantry`, and `/health`
- USDA ETL flow exists for local CSV transform and database load
- Pantry state MVP exists with spoilage ranking and pantry retrieval
- A basic backend Dockerfile and environment/infrastructure documentation now exist
- Cloud infrastructure, pantry state validation hardening, recipe inference, full testing, and deployment are not finished

Recommended execution order:
1. Stabilize platform and environment setup
2. Add image upload and perception pipeline
3. Add pantry state and FIFO spoilage prioritization
4. Add structured recipe inference pipeline
5. Add integration tests and evaluation
6. Add deployment automation and production operations

---

## 0. Prerequisites and Project Hardening

Do this before building the remaining product layers.

### Goals
- Make local, staging, and production configuration explicit
- Remove ambiguity between SQLite local development and PostgreSQL production
- Prepare the repo for Cloud Run deployment

### Tasks
- Add documented backend environment configuration in `backend/.env`
- Add a backend `Dockerfile`
- Add dependency pinning in `backend/requirements.txt` or move to a lock-based workflow
- Add database migration support
  - Recommended: Alembic for SQLAlchemy schema changes
  - Do not rely on `Base.metadata.create_all()` for production evolution
- Split config into clear settings categories
  - local development
  - test
  - staging
  - production
- Add explicit app settings for:
  - database
  - GCS bucket names
  - GCP project and region
  - vision provider/model
  - inference provider/model
  - logging level
  - environment name
- Decide whether frontend deployment will be:
  - Vercel for Next.js and Cloud Run for API
  - fully on GCP

Current status:
- Documented backend environment setup now exists in `backend/env_setup.md`
- A basic `backend/Dockerfile` now exists and is suitable for a simple Cloud Run container
- `infra/README.md` now documents the intended GCP architecture
- Dependency pinning, migrations, expanded settings, and deployment automation are still not done

### Suggested backend additions
- `backend/app/core/settings.py` or expand `backend/app/core/config.py`
- `backend/alembic.ini`
- `backend/alembic/`
- `backend/Dockerfile`
- environment setup documentation for `backend/.env`

### Required environment variables
- `ENVIRONMENT`
- `PROJECT_NAME`
- `DATABASE_URL`
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCS_UPLOAD_BUCKET`
- `GCS_RAW_BUCKET`
- `GCS_CLEAN_BUCKET`
- `GOOGLE_APPLICATION_CREDENTIALS` for local development only when needed
- `VISION_PROVIDER`
- `VISION_MODEL`
- `OPENAI_API_KEY` or other LLM provider key if used
- `RECIPE_MODEL`
- `LOG_LEVEL`

### Acceptance criteria
- Local backend runs with documented setup steps
- Staging and production config shape is defined
- Docker image builds locally
- Migrations exist for schema changes

Current status:
- Partially met
- Local setup and environment shape are documented
- A Dockerfile exists in the repo
- Migrations do not exist yet
- Cloud Run deployment automation is not implemented yet

---

## 1. GCP Environment Configuration

This corresponds to your first remaining task.

### Objective
Provision and configure GCP services for backend runtime, database, object storage, and secure service-to-service access.

### Target architecture
- FastAPI backend on Cloud Run
- PostgreSQL on Cloud SQL
- Uploaded images and ETL artifacts in Google Cloud Storage
- Secrets in Secret Manager
- IAM-bound service accounts for runtime and CI/CD

### Step-by-step tasks

#### 1.1 Create and configure the GCP project
- Create a dedicated GCP project for Pantry to Plate
- Set billing
- Set default region
- Enable required APIs:
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

#### 1.2 Create storage resources
- Create GCS buckets for:
  - user image uploads
  - raw ETL data
  - clean ETL outputs
  - optional model artifacts
- Turn on uniform bucket-level access
- Decide lifecycle rules for uploads and ETL artifacts
- Decide whether uploaded user images should expire automatically after a retention period

Suggested bucket naming:
- `<project>-user-uploads`
- `<project>-etl-raw`
- `<project>-etl-clean`

#### 1.3 Create Cloud SQL
- Create PostgreSQL instance
- Create database `pantry_to_plate`
- Create dedicated application database user
- Prefer private IP or Cloud SQL connector path for Cloud Run
- Apply schema from `backend/db/schema.sql`
- Add migrations and move future changes to Alembic

#### 1.4 Create service accounts
- Create separate service accounts for:
  - Cloud Run backend runtime
  - CI/CD deploy pipeline
  - optional ETL job runner

Recommended service accounts:
- `pantry-backend-sa`
- `pantry-deploy-sa`
- `pantry-etl-sa`

#### 1.5 Assign IAM roles

Cloud Run backend service account should have only what it needs:
- `roles/cloudsql.client`
- `roles/storage.objectAdmin` or narrower bucket-scoped storage permissions
- `roles/secretmanager.secretAccessor`
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`

CI/CD deploy service account typically needs:
- `roles/run.admin`
- `roles/iam.serviceAccountUser`
- `roles/cloudbuild.builds.editor`
- `roles/artifactregistry.writer`
- `roles/secretmanager.secretAccessor` only if deploy step resolves secrets

ETL service account may need:
- `roles/cloudsql.client`
- `roles/storage.objectAdmin`
- `roles/logging.logWriter`

#### 1.6 Configure secrets and environment variables
- Store secrets in Secret Manager
  - database password
  - API keys for vision or LLM providers
- Configure non-secret environment variables on Cloud Run
- Do not commit service account keys to the repo
- For local development, use `.env`
- For production, inject secrets from Secret Manager

#### 1.7 Configure Cloud Run service
- Add backend container build and deploy flow
- Set service account to `pantry-backend-sa`
- Configure Cloud SQL connection
- Set concurrency, CPU, memory, min instances, and request timeout
- Configure CORS for frontend origin
- Set health check expectations

### Suggested deliverables
- `infra/README.md`
- `infra/gcp_setup.md`
- `cloudbuild.yaml`
- `backend/Dockerfile`
- environment setup documentation for `backend/.env`
- deployment scripts or Terraform if using IaC

Current repo coverage:
- Present: `infra/README.md`, `backend/Dockerfile`, environment setup documentation
- Missing: `infra/gcp_setup.md`, `cloudbuild.yaml`, deployment scripts, IaC

### Acceptance criteria
- GCP project is created and configured
- Cloud Run, Cloud SQL, and GCS are enabled
- Service accounts and IAM roles are configured
- Environment variables and credentials are set securely

### Missing items you should include
- Secret Manager
- Artifact Registry
- Cloud Build or GitHub Actions deploy pipeline
- Logging and Monitoring
- bucket lifecycle policies
- staging environment separate from production

---

## 2. Perception Layer: Ingredient Detection From Images

This corresponds to your second remaining task.

### Objective
Accept uploaded images, store them safely, run ingredient detection, and return a structured result usable by the next layer.

### Minimum product behavior
- User uploads image
- Backend validates file type and size
- Image is stored in GCS or a temp path
- Vision model runs inference
- Result returns a normalized ingredient list with confidence scores
- Output is editable or confirmable by the user before persistence

### Design decisions to make first
- Model choice:
  - Gemini Vision style multimodal extraction
  - YOLO-based object detection plus ingredient label mapping
  - hybrid approach
- Response shape:
  - bounding boxes or no bounding boxes
  - one detection per object vs deduplicated ingredient names
- Whether manual correction is required before committing to pantry state

### Recommended implementation path

#### 2.1 Add upload API
- Add route: `POST /perception/detect`
- Accept multipart image upload or signed URL reference
- Validate:
  - MIME type
  - file size
  - supported formats
- Store original image to GCS
- Return upload reference and detection result

Suggested files:
- `backend/app/api/routes/perception.py`
- `backend/app/services/storage.py`
- `backend/app/services/perception.py`
- `backend/app/schemas/perception.py`

#### 2.2 Add structured detection schema
- Create response models such as:
  - `DetectedIngredient`
  - `PerceptionResult`

Suggested response shape:
```json
{
  "image_uri": "gs://bucket/user-uploads/123.jpg",
  "ingredients": [
    {
      "raw_label": "apple",
      "normalized_name": "Apple",
      "confidence": 0.94
    }
  ]
}
```

Optional fields:
- `bbox`
- `quantity_hint`
- `unit_hint`
- `source_model`

#### 2.3 Normalize detections for downstream use
- Map raw labels to canonical ingredient names
- Reuse existing ingredient records where possible
- Add alias handling for cases like:
  - scallion vs green onion
  - bell pepper vs capsicum
  - coriander vs cilantro

This normalization logic should live outside the route handler.

Suggested module:
- `backend/app/services/ingredient_normalizer.py`

#### 2.4 Persist perception events
- Add a table for uploaded images and detection results
- Recommended new tables:
  - `image_uploads`
  - `ingredient_detections`

This gives traceability and helps debugging model quality later.

#### 2.5 Handle failure modes
- corrupted image
- unsupported format
- no ingredients detected
- low-confidence detections
- provider timeout or API failure

### Acceptance criteria
- Image input is processed successfully
- Ingredients are detected and returned as structured output
- Confidence scores are included
- Output is usable by downstream components

### Missing items you should include
- manual review/edit step for low-confidence detections
- image validation and rate limiting
- image retention policy
- normalized ingredient alias table or synonym map
- detection persistence for analytics and debugging

---

## 3. Application State Layer: Pantry State and FIFO Spoilage Prioritization

This corresponds to your third remaining task.

### Objective
Store the detected ingredient list as application state, map shelf-life data, and rank ingredients by urgency so the recipe layer can prioritize them.

### Core rule
The system should not only store what was detected. It should transform detections into pantry items with timestamps, expiry estimates, and a repeatable ranking algorithm.

### Recommended flow
1. Accept confirmed detection list from perception layer
2. Map each detected ingredient to canonical ingredient metadata
3. Create pantry item rows with `date_added`
4. Estimate expiry using ingredient metadata
5. Rank by FIFO and spoilage urgency
6. Return ranked pantry view

### Tasks

#### 3.1 Add pantry ingestion endpoint
- Add route: `POST /pantry/ingest`
- Input:
  - user id
  - detected ingredient list
  - optional manual corrections
- Output:
  - persisted pantry items
  - spoilage ranking
  - priority flags

Suggested files:
- `backend/app/api/routes/pantry.py`
- `backend/app/schemas/pantry.py`
- `backend/app/services/pantry_state.py`
- `backend/app/services/spoilage.py`

Status in current repo:
- Completed
- `POST /pantry/ingest` persists matched detections as `PantryItem` rows
- Optional manual corrections are supported as a simple detected-name to corrected-name mapping
- Unmatched detections are returned so callers can review what was not persisted

#### 3.2 Add shelf-life mapping logic
- Use existing `Ingredient.estimated_shelf_life_days`
- Fill missing shelf-life data for canonical ingredients
- Decide a fallback policy when shelf-life is unknown
  - mark as unknown
  - exclude from priority
  - use category-based defaults

Recommended approach:
- keep explicit per-ingredient shelf life when available
- fall back to category defaults only when no explicit value exists

Status in current repo:
- Completed for MVP
- Explicit per-ingredient shelf life is used first
- Category defaults are used as a fallback
- If no explicit or category shelf life exists, expiry remains unknown

#### 3.3 Implement FIFO ranking
- Use `date_added`
- Estimate `estimated_expiry_date`
- Rank by:
  - earliest expiry first
  - then earliest added date
  - then highest confidence or highest quantity if needed

Example priority rule:
- `HIGH`: expires within 2 days
- `MEDIUM`: expires within 3 to 5 days
- `LOW`: all others
- `UNKNOWN`: missing shelf-life data

Status in current repo:
- Completed for MVP
- Ranking is deterministic
- Ordering is by earliest expiry, then earliest added date, then confidence/quantity tie-breakers
- Unknown expiry dates are placed at the end

#### 3.4 Expose pantry retrieval endpoint
- Add route: `GET /pantry`
- Filter by user
- Return:
  - canonical ingredient metadata
  - quantity or detection confidence
  - date added
  - estimated expiry
  - priority rank

Status in current repo:
- Completed
- `GET /pantry?user_id=...` returns ranked pantry items with ingredient metadata, expiry, priority bucket, and rank

#### 3.5 Add state mutation operations
- Add support for:
  - confirm detection
  - remove false positive
  - manually edit quantity
  - mark consumed
  - archive expired items

Without these controls, state quality will degrade quickly.

Status in current repo:
- Partially completed
- `PATCH /pantry/{id}` updates quantity and unit
- `DELETE /pantry/{id}` removes a pantry item
- `POST /pantry/{id}/consume` reduces quantity and deletes the item when fully consumed
- Still missing: explicit false-positive workflow, archive-expired operation, and a separate confirm-detection state transition

### Acceptance criteria
- Ingredient list is stored as application state
- Shelf-life data is mapped to ingredients
- FIFO ranking logic is implemented
- Priority ingredients are identified correctly

Current status:
- Met for Pantry State MVP
- Remaining gaps are auditability, explicit false-positive/archive workflows, and deterministic tests

### Missing items you should include
- user identity model or temporary session identity
- pantry item lifecycle actions
- fallback logic for unknown shelf life
- deterministic ranking tests
- auditability of detection-to-pantry mapping

---

## 4. Inference Layer: Recipe Generation Based on Prioritized Ingredients

This corresponds to your fourth remaining task.

### Objective
Generate recipes from the ranked pantry list using a structured and reliable flow rather than unconstrained free-text generation.

### Recommended architecture
- Start with database-first retrieval
- Then use an LLM only for structured stitching, substitution handling, formatting, and explanation
- Validate output against a strict schema before returning it

### Recommended flow
1. Accept ranked pantry input
2. Query candidate recipes from database using ingredient overlap
3. Score candidates using priority ingredients
4. If enough structured recipes exist, return them directly
5. If coverage is weak, invoke LLM to produce structured recipe output
6. Validate recipe response against schema
7. Attach nutrition summary where possible

### Tasks

#### 4.1 Add recipe generation endpoint
- Add route: `POST /recipes/generate`
- Input:
  - user id or pantry id
  - ranked ingredient list
  - optional dietary constraints
  - optional max cook time
- Output:
  - structured list of recipes

Suggested files:
- `backend/app/api/routes/recipe_generation.py`
- `backend/app/services/recipe_matcher.py`
- `backend/app/services/recipe_generator.py`
- `backend/app/services/nutrition.py`
- `backend/app/schemas/recipe_generation.py`

#### 4.2 Define strict response schema
- Do not return arbitrary text blobs
- Use Pydantic response schemas

Suggested fields:
- `title`
- `summary`
- `ingredients`
- `priority_ingredients_used`
- `missing_ingredients`
- `instructions`
- `estimated_cook_time_minutes`
- `servings`
- `nutrition`
- `source`

#### 4.3 Implement prioritization-aware ranking
- Candidate scoring should reward:
  - use of high-priority ingredients
  - higher pantry coverage
  - fewer missing ingredients
- Penalize recipes that ignore urgent items

Example scoring factors:
- pantry overlap score
- urgent ingredient usage score
- missing ingredient penalty
- cook time fit

#### 4.4 Add prompt and validation layer if using LLM
- Build structured prompt using:
  - pantry list
  - ranked priority items
  - ingredient metadata
  - recipe candidate skeletons if available
- Require JSON output
- Validate with Pydantic
- Retry once on invalid output
- Log invalid generations for debugging

#### 4.5 Add nutrition enrichment
- Use `ingredient_nutrition`
- Estimate recipe-level totals from ingredient quantities where possible
- If exact recipe quantity is unavailable, return nutrition estimate with confidence note

### Acceptance criteria
- Input ingredient list is accepted
- Recipe output is generated successfully
- Output follows structured format
- Priority ingredients are reflected in output

### Missing items you should include
- schema validation of LLM output
- fallback when generation fails
- prompt versioning
- trace logging for model responses
- recipe scoring metrics

---

## 5. Testing and Validation

You mentioned testing after the feature work. It should be planned in parallel, not only at the end.

### Test layers to add

#### 5.1 Unit tests
- spoilage ranking logic
- ingredient normalization
- recipe scoring
- response schema validation
- GCS path building
- config loading

#### 5.2 Integration tests
- image upload to perception route
- perception output to pantry ingest
- pantry ingest to FIFO ranking
- ranked pantry to recipe generation
- Cloud SQL integration against PostgreSQL

#### 5.3 Contract tests
- Verify API response shapes for:
  - `/perception/detect`
  - `/pantry/ingest`
  - `/pantry`
  - `/recipes/generate`

#### 5.4 Model evaluation
- perception precision and recall on a labeled image set
- recipe usefulness evaluation
- priority ingredient coverage rate
- structured output validity rate

#### 5.5 Manual QA
- upload common fridge image
- upload noisy image
- confirm low-confidence edits
- verify urgent items rise to top
- verify generated recipes use urgent ingredients

### Acceptance criteria
- All core services have unit tests
- Main user flow has integration coverage
- API schemas are validated
- Perception and inference quality are measured, not assumed

---

## 6. Deployment and Operations

After feature completion and testing, finish deployment properly.

### Tasks
- Build backend container image
- Push to Artifact Registry
- Deploy Cloud Run service
- Configure Cloud SQL connection
- Configure runtime secrets from Secret Manager
- Set CORS for frontend origin
- Set logging and monitoring dashboards
- Add error alerting
- Add CI/CD pipeline
- Add staging deployment before production

### Recommended production endpoints
- `/health`
- `/perception/detect`
- `/pantry/ingest`
- `/pantry`
- `/recipes/generate`

### CI/CD checklist
- lint
- type checks
- tests
- build container
- deploy to staging
- smoke test staging
- manual approval for production
- deploy to production

### Operational items you should not skip
- request logging with correlation IDs
- structured JSON logs
- retry policy for external providers
- rate limiting
- timeout configuration
- cost controls for model inference
- data retention policy for uploaded images

---

## 7. Recommended Database and API Additions

These are not in your four feature bullets, but they are likely needed.

### New database tables to consider
- `image_uploads`
- `ingredient_detections`
- `recipe_generation_runs`
- `ingredient_aliases`
- optional `users` or `sessions`

### New backend routes to consider
- `POST /perception/detect`
- `POST /pantry/ingest`
- `GET /pantry`
- `PATCH /pantry/{id}`
- `DELETE /pantry/{id}`
- `POST /pantry/{id}/consume`
- `POST /recipes/generate`
- `GET /recipes/generated/{id}` if generation results are persisted

### New service modules to consider
- `storage.py`
- `perception.py`
- `ingredient_normalizer.py`
- `pantry_state.py`
- `spoilage.py`
- `recipe_matcher.py`
- `recipe_generator.py`
- `nutrition.py`

---

## 8. Suggested Milestone Plan

### Milestone 1: Platform Ready
- Dockerfile added
- `.env` shape documented
- GCP project and services created
- Cloud SQL reachable
- Cloud Run deploy works
- Secret Manager wired

Current status:
- Partially complete
- Dockerfile and environment documentation are present
- GCP provisioning, Cloud SQL reachability validation, deployment, and Secret Manager wiring are still pending

### Milestone 2: Perception MVP
- image upload works
- detections returned with confidence
- detections normalized
- low-confidence handling defined

### Milestone 3: Pantry State MVP
- confirmed detections stored as pantry items
- shelf-life mapped
- FIFO ranking works
- pantry API returns priority labels

Current status:
- Implemented in the backend
- Still missing archive-expired flow, false-positive handling, and dedicated tests

### Milestone 4: Recipe MVP
- ranked pantry accepted
- structured recipe output returned
- priority ingredients reflected
- schema validation added

### Milestone 5: Quality and Deployment
- unit and integration tests pass
- staging deployed
- production deploy checklist completed
- monitoring and alerts configured

---

## 9. Immediate Next Actions

If you want the most efficient next sequence from the current repo, do this:

1. Add Dockerfile, environment setup documentation, and Alembic migrations
2. Provision GCP project, Cloud SQL, GCS, Secret Manager, service accounts, and Cloud Run
3. Add `POST /perception/detect` with storage + structured response schema
4. Add normalized detection persistence tables
5. Add the remaining pantry lifecycle actions: remove false positives, archive expired items, and explicit confirm-detection handling
6. Add `POST /recipes/generate` with strict output schema
7. Add integration tests for the full upload → pantry → recipe flow
8. Add CI/CD and staging deployment

---

## 10. Definition of Done

The project should be considered complete only when all of the following are true:
- Infrastructure exists in GCP and is reproducible
- Secrets are managed securely
- Image uploads are processed successfully
- Detections are normalized and confidence-scored
- Pantry state is persisted and ranked by spoilage urgency
- Recipe generation is structured and prioritization-aware
- Tests cover the main user flow
- Staging and production deployments are repeatable
- Logs, alerts, and runtime monitoring are in place
