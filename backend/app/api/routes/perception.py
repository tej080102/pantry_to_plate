from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.perception import PerceptionResultRead
from app.services.perception import detect_ingredients_from_upload


router = APIRouter(prefix="/perception", tags=["perception"])


@router.post("/detect", response_model=PerceptionResultRead)
async def detect_ingredients(file: UploadFile = File(...)) -> PerceptionResultRead:
    """Process one uploaded image and return structured ingredient detections."""
    payload = await file.read()
    try:
        return detect_ingredients_from_upload(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
