"""Module entrypoint for running ETL commands."""

from app.etl.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
