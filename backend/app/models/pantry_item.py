from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient


class PantryItem(Base):
    __tablename__ = "pantry_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_pantry_items_quantity_nonnegative"),
        CheckConstraint(
            "detected_confidence IS NULL OR (detected_confidence >= 0 AND detected_confidence <= 1)",
            name="ck_pantry_items_detected_confidence_range",
        ),
        Index("ix_pantry_items_user_id_estimated_expiry_date", "user_id", "estimated_expiry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detected_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_detected_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_added: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_false_positive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="pantry_items")
