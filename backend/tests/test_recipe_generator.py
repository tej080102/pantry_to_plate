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
