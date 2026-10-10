"""Birth registry: simple mapping of agent_id -> human-readable name captured at birth.

This registry is intentionally minimal: it records the name provided at birth
time and exposes a single authoritative lookup `get_human_name(agent_id)` that
other subsystems should consult when they need a human-friendly name for an
agent. It also persists to disk alongside other save files.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict
from pathlib import Path
from typing import Any


REGISTRY_VERSION = "1.1"
REGISTRY_FILENAME = "birth_registry.json"


class BirthRegistry:
    """Registry of all agents that were born (id -> human-friendly name).

    The registry intentionally does not attempt to synthesise fallback names;
    callers should treat an empty string as "no human name recorded" and may
    decide what to display (we keep that decision minimal here).
    """

    def __init__(self, save_dir: str | Path | None = None) -> None:
        # _name_map stores the canonical/gui-ready name (GxAyS<sex>) when
        # available. _raw_name_map preserves the original agent.name value.
        self._name_map: dict[str, str] = {}
        self._raw_name_map: dict[str, str] = {}
        self._birth_times: dict[str, float] = {}
        self._save_dir: Path | None = Path(save_dir) if save_dir else None

    def register_birth(self, agent: Any, sim_time: float, canonical_name: str | None = None) -> None:
        agent_id = str(getattr(agent, "agent_id", "") or "")
        if not agent_id:
            return
        try:
            raw = str(getattr(agent, "name", "") or "")
        except Exception:
            raw = ""
        # Preserve raw name regardless.
        self._raw_name_map[agent_id] = raw
        # If a canonical name is provided, record it as authoritative.
        if canonical_name:
            try:
                self._name_map[agent_id] = str(canonical_name)
            except Exception:
                pass
        try:
            self._birth_times[agent_id] = float(sim_time)
        except Exception:
            self._birth_times.setdefault(agent_id, 0.0)

    def get_human_name(self, agent_id: str) -> str:
        """Return the human-friendly name recorded at birth, or empty string."""
        if not agent_id:
            return ""
        aid = str(agent_id)
        # Prefer canonical/gui name when available, else fall back to raw
        # name recorded at birth. Return empty string when nothing recorded.
        return self._name_map.get(aid) or self._raw_name_map.get(aid, "")

    def save(self, path: str | Path) -> None:
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Any] = {
                "version": REGISTRY_VERSION,
                "birth_times": {str(k): float(v) for k, v in self._birth_times.items()},
                "names": {str(k): str(v) for k, v in self._name_map.items()},
                "raw_names": {str(k): str(v) for k, v in self._raw_name_map.items()},
            }
            with target.open("w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            warnings.warn(f"Failed to save birth registry to '{path}': {exc}", RuntimeWarning)

    def load(self, path: str | Path) -> None:
        try:
            source = Path(path)
            with source.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
            if not isinstance(payload, dict):
                raise ValueError("registry payload must be a JSON object")
            birth_times_raw = payload.get("birth_times", {}) or {}
            names_raw = payload.get("names", {}) or {}
            raw_names_raw = payload.get("raw_names", {}) or {}
            if not isinstance(birth_times_raw, dict) or not isinstance(names_raw, dict):
                raise ValueError("invalid birth registry payload")

            for key, value in birth_times_raw.items():
                aid = str(key or "")
                if not aid:
                    continue
                try:
                    self._birth_times[aid] = float(value)
                except Exception:
                    self._birth_times.setdefault(aid, 0.0)

            for key, value in names_raw.items():
                aid = str(key or "")
                if not aid:
                    continue
                try:
                    self._name_map[aid] = str(value or "")
                except Exception:
                    continue
            for key, value in raw_names_raw.items():
                aid = str(key or "")
                if not aid:
                    continue
                try:
                    self._raw_name_map[aid] = str(value or "")
                except Exception:
                    continue
        except Exception as exc:
            warnings.warn(f"Failed to load birth registry from '{path}': {exc}", RuntimeWarning)

    def autosave(self) -> None:
        if self._save_dir is None:
            return
        try:
            self.save(self._save_dir / REGISTRY_FILENAME)
        except Exception:
            pass

    def clear(self) -> None:
        self._name_map.clear()
        self._birth_times.clear()

    def summary(self) -> str:
        total = len(self._birth_times)
        named = len(self._name_map)
        return f"BirthRegistry: {total} born, {named} named"


__all__ = ["BirthRegistry"]
