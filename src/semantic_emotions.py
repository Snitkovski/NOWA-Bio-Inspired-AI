"""
Semantic Emotions (Phase 4.1)

Interprets the continuous affective space (Phase 4) as a set of
overlapping semantic emotion attractors. This layer does NOT influence
action selection and does not generate affective control signals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from affective_space import AXES, AffectiveSpace


def _clamp(value: float, min_v: float = 0.0, max_v: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return max(min_v, min(max_v, v))


def _axis(axes: Dict[str, float], name: str) -> float:
    """Non-negative readout in [0, 1] for attractor formulas."""
    return _clamp(axes.get(name, 0.0), 0.0, 1.0)


def _signed(axes: Dict[str, float], name: str) -> float:
    try:
        return max(-1.0, min(1.0, float(axes.get(name, 0.0))))
    except Exception:
        return 0.0


def _pos(axes: Dict[str, float], name: str) -> float:
    return _clamp(max(0.0, _signed(axes, name)), 0.0, 1.0)


def _neg(axes: Dict[str, float], name: str) -> float:
    return _clamp(max(0.0, -_signed(axes, name)), 0.0, 1.0)


def _unit(axes: Dict[str, float], name: str) -> float:
    return _clamp((_signed(axes, name) + 1.0) / 2.0, 0.0, 1.0)


def _joy(axes: Dict[str, float]) -> float:
    return _clamp((_pos(axes, "valence") * 0.5) + (_pos(axes, "arousal") * 0.4) - (_pos(axes, "stress") * 0.4))


def _sadness(axes: Dict[str, float]) -> float:
    return _clamp(
        (_pos(axes, "stress") * 0.4)
        + (_neg(axes, "valence") * 0.3)
        + ((1.0 - _unit(axes, "arousal")) * 0.2)
        + (_pos(axes, "attachment") * 0.3)
    )


def _love(axes: Dict[str, float]) -> float:
    return _clamp(
        (_pos(axes, "attachment") * 0.5)
        + (_pos(axes, "valence") * 0.3)
        + (_pos(axes, "trust") * 0.15)
        + (_neg(axes, "stability") * 0.3)
    )


def _hate(axes: Dict[str, float]) -> float:
    return _clamp(
        (_neg(axes, "trust") * 0.5)
        + (_pos(axes, "arousal") * 0.3)
        + (_pos(axes, "dominance") * 0.3)
        + (_pos(axes, "stress") * 0.15)
    )


def _fear(axes: Dict[str, float]) -> float:
    return _clamp(
        (_pos(axes, "stress") * 0.5)
        + (_pos(axes, "arousal") * 0.3)
        + (_neg(axes, "dominance") * 0.3)
        + (_neg(axes, "stability") * 0.2)
    )


def _pleasure_rest(axes: Dict[str, float]) -> float:
    return _clamp((_pos(axes, "valence") * 0.5) + (_pos(axes, "stability") * 0.5) - (_pos(axes, "arousal") * 0.15))


@dataclass
class SemanticEmotionDefinition:
    name: str
    axes: List[str]
    compute: Callable[[Dict[str, float]], float]


CANONICAL_EMOTIONS: List[SemanticEmotionDefinition] = [
    SemanticEmotionDefinition(name="joy", axes=["valence", "arousal", "stress"], compute=_joy),
    SemanticEmotionDefinition(name="sadness", axes=["stress", "arousal", "attachment"], compute=_sadness),
    SemanticEmotionDefinition(name="love", axes=["attachment", "valence", "stability"], compute=_love),
    SemanticEmotionDefinition(name="hate", axes=["trust", "arousal", "dominance"], compute=_hate),
    SemanticEmotionDefinition(name="fear", axes=["stress", "arousal", "dominance"], compute=_fear),
    SemanticEmotionDefinition(name="pleasure_rest", axes=["valence", "stability"], compute=_pleasure_rest),
]


@dataclass
class SemanticEmotionsLayer:
    """
    Phase 4.1 semantic emotions layer.

    Inputs: AffectiveSpace axes + inertia + fall_rate + speed
    Output: List of active semantic emotions (activation, stability, obsessive)
    """

    activation_threshold: float = 0.0
    inertia_high_threshold: float = 0.6
    fall_rate_low_threshold: float = 0.3
    focus_high_threshold: float = 0.6
    active_emotions: List[Dict[str, Any]] = field(default_factory=list)
    last_update_ts: float = field(default_factory=time.time)

    def update_from_space(
        self,
        space: Optional[AffectiveSpace],
        wakefulness: Optional[float] = None,
        agent_lifetime: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute semantic emotions from AffectiveSpace.

        Args:
            space: AffectiveSpace instance (required)
            wakefulness: optional, reserved for future use
            agent_lifetime: optional, reserved for future use
        """
        if space is None:
            self.active_emotions = []
            return []

        axes = dict(getattr(space, "axes", {}) or {})

        inertia = dict(getattr(space, "inertia", {}) or {})
        fall_rate = dict(getattr(space, "fall_rate", {}) or {})

        stability = _clamp(1.0 - float(getattr(space, "speed", lambda: 0.0)()), 0.0, 1.0)

        focus_high = max(_pos(axes, "dominance"), _pos(axes, "curiosity")) >= self.focus_high_threshold

        emotions: List[Dict[str, Any]] = []
        for definition in CANONICAL_EMOTIONS:
            activation = _clamp(definition.compute(axes), 0.0, 1.0)
            if activation <= self.activation_threshold:
                continue

            # Axis-specific obsessiveness (mean across emotion axes)
            inertia_vals = [_clamp(inertia.get(axis, 0.0), 0.0, 1.0) for axis in definition.axes]
            fall_vals = [_clamp(fall_rate.get(axis, 0.0), 0.0, 1.0) for axis in definition.axes]

            inertia_mean = sum(inertia_vals) / len(inertia_vals) if inertia_vals else 0.0
            fall_mean = sum(fall_vals) / len(fall_vals) if fall_vals else 0.0

            inertia_high = inertia_mean >= self.inertia_high_threshold
            fall_rate_low = fall_mean <= self.fall_rate_low_threshold

            obsessive = bool(inertia_high and fall_rate_low and focus_high)

            emotions.append(
                {
                    "emotion": definition.name,
                    "activation": activation,
                    "stability": stability,
                    "obsessive": obsessive,
                }
            )

        emotions.sort(key=lambda e: e.get("activation", 0.0), reverse=True)
        self.active_emotions = emotions
        self.last_update_ts = time.time()
        return emotions

    def snapshot(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in (self.active_emotions or [])]

    def describe_brief(
        self,
        space: Optional[AffectiveSpace] = None,
        background: Optional[Dict[str, float]] = None,
        max_sentences: int = 2,
    ) -> str:
        """
        Return a short, human-readable description of the current semantic-emotional state.
        This is a narrative layer only and is not used for action selection.
        """
        axes: Dict[str, float] = {}
        conflict = 0.0
        stability = None
        if space is not None:
            if hasattr(space, "legacy_axes_snapshot"):
                axes = dict(getattr(space, "legacy_axes_snapshot")() or {})
            else:
                axes = dict(getattr(space, "axes", {}) or {})
            try:
                conflict = float(space.axis_conflict())
            except Exception:
                conflict = 0.0
            try:
                stability = _clamp(1.0 - (float(space.speed()) * 0.5), 0.0, 1.0)
            except Exception:
                stability = None

        background = background or {}

        def _bg(name: str) -> float:
            return _clamp(background.get(f"background_{name}", 0.0), 0.0, 1.0)

        pleasure = _axis(axes, "pleasure")
        pain = _axis(axes, "pain")
        arousal = _axis(axes, "arousal")
        relaxation = _axis(axes, "relaxation")
        attachment = _axis(axes, "attachment")
        rejection = _axis(axes, "rejection")
        vulnerability = _axis(axes, "vulnerability")
        focus = _axis(axes, "focus")

        bg_anxiety = _bg("anxiety")
        bg_tension = _bg("tension")
        bg_satisfaction = _bg("satisfaction")
        bg_interest = _bg("interest")

        sentences: List[str] = []
        used_tags = set()

        def _add(sentence: str, tag: str) -> None:
            if not sentence:
                return
            if tag in used_tags:
                return
            if sentence in sentences:
                return
            sentences.append(sentence)
            used_tags.add(tag)

        interest_high = bg_interest >= 0.6
        tension_high = bg_tension >= 0.6
        satisfaction_high = bg_satisfaction >= 0.6
        anxiety_high = bg_anxiety > 0.7
        anxiety_mid = 0.4 <= bg_anxiety <= 0.7

        arousal_vs_pleasure_high = arousal > pleasure + 0.25
        pleasure_vs_arousal_high = (pleasure > arousal + 0.25) and (relaxation > 0.3)
        pain_vs_pleasure_high = pain > pleasure + 0.25
        relax_low_arousal = relaxation > 0.6 and arousal < 0.3

        pain_high = pain >= 0.6
        rejection_high = rejection >= 0.6
        vulnerability_high = vulnerability >= 0.6
        focus_high = focus >= 0.6
        has_obsessive = any(bool(item.get("obsessive")) for item in (self.active_emotions or []))

        # Primary sentence: interest+tension blend or dominant semantic emotions
        if interest_high and tension_high:
            if stability is not None and stability >= 0.6:
                _add("Я чувствую устойчивую смесь интереса и напряжения.", "interest_tension")
            else:
                _add("Я чувствую смесь интереса и напряжения.", "interest_tension")
        else:
            top = [
                item for item in sorted(self.active_emotions or [], key=lambda e: float(e.get("activation", 0.0)), reverse=True)
                if float(item.get("activation", 0.0)) >= 0.3
            ]
            name_map_gen = {
                "joy": "радости",
                "sadness": "грусти",
                "love": "привязанности",
                "hate": "отторжения",
                "fear": "страха",
                "pleasure_rest": "спокойствия",
            }
            name_map_acc = {
                "joy": "радость",
                "sadness": "грусть",
                "love": "привязанность",
                "hate": "отторжение",
                "fear": "страх",
                "pleasure_rest": "спокойствие",
            }
            if top:
                if len(top) >= 2:
                    n1 = name_map_gen.get(top[0].get("emotion"), "смешанных ощущений")
                    n2 = name_map_gen.get(top[1].get("emotion"), "смешанных ощущений")
                    prefix = "Я чувствую "
                    if stability is not None and stability >= 0.6:
                        prefix += "устойчивую "
                    _add(f"{prefix}смесь {n1} и {n2}.", "semantic_mix")
                else:
                    n1 = name_map_acc.get(top[0].get("emotion"), "смешанные ощущения")
                    _add(f"Я чувствую {n1}.", "semantic_single")
            else:
                if anxiety_high:
                    _add("Фоновая тревога доминирует.", "anxiety_high")
                elif satisfaction_high and relaxation > 0.4:
                    _add("Преобладает спокойное удовлетворение.", "satisfaction")
                elif interest_high and bg_tension < 0.4:
                    _add("Преобладает интерес без выраженного напряжения.", "interest_only")
                elif interest_high:
                    _add("Преобладает фоновый интерес.", "interest_only")
                elif tension_high:
                    _add("Фоновое напряжение выражено.", "tension_only")
                elif arousal_vs_pleasure_high:
                    _add("Сейчас больше возбуждения, чем удовольствия — это похоже на ожидание.", "arousal_vs_pleasure")
                elif pleasure_vs_arousal_high:
                    _add("Сейчас больше удовольствия, чем возбуждения — это похоже на удовлетворение.", "pleasure_vs_arousal")
                elif pain_vs_pleasure_high:
                    _add("Боль заметнее удовольствия — это похоже на внутренний дискомфорт.", "pain_vs_pleasure")
                elif relax_low_arousal:
                    _add("Состояние спокойное и расслабленное.", "calm_relax")
                elif bg_satisfaction > 0.5:
                    _add("Присутствует спокойное удовлетворение.", "satisfaction")
                else:
                    _add("Состояние ровное и без выраженных доминант.", "neutral")

        # Secondary sentence: attachment+conflict, anxiety, or arousal/pleasure contrast
        if len(sentences) < max_sentences:
            if attachment > 0.6 and conflict > 0.35:
                if pleasure > 0.4:
                    _add("Присутствует тёплая привязанность, несмотря на внутренний конфликт.", "attachment_conflict")
                else:
                    _add("Присутствует привязанность, несмотря на внутренний конфликт.", "attachment_conflict")
            elif anxiety_mid:
                _add("Есть фоновая тревога, но она не доминирует.", "anxiety_mid")
            elif interest_high and bg_tension < 0.4:
                _add("Есть фоновый интерес без выраженного напряжения.", "interest_only_secondary")
            elif bg_tension > 0.6 and bg_interest < 0.4:
                _add("Фоновое напряжение выражено сильнее интереса.", "tension_over_interest")
            elif pain_high and pleasure < 0.4:
                _add("Есть ощущение боли при слабом удовольствии.", "pain_high")
            elif rejection_high:
                _add("Есть ощущение отторжения и дистанции.", "rejection_high")
            elif vulnerability_high:
                _add("Есть ощущение уязвимости.", "vulnerability_high")
            elif focus_high:
                _add("Фокус повышен, внимание собрано.", "focus_high")
            elif arousal_vs_pleasure_high:
                _add("Сейчас больше возбуждения, чем удовольствия — это похоже на ожидание.", "arousal_vs_pleasure")
            elif pleasure_vs_arousal_high:
                _add("Сейчас больше удовольствия, чем возбуждения — это похоже на удовлетворение.", "pleasure_vs_arousal")
            elif relax_low_arousal:
                _add("Состояние спокойное и расслабленное.", "calm_relax")
            elif bg_satisfaction > 0.5:
                _add("Присутствует спокойное удовлетворение.", "satisfaction")
            elif has_obsessive:
                _add("Есть навязчивые эмоциональные паттерны.", "obsessive")

        return "\n".join(sentences[:max_sentences]) if sentences else "(none)"

    def to_dict(self) -> dict:
        return {
            "active_emotions": self.snapshot(),
            "activation_threshold": self.activation_threshold,
            "inertia_high_threshold": self.inertia_high_threshold,
            "fall_rate_low_threshold": self.fall_rate_low_threshold,
            "focus_high_threshold": self.focus_high_threshold,
            "last_update_ts": self.last_update_ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticEmotionsLayer":
        inst = cls(
            activation_threshold=float(data.get("activation_threshold", 0.0)),
            inertia_high_threshold=float(data.get("inertia_high_threshold", 0.6)),
            fall_rate_low_threshold=float(data.get("fall_rate_low_threshold", 0.3)),
            focus_high_threshold=float(data.get("focus_high_threshold", 0.6)),
        )
        inst.last_update_ts = float(data.get("last_update_ts", time.time()))
        inst.active_emotions = [dict(item) for item in (data.get("active_emotions") or [])]
        return inst
