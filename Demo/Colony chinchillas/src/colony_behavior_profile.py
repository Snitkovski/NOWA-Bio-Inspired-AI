"""Dataset-driven base behavior profile for colony agents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_BASE_ABILITIES: tuple[str, ...] = (
    "explore",
    "eat",
    "drink",
    "sleep",
    "groom_self",
    "run_wheel",
    "hide",
    "socialize",
    "play",
    "rest",
)

DEFAULT_HABITS: tuple[dict[str, Any], ...] = (
    {"context": ["food_low"], "action": "eat", "strength": 1.4},
    {"context": ["food_critical"], "action": "eat", "strength": 2.2},
    {"context": ["hunger_high"], "action": "eat", "strength": 1.7},
    {"context": ["hunger_critical"], "action": "eat", "strength": 2.4},
    {"context": ["water_critical"], "action": "drink", "strength": 2.2},
    {"context": ["thirst_high"], "action": "drink", "strength": 1.8},
    {"context": ["thirst_critical"], "action": "drink", "strength": 2.5},
    {"context": ["wakefulness_high"], "action": "sleep", "strength": 1.8},
    {"context": ["wakefulness_critical"], "action": "sleep", "strength": 2.6},
    {"context": ["bored"], "action": "run_wheel", "strength": 0.9},
    {"context": ["social_contact:1"], "action": "socialize", "strength": 1.1},
    {"context": ["high_stress"], "action": "hide", "strength": 1.6},
)

DEFAULT_UNCONDITIONED_REFLEXES: tuple[dict[str, Any], ...] = (
    {
        "id": "panic_hide",
        "trigger_any": ["alarm_call", "high_stress"],
        "action": "hide",
        "priority": 1.0,
        "cooldown_s": 18.0,
        "override_exclusive": True,
    },
    {
        "id": "urgent_drink",
        "trigger_any": ["water_critical"],
        "action": "drink",
        "priority": 0.95,
        "cooldown_s": 8.0,
        "override_exclusive": False,
    },
    {
        "id": "urgent_feed",
        "trigger_any": ["food_critical"],
        "action": "eat",
        "priority": 0.9,
        "cooldown_s": 12.0,
        "override_exclusive": False,
    },
)

PROFILE_FILENAMES: tuple[str, ...] = (
    "colony_agent_profile.json",
    "colony_behavior_profile.json",
)


@dataclass(frozen=True, slots=True)
class HabitSeed:
    """Initial context->action bias entry for IntentMemory."""

    context: tuple[str, ...]
    action: str
    strength: float


@dataclass(frozen=True, slots=True)
class UnconditionedReflex:
    """Immediate response rule that can override selected action."""

    reflex_id: str
    trigger_any: tuple[str, ...]
    trigger_all: tuple[str, ...]
    action: str
    priority: float = 1.0
    cooldown_s: float = 0.0
    override_exclusive: bool = False


@dataclass(frozen=True, slots=True)
class ColonyBehaviorProfile:
    """Full behavior bootstrap package loaded from datasets."""

    base_abilities: tuple[str, ...]
    unconditioned_reflexes: tuple[UnconditionedReflex, ...]
    habits: tuple[HabitSeed, ...]
    source_file: str


def _as_str_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, (list, tuple)):
        return ()
    out: list[str] = []
    for item in value:
        casted = str(item).strip()
        if casted:
            out.append(casted)
    return tuple(out)


def _safe_float(value: Any, fallback: float) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if casted != casted or casted in (float("inf"), float("-inf")):
        return float(fallback)
    return float(casted)


def _normalize_ability(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("id", "")).strip()
    return str(entry).strip()


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    unique: dict[str, None] = {}
    for value in values:
        if value:
            unique.setdefault(value, None)
    return tuple(unique.keys())


def _parse_profile_payload(payload: dict[str, Any], *, source_file: str) -> ColonyBehaviorProfile:
    abilities_raw = payload.get("base_abilities", list(DEFAULT_BASE_ABILITIES))
    abilities = [_normalize_ability(item) for item in list(abilities_raw or [])]
    abilities = [item for item in abilities if item]
    if not abilities:
        abilities = list(DEFAULT_BASE_ABILITIES)

    reflexes_raw = payload.get("unconditioned_reflexes", payload.get("reflexes", []))
    reflexes: list[UnconditionedReflex] = []
    for idx, row in enumerate(list(reflexes_raw or [])):
        if not isinstance(row, dict):
            continue
        action = str(row.get("action", "")).strip()
        trigger_any = _as_str_list(row.get("trigger_any", row.get("context_any", [])))
        trigger_all = _as_str_list(row.get("trigger_all", row.get("context_all", [])))
        if not action or (not trigger_any and not trigger_all):
            continue
        if action not in abilities:
            abilities.append(action)
        reflexes.append(
            UnconditionedReflex(
                reflex_id=str(row.get("id", f"reflex_{idx}_{action}")).strip() or f"reflex_{idx}",
                trigger_any=trigger_any,
                trigger_all=trigger_all,
                action=action,
                priority=_safe_float(row.get("priority", 1.0), 1.0),
                cooldown_s=max(0.0, _safe_float(row.get("cooldown_s", 0.0), 0.0)),
                override_exclusive=bool(row.get("override_exclusive", False)),
            )
        )

    habits_raw = payload.get("habits", [])
    habits: list[HabitSeed] = []
    for row in list(habits_raw or []):
        if not isinstance(row, dict):
            continue
        action = str(row.get("action", "")).strip()
        context = _as_str_list(row.get("context", []))
        if not action or not context:
            continue
        if action not in abilities:
            abilities.append(action)
        habits.append(
            HabitSeed(
                context=context,
                action=action,
                strength=max(0.05, _safe_float(row.get("strength", 1.0), 1.0)),
            )
        )

    reflexes.sort(key=lambda item: item.priority, reverse=True)
    return ColonyBehaviorProfile(
        base_abilities=_dedupe_preserve_order(abilities),
        unconditioned_reflexes=tuple(reflexes),
        habits=tuple(habits),
        source_file=source_file,
    )


def _default_profile(reason: str) -> ColonyBehaviorProfile:
    payload: dict[str, Any] = {
        "base_abilities": list(DEFAULT_BASE_ABILITIES),
        "unconditioned_reflexes": list(DEFAULT_UNCONDITIONED_REFLEXES),
        "habits": list(DEFAULT_HABITS),
    }
    return _parse_profile_payload(payload, source_file=reason)


def _dataset_dir_candidates() -> tuple[Path, ...]:
    demo_dir = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[3]
    return (
        demo_dir / "datasets",
        demo_dir / "Datasets",
        repo_root / "datasets",
    )


@lru_cache(maxsize=1)
def load_colony_behavior_profile() -> ColonyBehaviorProfile:
    """Load colony behavior profile from datasets with safe fallback."""
    for directory in _dataset_dir_candidates():
        if not directory.exists():
            continue
        for filename in PROFILE_FILENAMES:
            filepath = directory / filename
            if not filepath.exists():
                continue
            try:
                payload = json.loads(filepath.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                return _parse_profile_payload(payload, source_file=str(filepath))
    return _default_profile("builtin-default")
