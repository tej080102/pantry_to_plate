from __future__ import annotations

import app.models  # noqa: F401
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, build_engine as build_app_engine


def build_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine suitable for the configured backend."""
    return build_app_engine(database_url)


def build_session_factory(database_url: str | None = None) -> tuple[Engine, sessionmaker]:
    """Return an engine and bound session factory."""
    engine = build_engine(database_url)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


def initialize_database(engine: Engine) -> None:
    """Create tables for local development and ETL workflows."""
    Base.metadata.create_all(bind=engine)
