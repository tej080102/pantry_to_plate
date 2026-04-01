import { apiRequest } from "./client";

export function fetchRecipes() {
  return apiRequest("/recipes");
}

export function fetchRecipe(recipeId) {
  return apiRequest(`/recipes/${recipeId}`);
}

export async function generateRecipeSuggestionsFromCatalog() {
  const recipes = await fetchRecipes();
  return Promise.all(recipes.map((recipe) => fetchRecipe(recipe.id)));
}
