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
├── Computer Vision (YOLO / Gemini Vision)
└── LLM (Gemini / Llama)

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

## AI Components (Planned)

### Computer Vision
- YOLOv8 or Gemini Vision
- Ingredient detection from fridge images

### LLM Layer
- Gemini Pro or Llama 3
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
| AI Models    | Gemini / YOLO          |
| Deployment   | GCP Cloud Run          |
| CI/CD        | GitHub Actions         |

---

## Deployment Readiness

The repository is structured for a GCP deployment target:
- FastAPI backend intended for Cloud Run
- PostgreSQL schema prepared for Cloud SQL
- GCS planned for uploads and ETL artifact storage

Current infrastructure-facing files:
- [`backend/Dockerfile`](/Users/somyapathak/Desktop/Masters/spring%202026/BDA/pantry_to_plate/backend/Dockerfile)
- [`backend/cloud_sql_setup.md`](/Users/somyapathak/Desktop/Masters/spring%202026/BDA/pantry_to_plate/backend/cloud_sql_setup.md)
- [`backend/env_setup.md`](/Users/somyapathak/Desktop/Masters/spring%202026/BDA/pantry_to_plate/backend/env_setup.md)
- [`infra/README.md`](/Users/somyapathak/Desktop/Masters/spring%202026/BDA/pantry_to_plate/infra/README.md)

Cloud provisioning and deployment automation are still manual and not yet complete.

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
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
- `/pantry/{id}`
- `/pantry/{id}/consume`
- `/pantry/archive-expired`
- `/recipes`
- `/recipes/{id}`

The current frontend demo flow:
- uploads an image and attempts `/perception/detect`
- falls back to manual or sample detections if that backend route is unavailable
- persists pantry state through `/pantry/ingest`
- manages pantry items through update, consume, delete, dismiss, and archive actions
- ranks recipe suggestions from the existing recipe catalog when `/recipes/generate` is not available

The frontend does not require additional backend changes on this branch because:
- CORS already allows local Vite origins
- pantry lifecycle routes already exist
- recipe catalog routes already exist

What is still not implemented in the backend:
- image perception upload/detection endpoint
- recipe generation endpoint

The UI handles those gaps explicitly and remains demo-safe.
