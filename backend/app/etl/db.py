from __future__ import annotations

import app.models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.config import settings


def build_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine suitable for the configured backend."""
    resolved_database_url = database_url or settings.DATABASE_URL
    engine_kwargs = {"pool_pre_ping": True}
    if resolved_database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(resolved_database_url, **engine_kwargs)


def build_session_factory(database_url: str | None = None) -> tuple[Engine, sessionmaker]:
    """Return an engine and bound session factory."""
    engine = build_engine(database_url)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


def initialize_database(engine: Engine) -> None:
    """Create tables for local development and ETL workflows."""
    Base.metadata.create_all(bind=engine)
