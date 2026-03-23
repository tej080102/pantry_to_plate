from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient
    from app.models.recipe import Recipe


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipe_ingredients")