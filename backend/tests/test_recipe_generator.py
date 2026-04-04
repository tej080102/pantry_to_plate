from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.exc import OperationalError

from app.schemas.recipe import RecipeGenerateRequest
from app.services import recipe_generator


class RecipeGeneratorTestCase(unittest.TestCase):
    def test_coerce_gemini_recipes_strips_redundant_step_numbering(self) -> None:
        recipes = recipe_generator._coerce_gemini_recipes(
            [
                {
                    "title": "Cheese Toast",
                    "description": "Simple toast.",
                    "servings": 2,
                    "estimated_cook_time_minutes": 10,
                    "ingredients": [
                        {
                            "name": "Bread",
                            "quantity": "2 slices",
                            "is_priority": False,
                            "available_in_pantry": True,
                        }
                    ],
                    "steps": [
                        "1. 1. Lightly oil one side of each bread slice.",
                        "Step 2: Toast until golden.",
                        "- Serve warm.",
                    ],
                    "priority_ingredients_used": [],
                    "pantry_coverage_percent": 100,
                }
            ]
        )

        self.assertEqual(
            recipes[0].steps,
            [
                "Lightly oil one side of each bread slice.",
                "Toast until golden.",
                "Serve warm.",
            ],
        )

    def test_generate_recipes_falls_back_when_catalog_lookup_fails(self) -> None:
        payload = RecipeGenerateRequest(
            ingredients=[
                {
                    "name": "Spinach",
                    "quantity": 120,
                    "unit": "g",
                    "priority": "HIGH",
                    "days_until_expiry": 1,
                },
                {
                    "name": "Egg",
                    "quantity": 6,
                    "unit": "count",
                    "priority": "MEDIUM",
                    "days_until_expiry": 3,
                },
            ],
            max_recipes=3,
            servings=2,
        )

        with (
            mock.patch.object(
                recipe_generator,
                "_find_candidate_recipes",
                side_effect=OperationalError("SELECT 1", {}, Exception("db down")),
            ),
            mock.patch.object(
                recipe_generator,
                "_generate_with_gemini",
                side_effect=RuntimeError("gemini unavailable"),
            ),
        ):
            response = recipe_generator.generate_recipes(mock.Mock(), payload)

        self.assertEqual(response.generation_method, "db_fallback")
        self.assertEqual(response.priority_ingredients, ["Spinach", "Egg"])
        self.assertEqual(len(response.recipes), 1)

        recipe = response.recipes[0]
        self.assertEqual(recipe.title, "Pantry Clear-Out Bowl")
        self.assertEqual(recipe.pantry_coverage_percent, 100.0)
        self.assertEqual(recipe.priority_ingredients_used, ["Spinach", "Egg"])


if __name__ == "__main__":
    unittest.main()
