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