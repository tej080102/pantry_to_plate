from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Ingredient, IngredientNutrition
from app.schemas.ingredient import IngredientCreate, IngredientRead


router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("", response_model=list[IngredientRead])
def list_ingredients(db: Session = Depends(get_db)) -> list[Ingredient]:
    """Return all ingredients ordered by name for predictable API output."""
    return (
        db.query(Ingredient)
        .options(joinedload(Ingredient.nutrition))
        .order_by(Ingredient.name.asc())
        .all()
    )


@router.post(
    "",
    response_model=IngredientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ingredient(
    ingredient_in: IngredientCreate,
    db: Session = Depends(get_db),
) -> Ingredient:
    """Create a new ingredient record."""
    existing_ingredient = (
        db.query(Ingredient)
        .filter(Ingredient.name == ingredient_in.name)
        .first()
    )
    if existing_ingredient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient with this name already exists",
        )

    ingredient_data = ingredient_in.model_dump(exclude={"nutrition"})
    ingredient = Ingredient(**ingredient_data)
    if ingredient_in.nutrition is not None:
        ingredient.nutrition = IngredientNutrition(**ingredient_in.nutrition.model_dump())

    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient
