# Infrastructure Overview

Pantry to Plate is designed for a simple GCP architecture:

- FastAPI backend deployed to Cloud Run
- PostgreSQL database hosted on Cloud SQL
- Google Cloud Storage used for user uploads and ETL artifacts

## Intended setup flow

1. Create a dedicated GCP project.
2. Enable the required APIs for Cloud Run, Cloud SQL, Cloud Storage, IAM, and Secret Manager.
3. Create a PostgreSQL Cloud SQL instance and a `pantry_to_plate` database.
4. Create GCS buckets for uploads, raw ETL data, and clean ETL data.
5. Configure secrets and environment variables for the backend runtime.
6. Build and deploy the backend container to Cloud Run.

## Current repo support

- SQL schema and seed scripts live under [`backend/db`](../backend/db)
- A Cloud Run-friendly backend container definition exists at [`backend/Dockerfile`](../backend/Dockerfile)
- Environment setup guidance exists at [`backend/env_setup.md`](../backend/env_setup.md)

## Still manual / not automated yet

- GCP project provisioning
- Cloud SQL instance creation
- IAM and service account setup
- Secret Manager wiring
- Cloud Build or GitHub Actions deployment automation
- Terraform or other infrastructure-as-code support
