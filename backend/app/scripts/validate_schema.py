"""Local-only schema validation script.

This utility may drop and recreate tables in the configured SQLite database.
Use it only for local development and demonstration data setup.
"""

from __future__ import annotations

from datetime import date, timedelta

import app.models  # Ensure all model metadata is registered.
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import Ingredient, IngredientNutrition, PantryItem, Recipe, RecipeIngredient


def reset_schema() -> None:
    """Recreate tables for a repeatable local validation run."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        raise RuntimeError(
            "validate_schema.py is intended for local SQLite development only. "
            "Point DATABASE_URL at SQLite before running it."
        )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_data() -> None:
    """Insert a small, readable sample dataset."""
    with SessionLocal() as db:
        spinach = Ingredient(
            name="Spinach",
            category="Vegetable",
            standard_unit="g",
            estimated_shelf_life_days=5,
            storage_type="refrigerated",
            nutrition=IngredientNutrition(
                calories_per_100g=23.0,
                protein_per_100g=2.9,
                carbs_per_100g=3.6,
                fat_per_100g=0.4,
                fiber_per_100g=2.2,
            ),
        )
        onion = Ingredient(
            name="Onion",
            category="Vegetable",
            standard_unit="g",
            estimated_shelf_life_days=14,
            storage_type="counter",
            nutrition=IngredientNutrition(
                calories_per_100g=40.0,
                protein_per_100g=1.1,
                carbs_per_100g=9.3,
                fat_per_100g=0.1,
                fiber_per_100g=1.7,
            ),
        )
        tomato = Ingredient(
            name="Tomato",
            category="Vegetable",
            standard_unit="g",
            estimated_shelf_life_days=7,
            storage_type="counter",
            nutrition=IngredientNutrition(
                calories_per_100g=18.0,
                protein_per_100g=0.9,
                carbs_per_100g=3.9,
                fat_per_100g=0.2,
                fiber_per_100g=1.2,
            ),
        )
        egg = Ingredient(
            name="Egg",
            category="Protein",
            standard_unit="count",
            estimated_shelf_life_days=21,
            storage_type="refrigerated",
            nutrition=IngredientNutrition(
                calories_per_100g=155.0,
                protein_per_100g=13.0,
                carbs_per_100g=1.1,
                fat_per_100g=11.0,
                fiber_per_100g=0.0,
            ),
        )
        cheese = Ingredient(
            name="Cheese",
            category="Dairy",
            standard_unit="g",
            estimated_shelf_life_days=21,
            storage_type="refrigerated",
            nutrition=IngredientNutrition(
                calories_per_100g=402.0,
                protein_per_100g=25.0,
                carbs_per_100g=1.3,
                fat_per_100g=33.0,
                fiber_per_100g=0.0,
            ),
        )
        olive_oil = Ingredient(
            name="Olive Oil",
            category="Pantry",
            standard_unit="ml",
            estimated_shelf_life_days=365,
            storage_type="pantry",
            nutrition=IngredientNutrition(
                calories_per_100g=884.0,
                protein_per_100g=0.0,
                carbs_per_100g=0.0,
                fat_per_100g=100.0,
                fiber_per_100g=0.0,
            ),
        )

        salad = Recipe(
            title="Simple Spinach Tomato Salad",
            source_name="pantry_to_plate_demo",
            source_url="https://example.com/spinach-tomato-salad",
            instructions="Combine chopped spinach and tomato, then drizzle with olive oil.",
            estimated_cook_time_minutes=10,
            servings=2,
            recipe_ingredients=[
                RecipeIngredient(quantity=100, unit="g", ingredient=spinach),
                RecipeIngredient(quantity=150, unit="g", ingredient=tomato),
                RecipeIngredient(quantity=15, unit="ml", ingredient=olive_oil),
            ],
        )

        today = date.today()
        pantry_items = [
            PantryItem(
                user_id="demo-user",
                ingredient=spinach,
                quantity=200,
                unit="g",
                detected_confidence=0.98,
                date_added=today,
                estimated_expiry_date=today + timedelta(days=3),
                is_priority=True,
            ),
            PantryItem(
                user_id="demo-user",
                ingredient=tomato,
                quantity=4,
                unit="count",
                detected_confidence=0.94,
                date_added=today,
                estimated_expiry_date=today + timedelta(days=5),
                is_priority=False,
            ),
            PantryItem(
                user_id="demo-user",
                ingredient=egg,
                quantity=6,
                unit="count",
                detected_confidence=0.97,
                date_added=today,
                estimated_expiry_date=today + timedelta(days=10),
                is_priority=False,
            ),
            PantryItem(
                user_id="demo-user",
                ingredient=olive_oil,
                quantity=250,
                unit="ml",
                detected_confidence=0.99,
                date_added=today,
                estimated_expiry_date=today + timedelta(days=120),
                is_priority=False,
            ),
        ]

        db.add_all([salad, *pantry_items])
        db.commit()


def print_ingredients_with_nutrition() -> None:
    print("\nIngredients with nutrition")
    print("-" * 32)
    with SessionLocal() as db:
        ingredients = db.query(Ingredient).order_by(Ingredient.name.asc()).all()
        for ingredient in ingredients:
            nutrition = ingredient.nutrition
            if nutrition is None:
                print(f"{ingredient.name}: no nutrition row")
                continue
            print(
                f"{ingredient.name} | calories={nutrition.calories_per_100g} "
                f"protein={nutrition.protein_per_100g} carbs={nutrition.carbs_per_100g} "
                f"fat={nutrition.fat_per_100g} fiber={nutrition.fiber_per_100g}"
            )


def print_recipe_with_ingredients() -> None:
    print("\nOne recipe with ingredients")
    print("-" * 30)
    with SessionLocal() as db:
        recipe = db.query(Recipe).filter(Recipe.title == "Simple Spinach Tomato Salad").first()
        if recipe is None:
            print("Recipe not found")
            return
        print(f"{recipe.title} ({recipe.servings} servings)")
        for recipe_ingredient in recipe.recipe_ingredients:
            print(
                f"- {recipe_ingredient.quantity} {recipe_ingredient.unit} "
                f"{recipe_ingredient.ingredient.name}"
            )


def print_pantry_by_expiry() -> None:
    print("\nPantry items by estimated expiry date")
    print("-" * 37)
    with SessionLocal() as db:
        pantry_items = (
            db.query(PantryItem)
            .order_by(PantryItem.estimated_expiry_date.asc(), PantryItem.id.asc())
            .all()
        )
        for item in pantry_items:
            print(
                f"{item.estimated_expiry_date} | {item.ingredient.name} | "
                f"{item.quantity} {item.unit} | priority={item.is_priority}"
            )


def main() -> None:
    reset_schema()
    seed_data()
    print_ingredients_with_nutrition()
    print_recipe_with_ingredients()
    print_pantry_by_expiry()


if __name__ == "__main__":
    main()
