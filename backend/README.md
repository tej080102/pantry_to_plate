# Sprout Recipe Developer — Backend

## Overview

The Sprout backend is a FastAPI-based service that powers an AI-driven system to reduce food waste and generate recipes from available ingredients. It provides the core data models, APIs, and storage layer required for ingredient management, pantry tracking, and recipe retrieval.

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
  - Nutritional metadata (calories, protein, etc.)
  - Shelf-life estimation for spoilage tracking

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

---

## Local Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt