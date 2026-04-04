from __future__ import annotations

import colorsys
import json
import logging
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.schemas.perception import (
    DetectedIngredientRead,
    PerceptionImageMetadataRead,
    PerceptionResultRead,
)


logger = logging.getLogger(__name__)

LOCAL_VISION_MODEL_NAME = "pantry-color-signature-v1"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/gif",
    "image/tiff",
}
IMAGE_FORMAT_TO_MIME_TYPE = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
    "GIF": "image/gif",
    "TIFF": "image/tiff",
}
GEMINI_PERCEPTION_PROMPT = """
You are detecting food ingredients visible in a pantry or fridge photo.

Return only a JSON array. Each item must contain:
- raw_label: short lower-case phrase from the image, such as "spinach" or "olive oil"
- normalized_name: cleaned canonical ingredient name in title case
- confidence: number from 0.0 to 1.0
- quantity_hint: number or null
- unit_hint: short unit string or null

Rules:
- Include only ingredients that are plausibly visible in the image.
- Do not include containers, shelves, or non-food objects.
- Prefer common pantry ingredient names over brands.
- Keep the list concise and high precision.
- If quantity is unclear, use null.
- If no ingredients are confidently visible, return an empty array.
""".strip()
GEMINI_DETECTIONS_JSON_SCHEMA: dict[str, Any] = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "raw_label": {"type": "STRING"},
            "normalized_name": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "quantity_hint": {"type": "NUMBER", "nullable": True},
            "unit_hint": {"type": "STRING", "nullable": True},
        },
        "required": ["raw_label", "normalized_name", "confidence", "quantity_hint", "unit_hint"],
    },
}


class PerceptionProviderError(RuntimeError):
    """Raised when the configured perception provider cannot complete inference."""


@dataclass(frozen=True)
class ColorPrototype:
    rgb: tuple[int, int, int]
    minimum_coverage: float
    weight: float = 1.0


@dataclass(frozen=True)
class IngredientProfile:
    normalized_name: str
    raw_label: str
    quantity_hint: float | None
    unit_hint: str | None
    prototypes: tuple[ColorPrototype, ...]


@dataclass(frozen=True)
class PaletteSwatch:
    rgb: tuple[int, int, int]
    coverage: float


INGREDIENT_PROFILES: tuple[IngredientProfile, ...] = (
    IngredientProfile(
        normalized_name="Spinach",
        raw_label="spinach",
        quantity_hint=120,
        unit_hint="g",
        prototypes=(
            ColorPrototype((60, 120, 55), minimum_coverage=0.16, weight=1.0),
            ColorPrototype((110, 155, 75), minimum_coverage=0.08, weight=0.6),
        ),
    ),
    IngredientProfile(
        normalized_name="Tomato",
        raw_label="tomato",
        quantity_hint=3,
        unit_hint="count",
        prototypes=(
            ColorPrototype((196, 58, 44), minimum_coverage=0.1, weight=1.0),
            ColorPrototype((92, 140, 54), minimum_coverage=0.04, weight=0.35),
        ),
    ),
    IngredientProfile(
        normalized_name="Onion",
        raw_label="onion",
        quantity_hint=1,
        unit_hint="count",
        prototypes=(
            ColorPrototype((214, 190, 142), minimum_coverage=0.1, weight=1.0),
            ColorPrototype((245, 230, 197), minimum_coverage=0.08, weight=0.45),
        ),
    ),
    IngredientProfile(
        normalized_name="Egg",
        raw_label="egg",
        quantity_hint=6,
        unit_hint="count",
        prototypes=(
            ColorPrototype((234, 225, 206), minimum_coverage=0.12, weight=1.0),
            ColorPrototype((245, 195, 88), minimum_coverage=0.04, weight=0.5),
        ),
    ),
    IngredientProfile(
        normalized_name="Cheese",
        raw_label="cheese",
        quantity_hint=80,
        unit_hint="g",
        prototypes=(
            ColorPrototype((245, 196, 61), minimum_coverage=0.1, weight=1.0),
            ColorPrototype((255, 224, 141), minimum_coverage=0.06, weight=0.5),
        ),
    ),
    IngredientProfile(
        normalized_name="Olive Oil",
        raw_label="olive oil",
        quantity_hint=30,
        unit_hint="ml",
        prototypes=(
            ColorPrototype((165, 145, 47), minimum_coverage=0.1, weight=1.0),
            ColorPrototype((214, 190, 92), minimum_coverage=0.06, weight=0.4),
        ),
    ),
)


def detect_ingredients_from_upload(
    *,
    filename: str | None,
    content_type: str | None,
    payload: bytes,
) -> PerceptionResultRead:
    """Validate an uploaded image and infer likely pantry ingredients."""
    _validate_upload(filename=filename, content_type=content_type, payload=payload)
    image, image_format = _open_image(payload)
    resolved_content_type = _resolve_content_type(
        content_type=content_type,
        image_format=image_format,
    )
    image_metadata = PerceptionImageMetadataRead(
        filename=filename,
        content_type=resolved_content_type,
        width=image.width,
        height=image.height,
        bytes=len(payload),
        format=image_format,
    )
    ingredients = _detect_ingredients(
        image=image,
        payload=payload,
        content_type=resolved_content_type,
    )

    return PerceptionResultRead(
        image=image_metadata,
        ingredients=ingredients,
    )


def _detect_ingredients(
    *,
    image: Image.Image,
    payload: bytes,
    content_type: str,
) -> list[DetectedIngredientRead]:
    provider = settings.VISION_PROVIDER.strip().lower()
    if provider in {"local", "local_heuristic", "heuristic"}:
        return _detect_with_local_palette(image)

    if provider in {"gemini", "gemini_vertex", "vertex_ai_gemini", "vertex"}:
        try:
            return _detect_with_gemini_vertex(
                payload=payload,
                content_type=content_type,
            )
        except PerceptionProviderError:
            if not settings.PERCEPTION_ALLOW_LOCAL_FALLBACK:
                raise

            logger.warning(
                "Vertex AI Gemini perception failed; falling back to local heuristic provider.",
                exc_info=True,
            )
            return _detect_with_local_palette(image)

    raise ValueError(
        f"Unsupported VISION_PROVIDER '{settings.VISION_PROVIDER}'. "
        "Use 'gemini_vertex' or 'local_heuristic'."
    )


def _detect_with_gemini_vertex(
    *,
    payload: bytes,
    content_type: str,
) -> list[DetectedIngredientRead]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise PerceptionProviderError(
            "Gemini on Vertex AI requires the 'google-genai' package."
        ) from exc

    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        if not settings.GCP_PROJECT_ID:
            raise PerceptionProviderError(
                "GCP_PROJECT_ID must be set when using Gemini through Vertex AI."
            )
    elif not settings.GOOGLE_API_KEY:
        raise PerceptionProviderError(
            "GOOGLE_API_KEY must be set when using Gemini without Vertex AI."
        )

    try:
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

        client = genai.Client(
            **client_kwargs,
        )
        response = client.models.generate_content(
            model=settings.VISION_MODEL,
            contents=[
                GEMINI_PERCEPTION_PROMPT,
                types.Part.from_bytes(data=payload, mime_type=content_type),
            ],
            config={
                "temperature": 0,
                "response_mime_type": "application/json",
                "response_schema": GEMINI_DETECTIONS_JSON_SCHEMA,
            },
        )
    except Exception as exc:
        raise PerceptionProviderError(
            "Vertex AI Gemini request failed. Verify ADC credentials, "
            "project/region settings, and model access."
        ) from exc

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        response_text = getattr(response, "text", "")
        if not response_text:
            raise PerceptionProviderError("Vertex AI Gemini returned an empty response.")
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise PerceptionProviderError(
                "Vertex AI Gemini returned non-JSON content for structured perception output."
            ) from exc

    return _coerce_gemini_detections(parsed)


def _coerce_gemini_detections(payload: Any) -> list[DetectedIngredientRead]:
    if not isinstance(payload, list):
        raise PerceptionProviderError(
            "Vertex AI Gemini returned an unexpected detection payload shape."
        )

    by_name: dict[str, DetectedIngredientRead] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue

        raw_label = _normalize_label(item.get("raw_label"))
        normalized_name = _normalize_title_case_name(item.get("normalized_name"))
        confidence = _coerce_confidence(item.get("confidence"))
        quantity_hint = _coerce_optional_nonnegative_number(item.get("quantity_hint"))
        unit_hint = _normalize_label(item.get("unit_hint"))

        if not raw_label or not normalized_name or confidence is None:
            continue

        detection = DetectedIngredientRead(
            raw_label=raw_label,
            normalized_name=normalized_name,
            confidence=confidence,
            quantity_hint=quantity_hint,
            unit_hint=unit_hint,
            source_model=settings.VISION_MODEL,
        )
        dedupe_key = normalized_name.lower()
        existing = by_name.get(dedupe_key)
        if existing is None or detection.confidence > existing.confidence:
            by_name[dedupe_key] = detection

    detections = sorted(by_name.values(), key=lambda item: item.confidence, reverse=True)
    return detections[:8]


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().lower().split())
    return normalized or None


def _normalize_title_case_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    return normalized.title() or None


def _coerce_confidence(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(max(0.0, min(1.0, parsed)), 2)


def _coerce_optional_nonnegative_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _resolve_content_type(*, content_type: str | None, image_format: str) -> str:
    if content_type:
        return content_type.lower()
    return IMAGE_FORMAT_TO_MIME_TYPE.get(image_format, "image/png")


def _validate_upload(
    *,
    filename: str | None,
    content_type: str | None,
    payload: bytes,
) -> None:
    if not payload:
        raise ValueError("Uploaded image is empty")

    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded image exceeds the 8 MB size limit")

    if content_type and content_type.lower() not in SUPPORTED_CONTENT_TYPES:
        raise ValueError("Unsupported image content type")

    suffix = Path(filename or "").suffix.lower()
    if suffix and suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported image file extension")


def _open_image(payload: bytes) -> tuple[Image.Image, str]:
    try:
        image = Image.open(BytesIO(payload))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Uploaded file could not be decoded as an image") from exc

    image_format = (image.format or "UNKNOWN").upper()
    image = ImageOps.exif_transpose(image).convert("RGB")
    return image, image_format


def _detect_with_local_palette(image: Image.Image) -> list[DetectedIngredientRead]:
    palette = _extract_palette(image)
    ingredients = _score_palette_against_profiles(palette)
    return ingredients


def _extract_palette(image: Image.Image) -> list[PaletteSwatch]:
    working = image.copy()
    working.thumbnail((160, 160))
    quantized = working.quantize(colors=8)
    paletted = quantized.convert("RGB")
    colors = paletted.getcolors(maxcolors=160 * 160) or []

    if not colors:
        return []

    total_pixels = sum(count for count, _ in colors)
    swatches = [
        PaletteSwatch(rgb=rgb, coverage=count / total_pixels)
        for count, rgb in colors
        if (count / total_pixels) >= 0.03
    ]
    return sorted(swatches, key=lambda swatch: swatch.coverage, reverse=True)


def _score_palette_against_profiles(
    swatches: list[PaletteSwatch],
) -> list[DetectedIngredientRead]:
    detections: list[DetectedIngredientRead] = []
    for profile in INGREDIENT_PROFILES:
        profile_score = _score_profile(profile, swatches)
        if profile_score < 0.58:
            continue

        confidence = round(min(0.99, 0.22 + (profile_score * 0.77)), 2)
        detections.append(
            DetectedIngredientRead(
                raw_label=profile.raw_label,
                normalized_name=profile.normalized_name,
                confidence=confidence,
                quantity_hint=profile.quantity_hint,
                unit_hint=profile.unit_hint,
                source_model=LOCAL_VISION_MODEL_NAME,
            )
        )

    detections.sort(key=lambda item: item.confidence, reverse=True)
    return detections[:5]


def _score_profile(profile: IngredientProfile, swatches: list[PaletteSwatch]) -> float:
    if not swatches:
        return 0.0

    weighted_total = 0.0
    weight_sum = 0.0
    for prototype in profile.prototypes:
        best_match = max(
            (
                _color_similarity(swatch.rgb, prototype.rgb)
                * min(1.0, swatch.coverage / prototype.minimum_coverage)
            )
            for swatch in swatches
        )
        weighted_total += best_match * prototype.weight
        weight_sum += prototype.weight

    if not weight_sum:
        return 0.0
    return weighted_total / weight_sum


def _color_similarity(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    left_hsv = colorsys.rgb_to_hsv(*(channel / 255 for channel in left))
    right_hsv = colorsys.rgb_to_hsv(*(channel / 255 for channel in right))

    hue_distance = min(abs(left_hsv[0] - right_hsv[0]), 1 - abs(left_hsv[0] - right_hsv[0]))
    saturation_distance = abs(left_hsv[1] - right_hsv[1])
    value_distance = abs(left_hsv[2] - right_hsv[2])

    rgb_distance = math.sqrt(
        sum(((left_channel - right_channel) / 255) ** 2 for left_channel, right_channel in zip(left, right))
    ) / math.sqrt(3)

    score = 1 - (
        (hue_distance / 0.5) * 0.45
        + saturation_distance * 0.2
        + value_distance * 0.15
        + rgb_distance * 0.2
    )
    return max(0.0, min(1.0, score))
