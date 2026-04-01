import { apiRequest } from "./client";

export async function detectIngredientsFromImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest("/perception/detect", {
    method: "POST",
    body: formData,
  });
}
