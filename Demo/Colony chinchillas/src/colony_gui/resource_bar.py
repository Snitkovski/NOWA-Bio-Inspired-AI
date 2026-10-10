"""Resource panel helpers."""

from __future__ import annotations

from .utils import clamp01


class ResourceBar:
    """Clamp and expose normalized resource values."""

    @staticmethod
    def clamp_level(value: float) -> float:
        return clamp01(value)

