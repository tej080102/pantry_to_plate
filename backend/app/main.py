from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models
from app.api.routes import ingredients_router, pantry_router, recipes_router
from app.core.config import settings
from app.core.database import Base, engine, ensure_pantry_item_schema_compatibility

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def create_tables() -> None:
    """Create tables locally until migrations are added."""
    Base.metadata.create_all(bind=engine)
    ensure_pantry_item_schema_compatibility(engine)


#(Cloud SQL check)
@app.get("/ingredients-test")
def test_db():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM ingredients LIMIT 10")).fetchall()
        return [dict(row._mapping) for row in rows]


# existing routers
app.include_router(ingredients_router)
app.include_router(pantry_router)
app.include_router(recipes_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "pantry_to_plate-backend"}
