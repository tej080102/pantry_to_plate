from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DetectedIngredientInput(BaseModel):
    detected_name: str = Field(..., min_length=1)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    detected_confidence: float | None = Field(default=None, ge=0, le=1)
    date_added: date | None = None


class ManualCorrectionInput(BaseModel):
    detected_name: str = Field(..., min_length=1)
    corrected_name: str = Field(..., min_length=1)


class PantryIngestRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    detected_ingredients: list[DetectedIngredientInput]
    manual_corrections: list[ManualCorrectionInput] | None = None


class PantryIngredientSummary(BaseModel):
    id: int
    name: str
    category: str | None = None
    standard_unit: str | None = None
    estimated_shelf_life_days: int | None = None
    storage_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PantryItemRead(BaseModel):
    id: int
    user_id: str
    ingredient: PantryIngredientSummary
    quantity: float | None = None
    unit: str | None = None
    detected_confidence: float | None = None
    source_detected_name: str | None = None
    date_added: date | None = None
    estimated_expiry_date: date | None = None
    is_priority: bool
    is_archived: bool
    is_false_positive: bool
    priority_bucket: str
    priority_rank: int


class PantryItemUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    estimated_expiry_date: date | None = None
    is_false_positive: bool | None = None


class PantryConsumeRequest(BaseModel):
    amount: float = Field(..., gt=0)


class PantryConsumeResponse(BaseModel):
    deleted: bool
    item: PantryItemRead | None = None


class PantryArchiveExpiredResponse(BaseModel):
    archived_count: int
    archived_item_ids: list[int]


class PantryRecipeIngredientInput(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: str | None = None
    available_in_pantry: bool = False


class PantryRecipeDeductionRead(BaseModel):
    ingredient_name: str
    pantry_item_id: int
    amount: float
    unit: str | None = None
    deleted: bool
    remaining_quantity: float | None = None


class PantryRecipeSkippedIngredientRead(BaseModel):
    ingredient_name: str
    reason: str


class PantryApplyRecipeRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    recipe_title: str = Field(..., min_length=1)
    ingredients: list[PantryRecipeIngredientInput] = Field(..., min_length=1)


class PantryApplyRecipeResponse(BaseModel):
    recipe_title: str
    applied_deductions: list[PantryRecipeDeductionRead]
    skipped_ingredients: list[PantryRecipeSkippedIngredientRead]
    items: list[PantryItemRead]


class UnmatchedDetectedIngredientRead(BaseModel):
    detected_name: str
    quantity: float | None = None
    unit: str | None = None
    confidence: float | None = None
    reason: str


class PantryIngestResponse(BaseModel):
    items: list[PantryItemRead]
    unmatched_detections: list[str]
    unmatched_detected_ingredients: list[UnmatchedDetectedIngredientRead]
