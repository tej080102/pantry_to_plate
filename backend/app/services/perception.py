from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.perception import (
    DetectedIngredientRead,
    PerceptionImageMetadataRead,
    PerceptionResultRead,
)

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
    palette = _extract_palette(image)
    ingredients = _score_palette_against_profiles(palette)

    return PerceptionResultRead(
        image=PerceptionImageMetadataRead(
            filename=filename,
            content_type=content_type,
            width=image.width,
            height=image.height,
            bytes=len(payload),
            format=image_format,
        ),
        ingredients=ingredients,
    )


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
