"""
Conflict & Arbitration layer (ACC-like).

The module monitors conflict/error demand and emits control modulation signals.
It never selects actions directly and never rewrites reward/CER/Hippocampus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    v = _safe_float(value, lo)
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _mean_abs(values: Iterable[Any]) -> float:
    arr: List[float] = []
    for item in values or []:
        arr.append(abs(_safe_float(item, 0.0)))
    if not arr:
        return 0.0
    return sum(arr) / float(len(arr))


@dataclass
class ConflictArbitrationLayer:
    # Conflict-score weights.
    w_top2_gap: float = 0.34
    w_entropy: float = 0.30
    w_wm_load: float = 0.20
    w_pattern_confidence: float = 0.16

    # Error-likelihood weights.
    a_prediction_error: float = 0.45
    a_recent_failure: float = 0.35
    a_conflict: float = 0.20

    # Control-demand weights.
    b_conflict: float = 0.35
    b_error: float = 0.40
    b_task_complexity: float = 0.25
    b_latency: float = 0.10

    # Hysteresis thresholds.
    habitual_enter_conflict: float = 0.32
    habitual_exit_conflict: float = 0.44
    deliberative_enter_conflict: float = 0.66
    deliberative_exit_conflict: float = 0.52

    # Mode guards.
    error_low_threshold: float = 0.25
    error_high_threshold: float = 0.60
    error_recover_threshold: float = 0.45
    novelty_low_threshold: float = 0.30
    novelty_exploration_threshold: float = 0.65

    # Inhibit triggers.
    inhibit_conflict_threshold: float = 0.72
    inhibit_error_threshold: float = 0.72
    inhibit_failure_threshold: float = 0.65

    # Hard constraints.
    control_cost_gain: float = 0.06
    control_cost_decay: float = 0.025
    control_cost_limit: float = 1.0
    refractory_steps_after_deliberative: int = 3
    max_inhibit_streak: int = 2
    failure_window_size: int = 24
    error_window_size: int = 24

    # Runtime state.
    control_mode: str = "balanced"
    control_cost: float = 0.0
    refractory_remaining: int = 0
    inhibit_streak: int = 0
    mode_switches: int = 0
    forced_downshift_count: int = 0
    refractory_blocks: int = 0
    inhibit_cap_blocks: int = 0
    recent_failure_rate: float = 0.0
    recent_failures: List[float] = field(default_factory=list)
    error_history_window: List[float] = field(default_factory=list)
    mode_counts: Dict[str, int] = field(
        default_factory=lambda: {
            "habitual": 0,
            "balanced": 0,
            "deliberative": 0,
            "inhibit": 0,
        }
    )
    last_metrics: Dict[str, float] = field(default_factory=dict)
    last_output: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.w_top2_gap = max(0.0, _safe_float(self.w_top2_gap, 0.34))
        self.w_entropy = max(0.0, _safe_float(self.w_entropy, 0.30))
        self.w_wm_load = max(0.0, _safe_float(self.w_wm_load, 0.20))
        self.w_pattern_confidence = max(0.0, _safe_float(self.w_pattern_confidence, 0.16))

        self.a_prediction_error = max(0.0, _safe_float(self.a_prediction_error, 0.45))
        self.a_recent_failure = max(0.0, _safe_float(self.a_recent_failure, 0.35))
        self.a_conflict = max(0.0, _safe_float(self.a_conflict, 0.20))

        self.b_conflict = max(0.0, _safe_float(self.b_conflict, 0.35))
        self.b_error = max(0.0, _safe_float(self.b_error, 0.40))
        self.b_task_complexity = max(0.0, _safe_float(self.b_task_complexity, 0.25))
        self.b_latency = max(0.0, _safe_float(self.b_latency, 0.10))

        self.habitual_enter_conflict = _clamp(self.habitual_enter_conflict, 0.0, 1.0)
        self.habitual_exit_conflict = _clamp(
            max(self.habitual_enter_conflict + 0.02, _safe_float(self.habitual_exit_conflict, 0.44)),
            0.0,
            1.0,
        )
        self.deliberative_enter_conflict = _clamp(self.deliberative_enter_conflict, 0.0, 1.0)
        self.deliberative_exit_conflict = _clamp(
            min(self.deliberative_enter_conflict - 0.02, _safe_float(self.deliberative_exit_conflict, 0.52)),
            0.0,
            1.0,
        )

        self.error_low_threshold = _clamp(self.error_low_threshold, 0.0, 1.0)
        self.error_high_threshold = _clamp(self.error_high_threshold, 0.0, 1.0)
        self.error_recover_threshold = _clamp(self.error_recover_threshold, 0.0, 1.0)
        self.novelty_low_threshold = _clamp(self.novelty_low_threshold, 0.0, 1.0)
        self.novelty_exploration_threshold = _clamp(self.novelty_exploration_threshold, 0.0, 1.0)

        self.inhibit_conflict_threshold = _clamp(self.inhibit_conflict_threshold, 0.0, 1.0)
        self.inhibit_error_threshold = _clamp(self.inhibit_error_threshold, 0.0, 1.0)
        self.inhibit_failure_threshold = _clamp(self.inhibit_failure_threshold, 0.0, 1.0)

        self.control_cost_gain = max(0.0, _safe_float(self.control_cost_gain, 0.06))
        self.control_cost_decay = max(0.0, _safe_float(self.control_cost_decay, 0.025))
        self.control_cost_limit = max(0.05, _safe_float(self.control_cost_limit, 1.0))

        self.refractory_steps_after_deliberative = max(
            0,
            int(_safe_float(self.refractory_steps_after_deliberative, 3)),
        )
        self.max_inhibit_streak = max(1, int(_safe_float(self.max_inhibit_streak, 2)))
        self.failure_window_size = max(4, int(_safe_float(self.failure_window_size, 24)))
        self.error_window_size = max(4, int(_safe_float(self.error_window_size, 24)))

        self.control_mode = self._normalize_mode(self.control_mode)
        self.control_cost = max(0.0, _safe_float(self.control_cost, 0.0))
        self.refractory_remaining = max(0, int(_safe_float(self.refractory_remaining, 0)))
        self.inhibit_streak = max(0, int(_safe_float(self.inhibit_streak, 0)))
        self.mode_switches = max(0, int(_safe_float(self.mode_switches, 0)))
        self.forced_downshift_count = max(0, int(_safe_float(self.forced_downshift_count, 0)))
        self.refractory_blocks = max(0, int(_safe_float(self.refractory_blocks, 0)))
        self.inhibit_cap_blocks = max(0, int(_safe_float(self.inhibit_cap_blocks, 0)))
        self.recent_failure_rate = _clamp(self.recent_failure_rate, 0.0, 1.0)

        self.recent_failures = [_clamp(v, 0.0, 1.0) for v in list(self.recent_failures or [])][-self.failure_window_size :]
        self.error_history_window = [
            _clamp(abs(_safe_float(v, 0.0)), 0.0, 1.0) for v in list(self.error_history_window or [])
        ][-self.error_window_size :]

        mode_counts_norm = {"habitual": 0, "balanced": 0, "deliberative": 0, "inhibit": 0}
        for mode, count in dict(self.mode_counts or {}).items():
            mode_norm = self._normalize_mode(mode)
            mode_counts_norm[mode_norm] = max(0, int(_safe_float(count, 0)))
        self.mode_counts = mode_counts_norm
        self.last_metrics = {
            str(k): _safe_float(v, 0.0) for k, v in dict(self.last_metrics or {}).items()
        }
        self.last_output = dict(self.last_output or {})

    @staticmethod
    def _normalize_mode(mode: Any) -> str:
        value = str(mode or "balanced").strip().lower()
        if value in ("habitual", "balanced", "deliberative", "inhibit"):
            return value
        return "balanced"

    @staticmethod
    def _weighted_norm(values: Dict[str, float], weights: Dict[str, float]) -> float:
        total_w = 0.0
        acc = 0.0
        for key, value in values.items():
            w = max(0.0, _safe_float(weights.get(key, 0.0), 0.0))
            total_w += w
            acc += _clamp(value, 0.0, 1.0) * w
        if total_w <= 0.0:
            return 0.0
        return _clamp(acc / total_w, 0.0, 1.0)

    @staticmethod
    def _top2_gap_from_signals(go_signals: Iterable[Any]) -> float:
        vals = sorted([max(0.0, _safe_float(v, 0.0)) for v in (go_signals or [])], reverse=True)
        if not vals:
            return 0.0
        if len(vals) == 1:
            return 1.0
        top = vals[0]
        second = vals[1]
        if top <= 1e-12:
            return 0.0
        return _clamp((top - second) / top, 0.0, 1.0)

    def register_outcome(self, reward_signal: float, prediction_error: float = 0.0) -> None:
        from learning_guard import guard_owned_writer

        if not guard_owned_writer(self, "ConflictArbitrationLayer.register_outcome"):
            return
        failure_flag = 1.0 if _safe_float(reward_signal, 0.0) < 0.0 else 0.0
        self.recent_failures.append(failure_flag)
        if len(self.recent_failures) > self.failure_window_size:
            self.recent_failures = self.recent_failures[-self.failure_window_size :]
        if self.recent_failures:
            self.recent_failure_rate = _clamp(
                sum(self.recent_failures) / float(len(self.recent_failures)),
                0.0,
                1.0,
            )
        else:
            self.recent_failure_rate = 0.0

        self.error_history_window.append(_clamp(abs(_safe_float(prediction_error, 0.0)), 0.0, 1.0))
        if len(self.error_history_window) > self.error_window_size:
            self.error_history_window = self.error_history_window[-self.error_window_size :]

    def _regime_intensity(self, mode: str) -> float:
        mapping = {
            "habitual": 0.20,
            "balanced": 0.55,
            "deliberative": 1.00,
            "inhibit": 1.20,
        }
        return float(mapping.get(mode, 0.55))

    def _select_mode(
        self,
        conflict_score: float,
        error_likelihood: float,
        novelty_score: float,
        recent_failure_rate: float,
    ) -> str:
        prev_mode = self._normalize_mode(self.control_mode)
        mode = "balanced"

        # Inhibit has top priority under repeated failure pressure.
        if (
            conflict_score >= self.inhibit_conflict_threshold
            and error_likelihood >= self.inhibit_error_threshold
            and recent_failure_rate >= self.inhibit_failure_threshold
        ):
            mode = "inhibit"
        else:
            if prev_mode == "deliberative":
                if (
                    conflict_score >= self.deliberative_exit_conflict
                    and error_likelihood >= self.error_recover_threshold
                ):
                    mode = "deliberative"
                else:
                    mode = "balanced"
            elif prev_mode == "habitual":
                if (
                    conflict_score <= self.habitual_exit_conflict
                    and error_likelihood <= self.error_recover_threshold
                ):
                    mode = "habitual"
                else:
                    mode = "balanced"

            can_enter_deliberative = (
                self.refractory_remaining <= 0 or prev_mode == "deliberative"
            )
            if (
                mode != "deliberative"
                and can_enter_deliberative
                and conflict_score >= self.deliberative_enter_conflict
                and error_likelihood >= self.error_high_threshold
            ):
                mode = "deliberative"

            if mode not in ("deliberative", "inhibit"):
                if (
                    conflict_score <= self.habitual_enter_conflict
                    and error_likelihood <= self.error_low_threshold
                    and novelty_score <= self.novelty_low_threshold
                ):
                    mode = "habitual"
                elif (
                    prev_mode == "habitual"
                    and conflict_score <= self.habitual_exit_conflict
                    and error_likelihood <= self.error_recover_threshold
                ):
                    mode = "habitual"

        return self._normalize_mode(mode)

    def arbitrate(
        self,
        *,
        go_signals: Optional[Iterable[Any]] = None,
        top2_gap: Optional[float] = None,
        policy_entropy: float = 0.0,
        decision_latency: float = 0.0,
        threshold_current: float = 0.0,
        arousal: float = 0.0,
        stress_level: float = 0.0,
        valence: float = 0.0,
        novelty_score: float = 0.0,
        pattern_completion_confidence: float = 0.0,
        prediction_error: float = 0.0,
        recent_failure_rate: Optional[float] = None,
        error_history_window: Optional[Iterable[Any]] = None,
        working_memory_load: float = 0.0,
        task_complexity: float = 0.0,
    ) -> Dict[str, Any]:
        # Refractory countdown is time-based (per-step).
        if self.refractory_remaining > 0:
            self.refractory_remaining -= 1

        go_list = [max(0.0, _safe_float(v, 0.0)) for v in (go_signals or [])]
        gap_fallback = self._top2_gap_from_signals(go_list)
        top2_gap_norm = _clamp(top2_gap if top2_gap is not None else gap_fallback, 0.0, 1.0)
        entropy_norm = _clamp(policy_entropy, 0.0, 1.0)
        wm_load_norm = _clamp(working_memory_load, 0.0, 1.0)
        pattern_confidence = _clamp(pattern_completion_confidence, 0.0, 1.0)
        novelty_norm = _clamp(novelty_score, 0.0, 1.0)
        task_complexity_norm = _clamp(task_complexity, 0.0, 1.0)
        threshold_norm = _clamp((_safe_float(threshold_current, 0.0) + 0.5) / 1.5, 0.0, 1.0)
        latency_norm = _clamp(decision_latency, 0.0, 1.0)
        _ = threshold_norm

        if error_history_window is not None:
            history_norm = [
                _clamp(abs(_safe_float(v, 0.0)), 0.0, 1.0)
                for v in list(error_history_window or [])
            ]
            if history_norm:
                self.error_history_window = history_norm[-self.error_window_size :]
        pe_norm = _clamp(abs(_safe_float(prediction_error, 0.0)), 0.0, 1.0)
        if pe_norm <= 1e-9 and self.error_history_window:
            pe_norm = _clamp(_mean_abs(self.error_history_window), 0.0, 1.0)

        if recent_failure_rate is None:
            failure_rate = _clamp(self.recent_failure_rate, 0.0, 1.0)
        else:
            failure_rate = _clamp(recent_failure_rate, 0.0, 1.0)
            self.recent_failure_rate = failure_rate

        conflict_score = self._weighted_norm(
            {
                "gap": 1.0 - top2_gap_norm,
                "entropy": entropy_norm,
                "wm": wm_load_norm,
                "pattern": 1.0 - pattern_confidence,
            },
            {
                "gap": self.w_top2_gap,
                "entropy": self.w_entropy,
                "wm": self.w_wm_load,
                "pattern": self.w_pattern_confidence,
            },
        )
        error_likelihood = self._weighted_norm(
            {
                "pe": pe_norm,
                "failure": failure_rate,
                "conflict": conflict_score,
            },
            {
                "pe": self.a_prediction_error,
                "failure": self.a_recent_failure,
                "conflict": self.a_conflict,
            },
        )
        control_demand = self._weighted_norm(
            {
                "conflict": conflict_score,
                "error": error_likelihood,
                "task": task_complexity_norm,
                "latency": latency_norm,
            },
            {
                "conflict": self.b_conflict,
                "error": self.b_error,
                "task": self.b_task_complexity,
                "latency": self.b_latency,
            },
        )

        previous_mode = self._normalize_mode(self.control_mode)
        mode = self._select_mode(
            conflict_score=conflict_score,
            error_likelihood=error_likelihood,
            novelty_score=novelty_norm,
            recent_failure_rate=failure_rate,
        )

        if (
            mode == "deliberative"
            and previous_mode != "deliberative"
            and self.refractory_remaining > 0
        ):
            mode = "balanced"
            self.refractory_blocks += 1

        if mode == "inhibit" and self.inhibit_streak >= self.max_inhibit_streak:
            mode = "balanced"
            self.inhibit_cap_blocks += 1

        self.control_cost = max(0.0, self.control_cost - self.control_cost_decay)
        intensity = self._regime_intensity(mode)
        projected_cost = self.control_cost + (self.control_cost_gain * intensity)
        if projected_cost > self.control_cost_limit and mode in ("deliberative", "inhibit"):
            mode = "balanced"
            intensity = self._regime_intensity(mode)
            projected_cost = self.control_cost + (self.control_cost_gain * intensity)
            self.forced_downshift_count += 1
        self.control_cost = max(0.0, min(self.control_cost_limit * 2.0, projected_cost))

        if previous_mode == "deliberative" and mode != "deliberative":
            self.refractory_remaining = max(
                self.refractory_remaining,
                int(self.refractory_steps_after_deliberative),
            )

        if mode == "inhibit":
            self.inhibit_streak += 1
        else:
            self.inhibit_streak = 0

        if mode != previous_mode:
            self.mode_switches += 1
        self.control_mode = mode
        self.mode_counts[mode] = int(self.mode_counts.get(mode, 0)) + 1

        if mode == "habitual":
            threshold_delta = _clamp(-0.05 - (0.10 * (1.0 - conflict_score)), -0.30, 0.0)
            control_gain = _clamp(0.80 + (0.05 * (1.0 - error_likelihood)), 0.70, 1.20)
            wm_boost_flag = False
            exploration_override = False
            inhibit_action = False
        elif mode == "balanced":
            threshold_delta = _clamp(0.03 * (control_demand - 0.5), -0.08, 0.12)
            control_gain = _clamp(0.95 + (0.15 * control_demand), 0.80, 1.25)
            wm_boost_flag = bool(control_demand >= 0.72)
            exploration_override = False
            inhibit_action = False
        elif mode == "deliberative":
            threshold_delta = _clamp(0.10 + (0.22 * control_demand), 0.08, 0.55)
            control_gain = _clamp(1.10 + (0.25 * control_demand), 1.00, 1.60)
            wm_boost_flag = True
            exploration_override = bool(novelty_norm >= self.novelty_exploration_threshold)
            inhibit_action = False
        else:  # inhibit
            threshold_delta = _clamp(0.28 + (0.24 * control_demand), 0.20, 0.80)
            control_gain = _clamp(1.20 + (0.20 * control_demand), 1.05, 1.60)
            wm_boost_flag = True
            exploration_override = False
            inhibit_action = True

        metrics = {
            "conflict_score": float(conflict_score),
            "error_likelihood": float(error_likelihood),
            "control_demand": float(control_demand),
            "top2_gap_norm": float(top2_gap_norm),
            "entropy_norm": float(entropy_norm),
            "wm_load_norm": float(wm_load_norm),
            "pattern_confidence": float(pattern_confidence),
            "prediction_error_norm": float(pe_norm),
            "recent_failure_rate": float(failure_rate),
            "task_complexity_norm": float(task_complexity_norm),
            # Diagnostics-only values; never used in conflict equation.
            "arousal": float(_clamp(arousal, 0.0, 1.0)),
            "stress_level": float(_clamp(stress_level, 0.0, 1.0)),
            "valence": float(_clamp(valence, -1.0, 1.0)),
            "decision_latency_norm": float(_clamp(decision_latency, 0.0, 1.0)),
            "threshold_current_norm": float(threshold_norm),
        }
        self.last_metrics = dict(metrics)

        output = {
            "control_mode": mode,
            "threshold_delta": float(threshold_delta),
            "control_gain_multiplier": float(control_gain),
            "wm_boost_flag": bool(wm_boost_flag),
            "exploration_override": bool(exploration_override),
            "request_additional_evaluation": bool(mode == "inhibit"),
            "inhibit_action": bool(inhibit_action),
            "regime_intensity": float(intensity),
            "metrics": dict(metrics),
            "affective_impulse": {
                "stress": float(_clamp(0.12 * float(conflict_score), 0.0, 0.2)) if float(conflict_score) >= 0.5 else 0.0,
                "arousal": float(_clamp(0.08 * float(conflict_score), 0.0, 0.15)) if float(conflict_score) >= 0.5 else 0.0,
            },
            "diagnostics": {
                "control_cost": float(self.control_cost),
                "control_cost_limit": float(self.control_cost_limit),
                "refractory_remaining": int(self.refractory_remaining),
                "inhibit_streak": int(self.inhibit_streak),
                "mode_switches": int(self.mode_switches),
                "forced_downshift_count": int(self.forced_downshift_count),
                "refractory_blocks": int(self.refractory_blocks),
                "inhibit_cap_blocks": int(self.inhibit_cap_blocks),
            },
        }
        self.last_output = dict(output)
        return output

    def snapshot(self) -> Dict[str, Any]:
        mode_total = max(1, sum(int(v) for v in dict(self.mode_counts or {}).values()))
        mode_distribution = {
            mode: float(int(count)) / float(mode_total)
            for mode, count in dict(self.mode_counts or {}).items()
        }
        return {
            "control_mode": str(self.control_mode),
            "control_cost": float(self.control_cost),
            "control_cost_limit": float(self.control_cost_limit),
            "refractory_remaining": int(self.refractory_remaining),
            "inhibit_streak": int(self.inhibit_streak),
            "recent_failure_rate": float(self.recent_failure_rate),
            "mode_counts": {k: int(v) for k, v in dict(self.mode_counts or {}).items()},
            "mode_distribution": mode_distribution,
            "mode_switches": int(self.mode_switches),
            "forced_downshift_count": int(self.forced_downshift_count),
            "refractory_blocks": int(self.refractory_blocks),
            "inhibit_cap_blocks": int(self.inhibit_cap_blocks),
            "last_metrics": dict(self.last_metrics),
            "last_output": dict(self.last_output),
            "recent_failures": list(self.recent_failures),
            "error_history_window": list(self.error_history_window),
            "config": {
                "weights": {
                    "conflict": {
                        "w_top2_gap": float(self.w_top2_gap),
                        "w_entropy": float(self.w_entropy),
                        "w_wm_load": float(self.w_wm_load),
                        "w_pattern_confidence": float(self.w_pattern_confidence),
                    },
                    "error": {
                        "a_prediction_error": float(self.a_prediction_error),
                        "a_recent_failure": float(self.a_recent_failure),
                        "a_conflict": float(self.a_conflict),
                    },
                    "control": {
                        "b_conflict": float(self.b_conflict),
                        "b_error": float(self.b_error),
                        "b_task_complexity": float(self.b_task_complexity),
                        "b_latency": float(self.b_latency),
                    },
                },
                "thresholds": {
                    "habitual_enter_conflict": float(self.habitual_enter_conflict),
                    "habitual_exit_conflict": float(self.habitual_exit_conflict),
                    "deliberative_enter_conflict": float(self.deliberative_enter_conflict),
                    "deliberative_exit_conflict": float(self.deliberative_exit_conflict),
                    "error_low_threshold": float(self.error_low_threshold),
                    "error_high_threshold": float(self.error_high_threshold),
                    "error_recover_threshold": float(self.error_recover_threshold),
                    "inhibit_conflict_threshold": float(self.inhibit_conflict_threshold),
                    "inhibit_error_threshold": float(self.inhibit_error_threshold),
                    "inhibit_failure_threshold": float(self.inhibit_failure_threshold),
                },
                "constraints": {
                    "control_cost_gain": float(self.control_cost_gain),
                    "control_cost_decay": float(self.control_cost_decay),
                    "refractory_steps_after_deliberative": int(self.refractory_steps_after_deliberative),
                    "max_inhibit_streak": int(self.max_inhibit_streak),
                    "failure_window_size": int(self.failure_window_size),
                    "error_window_size": int(self.error_window_size),
                },
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictArbitrationLayer":
        src = dict(data or {})
        cfg = dict(src.get("config", {}) or {})
        cfg_weights = dict(cfg.get("weights", {}) or {})
        cfg_conflict = dict(cfg_weights.get("conflict", {}) or {})
        cfg_error = dict(cfg_weights.get("error", {}) or {})
        cfg_control = dict(cfg_weights.get("control", {}) or {})
        cfg_thresholds = dict(cfg.get("thresholds", {}) or {})
        cfg_constraints = dict(cfg.get("constraints", {}) or {})

        inst = cls(
            w_top2_gap=cfg_conflict.get("w_top2_gap", src.get("w_top2_gap", 0.34)),
            w_entropy=cfg_conflict.get("w_entropy", src.get("w_entropy", 0.30)),
            w_wm_load=cfg_conflict.get("w_wm_load", src.get("w_wm_load", 0.20)),
            w_pattern_confidence=cfg_conflict.get(
                "w_pattern_confidence",
                src.get("w_pattern_confidence", 0.16),
            ),
            a_prediction_error=cfg_error.get("a_prediction_error", src.get("a_prediction_error", 0.45)),
            a_recent_failure=cfg_error.get("a_recent_failure", src.get("a_recent_failure", 0.35)),
            a_conflict=cfg_error.get("a_conflict", src.get("a_conflict", 0.20)),
            b_conflict=cfg_control.get("b_conflict", src.get("b_conflict", 0.35)),
            b_error=cfg_control.get("b_error", src.get("b_error", 0.40)),
            b_task_complexity=cfg_control.get(
                "b_task_complexity",
                src.get("b_task_complexity", 0.25),
            ),
            b_latency=cfg_control.get("b_latency", src.get("b_latency", 0.10)),
            habitual_enter_conflict=cfg_thresholds.get(
                "habitual_enter_conflict",
                src.get("habitual_enter_conflict", 0.32),
            ),
            habitual_exit_conflict=cfg_thresholds.get(
                "habitual_exit_conflict",
                src.get("habitual_exit_conflict", 0.44),
            ),
            deliberative_enter_conflict=cfg_thresholds.get(
                "deliberative_enter_conflict",
                src.get("deliberative_enter_conflict", 0.66),
            ),
            deliberative_exit_conflict=cfg_thresholds.get(
                "deliberative_exit_conflict",
                src.get("deliberative_exit_conflict", 0.52),
            ),
            error_low_threshold=cfg_thresholds.get(
                "error_low_threshold",
                src.get("error_low_threshold", 0.25),
            ),
            error_high_threshold=cfg_thresholds.get(
                "error_high_threshold",
                src.get("error_high_threshold", 0.60),
            ),
            error_recover_threshold=cfg_thresholds.get(
                "error_recover_threshold",
                src.get("error_recover_threshold", 0.45),
            ),
            inhibit_conflict_threshold=cfg_thresholds.get(
                "inhibit_conflict_threshold",
                src.get("inhibit_conflict_threshold", 0.72),
            ),
            inhibit_error_threshold=cfg_thresholds.get(
                "inhibit_error_threshold",
                src.get("inhibit_error_threshold", 0.72),
            ),
            inhibit_failure_threshold=cfg_thresholds.get(
                "inhibit_failure_threshold",
                src.get("inhibit_failure_threshold", 0.65),
            ),
            control_cost_gain=cfg_constraints.get(
                "control_cost_gain",
                src.get("control_cost_gain", 0.06),
            ),
            control_cost_decay=cfg_constraints.get(
                "control_cost_decay",
                src.get("control_cost_decay", 0.025),
            ),
            control_cost_limit=src.get("control_cost_limit", cfg_constraints.get("control_cost_limit", 1.0)),
            refractory_steps_after_deliberative=cfg_constraints.get(
                "refractory_steps_after_deliberative",
                src.get("refractory_steps_after_deliberative", 3),
            ),
            max_inhibit_streak=cfg_constraints.get(
                "max_inhibit_streak",
                src.get("max_inhibit_streak", 2),
            ),
            failure_window_size=cfg_constraints.get(
                "failure_window_size",
                src.get("failure_window_size", 24),
            ),
            error_window_size=cfg_constraints.get(
                "error_window_size",
                src.get("error_window_size", 24),
            ),
            control_mode=src.get("control_mode", "balanced"),
            control_cost=src.get("control_cost", 0.0),
            refractory_remaining=src.get("refractory_remaining", 0),
            inhibit_streak=src.get("inhibit_streak", 0),
            mode_switches=src.get("mode_switches", 0),
            forced_downshift_count=src.get("forced_downshift_count", 0),
            refractory_blocks=src.get("refractory_blocks", 0),
            inhibit_cap_blocks=src.get("inhibit_cap_blocks", 0),
            recent_failure_rate=src.get("recent_failure_rate", 0.0),
            recent_failures=src.get("recent_failures", []),
            error_history_window=src.get("error_history_window", []),
            mode_counts=src.get("mode_counts", {}),
            last_metrics=src.get("last_metrics", {}),
            last_output=src.get("last_output", {}),
        )
        return inst


__all__ = ["ConflictArbitrationLayer"]
