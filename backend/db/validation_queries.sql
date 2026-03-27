-- Basic retrieval queries for Pantry to Plate schema validation.

-- 1. Get all recipes
SELECT
    id,
    title,
    estimated_cook_time_minutes,
    servings,
    created_at
FROM recipes
ORDER BY created_at DESC, id DESC;

-- 2. Get ingredients for a recipe
SELECT
    r.title,
    i.name AS ingredient_name,
    ri.quantity,
    ri.unit,
    ri.is_optional
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients i ON i.id = ri.ingredient_id
WHERE r.title = 'Simple Spinach Tomato Salad'
ORDER BY i.name;

-- 3. Get nutrition for a recipe by aggregating ingredient nutrition
SELECT
    r.title,
    ROUND(SUM(COALESCE(n.calories_per_100g, 0) * COALESCE(ri.quantity, 0) / 100.0)::numeric, 2) AS total_calories,
    ROUND(SUM(COALESCE(n.protein_per_100g, 0) * COALESCE(ri.quantity, 0) / 100.0)::numeric, 2) AS total_protein_g,
    ROUND(SUM(COALESCE(n.carbs_per_100g, 0) * COALESCE(ri.quantity, 0) / 100.0)::numeric, 2) AS total_carbs_g,
    ROUND(SUM(COALESCE(n.fat_per_100g, 0) * COALESCE(ri.quantity, 0) / 100.0)::numeric, 2) AS total_fat_g,
    ROUND(SUM(COALESCE(n.fiber_per_100g, 0) * COALESCE(ri.quantity, 0) / 100.0)::numeric, 2) AS total_fiber_g
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredient_nutrition n ON n.ingredient_id = ri.ingredient_id
WHERE r.title = 'Simple Spinach Tomato Salad'
GROUP BY r.title;

-- 4. Get pantry items that match recipe ingredients for a user
SELECT
    r.title,
    i.name AS ingredient_name,
    p.quantity AS pantry_quantity,
    p.unit AS pantry_unit,
    p.estimated_expiry_date
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN pantry_items p
    ON p.ingredient_id = i.id
   AND p.user_id = 'demo-user'
WHERE r.title = 'Simple Spinach Tomato Salad'
ORDER BY p.estimated_expiry_date NULLS LAST, i.name;

-- 5. Join recipes + ingredients + nutrition
SELECT
    r.title,
    i.name AS ingredient_name,
    ri.quantity,
    ri.unit,
    n.calories_per_100g,
    n.protein_per_100g,
    n.carbs_per_100g,
    n.fat_per_100g,
    n.fiber_per_100g
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN ingredient_nutrition n ON n.ingredient_id = i.id
ORDER BY r.title, i.name;
