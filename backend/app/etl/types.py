from __future__ import annotations

from dataclasses import dataclass, field


INGREDIENT_FIELDNAMES = [
    "name",
    "category",
    "standard_unit",
    "calories_per_100g",
    "protein_per_100g",
    "carbs_per_100g",
    "fat_per_100g",
    "fiber_per_100g",
    "estimated_shelf_life_days",
    "storage_type",
]


@dataclass(frozen=True)
class NormalizedIngredientRecord:
    """Canonical ingredient record emitted by ETL sources."""

    name: str
    category: str | None
    standard_unit: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float | None = None
    estimated_shelf_life_days: int | None = None
    storage_type: str | None = None

    def as_csv_row(self) -> dict[str, str | float | int | None]:
        return {
            "name": self.name,
            "category": self.category,
            "standard_unit": self.standard_unit,
            "calories_per_100g": self.calories_per_100g,
            "protein_per_100g": self.protein_per_100g,
            "carbs_per_100g": self.carbs_per_100g,
            "fat_per_100g": self.fat_per_100g,
            "fiber_per_100g": self.fiber_per_100g,
            "estimated_shelf_life_days": self.estimated_shelf_life_days,
            "storage_type": self.storage_type,
        }


@dataclass(frozen=True)
class SourceFiles:
    """Filesystem locations for USDA source files."""

    food: str
    food_category: str
    nutrient: str
    food_nutrient: str
    food_portion: str | None = None
    measure_unit: str | None = None


@dataclass
class NormalizedBatch:
    """Normalized records produced by a source adapter."""

    ingredients: list[NormalizedIngredientRecord] = field(default_factory=list)


@dataclass(frozen=True)
class TransformStats:
    """Aggregate counts captured during transform."""

    rows_read: int
    rows_dropped: int
    rows_deduplicated: int
    rows_written: int


@dataclass(frozen=True)
class LoadStats:
    """Aggregate counts captured during database load."""

    processed: int
    inserted: int
    updated: int
