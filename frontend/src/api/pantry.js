import { apiRequest } from "./client";

export function fetchPantryItems(userId, includeInactive = false) {
  const params = new URLSearchParams({
    user_id: userId,
    include_inactive: String(includeInactive),
  });
  return apiRequest(`/pantry?${params.toString()}`);
}

export function ingestPantry(payload) {
  return apiRequest("/pantry/ingest", {
    method: "POST",
    body: payload,
  });
}

export function updatePantryItem(id, payload) {
  return apiRequest(`/pantry/${id}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deletePantryItem(id) {
  return apiRequest(`/pantry/${id}`, {
    method: "DELETE",
  });
}

export function consumePantryItem(id, amount) {
  return apiRequest(`/pantry/${id}/consume`, {
    method: "POST",
    body: { amount },
  });
}
