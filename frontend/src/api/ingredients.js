import { apiRequest } from "./client";

export function fetchIngredients() {
  return apiRequest("/ingredients");
}
