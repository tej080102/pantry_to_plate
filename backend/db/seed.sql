-- Sample data for Pantry to Plate schema validation.
-- Intended for local development or a fresh demo database.

BEGIN;

INSERT INTO ingredients (name, category, standard_unit, estimated_shelf_life_days, storage_type)
SELECT 'Spinach', 'Vegetable', 'g', 5, 'refrigerated'
WHERE NOT EXISTS (
    SELECT 1 FROM ingredients WHERE name = 'Spinach'
);

INSERT INTO ingredients (name, category, standard_unit, estimated_shelf_life_days, storage_type)
SELECT 'Tomato', 'Vegetable', 'g', 7, 'counter'
WHERE NOT EXISTS (
    SELECT 1 FROM ingredients WHERE name = 'Tomato'
);

INSERT INTO ingredients (name, category, standard_unit, estimated_shelf_life_days, storage_type)
SELECT 'Olive Oil', 'Pantry', 'ml', 365, 'pantry'
WHERE NOT EXISTS (
    SELECT 1 FROM ingredients WHERE name = 'Olive Oil'
);

INSERT INTO ingredient_nutrition (
    ingredient_id,
    calories_per_100g,
    protein_per_100g,
    carbs_per_100g,
    fat_per_100g,
    fiber_per_100g
)
SELECT id, 23.0, 2.9, 3.6, 0.4, 2.2
FROM ingredients
WHERE name = 'Spinach'
ON CONFLICT (ingredient_id) DO NOTHING;

INSERT INTO ingredient_nutrition (
    ingredient_id,
    calories_per_100g,
    protein_per_100g,
    carbs_per_100g,
    fat_per_100g,
    fiber_per_100g
)
SELECT id, 18.0, 0.9, 3.9, 0.2, 1.2
FROM ingredients
WHERE name = 'Tomato'
ON CONFLICT (ingredient_id) DO NOTHING;

INSERT INTO ingredient_nutrition (
    ingredient_id,
    calories_per_100g,
    protein_per_100g,
    carbs_per_100g,
    fat_per_100g,
    fiber_per_100g
)
SELECT id, 884.0, 0.0, 0.0, 100.0, 0.0
FROM ingredients
WHERE name = 'Olive Oil'
ON CONFLICT (ingredient_id) DO NOTHING;

INSERT INTO recipes (
    title,
    source_name,
    source_url,
    instructions,
    estimated_cook_time_minutes,
    servings
)
SELECT
    'Simple Spinach Tomato Salad',
    'pantry_to_plate_demo',
    'https://example.com/spinach-tomato-salad',
    'Combine chopped spinach and tomato, then drizzle with olive oil.',
    10,
    2
WHERE NOT EXISTS (
    SELECT 1 FROM recipes WHERE title = 'Simple Spinach Tomato Salad'
);

INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, is_optional)
SELECT r.id, i.id, 100, 'g', FALSE
FROM recipes r
JOIN ingredients i ON i.name = 'Spinach'
WHERE r.title = 'Simple Spinach Tomato Salad'
ON CONFLICT (recipe_id, ingredient_id) DO NOTHING;

INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, is_optional)
SELECT r.id, i.id, 150, 'g', FALSE
FROM recipes r
JOIN ingredients i ON i.name = 'Tomato'
WHERE r.title = 'Simple Spinach Tomato Salad'
ON CONFLICT (recipe_id, ingredient_id) DO NOTHING;

INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, is_optional)
SELECT r.id, i.id, 15, 'ml', FALSE
FROM recipes r
JOIN ingredients i ON i.name = 'Olive Oil'
WHERE r.title = 'Simple Spinach Tomato Salad'
ON CONFLICT (recipe_id, ingredient_id) DO NOTHING;

INSERT INTO pantry_items (
    user_id,
    ingredient_id,
    quantity,
    unit,
    detected_confidence,
    date_added,
    estimated_expiry_date,
    is_priority
)
SELECT 'demo-user', i.id, 200, 'g', 0.98, CURRENT_DATE, CURRENT_DATE + INTERVAL '3 day', TRUE
FROM ingredients i
WHERE i.name = 'Spinach'
AND NOT EXISTS (
    SELECT 1
    FROM pantry_items p
    WHERE p.user_id = 'demo-user'
      AND p.ingredient_id = i.id
      AND p.estimated_expiry_date = CURRENT_DATE + INTERVAL '3 day'
);

INSERT INTO pantry_items (
    user_id,
    ingredient_id,
    quantity,
    unit,
    detected_confidence,
    date_added,
    estimated_expiry_date,
    is_priority
)
SELECT 'demo-user', i.id, 4, 'count', 0.94, CURRENT_DATE, CURRENT_DATE + INTERVAL '5 day', FALSE
FROM ingredients i
WHERE i.name = 'Tomato'
AND NOT EXISTS (
    SELECT 1
    FROM pantry_items p
    WHERE p.user_id = 'demo-user'
      AND p.ingredient_id = i.id
      AND p.estimated_expiry_date = CURRENT_DATE + INTERVAL '5 day'
);

INSERT INTO pantry_items (
    user_id,
    ingredient_id,
    quantity,
    unit,
    detected_confidence,
    date_added,
    estimated_expiry_date,
    is_priority
)
SELECT 'demo-user', i.id, 250, 'ml', 0.99, CURRENT_DATE, CURRENT_DATE + INTERVAL '120 day', FALSE
FROM ingredients i
WHERE i.name = 'Olive Oil'
AND NOT EXISTS (
    SELECT 1
    FROM pantry_items p
    WHERE p.user_id = 'demo-user'
      AND p.ingredient_id = i.id
      AND p.estimated_expiry_date = CURRENT_DATE + INTERVAL '120 day'
);

COMMIT;
