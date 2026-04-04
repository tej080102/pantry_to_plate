# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session, joinedload

# from app.core.database import get_db
# from app.models import Ingredient, Recipe, RecipeIngredient
# from app.schemas.recipe import RecipeRead, RecipeWithIngredientsRead

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Recipe, RecipeIngredient
from app.schemas.recipe import (
    RecipeGenerateRequest,
    RecipeGenerateResponse,
    RecipeRead,
    RecipeWithIngredientsRead,
)
from app.services.recipe_generator import generate_recipes


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

@router.post("/generate", response_model=RecipeGenerateResponse)
def generate(
    payload: RecipeGenerateRequest,
    db: Session = Depends(get_db),
) -> RecipeGenerateResponse:
    """
    Generate recipes from a prioritised ingredient list.

    Priority flow:
      1. DB-first: find catalog recipes with the best pantry overlap
         (priority ingredients score ×2 vs regular matches).
      2. Gemini on Vertex AI: generate structured recipes grounded in the
         DB candidates and ranked ingredient list.
      3. DB-derived fallback: if Gemini is unavailable, return the top
         catalog matches formatted into the same output shape.

    The response always includes:
    - Which ingredients were treated as HIGH/MEDIUM priority
    - Which generation method was used
    - pantry_coverage_percent per recipe (computed server-side)
    """
    try:
        return generate_recipes(db, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recipe generation failed: {exc}",
        ) from exc