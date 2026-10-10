"""
Prediction Layer - minimal v1 implementation (renamed from PlanC)

Provides a pure `PredictionLayer.predict` implementation that, given read-only
inputs, returns a mapping `action -> pressure` with small magnitudes.

This implementation follows the specification in
`Docs/plan_c_prediction_layer_formal_spec.md` and is a direct rename of
the earlier `plan_c` implementation.
"""
from typing import Dict, List, Any


class PredictionLayer:
    """Minimal prediction layer implementation (v1).

    The predict method is intentionally simple: it inspects recent events
    for past actions, aggregates their observed (proxy) affect, and
    produces a small advisory pressure per action. The implementation is
    pure and avoids any side-effects.
    """

    def __init__(self, max_pressure: float = 0.3):
        self.max_pressure = float(max_pressure)

    def predict(self,
                context: Dict[str, Any],
                recent_events: List[str],
                affect_state: Any,
                neuromodulators: Any,
                temporal_levels: Any) -> Dict[str, float]:
        """Return advisory pressures for actions found in `recent_events`.

        Notes:
        - Does not mutate any input.
        - Returns pressures in range [-max_pressure, +max_pressure].
        - Only infers actions that appear as tokens like 'action:<name>'.
        """
        # Defensive copies of inputs where we'll iterate (do not mutate originals)
        recent = list(recent_events) if recent_events is not None else []

        # Estimate a global valence proxy from neuromodulators if available
        valence = 0.0
        try:
            if hasattr(neuromodulators, 'snapshot'):
                snap = neuromodulators.snapshot()
            elif isinstance(neuromodulators, dict):
                snap = neuromodulators
            else:
                snap = {}

            # Use dopamine (DA) and serotonin (5-HT) as rough proxies if present
            da = float(snap.get('DA', 0.0)) if snap else 0.0
            ht = float(snap.get('5-HT', snap.get('5HT', 0.0))) if snap else 0.0
            valence = 0.5 * da + 0.5 * ht
        except Exception:
            valence = 0.0

        # Temporal discount factor (prefer short-term signals)
        discount = 1.0
        try:
            if isinstance(temporal_levels, dict):
                # If T1/T2 available, prefer T1
                discount = float(temporal_levels.get('T1_discount', 1.0))
                if discount <= 0:
                    discount = 1.0
        except Exception:
            discount = 1.0

        # Aggregate occurrences of actions with a simple recency weighting
        action_scores = {}
        for idx, token in enumerate(reversed(recent)):
            if not isinstance(token, str):
                continue
            if not token.startswith('action:'):
                continue
            name = token.split(':', 1)[1]
            # recency weight: newer events contribute more (1.0 -> recent, decays)
            weight = 1.0 / (1 + idx * 0.5)
            action_scores.setdefault(name, 0.0)
            action_scores[name] += weight

        # Convert aggregated scores to advisory pressures in bounded range
        pressures: Dict[str, float] = {}
        if not action_scores:
            return {}

        max_score = max(action_scores.values()) if action_scores else 1.0
        for a, s in action_scores.items():
            # normalized score in (0,1]
            norm = s / max_score if max_score > 0 else 0.0
            # base pressure follows signed valence; if valence == 0 use small positive bias
            base = (valence if abs(valence) > 1e-6 else 0.05) * norm
            # apply temporal discount and compress to [-max_pressure, max_pressure]
            p = max(-self.max_pressure, min(self.max_pressure, base * discount))
            pressures[a] = float(p)

        shock = max((abs(v) for v in pressures.values()), default=0.0)
        self.last_affective_impulse = {
            "stress": min(0.2, shock * 0.4),
            "curiosity": min(0.2, shock * 0.3),
        }
        return pressures


__all__ = ["PredictionLayer"]
