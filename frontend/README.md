# Pantry to Plate Frontend

This frontend is a React + Vite app that integrates with the current FastAPI backend.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173`.

## Backend URL configuration

Set the backend base URL with:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

You can provide it in your shell before starting Vite, or through a local Vite env file if you prefer.

## Current backend integrations

- `GET /health`
- `GET /ingredients`
- `POST /perception/detect`
- `POST /pantry/ingest`
- `GET /pantry`
- `PATCH /pantry/{id}`
- `DELETE /pantry/{id}`
- `POST /pantry/{id}/consume`
- `POST /pantry/archive-expired`
- `GET /recipes`
- `GET /recipes/{id}`

## Fallback behavior

One product flow is not yet fully implemented in the backend on this branch:

- recipe generation at `/recipes/generate`

The frontend also includes a resilience fallback for perception if the backend provider is unavailable or misconfigured.

The frontend handles those gaps by:

- falling back to manual or sample detections when image detection fails
- ranking recipe suggestions from the existing recipe catalog and current pantry state

That keeps the demo usable without pretending those backend routes exist.
