import { apiRequest } from "./client";

export function fetchRecipes() {
  return apiRequest("/recipes");
}

export function fetchRecipe(recipeId) {
  return apiRequest(`/recipes/${recipeId}`);
}

export function generateRecipes(payload) {
  return apiRequest("/recipes/generate", {
    method: "POST",
    body: payload,
  });
}
