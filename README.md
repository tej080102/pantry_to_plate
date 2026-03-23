# Sprout: AI-Powered Recipe Developer

Turn your fridge into intelligent meals. Reduce food waste. Optimize nutrition.

---

## Overview

Sprout is an AI-powered full-stack application that helps users generate recipes from available ingredients while prioritizing items that are close to spoiling.

Users upload a photo of their fridge → the system detects ingredients → ranks them based on spoilage → and generates structured recipes using a database-first + LLM hybrid approach.

---

## Core Idea

Instead of randomly generating recipes, Sprout ensures:
- Expiring ingredients are used first (FIFO logic)
- Recipes are grounded in real data (not hallucinated)
- Nutrition is calculated and surfaced to users

---

## System Architecture
Frontend (Next.js)
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
  - `/recipes`
  - `/health`
- Local SQLite setup (Postgres-ready for Cloud SQL)
- Swagger docs available at `/docs`

---

## Data Pipeline (Planned)

- Scrapy-based ingestion (Open Food Facts, USDA)
- Data cleaning and normalization
- Shelf-life scoring engine
- GCS data lake + Cloud SQL loading
- ETL run tracking for observability

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
| Frontend     | Next.js                |
| Backend      | FastAPI                |
| Database     | PostgreSQL (Cloud SQL) |
| Storage      | GCS                    |
| AI Models    | Gemini / YOLO          |
| Deployment   | GCP Cloud Run          |
| CI/CD        | GitHub Actions         |

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
