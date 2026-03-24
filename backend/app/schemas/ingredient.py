from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngredientNutritionBase(BaseModel):
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    fiber_per_100g: float | None = None


class IngredientNutritionCreate(IngredientNutritionBase):
    pass


class IngredientNutritionRead(IngredientNutritionBase):
    id: int
    ingredient_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngredientBase(BaseModel):
    name: str
    category: str | None = None
    standard_unit: str | None = None
    estimated_shelf_life_days: int | None = None
    storage_type: str | None = None


class IngredientCreate(IngredientBase):
    nutrition: IngredientNutritionCreate | None = None


class IngredientRead(IngredientBase):
    id: int
    created_at: datetime
    nutrition: IngredientNutritionRead | None = None

    model_config = ConfigDict(from_attributes=True)
