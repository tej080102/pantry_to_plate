function normalizeName(value) {
  return value.trim().toLowerCase();
}

function nutritionTotal(recipeIngredient, key) {
  const nutrition = recipeIngredient.ingredient?.nutrition;
  if (!nutrition || recipeIngredient.quantity == null || !recipeIngredient.unit) {
    return null;
  }

  const unit = normalizeName(recipeIngredient.unit);
  if (!["g", "gram", "grams", "ml"].includes(unit)) {
    return null;
  }

  return ((nutrition[key] || 0) * recipeIngredient.quantity) / 100;
}

export function estimateRecipeNutrition(recipe) {
  const totals = {
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0,
    fiber: 0,
  };

  let usableRows = 0;
  for (const item of recipe.recipe_ingredients || []) {
    const calories = nutritionTotal(item, "calories_per_100g");
    const protein = nutritionTotal(item, "protein_per_100g");
    const carbs = nutritionTotal(item, "carbs_per_100g");
    const fat = nutritionTotal(item, "fat_per_100g");
    const fiber = nutritionTotal(item, "fiber_per_100g");

    if ([calories, protein, carbs, fat, fiber].every((value) => value == null)) {
      continue;
    }

    usableRows += 1;
    totals.calories += calories || 0;
    totals.protein += protein || 0;
    totals.carbs += carbs || 0;
    totals.fat += fat || 0;
    totals.fiber += fiber || 0;
  }

  if (usableRows === 0) {
    return null;
  }

  return {
    calories: Math.round(totals.calories),
    protein: Number(totals.protein.toFixed(1)),
    carbs: Number(totals.carbs.toFixed(1)),
    fat: Number(totals.fat.toFixed(1)),
    fiber: Number(totals.fiber.toFixed(1)),
    note: "Approximate from ingredient nutrition rows with gram/ml quantities.",
  };
}

export function rankRecipesAgainstPantry(recipes, pantryItems) {
  const activePantry = pantryItems.filter(
    (item) => !item.is_archived && !item.is_false_positive,
  );
  const pantryByName = new Map(
    activePantry.map((item) => [normalizeName(item.ingredient.name), item]),
  );

  return recipes
    .map((recipe) => {
      const recipeIngredients = recipe.recipe_ingredients || [];
      const matched = [];
      const missing = [];

      for (const recipeIngredient of recipeIngredients) {
        const ingredientName = recipeIngredient.ingredient?.name || "Unknown ingredient";
        const pantryItem = pantryByName.get(normalizeName(ingredientName));
        if (pantryItem) {
          matched.push({
            pantryItem,
            recipeIngredient,
          });
        } else {
          missing.push(ingredientName);
        }
      }

      const urgentMatches = matched.filter(({ pantryItem }) =>
        ["HIGH", "MEDIUM"].includes(pantryItem.priority_bucket),
      );
      const score = matched.length * 3 + urgentMatches.length * 2 - missing.length;

      return {
        recipe,
        matched,
        missing,
        urgentMatches,
        score,
        nutritionEstimate: estimateRecipeNutrition(recipe),
      };
    })
    .sort((left, right) => right.score - left.score || left.missing.length - right.missing.length);
}
