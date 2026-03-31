from __future__ import annotations

import abc
import csv
import re
from pathlib import Path

from app.etl.types import NormalizedBatch, NormalizedIngredientRecord, SourceFiles, TransformStats


TARGET_NUTRIENT_IDS = {
    1008: "calories_per_100g",
    1003: "protein_per_100g",
    1005: "carbs_per_100g",
    1004: "fat_per_100g",
    1079: "fiber_per_100g",
}


class DatasetSourceAdapter(abc.ABC):
    """Common adapter interface for normalized ETL sources."""

    source_name: str

    @abc.abstractmethod
    def validate(self, raw_dir: Path) -> SourceFiles:
        """Validate source files and return resolved filesystem paths."""

    @abc.abstractmethod
    def transform(self, raw_dir: Path) -> tuple[NormalizedBatch, TransformStats]:
        """Read raw files and return normalized records plus stats."""


class USDAFoundationSourceAdapter(DatasetSourceAdapter):
    """Adapter for USDA FoodData Central Foundation Foods CSV extracts."""

    source_name = "usda_foundation"

    def validate(self, raw_dir: Path) -> SourceFiles:
        expected_files = {
            "food": raw_dir / "food.csv",
            "food_category": raw_dir / "food_category.csv",
            "nutrient": raw_dir / "nutrient.csv",
            "food_nutrient": raw_dir / "food_nutrient.csv",
        }
        missing = [path.name for path in expected_files.values() if not path.exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing USDA Foundation source files in {raw_dir}: {', '.join(sorted(missing))}"
            )

        optional_portion = raw_dir / "food_portion.csv"
        optional_measure_unit = raw_dir / "measure_unit.csv"
        return SourceFiles(
            food=str(expected_files["food"]),
            food_category=str(expected_files["food_category"]),
            nutrient=str(expected_files["nutrient"]),
            food_nutrient=str(expected_files["food_nutrient"]),
            food_portion=str(optional_portion) if optional_portion.exists() else None,
            measure_unit=str(optional_measure_unit) if optional_measure_unit.exists() else None,
        )

    def transform(self, raw_dir: Path) -> tuple[NormalizedBatch, TransformStats]:
        source_files = self.validate(raw_dir)
        self._validate_nutrients(Path(source_files.nutrient))

        categories = self._read_categories(Path(source_files.food_category))
        nutrient_values = self._read_nutrients(Path(source_files.food_nutrient))
        units = self._read_units(source_files)

        batch = NormalizedBatch()
        deduped_records: dict[str, tuple[int, NormalizedIngredientRecord, tuple[int, int]]] = {}
        rows_read = 0
        rows_dropped = 0
        valid_pre_dedupe = 0

        for row_index, row in enumerate(self._read_csv(Path(source_files.food))):
            if not self._is_foundation_row(row):
                continue

            rows_read += 1
            record = self._build_record(row, categories, nutrient_values, units)
            if record is None:
                rows_dropped += 1
                continue

            valid_pre_dedupe += 1
            dedupe_key = _dedupe_key(record.name)
            candidate_score = _record_score(record)
            existing = deduped_records.get(dedupe_key)
            if existing is None or candidate_score > existing[2]:
                deduped_records[dedupe_key] = (row_index, record, candidate_score)

        ordered_records = sorted(deduped_records.values(), key=lambda item: item[0])
        batch.ingredients = [record for _, record, _ in ordered_records]
        rows_deduplicated = valid_pre_dedupe - len(batch.ingredients)
        stats = TransformStats(
            rows_read=rows_read,
            rows_dropped=rows_dropped,
            rows_deduplicated=rows_deduplicated,
            rows_written=len(batch.ingredients),
        )
        return batch, stats

    def _validate_nutrients(self, nutrient_csv: Path) -> None:
        found_ids = {
            int(row["id"])
            for row in self._read_csv(nutrient_csv)
            if row.get("id") and row["id"].isdigit()
        }
        missing_ids = sorted(set(TARGET_NUTRIENT_IDS) - found_ids)
        if missing_ids:
            raise ValueError(
                f"Nutrient lookup is missing required USDA IDs: {', '.join(map(str, missing_ids))}"
            )

    def _read_categories(self, category_csv: Path) -> dict[str, str]:
        return {
            row["id"]: _clean_category(row.get("description"))
            for row in self._read_csv(category_csv)
            if row.get("id") and row.get("description")
        }

    def _read_nutrients(self, nutrient_csv: Path) -> dict[str, dict[str, float | None]]:
        nutrients_by_food: dict[str, dict[str, float | None]] = {}
        for row in self._read_csv(nutrient_csv):
            nutrient_id = row.get("nutrient_id")
            fdc_id = row.get("fdc_id")
            if not nutrient_id or not fdc_id:
                continue
            if not nutrient_id.isdigit():
                continue

            nutrient_key = TARGET_NUTRIENT_IDS.get(int(nutrient_id))
            if nutrient_key is None:
                continue

            amount = _safe_float(row.get("amount"))
            if amount is None:
                continue

            nutrients_by_food.setdefault(fdc_id, {})[nutrient_key] = amount

        return nutrients_by_food

    def _read_units(self, source_files: SourceFiles) -> dict[str, str]:
        if not source_files.food_portion or not source_files.measure_unit:
            return {}

        measure_units = {
            row["id"]: _normalize_unit_name(row.get("name"))
            for row in self._read_csv(Path(source_files.measure_unit))
            if row.get("id") and row.get("name")
        }

        units_by_food: dict[str, tuple[int, str]] = {}
        for row in self._read_csv(Path(source_files.food_portion)):
            fdc_id = row.get("fdc_id")
            measure_unit_id = row.get("measure_unit_id")
            if not fdc_id or not measure_unit_id:
                continue

            unit_name = measure_units.get(measure_unit_id)
            if not unit_name:
                continue

            sequence = _portion_sequence(row)
            current = units_by_food.get(fdc_id)
            if current is None or sequence < current[0]:
                units_by_food[fdc_id] = (sequence, unit_name)

        return {fdc_id: unit_name for fdc_id, (_, unit_name) in units_by_food.items()}

    def _build_record(
        self,
        row: dict[str, str],
        categories: dict[str, str],
        nutrient_values: dict[str, dict[str, float | None]],
        units: dict[str, str],
    ) -> NormalizedIngredientRecord | None:
        fdc_id = row.get("fdc_id")
        raw_name = row.get("description")
        if not fdc_id or not raw_name:
            return None

        name = _clean_name(raw_name)
        if not name:
            return None

        nutrient_map = nutrient_values.get(fdc_id, {})
        calories = nutrient_map.get("calories_per_100g")
        protein = nutrient_map.get("protein_per_100g")
        carbs = nutrient_map.get("carbs_per_100g")
        fat = nutrient_map.get("fat_per_100g")
        if None in (calories, protein, carbs, fat):
            return None

        category = categories.get(row.get("food_category_id", ""), None)
        return NormalizedIngredientRecord(
            name=name,
            category=category,
            standard_unit=units.get(fdc_id, "g"),
            calories_per_100g=calories,
            protein_per_100g=protein,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
            fiber_per_100g=nutrient_map.get("fiber_per_100g"),
            estimated_shelf_life_days=None,
            storage_type=None,
        )

    def _is_foundation_row(self, row: dict[str, str]) -> bool:
        data_type = (row.get("data_type") or "").strip().lower()
        return not data_type or "foundation" in data_type

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))


def _clean_name(raw_name: str | None) -> str | None:
    if raw_name is None:
        return None
    cleaned = raw_name.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s*([,;/()\-])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" ,;:/-()")
    if not cleaned:
        return None
    if cleaned.isupper():
        cleaned = cleaned.title()
    return cleaned


def _clean_category(raw_category: str | None) -> str | None:
    if raw_category is None:
        return None
    cleaned = re.sub(r"\s+", " ", raw_category.strip())
    return cleaned or None


def _dedupe_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _record_score(record: NormalizedIngredientRecord) -> tuple[int, int]:
    macro_completeness = sum(
        value is not None
        for value in (
            record.calories_per_100g,
            record.protein_per_100g,
            record.carbs_per_100g,
            record.fat_per_100g,
            record.fiber_per_100g,
        )
    )
    return macro_completeness, int(record.category is not None)


def _safe_float(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    stripped = raw_value.strip()
    if not stripped:
        return None
    return float(stripped)


def _portion_sequence(row: dict[str, str]) -> int:
    for key in ("seq_num", "id"):
        value = row.get(key)
        if value and value.isdigit():
            return int(value)
    return 10**9


def _normalize_unit_name(raw_unit: str | None) -> str:
    if raw_unit is None:
        return "g"
    cleaned = raw_unit.strip().lower()
    return cleaned or "g"
