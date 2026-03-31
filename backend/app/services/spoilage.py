from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol, TypeVar


class PantrySortable(Protocol):
    """Minimal pantry item shape needed for ranking and spoilage evaluation."""

    estimated_expiry_date: date | None
    date_added: date | None
    detected_confidence: float | None
    quantity: float | None


PantrySortableT = TypeVar("PantrySortableT", bound=PantrySortable)

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
UNKNOWN = "UNKNOWN"


def estimate_expiry_date(date_added: date | None, shelf_life_days: int | None) -> date | None:
    """Estimate expiry from the date an item was added and its shelf life."""
    if date_added is None or shelf_life_days is None:
        return None
    return date_added + timedelta(days=shelf_life_days)


def priority_bucket(expiry_date: date | None) -> str:
    """Assign a spoilage priority bucket using days until expiry."""
    if expiry_date is None:
        return UNKNOWN

    days_remaining = (expiry_date - date.today()).days
    if days_remaining <= 2:
        return HIGH
    if days_remaining <= 5:
        return MEDIUM
    return LOW


def is_priority_bucket(bucket: str) -> bool:
    """Treat HIGH and MEDIUM items as priority pantry items."""
    return bucket in {HIGH, MEDIUM}


def pantry_sort_key(item: PantrySortableT) -> tuple[bool, date, date, float, float, int]:
    """Create a deterministic sort key for pantry ordering."""
    return (
        item.estimated_expiry_date is None,
        item.estimated_expiry_date or date.max,
        item.date_added or date.max,
        -(item.detected_confidence if item.detected_confidence is not None else -1.0),
        -(item.quantity if item.quantity is not None else -1.0),
        getattr(item, "id", 0),
    )


def rank_pantry_items(pantry_items: list[PantrySortableT]) -> list[PantrySortableT]:
    """Return pantry items ordered by spoilage urgency and FIFO tie-breakers."""
    return sorted(pantry_items, key=pantry_sort_key)
