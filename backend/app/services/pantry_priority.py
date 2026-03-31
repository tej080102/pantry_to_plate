from __future__ import annotations

from datetime import date
from typing import Protocol, TypeVar


class PantryItemLike(Protocol):
    """Minimal shape needed for pantry prioritization helpers."""

    estimated_expiry_date: date | None
    is_priority: bool


PantryItemT = TypeVar("PantryItemT", bound=PantryItemLike)


def days_until_expiry(expiry_date: date | None) -> int | None:
    """Return the number of days from today until the given expiry date."""
    if expiry_date is None:
        return None
    return (expiry_date - date.today()).days


def is_priority_item(expiry_date: date | None, threshold_days: int = 3) -> bool:
    """Return True when an item expires within the configured threshold."""
    remaining_days = days_until_expiry(expiry_date)
    return remaining_days is not None and remaining_days <= threshold_days


def sort_pantry_items_by_expiry(pantry_items: list[PantryItemT]) -> list[PantryItemT]:
    """Sort pantry items by earliest expiry date, placing unknown dates last."""
    return sorted(
        pantry_items,
        key=lambda item: (
            item.estimated_expiry_date is None,
            item.estimated_expiry_date or date.max,
        ),
    )


def annotate_priority_flags(
    pantry_items: list[PantryItemT],
    threshold_days: int = 3,
) -> list[PantryItemT]:
    """Set in-memory priority flags based on expiry proximity and return the items."""
    for item in pantry_items:
        # Keep the update explicit so the caller can persist changes if needed.
        item.is_priority = is_priority_item(item.estimated_expiry_date, threshold_days)
    return pantry_items
