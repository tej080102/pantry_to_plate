from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Ingredient, Recipe, RecipeIngredient
from app.schemas.recipe import RecipeRead, RecipeWithIngredientsRead


router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeRead])
def list_recipes(db: Session = Depends(get_db)) -> list[Recipe]:
    """Return all recipes ordered by most recent first."""
    return db.query(Recipe).order_by(Recipe.created_at.desc()).all()


@router.get("/{recipe_id}", response_model=RecipeWithIngredientsRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> Recipe:
    """Return one recipe together with its linked ingredient rows."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.recipe_ingredients)
            .joinedload(RecipeIngredient.ingredient)
            .joinedload(Ingredient.nutrition),
        )
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )
    return recipe
