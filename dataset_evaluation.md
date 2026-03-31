# Pantry to Plate — Dataset Evaluation & Selection for ETL Ingestion

## 1. Overview

This document evaluates publicly available food and nutrition datasets for ingestion into the Pantry to Plate ETL pipeline. The goal is to populate the Cloud SQL database with ingredient-level nutritional data, shelf-life data, and recipe content that supports FIFO spoilage ranking and grounded recipe generation.

**Evaluation criteria:**
- Relevance of data fields to the `ingredients`, `recipes`, and `recipe_ingredients` tables
- Completeness and data quality
- Format and accessibility (bulk download, API, licensing)
- Shelf-life data availability (critical for FIFO ranker)
- Scale (record count)

---

## 2. Datasets Evaluated

### Dataset 1: Open Food Facts (OFF)

| Property | Details |
|---|---|
| **URL** | https://world.openfoodfacts.org/data |
| **License** | Open Database License (ODbL) — free to use, share, and adapt |
| **Record Count** | ~3–4 million products from 150+ countries |
| **Update Frequency** | Continuous community contributions; daily delta exports available |
| **Bulk Download Formats** | MongoDB dump, JSONL, CSV (via advanced search), daily delta JSONL |
| **API Access** | REST API v2 (v3 in development); no API key required |
| **Download Size** | Full dump ~9 GB; filtered CSV subsets ~400 MB–716 MB |

#### 2.1.1 Relevant Data Fields

| Field | Column in OFF | Maps to Pantry to Plate Table |
|---|---|---|
| Product name | `product_name` | `ingredients.name` |
| Generic name | `generic_name` | `ingredients.name` (fallback) |
| Category | `categories_tags` | `ingredients.category` |
| Serving size | `serving_size` | `ingredients.standard_unit` (derived) |
| Energy (kcal) | `energy-kcal_100g` | `ingredients.calories_per_100g` |
| Protein | `proteins_100g` | `ingredients.protein_per_100g` |
| Carbohydrates | `carbohydrates_100g` | `ingredients.carbs_per_100g` |
| Fat | `fat_100g` | `ingredients.fat_per_100g` |
| Fiber | `fiber_100g` | `ingredients.fiber_per_100g` |
| Ingredients list | `ingredients_text` | `recipe_ingredients` (parsing required) |
| Storage conditions | `conservation_conditions` | Shelf-life scoring input (sparse) |
| Expiry / best-before | (not a structured field) | ❌ Not reliably available |

#### 2.1.2 Strengths
- Massive scale: millions of real-world food products
- Rich nutritional data per 100g — directly matches the `ingredients` schema
- Free, open license with no usage restrictions
- Multiple export formats; no API key required
- Community-maintained with active updates
- Global coverage including brand-name products

#### 2.1.3 Weaknesses
- **No structured shelf-life data** — `conservation_conditions` is a free-text field, not machine-readable
- Product-centric, not ingredient-centric: records represent packaged goods (e.g., "Heinz Ketchup"), not raw ingredients (e.g., "tomato")
- High noise and incompleteness: many records have missing or incorrectly entered fields
- `ingredients_text` is unstructured and requires NLP parsing to extract individual ingredients
- No recipe instructions — only ingredient lists on product labels
- Requires significant cleaning: unit normalization, alias resolution, deduplication

#### 2.1.4 Compatibility Assessment

| System Requirement | Compatibility |
|---|---|
| Ingredient nutritional data (per 100g macros) | ✅ Strong |
| Ingredient category classification | ✅ Available via `categories_tags` |
| Standard unit mapping | 🟡 Requires normalization |
| Shelf-life scoring | ❌ Not available in structured form |
| Recipe catalog with instructions | ❌ Not available |

---

### Dataset 2: USDA FoodData Central (FDC)

| Property | Details |
|---|---|
| **URL** | https://fdc.nal.usda.gov/ |
| **License** | Public domain (U.S. Government data — no copyright) |
| **Record Count** | ~1 million food items across all data types |
| **Update Frequency** | Annual releases; Foundation Foods updated April 2024 |
| **Bulk Download Formats** | CSV and JSON (full or abridged); per-data-type zip archives |
| **API Access** | REST API; requires free API key from api.data.gov; 1,000 requests/hour |
| **Download Size** | Per-type CSVs range from ~10 MB (Foundation) to ~500 MB (Branded) |

#### 2.2.1 FoodData Central Data Types

| Type | Description | Best For Pantry to Plate |
|---|---|---|
| **Foundation Foods** | Curated raw foods with enhanced nutrient profiles and sampling metadata | ✅ Primary — clean raw ingredient data |
| **SR Legacy** | Standard Reference (final 2018 release); 7,793 food items | ✅ Secondary — stable raw ingredient catalog |
| **FNDDS** | Food and Nutrient Database for Dietary Studies; consumption-focused | 🟡 Useful for common meal patterns |
| **Branded Foods** | Nutrient values from commercial product labels | ❌ Redundant with OFF |
| **Experimental Foods** | Research-grade, not production-ready | ❌ Skip |

#### 2.2.2 Relevant Data Fields

| Field | FDC Field | Maps to Pantry to Plate Table |
|---|---|---|
| Food name | `description` | `ingredients.name` |
| Food category | `foodCategory.description` | `ingredients.category` |
| Calories | Nutrient ID 1008 (`Energy`) | `ingredients.calories_per_100g` |
| Protein | Nutrient ID 1003 (`Protein`) | `ingredients.protein_per_100g` |
| Total fat | Nutrient ID 1004 (`Total lipid (fat)`) | `ingredients.fat_per_100g` |
| Carbohydrates | Nutrient ID 1005 (`Carbohydrate, by difference`) | `ingredients.carbs_per_100g` |
| Fiber | Nutrient ID 1079 (`Fiber, total dietary`) | `ingredients.fiber_per_100g` |
| Serving size | `servingSize` + `servingSizeUnit` | `ingredients.standard_unit` (derived) |
| Storage conditions | Not available as structured field | ❌ Not available |

#### 2.2.3 Strengths
- **Scientifically rigorous** — government-validated nutrient measurements, not self-reported
- **Raw ingredient focus** — Foundation Foods and SR Legacy cover basic foods (chicken breast, spinach, egg), not packaged products
- Highly complete nutritional profiles: 60+ nutrients including micros, minerals, vitamins
- Clean, well-structured CSV and JSON exports — low transformation overhead
- Public domain — no licensing restrictions
- Stable FDC IDs for reliable cross-referencing

#### 2.2.4 Weaknesses
- **No shelf-life data** — USDA does not publish storage duration data in FDC
- **No recipe instructions** — FDC is purely ingredient/nutrient-focused
- API rate-limited to 1,000 req/hr — bulk scraping requires using CSV downloads, not API
- SR Legacy is frozen at 2018 — Foundation Foods is preferred for current data
- Branded Foods (500 MB+) is large and partially redundant with OFF

#### 2.2.5 Compatibility Assessment

| System Requirement | Compatibility |
|---|---|
| Ingredient nutritional data (per 100g macros) | ✅ Excellent — scientifically accurate |
| Ingredient category classification | ✅ Available via `foodCategory` |
| Standard unit mapping | ✅ Clean `servingSize` + `servingSizeUnit` fields |
| Shelf-life scoring | ❌ Not available |
| Recipe catalog with instructions | ❌ Not available |

---

### Dataset 3 (Supplementary): Rule-Based Shelf-Life Reference

Since neither OFF nor FDC provides structured shelf-life data, the FIFO ranker requires a supplementary approach.

| Property | Details |
|---|---|
| **Approach** | Curated lookup table: `(ingredient_category, storage_method) → shelf_life_days` |
| **Source** | USDA Food Keeper App data (publicly available), StillTasty reference data, academic food science literature |
| **Format** | Static JSON / CSV seeded directly into Cloud SQL |
| **Record Count** | ~200–400 category-level rules covering common fresh ingredient types |
| **Maintenance** | Manual; updated as edge cases are discovered |

#### 3.1 Example Rule Schema

```json
{
  "category": "leafy_greens",
  "storage_method": "refrigerated",
  "shelf_life_days": 5,
  "notes": "Unwashed; bagged greens may last 7-10 days"
}
```

```json
{
  "category": "dairy_eggs",
  "storage_method": "refrigerated",
  "shelf_life_days": 21
}
```

This lookup is applied during the Transform stage (F2) to assign `estimated_shelf_life_days` to each ingredient record.

---

## 3. Comparative Summary

| Criterion | Open Food Facts | USDA FoodData Central | Shelf-Life Lookup |
|---|---|---|---|
| **Record count** | ~3-4M products | ~1M food items | ~200–400 rules |
| **Nutritional data quality** | 🟡 Variable (community) | ✅ High (lab-validated) | N/A |
| **Raw ingredient focus** | ❌ Mostly packaged goods | ✅ Strong (Foundation Foods) | ✅ Category-level |
| **Shelf-life data** | ❌ None (structured) | ❌ None | ✅ Primary source |
| **Recipe instructions** | ❌ None | ❌ None | N/A |
| **Bulk download** | ✅ JSONL / CSV / MongoDB | ✅ CSV / JSON per type | ✅ Static seed file |
| **API key required** | ❌ No | ✅ Yes (free) | N/A |
| **License** | ODbL (open) | Public domain | N/A |
| **Cleaning overhead** | 🔴 High | 🟢 Low | 🟢 Minimal |
| **Best use in Pantry to Plate** | Supplementary ingredient enrichment | Primary nutritional catalog | Shelf-life scoring |

---

## 4. Final Dataset Selection

### Primary: USDA FoodData Central — Foundation Foods + SR Legacy

**Rationale:**
- Scientifically validated nutrient values map cleanly to the `ingredients` schema
- Raw ingredient focus matches the app's detection targets (e.g., "egg", "spinach", "chicken breast")
- Low cleaning overhead — consistent units, structured categories, stable IDs
- Public domain — no licensing friction

**Ingestion plan:**
- Download Foundation Foods CSV from https://fdc.nal.usda.gov/download-foods.html
- Download SR Legacy CSV as a supplementary catalog for broader coverage
- Transform stage maps `description` → `name`, `foodCategory` → `category`, nutrient fields → per-100g macro columns
- Join shelf-life lookup on `category` to populate `estimated_shelf_life_days`

### Supplementary: Open Food Facts

**Rationale:**
- Fills gaps for processed or branded ingredients not covered by USDA raw foods
- Provides `categories_tags` for broader ingredient classification
- Useful for alias resolution during the Transform stage (e.g., "yogurt" vs "Greek yogurt")

**Ingestion plan:**
- Use filtered JSONL export (fresh foods category only) to limit noise
- Apply strict completeness filters: records missing `product_name`, `energy-kcal_100g`, or `proteins_100g` are dropped
- Deduplicate against USDA records by normalized name; USDA values take precedence on conflict

### Supplementary: Shelf-Life Lookup Table

**Rationale:**
- The only viable source of structured shelf-life data for the FIFO ranker
- Applied during Transform stage to all ingredient records

**Ingestion plan:**
- Seed as a static JSON file committed to the repo
- Applied in the Transform job: `category` → `estimated_shelf_life_days` and `storage_type`
- Unmatched categories default to a conservative 7-day fallback

---

## 5. Fields Selected for Ingestion

The following fields from the selected datasets map to the `ingredients` table in Cloud SQL:

| `ingredients` Column | USDA FDC Source | OFF Source | Shelf-Life Lookup |
|---|---|---|---|
| `name` | `description` | `product_name` / `generic_name` | — |
| `category` | `foodCategory.description` | `categories_tags[0]` | — |
| `standard_unit` | `servingSizeUnit` | Derived from `serving_size` | — |
| `calories_per_100g` | Nutrient ID 1008 | `energy-kcal_100g` | — |
| `protein_per_100g` | Nutrient ID 1003 | `proteins_100g` | — |
| `carbs_per_100g` | Nutrient ID 1005 | `carbohydrates_100g` | — |
| `fat_per_100g` | Nutrient ID 1004 | `fat_100g` | — |
| `fiber_per_100g` | Nutrient ID 1079 | `fiber_100g` | — |
| `estimated_shelf_life_days` | — | — | `shelf_life_days` (by category) |
| `storage_type` | — | — | `storage_method` (by category) |

---

## 6. Data Quality & Cleaning Notes

| Issue | Affected Dataset | Mitigation |
|---|---|---|
| Missing macro values | OFF (high), FDC (low) | Drop records where calories, protein, or carbs are null before load |
| Unit inconsistency | OFF (grams, oz, ml mixed) | Normalize all values to per-100g in Transform stage |
| Ingredient name aliases | Both | Build synonym map during Transform (e.g., "chicken" = "broiler") |
| Duplicate records | Both | Deduplicate by normalized lowercase name; prefer USDA on conflict |
| Non-food categories | OFF | Filter to food categories only; exclude cosmetics, pet food, etc. |
| HTML artifacts in text fields | OFF | Strip tags during cleaning pass |
| Sparse fresh-food coverage | USDA Foundation Foods | Supplement with SR Legacy and filtered OFF |

---

## 7. Acceptance Criteria Checklist

- [x] **At least 2 datasets evaluated** — Open Food Facts and USDA FoodData Central evaluated in detail; shelf-life lookup identified as required supplementary source
- [x] **Data fields relevant to recipes and nutrition identified** — Full field mapping in Section 5 with direct column-level alignment to the `ingredients` schema
- [x] **Data format and accessibility verified** — Bulk download formats, API access, licensing, and record counts confirmed for each dataset
- [x] **Final dataset(s) selected for ingestion** — USDA FDC (primary), OFF (supplementary, filtered), shelf-life lookup table (supplementary, static seed)
