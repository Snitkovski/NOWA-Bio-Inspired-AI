"""
Action Selector - Non-learnable mechanism for action selection.

Does NOT learn or have optimizable weights.
Makes decisions based on:
1. Hippocampal experiences (recent, active)
2. Cortical patterns (consolidated, stable)
3. Pressure calculation and confidence
"""

import math
from typing import Any, Dict, List, Mapping, Optional

from simulation_utility import DEFAULT_DRIVE_UTILITY_PROFILES, compute_drive_utility_components


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = lo
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class ActionSelector:
    """
    Selects action based on experience and patterns.
    
    NOT a learning mechanism. Behavior emerges from:
    - Recent experience activation (hippocampus)
    - Consolidated patterns (cortex)
    - Conflict resolution via confidence threshold

    Internal simulation support:
    - choose(...) acts as proposer only
    - evaluate(hypothetical_state) scores hypothetical variants
    """

    def __init__(
        self,
        actions: List[str],
        confidence_threshold: float = 0.7,
        action_metadata: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ):
        """
        Initialize selector with available actions

        Args:
            actions: List of possible actions
            confidence_threshold: If max_pressure/total_pressure > threshold,
                                 choose deterministically. Else probabilistically.
            action_metadata: Optional mapping
                action -> {"predicted_effect": {"axes": {...}, "drives": {...}, "active_drive_delta": float}}
        """
        self.actions = list(actions)
        self.confidence_threshold = confidence_threshold
        self.action_metadata: Dict[str, Dict[str, Any]] = {}
        for action in self.actions:
            self.action_metadata[action] = self._default_action_metadata(action)
        if action_metadata:
            for action, meta in dict(action_metadata).items():
                self.set_action_metadata(str(action), dict(meta or {}))

        # Drive-aware utility profiles used by evaluate().
        self.drive_utility_profiles: Dict[str, Dict[str, float]] = {
            name: dict(weights)
            for name, weights in DEFAULT_DRIVE_UTILITY_PROFILES.items()
        }

    def _default_action_metadata(self, action_name: str) -> Dict[str, Any]:
        return {
            "action": str(action_name),
            "predicted_effect": {
                "axes": {},
                "drives": {},
                # Generic expectation: any purposeful action slightly relieves active deficit.
                "active_drive_delta": -0.08,
            },
            # Semantic Action Consolidation (sleep-only) state.
            "expected_effect_mean": 0.0,
            "expected_effect_variance": 0.25,
            "success_alpha": 1.0,
            "success_beta": 1.0,
            "risk_estimate": 0.125,
            "semantic_confidence": 0.0,
            "stability_score": 0.0,
            # EDPC <-> SAC synchronization fields.
            "confidence": 0.0,
            "stability": 0.0,
            "td_mean": 0.0,
            "td_variance": 0.0,
            "consolidated": False,
            "consolidation_flag": False,
            "conflict_flag": False,
            "last_state_key": "",
        }

    def set_action_metadata(self, action_name: str, metadata: Mapping[str, Any]) -> None:
        action = str(action_name)
        merged = dict(self._default_action_metadata(action))
        incoming = dict(metadata or {})
        predicted_in = dict(incoming.get("predicted_effect", {}) or {})
        merged.update({k: v for k, v in incoming.items() if k != "predicted_effect"})

        predicted = dict(merged.get("predicted_effect", {}) or {})
        predicted.update(predicted_in)
        predicted["axes"] = dict(predicted.get("axes", {}) or {})
        predicted["drives"] = dict(predicted.get("drives", {}) or {})
        predicted["active_drive_delta"] = float(predicted.get("active_drive_delta", -0.08))
        merged["predicted_effect"] = predicted
        merged["expected_effect_mean"] = float(merged.get("expected_effect_mean", 0.0))
        merged["expected_effect_variance"] = max(0.0, float(merged.get("expected_effect_variance", 0.25)))
        merged["success_alpha"] = max(1e-6, float(merged.get("success_alpha", 1.0)))
        merged["success_beta"] = max(1e-6, float(merged.get("success_beta", 1.0)))
        merged["risk_estimate"] = _clamp(merged.get("risk_estimate", 0.125), 0.0, 1.0)
        merged["semantic_confidence"] = _clamp(merged.get("semantic_confidence", 0.0), 0.0, 1.0)
        self.action_metadata[action] = merged

    def get_action_metadata(self, action_name: str) -> Dict[str, Any]:
        action = str(action_name)
        if action in self.action_metadata:
            base = self.action_metadata[action]
            predicted_effect = base.get("predicted_effect", {}) or {}
            stability_score = _clamp(base.get("stability_score", base.get("stability", 0.0)), 0.0, 1.0)
            confidence_score = _clamp(base.get("confidence", base.get("semantic_confidence", 0.0)), 0.0, 1.0)
            consolidated_flag = bool(base.get("consolidated", base.get("consolidation_flag", False)))
            return {
                "action": str(base.get("action", action)),
                "predicted_effect": {
                    "axes": dict(predicted_effect.get("axes", {}) or {}),
                    "drives": dict(predicted_effect.get("drives", {}) or {}),
                    "active_drive_delta": float(predicted_effect.get("active_drive_delta", -0.08)),
                },
                "expected_effect_mean": float(base.get("expected_effect_mean", 0.0)),
                "expected_effect_variance": max(0.0, float(base.get("expected_effect_variance", 0.25))),
                "success_alpha": max(1e-6, float(base.get("success_alpha", 1.0))),
                "success_beta": max(1e-6, float(base.get("success_beta", 1.0))),
                "risk_estimate": _clamp(base.get("risk_estimate", 0.125), 0.0, 1.0),
                "semantic_confidence": _clamp(base.get("semantic_confidence", 0.0), 0.0, 1.0),
                "stability_score": stability_score,
                "confidence": confidence_score,
                "stability": _clamp(base.get("stability", stability_score), 0.0, 1.0),
                "td_mean": float(base.get("td_mean", 0.0)),
                "td_variance": max(0.0, float(base.get("td_variance", 0.0))),
                "consolidated": bool(consolidated_flag),
                "consolidation_flag": bool(base.get("consolidation_flag", consolidated_flag)),
                "conflict_flag": bool(base.get("conflict_flag", False)),
                "last_state_key": str(base.get("last_state_key", "")),
            }
        return self._default_action_metadata(action)

    def get_action_effect(self, action_name: str) -> Dict[str, Any]:
        meta = self.get_action_metadata(action_name)
        return dict(meta.get("predicted_effect", {}) or {})

    def compute_pressures(
        self,
        hippocampal_exps,
        cortical_patterns,
        intent_pressure=None,
        affect_modifier: float = 1.0,
        temporal_chains_bias: dict = None,
        prediction_pressure: dict = None,
        verbose: bool = False,
    ) -> Dict[str, float]:
        """
        Build cortical competition pressure vector for actions.

        This method does NOT choose an action; it only returns pressure values.
        """
        pressure = {a: 0.0 for a in self.actions}

        # 1. Hippocampal pressure: mean signed outcome, not raw frequency.
        #    Repeating a punished action must not outgrow a rare rewarded one.
        signed = self._signed_recall_means(hippocampal_exps)
        for action_name, signed_mean in signed.items():
            if action_name in pressure:
                pressure[action_name] += _clamp(signed_mean, -1.0, 1.0)

        # 2. Cortical pressure (stable patterns), clipped per pattern.
        for pattern in cortical_patterns:
            pattern_weight = _clamp(getattr(pattern, "strength", 0.0), 0.0, 1.0) * 0.3
            for event in pattern.signature:
                if event.startswith("action:"):
                    action = event.split(":", 1)[1]
                    if action in pressure:
                        pressure[action] += pattern_weight

        # 3. Intent pressure. tanh keeps a large legacy count on the same
        #    scale as go/nogo weights in [0, 1].
        if intent_pressure:
            for intent_type, intent_p in intent_pressure.items():
                if intent_type in pressure:
                    try:
                        # /3 keeps a clearly dominant habit above the selector
                        # confidence threshold while the result stays in (-1, 1).
                        pressure[intent_type] += math.tanh(float(intent_p) / 3.0)
                    except (TypeError, ValueError):
                        continue

        # 4. Temporal chains advisory pressure
        if temporal_chains_bias:
            for action_name, chain_bias in temporal_chains_bias.items():
                if action_name in pressure:
                    try:
                        pressure[action_name] += _clamp(float(chain_bias), -1.0, 1.0) * 0.6
                    except (TypeError, ValueError):
                        continue

        # 5. Prediction-layer advisory pressure
        if prediction_pressure:
            try:
                for action_name, pred_p in prediction_pressure.items():
                    if action_name in pressure:
                        pressure[action_name] += _clamp(float(pred_p), -1.0, 1.0) * 0.8
            except Exception:
                pass

        # 6. Strategy policy modulation (if external layer provided strategy weights).
        # Expected format in action_metadata[action]["strategy_weight"] as probability [0..1].
        # Convert to centered bias relative to uniform prior so total pressure remains balanced.
        try:
            if self.actions:
                baseline = 1.0 / float(len(self.actions))
                for action_name in self.actions:
                    meta = self.action_metadata.get(action_name, {}) if isinstance(self.action_metadata, dict) else {}
                    if not isinstance(meta, Mapping):
                        continue
                    if "strategy_weight" not in meta:
                        continue
                    strategy_weight = _clamp(meta.get("strategy_weight", baseline), 0.0, 1.0)
                    centered = strategy_weight - baseline
                    pressure[action_name] += centered * 0.8
        except Exception:
            pass

        # NOTE: Affective and physiological modulation is applied in BG.
        # Selector output should remain cortical/cognitive competition only.
        _ = affect_modifier

        # One bounded scale for every gate term. tanh keeps ordering and
        # stops a large sum from swamping weights that live in [0, 1].
        for action_name in list(pressure.keys()):
            try:
                value = float(pressure[action_name])
            except (TypeError, ValueError):
                value = 0.0
            if not math.isfinite(value):
                value = 0.0
            pressure[action_name] = math.tanh(value)

        if verbose:
            print(f"Pressure vector: {pressure}")
            print(f"Affect modifier: {affect_modifier:.2f}")

        return pressure

    def _signed_recall_means(self, hippocampal_exps) -> Dict[str, float]:
        """Energy-weighted mean of episode reward for each recalled action."""
        sums = {action: 0.0 for action in self.actions}
        weights = {action: 0.0 for action in self.actions}
        for exp in list(hippocampal_exps or []):
            try:
                outcome = _clamp(getattr(exp, "reward", 0.0), -1.0, 1.0)
                intensity = _clamp(getattr(exp, "intensity", 0.0), 0.0, 2.0) / 2.0
                activation = _clamp(getattr(exp, "activation_energy", 0.0), 0.0, 1.0)
            except Exception:
                continue
            energy = intensity * activation
            if energy <= 1e-12:
                continue
            events = getattr(getattr(exp, "path", None), "events", None) or []
            seen = set()
            for event in events:
                try:
                    if getattr(getattr(event, "event_type", None), "value", "") != "action":
                        continue
                    action_name = str(event.name).split(":", 1)[-1]
                except Exception:
                    continue
                if action_name not in sums or action_name in seen:
                    continue
                seen.add(action_name)
                sums[action_name] += outcome * energy
                weights[action_name] += energy
        means = {}
        for action_name, weight in weights.items():
            if weight > 1e-12:
                means[action_name] = sums[action_name] / weight
        return means

    def choose(
        self,
        hippocampal_exps,
        cortical_patterns,
        intent_pressure=None,
        affect_modifier: float = 1.0,
        temporal_chains_bias: dict = None,
        prediction_pressure: dict = None,
        verbose: bool = False,
        affect_bias: Optional[Dict[str, float]] = None,
    ):
        """
        Choose action based on active experiences, patterns, intent habits, and affective state.

        ``affect_modifier`` is a deprecated scalar fallback. Prefer ``affect_bias``
        (decision_bias dict) or per-action scaling applied by the caller (Agent).
        """
        if affect_bias:
            try:
                response_speed = float(affect_bias.get("response_speed", 0.0))
                stress = float(affect_bias.get("stress", 0.0))
                fallback = 1.0 + (0.2 * response_speed) - (0.25 * max(0.0, stress))
                if abs(float(affect_modifier) - 1.0) < 1e-12:
                    affect_modifier = max(0.1, min(2.0, fallback))
            except Exception:
                pass

        pressure = self.compute_pressures(
            hippocampal_exps=hippocampal_exps,
            cortical_patterns=cortical_patterns,
            intent_pressure=intent_pressure,
            affect_modifier=affect_modifier,
            temporal_chains_bias=temporal_chains_bias,
            prediction_pressure=prediction_pressure,
            verbose=False,
        )

        # Legacy choose() behavior keeps explicit affect scaling for callers
        # that still use selector.choose() directly.
        for action_name in pressure:
            pressure[action_name] *= float(affect_modifier)

        # 4. Handle empty pressure (no experiences)
        positive_total_pressure = sum(max(0.0, p) for p in pressure.values())
        if positive_total_pressure <= 0.0:
            # No guidance - return random action
            import random
            return random.choice(self.actions)
        
        # 5. Calculate confidence
        max_pressure = max(pressure.values())
        confidence = max(0.0, max_pressure) / positive_total_pressure if positive_total_pressure > 0.0 else 0.0
        
        if verbose:
            print(f"Pressure: {pressure}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Affect modifier: {affect_modifier:.2f}")
        
        # 6. Decision based on confidence
        if confidence > self.confidence_threshold:
            # Deterministic choice
            action = max(pressure, key=pressure.get)
        else:
            # Stochastic choice - controlled variability
            action = self._stochastic_choice(pressure)
        
        return action

    def apply_decision_modulation(
        self,
        pressure_vector: Mapping[str, float],
        state: Optional[Mapping[str, Any]] = None,
        decision_mode: str = "HABITUAL",
    ) -> Dict[str, float]:
        scores = {str(action): float(value) for action, value in dict(pressure_vector or {}).items()}
        if str(decision_mode).upper() != "DELIBERATIVE":
            return scores

        for action in list(scores.keys()):
            meta = self.get_action_metadata(action)
            action_confidence = _clamp(
                meta.get("confidence", meta.get("semantic_confidence", 1.0)), 0.0, 1.0
            )
            action_stability = _clamp(
                meta.get("stability_score", meta.get("stability", 1.0)), 0.0, 1.0
            )
            has_semantic = bool(meta.get("consolidated", meta.get("consolidation_flag", False)))
            if not has_semantic and action_confidence <= 0.0 and action_stability <= 0.0:
                action_confidence = 1.0
                action_stability = 1.0
            base_score = scores[action]
            penalized = base_score * action_confidence * action_stability

            edpc_bias = 0.0
            if isinstance(state, Mapping):
                predictions = state.get("edpc_predictions")
                if isinstance(predictions, Mapping):
                    edpc_bias = float(predictions.get(action, 0.0))
                else:
                    edpc_bias = float(state.get("expected_reward_mean", 0.0))
            if abs(edpc_bias) > 1e-12:
                penalized *= (1.0 + (0.25 * _clamp(edpc_bias, -1.0, 1.0)))
            scores[action] = penalized
        return scores

    def select_action(
        self,
        state: Optional[Mapping[str, Any]],
        pressure_vector: Mapping[str, float],
        temperature: float,
        decision_mode: str,
    ) -> str:
        import random

        scores = self.apply_decision_modulation(
            pressure_vector=pressure_vector,
            state=state,
            decision_mode=decision_mode,
        )
        if not scores:
            return random.choice(self.actions) if self.actions else ""

        if not any(abs(float(v)) > 1e-12 for v in scores.values()):
            return random.choice(self.actions) if self.actions else ""

        temp = max(0.01, float(temperature))
        if str(decision_mode).upper() == "DELIBERATIVE":
            temp = max(temp, 0.8)

        probabilities = self._softmax(scores, temp)
        if not probabilities:
            return random.choice(self.actions) if self.actions else ""
        actions = list(probabilities.keys())
        weights = [probabilities[a] for a in actions]
        return random.choices(actions, weights=weights, k=1)[0]

    def evaluate(self, hypothetical_state: Mapping[str, Any]) -> Dict[str, float]:
        """
        Evaluate a hypothetical variant (utility-only, no action selection).
        """
        state = dict(hypothetical_state or {})
        active_drive = str(state.get("active_drive", ""))
        proposed_action = str(state.get("proposed_action", ""))

        effect = dict(state.get("predicted_effect", {}) or {})
        if not effect:
            effect = self.get_action_effect(proposed_action)
        state["predicted_effect"] = effect
        components = compute_drive_utility_components(
            state,
            drive_utility_profiles=self.drive_utility_profiles,
        )

        return {
            "utility": float(components["utility"]),
            "confidence": float(components["confidence_hint"]),
            "relevance_score": float(components["relevance_hint"]),
            "best_action": proposed_action,
            "drive_relief": float(components["drive_relief"]),
            "axes_score": float(components["axes_score"]),
            "effect_energy": float(components["effect_energy"]),
        }

    def _stochastic_choice(self, pressure: Dict[str, float]) -> str:
        """
        Stochastic selection with probability proportional to pressure.
        
        This adds controlled variability when confidence is low.
        Not learning - just exploration.
        """
        import random
        
        min_pressure = min(pressure.values()) if pressure else 0.0
        if min_pressure < 0.0:
            adjusted = {a: (p - min_pressure) for a, p in pressure.items()}
        else:
            adjusted = dict(pressure)

        total = sum(adjusted.values())
        if total <= 0:
            return random.choice(self.actions)
        
        # Normalize to probabilities
        probabilities = {a: p / total for a, p in adjusted.items()}
        
        # Sample according to pressure
        actions_list = list(probabilities.keys())
        probs_list = [probabilities[a] for a in actions_list]
        
        return random.choices(actions_list, weights=probs_list, k=1)[0]

    def _softmax(self, scores: Dict[str, float], temperature: float) -> Dict[str, float]:
        if not scores:
            return {}
        t = max(1e-6, float(temperature))
        max_score = max(scores.values())
        exp_vals: Dict[str, float] = {}
        exp_sum = 0.0
        for action_id, score in scores.items():
            val = math.exp((float(score) - max_score) / t)
            exp_vals[action_id] = val
            exp_sum += val
        if exp_sum <= 0.0:
            p = 1.0 / float(len(scores))
            return {action_id: p for action_id in scores}
        return {action_id: (val / exp_sum) for action_id, val in exp_vals.items()}
