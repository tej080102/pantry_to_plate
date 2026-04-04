from __future__ import annotations

import re
from collections.abc import Iterable

from app.models import Ingredient

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_NOISE_TOKENS = {
    "a",
    "an",
    "and",
    "or",
    "with",
    "without",
    "the",
    "fresh",
    "frozen",
    "prepared",
    "heated",
    "cooked",
    "boiled",
    "drained",
    "dried",
    "grated",
    "shredded",
    "chopped",
    "diced",
    "sliced",
    "pasteurized",
    "grade",
    "large",
    "medium",
    "small",
    "whole",
    "part",
    "skim",
    "low",
    "lowfat",
    "fortified",
    "restaurant",
    "only",
    "salad",
    "cooking",
}
_PROCESSED_TOKENS = {
    "breaded",
    "fried",
    "frozen",
    "prepared",
    "heated",
    "cooked",
    "drained",
    "dried",
    "restaurant",
    "fortified",
    "pasteurized",
}
_PREFERRED_TOKENS = {"raw", "fresh"}
_EXPLICIT_SINGULARS = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "onions": "onion",
    "eggs": "egg",
    "olives": "olive",
    "cheeses": "cheese",
}


def normalize_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower()))


def tokenize_significant(value: str) -> tuple[str, ...]:
    tokens = []
    for token in _TOKEN_RE.findall(value.lower()):
        singular = _singularize_token(token)
        if singular and singular not in _NOISE_TOKENS:
            tokens.append(singular)
    return tuple(_dedupe_preserving_order(tokens))


def ingredient_names_match(left: str, right: str) -> bool:
    left_tokens = set(tokenize_significant(left))
    right_tokens = set(tokenize_significant(right))
    if not left_tokens or not right_tokens:
        return normalize_text(left) == normalize_text(right)

    shared = left_tokens & right_tokens
    if not shared:
        return False

    return left_tokens.issubset(right_tokens) or right_tokens.issubset(left_tokens)


def resolve_ingredient_by_name(
    ingredients: Iterable[Ingredient],
    candidate_name: str,
) -> Ingredient | None:
    normalized_candidate = normalize_text(candidate_name)
    candidate_tokens = set(tokenize_significant(candidate_name))
    if not normalized_candidate:
        return None

    best_match: Ingredient | None = None
    best_score: tuple[float, ...] | None = None

    for ingredient in ingredients:
        score = _score_ingredient_match(
            ingredient=ingredient,
            normalized_candidate=normalized_candidate,
            candidate_tokens=candidate_tokens,
        )
        if score is None:
            continue
        if best_score is None or score > best_score:
            best_match = ingredient
            best_score = score

    return best_match


def _score_ingredient_match(
    *,
    ingredient: Ingredient,
    normalized_candidate: str,
    candidate_tokens: set[str],
) -> tuple[float, ...] | None:
    normalized_name = normalize_text(ingredient.name)
    alias_phrases = _ingredient_alias_phrases(ingredient.name)
    if normalized_candidate == normalized_name:
        return (10.0, 10.0, 10.0, 0.0, 0.0)
    if normalized_candidate in alias_phrases:
        return (9.0, 9.0, 9.0, 0.0, -len(normalized_name))

    if not candidate_tokens:
        return None

    processed_penalty = sum(
        1 for token in _TOKEN_RE.findall(ingredient.name.lower()) if token in _PROCESSED_TOKENS
    )
    preferred_bonus = sum(
        1 for token in _TOKEN_RE.findall(ingredient.name.lower()) if token in _PREFERRED_TOKENS
    )

    best_score: tuple[float, ...] | None = None
    for alias_phrase in alias_phrases:
        alias_tokens = set(tokenize_significant(alias_phrase))
        if not alias_tokens:
            continue
        shared = candidate_tokens & alias_tokens
        if not shared:
            continue

        candidate_coverage = len(shared) / len(candidate_tokens)
        alias_coverage = len(shared) / len(alias_tokens)
        subset_bonus = 1.0 if candidate_tokens.issubset(alias_tokens) else 0.0
        extra_tokens = len(alias_tokens - shared)

        score = (
            subset_bonus,
            candidate_coverage,
            alias_coverage,
            preferred_bonus,
            -processed_penalty,
            -extra_tokens,
            -len(alias_phrase),
        )
        if best_score is None or score > best_score:
            best_score = score

    if best_score is None:
        return None

    if best_score[1] < 0.5:
        return None
    return best_score


def _ingredient_alias_phrases(name: str) -> set[str]:
    aliases: set[str] = set()
    normalized_name = normalize_text(name)
    if normalized_name:
        aliases.add(normalized_name)

    chunks = [chunk.strip() for chunk in name.split(",") if chunk.strip()]
    significant_chunks = [tokenize_significant(chunk) for chunk in chunks]
    meaningful_chunks = [chunk for chunk in significant_chunks if chunk]
    if not meaningful_chunks:
        return aliases

    base_tokens = meaningful_chunks[0]
    aliases.add(" ".join(base_tokens))
    aliases.add(base_tokens[0])

    for chunk_tokens in meaningful_chunks[1:]:
        aliases.add(" ".join(chunk_tokens))
        aliases.add(chunk_tokens[-1])
        combined = tuple(_dedupe_preserving_order([*chunk_tokens, base_tokens[0]]))
        aliases.add(" ".join(combined))

    collapsed_tokens = tuple(_dedupe_preserving_order(token for chunk in meaningful_chunks for token in chunk))
    aliases.add(" ".join(collapsed_tokens))
    return {alias for alias in aliases if alias}


def _singularize_token(token: str) -> str:
    if token in _EXPLICIT_SINGULARS:
        return _EXPLICIT_SINGULARS[token]
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("oes") and len(token) > 4:
        return f"{token[:-2]}"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
