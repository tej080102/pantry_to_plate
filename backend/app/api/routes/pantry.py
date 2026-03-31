from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pantry import PantryIngestRequest, PantryIngestResponse, PantryItemRead
from app.services.pantry_state import get_ranked_pantry_items, ingest_pantry_items


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
    db: Session = Depends(get_db),
) -> list[PantryItemRead]:
    """Return one user's pantry ordered by spoilage urgency and FIFO rules."""
    return get_ranked_pantry_items(db, user_id)
