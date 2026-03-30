from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ingredient_nutrition import IngredientNutrition
    from app.models.pantry_item import PantryItem
    from app.models.recipe_ingredient import RecipeIngredient


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    standard_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    nutrition: Mapped["IngredientNutrition | None"] = relationship(
        "IngredientNutrition",
        back_populates="ingredient",
        uselist=False,
        cascade="all, delete-orphan",
    )
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )
    pantry_items: Mapped[list["PantryItem"]] = relationship(
        "PantryItem",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )
