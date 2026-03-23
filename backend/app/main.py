from fastapi import FastAPI

import app.models
from app.api.routes import ingredients_router, recipes_router
from app.core.config import settings
from app.core.database import Base, engine


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
)


@app.on_event("startup")
def create_tables() -> None:
    """Create tables locally until migrations are added."""
    Base.metadata.create_all(bind=engine)


app.include_router(ingredients_router)
app.include_router(recipes_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple health endpoint for load balancers and uptime checks."""
    return {"status": "ok", "service": "sprout-backend"}