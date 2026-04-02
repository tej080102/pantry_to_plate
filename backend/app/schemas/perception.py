from pydantic import BaseModel, Field


class DetectedIngredientRead(BaseModel):
    raw_label: str = Field(..., min_length=1)
    normalized_name: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0, le=1)
    quantity_hint: float | None = Field(default=None, ge=0)
    unit_hint: str | None = None
    source_model: str = Field(..., min_length=1)


class PerceptionImageMetadataRead(BaseModel):
    filename: str | None = None
    content_type: str | None = None
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    bytes: int = Field(..., gt=0)
    format: str = Field(..., min_length=1)


class PerceptionResultRead(BaseModel):
    image: PerceptionImageMetadataRead
    ingredients: list[DetectedIngredientRead]
