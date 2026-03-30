from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.models import ETLRun


class ETLTracker:
    """Persist ETL execution state independently of the load transaction."""

    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def start_run(self, source_name: str, raw_path: Path | str) -> ETLRun:
        with self._session_factory() as session:
            run = ETLRun(
                run_date=date.today(),
                source_name=source_name,
                raw_gcs_path=str(raw_path),
                status="RUNNING",
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def mark_success(
        self,
        run_id: int,
        clean_path: Path | str,
        records_processed: int,
    ) -> None:
        with self._session_factory() as session:
            run = self._get_run(session, run_id)
            run.clean_gcs_path = str(clean_path)
            run.records_processed = records_processed
            run.status = "SUCCESS"
            run.error_message = None
            session.commit()

    def mark_failure(
        self,
        run_id: int,
        clean_path: Path | str | None,
        error_message: str,
    ) -> None:
        with self._session_factory() as session:
            run = self._get_run(session, run_id)
            run.clean_gcs_path = str(clean_path) if clean_path is not None else None
            run.status = "FAILED"
            run.error_message = error_message[:1000]
            session.commit()

    def _get_run(self, session: Session, run_id: int) -> ETLRun:
        run = session.query(ETLRun).filter(ETLRun.id == run_id).one()
        return run
