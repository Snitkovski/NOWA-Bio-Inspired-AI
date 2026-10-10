"""Agent detail payload helper."""

from __future__ import annotations

from typing import Any

from .utils import build_generation_index_map


def build_agent_detail(agent: Any, agents: list[Any], name_registry: Any | None = None) -> dict[str, Any]:
    """Build expanded popup payload for one agent."""
    index_map = build_generation_index_map(agents)
    knowledge = getattr(agent, "knowledge", {}) or {}
    relationships = []
    for known in sorted(
        knowledge.values(),
        key=lambda item: float(getattr(item, "affinity", 0.0)),
        reverse=True,
    ):
        relationships.append(
            {
                "agent_id": str(getattr(known, "agent_id", "")),
                "name": str(getattr(known, "name", "")),
                "relationship_type": str(getattr(known, "relationship_type", "stranger")),
                "affinity": float(getattr(known, "affinity", 0.0)),
            }
        )

    try:
        registry_name = ""
        agent_id = str(getattr(agent, "agent_id", ""))
        if name_registry is not None and agent_id:
            registry_name = name_registry.get_human_name(agent_id) or ""
    except Exception:
        registry_name = ""

    if not registry_name:
        registry_name = str(getattr(agent, "agent_id", ""))

    return {
        "agent_id": str(getattr(agent, "agent_id", "")),
        "name": registry_name,
        "sex": str(getattr(agent, "sex", "?")),
        "generation": int(getattr(agent, "generation", 0) or 0),
        "parents": tuple(getattr(agent, "parents", (None, None)) or (None, None)),
        "age": float(getattr(agent, "age", 0.0) or 0.0),
        "lived_steps": int(getattr(agent, "lived_steps", 0) or 0),
        "relationships": relationships,
    }

