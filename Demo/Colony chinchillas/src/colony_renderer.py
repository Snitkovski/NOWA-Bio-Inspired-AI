"""Minimal renderer-facing utilities for colony state snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from agent_knowledge import PublicState
from shared_resources import SharedResources

ZONE_SLOT_OFFSETS: dict[str, list[tuple[int, int]]] = {
    "floor": [(0, 0), (40, 10), (-35, 15), (20, -20)],
    "house": [(0, 0), (15, 5), (-15, 5)],
    "wheel": [(0, 0)],
}


@dataclass(slots=True)
class RenderSnapshot:
    """Data consumed by UI layer."""

    agents: list[PublicState]
    resources: SharedResources
    sim_time: float


def build_snapshot(
    agent_states: list[PublicState], resources: SharedResources, sim_time: float
) -> RenderSnapshot:
    """Create renderer snapshot without behavior logic."""
    return RenderSnapshot(agents=agent_states, resources=resources, sim_time=sim_time)
