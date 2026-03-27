import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_FILE)


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "Pantry to Plate"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./pantry_to_plate.db",
    )


settings = Settings()
