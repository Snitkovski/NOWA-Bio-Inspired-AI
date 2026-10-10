"""
Phase 4.2 — Emotional Memory & Narratives

Emotional autobiographical memory derived from semantic emotions and affective space.
This layer does NOT influence action selection or planning.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

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
class EmotionalMemoryNarrativesLayer:
    """
    Phase 4.2 emotional memory and narrative layer.

    Aggregates semantic emotions into episodes, consolidates patterns,
    and renders retrospective narrative fragments.
    """

    activation_threshold: float = 0.25
    max_episode_gap: float = 5.0
    min_recurrence_freq: int = 2
    recurrence_ratio_threshold: float = 0.4
    min_total_episodes: int = 3
    stability_high_threshold: float = 0.7
    obsessive_inertia_threshold: float = 0.6
    recency_half_life_seconds: float = 3600.0
    max_episode_history: int = 200

    episodes: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    narrative_fragments: List[Dict[str, Any]] = field(default_factory=list)
    character_traits: List[str] = field(default_factory=list)
    last_update_ts: float = field(default_factory=time.time)
    _current_episode: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def update_from_layers(
        self,
        semantic_emotions: Optional[SemanticEmotionsLayer | Iterable[Dict[str, Any]]],
        space: Optional[Any] = None,
        background: Optional[Dict[str, float]] = None,
        agent_lifetime: Optional[float] = None,
        timestamp: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Update emotional memory from semantic emotions and contextual state.
        """
        ts = float(timestamp) if timestamp is not None else time.time()
        background = background or {}
        self.last_update_ts = ts

        active = self._extract_active(semantic_emotions)
        active = [item for item in active if float(item.get("activation", 0.0)) >= self.activation_threshold]
        active.sort(key=lambda e: float(e.get("activation", 0.0)), reverse=True)

        emotions, mean_activation, mean_stability, obsessive = self._select_emotions(active)

        if not emotions:
            self._finalize_current(ts)
            self._recompute_patterns(background, agent_lifetime, active)
            return self.narrative_fragments

        self._update_episode(emotions, ts, mean_activation, mean_stability, obsessive)
        self._recompute_patterns(background, agent_lifetime, active)
        return self.narrative_fragments

    def snapshot(self) -> Dict[str, Any]:
        return {
            "episodes": [dict(item) for item in (self.episodes or [])],
            "patterns": [dict(item) for item in (self.patterns or [])],
            "narrative_fragments": [dict(item) for item in (self.narrative_fragments or [])],
            "character_traits": list(self.character_traits or []),
            "last_update_ts": self.last_update_ts,
        }

    def describe_brief(self, max_fragments: int = 2) -> str:
        fragments = [f.get("text", "") for f in (self.narrative_fragments or []) if f.get("text")]
        if not fragments:
            return "(none)"
        return "\n".join(fragments[:max_fragments])

    def to_dict(self) -> dict:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalMemoryNarrativesLayer":
        inst = cls()
        inst.episodes = [dict(item) for item in (data.get("episodes") or [])]
        inst.patterns = [dict(item) for item in (data.get("patterns") or [])]
        inst.narrative_fragments = [dict(item) for item in (data.get("narrative_fragments") or [])]
        inst.character_traits = list(data.get("character_traits") or [])
        inst.last_update_ts = float(data.get("last_update_ts", time.time()))
        return inst

    def _extract_active(self, semantic_emotions: Optional[SemanticEmotionsLayer | Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
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

    def _select_emotions(self, active: List[Dict[str, Any]]) -> tuple[List[str], float, float, bool]:
        if not active:
            return [], 0.0, 0.0, False

        emotions = [str(active[0].get("emotion", ""))]
        if len(active) > 1:
            top = float(active[0].get("activation", 0.0))
            second = float(active[1].get("activation", 0.0))
            if second >= max(0.3, top - 0.15):
                emotions.append(str(active[1].get("emotion", "")))

        activation_vals = [float(item.get("activation", 0.0)) for item in active if item.get("emotion") in emotions]
        stability_vals = [float(item.get("stability", 0.0)) for item in active if item.get("emotion") in emotions]
        mean_activation = sum(activation_vals) / len(activation_vals) if activation_vals else 0.0
        mean_stability = sum(stability_vals) / len(stability_vals) if stability_vals else 0.0
        obsessive = any(bool(item.get("obsessive")) for item in active if item.get("emotion") in emotions)
        return emotions, mean_activation, mean_stability, obsessive

    def _update_episode(self, emotions: List[str], ts: float, activation: float, stability: float, obsessive: bool) -> None:
        if self._current_episode:
            same = self._current_episode.get("emotions") == emotions
            gap = ts - float(self._current_episode.get("last_ts", ts))
            if same and gap <= self.max_episode_gap:
                self._current_episode["last_ts"] = ts
                self._current_episode["samples"] += 1
                self._current_episode["activation_sum"] += activation
                self._current_episode["stability_sum"] += stability
                self._current_episode["obsessive"] = bool(self._current_episode.get("obsessive") or obsessive)
                return
            self._finalize_current(ts)

        self._current_episode = {
            "emotions": list(emotions),
            "start_ts": ts,
            "last_ts": ts,
            "samples": 1,
            "activation_sum": float(activation),
            "stability_sum": float(stability),
            "obsessive": bool(obsessive),
        }

    def _finalize_current(self, ts: float) -> None:
        if not self._current_episode:
            return
        end_ts = float(self._current_episode.get("last_ts", ts))
        start_ts = float(self._current_episode.get("start_ts", end_ts))
        samples = max(1, int(self._current_episode.get("samples", 1)))
        duration = max(0.0, end_ts - start_ts)
        mean_activation = float(self._current_episode.get("activation_sum", 0.0)) / samples
        mean_stability = float(self._current_episode.get("stability_sum", 0.0)) / samples
        episode = {
            "emotions": list(self._current_episode.get("emotions", [])),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "duration": duration,
            "mean_activation": mean_activation,
            "stability": mean_stability,
            "obsessive": bool(self._current_episode.get("obsessive")),
        }
        self.episodes.append(episode)
        if len(self.episodes) > self.max_episode_history:
            self.episodes = self.episodes[-self.max_episode_history :]
        self._current_episode = None

    def _episodes_with_current(self) -> List[Dict[str, Any]]:
        episodes = list(self.episodes or [])
        if self._current_episode:
            samples = max(1, int(self._current_episode.get("samples", 1)))
            end_ts = float(self._current_episode.get("last_ts", self.last_update_ts))
            start_ts = float(self._current_episode.get("start_ts", end_ts))
            duration = max(0.0, end_ts - start_ts)
            episodes.append(
                {
                    "emotions": list(self._current_episode.get("emotions", [])),
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "duration": duration,
                    "mean_activation": float(self._current_episode.get("activation_sum", 0.0)) / samples,
                    "stability": float(self._current_episode.get("stability_sum", 0.0)) / samples,
                    "obsessive": bool(self._current_episode.get("obsessive")),
                }
            )
        return episodes

    def _recompute_patterns(
        self,
        background: Dict[str, float],
        agent_lifetime: Optional[float],
        active: List[Dict[str, Any]],
    ) -> None:
        episodes = self._episodes_with_current()
        if len(episodes) < self.min_total_episodes:
            self.patterns = []
            self.character_traits = []
            self.narrative_fragments = []
            return
        now_ts = self.last_update_ts
        self.patterns = self._consolidate_patterns(episodes, now_ts, agent_lifetime)
        self.character_traits = self._derive_traits(self.patterns)
        self.narrative_fragments = self._render_narratives(self.patterns, background, agent_lifetime, active, now_ts, episodes)

    def _consolidate_patterns(self, episodes: List[Dict[str, Any]], now_ts: float, agent_lifetime: Optional[float]) -> List[Dict[str, Any]]:
        if not episodes:
            return []
        total = len(episodes)
        half_life = self._recency_half_life(agent_lifetime)
        weights = [self._episode_weight(ep, now_ts, half_life) for ep in episodes]
        total_weight = sum(weights) if weights else 0.0
        if total_weight <= 0.0:
            total_weight = float(total)
            weights = [1.0 for _ in episodes]

        stats: Dict[str, Dict[str, Any]] = {}
        for i, ep in enumerate(episodes):
            w = weights[i] if i < len(weights) else 1.0
            for emotion in ep.get("emotions", []) or []:
                name = str(emotion)
                if name not in stats:
                    stats[name] = {
                        "frequency": 0,
                        "weighted_frequency": 0.0,
                        "weighted_activation": 0.0,
                        "weighted_stability": 0.0,
                        "obsessive": False,
                    }
                stats[name]["frequency"] += 1
                stats[name]["weighted_frequency"] += w
                stats[name]["weighted_activation"] += w * float(ep.get("mean_activation", 0.0))
                stats[name]["weighted_stability"] += w * float(ep.get("stability", 0.0))
                stats[name]["obsessive"] = bool(stats[name]["obsessive"] or ep.get("obsessive"))

        patterns: List[Dict[str, Any]] = []
        for emotion, info in stats.items():
            frequency = int(info.get("frequency", 0))
            if frequency < self.min_recurrence_freq:
                continue
            weighted_frequency = float(info.get("weighted_frequency", 0.0))
            weighted_activation = float(info.get("weighted_activation", 0.0))
            weighted_stability = float(info.get("weighted_stability", 0.0))
            recurrence = frequency / total if total > 0 else 0.0
            weighted_recurrence = weighted_frequency / total_weight if total_weight > 0.0 else recurrence
            inertia = (weighted_stability / weighted_frequency) if weighted_frequency > 0.0 else 0.0
            mean_activation = (weighted_activation / weighted_frequency) if weighted_frequency > 0.0 else 0.0
            obsessive = bool(info.get("obsessive")) and inertia >= self.obsessive_inertia_threshold
            confidence = _clamp(0.3 + 0.7 * inertia)
            patterns.append(
                {
                    "emotion": emotion,
                    "frequency": frequency,
                    "recurrence": weighted_recurrence,
                    "inertia": inertia,
                    "mean_activation": mean_activation,
                    "obsessive": obsessive,
                    "confidence": confidence,
                }
            )
        patterns.sort(key=lambda p: (p.get("recurrence", 0.0), p.get("frequency", 0)), reverse=True)
        return patterns

    def _derive_traits(self, patterns: List[Dict[str, Any]]) -> List[str]:
        traits = []
        for p in patterns:
            if p.get("frequency", 0) >= 3 or p.get("recurrence", 0.0) >= 0.5:
                traits.append(str(p.get("emotion")))
        return traits

    def _render_narratives(
        self,
        patterns: List[Dict[str, Any]],
        background: Dict[str, float],
        agent_lifetime: Optional[float],
        active: List[Dict[str, Any]],
        now_ts: float,
        episodes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not patterns:
            return []

        fragments: List[Dict[str, Any]] = []
        top = patterns[0]
        emotion = str(top.get("emotion"))
        emotion_text = _EMOTION_TEXT.get(emotion, emotion)

        if top.get("frequency", 0) >= self.min_recurrence_freq and top.get("recurrence", 0.0) >= self.recurrence_ratio_threshold:
            fragments.append(
                {
                    "text": f"Часто возникает {emotion_text}.",
                    "confidence": top.get("confidence", 0.5),
                    "tag": "recurrent",
                }
            )

        direction_phrase = self._direction_shift_fragment(episodes, now_ts, agent_lifetime)
        if direction_phrase:
            fragments.append(
                {
                    "text": direction_phrase,
                    "confidence": top.get("confidence", 0.5),
                    "tag": "direction_shift",
                }
            )
        else:
            temporal_phrase = self._temporal_fragment(emotion, emotion_text, episodes, now_ts, agent_lifetime)
            if temporal_phrase:
                fragments.append(
                    {
                        "text": temporal_phrase,
                        "confidence": top.get("confidence", 0.5),
                        "tag": "temporal",
                    }
                )

        if bool(top.get("obsessive")):
            fragments.append(
                {
                    "text": "Есть навязчивый эмоциональный паттерн.",
                    "confidence": top.get("confidence", 0.5),
                    "tag": "obsessive",
                }
            )

        tension = _clamp(background.get("background_tension", 0.0), 0.0, 1.0)
        if tension >= 0.6 and any(p.get("emotion") == "joy" for p in patterns):
            fragments.append(
                {
                    "text": "Радость и напряжение часто проявляются вместе.",
                    "confidence": top.get("confidence", 0.5),
                    "tag": "mixed_tension",
                }
            )

        if float(top.get("inertia", 0.0)) >= self.stability_high_threshold:
            fragments.append(
                {
                    "text": "Состояние устойчиво.",
                    "confidence": top.get("confidence", 0.5),
                    "tag": "stability",
                }
            )

        # Keep only unique fragments by tag
        seen = set()
        unique_fragments = []
        for frag in fragments:
            tag = frag.get("tag")
            if tag in seen:
                continue
            seen.add(tag)
            unique_fragments.append(frag)
        return unique_fragments

    def _recency_half_life(self, agent_lifetime: Optional[float]) -> float:
        base = float(self.recency_half_life_seconds or 0.0)
        if agent_lifetime is None or agent_lifetime <= 0.0:
            return max(1.0, base)
        dynamic = float(agent_lifetime) * 0.1
        # Cap to keep recency effects noticeable for long lifetimes
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

    def _temporal_fragment(
        self,
        emotion: str,
        emotion_text: str,
        episodes: List[Dict[str, Any]],
        now_ts: float,
        agent_lifetime: Optional[float],
    ) -> str:
        if agent_lifetime is None or agent_lifetime <= 0.0:
            return ""
        creation_ts = float(now_ts) - float(agent_lifetime)
        if agent_lifetime <= 0.0:
            return ""

        early_weight = 0.0
        recent_weight = 0.0
        total_weight = 0.0
        half_life = self._recency_half_life(agent_lifetime)
        for ep in episodes:
            if emotion not in (ep.get("emotions") or []):
                continue
            try:
                mid_ts = (float(ep.get("start_ts", now_ts)) + float(ep.get("end_ts", now_ts))) / 2.0
            except Exception:
                mid_ts = now_ts
            rel = (mid_ts - creation_ts) / float(agent_lifetime)
            rel = _clamp(rel, 0.0, 1.0)
            w = self._episode_weight(ep, now_ts, half_life)
            total_weight += w
            if rel <= 0.33:
                early_weight += w
            if rel >= 0.67:
                recent_weight += w

        if total_weight <= 0.0:
            return ""
        early_ratio = early_weight / total_weight
        recent_ratio = recent_weight / total_weight
        if early_ratio >= 0.6:
            return f"На раннем этапе жизни часто возникала {emotion_text}."
        if recent_ratio >= 0.6:
            return f"В последнее время преобладает {emotion_text}."
        return ""

    def _direction_shift_fragment(
        self,
        episodes: List[Dict[str, Any]],
        now_ts: float,
        agent_lifetime: Optional[float],
    ) -> str:
        if agent_lifetime is None or agent_lifetime <= 0.0:
            return ""
        creation_ts = float(now_ts) - float(agent_lifetime)
        if agent_lifetime <= 0.0:
            return ""

        half_life = self._recency_half_life(agent_lifetime)
        early_weights: Dict[str, float] = {}
        recent_weights: Dict[str, float] = {}
        total_early = 0.0
        total_recent = 0.0

        for ep in episodes:
            try:
                mid_ts = (float(ep.get("start_ts", now_ts)) + float(ep.get("end_ts", now_ts))) / 2.0
            except Exception:
                mid_ts = now_ts
            rel = (mid_ts - creation_ts) / float(agent_lifetime)
            rel = _clamp(rel, 0.0, 1.0)
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
            return ""
        early_emotion, early_w = max(early_weights.items(), key=lambda item: item[1]) if early_weights else ("", 0.0)
        recent_emotion, recent_w = max(recent_weights.items(), key=lambda item: item[1]) if recent_weights else ("", 0.0)
        if not early_emotion or not recent_emotion or early_emotion == recent_emotion:
            return ""
        if (early_w / total_early) < 0.55 or (recent_w / total_recent) < 0.55:
            return ""

        early_text = _EMOTION_TEXT.get(early_emotion, early_emotion)
        recent_text = _EMOTION_TEXT.get(recent_emotion, recent_emotion)
        return f"Ранее преобладала {early_text}, сейчас чаще возникает {recent_text}."
