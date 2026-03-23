from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.ingredient import IngredientRead


class RecipeRead(BaseModel):
    id: int
    title: str
    source_name: str | None = None
    source_url: str | None = None
    instructions: str | None = None
    estimated_cook_time_minutes: int | None = None
    servings: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientRead(BaseModel):
    id: int
    recipe_id: int
    ingredient_id: int
    quantity: float | None = None
    unit: str | None = None
    is_optional: bool
    ingredient: IngredientRead

    model_config = ConfigDict(from_attributes=True)


class RecipeWithIngredientsRead(RecipeRead):
    recipe_ingredients: list[RecipeIngredientRead]
