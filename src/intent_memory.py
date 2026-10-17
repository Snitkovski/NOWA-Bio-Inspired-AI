"""
IntentMemory — память привычек, связывающая контекст с намерениями.

Не обучает, не оптимизирует, не выбирает.
Формирует давление привычки на основе опыта.
"""

import math
import time
import hashlib
from typing import ClassVar, Dict, List, Tuple
from dataclasses import dataclass, field


def _event_priority(token: str) -> int:
    """Higher means more salient. Unknown events sort by name after these."""
    priorities = {
        "alarm_call": 100,
        "high_stress": 90,
        "hunger_critical": 80,
        "thirst_critical": 80,
        "wakefulness_critical": 80,
        "food_critical": 76,
        "water_critical": 76,
        "hunger_high": 70,
        "thirst_high": 70,
        "wakefulness_high": 70,
        "food_low": 60,
        "estrus": 55,
        "pregnant": 50,
        "stranger_nearby": 40,
        "juvenile": 36,
        "bored": 20,
        "food_ok": 10,
    }
    if token in priorities:
        return priorities[token]
    if token.startswith("social_contact:"):
        return 45
    if token.startswith("zone:"):
        return 5
    return 0


@dataclass
class IntentTrace:
    """
    Trace связи контекст → намерение.
    Представляет привычку, а не правило.
    """
    intent_type: str
    context_signature: str
    MAX_STRENGTH: ClassVar[float] = 64.0
    strength: float = 1.0  # Частота / устойчивость
    recency: float = 0.0   # Свежесть (0-1), decay со временем
    timestamp: float = field(default_factory=time.time)
    # Canonical events this trace was stored under. Empty on legacy saves.
    context_features: tuple = ()
    # Priors (dataset seeds) may match when their features are contained.
    # Learned traces stay exact, so one situation cannot rewrite another.
    match_subset: bool = False
    
    def __repr__(self):
        return f"IntentTrace({self.intent_type}@{self.context_signature}, strength={self.strength:.2f}, recency={self.recency:.2f})"
    
    def age_in_seconds(self) -> float:
        """Возраст trace в секундах"""
        return time.time() - self.timestamp
    
    def update_recency(self, half_life: float = 3600.0):
        """
        Обновить recency с exponential decay.
        half_life - время в секундах, за которое recency уменьшается вдвое.
        """
        age = self.age_in_seconds()
        self.recency = 2.0 ** (-age / half_life)  # Exponential decay
    
    def strengthen(self):
        """Усилить trace при повторном использовании. Рост ограничен."""
        self.strength = min(self.MAX_STRENGTH, self.strength + 1.0)
        self.timestamp = time.time()
        self.recency = 1.0


class IntentMemory:
    """
    Память привычек - связи контекст → намерение.
    
    Не выбирает действие, а создаёт давление.
    Ослабевает при неиспользовании.
    Укрепляется при повторении.
    """
    
    def __init__(self, context_signature_window: int = 1, 
                 recency_half_life: float = 3600.0,
                 min_strength_for_trace: float = 0.1):
        """
        Args:
            context_signature_window: legacy tail length. New keys use the
                canonical feature set; this window is only how old saves match.
            recency_half_life: время в секундах для exponential decay recency
            min_strength_for_trace: минимальная strength для активации
        """
        self.traces: Dict[str, IntentTrace] = {}  # key: intent_type + context_signature
        self.context_signature_window = context_signature_window
        self.recency_half_life = recency_half_life
        self.min_strength_for_trace = min_strength_for_trace
    
    def _signature_text(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:8]

    def canonical_context_features(self, context: List[str]) -> tuple:
        """Order-independent salient set. Priority, then name, breaks ties.

        Duplicates collapse. The result does not depend on PYTHONHASHSEED.
        """
        seen = set()
        tokens: List[str] = []
        for item in list(context or []):
            token = str(item).strip()
            if not token or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
        tokens.sort(key=lambda token: (-_event_priority(token), token))
        return tuple(tokens)

    def _compute_context_signature(self, context: List[str]) -> str:
        """Hash the canonical feature set, not the last event."""
        return self._signature_text("|".join(self.canonical_context_features(context)))

    def _legacy_context_signature(self, context: List[str]) -> str:
        """Historical key: md5 of the last ``context_signature_window`` events."""
        window = list(context)[-self.context_signature_window:] if context else []
        return self._signature_text("|".join(str(item) for item in window))

    def _trace_match_weight(self, trace: IntentTrace, features: tuple, exact: str, legacy: str) -> float:
        signature = str(getattr(trace, "context_signature", "") or "")
        if signature == exact:
            return 1.0
        stored = tuple(getattr(trace, "context_features", ()) or ())
        if bool(getattr(trace, "match_subset", False)) and stored and set(stored) < set(features):
            return 0.5
        # Saves written before the canonical key only have the tail hash.
        if (not stored) and signature == legacy and signature != exact:
            return 1.0
        return 0.0
    
    def record_trace(self, context: List[str], intent_type: str):
        """
        Записать использование пары (контекст, намерение).
        
        Если trace уже есть:
          - усилить (strength += 1)
          - обновить recency
        Если нет:
          - создать новый trace
        """
        features = self.canonical_context_features(context)
        context_sig = self._signature_text("|".join(features))
        trace_key = f"{intent_type}:{context_sig}"
        
        if trace_key in self.traces:
            self.traces[trace_key].strengthen()
            if not getattr(self.traces[trace_key], "context_features", ()):
                self.traces[trace_key].context_features = features
        else:
            self.traces[trace_key] = IntentTrace(
                intent_type=intent_type,
                context_signature=context_sig,
                strength=1.0,
                recency=1.0,
                timestamp=time.time(),
                context_features=features,
            )
    
    def activate_by_context(self, context: List[str]) -> Dict[str, float]:
        """
        Активировать traces, релевантные контексту.
        
        Возвращает распределение давления:
        {
            intent_type_1: pressure_1,
            intent_type_2: pressure_2
        }
        
        pressure = strength × recency × relevance
        """
        features = self.canonical_context_features(context)
        exact = self._signature_text("|".join(features))
        legacy = self._legacy_context_signature(context)
        pressure: Dict[str, float] = {}
        
        # Обновить recency для всех traces и активировать релевантные
        for trace_key, trace in self.traces.items():
            trace.update_recency(self.recency_half_life)
            weight = self._trace_match_weight(trace, features, exact, legacy)
            if weight <= 0.0:
                continue
            if trace.strength >= self.min_strength_for_trace:
                p = trace.strength * trace.recency * weight
                intent = trace.intent_type
                pressure[intent] = pressure.get(intent, 0.0) + p
        
        return pressure
    
    def get_dominant_intent(self, context: List[str], 
                           confidence_threshold: float = 0.7) -> Tuple[str, float]:
        """
        Получить доминирующее намерение по давлению.
        
        Возвращает: (intent_type, confidence)
        
        confidence рассчитывается как:
          dominant_pressure / sum(all_pressures)
        
        Если confidence < threshold → None, None (неуверенность)
        """
        pressure = self.activate_by_context(context)
        
        if not pressure:
            return None, 0.0
        
        total = sum(pressure.values())
        dominant_intent = max(pressure, key=pressure.get)
        dominant_pressure = pressure[dominant_intent]
        confidence = dominant_pressure / total if total > 0 else 0.0
        
        if confidence < confidence_threshold:
            return dominant_intent, confidence  # Все ещё возвращаем, но с низкой confidence
        
        return dominant_intent, confidence
    
    def degrade_unused(self, decay_factor: float = 0.5):
        """
        Ослабить неиспользуемые traces.
        Вызывается во время сна.
        
        Args:
            decay_factor: на какой множитель умножить strength (0-1)
        """
        traces_to_remove = []
        for trace_key, trace in self.traces.items():
            trace.strength *= decay_factor
            if trace.strength < self.min_strength_for_trace:
                traces_to_remove.append(trace_key)
        
        for key in traces_to_remove:
            del self.traces[key]
    
    def strengthen_trace(self, context: List[str], intent_type: str, factor: float = 1.5):
        """Усилить конкретный trace при его успешном использовании"""
        context_sig = self._compute_context_signature(context)
        trace_key = f"{intent_type}:{context_sig}"
        
        if trace_key in self.traces:
            trace = self.traces[trace_key]
            try:
                factor_v = float(factor)
            except (TypeError, ValueError):
                factor_v = 1.0
            if not math.isfinite(factor_v):
                factor_v = 1.0
            updated = trace.strength * factor_v
            if not math.isfinite(updated):
                updated = IntentTrace.MAX_STRENGTH
            trace.strength = min(IntentTrace.MAX_STRENGTH, max(0.0, updated))
            trace.recency = 1.0
            trace.timestamp = time.time()

    def note_selection(self, context: List[str], intent_type: str) -> None:
        """Remember that an action was selected, without counting it as success.

        Outcome-blind ``strength += 1`` locked the first pick. The trace is
        created at strength 0 until ``apply_outcome`` sees a real result.
        """
        features = self.canonical_context_features(context)
        context_sig = self._signature_text("|".join(features))
        trace_key = f"{intent_type}:{context_sig}"
        if trace_key in self.traces:
            trace = self.traces[trace_key]
            trace.timestamp = time.time()
            trace.recency = 1.0
            if not getattr(trace, "context_features", ()):
                trace.context_features = features
            return
        self.traces[trace_key] = IntentTrace(
            intent_type=intent_type,
            context_signature=context_sig,
            strength=0.0,
            recency=1.0,
            timestamp=time.time(),
            context_features=features,
        )

    def apply_outcome(
        self,
        context: List[str],
        intent_type: str,
        outcome: float,
        affect_gain: float = 1.0,
    ) -> None:
        """EMA the habit toward 1 on success and toward 0 on failure.

        Affect only scales the learning rate, and only inside a fixed bound.
        It does not multiply the trace.
        """
        try:
            outcome_v = float(outcome)
        except (TypeError, ValueError):
            return
        if not math.isfinite(outcome_v):
            return
        outcome_v = max(-1.0, min(1.0, outcome_v))
        self.note_selection(context, intent_type)
        if abs(outcome_v) < 1e-12:
            return
        try:
            gain = float(affect_gain)
        except (TypeError, ValueError):
            gain = 1.0
        if not math.isfinite(gain):
            gain = 1.0
        gain = max(0.25, min(1.5, gain))
        rate = 0.20 * gain
        target = 1.0 if outcome_v > 0.0 else 0.0
        context_sig = self._compute_context_signature(context)
        trace = self.traces[f"{intent_type}:{context_sig}"]
        updated = trace.strength + (rate * (target - trace.strength))
        trace.strength = max(0.0, min(1.0, updated))
        trace.timestamp = time.time()
        trace.recency = 1.0
    
    def get_habit_affect_modulation(self, affect_state):
        """
        FIXED (Spec #1, #10): Return modulation multipliers only, don't make decisions or modify traces.
        
        This fixes violation of decision-making logic. Instead of modifying/deleting traces directly,
        return multipliers for the sleep consolidation phase to apply.
        
        Args:
            affect_state: AffectiveState instance
        
        Returns:
            Dict mapping trace_keys to modulation multipliers [0.0 .. 2.0]
        """
        modulation_map = {}
        conflict_severity = affect_state.conflict_severity()
        axes = getattr(affect_state, "axes", None)
        if isinstance(axes, dict):
            valence = float(axes.get("valence", getattr(affect_state, "valence", 0.0)))
            threat = max(0.0, float(axes.get("stress", getattr(affect_state, "threat", 0.0))))
        else:
            valence = float(getattr(affect_state, "valence", 0.0))
            threat = float(getattr(affect_state, "threat", 0.0))
        
        for trace_key, trace in self.traces.items():
            # Start with baseline
            multiplier = 1.0
            
            # Threat / canonical stress reduces habit reinforcement
            multiplier *= (1.0 - threat * 0.2)
            
            # Positive valence enhances recent habits
            recency_age = trace.age_in_seconds()
            is_recent = recency_age < (self.recency_half_life * 0.5)
            if is_recent and valence > 0.5:
                multiplier *= 1.1
            
            # Conflict reduces habit strength
            multiplier *= (1.0 - conflict_severity * 0.15)
            
            # Clamp and ensure non-negative
            modulation_map[trace_key] = max(0.0, min(2.0, multiplier))
        
        return modulation_map
    
    def apply_habit_affect_modulation(self, affect_modulation: dict):
        """
        Apply modulation from affect (called by sleep consolidation).
        Does NOT delete traces - only modulates strength. Deletion happens via decay in sleep.
        
        Args:
            affect_modulation: Dict from get_habit_affect_modulation()
        """
        for trace_key, multiplier in affect_modulation.items():
            if trace_key in self.traces:
                # Apply multiplier; allow strengthening above 1.0 for consolidation,
                # but never let a geometric affect factor overflow the trace.
                updated = self.traces[trace_key].strength * multiplier
                if not math.isfinite(updated):
                    updated = IntentTrace.MAX_STRENGTH
                self.traces[trace_key].strength = min(
                    IntentTrace.MAX_STRENGTH,
                    max(0.0, updated),
                )
    
    def consolidate_with_affect_profile(self, context: List[str], intent_type: str, 
                                       affect_profile: dict):
        """
        Сохранить профиль аффективного состояния с привычкой.
        
        Используется для анализа того, в каком состоянии привычка была закреплена.
        
        Args:
            context: Context list
            intent_type: Action/intent type
            affect_profile: Snapshot of affect state at time of reinforcement
        """
        context_sig = self._compute_context_signature(context)
        trace_key = f"{intent_type}:{context_sig}"
        
        if trace_key in self.traces:
            # Сохранить в расширенной информации
            if not hasattr(self.traces[trace_key], 'affect_profiles'):
                self.traces[trace_key].affect_profiles = []
            self.traces[trace_key].affect_profiles.append(affect_profile)
            
            # Ограничить размер истории
            if len(self.traces[trace_key].affect_profiles) > 10:
                self.traces[trace_key].affect_profiles.pop(0)
    
    def get_all_traces_for_intent(self, intent_type: str) -> List[IntentTrace]:
        """Получить все traces для определённого намерения"""
        return [t for t in self.traces.values() if t.intent_type == intent_type]
    
    def get_stats(self) -> Dict:
        """Статистика по IntentMemory"""
        if not self.traces:
            return {"total_traces": 0}
        
        by_intent = {}
        for trace in self.traces.values():
            if trace.intent_type not in by_intent:
                by_intent[trace.intent_type] = []
            by_intent[trace.intent_type].append(trace.strength)
        
        stats = {"total_traces": len(self.traces), "by_intent": {}}
        for intent, strengths in by_intent.items():
            stats["by_intent"][intent] = {
                "count": len(strengths),
                "total_strength": sum(strengths),
                "avg_strength": sum(strengths) / len(strengths)
            }
        
        return stats
    
    def to_dict(self) -> Dict:
        """Serialize habits. Legacy loads may omit features and match_subset."""
        traces = []
        for trace in self.traces.values():
            traces.append(
                {
                    "intent_type": trace.intent_type,
                    "context_signature": trace.context_signature,
                    "strength": float(trace.strength),
                    "recency": float(trace.recency),
                    "timestamp": float(trace.timestamp),
                    "context_features": list(getattr(trace, "context_features", ()) or ()),
                    "match_subset": bool(getattr(trace, "match_subset", False)),
                }
            )
        return {
            "context_signature_window": int(self.context_signature_window),
            "recency_half_life": float(self.recency_half_life),
            "min_strength_for_trace": float(self.min_strength_for_trace),
            "traces": traces,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "IntentMemory":
        """Load a habit save. Missing feature lists keep the legacy tail key."""
        payload = data if isinstance(data, dict) else {}
        try:
            window = int(payload.get("context_signature_window", 1))
        except (TypeError, ValueError):
            window = 1
        try:
            half_life = float(payload.get("recency_half_life", 3600.0))
        except (TypeError, ValueError):
            half_life = 3600.0
        try:
            min_strength = float(payload.get("min_strength_for_trace", 0.1))
        except (TypeError, ValueError):
            min_strength = 0.1
        memory = cls(
            context_signature_window=max(1, window),
            recency_half_life=half_life if half_life > 0.0 else 3600.0,
            min_strength_for_trace=min_strength,
        )
        rows = payload.get("traces", []) or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        now = time.time()
        for row in list(rows):
            if not isinstance(row, dict):
                continue
            intent = str(row.get("intent_type", "") or "").strip()
            signature = str(row.get("context_signature", "") or "").strip()
            if not intent or not signature:
                continue
            raw_features = row.get("context_features", []) or []
            features = tuple(str(item).strip() for item in list(raw_features) if str(item).strip())
            try:
                strength = float(row.get("strength", 1.0))
            except (TypeError, ValueError):
                strength = 1.0
            try:
                recency = float(row.get("recency", 0.0))
            except (TypeError, ValueError):
                recency = 0.0
            try:
                timestamp = float(row.get("timestamp", now))
            except (TypeError, ValueError):
                timestamp = now
            if not math.isfinite(strength):
                strength = 1.0
            if not math.isfinite(recency):
                recency = 0.0
            if not math.isfinite(timestamp):
                timestamp = now
            memory.traces[f"{intent}:{signature}"] = IntentTrace(
                intent_type=intent,
                context_signature=signature,
                strength=strength,
                recency=recency,
                timestamp=timestamp,
                context_features=features,
                match_subset=bool(row.get("match_subset", False)),
            )
        return memory

    def __repr__(self):
        return f"IntentMemory({len(self.traces)} traces)"
