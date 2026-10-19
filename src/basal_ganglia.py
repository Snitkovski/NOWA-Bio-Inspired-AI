"""
Phase 3: Basal Ganglia / Action Gating (BG-AG).

Core rule:
- ActionSelector builds cortical pressure vector
- BasalGangliaGate.process() computes Go/NoGo competition
- ThalamicGate.select() performs final action selection
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from learning_guard import assert_learning_allowed


NO_ACTION = "NO_ACTION"


def _safe_finite_float(value: object, default: float = 0.0) -> float:
    """Convert value to float with NaN/inf protection."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(parsed):
        return float(default)
    return parsed


@dataclass
class ActionChannel:
    """
    Per-action BG channel state used for sleep learning and habit traces.
    """

    action_id: str
    go_weight: float = 0.5
    nogo_weight: float = 0.5
    habit_strength: float = 0.0

    selection_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_outcome: Optional[float] = None
    # Resting weights. Sleep decay relaxes toward these, not toward 0.
    # None means "adopt the initial weight" so old callers stay stable.
    prior_go: Optional[float] = None
    prior_nogo: Optional[float] = None
    prior_habit: Optional[float] = None

    def __setattr__(self, name, value):
        # Direct assignment of learned weights is a stable write. Construction
        # (before the channel is sealed) and host seeding under initializing()
        # still go through. Sleep opens learning_allowed() for the real writers.
        if name in ("go_weight", "nogo_weight", "habit_strength") and getattr(self, "_weights_sealed", False):
            if not assert_learning_allowed(f"ActionChannel.{name}"):
                return
        object.__setattr__(self, name, value)

    def __post_init__(self):
        object.__setattr__(self, "go_weight", max(0.0, min(1.0, float(self.go_weight))))
        object.__setattr__(self, "nogo_weight", max(0.0, min(1.0, float(self.nogo_weight))))
        object.__setattr__(self, "habit_strength", max(0.0, min(1.0, float(self.habit_strength))))
        object.__setattr__(self, "prior_go", self._prior_or_weight(self.prior_go, self.go_weight))
        object.__setattr__(self, "prior_nogo", self._prior_or_weight(self.prior_nogo, self.nogo_weight))
        object.__setattr__(self, "prior_habit", self._prior_or_weight(self.prior_habit, self.habit_strength))
        object.__setattr__(self, "_weights_sealed", True)

    @staticmethod
    def _prior_or_weight(prior: Optional[float], weight: float) -> float:
        if prior is None:
            return float(weight)
        try:
            value = float(prior)
        except (TypeError, ValueError):
            return float(weight)
        if not math.isfinite(value):
            return float(weight)
        return max(0.0, min(1.0, value))

    def update_weights(self, go_delta: float = 0.0, nogo_delta: float = 0.0, habit_delta: float = 0.0):
        if not assert_learning_allowed("ActionChannel.update_weights"):
            return
        self.go_weight = max(0.0, min(1.0, self.go_weight + float(go_delta)))
        self.nogo_weight = max(0.0, min(1.0, self.nogo_weight + float(nogo_delta)))
        self.habit_strength = max(0.0, min(1.0, self.habit_strength + float(habit_delta)))

    def record_outcome(self, outcome: float):
        self.selection_count += 1
        self.last_outcome = float(outcome)
        if outcome > 0:
            self.success_count += 1
        else:
            self.failure_count += 1

    def get_success_rate(self) -> float:
        if self.selection_count <= 0:
            return 0.5
        return self.success_count / float(self.selection_count)

    def clone(self) -> "ActionChannel":
        return ActionChannel(
            action_id=self.action_id,
            go_weight=self.go_weight,
            nogo_weight=self.nogo_weight,
            habit_strength=self.habit_strength,
            selection_count=self.selection_count,
            success_count=self.success_count,
            failure_count=self.failure_count,
            last_outcome=self.last_outcome,
            prior_go=self.prior_go,
            prior_nogo=self.prior_nogo,
            prior_habit=self.prior_habit,
        )


class ThalamicGate:
    """
    Final stochastic action gate over non-negative BG gated scores.
    """

    def __init__(self, base_temperature: float = 1.0, min_temperature: float = 0.05, ne_gain: float = 1.0):
        self.base_temperature = max(1e-6, float(base_temperature))
        self.min_temperature = max(1e-6, float(min_temperature))
        self.ne_gain = max(0.0, float(ne_gain))
        self.last_probabilities: Dict[str, float] = {}
        self.last_temperature: float = self.base_temperature

    def temperature_from_ne(self, norepinephrine_level: float, exploration_bias: float = 0.0) -> float:
        ne = max(0.0, float(norepinephrine_level))
        cer_exploration = max(0.0, min(1.5, float(exploration_bias)))
        temp = self.base_temperature * (1.0 + self.ne_gain * ne) * (1.0 + 0.8 * cer_exploration)
        return max(self.min_temperature, temp)

    def _softmax(self, scores: Dict[str, float], temperature: float) -> Dict[str, float]:
        if not scores:
            return {}
        cleaned_scores = {
            str(action_id): _safe_finite_float(score, 0.0)
            for action_id, score in dict(scores).items()
        }
        if not cleaned_scores:
            return {}

        t = max(self.min_temperature, _safe_finite_float(temperature, self.base_temperature))
        max_score = max(cleaned_scores.values())
        if not math.isfinite(max_score):
            p = 1.0 / float(len(cleaned_scores))
            return {action_id: p for action_id in cleaned_scores}

        exp_vals: Dict[str, float] = {}
        exp_sum = 0.0
        for action_id, score in cleaned_scores.items():
            exponent = (score - max_score) / t
            if not math.isfinite(exponent):
                exponent = -700.0
            exponent = max(-700.0, min(700.0, exponent))
            val = math.exp(exponent)
            if not math.isfinite(val):
                val = 0.0
            exp_vals[action_id] = val
            exp_sum += val
        if (not math.isfinite(exp_sum)) or exp_sum <= 0.0:
            p = 1.0 / float(len(cleaned_scores))
            return {action_id: p for action_id in cleaned_scores}
        return {action_id: (val / exp_sum) for action_id, val in exp_vals.items()}

    def select(
        self,
        gated_scores: Dict[str, float],
        norepinephrine_level: float,
        exploration_bias: float = 0.0,
        stability: float = 1.0,
        rng: Optional["random.Random"] = None,
    ) -> str:
        scores: Dict[str, float] = {}
        stability_v = max(0.0, min(1.0, _safe_finite_float(stability, 1.0)))
        impulse_scale = 0.55 + 0.45 * stability_v  # low stability → harder impulsive Go
        for action_id, score in dict(gated_scores or {}).items():
            safe_score = max(0.0, _safe_finite_float(score, 0.0)) * impulse_scale
            # A gated score of 0 is a veto, not a uniform-softmax candidate.
            if safe_score > 1e-12:
                scores[str(action_id)] = safe_score
        if not scores or sum(scores.values()) <= 0.0:
            self.last_probabilities = {}
            self.last_temperature = self.temperature_from_ne(
                norepinephrine_level,
                exploration_bias=exploration_bias,
            )
            return NO_ACTION

        self.last_temperature = self.temperature_from_ne(
            norepinephrine_level,
            exploration_bias=exploration_bias,
        )
        probabilities = self._softmax(scores, self.last_temperature)
        probabilities = {
            action_id: max(0.0, _safe_finite_float(probability, 0.0))
            for action_id, probability in probabilities.items()
        }
        total_prob = sum(probabilities.values())
        if (not probabilities) or (not math.isfinite(total_prob)) or total_prob <= 0.0:
            self.last_probabilities = {}
            return max(scores, key=scores.get)
        probabilities = {
            action_id: (probability / total_prob) for action_id, probability in probabilities.items()
        }
        self.last_probabilities = dict(probabilities)
        actions = list(probabilities.keys())
        weights = [probabilities[a] for a in actions]
        chooser = rng if rng is not None else random
        try:
            return chooser.choices(actions, weights=weights, k=1)[0]
        except ValueError:
            return max(scores, key=scores.get)


class BasalGangliaGate:
    """
    Basal ganglia Go/NoGo competition module.

    Mandatory interface:
    - process(...) returns gated non-negative scores per action
    - final action must be selected by ThalamicGate.select(...)
    """

    def __init__(
        self,
        temperature: float = 0.8,
        threshold: float = 0.0,
        go_gain_alpha: float = 0.9,
        habit_gain_beta: float = 0.6,
        cortisol_gain_gamma: float = 1.2,
        aversion_gain_delta: float = 0.8,
        cer_bonus_gain: float = 0.25,
        cer_bonus_cap_abs: float = 0.05,
        cer_go_pressure_cap_ratio: float = 2.5,
    ):
        self.temperature = max(0.05, float(temperature))
        self.threshold = float(threshold)
        self.go_gain_alpha = float(go_gain_alpha)
        self.habit_gain_beta = float(habit_gain_beta)
        self.cortisol_gain_gamma = float(cortisol_gain_gamma)
        self.aversion_gain_delta = float(aversion_gain_delta)
        self.cer_bonus_gain = max(0.0, float(cer_bonus_gain))
        self.cer_bonus_cap_abs = max(0.0, float(cer_bonus_cap_abs))
        self.cer_go_pressure_cap_ratio = max(1.0, float(cer_go_pressure_cap_ratio))

        self.selection_history: List[Tuple[str, float]] = []
        self.last_go: Dict[str, float] = {}
        self.last_nogo: Dict[str, float] = {}
        self.last_nets: Dict[str, float] = {}
        self.last_gated: Dict[str, float] = {}
        self.last_temperature_hint: float = self.temperature
        self.last_effective_threshold: float = self.threshold
        self.last_exploration_bias: float = 0.0
        self.last_decision_threshold_shift: float = 0.0
        self.last_habit_gain_scale: float = 1.0
        self.last_uncertainty_bonus: Dict[str, float] = {}
        self.last_go_cap: Dict[str, float] = {}
        self.last_outcome: Optional[Tuple[str, float]] = None

        # Legacy constants preserved for compatibility with existing integrations.
        self.PFC_GAIN = 2.0
        self.THREAT_NOGO_GAIN = 0.6

        self.thalamic_gate = ThalamicGate(
            base_temperature=max(0.05, self.temperature * 0.35),
            min_temperature=0.03,
            ne_gain=0.6,
        )

    def _compute_da_modifier(self, dopamine: float) -> float:
        return max(0.0, float(dopamine))

    def _compute_cort_modifier(self, cortisol: float) -> float:
        return max(0.0, float(cortisol))

    def _compute_affect_modifier(self, affect) -> float:
        valence = 0.0
        threat = 0.0
        try:
            if hasattr(affect, "axes"):
                axes = dict(getattr(affect, "axes", {}) or {})
                valence = float(axes.get("valence", 0.0))
                threat = max(0.0, float(axes.get("stress", 0.0)))
            else:
                valence = float(getattr(affect, "valence", 0.0))
                threat = max(0.0, float(getattr(affect, "threat", 0.0)))
        except Exception:
            pass
        return (0.30 * valence) - (0.70 * threat)

    def _compute_wakefulness_modifier(self, wakefulness) -> float:
        try:
            if hasattr(wakefulness, "get_cognitive_reliability"):
                return max(0.0, min(1.0, float(wakefulness.get_cognitive_reliability())))
            return max(0.0, min(1.0, 1.0 - float(getattr(wakefulness, "wakefulness", 0.0))))
        except Exception:
            return 1.0

    def _compute_temperature(self, norepinephrine: float) -> float:
        return self.thalamic_gate.temperature_from_ne(norepinephrine)

    def process(
        self,
        pressure_vector: Dict[str, float],
        dopamine_level: float,
        cortisol_level: float,
        norepinephrine_level: float,
        habit_strengths: Optional[Dict[str, float]] = None,
        aversive_signal: float = 0.0,
        channel_modulators: Optional[Dict[str, Dict[str, float]]] = None,
        exploration_bias: float = 0.0,
        decision_threshold_shift: float = 0.0,
        habit_gain_scale: float = 1.0,
        response_speed: float = 0.0,
        caution: float = 0.0,
        visit_counts: Optional[Dict[str, int]] = None,
    ) -> Dict[str, float]:
        """
        Process pressure vector through BG Go/NoGo competition.

        Optional caller floats (from Agent, not AffectiveSpace):
        - ``response_speed`` raises Go gain
        - ``caution`` raises NoGo gain
        - ``exploration_bias`` already raises thalamic temperature; Agent may
          fold ``novelty_seek`` into it.

        Formula:
        Go   = (pressure * (1 + alpha * dopamine) + beta * habit * habit_gain_scale
                + uncertainty_bonus) * go_weight
        NoGo = nogo_weight * (0.05 + 0.12 * (gamma * cortisol + delta * aversive_signal))
        Net  = Go - NoGo
        gated_score = max(Net - threshold, 0)
        Stress scales this channel's NoGo weight. It does not multiply |pressure|
        for every action. If the shared threshold zeroes every score while some
        net is still positive, those positive nets stay selectable.
        """
        cer_exploration = max(0.0, min(1.5, _safe_finite_float(exploration_bias, 0.0)))
        cer_threshold_shift = max(-0.5, min(0.8, _safe_finite_float(decision_threshold_shift, 0.0)))
        cer_habit_scale = max(0.7, min(1.6, _safe_finite_float(habit_gain_scale, 1.0)))
        go_speed = max(0.0, _safe_finite_float(response_speed, 0.0))
        nogo_caution = max(0.0, _safe_finite_float(caution, 0.0))
        self.last_temperature_hint = self.thalamic_gate.temperature_from_ne(
            _safe_finite_float(norepinephrine_level, 0.0),
            exploration_bias=cer_exploration,
        )
        self.last_exploration_bias = cer_exploration
        self.last_decision_threshold_shift = cer_threshold_shift
        self.last_habit_gain_scale = cer_habit_scale
        habits = dict(habit_strengths or {})
        mods = dict(channel_modulators or {})
        actions = set(dict(pressure_vector or {}).keys()) | set(habits.keys())

        da = max(0.0, _safe_finite_float(dopamine_level, 0.0))
        cort = max(0.0, _safe_finite_float(cortisol_level, 0.0))
        aversive = max(0.0, _safe_finite_float(aversive_signal, 0.0))

        effective_threshold = self.threshold + cer_threshold_shift
        self.last_effective_threshold = effective_threshold

        go_map: Dict[str, float] = {}
        nogo_map: Dict[str, float] = {}
        net_map: Dict[str, float] = {}
        gated: Dict[str, float] = {}
        uncertainty_bonus_map: Dict[str, float] = {}
        go_cap_map: Dict[str, float] = {}
        use_visits = visit_counts is not None
        visits = {
            str(action_id): max(0, int(_safe_finite_float(count, 0.0)))
            for action_id, count in dict(visit_counts or {}).items()
        }
        total_visits = sum(visits.values())

        for action_id in sorted(actions):
            pressure = _safe_finite_float(dict(pressure_vector or {}).get(action_id, 0.0), 0.0)
            habit = max(0.0, _safe_finite_float(habits.get(action_id, 0.0), 0.0))
            action_mod = dict(mods.get(action_id, {}) or {})
            go_weight = max(0.0, _safe_finite_float(action_mod.get("go_weight", 1.0), 1.0))
            nogo_weight = max(0.0, _safe_finite_float(action_mod.get("nogo_weight", 1.0), 1.0))

            # Optimism is larger for untried actions. Without visit counts,
            # keep the previous evidence-gated CER bonus.
            uncertainty_bonus = 0.0
            n_visits = int(visits.get(action_id, 0))
            if use_visits:
                optimism = math.sqrt(math.log(float(total_visits) + 2.0) / (float(n_visits) + 1.0))
                uncertainty_bonus_raw = optimism * self.cer_bonus_gain * max(0.35, cer_exploration)
                uncertainty_bonus = min(self.cer_bonus_cap_abs, max(0.0, uncertainty_bonus_raw))
            elif abs(pressure) > 1e-12 or habit > 1e-12:
                uncertainty_bonus_raw = cer_exploration * max(0.0, 0.25 - abs(pressure)) * self.cer_bonus_gain
                uncertainty_bonus = min(self.cer_bonus_cap_abs, uncertainty_bonus_raw)

            habit_term = self.habit_gain_beta * cer_habit_scale * habit
            go_signal_raw = (
                pressure * (1.0 + self.go_gain_alpha * da)
                + habit_term
                + uncertainty_bonus
            ) * go_weight
            # Hard upper-bound for CER contribution:
            # final Go cannot run away relative to base pressure envelope.
            pressure_envelope = max(1e-6, abs(pressure) * (1.0 + self.go_gain_alpha * da))
            go_cap = (
                self.cer_go_pressure_cap_ratio * pressure_envelope
                + habit_term
                + self.cer_bonus_cap_abs
            ) * go_weight
            if not math.isfinite(go_signal_raw):
                go_signal_raw = 0.0
            if (not math.isfinite(go_cap)) or go_cap < 0.0:
                go_cap = 0.0
            go_signal = min(go_signal_raw, go_cap) * (1.0 + 0.25 * go_speed)
            # NoGo is this channel's learned inhibition. Cortisol and stress
            # scale that weight; they do not multiply |pressure| for every
            # action, which used to drive every net negative at once.
            stress_drive = (self.cortisol_gain_gamma * cort) + (self.aversion_gain_delta * aversive)
            nogo_signal = nogo_weight * (0.05 + 0.12 * stress_drive)
            nogo_signal *= (1.0 + 0.35 * nogo_caution)
            if not math.isfinite(go_signal):
                go_signal = 0.0
            if (not math.isfinite(nogo_signal)) or nogo_signal < 0.0:
                nogo_signal = 0.0
            net_signal = go_signal - nogo_signal
            gated_score = max(net_signal - effective_threshold, 0.0)
            if not math.isfinite(net_signal):
                net_signal = 0.0
            if (not math.isfinite(gated_score)) or gated_score < 0.0:
                gated_score = 0.0
            # An untried action stays available. This is not a veto bypass:
            # once the action has been visited, a non-positive gate stands.
            if use_visits and n_visits <= 0 and uncertainty_bonus > 0.0:
                gated_score = max(gated_score, uncertainty_bonus)

            go_map[action_id] = go_signal
            nogo_map[action_id] = nogo_signal
            net_map[action_id] = net_signal
            gated[action_id] = gated_score
            uncertainty_bonus_map[action_id] = uncertainty_bonus
            go_cap_map[action_id] = go_cap

        # A shared threshold may rise under stress, but it must not silence
        # every channel while at least one action still has a positive surplus.
        if gated and all(score <= 1e-12 for score in gated.values()):
            positive_nets = {
                action_id: net
                for action_id, net in net_map.items()
                if math.isfinite(net) and net > 1e-8
            }
            if positive_nets:
                for action_id, net in positive_nets.items():
                    gated[action_id] = net

        self.last_go = go_map
        self.last_nogo = nogo_map
        self.last_nets = net_map
        self.last_gated = gated
        self.last_uncertainty_bonus = uncertainty_bonus_map
        self.last_go_cap = go_cap_map
        return gated

    def choose(
        self,
        channels: List[ActionChannel],
        affect,
        neuromodulators,
        wakefulness,
        pfc_pressure: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Backward-compatible helper for channel-based selection.

        Main pipeline users should call:
        process(...) -> ThalamicGate.select(...)
        """
        if not channels:
            raise ValueError("No action channels provided")

        pfc = dict(pfc_pressure or {})
        wake_mod = self._compute_wakefulness_modifier(wakefulness)
        threat = 0.0
        try:
            if hasattr(affect, "axes"):
                threat = max(0.0, float((getattr(affect, "axes", {}) or {}).get("stress", 0.0)))
            else:
                threat = max(0.0, float(getattr(affect, "threat", 0.0)))
        except Exception:
            threat = 0.0
        aversive_signal = threat

        pressure_vector: Dict[str, float] = {}
        habit_strengths: Dict[str, float] = {}
        channel_modulators: Dict[str, Dict[str, float]] = {}

        for channel in channels:
            pressure = float(channel.go_weight) - 0.40 * float(channel.nogo_weight)
            if channel.action_id in pfc:
                clamped_pfc = max(-0.2, min(0.2, float(pfc[channel.action_id])))
                pressure += clamped_pfc * wake_mod * self.PFC_GAIN
            pressure_vector[channel.action_id] = pressure
            habit_strengths[channel.action_id] = float(channel.habit_strength)
            channel_modulators[channel.action_id] = {
                "go_weight": float(channel.go_weight),
                "nogo_weight": float(channel.nogo_weight),
            }

        gated = self.process(
            pressure_vector=pressure_vector,
            dopamine_level=float(getattr(neuromodulators, "dopamine", 0.0)),
            cortisol_level=float(getattr(neuromodulators, "cortisol", 0.0)),
            norepinephrine_level=float(getattr(neuromodulators, "norepinephrine", 0.0)),
            habit_strengths=habit_strengths,
            aversive_signal=aversive_signal,
            channel_modulators=channel_modulators,
        )

        selected_action_id = self.thalamic_gate.select(
            gated_scores=gated,
            norepinephrine_level=float(getattr(neuromodulators, "norepinephrine", 0.0)),
            exploration_bias=0.0,
        )

        self.selection_history.append((selected_action_id, self.last_nets.get(selected_action_id, 0.0)))
        return selected_action_id

    def record_outcome(self, action_id: str, outcome: float):
        self.last_outcome = (str(action_id), float(outcome))

    def reset_history(self):
        self.selection_history = []

    def get_action_stats(self, action_id: str) -> Dict:
        selections = [1 for aid, _ in self.selection_history if aid == action_id]
        count = len(selections)
        return {
            "action_id": action_id,
            "selections": count,
            "frequency": count / len(self.selection_history) if self.selection_history else 0.0,
        }


class BasalGangliaLearning:
    """
    BG sleep-learning module.
    """

    def __init__(self, learning_rate: float = 0.05):
        self.learning_rate = max(0.01, min(0.2, float(learning_rate)))

    def apply_sleep_learning(
        self,
        channels: List[ActionChannel],
        memories: Dict[str, List[Tuple[str, float]]],
        neuromodulators,
        forget_rate: float = 0.01,
    ) -> List[ActionChannel]:
        """Replay BG memories into a clone.

        This does not open the learning guard. The sleep path
        (``SleepManager`` / a host sleep that enters ``learning_allowed``)
        must already be open. A waking call leaves the clone unchanged
        (or raises when ``NOWA_STRICT_LEARNING`` is set).
        """
        return self._apply_sleep_learning_unlocked(
            channels,
            memories,
            neuromodulators,
            forget_rate=forget_rate,
        )

    def _apply_sleep_learning_unlocked(
        self,
        channels: List[ActionChannel],
        memories: Dict[str, List[Tuple[str, float]]],
        neuromodulators,
        forget_rate: float = 0.01,
    ) -> List[ActionChannel]:
        updated_channels = [ch.clone() for ch in channels]

        for channel in updated_channels:
            if channel.action_id not in memories:
                channel.update_weights(
                    go_delta=-channel.go_weight * forget_rate,
                    nogo_delta=-channel.nogo_weight * forget_rate,
                    habit_delta=-channel.habit_strength * forget_rate * 0.1,
                )
                continue

            action_memories = memories[channel.action_id]
            for outcome, da, cort, serotonin in action_memories:
                if outcome > 0:
                    go_delta = da * self.learning_rate
                    nogo_delta = -da * self.learning_rate * 0.5
                    habit_delta = serotonin * self.learning_rate * 0.1
                else:
                    go_delta = -cort * self.learning_rate
                    nogo_delta = cort * self.learning_rate * 0.5
                    habit_delta = -serotonin * self.learning_rate * 0.05

                channel.update_weights(go_delta=go_delta, nogo_delta=nogo_delta, habit_delta=habit_delta)

            channel.update_weights(
                go_delta=-channel.go_weight * forget_rate,
                nogo_delta=-channel.nogo_weight * forget_rate,
                habit_delta=-channel.habit_strength * forget_rate * 0.1,
            )

        return updated_channels

    def consolidate_habits(self, channels: List[ActionChannel], serotonin: float) -> List[ActionChannel]:
        if not assert_learning_allowed("BasalGangliaLearning.consolidate_habits"):
            return [ch.clone() for ch in channels]
        updated = [ch.clone() for ch in channels]
        for channel in updated:
            if channel.selection_count > 0:
                success_rate = channel.get_success_rate()
                effective_success = max(0.1, success_rate)
                repetition_factor = math.log(channel.selection_count + 1) * 0.01
                serotonin_effect = float(serotonin) * 0.05
                habit_delta = effective_success * (repetition_factor + serotonin_effect)
                channel.habit_strength = max(0.0, min(1.0, channel.habit_strength + habit_delta))
        return updated
