from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.pantry_item import PantryItem
    from app.models.recipe_ingredient import RecipeIngredient


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    standard_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calories_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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