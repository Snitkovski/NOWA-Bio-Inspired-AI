"""
Phase 4.5 - Stability Monitoring & Drift Control.

Read-only diagnostic layer that monitors long-horizon stability of:
- emotional state
- affective background
- neuromodulators
- emotional expectations
- Phase 4.4 regulation activation

The layer never modifies external components and never initiates regulation.
"""

from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

try:
    from neuromodulators import NeuromodulatorState
except Exception:  # pragma: no cover - defensive fallback
    NeuromodulatorState = None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, min_v: float = 0.0, max_v: float = 1.0) -> float:
    v = _safe_float(value, default=min_v)
    return max(min_v, min(max_v, v))


def _clamp_window(value: Any) -> int:
    try:
        window = int(value)
    except Exception:
        window = 500
    return max(500, min(2000, window))


_FLAG_KEYS = (
    "regulation_overuse",
    "background_drift",
    "neuromodulator_drift",
    "dominant_emotion_lock",
    "outlook_bias",
)

_NEURO_KEYS = ("dopamine", "norepinephrine", "serotonin", "cortisol")

_DEFAULT_WEIGHTS = {
    "regulation_overuse": 0.25,
    "background_drift": 0.25,
    "neuromodulator_drift": 0.25,
    "dominant_emotion_lock": 0.15,
    "outlook_bias": 0.10,
}

_DEFAULT_BASELINES = {
    "dopamine": getattr(NeuromodulatorState, "BASELINE_DA", 0.1),
    "norepinephrine": getattr(NeuromodulatorState, "BASELINE_NE", 0.1),
    "serotonin": getattr(NeuromodulatorState, "BASELINE_HT", 0.1),
    "cortisol": getattr(NeuromodulatorState, "BASELINE_CORT", 0.05),
}

_HYSTERESIS_FLAGS = (
    "background_drift",
    "neuromodulator_drift",
    "dominant_emotion_lock",
    "outlook_bias",
)


@dataclass
class StabilityMonitoringLayer:
    """
    Phase 4.5 monitoring layer.

    Returns:
        {
            "stability_index": float,
            "drift_flags": {
                "regulation_overuse": bool,
                "background_drift": bool,
                "neuromodulator_drift": bool,
                "dominant_emotion_lock": bool,
                "outlook_bias": bool
            },
            "recommendation": "none" |
                              "inspect_expectations" |
                              "inspect_memory" |
                              "inspect_regulation" |
                              "inspect_background" |
                              "inspect_neuromodulators"
        }
    """

    window_size: int = 500
    hysteresis_windows: int = 2
    baseline_warmup_samples: Optional[int] = None
    baseline_background: Optional[float] = None
    baseline_neuromodulators: Dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_BASELINES))
    weights: Dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))

    stability_index: float = 1.0
    drift_flags: Dict[str, bool] = field(default_factory=lambda: {key: False for key in _FLAG_KEYS})
    recommendation: str = "none"
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_update_ts: float = field(default_factory=time.time)

    _regulation_active_history: Deque[int] = field(default_factory=deque, repr=False)
    _background_anxiety_history: Deque[float] = field(default_factory=deque, repr=False)
    _neuromodulator_histories: Dict[str, Deque[float]] = field(default_factory=dict, repr=False)
    _outlook_history: Deque[str] = field(default_factory=deque, repr=False)
    _dominant_emotion_history: Deque[str] = field(default_factory=deque, repr=False)
    _dominant_intensity_history: Deque[float] = field(default_factory=deque, repr=False)
    _trigger_history: Deque[int] = field(default_factory=deque, repr=False)
    _background_baseline_buffer: Deque[float] = field(default_factory=deque, repr=False)
    _hysteresis_counts: Dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.window_size = _clamp_window(self.window_size)
        self.hysteresis_windows = max(1, int(_safe_float(self.hysteresis_windows, 2.0)))
        self.baseline_warmup_samples = self._resolve_baseline_warmup_samples(self.baseline_warmup_samples)
        self.baseline_background = (
            _clamp(self.baseline_background) if self.baseline_background is not None else None
        )
        self.baseline_neuromodulators = self._normalize_baselines(self.baseline_neuromodulators)
        self.weights = self._normalize_weights(self.weights)
        self.drift_flags = self._normalize_flags(self.drift_flags)
        self.recommendation = self._normalize_recommendation(self.recommendation)
        self.stability_index = _clamp(self.stability_index, 0.0, 1.0)
        self.metrics = dict(self.metrics or {})
        self._rebuild_histories()

    def update(
        self,
        emotional_state_snapshot: Optional[Dict[str, Any]],
        affective_background_snapshot: Optional[Dict[str, float]],
        neuromodulators_snapshot: Optional[Dict[str, float]],
        expectations_snapshot: Optional[Dict[str, Any]],
        regulation_snapshot: Optional[Dict[str, Any]],
        semantic_emotions_snapshot: Optional[Iterable[Dict[str, Any]]] = None,
        trigger_event: Optional[bool] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Update diagnostics from read-only snapshots.
        """
        self.last_update_ts = float(timestamp) if timestamp is not None else time.time()

        affect = dict(emotional_state_snapshot or {})
        background = dict(affective_background_snapshot or {})
        neuromods = dict(neuromodulators_snapshot or {})
        expectations = dict(expectations_snapshot or {})
        regulation = dict(regulation_snapshot or {})
        semantic = [dict(item) for item in (semantic_emotions_snapshot or [])]

        background_anxiety = _clamp(background.get("background_anxiety", 0.0), 0.0, 1.0)
        if self.baseline_background is None:
            self._background_baseline_buffer.append(float(background_anxiety))
            if len(self._background_baseline_buffer) >= int(self.baseline_warmup_samples or self.window_size):
                self.baseline_background = self._median(self._background_baseline_buffer)

        regulation_active = bool(regulation.get("regulation_active", False))
        self._regulation_active_history.append(1 if regulation_active else 0)
        self._background_anxiety_history.append(background_anxiety)

        for key in _NEURO_KEYS:
            level = neuromods.get(key, self.baseline_neuromodulators.get(key, 0.0))
            self._neuromodulator_histories[key].append(_clamp(level, 0.0, 1.0))

        outlook = str(expectations.get("global_outlook", "stabilizing") or "stabilizing")
        self._outlook_history.append(outlook)

        prev_emotion = self._dominant_emotion_history[-1] if self._dominant_emotion_history else ""
        dominant_emotion, dominant_intensity = self._extract_dominant_emotion(
            emotional_state_snapshot=affect,
            expectations_snapshot=expectations,
            semantic_emotions_snapshot=semantic,
        )
        inferred_trigger = bool(
            dominant_emotion
            and prev_emotion
            and dominant_emotion != prev_emotion
        )
        self._dominant_emotion_history.append(dominant_emotion)
        self._dominant_intensity_history.append(_clamp(dominant_intensity, 0.0, 1.0))
        effective_trigger = bool(trigger_event) if trigger_event is not None else inferred_trigger
        self._trigger_history.append(1 if effective_trigger else 0)

        sample_count = len(self._regulation_active_history)
        enough_data = sample_count >= self.window_size

        regulation_activation_rate = self._mean(self._regulation_active_history)
        mean_background = self._mean(self._background_anxiety_history)
        neuromodulator_means = {
            key: self._mean(history) for key, history in self._neuromodulator_histories.items()
        }

        dominant_ratio, dominant_name = self._dominant_ratio()
        dominant_growth = self._dominant_intensity_growth(dominant_name)
        trigger_ratio = self._mean(self._trigger_history)
        escalating_ratio = self._ratio(self._outlook_history, "escalating")

        baseline_ready = self.baseline_background is not None
        baseline_bg = float(self.baseline_background if self.baseline_background is not None else 0.0)
        raw_flags = {
            "regulation_overuse": bool(enough_data and regulation_activation_rate > 0.15),
            "background_drift": bool(enough_data and baseline_ready and mean_background > (baseline_bg + 0.20)),
            "neuromodulator_drift": bool(
                enough_data and any(
                    abs(float(neuromodulator_means.get(key, 0.0)) - float(self.baseline_neuromodulators.get(key, 0.0))) > 0.25
                    for key in _NEURO_KEYS
                )
            ),
            "dominant_emotion_lock": bool(
                enough_data
                and dominant_name
                and dominant_ratio > 0.70
                and dominant_growth <= 0.05
                and trigger_ratio <= 0.05
            ),
            "outlook_bias": bool(enough_data and escalating_ratio > 0.70),
        }

        flags = {
            "regulation_overuse": bool(raw_flags["regulation_overuse"]),
            "background_drift": self._apply_hysteresis("background_drift", raw_flags["background_drift"], enough_data),
            "neuromodulator_drift": self._apply_hysteresis(
                "neuromodulator_drift", raw_flags["neuromodulator_drift"], enough_data
            ),
            "dominant_emotion_lock": self._apply_hysteresis(
                "dominant_emotion_lock", raw_flags["dominant_emotion_lock"], enough_data
            ),
            "outlook_bias": self._apply_hysteresis("outlook_bias", raw_flags["outlook_bias"], enough_data),
        }

        self.drift_flags = flags
        self.recommendation = self._compute_recommendation(flags)
        self.stability_index = self._compute_stability_index(flags)
        self.metrics = {
            "sample_count": sample_count,
            "regulation_activation_rate": regulation_activation_rate,
            "mean_background_anxiety": mean_background,
            "baseline_background_ready": baseline_ready,
            "baseline_warmup_samples": int(self.baseline_warmup_samples or self.window_size),
            "baseline_warmup_progress": self._baseline_warmup_progress(),
            "baseline_background_anxiety": baseline_bg,
            "neuromodulator_means": dict(neuromodulator_means),
            "dominant_emotion": dominant_name,
            "dominant_emotion_ratio": dominant_ratio,
            "dominant_intensity_growth": dominant_growth,
            "trigger_ratio": trigger_ratio,
            "escalating_ratio": escalating_ratio,
            "raw_flags": dict(raw_flags),
        }

        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "stability_index": float(self.stability_index),
            "drift_flags": self._normalize_flags(self.drift_flags),
            "recommendation": self._normalize_recommendation(self.recommendation),
            "metrics": dict(self.metrics or {}),
            "last_update_ts": float(self.last_update_ts),
        }

    def to_dict(self) -> dict:
        return {
            "window_size": self.window_size,
            "hysteresis_windows": self.hysteresis_windows,
            "baseline_warmup_samples": self.baseline_warmup_samples,
            "baseline_background": self.baseline_background,
            "baseline_neuromodulators": dict(self.baseline_neuromodulators),
            "weights": dict(self.weights),
            "stability_index": self.stability_index,
            "drift_flags": self._normalize_flags(self.drift_flags),
            "recommendation": self._normalize_recommendation(self.recommendation),
            "metrics": dict(self.metrics or {}),
            "last_update_ts": self.last_update_ts,
            "history": {
                "regulation_active": list(self._regulation_active_history),
                "background_anxiety": list(self._background_anxiety_history),
                "outlook": list(self._outlook_history),
                "dominant_emotion": list(self._dominant_emotion_history),
                "dominant_intensity": list(self._dominant_intensity_history),
                "trigger": list(self._trigger_history),
                "baseline_buffer": list(self._background_baseline_buffer),
                "neuromodulators": {
                    key: list(self._neuromodulator_histories.get(key, []))
                    for key in _NEURO_KEYS
                },
            },
            "hysteresis_counts": dict(self._hysteresis_counts),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StabilityMonitoringLayer":
        inst = cls(
            window_size=data.get("window_size", 500),
            hysteresis_windows=data.get("hysteresis_windows", 2),
            baseline_warmup_samples=data.get("baseline_warmup_samples"),
            baseline_background=data.get("baseline_background"),
            baseline_neuromodulators=data.get("baseline_neuromodulators", {}),
            weights=data.get("weights", {}),
        )
        inst.stability_index = _clamp(data.get("stability_index", 1.0), 0.0, 1.0)
        inst.drift_flags = inst._normalize_flags(data.get("drift_flags", {}))
        inst.recommendation = inst._normalize_recommendation(data.get("recommendation", "none"))
        inst.metrics = dict(data.get("metrics", {}) or {})
        inst.last_update_ts = _safe_float(data.get("last_update_ts", time.time()), time.time())

        history = data.get("history", {}) or {}
        inst._regulation_active_history = deque(
            [1 if bool(v) else 0 for v in (history.get("regulation_active", []) or [])],
            maxlen=inst.window_size,
        )
        inst._background_anxiety_history = deque(
            [_clamp(v, 0.0, 1.0) for v in (history.get("background_anxiety", []) or [])],
            maxlen=inst.window_size,
        )
        inst._outlook_history = deque(
            [str(v) for v in (history.get("outlook", []) or [])],
            maxlen=inst.window_size,
        )
        inst._dominant_emotion_history = deque(
            [str(v) for v in (history.get("dominant_emotion", []) or [])],
            maxlen=inst.window_size,
        )
        inst._dominant_intensity_history = deque(
            [_clamp(v, 0.0, 1.0) for v in (history.get("dominant_intensity", []) or [])],
            maxlen=inst.window_size,
        )
        inst._trigger_history = deque(
            [1 if bool(v) else 0 for v in (history.get("trigger", []) or [])],
            maxlen=inst.window_size,
        )
        inst._background_baseline_buffer = deque(
            [_clamp(v, 0.0, 1.0) for v in (history.get("baseline_buffer", []) or [])],
            maxlen=int(inst.baseline_warmup_samples or inst.window_size),
        )

        nm_history = history.get("neuromodulators", {}) or {}
        inst._neuromodulator_histories = {}
        for key in _NEURO_KEYS:
            values = nm_history.get(key, []) or []
            inst._neuromodulator_histories[key] = deque(
                [_clamp(v, 0.0, 1.0) for v in values],
                maxlen=inst.window_size,
            )

        counts = data.get("hysteresis_counts", {}) or {}
        inst._hysteresis_counts = {
            key: max(0, int(_safe_float(counts.get(key, 0), 0.0)))
            for key in _HYSTERESIS_FLAGS
        }
        return inst

    def describe_brief(self, max_lines: int = 2) -> str:
        max_lines = max(1, int(max_lines))
        if not any(bool(self.drift_flags.get(key, False)) for key in _FLAG_KEYS):
            return "Слой стабильности: отклонений не обнаружено."

        lines: List[str] = [f"Индекс устойчивости: {self.stability_index:.2f}."]
        if self.recommendation != "none":
            lines.append(f"Рекомендация: {self.recommendation}.")
        return "\n".join(lines[:max_lines])

    def _rebuild_histories(self) -> None:
        self._regulation_active_history = deque(self._regulation_active_history, maxlen=self.window_size)
        self._background_anxiety_history = deque(self._background_anxiety_history, maxlen=self.window_size)
        self._outlook_history = deque(self._outlook_history, maxlen=self.window_size)
        self._dominant_emotion_history = deque(self._dominant_emotion_history, maxlen=self.window_size)
        self._dominant_intensity_history = deque(self._dominant_intensity_history, maxlen=self.window_size)
        self._trigger_history = deque(self._trigger_history, maxlen=self.window_size)
        self._background_baseline_buffer = deque(
            [_clamp(v, 0.0, 1.0) for v in self._background_baseline_buffer],
            maxlen=int(self.baseline_warmup_samples or self.window_size),
        )

        histories: Dict[str, Deque[float]] = {}
        for key in _NEURO_KEYS:
            histories[key] = deque(
                [_clamp(v, 0.0, 1.0) for v in self._neuromodulator_histories.get(key, [])],
                maxlen=self.window_size,
            )
        self._neuromodulator_histories = histories

        self._hysteresis_counts = {
            key: max(0, int(_safe_float(self._hysteresis_counts.get(key, 0), 0.0)))
            for key in _HYSTERESIS_FLAGS
        }

    def _normalize_weights(self, weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        result = dict(_DEFAULT_WEIGHTS)
        for key, value in (weights or {}).items():
            if key in _FLAG_KEYS:
                result[key] = _clamp(value, 0.0, 1.0)
        return result

    def _normalize_baselines(self, baselines: Optional[Dict[str, float]]) -> Dict[str, float]:
        result = dict(_DEFAULT_BASELINES)
        for key, value in (baselines or {}).items():
            if key in _NEURO_KEYS:
                result[key] = _clamp(value, 0.0, 1.0)
        return result

    @staticmethod
    def _normalize_flags(flags: Optional[Dict[str, Any]]) -> Dict[str, bool]:
        normalized = {key: False for key in _FLAG_KEYS}
        for key, value in (flags or {}).items():
            if key in normalized:
                normalized[key] = bool(value)
        return normalized

    @staticmethod
    def _normalize_recommendation(value: Any) -> str:
        rec = str(value or "none")
        if rec not in {
            "none",
            "inspect_expectations",
            "inspect_memory",
            "inspect_regulation",
            "inspect_background",
            "inspect_neuromodulators",
        }:
            return "none"
        return rec

    @staticmethod
    def _mean(values: Iterable[Any]) -> float:
        vals = [float(v) for v in values]
        if not vals:
            return 0.0
        return float(sum(vals)) / float(len(vals))

    @staticmethod
    def _ratio(values: Iterable[Any], target: str) -> float:
        vals = [str(v) for v in values]
        if not vals:
            return 0.0
        hits = sum(1 for v in vals if v == target)
        return float(hits) / float(len(vals))

    @staticmethod
    def _median(values: Iterable[Any]) -> float:
        vals = sorted(_clamp(v, 0.0, 1.0) for v in values)
        if not vals:
            return 0.0
        n = len(vals)
        mid = n // 2
        if n % 2 == 1:
            return float(vals[mid])
        return float((vals[mid - 1] + vals[mid]) / 2.0)

    def _resolve_baseline_warmup_samples(self, value: Optional[int]) -> int:
        if value is None:
            return int(self.window_size)
        try:
            samples = int(value)
        except Exception:
            samples = int(self.window_size)
        return max(1, min(int(self.window_size), samples))

    def _baseline_warmup_progress(self) -> float:
        target = float(self.baseline_warmup_samples or self.window_size)
        if target <= 0.0:
            return 1.0
        return _clamp(float(len(self._background_baseline_buffer)) / target, 0.0, 1.0)

    def _apply_hysteresis(self, flag_name: str, raw_condition: bool, enough_data: bool) -> bool:
        if flag_name not in _HYSTERESIS_FLAGS:
            return bool(raw_condition)

        if not enough_data:
            self._hysteresis_counts[flag_name] = 0
            return False

        if raw_condition:
            self._hysteresis_counts[flag_name] = int(self._hysteresis_counts.get(flag_name, 0)) + 1
        else:
            self._hysteresis_counts[flag_name] = 0

        return self._hysteresis_counts[flag_name] >= self.hysteresis_windows

    def _extract_dominant_emotion(
        self,
        emotional_state_snapshot: Dict[str, Any],
        expectations_snapshot: Dict[str, Any],
        semantic_emotions_snapshot: List[Dict[str, Any]],
    ) -> Tuple[str, float]:
        if semantic_emotions_snapshot:
            items = sorted(
                semantic_emotions_snapshot,
                key=lambda item: _safe_float(item.get("activation", 0.0), 0.0),
                reverse=True,
            )
            top = items[0]
            name = str(top.get("emotion", "")).strip()
            intensity = _clamp(top.get("activation", 0.0), 0.0, 1.0)
            return name, intensity

        expectations = list(expectations_snapshot.get("expectations", []) or [])
        if expectations:
            top = expectations[0]
            name = str(top.get("emotion", expectations_snapshot.get("dominant_forecast", ""))).strip()
            intensity = _clamp(top.get("probability", top.get("confidence", 0.0)), 0.0, 1.0)
            return name, intensity

        fallback_name = str(expectations_snapshot.get("dominant_forecast", "")).strip()
        if fallback_name:
            return fallback_name, 0.5

        valence = _safe_float(emotional_state_snapshot.get("valence", 0.0), 0.0)
        arousal_norm = _clamp(_safe_float(emotional_state_snapshot.get("arousal", 0.0), 0.0) / 2.0, 0.0, 1.0)
        if valence >= 0.15:
            return "positive", arousal_norm
        if valence <= -0.15:
            return "negative", arousal_norm
        return "", arousal_norm

    def _dominant_ratio(self) -> Tuple[float, str]:
        emotions = [name for name in self._dominant_emotion_history if name]
        if not emotions:
            return 0.0, ""
        counts = Counter(emotions)
        dominant, amount = counts.most_common(1)[0]
        return float(amount) / float(len(emotions)), str(dominant)

    def _dominant_intensity_growth(self, dominant_emotion: str) -> float:
        if not dominant_emotion:
            return 0.0
        intensities = [
            float(intensity)
            for emotion, intensity in zip(self._dominant_emotion_history, self._dominant_intensity_history)
            if emotion == dominant_emotion
        ]
        if len(intensities) < 4:
            return 0.0
        split = len(intensities) // 2
        if split <= 0 or split >= len(intensities):
            return 0.0
        early = sum(intensities[:split]) / float(split)
        recent = sum(intensities[split:]) / float(len(intensities) - split)
        return float(recent - early)

    def _compute_stability_index(self, flags: Dict[str, bool]) -> float:
        weighted_sum = 0.0
        for key, active in (flags or {}).items():
            if bool(active):
                weighted_sum += float(self.weights.get(key, 0.0))
        return _clamp(1.0 - weighted_sum, 0.0, 1.0)

    @staticmethod
    def _compute_recommendation(flags: Dict[str, bool]) -> str:
        if bool((flags or {}).get("regulation_overuse", False)):
            return "inspect_regulation"
        if bool((flags or {}).get("neuromodulator_drift", False)):
            return "inspect_neuromodulators"
        if bool((flags or {}).get("background_drift", False)):
            return "inspect_background"
        if bool((flags or {}).get("outlook_bias", False)):
            return "inspect_expectations"
        if bool((flags or {}).get("dominant_emotion_lock", False)):
            return "inspect_memory"
        return "none"


__all__ = ["StabilityMonitoringLayer"]
