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
from app.services.ingredient_matching import ingredient_names_match

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
    """Treat close grocery names and canonical ingredient names as equivalent."""
    return ingredient_names_match(recipe_name, pantry_name)



# ---------------------------------------------------------------------------
# Step 3a — Gemini generation
# ---------------------------------------------------------------------------


def _generate_with_gemini(
    *,
    sorted_ingredients: list[IngredientInput],
    priority_names: list[str],
    candidates: list[tuple[Recipe, float]],
    max_recipes: int,
    servings: int,
) -> list[GeneratedRecipe]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Recipe generation with Gemini requires the 'google-genai' package."
        ) from exc

    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        if not settings.GCP_PROJECT_ID:
            raise RuntimeError(
                "GCP_PROJECT_ID must be set when using Vertex AI for recipe generation."
            )
    elif not settings.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY must be set when using Gemini without Vertex AI for recipe generation."
        )

    model = settings.RECIPE_MODEL or _DEFAULT_RECIPE_MODEL

    prompt = _PROMPT_TEMPLATE.format(
        priority_list=_format_priority_list(sorted_ingredients),
        all_list=_format_all_list(sorted_ingredients),
        reference_recipes=_format_reference_recipes(candidates),
        max_recipes=max_recipes,
        servings=servings,
    )

    client_kwargs: dict[str, Any] = {
        "vertexai": settings.GOOGLE_GENAI_USE_VERTEXAI,
        "http_options": types.HttpOptions(
            api_version="v1" if settings.GOOGLE_GENAI_USE_VERTEXAI else "v1beta"
        ),
    }
    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        client_kwargs["project"] = settings.GCP_PROJECT_ID
        client_kwargs["location"] = settings.GCP_REGION
    else:
        client_kwargs["api_key"] = settings.GOOGLE_API_KEY

    client = genai.Client(**client_kwargs)

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config={
            "temperature": 0.4,
            "response_mime_type": "application/json",
            "response_schema": _GEMINI_RECIPE_JSON_SCHEMA,
        },
    )

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        text = getattr(response, "text", "") or ""
        if not text:
            raise RuntimeError("Gemini returned an empty response for recipe generation.")
        parsed = json.loads(text)

    return _coerce_gemini_recipes(parsed)


def _coerce_gemini_recipes(payload: Any) -> list[GeneratedRecipe]:
    if not isinstance(payload, list):
        raise RuntimeError("Gemini returned an unexpected shape for recipe generation.")

    recipes: list[GeneratedRecipe] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            raw_ingredients = item.get("ingredients") or []
            ingredients = [
                GeneratedRecipeIngredient(
                    name=str(ri.get("name", "")).strip(),
                    quantity=str(ri.get("quantity", "")) or None,
                    is_priority=bool(ri.get("is_priority", False)),
                    available_in_pantry=bool(ri.get("available_in_pantry", False)),
                )
                for ri in raw_ingredients
                if isinstance(ri, dict) and ri.get("name")
            ]
            recipes.append(
                GeneratedRecipe(
                    title=str(item.get("title", "Untitled Recipe")).strip(),
                    description=str(item.get("description", "")).strip(),
                    servings=int(item.get("servings", 2)),
                    estimated_cook_time_minutes=int(
                        item.get("estimated_cook_time_minutes", 30)
                    ),
                    ingredients=ingredients,
                    steps=[str(s) for s in (item.get("steps") or [])],
                    priority_ingredients_used=[
                        str(p) for p in (item.get("priority_ingredients_used") or [])
                    ],
                    pantry_coverage_percent=float(
                        item.get("pantry_coverage_percent", 0.0)
                    ),
                )
            )
        except (TypeError, ValueError):
            logger.warning("Skipping malformed recipe item from Gemini: %s", item)
            continue

    return recipes


# ---------------------------------------------------------------------------
# Step 3b — DB-derived fallback
# ---------------------------------------------------------------------------


def _generate_from_db_candidates(
    *,
    candidates: list[tuple[Recipe, float]],
    sorted_ingredients: list[IngredientInput],
    priority_names: list[str],
    max_recipes: int,
    servings: int,
) -> list[GeneratedRecipe]:
    """Convert top DB catalog recipes into the GeneratedRecipe shape."""
    pantry_lower = {i.name.lower() for i in sorted_ingredients}
    priority_lower = {n.lower() for n in priority_names}
    results: list[GeneratedRecipe] = []

    for recipe, _score in candidates[:max_recipes]:
        ingredients: list[GeneratedRecipeIngredient] = []
        priority_used: list[str] = []

        for ri in recipe.recipe_ingredients:
            if ri.ingredient is None:
                continue
            name = ri.ingredient.name
            name_lower = name.lower()

            in_pantry = any(_fuzzy_match(name_lower, p) for p in pantry_lower)
            is_priority = any(_fuzzy_match(name_lower, p) for p in priority_lower)

            qty_str = None
            if ri.quantity is not None:
                qty_str = f"{ri.quantity} {ri.unit or ''}".strip()

            ingredients.append(
                GeneratedRecipeIngredient(
                    name=name,
                    quantity=qty_str,
                    is_priority=is_priority,
                    available_in_pantry=in_pantry,
                )
            )
            if is_priority:
                priority_used.append(name)

        # Parse instructions into numbered steps
        raw_instructions = recipe.instructions or ""
        steps = [
            line.strip()
            for line in raw_instructions.splitlines()
            if line.strip()
        ] or ["Combine all ingredients and cook until done."]

        results.append(
            GeneratedRecipe(
                title=recipe.title,
                description=f"A recipe using your available pantry ingredients.",
                servings=recipe.servings or servings,
                estimated_cook_time_minutes=recipe.estimated_cook_time_minutes or 30,
                ingredients=ingredients,
                steps=steps,
                priority_ingredients_used=priority_used,
                pantry_coverage_percent=0.0,  # recomputed by caller
            )
        )

    # If the DB has nothing at all, build a minimal recipe from pantry items
    if not results:
        results.append(_minimal_pantry_recipe(sorted_ingredients, priority_names, servings))

    return results


def _minimal_pantry_recipe(
    sorted_ingredients: list[IngredientInput],
    priority_names: list[str],
    servings: int,
) -> GeneratedRecipe:
    """Last-resort recipe built entirely from the pantry list."""
    priority_lower = {n.lower() for n in priority_names}
    ingredients: list[GeneratedRecipeIngredient] = []
    priority_used: list[str] = []

    for item in sorted_ingredients:
        is_priority = item.name.lower() in priority_lower
        qty_str = f"{item.quantity} {item.unit or ''}".strip() if item.quantity else None
        ingredients.append(
            GeneratedRecipeIngredient(
                name=item.name,
                quantity=qty_str,
                is_priority=is_priority,
                available_in_pantry=True,
            )
        )
        if is_priority:
            priority_used.append(item.name)

    return GeneratedRecipe(
        title="Pantry Clear-Out Bowl",
        description=(
            "A flexible recipe that uses your available ingredients, "
            "prioritising items that are expiring soon."
        ),
        servings=servings,
        estimated_cook_time_minutes=20,
        ingredients=ingredients,
        steps=[
            "Prep all vegetables — wash, peel, and chop into bite-sized pieces.",
            "Heat oil in a pan over medium heat.",
            "Add priority ingredients first and cook for 3–4 minutes.",
            "Add remaining ingredients and stir well.",
            "Season with salt and pepper to taste.",
            "Cook until everything is heated through, then serve.",
        ],
        priority_ingredients_used=priority_used,
        pantry_coverage_percent=0.0,  # recomputed by caller
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_coverage(
    ingredients: list[GeneratedRecipeIngredient],
    pantry_name_set: set[str],
) -> float:
    """Percentage of recipe ingredients that are in the pantry."""
    if not ingredients:
        return 0.0
    matched = sum(
        1
        for ing in ingredients
        if any(_fuzzy_match(ing.name.lower(), p) for p in pantry_name_set)
    )
    return round((matched / len(ingredients)) * 100, 1)


def _format_priority_list(ingredients: list[IngredientInput]) -> str:
    priority = [i for i in ingredients if i.priority in _PRIORITY_BUCKETS]
    if not priority:
        return "(none — treat all ingredients equally)"
    lines = []
    for i in priority:
        expiry = (
            f"expires in {i.days_until_expiry} day(s)"
            if i.days_until_expiry is not None
            else "expiry unknown"
        )
        lines.append(f"- {i.name} [{i.priority}] ({expiry})")
    return "\n".join(lines)


def _format_all_list(ingredients: list[IngredientInput]) -> str:
    lines = []
    for i in ingredients:
        qty = f"{i.quantity} {i.unit or ''}".strip() if i.quantity else "unknown qty"
        lines.append(f"- {i.name} ({qty})")
    return "\n".join(lines)


def _format_reference_recipes(candidates: list[tuple[Recipe, float]]) -> str:
    if not candidates:
        return "(no matching catalog recipes found)"
    parts = []
    for recipe, score in candidates:
        ingredient_names = [
            ri.ingredient.name
            for ri in recipe.recipe_ingredients
            if ri.ingredient is not None
        ]
        parts.append(
            f"  Title: {recipe.title} (overlap score: {score:.2f})\n"
            f"  Ingredients: {', '.join(ingredient_names) or 'none'}"
        )
    return "\n\n".join(parts)

