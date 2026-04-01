from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # Ensure model metadata is registered.
from app.core.database import Base
from app.models import Ingredient, PantryItem
from app.schemas.pantry import (
    DetectedIngredientInput,
    ManualCorrectionInput,
    PantryArchiveExpiredResponse,
    PantryConsumeRequest,
    PantryIngestRequest,
    PantryItemUpdate,
)
from app.services.pantry_state import (
    archive_expired_pantry_items,
    consume_pantry_item,
    delete_pantry_item,
    get_ranked_pantry_items,
    ingest_pantry_items,
    update_pantry_item,
)
from app.services.spoilage import (
    HIGH,
    LOW,
    MEDIUM,
    UNKNOWN,
    estimate_expiry_date,
    priority_bucket,
    rank_pantry_items,
)


@dataclass
class PantryStub:
    estimated_expiry_date: date | None
    date_added: date | None
    detected_confidence: float | None
    quantity: float | None
    id: int = 0


class PantryStateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "pantry_test.db"
        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            connect_args={"check_same_thread": False},
        )
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_spoilage_helpers_cover_bucket_and_sort_rules(self) -> None:
        today = date.today()
        self.assertEqual(estimate_expiry_date(today, 5), today + timedelta(days=5))
        self.assertIsNone(estimate_expiry_date(today, None))

        self.assertEqual(priority_bucket(None), UNKNOWN)
        self.assertEqual(priority_bucket(today + timedelta(days=2)), HIGH)
        self.assertEqual(priority_bucket(today + timedelta(days=4)), MEDIUM)
        self.assertEqual(priority_bucket(today + timedelta(days=7)), LOW)

        items = [
            PantryStub(None, today, 0.8, 1, id=3),
            PantryStub(today + timedelta(days=4), today, 0.5, 1, id=2),
            PantryStub(today + timedelta(days=1), today + timedelta(days=1), 0.2, 1, id=1),
        ]

        ranked = rank_pantry_items(items)
        self.assertEqual([item.id for item in ranked], [1, 2, 3])

    def test_ingest_pantry_items_persists_matches_and_returns_unmatched(self) -> None:
        with self.session_factory() as session:
            spinach = Ingredient(
                name="Spinach",
                category="Vegetable",
                standard_unit="g",
                estimated_shelf_life_days=5,
                storage_type="refrigerated",
            )
            session.add(spinach)
            session.commit()

            payload = PantryIngestRequest(
                user_id="demo-user",
                detected_ingredients=[
                    DetectedIngredientInput(
                        detected_name="spinach",
                        quantity=120,
                        unit="g",
                        detected_confidence=0.93,
                    ),
                    DetectedIngredientInput(
                        detected_name="mystery herb",
                        quantity=1,
                        unit="bunch",
                        detected_confidence=0.51,
                    ),
                ],
            )

            items, unmatched = ingest_pantry_items(session, payload)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].ingredient.name, "Spinach")
            self.assertEqual(items[0].detected_confidence, 0.93)
            self.assertEqual(len(unmatched), 1)
            self.assertEqual(unmatched[0].detected_name, "mystery herb")
            self.assertEqual(unmatched[0].reason, "No canonical ingredient match found")

    def test_ingest_uses_category_fallback_when_shelf_life_is_missing(self) -> None:
        with self.session_factory() as session:
            onion = Ingredient(
                name="Onion",
                category="Vegetable",
                standard_unit="g",
                estimated_shelf_life_days=None,
                storage_type="counter",
            )
            session.add(onion)
            session.commit()

            payload = PantryIngestRequest(
                user_id="demo-user",
                detected_ingredients=[
                    DetectedIngredientInput(
                        detected_name="onion",
                        quantity=1,
                        unit="count",
                    )
                ],
            )

            items, unmatched = ingest_pantry_items(session, payload)

            self.assertEqual(len(unmatched), 0)
            self.assertEqual(len(items), 1)
            self.assertEqual(
                items[0].estimated_expiry_date,
                date.today() + timedelta(days=5),
            )

    def test_update_and_consume_pantry_item_keep_lifecycle_consistent(self) -> None:
        with self.session_factory() as session:
            ingredient = Ingredient(
                name="Egg",
                category="Protein",
                standard_unit="count",
                estimated_shelf_life_days=21,
                storage_type="refrigerated",
            )
            session.add(ingredient)
            session.commit()

            pantry_item = PantryItem(
                user_id="demo-user",
                ingredient_id=ingredient.id,
                quantity=6,
                unit="count",
                detected_confidence=0.99,
                date_added=date.today(),
                estimated_expiry_date=date.today() + timedelta(days=10),
                is_priority=False,
            )
            session.add(pantry_item)
            session.commit()

            updated = update_pantry_item(
                session,
                pantry_item.id,
                PantryItemUpdate(quantity=12, unit="eggs"),
            )
            self.assertIsNotNone(updated)
            self.assertEqual(updated.quantity, 12)
            self.assertEqual(updated.unit, "eggs")

            consumed = consume_pantry_item(
                session,
                pantry_item.id,
                PantryConsumeRequest(amount=5),
            )
            self.assertIsNotNone(consumed)
            self.assertFalse(consumed.deleted)
            self.assertIsNotNone(consumed.item)
            self.assertEqual(consumed.item.quantity, 7)

            consumed_all = consume_pantry_item(
                session,
                pantry_item.id,
                PantryConsumeRequest(amount=7),
            )
            self.assertIsNotNone(consumed_all)
            self.assertTrue(consumed_all.deleted)
            self.assertIsNone(consumed_all.item)

    def test_delete_pantry_item_removes_item_from_ranked_view(self) -> None:
        with self.session_factory() as session:
            ingredient = Ingredient(
                name="Cheese",
                category="Dairy",
                standard_unit="g",
                estimated_shelf_life_days=14,
                storage_type="refrigerated",
            )
            session.add(ingredient)
            session.commit()

            pantry_item = PantryItem(
                user_id="demo-user",
                ingredient_id=ingredient.id,
                quantity=200,
                unit="g",
                detected_confidence=0.87,
                date_added=date.today(),
                estimated_expiry_date=date.today() + timedelta(days=6),
                is_priority=False,
            )
            session.add(pantry_item)
            session.commit()

            self.assertEqual(len(get_ranked_pantry_items(session, "demo-user")), 1)
            self.assertTrue(delete_pantry_item(session, pantry_item.id))
            self.assertEqual(len(get_ranked_pantry_items(session, "demo-user")), 0)

    def test_archive_expired_items_excludes_them_from_active_pantry(self) -> None:
        with self.session_factory() as session:
            ingredient = Ingredient(
                name="Tomato",
                category="Vegetable",
                standard_unit="g",
                estimated_shelf_life_days=7,
                storage_type="counter",
            )
            session.add(ingredient)
            session.commit()

            expired_item = PantryItem(
                user_id="demo-user",
                ingredient_id=ingredient.id,
                quantity=2,
                unit="count",
                detected_confidence=0.9,
                source_detected_name="tomato",
                date_added=date.today() - timedelta(days=10),
                estimated_expiry_date=date.today() - timedelta(days=1),
                is_priority=True,
            )
            active_item = PantryItem(
                user_id="demo-user",
                ingredient_id=ingredient.id,
                quantity=1,
                unit="count",
                detected_confidence=0.8,
                source_detected_name="tomato",
                date_added=date.today(),
                estimated_expiry_date=date.today() + timedelta(days=3),
                is_priority=True,
            )
            session.add_all([expired_item, active_item])
            session.commit()

            response = archive_expired_pantry_items(session, "demo-user")
            self.assertIsInstance(response, PantryArchiveExpiredResponse)
            self.assertEqual(response.archived_count, 1)
            self.assertEqual(response.archived_item_ids, [expired_item.id])

            active_items = get_ranked_pantry_items(session, "demo-user")
            self.assertEqual(len(active_items), 1)
            self.assertEqual(active_items[0].id, active_item.id)

            all_items = get_ranked_pantry_items(session, "demo-user", include_inactive=True)
            archived = next(item for item in all_items if item.id == expired_item.id)
            self.assertTrue(archived.is_archived)
            self.assertFalse(archived.is_priority)

    def test_false_positive_dismissal_excludes_item_from_active_pantry(self) -> None:
        with self.session_factory() as session:
            ingredient = Ingredient(
                name="Cheese",
                category="Dairy",
                standard_unit="g",
                estimated_shelf_life_days=14,
                storage_type="refrigerated",
            )
            session.add(ingredient)
            session.commit()

            pantry_item = PantryItem(
                user_id="demo-user",
                ingredient_id=ingredient.id,
                quantity=150,
                unit="g",
                detected_confidence=0.72,
                source_detected_name="shredded cheese",
                date_added=date.today(),
                estimated_expiry_date=date.today() + timedelta(days=5),
                is_priority=True,
            )
            session.add(pantry_item)
            session.commit()

            updated = update_pantry_item(
                session,
                pantry_item.id,
                PantryItemUpdate(is_false_positive=True),
            )
            self.assertIsNotNone(updated)
            self.assertTrue(updated.is_false_positive)
            self.assertFalse(updated.is_priority)

            active_items = get_ranked_pantry_items(session, "demo-user")
            self.assertEqual(len(active_items), 0)

            all_items = get_ranked_pantry_items(session, "demo-user", include_inactive=True)
            self.assertEqual(len(all_items), 1)
            self.assertEqual(all_items[0].source_detected_name, "shredded cheese")
            self.assertTrue(all_items[0].is_false_positive)

    def test_traceability_field_is_persisted_on_ingest(self) -> None:
        with self.session_factory() as session:
            egg = Ingredient(
                name="Egg",
                category="Protein",
                standard_unit="count",
                estimated_shelf_life_days=21,
                storage_type="refrigerated",
            )
            session.add(egg)
            session.commit()

            payload = PantryIngestRequest(
                user_id="demo-user",
                detected_ingredients=[
                    DetectedIngredientInput(
                        detected_name="brown egg",
                        quantity=6,
                        unit="count",
                        detected_confidence=0.88,
                    )
                ],
                manual_corrections=[
                    ManualCorrectionInput(
                        detected_name="brown egg",
                        corrected_name="Egg",
                    )
                ],
            )

            items, unmatched = ingest_pantry_items(session, payload)

            self.assertEqual(len(unmatched), 0)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].ingredient.name, "Egg")
            self.assertEqual(items[0].source_detected_name, "brown egg")


if __name__ == "__main__":
    unittest.main()
