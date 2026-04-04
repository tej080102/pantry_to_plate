from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pantry import (
    PantryApplyRecipeRequest,
    PantryApplyRecipeResponse,
    PantryArchiveExpiredResponse,
    PantryConsumeRequest,
    PantryConsumeResponse,
    PantryIngestRequest,
    PantryIngestResponse,
    PantryItemRead,
    PantryItemUpdate,
)
from app.services.pantry_state import (
    apply_recipe_to_pantry,
    archive_expired_pantry_items,
    consume_pantry_item,
    delete_pantry_item,
    get_ranked_pantry_items,
    ingest_pantry_items,
    update_pantry_item,
)


router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.post("/ingest", response_model=PantryIngestResponse)
def ingest_pantry(
    payload: PantryIngestRequest,
    db: Session = Depends(get_db),
) -> PantryIngestResponse:
    """Persist confirmed ingredient detections as pantry state for one user."""
    items, unmatched_detected_ingredients = ingest_pantry_items(db, payload)
    return PantryIngestResponse(
        items=items,
        unmatched_detections=[
            item.detected_name for item in unmatched_detected_ingredients
        ],
        unmatched_detected_ingredients=unmatched_detected_ingredients,
    )


@router.get("", response_model=list[PantryItemRead])
def list_pantry(
    user_id: str = Query(..., min_length=1),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[PantryItemRead]:
    """Return one user's pantry ordered by spoilage urgency and FIFO rules."""
    return get_ranked_pantry_items(db, user_id, include_inactive=include_inactive)


@router.patch("/{pantry_item_id}", response_model=PantryItemRead)
def patch_pantry_item(
    pantry_item_id: int,
    payload: PantryItemUpdate,
    db: Session = Depends(get_db),
) -> PantryItemRead:
    """Update pantry quantity or unit for one item."""
    try:
        pantry_item = update_pantry_item(db, pantry_item_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if pantry_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pantry item not found",
        )
    return pantry_item


@router.delete("/{pantry_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pantry_item(
    pantry_item_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Delete one pantry item."""
    deleted = delete_pantry_item(db, pantry_item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pantry item not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{pantry_item_id}/consume", response_model=PantryConsumeResponse)
def consume_pantry(
    pantry_item_id: int,
    payload: PantryConsumeRequest,
    db: Session = Depends(get_db),
) -> PantryConsumeResponse:
    """Consume pantry quantity and delete the item when it reaches zero."""
    try:
        result = consume_pantry_item(db, pantry_item_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pantry item not found",
        )
    return result


@router.post("/apply-recipe", response_model=PantryApplyRecipeResponse)
def apply_recipe(
    payload: PantryApplyRecipeRequest,
    db: Session = Depends(get_db),
) -> PantryApplyRecipeResponse:
    """Deduct pantry quantities for the selected generated recipe."""
    return apply_recipe_to_pantry(db, payload)


@router.post("/archive-expired", response_model=PantryArchiveExpiredResponse)
def archive_expired_pantry(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> PantryArchiveExpiredResponse:
    """Archive expired pantry items for one user."""
    return archive_expired_pantry_items(db, user_id)
