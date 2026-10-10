"""Autonomous reproduction dynamics for emergent evolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


REPRODUCTION_VERSION = "1.0"
MIN_REPRODUCTIVE_AGE = 100
MIN_COMPATIBILITY_THRESHOLD = 0.4
REPRODUCTION_ENERGY_COST = 0.12


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if casted != casted or casted in (float("inf"), float("-inf")):
        return float(fallback)
    return casted


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


@dataclass
class ReproductiveSystem:
    """
    Autonomous reproduction subsystem for one agent.

    The system updates only from local state signals and does not access other agents.
    """

    reproductive_drive: float = 0.0
    drive_threshold: float = 0.7
    drive_decay: float = 0.01
    drive_recovery_rate: float = 0.05
    cooldown_steps: int = 0
    cooldown_duration: int = 50
    total_offspring: int = 0
    last_reproduction_step: int = -1

    def __post_init__(self) -> None:
        self.reproductive_drive = _clamp(_safe_float(self.reproductive_drive, 0.0), 0.0, 1.0)
        self.drive_threshold = _clamp(_safe_float(self.drive_threshold, 0.7), 0.0, 1.0)
        self.drive_decay = _clamp(_safe_float(self.drive_decay, 0.01), 0.0, 1.0)
        self.drive_recovery_rate = _clamp(_safe_float(self.drive_recovery_rate, 0.05), 0.0, 1.0)
        self.cooldown_steps = max(0, _safe_int(self.cooldown_steps, 0))
        self.cooldown_duration = max(0, _safe_int(self.cooldown_duration, 50))
        self.total_offspring = max(0, _safe_int(self.total_offspring, 0))
        self.last_reproduction_step = _safe_int(self.last_reproduction_step, -1)

    def update(
        self,
        energy: float,
        valence: float,
        cortisol: float,
        lived_steps: int,
        resource_share: float,
    ) -> None:
        """Update reproductive drive by one simulation step."""
        age_steps = max(0, _safe_int(lived_steps, 0))
        if age_steps < MIN_REPRODUCTIVE_AGE:
            self.reproductive_drive = 0.0
            return

        if self.cooldown_steps > 0:
            self.cooldown_steps = max(0, self.cooldown_steps - 1)
            self.reproductive_drive = 0.0
            return

        energy_v = _clamp(_safe_float(energy, 0.0), 0.0, 1.0)
        valence_v = _clamp(_safe_float(valence, 0.0), -1.0, 1.0)
        cortisol_v = _clamp(_safe_float(cortisol, 0.0), 0.0, 1.0)
        resource_v = _clamp(_safe_float(resource_share, 0.0), 0.0, 1.0)

        favorable = (
            energy_v * 0.4
            + max(0.0, valence_v) * 0.3
            + (1.0 - cortisol_v) * 0.2
            + resource_v * 0.1
        )
        delta = favorable * self.drive_recovery_rate - self.drive_decay
        self.reproductive_drive = _clamp(self.reproductive_drive + delta, 0.0, 1.0)

    def is_ready(self) -> bool:
        """Return whether the agent can reproduce now."""
        return self.cooldown_steps == 0 and self.reproductive_drive >= self.drive_threshold

    def register_reproduction(self, current_step: int) -> None:
        """Register successful reproduction and start cooldown."""
        self.total_offspring += 1
        self.last_reproduction_step = _safe_int(current_step, -1)
        self.cooldown_steps = max(0, self.cooldown_duration)
        self.reproductive_drive = 0.0

    def snapshot(self) -> Dict[str, Any]:
        """Return a diagnostic immutable-style snapshot of the subsystem."""
        return {
            "version": REPRODUCTION_VERSION,
            "reproductive_drive": float(self.reproductive_drive),
            "drive_threshold": float(self.drive_threshold),
            "drive_decay": float(self.drive_decay),
            "drive_recovery_rate": float(self.drive_recovery_rate),
            "cooldown_steps": int(self.cooldown_steps),
            "cooldown_duration": int(self.cooldown_duration),
            "total_offspring": int(self.total_offspring),
            "last_reproduction_step": int(self.last_reproduction_step),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReproductiveSystem":
        """Restore from dictionary payload."""
        payload = data if isinstance(data, dict) else {}
        return cls(
            reproductive_drive=_safe_float(payload.get("reproductive_drive"), 0.0),
            drive_threshold=_safe_float(payload.get("drive_threshold"), 0.7),
            drive_decay=_safe_float(payload.get("drive_decay"), 0.01),
            drive_recovery_rate=_safe_float(payload.get("drive_recovery_rate"), 0.05),
            cooldown_steps=_safe_int(payload.get("cooldown_steps"), 0),
            cooldown_duration=_safe_int(payload.get("cooldown_duration"), 50),
            total_offspring=_safe_int(payload.get("total_offspring"), 0),
            last_reproduction_step=_safe_int(payload.get("last_reproduction_step"), -1),
        )


def compute_compatibility(
    agent_a_snapshot: Dict[str, Any],
    agent_b_snapshot: Dict[str, Any],
) -> float:
    """
    Compute decentralized mating compatibility from two agent snapshots.

    The function is pure and has no side effects.
    """
    snapshot_a = agent_a_snapshot if isinstance(agent_a_snapshot, dict) else {}
    snapshot_b = agent_b_snapshot if isinstance(agent_b_snapshot, dict) else {}

    distance_a = snapshot_a.get("genome_distance")
    distance_b = snapshot_b.get("genome_distance")
    available_distances = []
    if distance_a is not None:
        available_distances.append(_clamp(_safe_float(distance_a, 0.3), 0.0, 1.0))
    if distance_b is not None:
        available_distances.append(_clamp(_safe_float(distance_b, 0.3), 0.0, 1.0))
    if available_distances:
        genome_distance = sum(available_distances) / float(len(available_distances))
        optimal_distance = 0.3
        genome_bonus = 1.0 - abs(genome_distance - optimal_distance) / optimal_distance
        genome_bonus = _clamp(genome_bonus, 0.0, 1.0)
    else:
        genome_bonus = 0.5

    valence_a = _clamp(_safe_float(snapshot_a.get("valence"), 0.0), -1.0, 1.0)
    valence_b = _clamp(_safe_float(snapshot_b.get("valence"), 0.0), -1.0, 1.0)
    affective_resonance = _clamp(1.0 - abs(valence_a - valence_b) / 2.0, 0.0, 1.0)

    cortisol_a = _clamp(_safe_float(snapshot_a.get("cortisol"), 1.0), 0.0, 1.0)
    cortisol_b = _clamp(_safe_float(snapshot_b.get("cortisol"), 1.0), 0.0, 1.0)
    stress_compatibility = _clamp((1.0 - cortisol_a) * (1.0 - cortisol_b), 0.0, 1.0)

    drive_a = _clamp(_safe_float(snapshot_a.get("reproductive_drive"), 0.0), 0.0, 1.0)
    drive_b = _clamp(_safe_float(snapshot_b.get("reproductive_drive"), 0.0), 0.0, 1.0)
    drive_alignment = _clamp(drive_a * drive_b, 0.0, 1.0)

    compatibility = (
        genome_bonus * 0.25
        + affective_resonance * 0.25
        + stress_compatibility * 0.25
        + drive_alignment * 0.25
    )
    return _clamp(compatibility, 0.0, 1.0)


__all__ = [
    "REPRODUCTION_VERSION",
    "MIN_REPRODUCTIVE_AGE",
    "MIN_COMPATIBILITY_THRESHOLD",
    "REPRODUCTION_ENERGY_COST",
    "ReproductiveSystem",
    "compute_compatibility",
]
