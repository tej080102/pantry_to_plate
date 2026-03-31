from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models import Ingredient, PantryItem
from app.schemas.pantry import (
    DetectedIngredientInput,
    ManualCorrectionInput,
    PantryIngestRequest,
    PantryItemRead,
    UnmatchedDetectedIngredientRead,
)
from app.services.spoilage import (
    estimate_expiry_date,
    is_priority_bucket,
    priority_bucket,
    rank_pantry_items,
)

# Fallback policy for pantry MVP:
# 1. Use explicit Ingredient.estimated_shelf_life_days when available.
# 2. Otherwise apply a simple category default.
# 3. If the category is unknown, leave expiry unknown and bucket as UNKNOWN.
CATEGORY_SHELF_LIFE_DEFAULTS: dict[str, int] = {
    "vegetable": 5,
    "fruit": 7,
    "herb": 5,
    "dairy": 7,
    "meat": 2,
    "seafood": 2,
    "pantry": 30,
    "grain": 90,
    "frozen": 30,
}


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _build_correction_map(
    manual_corrections: list[ManualCorrectionInput] | None,
) -> dict[str, str]:
    if not manual_corrections:
        return {}
    return {
        _normalize_name(correction.detected_name): correction.corrected_name.strip()
        for correction in manual_corrections
    }


def _canonical_name_for_detection(
    detection: DetectedIngredientInput,
    correction_map: dict[str, str],
) -> str:
    normalized_name = _normalize_name(detection.detected_name)
    return correction_map.get(normalized_name, detection.detected_name.strip())


def _ingredient_lookup(db: Session) -> dict[str, Ingredient]:
    ingredients = db.query(Ingredient).all()
    return {_normalize_name(ingredient.name): ingredient for ingredient in ingredients}


def _resolve_shelf_life_days(ingredient: Ingredient) -> int | None:
    if ingredient.estimated_shelf_life_days is not None:
        return ingredient.estimated_shelf_life_days

    if ingredient.category is None:
        return None

    return CATEGORY_SHELF_LIFE_DEFAULTS.get(_normalize_name(ingredient.category))


def _shape_pantry_item(item: PantryItem, priority_rank: int) -> PantryItemRead:
    bucket = priority_bucket(item.estimated_expiry_date)
    return PantryItemRead(
        id=item.id,
        user_id=item.user_id,
        ingredient=item.ingredient,
        quantity=item.quantity,
        unit=item.unit,
        detected_confidence=item.detected_confidence,
        date_added=item.date_added,
        estimated_expiry_date=item.estimated_expiry_date,
        is_priority=item.is_priority,
        priority_bucket=bucket,
        priority_rank=priority_rank,
    )


def _sync_priority_flags(db: Session, pantry_items: list[PantryItem]) -> None:
    has_changes = False
    for item in pantry_items:
        bucket = priority_bucket(item.estimated_expiry_date)
        expected_priority = is_priority_bucket(bucket)
        if item.is_priority != expected_priority:
            item.is_priority = expected_priority
            has_changes = True

    if has_changes:
        db.commit()
        for item in pantry_items:
            db.refresh(item)


def get_ranked_pantry_items(db: Session, user_id: str) -> list[PantryItemRead]:
    """Return one user's pantry ordered by expiry and FIFO tie-breakers."""
    pantry_items = (
        db.query(PantryItem)
        .options(joinedload(PantryItem.ingredient))
        .filter(PantryItem.user_id == user_id)
        .all()
    )

    _sync_priority_flags(db, pantry_items)
    ranked_items = rank_pantry_items(pantry_items)
    return [
        _shape_pantry_item(item, priority_rank=index)
        for index, item in enumerate(ranked_items, start=1)
    ]


def ingest_pantry_items(
    db: Session,
    payload: PantryIngestRequest,
) -> tuple[list[PantryItemRead], list[UnmatchedDetectedIngredientRead]]:
    """Persist pantry items from confirmed detections and return the ranked pantry view."""
    correction_map = _build_correction_map(payload.manual_corrections)
    ingredient_by_name = _ingredient_lookup(db)
    unmatched_detections: list[UnmatchedDetectedIngredientRead] = []
    today = date.today()

    for detection in payload.detected_ingredients:
        canonical_name = _canonical_name_for_detection(detection, correction_map)
        ingredient = ingredient_by_name.get(_normalize_name(canonical_name))
        if ingredient is None:
            unmatched_detections.append(
                UnmatchedDetectedIngredientRead(
                    detected_name=detection.detected_name,
                    quantity=detection.quantity,
                    unit=detection.unit,
                    confidence=detection.detected_confidence,
                    reason="No canonical ingredient match found",
                )
            )
            continue

        item_date_added = detection.date_added or today
        shelf_life_days = _resolve_shelf_life_days(ingredient)
        expiry_date = estimate_expiry_date(item_date_added, shelf_life_days)
        bucket = priority_bucket(expiry_date)

        pantry_item = PantryItem(
            user_id=payload.user_id,
            ingredient_id=ingredient.id,
            quantity=detection.quantity,
            unit=detection.unit,
            detected_confidence=detection.detected_confidence,
            date_added=item_date_added,
            estimated_expiry_date=expiry_date,
            is_priority=is_priority_bucket(bucket),
        )
        db.add(pantry_item)

    db.commit()
    ranked_items = get_ranked_pantry_items(db, payload.user_id)
    return ranked_items, unmatched_detections
