"""Confidence classification rules — centralized."""

from __future__ import annotations

from typing import Literal

ConfidenceLevel = Literal["alta", "media", "baja", "insuficiente"]

_ORDER: tuple[ConfidenceLevel, ...] = ("insuficiente", "baja", "media", "alta")


def _base_level(n: int) -> ConfidenceLevel:
    if n >= 8:
        return "alta"
    if n >= 4:
        return "media"
    if n >= 1:
        return "baja"
    return "insuficiente"


def classify_confidence(n: int, fallback_to_city: bool) -> ConfidenceLevel:
    """Apply the confidence table; downgrade one level when we had to
    widen the search from zone to city.

    Downgrade rules:
        alta  -> media
        media -> baja
        baja  -> baja          (already lowest non-empty level)
        insuficiente -> insuficiente
    """
    level = _base_level(n)
    if not fallback_to_city or level == "insuficiente":
        return level

    idx = _ORDER.index(level)
    return _ORDER[max(1, idx - 1)]  # never drop below "baja"
