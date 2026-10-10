"""Interaction overlay structures and extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import INTERACTION_DISPLAY_DURATION


@dataclass(slots=True)
class InteractionEntry:
    """One displayed interaction line between two agents."""

    agent_a_id: str
    agent_b_id: str
    offer_type: str
    started_real_time: float
    duration: float = INTERACTION_DISPLAY_DURATION

    def is_expired(self, now: float) -> bool:
        return (float(now) - float(self.started_real_time)) >= float(self.duration)


def extract_interactions(
    agents: list[Any],
    now: float,
    *,
    duration: float = INTERACTION_DISPLAY_DURATION,
) -> list[InteractionEntry]:
    """
    Derive recent interactions from known-agent episodic histories.

    This is intentionally read-only and tolerant to partially populated objects.
    """
    entries: list[InteractionEntry] = []
    seen: set[tuple[str, str, str, int]] = set()
    horizon = float(now) - float(duration)

    for agent in agents:
        agent_id = str(getattr(agent, "agent_id", ""))
        if not agent_id:
            continue
        knowledge = getattr(agent, "knowledge", {}) or {}
        for other_id, known in knowledge.items():
            history = list(getattr(known, "interaction_history", []) or [])
            if not history:
                continue
            episode = history[-1]
            started = float(getattr(episode, "time", -1.0))
            if started < horizon:
                continue
            offer_type = str(getattr(episode, "interaction_type", "socialize")) or "socialize"
            pair = tuple(sorted((agent_id, str(other_id))))
            key = (pair[0], pair[1], offer_type, int(started * 1000))
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                InteractionEntry(
                    agent_a_id=agent_id,
                    agent_b_id=str(other_id),
                    offer_type=offer_type,
                    started_real_time=started,
                    duration=float(duration),
                )
            )

    entries.sort(key=lambda item: item.started_real_time, reverse=True)
    return entries

