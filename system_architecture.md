# Pantry to Plate — System Architecture & Data Flow

## 1. Executive Summary

Pantry to Plate is an AI-powered recipe generation platform that reduces food waste by detecting ingredients from fridge photos, ranking them by spoilage urgency, and generating grounded recipes. The system is built on GCP infrastructure with a Next.js frontend, FastAPI backend, Cloud SQL database, GCS object storage, and an AI layer combining computer vision with LLM-based generation.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                       │
│                          Next.js on Vercel                                       │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ Image Upload  │  │ Pantry Dashboard  │  │  Recipe Cards    │                   │
│  │    Page       │  │ (FIFO view)       │  │  (Nutrition +    │                   │
│  │              │  │                    │  │   Printable)     │                   │
│  └──────┬───────┘  └────────┬──────────┘  └────────┬─────────┘                   │
└─────────┼──────────────────┼──────────────────────┼─────────────────────────────┘
          │ Upload           │ Pantry API           │ Recipe API
          │ image            │ requests             │ requests
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND — FastAPI on Cloud Run                          │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │ /upload      │  │ /pantry          │  │ /recipes/match   │  │ /health     │  │
│  │  Image       │  │  FIFO Ranker     │  │  DB-first match  │  │             │  │
│  │  Endpoint    │  │  Endpoint        │  │  + LLM stitch    │  │             │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬──────────┘  └─────────────┘  │
│         │                   │                     │                              │
│         ▼                   ▼                     ▼                              │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ CV Service   │  │ Spoilage Ranker  │  │ Recipe Generator │                   │
│  │ (YOLO /      │  │ (shelf-life      │  │ (DB query →      │                   │
│  │  Gemini      │  │  lookup + FIFO   │  │  Gemini Pro →    │                   │
│  │  Vision)     │  │  sort)           │  │  JSON validate)  │                   │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬──────────┘                   │
└─────────┼──────────────────┼──────────────────────┼─────────────────────────────┘
          │                   │                     │
          ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                         │
│                                                                                 │
│  ┌──────────────────────────────┐     ┌──────────────────────────────────────┐  │
│  │      Cloud SQL (PostgreSQL)  │     │         GCS (Object Storage)         │  │
│  │                              │     │                                      │  │
│  │  • ingredients               │     │  Bucket: raw-scrapes/               │  │
│  │  • recipes                   │     │    └── {run_date}/payload.json      │  │
│  │  • recipe_ingredients        │     │                                      │  │
│  │  • pantry_items              │     │  Bucket: clean-data/                │  │
│  │  • etl_runs                  │     │    └── {run_date}/normalized.json   │  │
│  │                              │     │                                      │  │
│  └──────────────────────────────┘     │  Bucket: user-uploads/              │  │
│                  ▲                     │    └── {user_id}/{timestamp}.jpg    │  │
│                  │                     └──────────────────────────────────────┘  │
│                  │                                    ▲                          │
└──────────────────┼────────────────────────────────────┼─────────────────────────┘
                   │                                    │
                   │  Bulk insert clean data            │  Write raw scrapes
                   │                                    │
┌──────────────────┼────────────────────────────────────┼─────────────────────────┐
│                  │       ETL PIPELINE (Cloud Run Jobs)│                          │
│                  │                                    │                          │
│  ┌───────────────┴──────────┐  ┌─────────────────────┴────────────────────────┐ │
│  │  F3: Load to Cloud SQL   │  │  F1: Scrapy Crawler → Raw GCS               │ │
│  │  (transactional insert,  │  │  (Open Food Facts, USDA; weekly schedule)    │ │
│  │   ETLRun logging)        │  │                                              │ │
│  └──────────────────────────┘  └──────────────────┬───────────────────────────┘ │
│                 ▲                                  │                             │
│                 │                                  ▼                             │
│  ┌──────────────┴──────────────────────────────────────────────────────────────┐ │
│  │  F2: Transform & Shelf-Life Scoring Engine                                 │ │
│  │  (unit standardization, alias resolution, shelf-life calc → clean GCS)     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  Trigger: Cloud Scheduler (weekly cron)                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. System Components

### 3.1 Frontend — Next.js (Vercel)

| Component | Responsibility |
|---|---|
| **Image Upload Page** | Capture / upload fridge photo, display detection results |
| **Pantry Dashboard** | Show ingredient cards color-coded by spoilage urgency (green → yellow → red), sortable expiry timeline, manual adjustment controls |
| **Recipe Cards** | Display generated recipes with nutrition labels, expiry-urgency badges, missing-ingredient flags; printable / shareable view |

Communication: All frontend ↔ backend communication is via REST API (JSON over HTTPS).

---

### 3.2 Backend — FastAPI (Cloud Run)

| Service | Responsibility |
|---|---|
| **Image Endpoint** (`/upload`) | Accepts fridge photo, stores to GCS, delegates to CV model, returns detected ingredient list with confidence scores |
| **Pantry Endpoint** (`/pantry`) | Cross-references detected ingredients against Cloud SQL shelf-life data, runs FIFO spoilage ranking, returns annotated priority list |
| **Recipe Endpoint** (`/recipes/match`) | Runs database-first recipe matching (weighted overlap with priority boost), sends skeleton to LLM, validates JSON output, enriches with per-serving nutrition |
| **CRUD Endpoints** (`/ingredients`, `/recipes`, `/health`) | Standard data access and health checks |

---

### 3.3 AI Layer

| Model | Purpose | Integration |
|---|---|---|
| **YOLOv8** (local) or **Gemini Vision** (API) | Detect raw ingredients from fridge image | Called by `/upload` endpoint; returns structured item list with confidence scores |
| **Gemini Pro** (API) or **Llama 3** (self-hosted) | Generate step-by-step recipes in strict JSON schema from structured inputs | Called by `/recipes/match` after DB matching; receives recipe skeleton + ranked ingredients; returns validated JSON |

---

### 3.4 Data Layer — Cloud SQL (PostgreSQL)

| Table | Key Columns | Role |
|---|---|---|
| `ingredients` | name, category, nutritional macros (per 100g), estimated_shelf_life_days, storage_type | Master ingredient catalog with nutritional + shelf-life data |
| `recipes` | title, source_name, source_url, instructions, cook_time, servings | Scraped recipe catalog |
| `recipe_ingredients` | recipe_id → ingredient_id, quantity, unit | Junction table linking recipes to ingredients |
| `pantry_items` | user_id, ingredient_id, quantity, date_added, estimated_expiry_date, is_priority, detected_confidence | Per-user pantry state with spoilage tracking |
| `etl_runs` | run_date, source_name, raw/clean GCS paths, records_processed, status, error_message | Pipeline observability log |

---

### 3.5 Object Storage — GCS

| Bucket / Prefix | Content | Lifecycle |
|---|---|---|
| `raw-scrapes/{run_date}/` | Raw HTML/JSON payloads from Scrapy | Immutable data lake; retained for audit |
| `clean-data/{run_date}/` | Normalized JSON after transform stage | Read by the Cloud SQL loader |
| `user-uploads/{user_id}/` | Uploaded fridge images | Referenced by CV detection endpoint |

---

### 3.6 ETL Pipeline — Cloud Run Jobs

Three sequential stages triggered weekly via Cloud Scheduler:

1. **Scrape** — Scrapy crawlers pull from Open Food Facts + USDA → write to `raw-scrapes/`
2. **Transform** — Clean, normalize, compute shelf-life scores → write to `clean-data/`
3. **Load** — Transactional bulk-insert into Cloud SQL; log execution in `etl_runs`

---

## 4. Data Flow Diagrams

### 4.1 Image Upload → Recipe Generation (Primary User Flow)

```
User                Frontend              Backend                AI Layer            Cloud SQL         GCS
 │                    │                      │                      │                   │               │
 │  1. Take photo     │                      │                      │                   │               │
 ├───────────────────►│                      │                      │                   │               │
 │                    │  2. POST /upload      │                      │                   │               │
 │                    │      (image file)     │                      │                   │               │
 │                    ├─────────────────────►│                      │                   │               │
 │                    │                      │  3. Store image       │                   │               │
 │                    │                      ├──────────────────────┼───────────────────┼──────────────►│
 │                    │                      │                      │                   │  user-uploads/ │
 │                    │                      │  4. Detect            │                   │               │
 │                    │                      │     ingredients       │                   │               │
 │                    │                      ├─────────────────────►│                   │               │
 │                    │                      │                      │                   │               │
 │                    │                      │  5. Detected items    │                   │               │
 │                    │                      │◄─────────────────────┤                   │               │
 │                    │                      │                      │                   │               │
 │                    │  6. Ingredient list   │                      │                   │               │
 │                    │◄─────────────────────┤                      │                   │               │
 │  7. Show results   │                      │                      │                   │               │
 │◄───────────────────┤                      │                      │                   │               │
 │                    │                      │                      │                   │               │
 │  8. Confirm &      │                      │                      │                   │               │
 │     request recipes│                      │                      │                   │               │
 ├───────────────────►│                      │                      │                   │               │
 │                    │  9. POST /pantry      │                      │                   │               │
 │                    │     (ingredients)     │                      │                   │               │
 │                    ├─────────────────────►│                      │                   │               │
 │                    │                      │  10. Lookup shelf-life│                   │               │
 │                    │                      ├──────────────────────┼──────────────────►│               │
 │                    │                      │  11. Shelf-life data  │                   │               │
 │                    │                      │◄─────────────────────┼───────────────────┤               │
 │                    │                      │                      │                   │               │
 │                    │                      │  12. FIFO rank &      │                   │               │
 │                    │                      │      flag priority    │                   │               │
 │                    │                      │                      │                   │               │
 │                    │  13. Ranked pantry    │                      │                   │               │
 │                    │◄─────────────────────┤                      │                   │               │
 │  14. Pantry view   │                      │                      │                   │               │
 │◄───────────────────┤                      │                      │                   │               │
 │                    │                      │                      │                   │               │
 │  15. Generate      │                      │                      │                   │               │
 │      recipes       │                      │                      │                   │               │
 ├───────────────────►│                      │                      │                   │               │
 │                    │ 16. POST /recipes/    │                      │                   │               │
 │                    │     match             │                      │                   │               │
 │                    ├─────────────────────►│                      │                   │               │
 │                    │                      │  17. DB-first match   │                   │               │
 │                    │                      ├──────────────────────┼──────────────────►│               │
 │                    │                      │  18. Recipe skeletons │                   │               │
 │                    │                      │◄─────────────────────┼───────────────────┤               │
 │                    │                      │                      │                   │               │
 │                    │                      │  19. LLM stitch       │                   │               │
 │                    │                      │      (skeleton +      │                   │               │
 │                    │                      │       ranked list)    │                   │               │
 │                    │                      ├─────────────────────►│                   │               │
 │                    │                      │  20. Structured JSON  │                   │               │
 │                    │                      │◄─────────────────────┤                   │               │
 │                    │                      │                      │                   │               │
 │                    │                      │  21. Enrich with      │                   │               │
 │                    │                      │      per-serving      │                   │               │
 │                    │                      │      nutrition        │                   │               │
 │                    │                      ├──────────────────────┼──────────────────►│               │
 │                    │                      │◄─────────────────────┼───────────────────┤               │
 │                    │                      │                      │                   │               │
 │                    │  22. Final recipes    │                      │                   │               │
 │                    │      (JSON + macros)  │                      │                   │               │
 │                    │◄─────────────────────┤                      │                   │               │
 │  23. Recipe cards  │                      │                      │                   │               │
 │◄───────────────────┤                      │                      │                   │               │
```

---

### 4.2 ETL Pipeline Flow

```
Cloud Scheduler (weekly cron)
        │
        ▼
┌───────────────┐      ┌──────────┐
│  F1: Scrapy   │─────►│  GCS     │
│  Crawler      │      │  raw-    │
│  (Cloud Run   │      │  scrapes/│
│   Job)        │      └────┬─────┘
└───────────────┘           │
                            ▼
                   ┌───────────────┐      ┌──────────┐
                   │  F2: Transform│─────►│  GCS     │
                   │  & Shelf-Life │      │  clean-  │
                   │  Scoring      │      │  data/   │
                   │  (Cloud Run   │      └────┬─────┘
                   │   Job)        │           │
                   └───────────────┘           │
                                               ▼
                                     ┌───────────────┐      ┌───────────┐
                                     │  F3: DB Load  │─────►│ Cloud SQL │
                                     │  (Cloud Run   │      │ (Postgres)│
                                     │   Job)        │      └───────────┘
                                     └───────┬───────┘
                                             │
                                             ▼
                                     ┌───────────────┐
                                     │  etl_runs log │
                                     │  (status,     │
                                     │   record count│
                                     │   error msg)  │
                                     └───────────────┘
```

---

## 5. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| **Frontend** | Next.js on Vercel | SSR/SSG support, fast iteration, seamless Vercel deployment |
| **Backend** | FastAPI on Cloud Run | Async-ready, auto-generated OpenAPI docs, containerized scaling |
| **Database** | Cloud SQL (PostgreSQL) | Managed relational DB, strong JSON support, GCP-native |
| **Object Storage** | Google Cloud Storage (GCS) | Immutable data lake for raw scrapes + user image uploads |
| **Computer Vision** | YOLOv8 (local) / Gemini Vision (API) | YOLOv8 for offline accuracy; Gemini Vision for faster API-based prototyping |
| **LLM** | Gemini Pro (API) / Llama 3 (self-hosted) | Gemini for MVP speed; Llama 3 for future infra control |
| **ETL Orchestration** | Cloud Run Jobs + Cloud Scheduler | Serverless batch processing, weekly cron trigger |
| **Web Scraping** | Scrapy | Configurable, async, robots.txt-compliant crawling |
| **ORM** | SQLAlchemy 2.0 | Type-safe mapped columns, async-capable, DB-agnostic |
| **CI/CD** | GitHub Actions | Automated test → build → deploy pipeline to Cloud Run |
| **Project Mgmt** | Jira Kanban | Epic/Story tracking with velocity metrics |

---

## 6. Key Design Decisions

### 6.1 Database-First Before LLM
Recipes are matched from the scraped database **before** the LLM is called. The LLM receives a factual skeleton, not a blank prompt. This dramatically reduces hallucination risk and keeps outputs grounded.

### 6.2 GCS as Immutable Data Lake
Raw scrapes are never modified or deleted in GCS. The transformation stage writes to a separate prefix. This preserves full audit history and allows re-processing from raw data if cleaning rules change.

### 6.3 FIFO Spoilage as a First-Class Concept
Spoilage priority isn't an afterthought — it drives the entire pipeline. The FIFO ranker runs before recipe matching, and priority ingredients receive scoring boosts in the recipe query. The frontend surfaces urgency through color-coding.

### 6.4 Strict JSON Schema from LLM
The LLM is instructed to return a fixed JSON schema (title, ingredients with quantities, steps, cook time). The backend validates the output and retries on parse failure. This ensures the frontend can reliably render recipe cards without fragile text parsing.

### 6.5 Separation of CV and LLM Models
The computer vision model (ingredient detection) and the language model (recipe generation) are completely decoupled. This allows independent model swapping — e.g., upgrading from YOLOv8 to Gemini Vision without touching any recipe logic.

---

## 7. Security & Infrastructure Notes

- **User uploads** are stored in a GCS bucket with per-user path isolation (`user-uploads/{user_id}/`)
- **Cloud SQL** connections use the Cloud SQL Auth Proxy for IAM-based access
- **Cloud Run** services are deployed with minimum instance counts and concurrency limits
- **API keys** (Gemini, etc.) are stored in GCP Secret Manager and injected as environment variables
- **CORS** is configured on the FastAPI backend to allow only the Vercel frontend origin

---

## 8. Acceptance Criteria Checklist

- [x] **All major system components identified** — Frontend, Backend, AI Layer, Data Layer (Cloud SQL + GCS), ETL Pipeline
- [x] **Data flow between components clearly defined** — Primary user flow (image → detection → ranking → recipe) and ETL pipeline flow documented with sequence diagrams
- [x] **Architecture diagram created** — Full system diagram in Section 2
- [x] **Technology stack decisions documented** — Complete table in Section 5 with justifications
