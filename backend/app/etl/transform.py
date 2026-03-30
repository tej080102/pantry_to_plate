from __future__ import annotations

import csv
from pathlib import Path

from app.etl.source import USDAFoundationSourceAdapter
from app.etl.types import INGREDIENT_FIELDNAMES, NormalizedBatch, TransformStats


def transform_usda_foundation(
    raw_dir: Path | str,
    output_path: Path | str,
) -> tuple[NormalizedBatch, TransformStats]:
    """Transform USDA Foundation Foods CSVs into the normalized ingredient format."""
    adapter = USDAFoundationSourceAdapter()
    batch, stats = adapter.transform(Path(raw_dir))
    write_clean_ingredient_csv(batch, output_path)
    return batch, stats


def write_clean_ingredient_csv(
    batch: NormalizedBatch,
    output_path: Path | str,
) -> Path:
    """Persist normalized ingredient rows to a CSV artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INGREDIENT_FIELDNAMES)
        writer.writeheader()
        for record in batch.ingredients:
            writer.writerow(record.as_csv_row())
    return path
