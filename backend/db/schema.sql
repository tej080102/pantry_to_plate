-- Pantry to Plate relational schema
-- PostgreSQL / Cloud SQL compatible

BEGIN;

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100),
    standard_unit VARCHAR(50),
    estimated_shelf_life_days INTEGER,
    storage_type VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ingredients_name ON ingredients (name);

CREATE TABLE IF NOT EXISTS ingredient_nutrition (
    id SERIAL PRIMARY KEY,
    ingredient_id INTEGER NOT NULL UNIQUE REFERENCES ingredients(id) ON DELETE CASCADE,
    calories_per_100g DOUBLE PRECISION CHECK (calories_per_100g >= 0),
    protein_per_100g DOUBLE PRECISION CHECK (protein_per_100g >= 0),
    carbs_per_100g DOUBLE PRECISION CHECK (carbs_per_100g >= 0),
    fat_per_100g DOUBLE PRECISION CHECK (fat_per_100g >= 0),
    fiber_per_100g DOUBLE PRECISION CHECK (fiber_per_100g >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ingredient_nutrition_ingredient_id
    ON ingredient_nutrition (ingredient_id);

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_name VARCHAR(255),
    source_url VARCHAR(500),
    instructions TEXT,
    estimated_cook_time_minutes INTEGER,
    servings INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_recipes_title ON recipes (title);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity DOUBLE PRECISION CHECK (quantity >= 0),
    unit VARCHAR(50),
    is_optional BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_recipe_ingredients_recipe_ingredient UNIQUE (recipe_id, ingredient_id)
);

CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe_id
    ON recipe_ingredients (recipe_id);

CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_ingredient_id
    ON recipe_ingredients (ingredient_id);

CREATE TABLE IF NOT EXISTS pantry_items (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity DOUBLE PRECISION CHECK (quantity >= 0),
    unit VARCHAR(50),
    detected_confidence DOUBLE PRECISION,
    date_added DATE,
    estimated_expiry_date DATE,
    is_priority BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pantry_items_detected_confidence_range
        CHECK (
            detected_confidence IS NULL
            OR (detected_confidence >= 0 AND detected_confidence <= 1)
        )
);

CREATE INDEX IF NOT EXISTS ix_pantry_items_user_id ON pantry_items (user_id);
CREATE INDEX IF NOT EXISTS ix_pantry_items_ingredient_id ON pantry_items (ingredient_id);
CREATE INDEX IF NOT EXISTS ix_pantry_items_estimated_expiry_date
    ON pantry_items (estimated_expiry_date);
CREATE INDEX IF NOT EXISTS ix_pantry_items_user_id_estimated_expiry_date
    ON pantry_items (user_id, estimated_expiry_date);

CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    raw_gcs_path VARCHAR(500),
    clean_gcs_path VARCHAR(500),
    records_processed INTEGER,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_etl_runs_run_date ON etl_runs (run_date);
CREATE INDEX IF NOT EXISTS ix_etl_runs_source_name ON etl_runs (source_name);
CREATE INDEX IF NOT EXISTS ix_etl_runs_status ON etl_runs (status);

COMMIT;
