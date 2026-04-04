from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.schemas.recipe import (
    GeneratedRecipe,
    GeneratedRecipeIngredient,
    IngredientInput,
    RecipeGenerateRequest,
    RecipeGenerateResponse,
)

logger = logging.getLogger(__name__)

_DEFAULT_RECIPE_MODEL = "gemini-2.5-flash"

# Priority buckets that count as "expiring soon"
_PRIORITY_BUCKETS = {"HIGH", "MEDIUM"}

# ---------------------------------------------------------------------------
# Gemini prompt + JSON schema
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are a professional chef generating practical recipes from available pantry ingredients.

PRIORITY INGREDIENTS — expiring soon, must be used in at least one recipe:
{priority_list}

ALL AVAILABLE PANTRY INGREDIENTS:
{all_list}

REFERENCE RECIPES FROM DATABASE (use for inspiration and grounding — do not hallucinate):
{reference_recipes}

TASK:
Generate exactly {max_recipes} distinct recipe(s) sized for {servings} serving(s).

Rules:
1. Every recipe MUST include at least one PRIORITY ingredient.
2. Use as many priority ingredients as possible across the recipe set.
3. Only use ingredients from the available list or universally assumed basics (salt, pepper, water, oil).
4. Steps must be numbered, clear, and actionable.
5. pantry_coverage_percent = (recipe ingredients present in pantry / total recipe ingredients) × 100.
6. is_priority = true only for ingredients that appear in the PRIORITY list.
7. available_in_pantry = true for ingredients present in the ALL AVAILABLE list.

Return ONLY a JSON array matching the provided schema. No extra text.
""".strip()

_GEMINI_RECIPE_JSON_SCHEMA: dict[str, Any] = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "description": {"type": "STRING"},
            "servings": {"type": "INTEGER"},
            "estimated_cook_time_minutes": {"type": "INTEGER"},
            "ingredients": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "quantity": {"type": "STRING"},
                        "is_priority": {"type": "BOOLEAN"},
                        "available_in_pantry": {"type": "BOOLEAN"},
                    },
                    "required": ["name", "quantity", "is_priority", "available_in_pantry"],
                },
            },
            "steps": {"type": "ARRAY", "items": {"type": "STRING"}},
            "priority_ingredients_used": {"type": "ARRAY", "items": {"type": "STRING"}},
            "pantry_coverage_percent": {"type": "NUMBER"},
        },
        "required": [
            "title",
            "description",
            "servings",
            "estimated_cook_time_minutes",
            "ingredients",
            "steps",
            "priority_ingredients_used",
            "pantry_coverage_percent",
        ],
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_recipes(db: Session, request: RecipeGenerateRequest) -> RecipeGenerateResponse:
    """
    Full pipeline:
      1. Sort + classify input ingredients by spoilage priority.
      2. DB-first: find recipe catalog candidates with the best pantry overlap.
      3. Call Gemini on Vertex AI with the ranked ingredients + DB candidates.
      4. Fall back to DB-derived recipes when Gemini is unavailable.
    """
    priority_names = [
        i.name for i in request.ingredients if i.priority in _PRIORITY_BUCKETS
    ]
    all_names = [i.name for i in request.ingredients]

    # Sort so highest-priority / soonest-expiring items appear first in the prompt
    sorted_ingredients = _sort_by_priority(request.ingredients)

    # DB-first: find catalog recipes that overlap with our pantry
    candidates = _find_candidate_recipes(db, all_names, priority_names)

    # Try Gemini; fall back to DB-derived output on any failure
    try:
        recipes = _generate_with_gemini(
            sorted_ingredients=sorted_ingredients,
            priority_names=priority_names,
            candidates=candidates,
            max_recipes=request.max_recipes,
            servings=request.servings,
        )
        method = settings.RECIPE_MODEL or _DEFAULT_RECIPE_MODEL
    except Exception:
        logger.warning(
            "Gemini recipe generation failed; using DB-derived fallback.",
            exc_info=True,
        )
        recipes = _generate_from_db_candidates(
            candidates=candidates,
            sorted_ingredients=sorted_ingredients,
            priority_names=priority_names,
            max_recipes=request.max_recipes,
            servings=request.servings,
        )
        method = "db_fallback"

    # Recompute pantry coverage in the backend for reliability
    pantry_name_set = {n.lower() for n in all_names}
    for recipe in recipes:
        recipe.pantry_coverage_percent = _compute_coverage(
            recipe.ingredients, pantry_name_set
        )

    return RecipeGenerateResponse(
        recipes=recipes,
        priority_ingredients=priority_names,
        generation_method=method,
    )


# ---------------------------------------------------------------------------
# Step 1 — Priority sorting
# ---------------------------------------------------------------------------


def _sort_by_priority(ingredients: list[IngredientInput]) -> list[IngredientInput]:
    """Return ingredients sorted HIGH → MEDIUM → LOW → UNKNOWN, then by days_until_expiry."""
    bucket_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
    return sorted(
        ingredients,
        key=lambda i: (
            bucket_order.get(i.priority, 3),
            i.days_until_expiry if i.days_until_expiry is not None else 9999,
        ),
    )


# ---------------------------------------------------------------------------
# Step 2 — DB-first candidate matching
# ---------------------------------------------------------------------------


def _find_candidate_recipes(
    db: Session,
    all_names: list[str],
    priority_names: list[str],
) -> list[tuple[Recipe, float]]:
    """
    Score every recipe in the catalog by pantry overlap.

    Score = (priority_matches × 2 + regular_matches) / total_recipe_ingredients

    Returns up to 5 recipes ordered by score descending.
    """
    if not all_names:
        return []

    lower_all = {n.lower() for n in all_names}
    lower_priority = {n.lower() for n in priority_names}

    recipes = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient)
        )
        .all()
    )

    scored: list[tuple[Recipe, float]] = []
    for recipe in recipes:
        ri_names = [
            ri.ingredient.name.lower()
            for ri in recipe.recipe_ingredients
            if ri.ingredient is not None
        ]
        if not ri_names:
            continue

        priority_matches = sum(
            1
            for name in ri_names
            if any(_fuzzy_match(name, p) for p in lower_priority)
        )
        regular_matches = sum(
            1
            for name in ri_names
            if any(_fuzzy_match(name, a) for a in lower_all)
        )

        if regular_matches == 0:
            continue

        score = (priority_matches * 2 + regular_matches) / len(ri_names)
        scored.append((recipe, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:5]


def _fuzzy_match(recipe_name: str, pantry_name: str) -> bool:
    """True when either string is a substring of the other."""
    return recipe_name in pantry_name or pantry_name in recipe_name

