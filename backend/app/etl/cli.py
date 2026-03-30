from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from app.etl.db import build_session_factory, initialize_database
from app.etl.load import load_clean_ingredients, load_ingredient_records
from app.etl.tracking import ETLTracker
from app.etl.transform import transform_usda_foundation


LOGGER = logging.getLogger("app.etl")
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = BACKEND_DIR / "data" / "raw" / "usda_foundation"
DEFAULT_CLEAN_DIR = BACKEND_DIR / "data" / "clean" / "usda_foundation"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pantry to Plate ETL utilities")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Defaults to DATABASE_URL/app settings.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level for ETL execution.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-usda-foundation",
        help="Validate, transform, write a clean CSV artifact, and load ingredients into the database.",
    )
    _add_usda_args(run_parser)

    transform_parser = subparsers.add_parser(
        "transform-usda-foundation",
        help="Validate USDA Foundation files and write a normalized clean CSV artifact.",
    )
    _add_usda_args(transform_parser)

    load_parser = subparsers.add_parser(
        "load-clean-ingredients",
        help="Load a previously generated normalized ingredient CSV into the database.",
    )
    load_parser.add_argument("--clean-file", required=True, help="Path to normalized ingredient CSV.")

    return parser


def _add_usda_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing extracted USDA Foundation CSV files.",
    )
    parser.add_argument(
        "--clean-dir",
        default=str(DEFAULT_CLEAN_DIR),
        help="Directory where normalized CSV files are written.",
    )
    parser.add_argument(
        "--output-file",
        default=None,
        help="Optional explicit normalized CSV output path.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    if args.command == "run-usda-foundation":
        return _run_usda_foundation(args)
    if args.command == "transform-usda-foundation":
        return _transform_usda_foundation(args)
    if args.command == "load-clean-ingredients":
        return _load_clean_ingredients(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_usda_foundation(args: argparse.Namespace) -> int:
    engine, session_factory = build_session_factory(args.database_url)
    initialize_database(engine)
    tracker = ETLTracker(session_factory)

    raw_dir = Path(args.raw_dir).resolve()
    clean_output = _resolve_clean_output(args.clean_dir, args.output_file)
    run = tracker.start_run(source_name="usda_foundation", raw_path=raw_dir)
    LOGGER.info("ETL run started: run_id=%s source=%s raw_dir=%s", run.id, run.source_name, raw_dir)

    try:
        LOGGER.info("Raw validation + transform started")
        batch, transform_stats = transform_usda_foundation(raw_dir=raw_dir, output_path=clean_output)
        LOGGER.info(
            "Transform complete: rows_read=%s rows_dropped=%s rows_deduplicated=%s rows_written=%s clean_output=%s",
            transform_stats.rows_read,
            transform_stats.rows_dropped,
            transform_stats.rows_deduplicated,
            transform_stats.rows_written,
            clean_output,
        )

        LOGGER.info("Database load started")
        load_stats = load_ingredient_records(batch.ingredients, session_factory)
        LOGGER.info(
            "Database load complete: processed=%s inserted=%s updated=%s",
            load_stats.processed,
            load_stats.inserted,
            load_stats.updated,
        )
        tracker.mark_success(run_id=run.id, clean_path=clean_output, records_processed=load_stats.processed)
        LOGGER.info("ETL run succeeded: run_id=%s", run.id)
        return 0
    except Exception as exc:
        LOGGER.exception("ETL run failed: run_id=%s error=%s", run.id, exc)
        tracker.mark_failure(run_id=run.id, clean_path=clean_output, error_message=str(exc))
        return 1
    finally:
        engine.dispose()


def _transform_usda_foundation(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir).resolve()
    clean_output = _resolve_clean_output(args.clean_dir, args.output_file)
    LOGGER.info("Transform started: raw_dir=%s", raw_dir)
    batch, stats = transform_usda_foundation(raw_dir=raw_dir, output_path=clean_output)
    LOGGER.info(
        "Transform complete: rows_read=%s rows_dropped=%s rows_deduplicated=%s rows_written=%s clean_output=%s",
        stats.rows_read,
        stats.rows_dropped,
        stats.rows_deduplicated,
        stats.rows_written,
        clean_output,
    )
    LOGGER.debug("Transformed ingredient count: %s", len(batch.ingredients))
    return 0


def _load_clean_ingredients(args: argparse.Namespace) -> int:
    engine, session_factory = build_session_factory(args.database_url)
    initialize_database(engine)
    tracker = ETLTracker(session_factory)

    clean_file = Path(args.clean_file).resolve()
    run = tracker.start_run(source_name="clean_ingredient_csv", raw_path=clean_file)
    LOGGER.info("Clean load started: run_id=%s clean_file=%s", run.id, clean_file)

    try:
        load_stats = load_clean_ingredients(clean_file, session_factory)
        tracker.mark_success(run_id=run.id, clean_path=clean_file, records_processed=load_stats.processed)
        LOGGER.info(
            "Clean load complete: run_id=%s processed=%s inserted=%s updated=%s",
            run.id,
            load_stats.processed,
            load_stats.inserted,
            load_stats.updated,
        )
        return 0
    except Exception as exc:
        LOGGER.exception("Clean load failed: run_id=%s error=%s", run.id, exc)
        tracker.mark_failure(run_id=run.id, clean_path=clean_file, error_message=str(exc))
        return 1
    finally:
        engine.dispose()


def _resolve_clean_output(clean_dir: str | None, output_file: str | None) -> Path:
    if output_file:
        return Path(output_file).resolve()

    base_dir = Path(clean_dir or DEFAULT_CLEAN_DIR).resolve()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return base_dir / f"ingredients_{timestamp}.csv"


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
