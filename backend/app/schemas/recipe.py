from datetime import datetime

from pydantic import BaseModel, ConfigDict , Field

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


class IngredientInput(BaseModel):
    """One ingredient the caller wants considered for recipe generation."""

    name: str = Field(..., min_length=1)
    quantity: float | None = None
    unit: str | None = None
    # Spoilage priority bucket from the pantry service
    priority: str = Field(default="LOW", pattern="^(HIGH|MEDIUM|LOW|UNKNOWN)$")
    days_until_expiry: int | None = None


class RecipeGenerateRequest(BaseModel):
    ingredients: list[IngredientInput] = Field(..., min_length=1)
    max_recipes: int = Field(default=3, ge=1, le=5)
    servings: int = Field(default=2, ge=1, le=12)


