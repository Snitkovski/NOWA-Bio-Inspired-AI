"""
Phase 4.3 — Emotional Expectations

Prospective forecasting layer derived from emotional memory.
This layer does NOT influence action selection or modify other layers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from emotional_memory_narratives import EmotionalMemoryNarrativesLayer
from semantic_emotions import SemanticEmotionsLayer


def _clamp(value: float, min_v: float = 0.0, max_v: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return max(min_v, min(max_v, v))


_EMOTION_TEXT = {
    "joy": "радость",
    "sadness": "грусть",
    "love": "привязанность",
    "hate": "отторжение",
    "fear": "страх",
    "pleasure_rest": "спокойствие",
}


@dataclass
class EmotionalExpectationsLayer:
    """
    Phase 4.3 emotional expectations (forecasting only).

    Computes probabilistic expectations from emotional memory patterns.
    """

    recency_half_life_seconds: float = 3600.0
    min_total_episodes: int = 3
    trend_delta_threshold: float = 0.1
    obsessive_inertia_threshold: float = 0.6

    expectations: List[Dict[str, Any]] = field(default_factory=list)
    dominant_forecast: str = ""
    global_outlook: str = "stabilizing"
    last_update_ts: float = field(default_factory=time.time)

    def update(
        self,
        memory_layer: Optional[EmotionalMemoryNarrativesLayer],
        semantic_emotions: Optional[SemanticEmotionsLayer | Iterable[Dict[str, Any]]],
        background: Optional[Dict[str, float]] = None,
        agent_lifetime: Optional[float] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Update expectations from emotional memory + semantic emotions.
        """
        from learning_guard import guard_owned_writer

        if not guard_owned_writer(self, "EmotionalExpectationsLayer.update"):
            return self.snapshot()
        ts = float(timestamp) if timestamp is not None else time.time()
        self.last_update_ts = ts
        background = background or {}

        episodes, patterns = self._extract_memory(memory_layer)

        min_required = int(getattr(memory_layer, "min_total_episodes", self.min_total_episodes) or self.min_total_episodes)
        if len(episodes) < max(1, min_required):
            self.expectations = []
            self.dominant_forecast = ""
            # "neutral" outlook maps to stabilizing for schema consistency
            self.global_outlook = "stabilizing"
            return self.snapshot()

        emotion_set = self._collect_emotions(episodes, semantic_emotions, memory_layer)
        if not emotion_set:
            self.expectations = []
            self.dominant_forecast = ""
            self.global_outlook = "stabilizing"
            return self.snapshot()

        trends, early_w, recent_w, counts = self._compute_trends(episodes, ts, agent_lifetime)
        pattern_map = {str(p.get("emotion")): dict(p) for p in (patterns or []) if p.get("emotion")}

        outlook = self._compute_global_outlook(episodes, patterns)

        expectations: List[Dict[str, Any]] = []
        for emotion in sorted(emotion_set):
            inertia = _clamp(pattern_map.get(emotion, {}).get("inertia", 0.0))
            trend = trends.get(emotion, "stable")

            probability = 0.4 + 0.6 * inertia
            if trend == "increasing":
                probability += 0.1
            elif trend == "decreasing":
                probability -= 0.1
            probability = _clamp(probability)

            risk = bool(pattern_map.get(emotion, {}).get("obsessive")) and inertia >= self.obsessive_inertia_threshold
            if risk:
                probability = max(probability, 0.8)

            confidence = self._estimate_confidence(
                inertia=inertia,
                emotion_count=int(counts.get(emotion, 0)),
                total_episodes=len(episodes),
                early_weight=float(early_w.get(emotion, 0.0)),
                recent_weight=float(recent_w.get(emotion, 0.0)),
            )

            expectations.append(
                {
                    "emotion": emotion,
                    "trend": trend,
                    "probability": _clamp(probability),
                    "confidence": _clamp(confidence),
                    "risk_of_repetition": bool(risk),
                }
            )

        # Direction continuation adjustment (Phase 4.2 shift)
        shift = self._detect_direction_shift(episodes, ts, agent_lifetime)
        if shift:
            previous_emotion, new_emotion = shift
            for item in expectations:
                if item.get("emotion") == new_emotion:
                    item["probability"] = _clamp(float(item.get("probability", 0.0)) + 0.1)
                    item["trend"] = "increasing"
                elif item.get("emotion") == previous_emotion:
                    item["probability"] = _clamp(float(item.get("probability", 0.0)) - 0.1)
                    item["trend"] = "decreasing"

        # Re-apply obsessive floor and clamp values
        for item in expectations:
            if item.get("risk_of_repetition"):
                item["probability"] = max(float(item.get("probability", 0.0)), 0.8)
            item["probability"] = _clamp(item.get("probability", 0.0))
            item["confidence"] = _clamp(item.get("confidence", 0.0))

        if outlook == "volatile":
            for item in expectations:
                item["confidence"] = _clamp(float(item.get("confidence", 0.0)) * 0.7)

        expectations.sort(key=lambda e: (e.get("probability", 0.0), e.get("confidence", 0.0)), reverse=True)

        self.expectations = expectations
        self.global_outlook = outlook
        self.dominant_forecast = expectations[0]["emotion"] if expectations else ""

        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "expectations": [dict(item) for item in (self.expectations or [])],
            "dominant_forecast": self.dominant_forecast,
            "global_outlook": self.global_outlook,
            "last_update_ts": self.last_update_ts,
        }

    def to_dict(self) -> dict:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalExpectationsLayer":
        inst = cls()
        inst.expectations = [dict(item) for item in (data.get("expectations") or [])]
        inst.dominant_forecast = str(data.get("dominant_forecast", ""))
        inst.global_outlook = str(data.get("global_outlook", "stabilizing"))
        inst.last_update_ts = float(data.get("last_update_ts", time.time()))
        return inst

    def describe_brief(self, max_lines: int = 2) -> str:
        if not self.expectations:
            return "(none)"

        lines: List[str] = []
        top = self.expectations[0]
        emotion = str(top.get("emotion", ""))
        trend = str(top.get("trend", "stable"))
        emotion_text = _EMOTION_TEXT.get(emotion, emotion or "эмоция")

        if trend == "increasing":
            lines.append(f"Наблюдается тенденция к усилению {emotion_text}.")
        elif trend == "decreasing":
            lines.append(f"Вероятно ослабление {emotion_text}.")
        else:
            lines.append(f"Вероятно сохранится {emotion_text}.")

        if bool(top.get("risk_of_repetition")):
            lines.append("Существует риск повторения навязчивого паттерна.")

        outlook_phrase = {
            "stabilizing": "Эмоциональная динамика вероятно стабилизируется.",
            "volatile": "Эмоциональная динамика выглядит нестабильной.",
            "escalating": "Эмоциональная динамика может усиливаться.",
        }.get(self.global_outlook, "")
        if outlook_phrase:
            lines.append(outlook_phrase)

        return "\n".join(lines[: max(1, int(max_lines))])

    @staticmethod
    def _extract_active(semantic_emotions: Optional[SemanticEmotionsLayer | Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if semantic_emotions is None:
            return []
        if isinstance(semantic_emotions, SemanticEmotionsLayer):
            return semantic_emotions.snapshot()
        if isinstance(semantic_emotions, list):
            return [dict(item) for item in semantic_emotions]
        try:
            return list(getattr(semantic_emotions, "snapshot", lambda: [])())
        except Exception:
            return []

    def _extract_memory(
        self,
        memory_layer: Optional[EmotionalMemoryNarrativesLayer],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        episodes: List[Dict[str, Any]] = []
        patterns: List[Dict[str, Any]] = []
        if memory_layer is None:
            return episodes, patterns
        try:
            if hasattr(memory_layer, "_episodes_with_current"):
                episodes = list(memory_layer._episodes_with_current())
            else:
                episodes = list(getattr(memory_layer, "episodes", []) or [])
        except Exception:
            episodes = list(getattr(memory_layer, "episodes", []) or [])
        try:
            patterns = list(getattr(memory_layer, "patterns", []) or [])
        except Exception:
            patterns = []
        return episodes, patterns

    def _collect_emotions(
        self,
        episodes: List[Dict[str, Any]],
        semantic_emotions: Optional[SemanticEmotionsLayer | Iterable[Dict[str, Any]]],
        memory_layer: Optional[EmotionalMemoryNarrativesLayer],
    ) -> set[str]:
        emotions: set[str] = set()
        for ep in episodes:
            for emotion in ep.get("emotions", []) or []:
                if emotion:
                    emotions.add(str(emotion))

        active = self._extract_active(semantic_emotions)
        threshold = getattr(memory_layer, "activation_threshold", 0.0) if memory_layer is not None else 0.0
        for item in active:
            try:
                if float(item.get("activation", 0.0)) >= float(threshold):
                    name = str(item.get("emotion", ""))
                    if name:
                        emotions.add(name)
            except Exception:
                continue
        return emotions

    def _recency_half_life(self, agent_lifetime: Optional[float]) -> float:
        base = float(self.recency_half_life_seconds or 0.0)
        if agent_lifetime is None or agent_lifetime <= 0.0:
            return max(1.0, base)
        dynamic = float(agent_lifetime) * 0.1
        half_life = max(base, min(dynamic, base * 10.0))
        return max(1.0, half_life)

    def _episode_weight(self, episode: Dict[str, Any], now_ts: float, half_life: float) -> float:
        try:
            end_ts = float(episode.get("end_ts", episode.get("last_ts", now_ts)))
        except Exception:
            end_ts = now_ts
        age = max(0.0, float(now_ts) - end_ts)
        if half_life <= 0.0:
            return 1.0
        return 0.5 ** (age / half_life)

    def _relative_position(
        self,
        idx: int,
        total: int,
        episode: Dict[str, Any],
        now_ts: float,
        agent_lifetime: Optional[float],
    ) -> float:
        if agent_lifetime is None or agent_lifetime <= 0.0:
            if total <= 1:
                return 1.0
            return _clamp(float(idx) / float(total - 1))

        creation_ts = float(now_ts) - float(agent_lifetime)
        try:
            start_ts = float(episode.get("start_ts", now_ts))
            end_ts = float(episode.get("end_ts", episode.get("last_ts", now_ts)))
            mid_ts = (start_ts + end_ts) / 2.0
        except Exception:
            mid_ts = now_ts
        rel = (mid_ts - creation_ts) / float(agent_lifetime)
        return _clamp(rel, 0.0, 1.0)

    def _compute_trends(
        self,
        episodes: List[Dict[str, Any]],
        now_ts: float,
        agent_lifetime: Optional[float],
    ) -> Tuple[Dict[str, str], Dict[str, float], Dict[str, float], Dict[str, int]]:
        early_sum: Dict[str, float] = {}
        early_w: Dict[str, float] = {}
        recent_sum: Dict[str, float] = {}
        recent_w: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        total = len(episodes)
        half_life = self._recency_half_life(agent_lifetime)

        for idx, ep in enumerate(episodes):
            emotions = [str(e) for e in (ep.get("emotions", []) or []) if e]
            if not emotions:
                continue
            rel = self._relative_position(idx, total, ep, now_ts, agent_lifetime)
            w = self._episode_weight(ep, now_ts, half_life)
            mean_activation = float(ep.get("mean_activation", 0.0))

            for emotion in emotions:
                counts[emotion] = counts.get(emotion, 0) + 1
                if rel <= 0.33:
                    early_sum[emotion] = early_sum.get(emotion, 0.0) + w * mean_activation
                    early_w[emotion] = early_w.get(emotion, 0.0) + w
                if rel >= 0.67:
                    recent_sum[emotion] = recent_sum.get(emotion, 0.0) + w * mean_activation
                    recent_w[emotion] = recent_w.get(emotion, 0.0) + w

        trends: Dict[str, str] = {}
        emotions = set(counts.keys()) | set(early_w.keys()) | set(recent_w.keys())
        for emotion in emotions:
            ew = float(early_w.get(emotion, 0.0))
            rw = float(recent_w.get(emotion, 0.0))
            if ew <= 0.0 or rw <= 0.0:
                trends[emotion] = "stable"
                continue
            early_mean = float(early_sum.get(emotion, 0.0)) / ew
            recent_mean = float(recent_sum.get(emotion, 0.0)) / rw
            delta = recent_mean - early_mean
            if delta > self.trend_delta_threshold:
                trends[emotion] = "increasing"
            elif delta < -self.trend_delta_threshold:
                trends[emotion] = "decreasing"
            else:
                trends[emotion] = "stable"

        return trends, early_w, recent_w, counts

    def _estimate_confidence(
        self,
        inertia: float,
        emotion_count: int,
        total_episodes: int,
        early_weight: float,
        recent_weight: float,
    ) -> float:
        coverage = float(emotion_count) / float(total_episodes) if total_episodes > 0 else 0.0
        base = 0.3 + 0.5 * _clamp(inertia) + 0.2 * _clamp(coverage)
        if early_weight <= 0.0 or recent_weight <= 0.0:
            base *= 0.6
        return _clamp(base)

    def _detect_direction_shift(
        self,
        episodes: List[Dict[str, Any]],
        now_ts: float,
        agent_lifetime: Optional[float],
    ) -> Optional[Tuple[str, str]]:
        if agent_lifetime is None or agent_lifetime <= 0.0:
            return None

        half_life = self._recency_half_life(agent_lifetime)
        early_weights: Dict[str, float] = {}
        recent_weights: Dict[str, float] = {}
        total_early = 0.0
        total_recent = 0.0

        for ep in episodes:
            try:
                start_ts = float(ep.get("start_ts", now_ts))
                end_ts = float(ep.get("end_ts", ep.get("last_ts", now_ts)))
                mid_ts = (start_ts + end_ts) / 2.0
            except Exception:
                mid_ts = now_ts

            rel = self._relative_position(0, 1, {"start_ts": mid_ts, "end_ts": mid_ts}, now_ts, agent_lifetime)
            w = self._episode_weight(ep, now_ts, half_life)
            emotions = ep.get("emotions") or []
            for emotion in emotions:
                name = str(emotion)
                if rel <= 0.33:
                    early_weights[name] = early_weights.get(name, 0.0) + w
                    total_early += w
                if rel >= 0.67:
                    recent_weights[name] = recent_weights.get(name, 0.0) + w
                    total_recent += w

        if total_early <= 0.0 or total_recent <= 0.0:
            return None
        early_emotion, early_w = max(early_weights.items(), key=lambda item: item[1]) if early_weights else ("", 0.0)
        recent_emotion, recent_w = max(recent_weights.items(), key=lambda item: item[1]) if recent_weights else ("", 0.0)
        if not early_emotion or not recent_emotion or early_emotion == recent_emotion:
            return None
        if (early_w / total_early) < 0.55 or (recent_w / total_recent) < 0.55:
            return None
        return early_emotion, recent_emotion

    def _compute_global_outlook(
        self,
        episodes: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
    ) -> str:
        if len(episodes) < max(1, self.min_total_episodes):
            return "stabilizing"

        recent = episodes[-min(len(episodes), 6) :]
        activations = [float(ep.get("mean_activation", 0.0)) for ep in recent if ep]
        if not activations:
            return "stabilizing"

        mean = sum(activations) / len(activations)
        variance = sum((v - mean) ** 2 for v in activations) / len(activations)

        dominant_inertia = 0.0
        if patterns:
            try:
                dominant_inertia = float(patterns[0].get("inertia", 0.0))
            except Exception:
                dominant_inertia = 0.0

        dominants = []
        for ep in recent:
            emos = ep.get("emotions") or []
            if emos:
                dominants.append(str(emos[0]))
        if len(dominants) >= 3:
            switches = sum(1 for i in range(1, len(dominants)) if dominants[i] != dominants[i - 1])
            if switches / max(1, len(dominants) - 1) >= 0.6:
                return "volatile"

        if len(activations) >= 3:
            diffs = [activations[i] - activations[i - 1] for i in range(1, len(activations))]
            if all(d >= -0.02 for d in diffs) and (activations[-1] - activations[0]) >= 0.15:
                return "escalating"

        if variance <= 0.02 and dominant_inertia >= self.obsessive_inertia_threshold:
            return "stabilizing"

        return "stabilizing"


__all__ = ["EmotionalExpectationsLayer"]
