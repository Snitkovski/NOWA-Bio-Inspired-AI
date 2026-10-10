"""Right-side agent panel builders."""

from __future__ import annotations

from typing import Any

from colony_renderer import RenderSnapshot

from .utils import build_generation_index_map, canonical_display_name, clamp01


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


class AgentPanel:
    """Compose concise cards for GUI display."""

    def __init__(self, snapshot: RenderSnapshot) -> None:
        self.snapshot = snapshot

    def build_card(self, agent_id: str, runner: Any) -> dict[str, Any]:
        agents = list(getattr(runner, "agents", []) or [])
        match = next((agent for agent in agents if str(getattr(agent, "agent_id", "")) == str(agent_id)), None)
        if match is None:
            raise KeyError(f"Agent not found: {agent_id}")

        index_map = build_generation_index_map(agents)
        relationships = []
        knowledge = getattr(match, "knowledge", {}) or {}
        ordered = sorted(
            knowledge.values(),
            key=lambda item: _safe_float(getattr(item, "affinity", 0.0)),
            reverse=True,
        )
        for known in ordered[:3]:
            known_id = str(getattr(known, "agent_id", ""))
            # Use birth registry as authoritative source of human-readable
            # names when available; otherwise fall back to id.
            name = known_id
            try:
                registry = getattr(runner, "birth_registry", None)
                if registry is not None and known_id:
                    name = registry.get_human_name(known_id) or known_id
            except Exception:
                name = known_id
            relationships.append(
                {
                    "agent_id": known_id,
                    "name": name,
                    "relationship_type": str(getattr(known, "relationship_type", "stranger")),
                    "affinity": _safe_float(getattr(known, "affinity", 0.0)),
                }
            )

        affect = {
            "stress": clamp01(_safe_float(getattr(match, "stress", 0.0))),
            "valence": clamp01((_safe_float(getattr(match, "valence", 0.0)) + 1.0) / 2.0),
            "arousal": clamp01(_safe_float(getattr(match, "arousal", 0.0))),
            "energy": clamp01(_safe_float(getattr(match, "energy", 1.0))),
        }

        # Authoritative display name comes only from the birth registry.
        try:
            registry = getattr(runner, "birth_registry", None)
            name = registry.get_human_name(str(getattr(match, "agent_id", ""))) if registry is not None else ""
        except Exception:
            name = ""
        if not name:
            name = str(getattr(match, "agent_id", ""))

        return {
            "agent_id": str(getattr(match, "agent_id", "")),
            "name": name,
            "raw_name": str(getattr(match, "name", "")),
            "sex": str(getattr(match, "sex", "?")),
            "age_category": str(getattr(match, "_age_category", lambda: "adult")()),
            "current_action": str(getattr(match, "current_action", "idle")),
            "affect_tone": str(getattr(match, "_compute_affect_tone", lambda: "calm")()),
            "affect": affect,
            "relationships": relationships,
            "generation": int(getattr(match, "generation", 0) or 0),
            "parents": tuple(getattr(match, "parents", (None, None)) or (None, None)),
            "lived_steps": int(getattr(match, "lived_steps", 0) or 0),
        }
