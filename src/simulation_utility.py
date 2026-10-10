"""
Shared utility computation for internal simulation.

This module centralizes drive-aware heuristic scoring so evaluator and
simulation loop always use the same formula.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    v = _f(value, lo)
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


DEFAULT_DRIVE_UTILITY_PROFILES: Dict[str, Dict[str, float]] = {
    "curiosity": {"curiosity": 0.55, "stability": 0.20, "stress": -0.25},
    "social_drive": {"trust": 0.45, "attachment": 0.35, "stress": -0.20},
    "goal_tension": {"dominance": 0.40, "stability": 0.35, "stress": -0.25},
    "exploration": {"curiosity": 0.50, "arousal": 0.20, "stress": -0.30},
    "energy_need": {"stability": 0.45, "arousal": -0.35, "stress": -0.20},
    "_default": {"stability": 0.45, "stress": -0.35, "curiosity": 0.20},
}


def compute_drive_utility_components(
    hypothetical_state: Mapping[str, Any],
    drive_utility_profiles: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Dict[str, float]:
    """
    Compute unified utility components for one hypothetical state.

    Returns keys:
        drive_relief, axes_score, effect_energy, utility, confidence_hint, relevance_hint
    """
    state = dict(hypothetical_state or {})
    active_drive = str(state.get("active_drive", ""))
    profiles = dict(drive_utility_profiles or DEFAULT_DRIVE_UTILITY_PROFILES)
    profile = dict(profiles.get(active_drive, profiles.get("_default", {})) or {})

    effect = dict(state.get("predicted_effect", {}) or {})
    effect_axes = dict(effect.get("axes", {}) or {})
    effect_drives = dict(effect.get("drives", {}) or {})
    active_delta = _f(effect.get("active_drive_delta", 0.0), 0.0)

    drives_before = dict(state.get("drives_before", {}) or {})
    drives_after = dict(state.get("drives", {}) or {})
    before = _clamp(_f(drives_before.get(active_drive, drives_after.get(active_drive, 0.0))), 0.0, 1.0)
    after = _clamp(_f(drives_after.get(active_drive, before)), 0.0, 1.0)
    observed_relief = _clamp(before - after, 0.0, 1.0)
    predicted_relief = _clamp(
        max(
            0.0,
            -_f(effect_drives.get(active_drive, 0.0), 0.0),
            -active_delta,
        ),
        0.0,
        1.0,
    )
    drive_relief = _clamp(max(observed_relief, predicted_relief), 0.0, 1.0)

    axes = dict(state.get("axes", {}) or {})
    weighted = 0.0
    total = 0.0
    for axis, weight in profile.items():
        w = _f(weight)
        x = _clamp((_f(axes.get(axis, 0.0)) + 1.0) * 0.5, 0.0, 1.0)
        if w >= 0.0:
            weighted += w * x
        else:
            weighted += abs(w) * (1.0 - x)
        total += abs(w)
    axes_score = _clamp(weighted / max(1e-6, total), 0.0, 1.0)

    effect_axes_energy = sum(abs(_f(v, 0.0)) for v in effect_axes.values()) / max(1, len(effect_axes))
    effect_drive_energy = sum(abs(_f(v, 0.0)) for v in effect_drives.values()) / max(1, len(effect_drives))
    effect_energy = _clamp((effect_axes_energy + effect_drive_energy + abs(active_delta)) / 3.0, 0.0, 1.0)

    utility = _clamp(0.50 * drive_relief + 0.40 * axes_score + 0.10 * effect_energy, 0.0, 1.0)
    confidence_hint = _clamp(0.35 + 0.40 * drive_relief + 0.25 * effect_energy, 0.0, 1.0)
    relevance_hint = _clamp(0.55 * utility + 0.45 * drive_relief, 0.0, 1.0)

    return {
        "drive_relief": drive_relief,
        "axes_score": axes_score,
        "effect_energy": effect_energy,
        "utility": utility,
        "confidence_hint": confidence_hint,
        "relevance_hint": relevance_hint,
    }

