from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient


class IngredientNutrition(Base):
    __tablename__ = "ingredient_nutrition"
    __table_args__ = (
        CheckConstraint("calories_per_100g >= 0", name="ck_ingredient_nutrition_calories_nonnegative"),
        CheckConstraint("protein_per_100g >= 0", name="ck_ingredient_nutrition_protein_nonnegative"),
        CheckConstraint("carbs_per_100g >= 0", name="ck_ingredient_nutrition_carbs_nonnegative"),
        CheckConstraint("fat_per_100g >= 0", name="ck_ingredient_nutrition_fat_nonnegative"),
        CheckConstraint("fiber_per_100g >= 0", name="ck_ingredient_nutrition_fiber_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    calories_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient",
        back_populates="nutrition",
    )
