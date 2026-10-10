"""
Continuous Emotional Regulation (CER).

The layer provides a continuous affective state and modulation factors:
- valence: [-1, 1]
- arousal: [0, 1]
- uncertainty_tension: [0, 1]

It never selects actions directly and never stores episodes.
It only emits modulation factors for other modules.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: Any, min_v: float = 0.0, max_v: float = 1.0) -> float:
    v = _safe_float(value, min_v)
    return max(min_v, min(max_v, v))


def _clamp_delta(target: float, previous: float, max_step: float = 0.3) -> float:
    delta = float(target) - float(previous)
    if delta > max_step:
        return float(previous) + max_step
    if delta < -max_step:
        return float(previous) - max_step
    return float(target)


@dataclass
class EmotionalRegulationLayer:
    """
    Continuous emotional regulation state and modulation factors.

    Compatibility:
    - keeps legacy fields: `regulation_active`, `regulation_mode`, `applied_adjustments`
    - supports legacy update signature; those arguments are ignored in CER mode
    """

    # Decays (hysteresis floors from spec)
    decay_v: float = 0.95
    decay_a: float = 0.90
    decay_u: float = 0.94

    # Core update weights
    w_reward: float = 0.20
    w_error: float = 0.25
    w_novelty: float = 0.35
    w_pe: float = 0.25
    w_entropy: float = 0.30
    w_resolution: float = 0.25

    # EMA for sustained prediction error
    ema_alpha: float = 0.90
    sustained_prediction_error: float = 0.0

    # Modulation coefficients
    base_exploration: float = 0.10
    k1: float = 0.35
    k2: float = 0.25
    k3: float = 0.30
    k4: float = 0.25
    k5: float = 0.20
    k6: float = 0.30
    k7: float = 0.20
    k8: float = 0.35
    k9: float = 0.20
    k10: float = 0.45
    k11: float = 0.22
    k12: float = 0.18

    # Runtime state
    valence: float = 0.0
    arousal: float = 0.0
    uncertainty_tension: float = 0.0

    chronic_negative_valence: float = 0.0
    depressive_bias: float = 0.0
    recovery_mode: bool = False

    negative_valence_steps: int = 0
    high_arousal_steps: int = 0
    step_count: int = 0
    runaway_activations: int = 0
    saturation_guard_activations: int = 0

    last_update_ts: float = field(default_factory=time.time)
    last_time_delta: float = 1.0
    _last_policy_entropy: float = 0.0
    _last_prediction_error: float = 0.0
    _last_reward_signal: float = 0.0

    # Compatibility fields for existing integrations.
    regulation_active: bool = False
    regulation_mode: str = "none"
    applied_adjustments: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {"background_shift": {}, "neuromodulator_shift": {}}
    )
    last_target_emotion: str = ""
    last_global_outlook: str = ""

    # Cached output factors
    modulation_factors: Dict[str, float] = field(
        default_factory=lambda: {
            "exploration_bias": 0.10,
            "learning_rate_scale": 1.0,
            "novelty_sensitivity_scale": 1.0,
            "decision_threshold_shift": 0.0,
            "habit_gain_scale": 1.0,
        }
    )
    # Slow top-down guidance over neuromodulators (indirect biological pathway).
    neuromodulator_guidance: Dict[str, float] = field(
        default_factory=lambda: {
            "dopamine": 0.0,
            "norepinephrine": 0.0,
            "serotonin": 0.0,
            "cortisol": 0.0,
        }
    )

    def __post_init__(self) -> None:
        self.decay_v = max(0.90, min(0.99, _safe_float(self.decay_v, 0.95)))
        self.decay_a = max(0.85, min(0.99, _safe_float(self.decay_a, 0.90)))
        self.decay_u = max(0.90, min(0.99, _safe_float(self.decay_u, 0.94)))
        self.ema_alpha = max(0.85, min(0.995, _safe_float(self.ema_alpha, 0.90)))

        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, 0.0, 1.0)
        self.uncertainty_tension = _clamp(self.uncertainty_tension, 0.0, 1.0)
        self.chronic_negative_valence = _clamp(self.chronic_negative_valence, 0.0, 1.0)
        self.depressive_bias = _clamp(self.depressive_bias, 0.0, 1.0)
        self.sustained_prediction_error = _clamp(self.sustained_prediction_error, 0.0, 1.0)
        self.modulation_factors = self._normalize_modulation_factors(self.modulation_factors)
        self.neuromodulator_guidance = self._normalize_neuromodulator_guidance(self.neuromodulator_guidance)

    def update(
        self,
        reward_signal: float = 0.0,
        prediction_error: float = 0.0,
        novelty_score: float = 0.0,
        policy_entropy: float = 0.0,
        resolution_success: float = 0.0,
        time_delta: float = 1.0,
        timestamp: Optional[float] = None,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Update CER by one step.

        Legacy kwargs are accepted for backward compatibility and ignored:
        - expectations_snapshot
        - affective_background_snapshot
        - neuromodulators_snapshot
        - agent_lifetime
        """
        ts = _safe_float(timestamp, time.time()) if timestamp is not None else time.time()
        self.last_update_ts = ts
        self.step_count += 1
        self.last_time_delta = max(1e-6, _safe_float(time_delta, 1.0))

        reward = _clamp(reward_signal, -1.0, 1.0)
        pe = _clamp(abs(prediction_error), 0.0, 1.0)
        novelty = _clamp(novelty_score, 0.0, 1.0)
        entropy = _clamp(policy_entropy, 0.0, 1.0)
        resolution = _clamp(resolution_success, 0.0, 1.0)

        self._last_reward_signal = reward
        self._last_prediction_error = pe
        self._last_policy_entropy = entropy

        # EMA over prediction error (alpha >= 0.85 per spec).
        self.sustained_prediction_error = _clamp(
            self.ema_alpha * self.sustained_prediction_error + (1.0 - self.ema_alpha) * pe,
            0.0,
            1.0,
        )

        # Saturation guard adjusts arousal dynamics.
        novelty_weight = self.w_novelty
        arousal_decay = self.decay_a
        guard_cooling = 0.0
        if self.high_arousal_steps > 30:
            novelty_weight *= 0.70
            arousal_decay = min(0.99, max(self.decay_a + 0.04, 0.85))
            guard_cooling = 0.26
            self.saturation_guard_activations += 1

        # Recovery mode strengthens decays and dampens learning.
        valence_decay = self.decay_v
        uncertainty_decay = self.decay_u
        if self.recovery_mode:
            valence_decay = min(0.995, self.decay_v + 0.03)
            arousal_decay = min(0.995, arousal_decay + 0.03)
            uncertainty_decay = min(0.995, self.decay_u + 0.02)

        prev_valence = self.valence
        prev_arousal = self.arousal
        prev_uncertainty = self.uncertainty_tension

        # Core dynamics with nonlinear saturation and threshold effects.
        reward_drive = math.tanh(1.35 * reward)
        if abs(reward_drive) < 0.02:
            reward_drive = 0.0
        pe_linear_drive = math.tanh(1.50 * self.sustained_prediction_error)
        pe_threshold_drive = math.tanh(2.20 * max(0.0, self.sustained_prediction_error - 0.12))
        reward_efficacy = max(0.55, 1.0 - (0.35 * self.depressive_bias))
        valence_penalty = (0.65 * pe_linear_drive) + (0.35 * pe_threshold_drive)

        novelty_drive = 1.0 - math.exp(-2.8 * novelty)
        pe_arousal_drive = 1.0 - math.exp(-2.2 * pe)
        surprise_gate = max(0.0, self.sustained_prediction_error - 0.20)
        surprise_drive = 1.0 - math.exp(-2.8 * surprise_gate)
        resolution_cooling = 0.12 * (1.0 - math.exp(-2.4 * resolution))
        calm_rebound = 0.0
        if novelty < 0.15 and pe < 0.15 and resolution > 0.40:
            calm_rebound = _clamp((resolution - 0.40) / 0.60, 0.0, 1.0) * 0.05

        entropy_drive = math.tanh(1.9 * entropy)
        resolution_drive = 1.0 - math.exp(-2.4 * resolution)
        resolution_gate = 1.0 / (1.0 + math.exp(-12.0 * (resolution - 0.35)))
        uncertainty_relief = (0.55 * resolution_drive) + (0.45 * resolution_gate)

        next_valence = _clamp(
            valence_decay * self.valence
            + (self.w_reward * reward_drive * reward_efficacy)
            - (self.w_error * valence_penalty),
            -1.0,
            1.0,
        )
        next_arousal = _clamp(
            arousal_decay * self.arousal
            + (novelty_weight * novelty_drive)
            + (self.w_pe * pe_arousal_drive)
            + (0.10 * surprise_drive)
            - guard_cooling
            - resolution_cooling
            - calm_rebound,
            0.0,
            1.0,
        )
        next_uncertainty = _clamp(
            uncertainty_decay * self.uncertainty_tension
            + (self.w_entropy * entropy_drive)
            + (0.12 * surprise_drive)
            - (self.w_resolution * uncertainty_relief),
            0.0,
            1.0,
        )

        # Hard limit: no immediate jump above 0.3 per step.
        self.valence = _clamp(_clamp_delta(next_valence, prev_valence, 0.3), -1.0, 1.0)
        self.arousal = _clamp(_clamp_delta(next_arousal, prev_arousal, 0.3), 0.0, 1.0)
        self.uncertainty_tension = _clamp(_clamp_delta(next_uncertainty, prev_uncertainty, 0.3), 0.0, 1.0)

        if self.valence < -0.9:
            self.negative_valence_steps += 1
        else:
            self.negative_valence_steps = 0

        if self.arousal > 0.95:
            self.high_arousal_steps += 1
        else:
            self.high_arousal_steps = 0

        if self.negative_valence_steps > 50:
            if not self.recovery_mode:
                self.runaway_activations += 1
            self.recovery_mode = True
        elif self.recovery_mode and self.valence > -0.6:
            # Exit with hysteresis.
            self.recovery_mode = False

        # Chronic negative valence / depressive bias.
        neg_component = max(0.0, -self.valence)
        self.chronic_negative_valence = _clamp(
            0.98 * self.chronic_negative_valence + 0.02 * neg_component,
            0.0,
            1.0,
        )
        self.depressive_bias = _clamp(
            0.97 * self.depressive_bias + 0.03 * max(neg_component, self.chronic_negative_valence),
            0.0,
            1.0,
        )

        self.modulation_factors = self._compute_modulation_factors()
        self.neuromodulator_guidance = self._compute_neuromodulator_guidance()
        self._update_compatibility_fields()
        return self.snapshot()

    def apply_adjustments(
        self,
        affective_background: Any,
        neuromodulators: Any,
        adjustments: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """Backward-compatible application hook (neuromodulators only)."""
        _ = affective_background
        guidance = dict(((adjustments or {}).get("neuromodulator_shift", {}) or {}))
        if not guidance:
            guidance = dict(self.neuromodulator_guidance or {})
        self.apply_neuromodulator_guidance(neuromodulators, guidance=guidance, gain=1.0)

    def apply_neuromodulator_guidance(
        self,
        neuromodulators: Any,
        guidance: Optional[Dict[str, float]] = None,
        gain: float = 1.0,
    ) -> Dict[str, float]:
        """
        Apply slow CER guidance to neuromodulators.

        This is intentionally bounded and indirect (small deltas).
        """
        g = self._normalize_neuromodulator_guidance(guidance or self.neuromodulator_guidance)
        gain_v = _clamp(gain, 0.0, 2.0)
        applied: Dict[str, float] = {}
        if neuromodulators is None:
            return applied

        for key, delta in g.items():
            if not hasattr(neuromodulators, key):
                continue
            current = _safe_float(getattr(neuromodulators, key, 0.0), 0.0)
            candidate = current + (delta * gain_v)
            if hasattr(neuromodulators, "_clamp"):
                candidate = float(neuromodulators._clamp(candidate))
            else:
                candidate = _clamp(candidate, 0.0, 1.0)
            setattr(neuromodulators, key, candidate)
            applied[key] = float(candidate - current)

        try:
            neuromodulators.timestamp = time.time()
        except Exception:
            pass
        return applied

    def _compute_modulation_factors(self) -> Dict[str, float]:
        neg_valence = max(0.0, -self.valence)
        pos_valence = max(0.0, self.valence)

        exploration_bias = self.base_exploration + (self.k1 * self.arousal) - (self.k2 * neg_valence)
        if self.recovery_mode:
            exploration_bias += 0.12
        exploration_bias = _clamp(exploration_bias, 0.0, 1.5)

        learning_rate_scale = (
            1.0
            + (self.k3 * self.arousal)
            + (self.k4 * self.uncertainty_tension)
            - (self.k5 * self.chronic_negative_valence)
        )
        if self.recovery_mode:
            learning_rate_scale -= 0.20
        learning_rate_scale = _clamp(learning_rate_scale, 0.5, 2.0)

        novelty_sensitivity_scale = 1.0 + (self.k6 * self.arousal) - (self.k7 * self.depressive_bias)
        novelty_sensitivity_scale = _clamp(novelty_sensitivity_scale, 0.5, 2.0)

        decision_threshold_shift = (self.k8 * self.uncertainty_tension) - (self.k9 * pos_valence)
        decision_threshold_shift = _clamp(decision_threshold_shift, -0.5, 0.8)

        habit_gain_scale = (
            1.0
            + (self.k10 * self.chronic_negative_valence)
            + (self.k11 * self.uncertainty_tension)
            - (self.k12 * pos_valence)
        )
        if self.recovery_mode:
            habit_gain_scale += 0.12
        habit_gain_scale = _clamp(habit_gain_scale, 0.75, 1.6)

        return {
            "exploration_bias": float(exploration_bias),
            "learning_rate_scale": float(learning_rate_scale),
            "novelty_sensitivity_scale": float(novelty_sensitivity_scale),
            "decision_threshold_shift": float(decision_threshold_shift),
            "habit_gain_scale": float(habit_gain_scale),
        }

    def _compute_neuromodulator_guidance(self) -> Dict[str, float]:
        """
        Compute bounded top-down guidance deltas for neuromodulators.

        Mapping rationale:
        - valence/arousal -> dopamine (mPFC->VTA-like influence)
        - uncertainty/arousal -> norepinephrine (mPFC->LC-like influence)
        - chronic negative valence -> serotonin suppression (mPFC->DRN-like influence)
        - uncertainty/negative valence -> cortisol tension signal
        """
        pos_valence = max(0.0, self.valence)
        neg_valence = max(0.0, -self.valence)

        dopamine_delta = (
            +0.0022 * pos_valence
            +0.0014 * self.arousal
            -0.0016 * self.uncertainty_tension
            -0.0023 * neg_valence
        )
        norepinephrine_delta = (
            +0.0028 * self.uncertainty_tension
            +0.0012 * self.arousal
            -0.0008 * pos_valence
        )
        serotonin_delta = (
            +0.0018 * pos_valence
            -0.0026 * self.chronic_negative_valence
            -0.0012 * self.depressive_bias
        )
        cortisol_delta = (
            +0.0026 * self.uncertainty_tension
            +0.0020 * neg_valence
            -0.0012 * pos_valence
        )

        if self.recovery_mode:
            dopamine_delta -= 0.0009
            serotonin_delta += 0.0009
            cortisol_delta -= 0.0006

        return self._normalize_neuromodulator_guidance(
            {
                "dopamine": dopamine_delta,
                "norepinephrine": norepinephrine_delta,
                "serotonin": serotonin_delta,
                "cortisol": cortisol_delta,
            }
        )

    @staticmethod
    def _normalize_modulation_factors(data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        src = dict(data or {})
        return {
            "exploration_bias": _clamp(src.get("exploration_bias", 0.10), 0.0, 1.5),
            "learning_rate_scale": _clamp(src.get("learning_rate_scale", 1.0), 0.5, 2.0),
            "novelty_sensitivity_scale": _clamp(src.get("novelty_sensitivity_scale", 1.0), 0.5, 2.0),
            "decision_threshold_shift": _clamp(src.get("decision_threshold_shift", 0.0), -0.5, 0.8),
            "habit_gain_scale": _clamp(src.get("habit_gain_scale", 1.0), 0.75, 1.6),
        }

    @staticmethod
    def _normalize_neuromodulator_guidance(data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        src = dict(data or {})
        return {
            "dopamine": _clamp(src.get("dopamine", 0.0), -0.006, 0.006),
            "norepinephrine": _clamp(src.get("norepinephrine", 0.0), -0.006, 0.006),
            "serotonin": _clamp(src.get("serotonin", 0.0), -0.006, 0.006),
            "cortisol": _clamp(src.get("cortisol", 0.0), -0.006, 0.006),
        }

    def _update_compatibility_fields(self) -> None:
        if self.recovery_mode:
            mode = "containment"
        elif self.uncertainty_tension > 0.65 or self.arousal > 0.75:
            mode = "stabilizing"
        elif self.valence < -0.35:
            mode = "dampening"
        else:
            mode = "none"

        self.regulation_mode = mode
        self.regulation_active = mode != "none"
        self.applied_adjustments = {
            "background_shift": {},
            "neuromodulator_shift": {
                key: float(value)
                for key, value in dict(self.neuromodulator_guidance or {}).items()
                if abs(float(value)) > 1e-9
            },
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            # CER core
            "valence": float(self.valence),
            "arousal": float(self.arousal),
            "uncertainty_tension": float(self.uncertainty_tension),
            "sustained_prediction_error": float(self.sustained_prediction_error),
            "chronic_negative_valence": float(self.chronic_negative_valence),
            "depressive_bias": float(self.depressive_bias),
            "recovery_mode": bool(self.recovery_mode),
            "step_count": int(self.step_count),
            "modulation_factors": dict(self.modulation_factors),
            "neuromodulator_guidance": dict(self.neuromodulator_guidance),
            # Diagnostics
            "negative_valence_steps": int(self.negative_valence_steps),
            "high_arousal_steps": int(self.high_arousal_steps),
            "runaway_activations": int(self.runaway_activations),
            "saturation_guard_activations": int(self.saturation_guard_activations),
            "last_inputs": {
                "reward_signal": float(self._last_reward_signal),
                "prediction_error": float(self._last_prediction_error),
                "policy_entropy": float(self._last_policy_entropy),
                "time_delta": float(self.last_time_delta),
            },
            # Backward compatibility
            "regulation_active": bool(self.regulation_active),
            "regulation_mode": str(self.regulation_mode),
            "applied_adjustments": {
                "background_shift": dict(self.applied_adjustments.get("background_shift", {})),
                "neuromodulator_shift": dict(self.applied_adjustments.get("neuromodulator_shift", {})),
            },
            "target_emotion": self.last_target_emotion,
            "global_outlook": self.last_global_outlook,
            "last_update_ts": float(self.last_update_ts),
        }

    def sync_from_canonical(self, axes: Optional[Dict[str, Any]] = None) -> None:
        """Project A(t) onto CER fields. CER is not a second source of truth."""
        if not isinstance(axes, dict):
            return
        try:
            self.valence = _clamp(axes.get("valence", self.valence), -1.0, 1.0)
        except Exception:
            pass
        try:
            arousal = float(axes.get("arousal", 0.0))
            self.arousal = _clamp((arousal + 1.0) / 2.0, 0.0, 1.0)
        except Exception:
            pass

    def emit_internal_impulse(self) -> Dict[str, float]:
        """Small internal impulse from regulation state (not a parallel VAD canon)."""
        intensity = 0.12
        valence_drive = _clamp(self.valence * 0.15, -1.0, 1.0)
        arousal_drive = _clamp((self.arousal - 0.5) * 0.2, -1.0, 1.0)
        stress_drive = _clamp(max(0.0, -self.valence) * 0.2 + self.uncertainty_tension * 0.15, 0.0, 1.0)
        stability_drive = _clamp((-0.2 * self.uncertainty_tension) + (0.15 if self.recovery_mode else 0.0), -1.0, 1.0)
        return {
            "valence": valence_drive * intensity,
            "arousal": arousal_drive * intensity,
            "stress": stress_drive * intensity,
            "stability": stability_drive * intensity,
        }

    def to_dict(self) -> dict:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalRegulationLayer":
        data = dict(data or {})
        inst = cls(
            decay_v=data.get("decay_v", 0.95),
            decay_a=data.get("decay_a", 0.90),
            decay_u=data.get("decay_u", 0.94),
            ema_alpha=data.get("ema_alpha", 0.90),
            valence=data.get("valence", 0.0),
            arousal=data.get("arousal", 0.0),
            uncertainty_tension=data.get("uncertainty_tension", 0.0),
            sustained_prediction_error=data.get("sustained_prediction_error", 0.0),
            chronic_negative_valence=data.get("chronic_negative_valence", 0.0),
            depressive_bias=data.get("depressive_bias", 0.0),
            recovery_mode=bool(data.get("recovery_mode", False)),
            negative_valence_steps=int(_safe_float(data.get("negative_valence_steps", 0), 0.0)),
            high_arousal_steps=int(_safe_float(data.get("high_arousal_steps", 0), 0.0)),
            step_count=int(_safe_float(data.get("step_count", 0), 0.0)),
            runaway_activations=int(_safe_float(data.get("runaway_activations", 0), 0.0)),
            saturation_guard_activations=int(_safe_float(data.get("saturation_guard_activations", 0), 0.0)),
            modulation_factors=data.get("modulation_factors", {}),
            neuromodulator_guidance=data.get("neuromodulator_guidance", {}),
        )
        inst.regulation_active = bool(data.get("regulation_active", inst.regulation_active))
        inst.regulation_mode = str(data.get("regulation_mode", inst.regulation_mode))
        applied = data.get("applied_adjustments") or {}
        inst.applied_adjustments = {
            "background_shift": dict(applied.get("background_shift", {}) or {}),
            "neuromodulator_shift": dict(applied.get("neuromodulator_shift", {}) or {}),
        }
        inst.last_target_emotion = str(data.get("target_emotion", ""))
        inst.last_global_outlook = str(data.get("global_outlook", ""))
        inst.last_update_ts = _safe_float(data.get("last_update_ts", time.time()), time.time())
        return inst

    def describe_brief(self, max_lines: int = 2) -> str:
        lines = [
            f"CER v={self.valence:+.2f}, a={self.arousal:.2f}, u={self.uncertainty_tension:.2f}.",
            f"Mode: {self.regulation_mode}, recovery={self.recovery_mode}.",
        ]
        return "\n".join(lines[: max(1, int(max_lines))])


__all__ = ["EmotionalRegulationLayer"]
