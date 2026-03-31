from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.models import Ingredient, IngredientNutrition
from app.etl.types import INGREDIENT_FIELDNAMES, LoadStats, NormalizedIngredientRecord


def load_clean_ingredients(
    clean_csv_path: Path | str,
    session_factory: sessionmaker,
) -> LoadStats:
    """Load canonical ingredient rows into the database with upsert semantics."""
    records = _read_clean_csv(clean_csv_path)
    return load_ingredient_records(records, session_factory)


def load_ingredient_records(
    records: list[NormalizedIngredientRecord],
    session_factory: sessionmaker,
) -> LoadStats:
    """Upsert canonical ingredient rows in a single database transaction."""
    inserted = 0
    updated = 0
    names = [record.name for record in records]

    with session_factory() as session:
        try:
            existing_rows = (
                session.query(Ingredient)
                .filter(Ingredient.name.in_(names))
                .all()
                if names
                else []
            )
            existing_by_name = {ingredient.name: ingredient for ingredient in existing_rows}

            for record in records:
                ingredient = existing_by_name.get(record.name)
                if ingredient is None:
                    ingredient = _build_ingredient(record)
                    session.add(ingredient)
                    existing_by_name[record.name] = ingredient
                    inserted += 1
                    continue

                _update_ingredient(ingredient, record)
                updated += 1

            session.commit()
        except Exception:
            session.rollback()
            raise

    return LoadStats(processed=len(records), inserted=inserted, updated=updated)


def _update_ingredient(ingredient: Ingredient, record: NormalizedIngredientRecord) -> None:
    ingredient.category = record.category
    ingredient.standard_unit = record.standard_unit
    ingredient.estimated_shelf_life_days = record.estimated_shelf_life_days
    ingredient.storage_type = record.storage_type
    _upsert_nutrition(ingredient, record)


def _build_ingredient(record: NormalizedIngredientRecord) -> Ingredient:
    ingredient = Ingredient(
        name=record.name,
        category=record.category,
        standard_unit=record.standard_unit,
        estimated_shelf_life_days=record.estimated_shelf_life_days,
        storage_type=record.storage_type,
    )
    ingredient.nutrition = _build_nutrition(record)
    return ingredient


def _upsert_nutrition(ingredient: Ingredient, record: NormalizedIngredientRecord) -> None:
    nutrition = ingredient.nutrition
    if nutrition is None:
        ingredient.nutrition = _build_nutrition(record)
        return

    nutrition.calories_per_100g = record.calories_per_100g
    nutrition.protein_per_100g = record.protein_per_100g
    nutrition.carbs_per_100g = record.carbs_per_100g
    nutrition.fat_per_100g = record.fat_per_100g
    nutrition.fiber_per_100g = record.fiber_per_100g


def _build_nutrition(record: NormalizedIngredientRecord) -> IngredientNutrition:
    return IngredientNutrition(
        calories_per_100g=record.calories_per_100g,
        protein_per_100g=record.protein_per_100g,
        carbs_per_100g=record.carbs_per_100g,
        fat_per_100g=record.fat_per_100g,
        fiber_per_100g=record.fiber_per_100g,
    )


def _read_clean_csv(clean_csv_path: Path | str) -> list[NormalizedIngredientRecord]:
    clean_path = Path(clean_csv_path)
    with clean_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [field for field in INGREDIENT_FIELDNAMES if field not in (reader.fieldnames or [])]
        if missing_columns:
            raise ValueError(
                f"Clean ingredient CSV is missing required columns: {', '.join(missing_columns)}"
            )

        return [_record_from_csv_row(row) for row in reader]


def _record_from_csv_row(row: dict[str, str]) -> NormalizedIngredientRecord:
    return NormalizedIngredientRecord(
        name=row["name"],
        category=_nullable_str(row["category"]),
        standard_unit=row["standard_unit"] or "g",
        calories_per_100g=float(row["calories_per_100g"]),
        protein_per_100g=float(row["protein_per_100g"]),
        carbs_per_100g=float(row["carbs_per_100g"]),
        fat_per_100g=float(row["fat_per_100g"]),
        fiber_per_100g=_nullable_float(row["fiber_per_100g"]),
        estimated_shelf_life_days=_nullable_int(row["estimated_shelf_life_days"]),
        storage_type=_nullable_str(row["storage_type"]),
    )


def _nullable_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _nullable_float(value: str | None) -> float | None:
    cleaned = _nullable_str(value)
    return float(cleaned) if cleaned is not None else None


def _nullable_int(value: str | None) -> int | None:
    cleaned = _nullable_str(value)
    return int(cleaned) if cleaned is not None else None
