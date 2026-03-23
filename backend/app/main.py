from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple health endpoint for load balancers and uptime checks."""
    return {"status": "ok", "service": "sprout-backend"}
