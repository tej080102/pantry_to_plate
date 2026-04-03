# Pantry to Plate: AI-Powered Recipe Developer 

Turn your fridge into intelligent meals. Reduce food waste. Optimize nutrition.

---

## Overview

Pantry to Plate is an AI-powered full-stack application that helps users generate recipes from available ingredients while prioritizing items that are close to spoiling.
Users upload a photo of their fridge → the system detects ingredients → ranks them based on spoilage → and generates structured recipes using a database-first + LLM hybrid approach.

---
## Core Idea

Instead of randomly generating recipes, Pantry to Plate ensures:
- Expiring ingredients are used first (FIFO logic)
- Recipes are grounded in real data (not hallucinated)
- Nutrition is calculated and surfaced to users

---

## System Architecture
Frontend (React + Vite)
↓
FastAPI Backend (Cloud Run)
↓
Cloud SQL (PostgreSQL)
↓
GCS (Image + Data Lake Storage)
↓
AI Layer
├── Computer Vision (Gemini on Vertex AI)
└── LLM (Recipe generation planned)

---

## Features

### Ingredient Detection
- Upload fridge image
- Detect ingredients using computer vision

### Pantry Management
- Store detected ingredients
- Track expiry and freshness

### FIFO Spoilage Ranking
- Prioritize ingredients nearing expiration
- Reduce food waste

### Recipe Generation
- Database-first recipe matching
- LLM-based structured recipe stitching

### Nutrition Insights
- Per-recipe macro calculations
- Sort by calories, protein, etc.

---

## Backend (Completed)

- FastAPI service with REST endpoints
- Relational schema using SQLAlchemy
- Models:
  - Ingredient
  - Recipe
  - RecipeIngredient
  - PantryItem
  - ETLRun
- API endpoints:
  - `/ingredients`
  - `/pantry`
  - `/pantry/ingest`
  - `/perception/detect`
  - `/recipes`
  - `/health`
- Local SQLite setup (Postgres-ready for Cloud SQL)
- Swagger docs available at `/docs`

---

## Data Pipeline (Current MVP)

- USDA FoodData Central Foundation Foods CSV ingestion
- Local raw → clean CSV → database ETL flow
- Data cleaning and normalization for names, categories, units, and macro fields
- Ingredient deduplication and ETL run tracking

Dataset source:
- USDA FoodData Central Downloadable Data: https://fdc.nal.usda.gov/download-datasets/
- USDA Foundation Foods documentation: https://fdc.nal.usda.gov/Foundation_Foods_Documentation/

Current ETL behavior:
- Reads USDA Foundation Foods raw CSV files from `backend/data/raw/usda_foundation/`
- Writes normalized ingredient CSV artifacts to `backend/data/clean/usda_foundation/`
- Loads cleaned records into the `ingredients` table
- Tracks execution status in the `etl_runs` table
- Keeps only `foundation_food` rows with complete core macros (`calories`, `protein`, `carbs`, `fat`) and then deduplicates by normalized ingredient name, so the final clean row count is much smaller than the raw file row count

---

## AI Components

### Computer Vision (Current)
- `POST /perception/detect` accepts image uploads
- Primary provider: Gemini on Vertex AI
- Local fallback provider: heuristic color-signature detector for dev/test use
- Structured ingredient output includes confidence scores, quantity hints, and unit hints

### Recipe Generation (Planned)
- Gemini on Vertex AI or another structured LLM path
- Structured JSON recipe generation
- Grounded in database results

---

## Tech Stack

| Layer        | Tech                   |
|--------------|------------------------|
| Frontend     | React + Vite           |
| Backend      | FastAPI                |
| Database     | PostgreSQL (Cloud SQL) |
| Storage      | GCS                    |
| AI Models    | Gemini on Vertex AI    |
| Deployment   | GCP Cloud Run          |
| CI/CD        | Cloud Build (planned)  |

---

## Deployment Readiness

The repository is structured for a GCP deployment target:
- FastAPI backend intended for Cloud Run
- PostgreSQL schema prepared for Cloud SQL
- GCS planned for uploads and ETL artifact storage
- Vertex AI Gemini is wired as the primary perception provider

Current infrastructure-facing files:
- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/cloud_sql_setup.md`
- `backend/env_setup.md`
- `infra/README.md`
- `infra/GCP_DEPLOYMENT_GUIDE.md`

Cloud provisioning and deployment automation are still manual and not yet complete.

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

### Run command to Run in conda environment
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend environment:

- `VITE_API_BASE_URL=http://localhost:8000`

The current frontend integrates directly with these backend routes:
- `/ingredients`
- `/pantry`
- `/pantry/ingest`
- `/perception/detect`
- `/pantry/{id}`
- `/pantry/{id}/consume`
- `/pantry/archive-expired`
- `/recipes`
- `/recipes/{id}`

The current frontend demo flow:
- uploads an image and calls `/perception/detect`
- falls back to manual or sample detections if the perception provider is unavailable or misconfigured
- persists pantry state through `/pantry/ingest`
- manages pantry items through update, consume, delete, dismiss, and archive actions
- ranks recipe suggestions from the existing recipe catalog when `/recipes/generate` is not available

The frontend does not require additional backend changes on this branch because:
- CORS already allows local Vite origins and can be configured for hosted origins through env vars
- pantry lifecycle routes already exist
- recipe catalog routes already exist

What is still not implemented in the backend:
- recipe generation endpoint
- GCS-backed image persistence
- production schema migrations

The UI handles those gaps explicitly and remains demo-safe.
