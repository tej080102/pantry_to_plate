from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


def build_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured database backend."""
    resolved_database_url = database_url or settings.DATABASE_URL
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if resolved_database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(resolved_database_url, **engine_kwargs)


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_pantry_item_schema_compatibility(target_engine: Engine) -> None:
    """Add BD-14 pantry columns to older local databases when they are missing."""
    inspector = inspect(target_engine)
    if "pantry_items" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("pantry_items")
    }
    missing_columns = []
    if "source_detected_name" not in existing_columns:
        missing_columns.append("ALTER TABLE pantry_items ADD COLUMN source_detected_name VARCHAR(255)")
    if "is_archived" not in existing_columns:
        missing_columns.append(
            "ALTER TABLE pantry_items ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE"
        )
    if "is_false_positive" not in existing_columns:
        missing_columns.append(
            "ALTER TABLE pantry_items ADD COLUMN is_false_positive BOOLEAN NOT NULL DEFAULT FALSE"
        )

    if not missing_columns:
        return

    with target_engine.begin() as connection:
        for statement in missing_columns:
            connection.execute(text(statement))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
