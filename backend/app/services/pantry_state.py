from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models import Ingredient, PantryItem
from app.schemas.pantry import (
    PantryArchiveExpiredResponse,
    PantryConsumeResponse,
    PantryConsumeRequest,
    DetectedIngredientInput,
    ManualCorrectionInput,
    PantryItemUpdate,
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
        source_detected_name=item.source_detected_name,
        date_added=item.date_added,
        estimated_expiry_date=item.estimated_expiry_date,
        is_priority=item.is_priority,
        is_archived=item.is_archived,
        is_false_positive=item.is_false_positive,
        priority_bucket=bucket,
        priority_rank=priority_rank,
    )


def _get_pantry_item(db: Session, pantry_item_id: int) -> PantryItem | None:
    return (
        db.query(PantryItem)
        .options(joinedload(PantryItem.ingredient))
        .filter(PantryItem.id == pantry_item_id)
        .first()
    )


def _sync_priority_flags(db: Session, pantry_items: list[PantryItem]) -> None:
    has_changes = False
    for item in pantry_items:
        if item.is_archived or item.is_false_positive:
            expected_priority = False
            if item.is_priority != expected_priority:
                item.is_priority = expected_priority
                has_changes = True
            continue

        bucket = priority_bucket(item.estimated_expiry_date)
        expected_priority = is_priority_bucket(bucket)
        if item.is_priority != expected_priority:
            item.is_priority = expected_priority
            has_changes = True

    if has_changes:
        db.commit()
        for item in pantry_items:
            db.refresh(item)


def get_ranked_pantry_items(
    db: Session,
    user_id: str,
    include_inactive: bool = False,
) -> list[PantryItemRead]:
    """Return one user's pantry ordered by expiry and FIFO tie-breakers."""
    query = (
        db.query(PantryItem)
        .options(joinedload(PantryItem.ingredient))
        .filter(PantryItem.user_id == user_id)
    )
    if not include_inactive:
        query = query.filter(
            PantryItem.is_archived.is_(False),
            PantryItem.is_false_positive.is_(False),
        )

    pantry_items = query.all()

    _sync_priority_flags(db, pantry_items)
    ranked_items = rank_pantry_items(pantry_items)
    return [
        _shape_pantry_item(item, priority_rank=index)
        for index, item in enumerate(ranked_items, start=1)
    ]


def get_ranked_pantry_item(db: Session, pantry_item_id: int) -> PantryItemRead | None:
    """Return one pantry item together with its current rank for the owning user."""
    pantry_item = _get_pantry_item(db, pantry_item_id)
    if pantry_item is None:
        return None

    ranked_items = get_ranked_pantry_items(
        db,
        pantry_item.user_id,
        include_inactive=True,
    )
    for item in ranked_items:
        if item.id == pantry_item_id:
            return item
    return None


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
            source_detected_name=detection.detected_name.strip(),
            date_added=item_date_added,
            estimated_expiry_date=expiry_date,
            is_priority=is_priority_bucket(bucket),
        )
        db.add(pantry_item)

    db.commit()
    ranked_items = get_ranked_pantry_items(db, payload.user_id)
    return ranked_items, unmatched_detections


def update_pantry_item(
    db: Session,
    pantry_item_id: int,
    payload: PantryItemUpdate,
) -> PantryItemRead | None:
    """Update pantry quantity or unit while keeping ranking output consistent."""
    pantry_item = _get_pantry_item(db, pantry_item_id)
    if pantry_item is None:
        return None

    if (
        payload.quantity is None
        and payload.unit is None
        and payload.is_false_positive is None
    ):
        raise ValueError("At least one updatable field must be provided")

    if payload.quantity is not None:
        pantry_item.quantity = payload.quantity
    if payload.unit is not None:
        pantry_item.unit = payload.unit
    if payload.is_false_positive is not None:
        pantry_item.is_false_positive = payload.is_false_positive
        if payload.is_false_positive:
            pantry_item.is_priority = False

    db.commit()
    return get_ranked_pantry_item(db, pantry_item_id)


def delete_pantry_item(db: Session, pantry_item_id: int) -> bool:
    """Delete one pantry item by id."""
    pantry_item = _get_pantry_item(db, pantry_item_id)
    if pantry_item is None:
        return False

    db.delete(pantry_item)
    db.commit()
    return True


def consume_pantry_item(
    db: Session,
    pantry_item_id: int,
    payload: PantryConsumeRequest,
) -> PantryConsumeResponse | None:
    """Reduce pantry quantity and delete the item when it is fully consumed."""
    pantry_item = _get_pantry_item(db, pantry_item_id)
    if pantry_item is None:
        return None

    if pantry_item.quantity is None:
        raise ValueError("Cannot consume an item with unknown quantity")

    remaining_quantity = pantry_item.quantity - payload.amount
    if remaining_quantity <= 0:
        db.delete(pantry_item)
        db.commit()
        return PantryConsumeResponse(deleted=True, item=None)

    pantry_item.quantity = remaining_quantity
    db.commit()
    return PantryConsumeResponse(
        deleted=False,
        item=get_ranked_pantry_item(db, pantry_item_id),
    )


def archive_expired_pantry_items(db: Session, user_id: str) -> PantryArchiveExpiredResponse:
    """Archive expired pantry items so active pantry views stay focused on usable items."""
    today = date.today()
    pantry_items = (
        db.query(PantryItem)
        .filter(
            PantryItem.user_id == user_id,
            PantryItem.is_archived.is_(False),
            PantryItem.is_false_positive.is_(False),
            PantryItem.estimated_expiry_date.is_not(None),
            PantryItem.estimated_expiry_date < today,
        )
        .all()
    )

    archived_item_ids: list[int] = []
    for item in pantry_items:
        item.is_archived = True
        item.is_priority = False
        archived_item_ids.append(item.id)

    if archived_item_ids:
        db.commit()

    return PantryArchiveExpiredResponse(
        archived_count=len(archived_item_ids),
        archived_item_ids=archived_item_ids,
    )
