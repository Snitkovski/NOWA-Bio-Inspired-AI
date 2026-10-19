"""
External interaction layer between environment and internal simulation.

This module provides:
- observation/action/feedback models
- delayed feedback queue
- learning hooks for drives/strategies/hypotheses
- async task scheduler for non-blocking observation and parallel simulation
"""

from __future__ import annotations

import asyncio
import inspect
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Iterable, List, Mapping, MutableMapping, Optional


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: Any, low: float, high: float) -> float:
    v = _to_float(value, low)
    if v < low:
        return low
    if v > high:
        return high
    return v


def _softmax_map(values: Mapping[str, Any], temperature: float = 1.0) -> Dict[str, float]:
    items = {str(k): _to_float(v, 0.0) for k, v in dict(values or {}).items()}
    if not items:
        return {}
    temp = max(1e-6, abs(_to_float(temperature, 1.0)))
    max_v = max(items.values())
    exps: Dict[str, float] = {}
    total = 0.0
    for key, value in items.items():
        scaled = (value - max_v) / temp
        # Clamp exponent argument for numerical stability.
        e = math.exp(max(-50.0, min(50.0, scaled)))
        exps[key] = e
        total += e
    if total <= 1e-12:
        uniform = 1.0 / float(max(1, len(items)))
        return {key: uniform for key in items}
    return {key: exps[key] / total for key in items}


@dataclass
class Hypothesis:
    """Minimal hypothesis model for Bayesian recalibration."""

    name: str
    prior: float = 0.5
    likelihood: float = 0.5
    likelihood_not_h: float = 0.5
    posterior: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def recalibrate(
        self,
        evidence_likelihood: float,
        evidence_likelihood_not_h: Optional[float] = None,
        evidence_base_rate: Optional[float] = None,
    ) -> float:
        """
        Bayesian update:
            P(H|E) = P(E|H) * P(H) / P(E)

        Supports explicit P(E|~H) and optional evidence base-rate P(E).
        """
        prior = _clamp(self.prior, 1e-6, 1.0 - 1e-6)
        like_h = _clamp(evidence_likelihood, 1e-6, 1.0 - 1e-6)

        base_rate_v = None
        if evidence_base_rate is not None:
            base_rate_v = _clamp(evidence_base_rate, 1e-6, 1.0 - 1e-6)

        if evidence_likelihood_not_h is None:
            if base_rate_v is not None:
                inferred = (base_rate_v - (like_h * prior)) / max(1e-12, 1.0 - prior)
                like_not_h = _clamp(inferred, 1e-6, 1.0 - 1e-6)
            else:
                from_meta = self.metadata.get("likelihood_not_h", self.likelihood_not_h)
                like_not_h = _clamp(from_meta, 1e-6, 1.0 - 1e-6)
        else:
            like_not_h = _clamp(evidence_likelihood_not_h, 1e-6, 1.0 - 1e-6)

        numerator = like_h * prior
        if base_rate_v is not None:
            denominator = max(1e-12, base_rate_v)
        else:
            denominator = max(1e-12, numerator + like_not_h * (1.0 - prior))

        posterior = _clamp(numerator / denominator, 0.0, 1.0)

        self.likelihood = like_h
        self.likelihood_not_h = like_not_h
        self.posterior = posterior
        self.prior = posterior
        self.metadata["last_like_h"] = like_h
        self.metadata["last_like_not_h"] = like_not_h
        if base_rate_v is not None:
            self.metadata["last_base_rate"] = base_rate_v
        return posterior


@dataclass
class Observation:
    timestamp: float
    source: str
    payload: Dict[str, Any]
    uncertainty: float

    def __post_init__(self) -> None:
        self.timestamp = _to_float(self.timestamp, time.time())
        self.source = str(self.source or "unknown")
        self.payload = dict(self.payload or {})
        self.uncertainty = _clamp(self.uncertainty, 0.0, 1.0)


@dataclass
class ExternalAction:
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Optional[Hypothesis] = None

    def __post_init__(self) -> None:
        self.action_type = str(self.action_type or "").strip()
        self.parameters = dict(self.parameters or {})


@dataclass
class Feedback:
    reward: float
    signal: Dict[str, Any] = field(default_factory=dict)
    success_probability: float = 0.0
    latency: float = 0.0

    def __post_init__(self) -> None:
        self.reward = _clamp(self.reward, -1.0, 1.0)
        self.signal = dict(self.signal or {})
        self.success_probability = _clamp(self.success_probability, 0.0, 1.0)
        self.latency = max(0.0, _to_float(self.latency, 0.0))


@dataclass
class DelayedFeedback:
    feedback: Feedback
    due_step: int
    hypothesis: Optional[Hypothesis] = None
    predicted_reward: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.due_step = max(0, int(self.due_step))
        self.predicted_reward = {
            str(key): _to_float(value, 0.0) for key, value in dict(self.predicted_reward or {}).items()
        }


class ExternalInteractionLayer:
    """
    Connects external environment signals to internal learning hooks.
    """

    def __init__(self, history_limit: int = 512) -> None:
        self.history_limit = max(1, int(history_limit))
        self.observation_history: Deque[Observation] = deque(maxlen=self.history_limit)
        self.pending_feedback: Deque[DelayedFeedback] = deque()
        self.current_step = 0
        # Strategy weights are exposed as normalized probabilities.
        self.strategy_weights: Dict[str, float] = {}
        # Internal logits for stable updates before normalization.
        self.strategy_logits: Dict[str, float] = {}
        self.strategy_temperature = 1.0
        self.strategy_weight_decay = 0.01
        self.drive_decay = 0.02
        self.drive_competition = 0.2
        self.drive_saturation = 0.75

    def ingest_observation(self, observation: Observation) -> Observation:
        obs = observation if isinstance(observation, Observation) else Observation(**dict(observation or {}))
        self.observation_history.append(obs)
        return obs

    def observe(
        self,
        source: str,
        payload: Optional[Mapping[str, Any]] = None,
        uncertainty: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> Observation:
        obs = Observation(
            timestamp=time.time() if timestamp is None else timestamp,
            source=source,
            payload=dict(payload or {}),
            uncertainty=uncertainty,
        )
        return self.ingest_observation(obs)

    def interpret_observation(self, observation: Observation) -> Dict[str, Any]:
        obs = observation if isinstance(observation, Observation) else Observation(**dict(observation or {}))
        confidence = _clamp(1.0 - obs.uncertainty, 0.0, 1.0)
        return {
            "timestamp": obs.timestamp,
            "source": obs.source,
            "payload": dict(obs.payload),
            "uncertainty": obs.uncertainty,
            "confidence": confidence,
            "probability": {
                "signal": confidence,
                "noise": obs.uncertainty,
            },
        }

    def recent_observations(self, limit: Optional[int] = None) -> List[Observation]:
        if limit is None:
            return list(self.observation_history)
        count = max(0, int(limit))
        if count == 0:
            return []
        return list(self.observation_history)[-count:]

    def build_action(
        self,
        action_type: str,
        parameters: Optional[Mapping[str, Any]] = None,
        expected_outcome: Optional[Hypothesis] = None,
    ) -> ExternalAction:
        return ExternalAction(
            action_type=action_type,
            parameters=dict(parameters or {}),
            expected_outcome=expected_outcome,
        )

    async def execute_action(self, action: ExternalAction, environment_interface: Any) -> Feedback:
        started_at = time.perf_counter()
        if environment_interface is None or not hasattr(environment_interface, "execute"):
            elapsed = time.perf_counter() - started_at
            return Feedback(
                reward=0.0,
                signal={"error": "environment_interface_missing", "action_type": action.action_type},
                success_probability=0.0,
                latency=elapsed,
            )

        execute_result = environment_interface.execute(action)
        if inspect.isawaitable(execute_result):
            execute_result = await execute_result

        feedback = self._coerce_feedback(execute_result)
        elapsed = time.perf_counter() - started_at

        merged_signal = dict(feedback.signal)
        merged_signal.setdefault("action_type", action.action_type)
        if action.expected_outcome is not None:
            merged_signal.setdefault("expected_hypothesis", action.expected_outcome.name)

        return Feedback(
            reward=feedback.reward,
            signal=merged_signal,
            success_probability=feedback.success_probability,
            latency=max(feedback.latency, elapsed),
        )

    def queue_feedback(
        self,
        feedback: Feedback,
        delay_steps: int = 0,
        current_step: Optional[int] = None,
        hypothesis: Optional[Hypothesis] = None,
        predicted_reward: Optional[Mapping[str, Any]] = None,
    ) -> DelayedFeedback:
        base_step = self.current_step if current_step is None else max(0, int(current_step))
        due_step = base_step + max(0, int(delay_steps))
        item = DelayedFeedback(
            feedback=self._coerce_feedback(feedback),
            due_step=due_step,
            hypothesis=hypothesis,
            predicted_reward={
                str(k): _to_float(v, 0.0) for k, v in dict(predicted_reward or {}).items()
            },
        )
        self.pending_feedback.append(item)
        return item

    def resolve_feedback(
        self,
        current_step: Optional[int] = None,
        max_items: Optional[int] = None,
    ) -> List[DelayedFeedback]:
        if current_step is not None:
            self.current_step = max(self.current_step, int(current_step))
        limit = None if max_items is None else max(0, int(max_items))

        resolved: List[DelayedFeedback] = []
        remaining: Deque[DelayedFeedback] = deque()
        for item in list(self.pending_feedback):
            is_due = int(item.due_step) <= int(self.current_step)
            has_capacity = limit is None or len(resolved) < limit
            if is_due and has_capacity:
                resolved.append(item)
            else:
                remaining.append(item)
        self.pending_feedback = remaining
        return resolved

    def register_strategy(self, strategy_id: str, initial_weight: float = 0.0) -> None:
        strategy = str(strategy_id)
        init = _to_float(initial_weight, 0.0)
        self.strategy_logits[strategy] = init
        self.strategy_weights = _softmax_map(
            self.strategy_logits,
            temperature=self.strategy_temperature,
        )

    def get_strategy_weights(self) -> Dict[str, float]:
        if self.strategy_logits:
            self.strategy_weights = _softmax_map(
                self.strategy_logits,
                temperature=self.strategy_temperature,
            )
            return dict(self.strategy_weights)
        return {key: _to_float(value, 0.0) for key, value in self.strategy_weights.items()}

    def _collect_drive_entries(self, drives: Optional[Any]) -> Dict[str, Dict[str, Any]]:
        entries: Dict[str, Dict[str, Any]] = {}
        if isinstance(drives, MutableMapping):
            for name in list(drives.keys()):
                key = str(name)
                target = drives.get(name)
                if hasattr(target, "intensity"):
                    current = _clamp(getattr(target, "intensity", 0.0), 0.0, 1.0)

                    def _set(v: float, target_obj=target) -> None:
                        setattr(target_obj, "intensity", _clamp(v, 0.0, 1.0))

                else:
                    current = _clamp(target, 0.0, 1.0)

                    def _set(v: float, source=drives, source_key=name) -> None:
                        source[source_key] = _clamp(v, 0.0, 1.0)

                entries[key] = {"current": current, "set": _set}
            return entries

        if drives is None:
            return entries

        for idx, drive_obj in enumerate(list(drives)):
            if not hasattr(drive_obj, "intensity"):
                continue
            key = str(getattr(drive_obj, "name", getattr(drive_obj, "id", f"drive_{idx}")))
            current = _clamp(getattr(drive_obj, "intensity", 0.0), 0.0, 1.0)

            def _set(v: float, target_obj=drive_obj) -> None:
                setattr(target_obj, "intensity", _clamp(v, 0.0, 1.0))

            entries[key] = {"current": current, "set": _set}
        return entries

    def _extract_drive_levels(self, drive_entries: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
        levels = {
            str(key): _clamp((entry or {}).get("current", 0.0), 0.0, 1.0)
            for key, entry in dict(drive_entries or {}).items()
        }
        if not levels:
            return {}
        mean_level = sum(levels.values()) / float(len(levels))
        return {
            key: _clamp((value - mean_level) + 0.5, 0.0, 1.0)
            for key, value in levels.items()
        }

    def _build_default_strategy_drive_coupling(
        self,
        strategy_keys: List[str],
        drive_levels: Mapping[str, Any],
    ) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        drive_names = [str(k) for k in dict(drive_levels or {}).keys()]
        for strategy in list(strategy_keys or []):
            key = str(strategy)
            links: Dict[str, float] = {}
            for drive in drive_names:
                if key == drive:
                    links[drive] = 1.0
                elif drive in key:
                    links[drive] = 0.35
            if links:
                out[key] = links
        return out

    def _compute_strategy_drive_signals(
        self,
        strategy_keys: List[str],
        drive_levels: Mapping[str, Any],
        strategy_drive_coupling: Optional[Mapping[str, Mapping[str, Any]]],
    ) -> Dict[str, float]:
        keys = [str(k) for k in list(strategy_keys or [])]
        if not keys:
            return {}
        levels = {str(k): _clamp(v, 0.0, 1.0) for k, v in dict(drive_levels or {}).items()}
        if not levels:
            return {key: 0.0 for key in keys}

        explicit = (
            {
                str(s): {str(d): _to_float(w, 0.0) for d, w in dict(c).items()}
                for s, c in dict(strategy_drive_coupling or {}).items()
                if isinstance(c, Mapping)
            }
            if isinstance(strategy_drive_coupling, Mapping)
            else {}
        )
        if not explicit:
            explicit = self._build_default_strategy_drive_coupling(keys, levels)

        signals: Dict[str, float] = {}
        for strategy in keys:
            couplings = dict(explicit.get(strategy, {}) or {})
            if not couplings:
                signals[strategy] = 0.0
                continue
            total_weight = 0.0
            acc = 0.0
            for drive_name, coupling_weight in couplings.items():
                if drive_name not in levels:
                    continue
                w = _to_float(coupling_weight, 0.0)
                acc += w * ((2.0 * levels[drive_name]) - 1.0)
                total_weight += abs(w)
            if total_weight <= 1e-12:
                signals[strategy] = 0.0
            else:
                signals[strategy] = _clamp(acc / total_weight, -1.0, 1.0)
        return signals

    def _collect_strategy_entries(self, strategy_source: Optional[Any]) -> Dict[str, Dict[str, Any]]:
        entries: Dict[str, Dict[str, Any]] = {}
        if isinstance(strategy_source, MutableMapping):
            for name in list(strategy_source.keys()):
                key = str(name)
                target = strategy_source.get(name)
                if hasattr(target, "weight"):
                    current_weight = _to_float(getattr(target, "weight", 0.0), 0.0)
                    current_logit = _to_float(
                        getattr(target, "logit", self.strategy_logits.get(key, current_weight)),
                        current_weight,
                    )

                    def _set_weight(v: float, target_obj=target) -> None:
                        setattr(target_obj, "weight", _to_float(v, 0.0))

                    if hasattr(target, "logit"):
                        def _set_logit(v: float, target_obj=target) -> None:
                            setattr(target_obj, "logit", _to_float(v, 0.0))
                    else:
                        _set_logit = None
                else:
                    current_weight = _to_float(target, 0.0)
                    current_logit = _to_float(self.strategy_logits.get(key, current_weight), current_weight)

                    def _set_weight(v: float, source=strategy_source, source_key=name) -> None:
                        source[source_key] = _to_float(v, 0.0)

                    _set_logit = None

                entries[key] = {
                    "weight": current_weight,
                    "logit": current_logit,
                    "set_weight": _set_weight,
                    "set_logit": _set_logit,
                }
            return entries

        if strategy_source is None:
            return entries

        for idx, strategy_obj in enumerate(list(strategy_source)):
            if not hasattr(strategy_obj, "weight"):
                continue
            key = str(getattr(strategy_obj, "name", getattr(strategy_obj, "id", f"strategy_{idx}")))
            current_weight = _to_float(getattr(strategy_obj, "weight", 0.0), 0.0)
            current_logit = _to_float(
                getattr(strategy_obj, "logit", self.strategy_logits.get(key, current_weight)),
                current_weight,
            )

            def _set_weight(v: float, target_obj=strategy_obj) -> None:
                setattr(target_obj, "weight", _to_float(v, 0.0))

            if hasattr(strategy_obj, "logit"):
                def _set_logit(v: float, target_obj=strategy_obj) -> None:
                    setattr(target_obj, "logit", _to_float(v, 0.0))
            else:
                _set_logit = None

            entries[key] = {
                "weight": current_weight,
                "logit": current_logit,
                "set_weight": _set_weight,
                "set_logit": _set_logit,
            }
        return entries

    def apply_learning_hooks(
        self,
        feedback: Feedback,
        *,
        drives: Optional[Any] = None,
        strategies: Optional[Any] = None,
        alpha: float = 0.1,
        learning_rate: float = 0.05,
        predicted_reward: Optional[Mapping[str, Any]] = None,
        hypothesis: Optional[Hypothesis] = None,
        drive_decay: Optional[float] = None,
        drive_competition: Optional[float] = None,
        drive_saturation: Optional[float] = None,
        strategy_temperature: Optional[float] = None,
        strategy_weight_decay: Optional[float] = None,
        strategy_drive_coupling: Optional[Mapping[str, Mapping[str, Any]]] = None,
        drive_policy_gain: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Learning hooks:
        - drive update with decay, saturation and competition
        - strategy logits update + softmax normalization + weight decay
          with drive->policy coupling term
        -         Bayesian hypothesis recalibration
        """
        from learning_guard import assert_learning_allowed

        if not assert_learning_allowed("ExternalInteractionLayer.apply_learning_hooks"):
            return {
                "reward_signal": 0.0,
                "drive_updates": {},
                "strategy_updates": {},
                "hypothesis_posterior": None,
                "skipped": True,
            }
        fb = self._coerce_feedback(feedback)
        reward_signal = _clamp(fb.reward, -1.0, 1.0)
        alpha_v = max(0.0, _to_float(alpha, 0.1))
        lr_v = max(0.0, _to_float(learning_rate, 0.05))
        predicted = {
            str(key): _to_float(value, 0.0) for key, value in dict(predicted_reward or {}).items()
        }
        drive_decay_v = _clamp(
            self.drive_decay if drive_decay is None else drive_decay,
            0.0,
            1.0,
        )
        drive_competition_v = _clamp(
            self.drive_competition if drive_competition is None else drive_competition,
            0.0,
            1.0,
        )
        drive_saturation_v = _clamp(
            self.drive_saturation if drive_saturation is None else drive_saturation,
            0.0,
            1.0,
        )
        strategy_temperature_v = max(
            1e-3,
            _to_float(
                self.strategy_temperature if strategy_temperature is None else strategy_temperature,
                1.0,
            ),
        )
        strategy_weight_decay_v = _clamp(
            self.strategy_weight_decay if strategy_weight_decay is None else strategy_weight_decay,
            0.0,
            1.0,
        )
        drive_policy_gain_v = _clamp(drive_policy_gain, 0.0, 2.0)
        self.strategy_temperature = strategy_temperature_v
        self.strategy_weight_decay = strategy_weight_decay_v
        self.drive_decay = drive_decay_v
        self.drive_competition = drive_competition_v
        self.drive_saturation = drive_saturation_v

        drive_updates: Dict[str, float] = {}
        drive_entries = self._collect_drive_entries(drives)
        drive_levels = self._extract_drive_levels(drive_entries)
        if drive_entries:
            raw_drive_updates: Dict[str, float] = {}
            for key, entry in drive_entries.items():
                current = _clamp(entry.get("current", 0.0), 0.0, 1.0)
                decayed = (1.0 - drive_decay_v) * current
                # Saturation gate: reduces update near extremes and keeps response in mid-range.
                edge_distance = abs((2.0 * current) - 1.0)
                saturation_gate = max(0.05, 1.0 - (drive_saturation_v * edge_distance))
                delta = alpha_v * reward_signal * saturation_gate
                raw_drive_updates[key] = _clamp(decayed + delta, 0.0, 1.0)

            competitive_drive_updates = dict(raw_drive_updates)
            if len(raw_drive_updates) > 1 and drive_competition_v > 0.0:
                total_energy = sum(raw_drive_updates.values())
                distribution = _softmax_map(raw_drive_updates, temperature=1.0)
                for key, value in raw_drive_updates.items():
                    competitive_drive_updates[key] = _clamp(
                        ((1.0 - drive_competition_v) * value)
                        + (drive_competition_v * distribution[key] * total_energy),
                        0.0,
                        1.0,
                    )

            for key, value in competitive_drive_updates.items():
                setter = drive_entries[key].get("set")
                if callable(setter):
                    setter(value)
                drive_updates[key] = value
            # Recompute centered levels after applying updates.
            for key, value in drive_updates.items():
                if key in drive_entries:
                    drive_entries[key]["current"] = value
            drive_levels = self._extract_drive_levels(drive_entries)

        strategy_updates: Dict[str, float] = {}
        strategy_drive_signal: Dict[str, float] = {}
        strategy_source = strategies if strategies is not None else self.strategy_weights
        strategy_entries = self._collect_strategy_entries(strategy_source)
        if strategy_entries:
            strategy_drive_signal = self._compute_strategy_drive_signals(
                strategy_keys=list(strategy_entries.keys()),
                drive_levels=drive_levels,
                strategy_drive_coupling=strategy_drive_coupling,
            )
            updated_logits: Dict[str, float] = {}
            for key, entry in strategy_entries.items():
                expected = _to_float(predicted.get(key, predicted.get("*", 0.0)), 0.0)
                current_logit = _to_float(entry.get("logit", 0.0), 0.0)
                td_residual = reward_signal - expected
                drive_term = drive_policy_gain_v * _to_float(strategy_drive_signal.get(key, 0.0), 0.0)
                updated_logits[key] = (
                    ((1.0 - strategy_weight_decay_v) * current_logit)
                    + (lr_v * (td_residual + drive_term))
                )
            normalized_weights = _softmax_map(
                updated_logits,
                temperature=strategy_temperature_v,
            )
            for key, norm_weight in normalized_weights.items():
                strategy_updates[key] = norm_weight
                self.strategy_weights[key] = norm_weight
                self.strategy_logits[key] = _to_float(updated_logits.get(key, 0.0), 0.0)
                set_weight = strategy_entries[key].get("set_weight")
                if callable(set_weight):
                    set_weight(norm_weight)
                set_logit = strategy_entries[key].get("set_logit")
                if callable(set_logit):
                    set_logit(self.strategy_logits[key])

        posterior = None
        if hypothesis is not None:
            signal = fb.signal if isinstance(fb.signal, Mapping) else {}
            like_not_h = signal.get("likelihood_not_h", signal.get("p_e_given_not_h"))
            base_rate = signal.get("evidence_base_rate", signal.get("p_e"))
            posterior = hypothesis.recalibrate(
                fb.success_probability,
                evidence_likelihood_not_h=like_not_h,
                evidence_base_rate=base_rate,
            )

        return {
            "reward_signal": reward_signal,
            "drive_updates": drive_updates,
            "strategy_updates": strategy_updates,
            "hypothesis_posterior": posterior,
            "drive_decay": drive_decay_v,
            "drive_competition": drive_competition_v,
            "drive_saturation": drive_saturation_v,
            "strategy_temperature": strategy_temperature_v,
            "strategy_weight_decay": strategy_weight_decay_v,
            "strategy_logits": dict(self.strategy_logits),
            "drive_policy_gain": drive_policy_gain_v,
            "strategy_drive_signal": strategy_drive_signal,
            "drive_levels": drive_levels,
        }

    def _coerce_feedback(self, value: Any) -> Feedback:
        if isinstance(value, Feedback):
            return value
        if isinstance(value, Mapping):
            signal = value.get("signal", {})
            return Feedback(
                reward=_to_float(value.get("reward", 0.0), 0.0),
                signal=dict(signal or {}) if isinstance(signal, Mapping) else {"raw_signal": signal},
                success_probability=_to_float(
                    value.get("success_probability", value.get("success", 0.0)),
                    0.0,
                ),
                latency=_to_float(value.get("latency", 0.0), 0.0),
            )
        if hasattr(value, "__dict__"):
            attrs = dict(value.__dict__)
            return self._coerce_feedback(attrs)
        return Feedback(
            reward=0.0,
            signal={"raw_feedback": value},
            success_probability=0.0,
            latency=0.0,
        )


class AsyncInteractionScheduler:
    """
    Async task scheduler for:
    - non-blocking observation polling
    - parallel internal simulation requests
    - delayed feedback resolution
    """

    def __init__(
        self,
        layer: ExternalInteractionLayer,
        environment_interface: Optional[Any] = None,
        simulation_callback: Optional[Callable[..., Any]] = None,
        max_parallel_simulations: int = 4,
    ) -> None:
        self.layer = layer
        self.environment_interface = environment_interface
        self.simulation_callback = simulation_callback
        self.max_parallel_simulations = max(1, int(max_parallel_simulations))
        self._observation_tasks: List[asyncio.Task] = []

    def set_environment_interface(self, environment_interface: Optional[Any]) -> None:
        self.environment_interface = environment_interface

    def set_simulation_callback(self, simulation_callback: Optional[Callable[..., Any]]) -> None:
        self.simulation_callback = simulation_callback

    def poll_observation_non_blocking(self) -> Optional[asyncio.Task]:
        if self.environment_interface is None or not hasattr(self.environment_interface, "observe"):
            return None
        task = asyncio.create_task(self._observe_once())
        self._observation_tasks.append(task)
        task.add_done_callback(self._cleanup_done_observation_tasks)
        return task

    async def _observe_once(self) -> Optional[Observation]:
        if self.environment_interface is None or not hasattr(self.environment_interface, "observe"):
            return None
        result = self.environment_interface.observe()
        if inspect.isawaitable(result):
            result = await result
        if result is None:
            return None
        if isinstance(result, Observation):
            return self.layer.ingest_observation(result)
        if isinstance(result, Mapping):
            return self.layer.ingest_observation(
                Observation(
                    timestamp=result.get("timestamp", time.time()),
                    source=result.get("source", "environment"),
                    payload=dict(result.get("payload", {}) or {}),
                    uncertainty=_to_float(result.get("uncertainty", 0.0), 0.0),
                )
            )
        return self.layer.ingest_observation(
            Observation(
                timestamp=time.time(),
                source="environment",
                payload={"raw_observation": result},
                uncertainty=0.5,
            )
        )

    def _cleanup_done_observation_tasks(self, _task: asyncio.Task) -> None:
        self._observation_tasks = [task for task in self._observation_tasks if not task.done()]

    async def schedule_parallel_simulations(
        self,
        simulation_requests: Iterable[Any],
    ) -> List[Any]:
        if self.simulation_callback is None:
            return []
        requests = list(simulation_requests or [])
        if not requests:
            return []

        semaphore = asyncio.Semaphore(self.max_parallel_simulations)

        async def _run_one(request: Any) -> Any:
            async with semaphore:
                out = self._invoke_simulation(request)
                if inspect.isawaitable(out):
                    out = await out
                return out

        tasks = [asyncio.create_task(_run_one(req)) for req in requests]
        return await asyncio.gather(*tasks)

    def _invoke_simulation(self, request: Any) -> Any:
        callback = self.simulation_callback
        if callback is None:
            return None
        if isinstance(request, Mapping):
            try:
                return callback(**dict(request))
            except TypeError:
                return callback(dict(request))
        return callback(request)

    def queue_feedback(
        self,
        feedback: Feedback,
        delay_steps: int = 0,
        current_step: Optional[int] = None,
        hypothesis: Optional[Hypothesis] = None,
        predicted_reward: Optional[Mapping[str, Any]] = None,
    ) -> DelayedFeedback:
        return self.layer.queue_feedback(
            feedback=feedback,
            delay_steps=delay_steps,
            current_step=current_step,
            hypothesis=hypothesis,
            predicted_reward=predicted_reward,
        )

    def resolve_feedback(
        self,
        current_step: Optional[int] = None,
        max_items: Optional[int] = None,
    ) -> List[DelayedFeedback]:
        return self.layer.resolve_feedback(current_step=current_step, max_items=max_items)


__all__ = [
    "AsyncInteractionScheduler",
    "DelayedFeedback",
    "ExternalAction",
    "ExternalInteractionLayer",
    "Feedback",
    "Hypothesis",
    "Observation",
]
