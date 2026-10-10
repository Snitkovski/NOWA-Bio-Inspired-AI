"""
Scheduling system for autonomous affect cycles.

Provides lightweight hunger/tiredness/boredom dynamics plus circadian rhythm.
This is a legacy-compatible layer used by the demo; it does not replace NOWA
DriveSystem but can coexist to provide simple drive hints and UI state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import math
from typing import Dict, Any


def _clamp(value: float, min_v: float = 0.0, max_v: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return max(min_v, min(max_v, v))


class CycleType(str, Enum):
    HUNGER = "hunger"
    TIREDNESS = "tiredness"
    BOREDOM = "boredom"


@dataclass
class AffectCycle:
    """Single autonomous cycle with simple rise/decay dynamics."""

    cycle_type: CycleType
    value: float
    increase_rate: float
    decay_rate: float
    critical_threshold: float
    satisfaction_threshold: float
    activity_boost: float = 0.0

    def update(self, dt: float, active: bool, activity_level: float = 0.0) -> float:
        """Advance cycle by dt. Returns delta."""
        before = self.value
        dt = max(0.0, float(dt))
        if active:
            self.value -= self.decay_rate * dt
        else:
            inc = self.increase_rate * dt
            if self.activity_boost and activity_level > 0.0:
                inc += self.activity_boost * activity_level * dt
            self.value += inc
        self.value = _clamp(self.value, 0.0, 1.0)
        return self.value - before

    def apply_satiation(self, amount: float) -> float:
        """Immediate satiation effect. Returns delta."""
        before = self.value
        self.value = _clamp(self.value - max(0.0, float(amount)), 0.0, 1.0)
        return self.value - before

    def urgency(self) -> float:
        """Urgency in [0,1] based on thresholds."""
        if self.value <= self.satisfaction_threshold:
            return 0.0
        if self.value >= self.critical_threshold:
            return 1.0
        span = max(1e-6, self.critical_threshold - self.satisfaction_threshold)
        return _clamp((self.value - self.satisfaction_threshold) / span, 0.0, 1.0)


class SchedulingSystem:
    """Manages hunger/tiredness/boredom cycles and circadian rhythm."""

    def __init__(self, logger: logging.Logger | None = None, cycle_period: float = 1200.0) -> None:
        self.logger = logger or logging.getLogger(__name__)
        # 20-minute day/night cycle in sim time by default
        self.cycle_period = max(60.0, float(cycle_period))
        self.circadian_phase: float = 0.0

        self.cycles: Dict[str, AffectCycle] = {
            "hunger": AffectCycle(
                cycle_type=CycleType.HUNGER,
                value=0.2,
                increase_rate=0.0008,
                decay_rate=0.08,
                critical_threshold=0.75,
                satisfaction_threshold=0.2,
            ),
            "tiredness": AffectCycle(
                cycle_type=CycleType.TIREDNESS,
                value=0.15,
                increase_rate=0.0006,
                decay_rate=0.10,
                critical_threshold=0.70,
                satisfaction_threshold=0.15,
                activity_boost=0.0006,
            ),
            "boredom": AffectCycle(
                cycle_type=CycleType.BOREDOM,
                value=0.25,
                increase_rate=0.0012,
                decay_rate=0.06,
                critical_threshold=0.80,
                satisfaction_threshold=0.25,
            ),
        }

        # Pending satiation boosts applied on next update
        self._pending_satiation: Dict[str, float] = {
            "hunger": 0.0,
            "tiredness": 0.0,
            "boredom": 0.0,
        }

    # ------------------------------------------------------------------
    # Update + circadian
    # ------------------------------------------------------------------

    def _advance_circadian(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        self.circadian_phase = (self.circadian_phase + dt / self.cycle_period) % 1.0

    def _activity_level(self) -> float:
        # 0.0 at night, 1.0 at day peak
        return _clamp(math.sin(self.circadian_phase * math.pi), 0.0, 1.0)

    def _active_flags(self, active_chains: Dict[str, Any]) -> Dict[str, bool]:
        active_keys = {str(k).lower() for k in (active_chains or {}).keys()}
        return {
            "hunger": any(k in active_keys for k in ("eating_and_grooming", "morning_awakening", "eat", "eating")),
            "tiredness": any(k in active_keys for k in ("bedtime_routine", "nesting", "sleep", "rest")),
            "boredom": any(k in active_keys for k in ("activity_burst", "exploration", "dust_bathing", "play")),
        }

    def update(self, dt: float, active_chains: Dict[str, Any] | None = None) -> Dict[str, float]:
        """
        Update all cycles and circadian rhythm.

        Returns a dict of cycle deltas (for optional affect integration).
        """
        self._advance_circadian(dt)
        activity_level = self._activity_level()
        active_flags = self._active_flags(active_chains or {})

        deltas: Dict[str, float] = {}
        for name, cycle in self.cycles.items():
            delta = cycle.update(dt, active_flags.get(name, False), activity_level)
            pending = self._pending_satiation.get(name, 0.0)
            if pending:
                delta += cycle.apply_satiation(pending)
                self._pending_satiation[name] = 0.0
            deltas[name] = delta

        # Night bias: increase tiredness slightly during night phase
        if activity_level < 0.3:
            extra = (0.3 - activity_level) * 0.001 * max(0.0, float(dt))
            if extra > 0.0:
                deltas["tiredness"] += self.cycles["tiredness"].apply_satiation(-extra)

        return deltas

    # ------------------------------------------------------------------
    # Triggers (instant satiation)
    # ------------------------------------------------------------------

    def trigger_eating(self, intensity: float = 1.0) -> None:
        self._pending_satiation["hunger"] = min(0.3, self._pending_satiation["hunger"] + 0.06 * _clamp(intensity))

    def trigger_sleeping(self, intensity: float = 1.0) -> None:
        self._pending_satiation["tiredness"] = min(0.35, self._pending_satiation["tiredness"] + 0.08 * _clamp(intensity))

    def trigger_playing(self, intensity: float = 1.0) -> None:
        self._pending_satiation["boredom"] = min(0.3, self._pending_satiation["boredom"] + 0.05 * _clamp(intensity))

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_cycle_status(self) -> Dict[str, Dict[str, float]]:
        return {
            name: {
                "value": cycle.value,
                "critical": cycle.critical_threshold,
                "satisfied": cycle.satisfaction_threshold,
            }
            for name, cycle in self.cycles.items()
        }

    def get_drive_suggestions(self) -> Dict[str, float]:
        hunger = self.cycles["hunger"].urgency()
        tired = self.cycles["tiredness"].urgency()
        bored = self.cycles["boredom"].urgency()

        activity_level = self._activity_level()
        is_night = activity_level < 0.3

        # Base suggestions from cycles
        suggestions = {
            "eating": hunger,
            "bedtime_routine": tired,
            "rest": tired * 0.7,
            "play": bored,
            "exploration": bored * 0.8,
            "social_contact": bored * 0.3,
        }

        # Circadian modulation
        if is_night:
            sleep_bias = _clamp((0.3 - activity_level) / 0.3)
            suggestions["bedtime_routine"] = _clamp(suggestions["bedtime_routine"] + 0.2 * sleep_bias)
            suggestions["rest"] = _clamp(suggestions["rest"] + 0.1 * sleep_bias)
            suggestions["play"] *= 0.5
            suggestions["exploration"] *= 0.5
        else:
            day_bias = _clamp((activity_level - 0.3) / 0.7)
            suggestions["play"] = _clamp(suggestions["play"] + 0.1 * day_bias)
            suggestions["exploration"] = _clamp(suggestions["exploration"] + 0.1 * day_bias)

        return {k: _clamp(v) for k, v in suggestions.items()}

    def get_circadian_state(self) -> Dict[str, float]:
        activity_level = self._activity_level()
        is_day = 1.0 if activity_level >= 0.5 else 0.0
        return {
            "phase": self.circadian_phase,
            "activity_level": activity_level,
            "is_day": is_day,
            "is_night": 1.0 - is_day,
        }

