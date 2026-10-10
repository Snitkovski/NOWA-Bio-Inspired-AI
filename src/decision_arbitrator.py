from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _mean(values: Iterable[float]) -> float:
    items = [float(v) for v in values if v is not None]
    if not items:
        return 0.0
    return sum(items) / float(len(items))


@dataclass
class DecisionArbitrator:
    """
    Arbitration layer that fuses EDPC, SAC, and affective uncertainty to pick
    decision mode and policy temperature.
    """

    enabled: bool = True
    w_td: float = 0.40
    w_error: float = 0.35
    w_surprise: float = 0.25
    td_var_scale: float = 0.5
    base_threshold: float = 0.55
    stress_gain: float = 0.25
    min_threshold: float = 0.25
    base_temp: float = 0.6
    uncertainty_gain: float = 0.8
    temp_min: float = 0.4
    temp_max: float = 1.5
    reliability_threshold: float = 0.35
    uncertainty_ema_beta: float = 0.2
    hysteresis_margin: float = 0.05
    deliberative_release_multiplier: float = 2.0
    _uncertainty_ema: float = field(default=0.0, init=False, repr=False)
    _ema_initialized: bool = field(default=False, init=False, repr=False)
    _last_decision_mode: str = field(default="HABITUAL", init=False, repr=False)

    def arbitrate(
        self,
        *,
        pressure_vector: Optional[Mapping[str, float]] = None,
        action_metadata: Optional[Mapping[str, Mapping[str, Any]]] = None,
        error_likelihood: Optional[float] = None,
        surprise: Optional[float] = None,
        stress_level: Optional[float] = None,
        action_stability_mean: Optional[float] = None,
        causality_mean: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not bool(self.enabled):
            self._last_decision_mode = "HABITUAL"
            return {
                "decision_mode": "HABITUAL",
                "global_uncertainty": 0.0,
                "global_uncertainty_raw": 0.0,
                "uncertainty_ema": float(self._uncertainty_ema),
                "policy_temperature": _clamp(self.base_temp, self.temp_min, self.temp_max),
                "policy_reliability": 1.0,
                "effective_threshold": _clamp(self.base_threshold, self.min_threshold, 1.0),
                "normalized_td_variance": 0.0,
            }

        td_variance = self._resolve_td_variance(
            pressure_vector=pressure_vector,
            action_metadata=action_metadata,
        )
        normalized_td_variance = _safe_float(td_variance) / max(1e-6, float(self.td_var_scale))
        error = _clamp(_safe_float(error_likelihood, 0.5), 0.0, 1.0)
        surprise_v = _clamp(_safe_float(surprise, 0.0), 0.0, 1.0)

        global_uncertainty_raw = (
            (self.w_td * normalized_td_variance)
            + (self.w_error * error)
            + (self.w_surprise * surprise_v)
        )
        global_uncertainty_raw = _clamp(global_uncertainty_raw, 0.0, 1.0)
        global_uncertainty = self._update_uncertainty_ema(global_uncertainty_raw)

        stress = _clamp(_safe_float(stress_level, 0.0), 0.0, 1.0)
        effective_threshold = _clamp(
            self.base_threshold - (self.stress_gain * stress),
            self.min_threshold,
            1.0,
        )
        decision_mode = self._resolve_mode(
            uncertainty=global_uncertainty,
            effective_threshold=effective_threshold,
        )

        temperature = self.base_temp + (self.uncertainty_gain * global_uncertainty)
        temperature = _clamp(temperature, self.temp_min, self.temp_max)

        if action_stability_mean is None or causality_mean is None:
            policy_reliability = 1.0
        else:
            stability_mean = _clamp(_safe_float(action_stability_mean, 0.0), 0.0, 1.0)
            causality_mean_v = _clamp(_safe_float(causality_mean, 0.0), 0.0, 1.0)
            policy_reliability = _clamp(
                stability_mean * (1.0 - global_uncertainty) * causality_mean_v,
                0.0,
                1.0,
            )

            if policy_reliability < float(self.reliability_threshold):
                decision_mode = "DELIBERATIVE"
        self._last_decision_mode = str(decision_mode).upper()

        return {
            "decision_mode": decision_mode,
            "global_uncertainty": float(global_uncertainty),
            "global_uncertainty_raw": float(global_uncertainty_raw),
            "uncertainty_ema": float(self._uncertainty_ema),
            "policy_temperature": float(temperature),
            "policy_reliability": float(policy_reliability),
            "effective_threshold": float(effective_threshold),
            "normalized_td_variance": float(normalized_td_variance),
            "hysteresis_margin": float(self.hysteresis_margin),
        }

    def _update_uncertainty_ema(self, uncertainty: float) -> float:
        current = _clamp(_safe_float(uncertainty, 0.0), 0.0, 1.0)
        beta = _clamp(_safe_float(self.uncertainty_ema_beta, 0.2), 0.01, 1.0)
        if not bool(self._ema_initialized):
            self._uncertainty_ema = current
            self._ema_initialized = True
            return float(self._uncertainty_ema)
        self._uncertainty_ema = _clamp(
            ((1.0 - beta) * float(self._uncertainty_ema)) + (beta * current),
            0.0,
            1.0,
        )
        return float(self._uncertainty_ema)

    def _resolve_mode(self, *, uncertainty: float, effective_threshold: float) -> str:
        margin = _clamp(_safe_float(self.hysteresis_margin, 0.05), 0.0, 0.3)
        release_mult = _clamp(_safe_float(self.deliberative_release_multiplier, 2.0), 1.0, 4.0)
        threshold = _clamp(_safe_float(effective_threshold, self.base_threshold), self.min_threshold, 1.0)
        prev_mode = str(getattr(self, "_last_decision_mode", "HABITUAL")).upper()
        uncertainty_v = _clamp(_safe_float(uncertainty, 0.0), 0.0, 1.0)

        if prev_mode == "DELIBERATIVE":
            downshift_threshold = _clamp(threshold - (margin * release_mult), self.min_threshold, 1.0)
            if uncertainty_v > downshift_threshold:
                return "DELIBERATIVE"
            return "HABITUAL"

        upshift_threshold = _clamp(threshold + margin, self.min_threshold, 1.0)
        if uncertainty_v > upshift_threshold:
            return "DELIBERATIVE"
        return "HABITUAL"

    def _resolve_td_variance(
        self,
        *,
        pressure_vector: Optional[Mapping[str, float]],
        action_metadata: Optional[Mapping[str, Mapping[str, Any]]],
    ) -> float:
        if not isinstance(action_metadata, Mapping):
            return 0.0

        weights: Dict[str, float] = {}
        if isinstance(pressure_vector, Mapping):
            for action, pressure in pressure_vector.items():
                weights[str(action)] = max(0.0, _safe_float(pressure, 0.0))

        td_values = []
        if weights:
            total = sum(weights.values())
            if total > 0.0:
                for action, weight in weights.items():
                    meta = action_metadata.get(action, {})
                    if isinstance(meta, Mapping):
                        td_variance = _safe_float(meta.get("td_variance", 0.0))
                    else:
                        td_variance = 0.0
                    td_values.append(td_variance * (weight / total))
                return sum(td_values)

        # Fallback: mean TD variance across available metadata.
        for meta in action_metadata.values():
            if isinstance(meta, Mapping):
                td_values.append(_safe_float(meta.get("td_variance", 0.0)))
        return _mean(td_values)
