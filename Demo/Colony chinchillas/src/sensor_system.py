"""Perception helpers for colony simulation."""

from __future__ import annotations

ADJACENT_ZONES: dict[str, set[str]] = {
    "floor": {"house", "bowl_pellets", "bowl_hay", "wheel", "dustbath", "corner", "toy"},
    "house": {"floor", "corner", "dustbath", "litter"},
    "wheel": {"floor", "shelf_lower"},
    "shelf_lower": {"wheel", "floor", "shelf_mid"},
    "shelf_mid": {"shelf_lower", "shelf_upper"},
    "shelf_upper": {"shelf_mid"},
    "dustbath": {"floor", "house"},
    "corner": {"floor", "house", "litter"},
    "bowl_pellets": {"floor", "bowl_hay"},
    "bowl_hay": {"floor", "bowl_pellets", "waterer"},
    "waterer": {"bowl_hay"},
    "litter": {"corner", "bars"},
    "bars": {"litter", "door"},
    "door": {"bars"},
    "toy": {"floor"},
    "mineral": {"floor"},
}


def is_same_or_adjacent(source: str, target: str) -> bool:
    """Return True when positions are in contact radius."""
    if source == target:
        return True
    return target in ADJACENT_ZONES.get(source, set())
