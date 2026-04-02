export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export async function apiRequest(path, options = {}) {
  const { body, headers, ...rest } = options;
  const requestHeaders = new Headers(headers || {});
  const requestOptions = {
    ...rest,
    headers: requestHeaders,
  };

  if (body instanceof FormData) {
    requestOptions.body = body;
  } else if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
    requestOptions.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, requestOptions);
  const contentType = response.headers.get("content-type") || "";

  let payload = null;
  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    const text = await response.text();
    payload = text ? { detail: text } : null;
  }

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      `${response.status} ${response.statusText}`;
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}
