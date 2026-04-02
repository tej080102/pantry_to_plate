from __future__ import annotations

import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes.perception import router as perception_router
from app.core.config import settings
from app.schemas.perception import DetectedIngredientRead
from app.services import perception as perception_service
from app.services.perception import PerceptionProviderError


class PerceptionApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.include_router(perception_router)
        cls.client = TestClient(app)

    def test_detect_returns_structured_output_with_confidence_scores(self) -> None:
        image_bytes = self._make_split_image()

        with mock.patch.object(settings, "VISION_PROVIDER", "local_heuristic"):
            response = self.client.post(
                "/perception/detect",
                files={"file": ("pantry.png", image_bytes, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("image", payload)
        self.assertIn("ingredients", payload)
        self.assertGreaterEqual(len(payload["ingredients"]), 1)
        self.assertEqual(payload["image"]["format"], "PNG")

        ingredient_names = {item["normalized_name"] for item in payload["ingredients"]}
        self.assertTrue({"Spinach", "Tomato"} & ingredient_names)
        for item in payload["ingredients"]:
            self.assertIn("confidence", item)
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 1)
            self.assertIn("source_model", item)

    def test_detect_can_identify_a_red_tomato_like_image(self) -> None:
        image_bytes = self._make_solid_image((205, 52, 42))

        with mock.patch.object(settings, "VISION_PROVIDER", "local_heuristic"):
            response = self.client.post(
                "/perception/detect",
                files={"file": ("tomato.png", image_bytes, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["ingredients"]), 1)
        top_hit = payload["ingredients"][0]
        self.assertEqual(top_hit["normalized_name"], "Tomato")
        self.assertIsNotNone(top_hit["quantity_hint"])
        self.assertEqual(top_hit["unit_hint"], "count")

    def test_detect_rejects_non_image_uploads(self) -> None:
        with mock.patch.object(settings, "VISION_PROVIDER", "local_heuristic"):
            response = self.client.post(
                "/perception/detect",
                files={"file": ("notes.txt", b"not-an-image", "text/plain")},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported image content type", response.json()["detail"])

    def test_detect_uses_gemini_vertex_when_configured(self) -> None:
        image_bytes = self._make_solid_image((205, 52, 42))
        gemini_detection = DetectedIngredientRead(
            raw_label="tomato",
            normalized_name="Tomato",
            confidence=0.93,
            quantity_hint=3,
            unit_hint="count",
            source_model="gemini-2.5-flash",
        )

        with (
            mock.patch.object(settings, "VISION_PROVIDER", "gemini_vertex"),
            mock.patch.object(settings, "GCP_PROJECT_ID", "demo-project"),
            mock.patch.object(
                perception_service,
                "_detect_with_gemini_vertex",
                return_value=[gemini_detection],
            ) as mocked_provider,
        ):
            response = self.client.post(
                "/perception/detect",
                files={"file": ("tomato.png", image_bytes, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ingredients"][0]["normalized_name"], "Tomato")
        self.assertEqual(payload["ingredients"][0]["source_model"], "gemini-2.5-flash")
        mocked_provider.assert_called_once()

    def test_detect_returns_503_when_gemini_provider_fails_without_fallback(self) -> None:
        image_bytes = self._make_solid_image((205, 52, 42))

        with (
            mock.patch.object(settings, "VISION_PROVIDER", "gemini_vertex"),
            mock.patch.object(settings, "GCP_PROJECT_ID", "demo-project"),
            mock.patch.object(settings, "PERCEPTION_ALLOW_LOCAL_FALLBACK", False),
            mock.patch.object(
                perception_service,
                "_detect_with_gemini_vertex",
                side_effect=PerceptionProviderError("Vertex AI Gemini request failed"),
            ),
        ):
            response = self.client.post(
                "/perception/detect",
                files={"file": ("tomato.png", image_bytes, "image/png")},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Vertex AI Gemini request failed", response.json()["detail"])

    def _make_solid_image(self, color: tuple[int, int, int]) -> bytes:
        image = Image.new("RGB", (96, 96), color=color)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _make_split_image(self) -> bytes:
        image = Image.new("RGB", (120, 80))
        for x in range(image.width):
            for y in range(image.height):
                image.putpixel((x, y), (50, 122, 48) if x < image.width // 2 else (204, 54, 44))

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
