# Pantry to Plate Recipe Developer: Backend

## Overview

The Pantry to Plate backend is a FastAPI-based service that powers an AI-driven system to reduce food waste and generate recipes from available ingredients. It provides the core data models, APIs, and storage layer required for ingredient management, pantry tracking, and recipe retrieval.

This backend is designed to support:
- Ingredient ingestion and normalization
- Pantry state tracking with spoilage awareness
- Recipe storage and retrieval
- Future integration with computer vision and LLM-based generation

---

## Architecture

- **Framework**: FastAPI
- **Database**: SQLite (local dev), designed for PostgreSQL (Cloud SQL)
- **ORM**: SQLAlchemy
- **API Layer**: RESTful endpoints with Pydantic schemas
- **Deployment Target**: Google Cloud Run (future)

---

## Data Model Design

The backend uses a relational schema optimized for food and recipe data:

### Core Entities

- **Ingredient**
  - Canonical ingredient metadata
  - Shelf-life estimation for spoilage tracking

- **IngredientNutrition**
  - One-to-one nutrition facts linked to an ingredient
  - Keeps nutrition normalized outside the ingredient record

- **Recipe**
  - Structured instructions and metadata

- **RecipeIngredient**
  - Many-to-many relationship between recipes and ingredients

- **PantryItem**
  - Tracks user-specific ingredients and expiry data
  - Enables FIFO-based prioritization

- **ETLRun**
  - Tracks ingestion pipeline runs for observability

This design supports:
- Efficient recipe matching
- Nutrition-based filtering
- Expiry-aware ingredient prioritization

SQL artifacts for PostgreSQL / Cloud SQL are available in:
- `db/schema.sql`
- `db/seed.sql`
- `db/validation_queries.sql`

---

## API Endpoints

### Health
- `GET /health` → Service status

### Ingredients
- `GET /ingredients` → List all ingredients
- `POST /ingredients` → Add a new ingredient

### Recipes
- `GET /recipes` → List all recipes
- `GET /recipes/{id}` → Get recipe with ingredients

### Pantry
- `POST /pantry/ingest` → Persist detected ingredients as pantry state
- `GET /pantry` → List ranked pantry items for a user
- `PATCH /pantry/{id}` → Update pantry quantity or unit
- `DELETE /pantry/{id}` → Remove pantry item
- `POST /pantry/{id}/consume` → Reduce pantry quantity or consume item fully

---

## Local Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the API
```bash
uvicorn app.main:app --reload
```

### 3. Run the ETL pipeline
Dataset source:
- USDA FoodData Central Downloadable Data: https://fdc.nal.usda.gov/download-datasets/
- USDA Foundation Foods documentation: https://fdc.nal.usda.gov/Foundation_Foods_Documentation/

Download the USDA Foundation Foods CSV archive from the official USDA site, extract it, and place the extracted files in `backend/data/raw/usda_foundation/`.

Place the extracted USDA Foundation Foods CSV files in `backend/data/raw/usda_foundation/`.

Required files:
- `food.csv`
- `food_category.csv`
- `nutrient.csv`
- `food_nutrient.csv`

Optional files:
- `food_portion.csv`
- `measure_unit.csv`

Transform only:
```bash
python -m app.etl transform-usda-foundation
```

Transform + load into the configured database:
```bash
python -m app.etl run-usda-foundation
```

Load a previously normalized CSV:
```bash
python -m app.etl load-clean-ingredients --clean-file backend/data/clean/usda_foundation/<file>.csv
```

Notes:
- The ETL writes normalized ingredient CSV artifacts to `backend/data/clean/usda_foundation/`.
- Pipeline execution state is recorded in the `etl_runs` table.
- Re-running the loader updates existing `ingredients` rows by name instead of creating duplicates.
- The current transform is intentionally strict: it keeps only `foundation_food` rows with complete `calories`, `protein`, `carbs`, and `fat` values, then deduplicates by normalized ingredient name.
- Because of that filtering, a full USDA Foundation Foods download can produce a much smaller clean output than the raw file size. In the current local run for this repository, the clean CSV contained 107 ingredient rows.

### 4. Configure environment
The backend reads configuration from `backend/.env`.

Default local configuration:
```env
DATABASE_URL=sqlite:///./pantry_to_plate.db
```
