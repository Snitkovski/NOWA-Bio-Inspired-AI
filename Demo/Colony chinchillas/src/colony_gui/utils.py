"""Utility helpers for colony GUI."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable

from .config import format_agent_name, is_formatted_name

_LEGACY_NAME_PATTERN = re.compile(r"^G(?P<generation>[0-9]+)A(?P<index>[0-9]+)$")


def clamp01(value: float) -> float:
    """Clamp numeric value into [0, 1]."""
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    if parsed != parsed:  # NaN
        return 0.0
    return max(0.0, min(1.0, parsed))


def format_sim_time(sim_time: float) -> str:
    """Format simulation time in HH:MM:SS."""
    try:
        total = max(0, int(float(sim_time)))
    except Exception:
        total = 0
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def build_generation_index_map(agents: Iterable[Any]) -> dict[str, int]:
    """Create deterministic index within generation for each agent id."""
    by_generation: dict[int, list[str]] = defaultdict(list)
    for agent in agents:
        agent_id = str(getattr(agent, "agent_id", ""))
        if not agent_id:
            continue
        generation = int(getattr(agent, "generation", 0) or 0)
        by_generation[generation].append(agent_id)

    mapping: dict[str, int] = {}
    for generation, agent_ids in by_generation.items():
        ordered = sorted(set(agent_ids))
        for idx, agent_id in enumerate(ordered, start=1):
            mapping[agent_id] = idx
    return mapping


def canonical_display_name(agent: Any, index_map: dict[str, int] | None = None) -> str:
    """Return GUI-safe display name in GxAyS<sex> format."""
    raw_name = str(getattr(agent, "name", ""))
    if is_formatted_name(raw_name):
        return raw_name
    sex = str(getattr(agent, "sex", "U") or "U")

    legacy_match = _LEGACY_NAME_PATTERN.match(raw_name)
    if legacy_match:
        generation = int(legacy_match.group("generation"))
        index = int(legacy_match.group("index"))
        return format_agent_name(generation, index, sex)

    generation = int(getattr(agent, "generation", 0) or 0)
    agent_id = str(getattr(agent, "agent_id", ""))
    index = 1
    if index_map is not None and agent_id:
        index = int(index_map.get(agent_id, 1))
    return format_agent_name(generation, index, sex)
