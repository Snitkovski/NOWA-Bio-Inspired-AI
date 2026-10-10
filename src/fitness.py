"""Multi-objective fitness evaluation utilities for NOWA agents."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

FITNESS_VERSION = "1.0"

CRITERIA_ORDER = [
    "longevity",
    "affective_range",
    "prediction_skill",
    "stress_resilience",
    "behavioral_diversity",
    "learning_efficiency",
    "memory_quality",
]

DEFAULT_WEIGHTS = {criterion: 1.0 for criterion in CRITERIA_ORDER}

AFFECTIVE_RANGE_NORM = 0.5
LEARNING_EFFICIENCY_NORM = 3.0
MEMORY_QUALITY_SAMPLE_LIMIT = 128


def _clamp_01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _std(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return math.sqrt(max(0.0, variance))


def _mapping_value(mapping: Any, key: str, default: Any = None) -> Any:
    if isinstance(mapping, Mapping):
        return mapping.get(key, default)
    return default


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except Exception:
        return []


@dataclass(frozen=True)
class FitnessVector:
    longevity: float
    affective_range: float
    prediction_skill: float
    stress_resilience: float
    behavioral_diversity: float
    learning_efficiency: float
    memory_quality: float
    agent_id: str
    generation: int
    evaluation_step: int

    def __post_init__(self) -> None:
        for criterion in CRITERIA_ORDER:
            object.__setattr__(self, criterion, _clamp_01(getattr(self, criterion, 0.0)))
        object.__setattr__(self, "agent_id", str(getattr(self, "agent_id", "") or ""))
        object.__setattr__(self, "generation", max(0, _safe_int(getattr(self, "generation", 0), 0)))
        object.__setattr__(
            self,
            "evaluation_step",
            max(0, _safe_int(getattr(self, "evaluation_step", 0), 0)),
        )


@dataclass(frozen=True)
class ParetoRank:
    agent_id: str
    rank: int
    crowding_distance: float
    fitness: FitnessVector


@dataclass
class FitnessEvaluator:
    weights: Dict[str, float] | None = None

    def __post_init__(self) -> None:
        raw_weights: Dict[str, float] = dict(DEFAULT_WEIGHTS)
        provided = self.weights if isinstance(self.weights, Mapping) else {}

        for criterion in CRITERIA_ORDER:
            if criterion in provided:
                candidate = _safe_float(provided.get(criterion), 0.0)
                raw_weights[criterion] = max(0.0, candidate or 0.0)

        total_weight = sum(raw_weights.values())
        if total_weight <= 0.0:
            normalized = {criterion: 1.0 / len(CRITERIA_ORDER) for criterion in CRITERIA_ORDER}
        else:
            normalized = {
                criterion: raw_weights[criterion] / total_weight for criterion in CRITERIA_ORDER
            }
        self.weights = normalized

    def evaluate(self, agent: Any) -> FitnessVector:
        try:
            lived_steps = max(0, _safe_int(getattr(agent, "lived_steps", 0), 0))
        except Exception:
            lived_steps = 0

        try:
            longevity = self._evaluate_longevity(agent, lived_steps)
        except Exception:
            longevity = 0.0

        try:
            affective_range = self._evaluate_affective_range(agent)
        except Exception:
            affective_range = 0.0

        try:
            prediction_skill = self._evaluate_prediction_skill(agent)
        except Exception:
            prediction_skill = 0.0

        try:
            stress_resilience = self._evaluate_stress_resilience(agent)
        except Exception:
            stress_resilience = 0.0

        try:
            behavioral_diversity = self._evaluate_behavioral_diversity(agent)
        except Exception:
            behavioral_diversity = 0.0

        try:
            learning_efficiency = self._evaluate_learning_efficiency(agent)
        except Exception:
            learning_efficiency = 0.0

        try:
            memory_quality = self._evaluate_memory_quality(agent)
        except Exception:
            memory_quality = 0.0

        try:
            agent_id = str(getattr(agent, "agent_id", "") or "")
        except Exception:
            agent_id = ""

        try:
            genome = getattr(agent, "genome", None)
            generation = max(0, _safe_int(getattr(genome, "generation", 0), 0))
        except Exception:
            generation = 0

        return FitnessVector(
            longevity=longevity,
            affective_range=affective_range,
            prediction_skill=prediction_skill,
            stress_resilience=stress_resilience,
            behavioral_diversity=behavioral_diversity,
            learning_efficiency=learning_efficiency,
            memory_quality=memory_quality,
            agent_id=agent_id,
            generation=generation,
            evaluation_step=lived_steps,
        )

    def evaluate_population(self, agents: List[Any]) -> List[FitnessVector]:
        return [self.evaluate(agent) for agent in list(agents or [])]

    def pareto_rank(self, fitness_vectors: List[FitnessVector]) -> List[ParetoRank]:
        vectors = list(fitness_vectors or [])
        if not vectors:
            return []
        if len(vectors) == 1:
            vector = vectors[0]
            return [
                ParetoRank(
                    agent_id=vector.agent_id,
                    rank=1,
                    crowding_distance=float("inf"),
                    fitness=vector,
                )
            ]

        size = len(vectors)
        domination_count = [0 for _ in range(size)]
        dominates_set: List[set[int]] = [set() for _ in range(size)]

        for left in range(size):
            for right in range(left + 1, size):
                left_dominates = self.dominates(vectors[left], vectors[right])
                right_dominates = self.dominates(vectors[right], vectors[left])

                if left_dominates and not right_dominates:
                    dominates_set[left].add(right)
                    domination_count[right] += 1
                elif right_dominates and not left_dominates:
                    dominates_set[right].add(left)
                    domination_count[left] += 1

        current_front = [idx for idx, count in enumerate(domination_count) if count == 0]
        current_front.sort()
        unresolved = set(range(size))
        rank_number = 1
        ranked_with_index: List[tuple[int, ParetoRank]] = []

        while current_front:
            crowding = self._crowding_distances(vectors, current_front)

            for idx in current_front:
                ranked_with_index.append(
                    (
                        idx,
                        ParetoRank(
                            agent_id=vectors[idx].agent_id,
                            rank=rank_number,
                            crowding_distance=float(crowding.get(idx, 0.0)),
                            fitness=vectors[idx],
                        ),
                    )
                )

            next_candidates: List[int] = []
            for idx in current_front:
                unresolved.discard(idx)
                for dominated_idx in sorted(dominates_set[idx]):
                    domination_count[dominated_idx] -= 1
                    if domination_count[dominated_idx] == 0:
                        next_candidates.append(dominated_idx)

            seen: set[int] = set()
            current_front = []
            for idx in sorted(next_candidates):
                if idx in unresolved and idx not in seen:
                    seen.add(idx)
                    current_front.append(idx)
            rank_number += 1

        ranked_with_index.sort(
            key=lambda item: (
                item[1].rank,
                self._crowding_sort_key(item[1].crowding_distance),
                item[0],
            )
        )
        return [item[1] for item in ranked_with_index]

    def scalar_score(self, fitness: FitnessVector) -> float:
        numerator = 0.0
        denominator = 0.0
        for criterion in CRITERIA_ORDER:
            weight = max(0.0, _safe_float(self.weights.get(criterion), 0.0) or 0.0)
            value = _clamp_01(getattr(fitness, criterion, 0.0))
            numerator += weight * value
            denominator += weight
        if denominator <= 0.0:
            return 0.0
        return _clamp_01(numerator / denominator)

    def dominates(self, a: FitnessVector, b: FitnessVector) -> bool:
        all_not_worse = True
        any_better = False

        for criterion in CRITERIA_ORDER:
            value_a = _clamp_01(getattr(a, criterion, 0.0))
            value_b = _clamp_01(getattr(b, criterion, 0.0))
            if value_a < value_b:
                all_not_worse = False
                break
            if value_a > value_b:
                any_better = True

        return all_not_worse and any_better

    def criteria_names(self) -> List[str]:
        return list(CRITERIA_ORDER)

    def fitness_to_dict(self, fitness: FitnessVector) -> dict:
        data = {criterion: _clamp_01(getattr(fitness, criterion, 0.0)) for criterion in CRITERIA_ORDER}
        data["agent_id"] = str(getattr(fitness, "agent_id", "") or "")
        data["generation"] = max(0, _safe_int(getattr(fitness, "generation", 0), 0))
        data["evaluation_step"] = max(0, _safe_int(getattr(fitness, "evaluation_step", 0), 0))
        return data

    def fitness_from_dict(self, data: dict) -> FitnessVector:
        raw = data if isinstance(data, Mapping) else {}
        return FitnessVector(
            longevity=_clamp_01(_mapping_value(raw, "longevity", 0.0)),
            affective_range=_clamp_01(_mapping_value(raw, "affective_range", 0.0)),
            prediction_skill=_clamp_01(_mapping_value(raw, "prediction_skill", 0.0)),
            stress_resilience=_clamp_01(_mapping_value(raw, "stress_resilience", 0.0)),
            behavioral_diversity=_clamp_01(_mapping_value(raw, "behavioral_diversity", 0.0)),
            learning_efficiency=_clamp_01(_mapping_value(raw, "learning_efficiency", 0.0)),
            memory_quality=_clamp_01(_mapping_value(raw, "memory_quality", 0.0)),
            agent_id=str(_mapping_value(raw, "agent_id", "") or ""),
            generation=max(0, _safe_int(_mapping_value(raw, "generation", 0), 0)),
            evaluation_step=max(0, _safe_int(_mapping_value(raw, "evaluation_step", 0), 0)),
        )

    def _evaluate_longevity(self, agent: Any, lived_steps: int) -> float:
        expected = _safe_float(getattr(agent, "expected_lifetime_steps", 0.0), 0.0) or 0.0
        if expected <= 0.0:
            return 0.0
        return _clamp_01(float(lived_steps) / expected)

    def _evaluate_affective_range(self, agent: Any) -> float:
        history = getattr(agent, "affective_history", None)
        if not isinstance(history, list):
            return 0.0
        if not history:
            return 0.0

        axis_to_values: Dict[str, List[float]] = {}
        for snapshot in history:
            if not isinstance(snapshot, Mapping):
                continue
            for axis_name, axis_value in snapshot.items():
                value = _safe_float(axis_value, None)
                if value is None:
                    continue
                axis_to_values.setdefault(str(axis_name), []).append(value)

        if not axis_to_values:
            return 0.0

        per_axis_std = [_std(values) for values in axis_to_values.values()]
        if not per_axis_std:
            return 0.0
        if AFFECTIVE_RANGE_NORM <= 0.0:
            return 0.0
        return _clamp_01(_mean(per_axis_std) / AFFECTIVE_RANGE_NORM)

    def _evaluate_prediction_skill(self, agent: Any) -> float:
        td_errors: List[float] = []
        td_history = getattr(agent, "td_error_history", None)
        if isinstance(td_history, list):
            for value in td_history:
                numeric = _safe_float(value, None)
                if numeric is not None:
                    td_errors.append(abs(numeric))

        if not td_errors:
            snapshot = self._value_snapshot(agent)
            current_td = _safe_float(_mapping_value(snapshot, "last_td_error", None), None)
            if current_td is not None:
                td_errors.append(abs(current_td))

        if not td_errors:
            return 0.0
        return _clamp_01(1.0 - _mean(td_errors))

    def _evaluate_stress_resilience(self, agent: Any) -> float:
        cortisol_samples: List[float] = []
        cortisol_history = getattr(agent, "cortisol_history", None)
        if isinstance(cortisol_history, list):
            for value in cortisol_history:
                numeric = _safe_float(value, None)
                if numeric is not None:
                    cortisol_samples.append(_clamp_01(numeric))

        if not cortisol_samples:
            neuromodulators = getattr(agent, "neuromodulators", None)
            current = _safe_float(getattr(neuromodulators, "cortisol", None), None)
            if current is not None:
                cortisol_samples.append(_clamp_01(current))

        if not cortisol_samples:
            return 0.0
        return _clamp_01(1.0 - _mean(cortisol_samples))

    def _evaluate_behavioral_diversity(self, agent: Any) -> float:
        channels = getattr(agent, "bg_action_channels", None)
        if not isinstance(channels, Mapping):
            return 0.0

        counts: List[float] = []
        for channel in channels.values():
            if isinstance(channel, Mapping):
                raw_count = _mapping_value(channel, "selection_count", 0.0)
            else:
                raw_count = getattr(channel, "selection_count", 0.0)
            numeric = _safe_float(raw_count, 0.0) or 0.0
            counts.append(max(0.0, numeric))

        if not counts:
            return 0.0

        num_actions = len(counts)
        total = sum(counts)
        if num_actions <= 1 or total <= 0.0:
            return 0.0

        entropy = 0.0
        for count in counts:
            if count <= 0.0:
                continue
            probability = count / total
            entropy -= probability * math.log(probability)

        denominator = math.log(num_actions)
        if denominator <= 0.0:
            return 0.0
        return _clamp_01(entropy / denominator)

    def _evaluate_learning_efficiency(self, agent: Any) -> float:
        snapshot = self._value_snapshot(agent)
        if not snapshot:
            return 0.0

        online = _safe_float(_mapping_value(snapshot, "online_update_count", 0.0), 0.0) or 0.0
        sleep = _safe_float(_mapping_value(snapshot, "sleep_update_count", 0.0), 0.0) or 0.0
        online = max(0.0, online)
        sleep = max(0.0, sleep)

        if LEARNING_EFFICIENCY_NORM <= 0.0:
            return 0.0
        ratio = sleep / (online + 1.0)
        return _clamp_01(ratio / LEARNING_EFFICIENCY_NORM)

    def _evaluate_memory_quality(self, agent: Any) -> float:
        hippocampus = getattr(agent, "hippocampus", None)
        experiences = _as_list(getattr(hippocampus, "experiences", []))
        if not experiences:
            return 0.0

        sampled = experiences[-MEMORY_QUALITY_SAMPLE_LIMIT:]
        weights: List[float] = []
        for experience in sampled:
            if isinstance(experience, Mapping):
                raw_weight = _mapping_value(experience, "consolidation_weight", None)
            else:
                raw_weight = getattr(experience, "consolidation_weight", None)
            numeric = _safe_float(raw_weight, None)
            if numeric is not None:
                weights.append(_clamp_01(numeric))

        if not weights:
            return 0.0
        return _clamp_01(_mean(weights))

    def _value_snapshot(self, agent: Any) -> Mapping[str, Any]:
        value_layer = getattr(agent, "value_layer", None)
        if value_layer is None:
            return {}
        snapshot_method = getattr(value_layer, "snapshot", None)
        if callable(snapshot_method):
            snapshot = snapshot_method()
            if isinstance(snapshot, Mapping):
                return snapshot
        return {}

    def _crowding_distances(
        self,
        vectors: Sequence[FitnessVector],
        front: Sequence[int],
    ) -> Dict[int, float]:
        distances: Dict[int, float] = {idx: 0.0 for idx in front}
        if len(front) == 1:
            distances[front[0]] = float("inf")
            return distances

        for criterion in CRITERIA_ORDER:
            ordered = sorted(
                front,
                key=lambda idx: (_clamp_01(getattr(vectors[idx], criterion, 0.0)), idx),
            )
            min_idx = ordered[0]
            max_idx = ordered[-1]
            min_value = _clamp_01(getattr(vectors[min_idx], criterion, 0.0))
            max_value = _clamp_01(getattr(vectors[max_idx], criterion, 0.0))
            span = max_value - min_value

            if span <= 0.0:
                continue

            distances[min_idx] = float("inf")
            distances[max_idx] = float("inf")

            for pos in range(1, len(ordered) - 1):
                idx = ordered[pos]
                if math.isinf(distances[idx]):
                    continue
                prev_value = _clamp_01(getattr(vectors[ordered[pos - 1]], criterion, 0.0))
                next_value = _clamp_01(getattr(vectors[ordered[pos + 1]], criterion, 0.0))
                distances[idx] += (next_value - prev_value) / span

        return distances

    @staticmethod
    def _crowding_sort_key(distance: float) -> float:
        if math.isinf(distance) and distance > 0.0:
            return float("-inf")
        return -float(distance)


__all__ = [
    "AFFECTIVE_RANGE_NORM",
    "CRITERIA_ORDER",
    "DEFAULT_WEIGHTS",
    "FITNESS_VERSION",
    "LEARNING_EFFICIENCY_NORM",
    "MEMORY_QUALITY_SAMPLE_LIMIT",
    "FitnessEvaluator",
    "FitnessVector",
    "ParetoRank",
]
