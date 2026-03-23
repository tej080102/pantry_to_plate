from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngredientBase(BaseModel):
    name: str
    category: str | None = None
    standard_unit: str | None = None
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    fiber_per_100g: float | None = None
    estimated_shelf_life_days: int | None = None
    storage_type: str | None = None


class IngredientCreate(IngredientBase):
    pass


class IngredientRead(IngredientBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
