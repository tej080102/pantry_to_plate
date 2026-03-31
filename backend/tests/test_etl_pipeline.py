from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.etl.cli import main
from app.etl.db import build_session_factory, initialize_database
from app.etl.load import load_ingredient_records
from app.etl.tracking import ETLTracker
from app.etl.transform import transform_usda_foundation
from app.etl.types import NormalizedIngredientRecord
from app.models import ETLRun, Ingredient, IngredientNutrition


class ETLPipelineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.raw_dir = self.workspace / "raw"
        self.clean_dir = self.workspace / "clean"
        self.raw_dir.mkdir()
        self.clean_dir.mkdir()
        self.database_path = self.workspace / "etl.db"
        self.database_url = f"sqlite:///{self.database_path}"
        self.engine, self.session_factory = build_session_factory(self.database_url)
        initialize_database(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_transform_pivots_nutrients_deduplicates_and_writes_clean_csv(self) -> None:
        self._write_usda_fixture(include_portions=True)
        output_file = self.clean_dir / "normalized.csv"

        batch, stats = transform_usda_foundation(self.raw_dir, output_file)

        self.assertEqual(stats.rows_read, 3)
        self.assertEqual(stats.rows_dropped, 1)
        self.assertEqual(stats.rows_deduplicated, 1)
        self.assertEqual(stats.rows_written, 1)
        self.assertEqual(len(batch.ingredients), 1)

        apple = batch.ingredients[0]
        self.assertEqual(apple.name, "Apple")
        self.assertEqual(apple.category, "Fruit")
        self.assertEqual(apple.standard_unit, "cup")
        self.assertEqual(apple.calories_per_100g, 53.0)
        self.assertEqual(apple.protein_per_100g, 0.4)
        self.assertEqual(apple.carbs_per_100g, 14.0)
        self.assertEqual(apple.fat_per_100g, 0.1)
        self.assertEqual(apple.fiber_per_100g, 2.6)
        self.assertTrue(output_file.exists())

    def test_transform_defaults_standard_unit_to_grams_when_portion_files_missing(self) -> None:
        self._write_usda_fixture(include_portions=False)
        output_file = self.clean_dir / "normalized.csv"

        batch, stats = transform_usda_foundation(self.raw_dir, output_file)

        self.assertEqual(stats.rows_written, 1)
        self.assertEqual(batch.ingredients[0].standard_unit, "g")

    def test_loader_inserts_and_updates_without_duplicates(self) -> None:
        records = [
            NormalizedIngredientRecord(
                name="Apple",
                category="Fruit",
                standard_unit="g",
                calories_per_100g=52.0,
                protein_per_100g=0.3,
                carbs_per_100g=14.0,
                fat_per_100g=0.2,
                fiber_per_100g=2.4,
            )
        ]

        first_stats = load_ingredient_records(records, self.session_factory)
        second_stats = load_ingredient_records(
            [
                NormalizedIngredientRecord(
                    name="Apple",
                    category="Fresh Fruit",
                    standard_unit="cup",
                    calories_per_100g=60.0,
                    protein_per_100g=0.5,
                    carbs_per_100g=15.0,
                    fat_per_100g=0.3,
                    fiber_per_100g=3.0,
                )
            ],
            self.session_factory,
        )

        self.assertEqual(first_stats.inserted, 1)
        self.assertEqual(first_stats.updated, 0)
        self.assertEqual(second_stats.inserted, 0)
        self.assertEqual(second_stats.updated, 1)

        with self.session_factory() as session:
            ingredients = session.query(Ingredient).all()
            self.assertEqual(len(ingredients), 1)
            self.assertEqual(ingredients[0].category, "Fresh Fruit")
            self.assertEqual(ingredients[0].standard_unit, "cup")
            self.assertIsNotNone(ingredients[0].nutrition)
            self.assertEqual(ingredients[0].nutrition.calories_per_100g, 60.0)
            self.assertEqual(ingredients[0].nutrition.protein_per_100g, 0.5)
            self.assertEqual(session.query(IngredientNutrition).count(), 1)

    def test_loader_rolls_back_when_commit_fails(self) -> None:
        records = [
            NormalizedIngredientRecord(
                name="Apple",
                category="Fruit",
                standard_unit="g",
                calories_per_100g=52.0,
                protein_per_100g=0.3,
                carbs_per_100g=14.0,
                fat_per_100g=0.2,
                fiber_per_100g=2.4,
            )
        ]

        with mock.patch("sqlalchemy.orm.session.Session.commit", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                load_ingredient_records(records, self.session_factory)

        with self.session_factory() as session:
            self.assertEqual(session.query(Ingredient).count(), 0)

    def test_tracker_records_success_and_failure_statuses(self) -> None:
        tracker = ETLTracker(self.session_factory)
        success_run = tracker.start_run("usda_foundation", self.raw_dir)
        tracker.mark_success(success_run.id, self.clean_dir / "normalized.csv", 7)

        failed_run = tracker.start_run("usda_foundation", self.raw_dir)
        tracker.mark_failure(failed_run.id, None, "transform failed")

        with self.session_factory() as session:
            runs = session.query(ETLRun).order_by(ETLRun.id.asc()).all()
            self.assertEqual(len(runs), 2)
            self.assertEqual(runs[0].status, "SUCCESS")
            self.assertEqual(runs[0].records_processed, 7)
            self.assertTrue(runs[0].clean_gcs_path.endswith("normalized.csv"))
            self.assertEqual(runs[1].status, "FAILED")
            self.assertEqual(runs[1].error_message, "transform failed")

    def test_cli_smoke_run_transforms_loads_and_tracks(self) -> None:
        self._write_usda_fixture(include_portions=True)
        exit_code = main(
            [
                "--database-url",
                self.database_url,
                "run-usda-foundation",
                "--raw-dir",
                str(self.raw_dir),
                "--clean-dir",
                str(self.clean_dir),
            ]
        )

        self.assertEqual(exit_code, 0)

        with self.session_factory() as session:
            self.assertEqual(session.query(Ingredient).count(), 1)
            runs = session.query(ETLRun).all()
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0].status, "SUCCESS")
            self.assertEqual(runs[0].records_processed, 1)

        clean_files = list(self.clean_dir.glob("ingredients_*.csv"))
        self.assertEqual(len(clean_files), 1)
        self.assertTrue(clean_files[0].exists())

    def _write_usda_fixture(self, include_portions: bool) -> None:
        self._write_csv(
            self.raw_dir / "food.csv",
            ["fdc_id", "description", "food_category_id", "data_type"],
            [
                {"fdc_id": "100", "description": " APPLE ", "food_category_id": "1", "data_type": "Foundation"},
                {"fdc_id": "101", "description": "APPLE", "food_category_id": "1", "data_type": "Foundation"},
                {"fdc_id": "102", "description": "Spinach", "food_category_id": "2", "data_type": "Foundation"},
            ],
        )
        self._write_csv(
            self.raw_dir / "food_category.csv",
            ["id", "description"],
            [
                {"id": "1", "description": "Fruit"},
                {"id": "2", "description": "Vegetable"},
            ],
        )
        self._write_csv(
            self.raw_dir / "nutrient.csv",
            ["id", "name"],
            [
                {"id": "1008", "name": "Energy"},
                {"id": "1003", "name": "Protein"},
                {"id": "1005", "name": "Carbohydrate, by difference"},
                {"id": "1004", "name": "Total lipid (fat)"},
                {"id": "1079", "name": "Fiber, total dietary"},
            ],
        )
        self._write_csv(
            self.raw_dir / "food_nutrient.csv",
            ["fdc_id", "nutrient_id", "amount"],
            [
                {"fdc_id": "100", "nutrient_id": "1008", "amount": "52"},
                {"fdc_id": "100", "nutrient_id": "1003", "amount": "0.3"},
                {"fdc_id": "100", "nutrient_id": "1005", "amount": "13.8"},
                {"fdc_id": "100", "nutrient_id": "1004", "amount": "0.2"},
                {"fdc_id": "101", "nutrient_id": "1008", "amount": "53"},
                {"fdc_id": "101", "nutrient_id": "1003", "amount": "0.4"},
                {"fdc_id": "101", "nutrient_id": "1005", "amount": "14.0"},
                {"fdc_id": "101", "nutrient_id": "1004", "amount": "0.1"},
                {"fdc_id": "101", "nutrient_id": "1079", "amount": "2.6"},
                {"fdc_id": "102", "nutrient_id": "1008", "amount": "23"},
                {"fdc_id": "102", "nutrient_id": "1003", "amount": "2.9"},
            ],
        )

        if include_portions:
            self._write_csv(
                self.raw_dir / "food_portion.csv",
                ["id", "fdc_id", "measure_unit_id", "seq_num"],
                [
                    {"id": "1", "fdc_id": "101", "measure_unit_id": "10", "seq_num": "1"},
                ],
            )
            self._write_csv(
                self.raw_dir / "measure_unit.csv",
                ["id", "name"],
                [
                    {"id": "10", "name": "Cup"},
                ],
            )

    def _write_csv(
        self,
        path: Path,
        fieldnames: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
