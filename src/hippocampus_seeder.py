"""Domain-agnostic hippocampus seeder (mind layer, not MCP).

Each stored path has context tokens plus exactly one ``EventType.ACTION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple, Type


def load_experience_types() -> Tuple[Type[Any], Type[Any], Any]:
    """Return ``(Path, Event, EventType)`` from core, with MCP-compat fallback."""
    try:
        from experience import Event, EventType, Path
        return Path, Event, EventType
    except Exception:
        from mcp_body._compat import load_experience_types as _compat_load
        return _compat_load()


@dataclass
class SeedEpisode:
    context_tokens: List[str]
    action: str
    consequence: str
    reward: float
    intensity: float = 0.5
    reinforce: bool = False


class HippocampusSeeder:
    """Corpus is supplied from outside this module."""

    def __init__(self, episodes: List[SeedEpisode]) -> None:
        self.episodes = list(episodes)

    def seed_agent(self, agent: Any) -> int:
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None or not hasattr(hippocampus, "store"):
            return 0
        added = 0
        for ep in self.episodes:
            try:
                action = str(getattr(ep, "action", "") or "").strip()
                if not action:
                    raise ValueError("SeedEpisode.action must be a non-empty action label")
                path = self._build_path(list(ep.context_tokens or []), action)
                consequence = self._build_consequence(ep.consequence)
                self._store(
                    hippocampus,
                    path,
                    consequence,
                    float(ep.intensity),
                    float(ep.reward),
                )
                added += 1
                if ep.reinforce and hasattr(hippocampus, "reinforce"):
                    try:
                        self._reinforce(
                            hippocampus, path, consequence, float(ep.intensity)
                        )
                    except Exception:
                        continue
            except Exception:
                continue
        return added

    def _build_path(self, tokens: List[str], action: str) -> Any:
        path_cls, event_cls, event_type = load_experience_types()
        path = path_cls()
        for token in tokens or []:
            label = str(token).strip()
            if not label:
                continue
            path = path.add_event(event_cls(label, event_type.CONTEXT))
        action_name = str(action).strip()
        if action_name and not action_name.startswith("action:"):
            action_name = f"action:{action_name}"
        if not action_name:
            raise ValueError("cannot build a seed path without an ACTION event")
        path = path.add_event(event_cls(action_name, event_type.ACTION))
        return path

    def _build_consequence(self, label: str) -> Any:
        _path_cls, event_cls, event_type = load_experience_types()
        name = str(label).strip() if label is not None else ""
        if not name:
            name = "unspecified_outcome"
        return event_cls(name, event_type.CONSEQUENCE)

    @staticmethod
    def _store(hippocampus: Any, path: Any, consequence: Any, intensity: float, reward: float) -> Any:
        try:
            return hippocampus.store(
                path, consequence=consequence, intensity=intensity, reward=reward
            )
        except TypeError:
            try:
                return hippocampus.store(path, consequence=consequence, intensity=intensity)
            except TypeError:
                return hippocampus.store(path, consequence=consequence)

    @staticmethod
    def _reinforce(hippocampus: Any, path: Any, consequence: Any, intensity: float) -> Any:
        try:
            return hippocampus.reinforce(path, consequence=consequence, intensity=intensity)
        except TypeError:
            try:
                return hippocampus.reinforce(path, consequence=consequence)
            except TypeError:
                return hippocampus.reinforce(path)


BusinessHippocampusSeeder = HippocampusSeeder

__all__ = [
    "BusinessHippocampusSeeder",
    "HippocampusSeeder",
    "SeedEpisode",
    "load_experience_types",
]
