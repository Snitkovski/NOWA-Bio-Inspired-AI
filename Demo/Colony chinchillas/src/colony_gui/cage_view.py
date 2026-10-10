"""Cage-space helpers for GUI placement."""

from __future__ import annotations

import random
from typing import Optional

from .config import (
    WINDOW_SIZE,
    ZONE_RENDER_COORDS,
    ZONE_SLOT_OFFSETS,
    ZONE_SLOT_OFFSETS_BY_ZONE,
)

_OVERFLOW_OFFSET_CACHE: dict[tuple[str, str, int], tuple[int, int]] = {}
_UNKNOWN_OFFSET_CACHE: dict[tuple[str, str], tuple[int, int]] = {}


def _clamp_position(x: int, y: int) -> tuple[int, int]:
    width, height = WINDOW_SIZE
    return (max(0, min(width, x)), max(0, min(height, y)))


def _seeded_overflow_offset(agent_id: str, zone: str, index: int) -> tuple[int, int]:
    key = (str(zone), str(agent_id), int(index))
    cached = _OVERFLOW_OFFSET_CACHE.get(key)
    if cached is not None:
        return cached
    seeded = random.Random(f"{zone}:{agent_id}:{index}")
    value = (seeded.randint(-30, 30), seeded.randint(-5, 5))
    _OVERFLOW_OFFSET_CACHE[key] = value
    return value


def _seeded_unknown_offset(agent_id: str, zone: str) -> tuple[int, int]:
    key = (str(zone), str(agent_id))
    cached = _UNKNOWN_OFFSET_CACHE.get(key)
    if cached is not None:
        return cached
    seeded = random.Random(f"{zone}:{agent_id}:unknown")
    value = (seeded.randint(-30, 30), seeded.randint(-30, 30))
    _UNKNOWN_OFFSET_CACHE[key] = value
    return value


def get_zone_render_pos(
    zone: str,
    agent_index: int = 0,
    agent_id: Optional[str] = None,
) -> tuple[int, int]:
    """Resolve render position in cage coordinates for one agent."""
    safe_zone = str(zone)
    base = ZONE_RENDER_COORDS.get(safe_zone)
    if base is None:
        fallback = ZONE_RENDER_COORDS["floor"]
        assert fallback is not None
        dx, dy = _seeded_unknown_offset(agent_id or "unknown", safe_zone)
        return _clamp_position(fallback[0] + dx, fallback[1] + dy)

    index = max(0, int(agent_index))
    offsets = ZONE_SLOT_OFFSETS_BY_ZONE.get(safe_zone, ZONE_SLOT_OFFSETS)
    if index < len(offsets):
        dx, dy = offsets[index]
    else:
        dx, dy = _seeded_overflow_offset(agent_id or "unknown", safe_zone, index)

    return _clamp_position(base[0] + dx, base[1] + dy)
