import os

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "Pantry to Plate"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./pantry_to_plate.db",
    )


settings = Settings()
