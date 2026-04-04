import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _parse_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    PROJECT_NAME: str = "Pantry to Plate"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./pantry_to_plate.db",
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CORS_ALLOW_ORIGINS: list[str] = _parse_csv_env(
        "CORS_ALLOW_ORIGINS",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )
    GCP_PROJECT_ID: str | None = os.getenv("GCP_PROJECT_ID")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    GCS_UPLOAD_BUCKET: str | None = os.getenv("GCS_UPLOAD_BUCKET")
    GCS_RAW_BUCKET: str | None = os.getenv("GCS_RAW_BUCKET")
    GCS_CLEAN_BUCKET: str | None = os.getenv("GCS_CLEAN_BUCKET")
    GOOGLE_GENAI_USE_VERTEXAI: bool = _parse_bool_env("GOOGLE_GENAI_USE_VERTEXAI", True)
    VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "gemini_vertex")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "gemini-2.5-flash")
    PERCEPTION_ALLOW_LOCAL_FALLBACK: bool = _parse_bool_env(
        "PERCEPTION_ALLOW_LOCAL_FALLBACK",
        True,
    )
    RECIPE_MODEL: str | None = os.getenv("RECIPE_MODEL")


settings = Settings()
