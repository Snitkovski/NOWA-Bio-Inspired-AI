"""Interpretive NOWA readouts for the colony agent inspector."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .i18n import character_id, profile_id, tone_id, tr


SECTION_LINE_COLOR = (195, 182, 165)
SECTION_TITLE_COLOR = (110, 98, 82)

AXIS_COLORS: dict[str, tuple[int, int, int]] = {
    "stress": (210, 90, 70),
    "arousal": (215, 150, 60),
    "valence": (90, 175, 115),
    "attachment": (180, 120, 200),
    "curiosity": (80, 170, 200),
    "trust": (110, 175, 140),
    "dominance": (200, 130, 80),
    "energy": (80, 155, 220),
    "social_drive": (155, 100, 190),
    "dopamine": (100, 160, 220),
    "serotonin": (90, 190, 130),
    "norepinephrine": (215, 140, 65),
    "cortisol": (205, 80, 70),
    "acetylcholine": (140, 110, 200),
    "wakefulness": (110, 155, 200),
    "sleep_pressure": (155, 125, 195),
    "circadian": (185, 165, 90),
    "alertness": (100, 180, 160),
}

TONE_BADGE_COLORS: dict[str, tuple[int, int, int]] = {
    "ПАНИКА": (200, 55, 45),
    "ОСТРЫЙ СТРЕСС": (210, 95, 55),
    "ХРОНИЧЕСКАЯ ТРЕВОГА": (195, 135, 65),
    "АГРЕССИЯ": (195, 65, 65),
    "ВОЗБУЖДЕНИЕ": (215, 178, 60),
    "СКУКА": (148, 138, 125),
    "ОДИНОЧЕСТВО": (105, 133, 178),
    "ЛЮБОПЫТСТВО": (85, 163, 143),
    "ПРИВЯЗАННОСТЬ": (183, 123, 193),
    "СПОКОЙСТВИЕ": (95, 168, 105),
    "УСТАЛОСТЬ": (135, 148, 168),
    "РАВНОВЕСИЕ": (143, 158, 133),
}


@dataclass
class AffectInterpretation:
    """Interpretation of the agent's affective state."""

    tone_label: str
    tone_color: tuple[int, int, int]
    summary: str
    axis_labels: dict[str, str]


@dataclass
class NeuroProfile:
    """Interpretation of the neuromodulator profile."""

    profile_label: str
    summary: str
    modulator_labels: dict[str, str]
    interactions: list[str]


@dataclass
class ValueLayerSnapshot:
    """Snapshot of one value/thalamic level."""

    level: int
    top_actions: list[tuple[str, float]]
    raw_values: dict[str, float]


@dataclass
class HabitPattern:
    """One stable cortex habit pattern."""

    context_tokens: list[str]
    action: str
    strength: float
    activation_count: int
    consequence: str


@dataclass
class RecentEpisode:
    """One significant recent hippocampus episode."""

    timestamp: float
    action: str
    context_tokens: list[str]
    reward: float
    consequence: str
    encoding_strength: float


@dataclass
class PersonalityReadout:
    """Behavioral personality readout."""

    character_label: str
    summary: str


@dataclass
class NowaInterpretation:
    """Full NOWA interpretation for the inspector tab."""

    affect: AffectInterpretation
    neuro: NeuroProfile
    value_layers: list[ValueLayerSnapshot]
    habits: list[HabitPattern]
    recent_episodes: list[RecentEpisode]
    personality: PersonalityReadout


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result:
        return default
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _as_list_str(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item)]
    return []


AXIS_KEYS = [
    "stress",
    "arousal",
    "valence",
    "attachment",
    "curiosity",
    "trust",
    "dominance",
    "energy",
    "social_drive",
]

AFFECT_TONES: list[tuple[str, tuple[int, int, int], Callable[[dict[str, float]], bool]]] = [
    ("ПАНИКА", (210, 60, 50), lambda a: a["stress"] > 0.85 and a["arousal"] > 0.80),
    ("ОСТРЫЙ СТРЕСС", (215, 100, 60), lambda a: a["stress"] > 0.70 and a["arousal"] > 0.60),
    ("ХРОНИЧЕСКАЯ ТРЕВОГА", (200, 140, 70), lambda a: a["stress"] > 0.55 and a["arousal"] < 0.55),
    ("АГРЕССИЯ", (200, 70, 70), lambda a: a["arousal"] > 0.75 and a["dominance"] > 0.60),
    ("ВОЗБУЖДЕНИЕ", (220, 185, 65), lambda a: a["arousal"] > 0.65 and a["stress"] < 0.45),
    ("СКУКА", (155, 145, 130), lambda a: a["curiosity"] < 0.20 and a["arousal"] < 0.30),
    ("ОДИНОЧЕСТВО", (110, 140, 185), lambda a: a["attachment"] < 0.10 and a["social_drive"] < 0.20),
    ("ЛЮБОПЫТСТВО", (90, 170, 150), lambda a: a["curiosity"] > 0.55 and a["stress"] < 0.40),
    ("ПРИВЯЗАННОСТЬ", (190, 130, 200), lambda a: a["attachment"] > 0.60 and a["trust"] > 0.50),
    ("СПОКОЙСТВИЕ", (100, 175, 110), lambda a: a["stress"] < 0.25 and a["arousal"] < 0.45),
    ("УСТАЛОСТЬ", (140, 155, 175), lambda a: a.get("energy", 1.0) < 0.25),
    ("РАВНОВЕСИЕ", (150, 165, 140), lambda a: True),
]

AFFECT_SUMMARIES: dict[str, str] = {
    "ПАНИКА": (
        "Агент находится в состоянии острого стресса с экстремальным возбуждением. "
        "Все когнитивные ресурсы направлены на выживание, социальные и исследовательские функции подавлены."
    ),
    "ОСТРЫЙ СТРЕСС": (
        "Высокий стресс при повышенном возбуждении. Агент воспринимает окружение как угрозу. "
        "Репродуктивный потенциал и социальность снижены."
    ),
    "ХРОНИЧЕСКАЯ ТРЕВОГА": (
        "Устойчивый стресс без острого возбуждения - признак хронического состояния. "
        "Агент привык к фоновой тревоге, но это истощает ресурсы со временем."
    ),
    "АГРЕССИЯ": (
        "Высокое возбуждение с доминантной позицией. "
        "Агент готов к конфронтации и активно отстаивает территорию или ресурсы."
    ),
    "ВОЗБУЖДЕНИЕ": (
        "Высокая активность без стресса - состояние игры или исследования. "
        "Агент открыт к новым взаимодействиям и готов к риску."
    ),
    "СКУКА": (
        "Низкое любопытство и возбуждение при отсутствии стресса. Агент не нашёл стимулирующих занятий. "
        "Риск развития апатичного поведения."
    ),
    "ОДИНОЧЕСТВО": (
        "Слабая привязанность и минимальный социальный драйв. "
        "Агент изолирован эмоционально, даже если физически находится в колонии."
    ),
    "ЛЮБОПЫТСТВО": (
        "Активное исследовательское состояние без стресса. "
        "Агент охотно взаимодействует с окружением и открыт к новому опыту."
    ),
    "ПРИВЯЗАННОСТЬ": (
        "Сильные эмоциональные связи с другими особями. "
        "Агент ориентирован на социальные взаимодействия и поддержание отношений."
    ),
    "СПОКОЙСТВИЕ": (
        "Низкий стресс и умеренное возбуждение - оптимальное базовое состояние. "
        "Агент доступен для всех типов взаимодействий."
    ),
    "УСТАЛОСТЬ": (
        "Критически низкий уровень энергии. Все поведенческие стратегии подчинены восстановлению."
    ),
    "РАВНОВЕСИЕ": (
        "Сбалансированный аффективный профиль без выраженных крайностей. "
        "Агент находится в стабильном состоянии средней активности."
    ),
}


def get_axis_label(axis: str, value: float) -> str:
    """Return a short label for an affective or wakefulness axis."""

    return tr(_axis_label_ru(axis, value))


def _axis_label_ru(axis: str, value: float) -> str:
    """Canonical Russian axis word. Translated at the edge by get_axis_label."""

    v = _safe_float(value, 0.0)
    if axis == "stress":
        if v > 0.85:
            return "критический"
        if v > 0.65:
            return "высокий"
        if v > 0.40:
            return "умеренный"
        if v > 0.15:
            return "низкий"
        return "минимальный"
    if axis == "arousal":
        if v > 0.85:
            return "экстремальное"
        if v > 0.65:
            return "высокое"
        if v > 0.40:
            return "умеренное"
        if v > 0.15:
            return "слабое"
        return "фоновое"
    if axis == "valence":
        if v > 0.60:
            return "радостный"
        if v > 0.25:
            return "позитивный"
        if v >= -0.25:
            return "нейтральный"
        if v >= -0.60:
            return "негативный"
        return "тяжёлый"
    if axis == "attachment":
        if v < 0.0:
            return "отчуждение"
        if v > 0.60:
            return "глубокая"
        if v > 0.30:
            return "есть связи"
        return "слабая"
    if axis == "curiosity":
        if v > 0.55:
            return "активное"
        if v > 0.25:
            return "умеренное"
        if v > 0.05:
            return "подавлено"
        return "отсутствует"
    if axis == "trust":
        if v < 0.0:
            return "недоверие"
        if v > 0.60:
            return "открытый"
        if v > 0.30:
            return "осторожный"
        return "закрытый"
    if axis == "dominance":
        if v < 0.0:
            return "подчинённое"
        if v > 0.60:
            return "доминирует"
        if v > 0.30:
            return "уверенный"
        return "уступает"
    if axis == "energy":
        if v > 0.75:
            return "полная"
        if v > 0.40:
            return "достаточная"
        if v > 0.20:
            return "низкая"
        return "критическая"
    if axis == "social_drive":
        if v > 0.60:
            return "ищет контактов"
        if v > 0.35:
            return "открыт к общению"
        if v > 0.10:
            return "замкнутый"
        return "избегает"
    if axis == "wakefulness":
        if v > 0.85:
            return "критическое"
        if v > 0.60:
            return "повышенное"
        if v > 0.35:
            return "умеренное"
        if v > 0.15:
            return "низкое"
        return "сонливость"
    if axis == "sleep_pressure":
        if v > 0.75:
            return "сильное"
        if v > 0.45:
            return "нарастает"
        if v > 0.20:
            return "умеренное"
        return "слабое"
    if axis == "circadian":
        if v > 0.70:
            return "активная фаза"
        if v > 0.35:
            return "переходная фаза"
        return "вечерняя фаза"
    if axis == "alertness":
        if v > 0.75:
            return "высокая"
        if v > 0.50:
            return "повышенная"
        if v > 0.25:
            return "умеренная"
        return "низкая"
    return f"{v:.2f}"


def interpret_affect(axes: Mapping[str, Any] | None) -> AffectInterpretation:
    """Interpret affective axes into one tone and axis labels."""

    source = _as_dict(axes or {})
    normalized = {key: _safe_float(source.get(key, 0.0), 0.0) for key in AXIS_KEYS}
    for label, color, condition in AFFECT_TONES:
        try:
            if condition(normalized):
                return AffectInterpretation(
                    tone_label=tr(label),
                    tone_color=TONE_BADGE_COLORS.get(label, color),
                    summary=tr(_flat(AFFECT_SUMMARIES.get(label, AFFECT_SUMMARIES["РАВНОВЕСИЕ"]))),
                    axis_labels={key: get_axis_label(key, normalized[key]) for key in AXIS_KEYS},
                )
        except Exception:
            continue
    return AffectInterpretation(
        tone_label=tr("РАВНОВЕСИЕ"),
        tone_color=TONE_BADGE_COLORS["РАВНОВЕСИЕ"],
        summary=tr(_flat(AFFECT_SUMMARIES["РАВНОВЕСИЕ"])),
        axis_labels={key: get_axis_label(key, normalized[key]) for key in AXIS_KEYS},
    )


def _flat(text: str) -> str:
    """Join wrapped source paragraphs into the phrase-catalog key."""

    return " ".join(part.strip() for part in str(text).split())


NEURO_KEYS = ["dopamine", "serotonin", "norepinephrine", "cortisol", "acetylcholine"]

NEURO_PROFILES: list[tuple[str, Callable[[dict[str, float]], bool]]] = [
    ("СТРЕССОВАЯ АКТИВАЦИЯ", lambda n: n["norepinephrine"] > 0.65 and n["dopamine"] < 0.20 and n["cortisol"] > 0.40),
    ("ДОФАМИНОВОЕ ИСТОЩЕНИЕ", lambda n: n["dopamine"] < 0.05 and n["cortisol"] > 0.50),
    ("ДОФАМИНОВЫЙ ПИК", lambda n: n["dopamine"] > 0.60 and n["cortisol"] < 0.30),
    ("СЕРОТОНИНОВЫЙ ДЕФИЦИТ", lambda n: n["serotonin"] < 0.10 and n["cortisol"] > 0.40),
    ("ХОЛИНЕРГИЧЕСКАЯ АКТИВАЦИЯ", lambda n: n["acetylcholine"] > 0.75 and n["dopamine"] < 0.30),
    ("КОРТИЗОЛЬНЫЙ ПИК", lambda n: n["cortisol"] > 0.85),
    ("СБАЛАНСИРОВАННЫЙ ПРОФИЛЬ", lambda n: all(0.20 < value < 0.75 for value in n.values())),
    ("ОБЩАЯ ДЕПРЕССИЯ", lambda n: n["dopamine"] < 0.10 and n["serotonin"] < 0.10 and n["norepinephrine"] < 0.20),
    ("ГИПЕРАКТИВАЦИЯ", lambda n: n["norepinephrine"] > 0.80 and n["acetylcholine"] > 0.75),
    ("СТАНДАРТНЫЙ", lambda n: True),
]

NM_LABELS: dict[str, dict[str, str]] = {
    "dopamine": {
        "high": "активная мотивация",
        "moderate": "умеренная тяга",
        "low": "слабая мотивация",
        "minimal": "нет мотивации",
    },
    "serotonin": {
        "high": "эмоциональная стабильность",
        "moderate": "умеренная стабильность",
        "low": "нестабильность",
        "minimal": "нет стабилизации",
    },
    "norepinephrine": {
        "high": "высокая готовность",
        "moderate": "умеренная активация",
        "low": "низкая реактивность",
        "minimal": "подавленная реакция",
    },
    "cortisol": {
        "high": "хронический стресс",
        "moderate": "стрессовая нагрузка",
        "low": "лёгкий тонус",
        "minimal": "минимальный",
    },
    "acetylcholine": {
        "high": "повышенное внимание",
        "moderate": "умеренное внимание",
        "low": "рассеянность",
        "minimal": "когнитивный минимум",
    },
}

NM_INTERACTIONS: list[tuple[Callable[[dict[str, float]], bool], str]] = [
    (lambda n: n["dopamine"] < 0.05 and n["cortisol"] > 0.50, "Кортизол подавляет выработку дофамина - нет мотивации при стрессе"),
    (lambda n: n["norepinephrine"] > 0.70 and n["dopamine"] < 0.15, "Норадреналин без дофамина - тревожная готовность без вознаграждения"),
    (lambda n: n["serotonin"] < 0.10 and n["cortisol"] > 0.50, "Дефицит серотонина при высоком кортизоле - хроническое негативное состояние"),
    (lambda n: n["acetylcholine"] > 0.75 and n["norepinephrine"] > 0.65, "Ацетилхолин и норадреналин - гиперфокус и тревожная бдительность"),
    (lambda n: n["dopamine"] > 0.55 and n["serotonin"] > 0.40, "Дофамин и серотонин - устойчивое позитивное состояние"),
    (lambda n: n["cortisol"] > 0.80 and n["norepinephrine"] > 0.70, "Кортизол и норадреналин - острая стрессовая реакция"),
    (lambda n: n["dopamine"] < 0.10 and n["serotonin"] < 0.10 and n["norepinephrine"] < 0.25, "Общее истощение нейромодуляторов - апатия и снижение всех функций"),
]

NEURO_SUMMARIES: dict[str, str] = {
    "ДОФАМИНОВОЕ ИСТОЩЕНИЕ": (
        "Кортизол подавляет выработку дофамина. Агент лишён мотивационного подкрепления - "
        "любые действия воспринимаются как бессмысленные."
    ),
    "СТРЕССОВАЯ АКТИВАЦИЯ": (
        "Норадреналин доминирует при подавленном дофамине. "
        "Характерно для состояния угрозы без вознаграждения: агент готов реагировать, "
        "но не мотивирован к продуктивным действиям."
    ),
    "ДОФАМИНОВЫЙ ПИК": (
        "Высокий дофамин при низком кортизоле. Агент находится в состоянии позитивного предвкушения "
        "и высокой мотивации."
    ),
    "СЕРОТОНИНОВЫЙ ДЕФИЦИТ": (
        "Низкий серотонин при высоком кортизоле. Агент лишён эмоциональной стабилизации, "
        "что усиливает негативный аффект."
    ),
    "ХОЛИНЕРГИЧЕСКАЯ АКТИВАЦИЯ": (
        "Высокий ацетилхолин при подавленном дофамине. Агент сфокусирован и внимателен, "
        "но без мотивационного компонента."
    ),
    "КОРТИЗОЛЬНЫЙ ПИК": (
        "Экстремально высокий кортизол подавляет большинство функций. "
        "Хронический стресс ускоряет сенесценцию и блокирует репродуктивную систему."
    ),
    "СБАЛАНСИРОВАННЫЙ ПРОФИЛЬ": (
        "Все нейромодуляторы в рабочем диапазоне без крайностей. "
        "Состояние оптимально для обучения и социализации."
    ),
    "ОБЩАЯ ДЕПРЕССИЯ": (
        "Все стимулирующие нейромодуляторы на минимуме. "
        "Агент в состоянии глубокого торможения."
    ),
    "ГИПЕРАКТИВАЦИЯ": (
        "Избыточная нейрохимическая активация через норадреналин и ацетилхолин. "
        "Агент истощает когнитивные ресурсы быстрее нормы."
    ),
    "СТАНДАРТНЫЙ": (
        "Нейромодуляторный профиль не выявил выраженного паттерна. Состояние умеренной активации."
    ),
}


def _get_nm_label(key: str, value: float) -> str:
    labels = NM_LABELS.get(key, {})
    if value > 0.65:
        return tr(labels.get("high", "высокий"))
    if value > 0.35:
        return tr(labels.get("moderate", "умеренный"))
    if value > 0.10:
        return tr(labels.get("low", "низкий"))
    return tr(labels.get("minimal", "минимальный"))


def interpret_neuro(neuromodulators: Mapping[str, Any] | None) -> NeuroProfile:
    """Interpret neuromodulator levels into a named profile."""

    source = _as_dict(neuromodulators or {})
    normalized = {key: _clamp(_safe_float(source.get(key, 0.0), 0.0)) for key in NEURO_KEYS}
    profile_label = "СТАНДАРТНЫЙ"
    for label, condition in NEURO_PROFILES:
        try:
            if condition(normalized):
                profile_label = label
                break
        except Exception:
            continue
    interactions: list[str] = []
    for condition, text in NM_INTERACTIONS:
        try:
            if condition(normalized):
                interactions.append(text)
        except Exception:
            continue
    return NeuroProfile(
        profile_label=tr(profile_label),
        summary=tr(_flat(NEURO_SUMMARIES.get(profile_label, NEURO_SUMMARIES["СТАНДАРТНЫЙ"]))),
        modulator_labels={key: _get_nm_label(key, normalized[key]) for key in NEURO_KEYS},
        interactions=[tr(text) for text in interactions],
    )


VALUE_ACTION_INTERPRETATIONS: dict[str, str] = {
    "eat": "агент устойчиво ориентирован на питание",
    "drink": "водный дефицит доминирует в решениях",
    "sleep": "усталость определяет приоритеты",
    "explore": "исследовательский мотив преобладает",
    "socialize": "социальная потребность в центре",
    "groom_self": "самоуход - текущая стратегия комфорта",
    "run_wheel": "физическая активность приоритетна",
    "hide": "агент в защитной стратегии",
    "play": "игровое поведение доминирует",
    "rest": "восстановление - текущий приоритет",
}


def _normalize_values(values: Mapping[str, Any]) -> dict[str, float]:
    numeric = {str(key): _safe_float(value, 0.0) for key, value in values.items() if str(key)}
    if not numeric:
        return {}
    min_value = min(numeric.values())
    max_value = max(numeric.values())
    if min_value >= 0.0 and max_value <= 1.0:
        return {key: _clamp(value) for key, value in numeric.items()}
    if max_value == min_value:
        return {key: 1.0 for key in numeric}
    span = max_value - min_value
    return {key: _clamp((value - min_value) / span) for key, value in numeric.items()}


def _snapshot_from_values(level: int, values: Mapping[str, Any]) -> ValueLayerSnapshot | None:
    normalized = _normalize_values(values)
    if not normalized:
        return None
    top_actions = sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:3]
    return ValueLayerSnapshot(level=max(0, int(level)), top_actions=top_actions, raw_values=normalized)


def _extract_from_layer_snapshots(raw_layers: Any) -> list[ValueLayerSnapshot]:
    layers: list[ValueLayerSnapshot] = []
    if isinstance(raw_layers, Mapping):
        raw_layers = raw_layers.get("layers", raw_layers.get("snapshots", []))
    if not isinstance(raw_layers, Sequence) or isinstance(raw_layers, (str, bytes)):
        return layers
    for index, raw_layer in enumerate(raw_layers):
        layer = _as_dict(raw_layer)
        if not layer:
            continue
        level = _safe_int(layer.get("level", layer.get("index", index)), index)
        values = _as_dict(layer.get("raw_values", layer.get("values", layer.get("action_values", {}))))
        if not values and isinstance(layer.get("top_actions"), Sequence):
            values = {str(action): value for action, value in layer.get("top_actions", [])}
        snapshot = _snapshot_from_values(level, values)
        if snapshot is not None:
            layers.append(snapshot)
    return layers


def _extract_from_action_values(action_values: Any) -> list[ValueLayerSnapshot]:
    source = _as_dict(action_values)
    if not source:
        return []
    per_level: dict[int, dict[str, float]] = {}
    for action, raw_levels in source.items():
        if isinstance(raw_levels, Mapping):
            for raw_level, value in raw_levels.items():
                level = _safe_int(str(raw_level).lstrip("Tt"), 0)
                per_level.setdefault(level, {})[action] = _safe_float(value, 0.0)
            continue
        if isinstance(raw_levels, Sequence) and not isinstance(raw_levels, (str, bytes)):
            for level, value in enumerate(raw_levels):
                per_level.setdefault(level, {})[action] = _safe_float(value, 0.0)
            continue
        per_level.setdefault(0, {})[action] = _safe_float(raw_levels, 0.0)
    layers: list[ValueLayerSnapshot] = []
    for level in sorted(per_level):
        snapshot = _snapshot_from_values(level, per_level[level])
        if snapshot is not None:
            layers.append(snapshot)
    return layers


def _extract_from_source_object(source: Any) -> dict[str, Any]:
    result = _as_dict(getattr(source, "value_layer_sources", {}))
    value_layer = getattr(source, "value_layer", None)
    if value_layer is not None:
        get_layer_snapshots = getattr(value_layer, "get_layer_snapshots", None)
        if callable(get_layer_snapshots) and "layer_snapshots" not in result:
            try:
                result["layer_snapshots"] = get_layer_snapshots()
            except Exception:
                pass
        if "action_values" not in result:
            result["action_values"] = getattr(value_layer, "action_values", {})
    thalamic_layer = getattr(source, "thalamic_layer", None)
    if thalamic_layer is not None and "thalamic_levels" not in result:
        result["thalamic_levels"] = getattr(thalamic_layer, "levels", [])
    if "value_history" not in result:
        result["value_history"] = getattr(source, "_value_history", [])
    thalamic_gate = getattr(source, "thalamic_gate", None)
    if thalamic_gate is not None and "thalamic_probabilities" not in result:
        result["thalamic_probabilities"] = getattr(thalamic_gate, "last_probabilities", {})
    return result


def extract_value_layers(source: Any) -> list[ValueLayerSnapshot]:
    """Extract value/thalamic snapshots from an inspector payload or agent-like object."""

    try:
        if bool(getattr(source, "is_deceased", False)):
            return []
        raw = _extract_from_source_object(source)
        for key in ("layer_snapshots", "thalamic_levels"):
            layers = _extract_from_layer_snapshots(raw.get(key))
            if layers:
                return layers
        layers = _extract_from_action_values(raw.get("action_values"))
        if layers:
            return layers
        history = raw.get("value_history")
        if isinstance(history, Sequence) and history and not isinstance(history, (str, bytes)):
            layers = _extract_from_layer_snapshots(history[-3:])
            if layers:
                return layers
        probabilities = _as_dict(raw.get("thalamic_probabilities"))
        snapshot = _snapshot_from_values(0, probabilities)
        return [snapshot] if snapshot is not None else []
    except Exception:
        return []


def extract_top_habits(cortex_patterns: Sequence[Mapping[str, Any]] | None, n: int = 5) -> list[HabitPattern]:
    """Return the strongest cortex patterns as habit dataclasses."""

    try:
        patterns = list(cortex_patterns or [])
        patterns.sort(key=lambda item: _safe_float(_as_dict(item).get("strength", 0.0), 0.0), reverse=True)
        habits: list[HabitPattern] = []
        for raw in patterns[:n]:
            item = _as_dict(raw)
            habits.append(
                HabitPattern(
                    context_tokens=_as_list_str(item.get("context_tokens", [])),
                    action=str(item.get("action", "")),
                    strength=_clamp(_safe_float(item.get("strength", 0.0), 0.0)),
                    activation_count=_safe_int(item.get("activation_count", item.get("source_experiences", 0)), 0),
                    consequence=str(item.get("consequence", "")),
                )
            )
        return habits
    except Exception:
        return []


def extract_significant_episodes(
    hippocampus_episodes: Sequence[Mapping[str, Any]] | None,
    n: int = 5,
) -> list[RecentEpisode]:
    """Return significant recent hippocampus episodes, with quiet episodes as filler."""

    try:
        episodes = [_as_dict(item) for item in list(hippocampus_episodes or [])]
        significant: list[dict[str, Any]] = []
        quiet: list[dict[str, Any]] = []
        for item in episodes:
            reward = _safe_float(item.get("reward", 0.0), 0.0)
            encoding = _safe_float(item.get("encoding_strength", 0.0), 0.0)
            if abs(reward) > 0.05 or encoding > 0.50:
                significant.append(item)
            else:
                quiet.append(item)
        significant.sort(key=lambda item: _safe_float(item.get("timestamp", 0.0), 0.0), reverse=True)
        quiet.sort(key=lambda item: _safe_float(item.get("timestamp", 0.0), 0.0), reverse=True)
        selected = (significant + quiet)[:n] if significant else quiet[:n]
        return [
            RecentEpisode(
                timestamp=_safe_float(item.get("timestamp", 0.0), 0.0),
                action=str(item.get("action", "")),
                context_tokens=_as_list_str(item.get("context_tokens", [])),
                reward=_safe_float(item.get("reward", 0.0), 0.0),
                consequence=str(item.get("consequence", "")),
                encoding_strength=_safe_float(item.get("encoding_strength", 0.0), 0.0),
            )
            for item in selected
        ]
    except Exception:
        return []


HABIT_PERSONALITY_MAP: list[tuple[list[str], str]] = [
    (["hide", "rest"], "ТРЕВОЖНЫЙ ОДИНОЧКА"),
    (["eat", "drink"], "РЕСУРСНЫЙ ПРАГМАТИК"),
    (["socialize", "play", "allogroom"], "СОЦИАЛЬНЫЙ АГЕНТ"),
    (["explore", "run_wheel"], "ИССЛЕДОВАТЕЛЬ"),
    (["sleep", "rest"], "ПАССИВНЫЙ"),
    (["groom_self", "rest", "hide"], "ЗАМКНУТЫЙ"),
]

PERSONALITY_SUMMARIES: dict[str, str] = {
    "ТРЕВОЖНЫЙ ОДИНОЧКА": (
        "Агент выработал стратегию выживания через избегание контактов и укрытие. "
        "Хронический стресс подавил любопытство и социальные мотивы. "
        "Паттерны питания и укрытия доминируют над всеми другими."
    ),
    "РЕСУРСНЫЙ ПРАГМАТИК": (
        "Поведение агента максимально ориентировано на ресурсы. "
        "Социальные взаимодействия происходят только когда не конкурируют с добычей еды. "
        "Стратегия стабильная, но ограниченная."
    ),
    "СОЦИАЛЬНЫЙ АГЕНТ": (
        "Агент сформировал выраженные социальные паттерны. "
        "Взаимодействия с колонией являются главным источником подкрепления. "
        "Высокий вклад в социальную сплочённость группы."
    ),
    "ИССЛЕДОВАТЕЛЬ": (
        "Паттерны исследования и физической активности доминируют. "
        "Агент активно картирует клетку и тестирует новые стратегии. "
        "Когнитивная активность повышена."
    ),
    "ПАССИВНЫЙ": (
        "Поведенческий репертуар агента сужен до минимума. "
        "Сон и отдых занимают большую часть активного времени. "
        "Это может быть признаком хронического истощения."
    ),
    "ЗАМКНУТЫЙ": (
        "Агент избегает контактов через самоизоляцию и самоуход. "
        "Набор привычек стабилен, но почти не включает социальную компоненту."
    ),
    "НЕОПРЕДЕЛЁННЫЙ": (
        "Достаточно данных для определения устойчивого характера не обнаружено. "
        "Агент ещё формирует поведенческий репертуар."
    ),
}


def build_personality_readout(
    habits: Sequence[HabitPattern],
    affect: AffectInterpretation,
    neuro: NeuroProfile,
) -> PersonalityReadout:
    """Build a compact personality readout from habits, affect and neuroprofile."""

    try:
        dominant_actions = [habit.action for habit in list(habits)[:3] if habit.action]
        for actions, label in HABIT_PERSONALITY_MAP:
            if any(action in dominant_actions for action in actions):
                return PersonalityReadout(tr(label), tr(_flat(PERSONALITY_SUMMARIES[label])))
        affect_id = tone_id(affect.tone_label)
        neuro_id = profile_id(neuro.profile_label)
        if affect_id in {"panic", "acute_stress", "chronic_anxiety"}:
            label = "ТРЕВОЖНЫЙ ОДИНОЧКА"
        elif affect_id == "curiosity" or neuro_id == "da_peak":
            label = "ИССЛЕДОВАТЕЛЬ"
        elif affect_id == "attachment":
            label = "СОЦИАЛЬНЫЙ АГЕНТ"
        elif affect_id == "fatigue":
            label = "ПАССИВНЫЙ"
        else:
            label = "НЕОПРЕДЕЛЁННЫЙ"
        return PersonalityReadout(tr(label), tr(_flat(PERSONALITY_SUMMARIES[label])))
    except Exception:
        return PersonalityReadout(tr("НЕОПРЕДЕЛЁННЫЙ"), tr(_flat(PERSONALITY_SUMMARIES["НЕОПРЕДЕЛЁННЫЙ"])))


def reward_label(reward: float) -> tuple[str, tuple[int, int, int]]:
    """Return display text and color for a reward value."""

    value = _safe_float(reward, 0.0)
    if value > 0.30:
        return (f"R=+{value:.2f} ✓", (70, 150, 75))
    if value > 0.05:
        return (f"R=+{value:.2f}", (100, 170, 110))
    if value < -0.20:
        return (f"R={value:.2f} ✗", (180, 75, 60))
    if value < -0.05:
        return (f"R={value:.2f}", (200, 110, 90))
    return (f"R={value:.2f}", (130, 120, 110))


def build_nowa_interpretation(data: Any) -> NowaInterpretation:
    """Build a full NOWA interpretation from an inspector payload without raising."""

    try:
        affect = interpret_affect(getattr(data, "affective_axes", {}))
    except Exception:
        affect = interpret_affect({})
    try:
        neuro = interpret_neuro(getattr(data, "neuromodulators", {}))
    except Exception:
        neuro = interpret_neuro({})
    try:
        value_layers = extract_value_layers(data)
    except Exception:
        value_layers = []
    try:
        habits = extract_top_habits(getattr(data, "cortex_patterns_detail", []))
    except Exception:
        habits = []
    try:
        recent_episodes = extract_significant_episodes(getattr(data, "hippocampus_episodes", []))
    except Exception:
        recent_episodes = []
    try:
        personality = build_personality_readout(habits, affect, neuro)
    except Exception:
        personality = PersonalityReadout("НЕОПРЕДЕЛЁННЫЙ", PERSONALITY_SUMMARIES["НЕОПРЕДЕЛЁННЫЙ"])
    return NowaInterpretation(
        affect=affect,
        neuro=neuro,
        value_layers=value_layers,
        habits=habits,
        recent_episodes=recent_episodes,
        personality=personality,
    )


__all__ = [
    "AFFECT_TONES",
    "AXIS_COLORS",
    "SECTION_LINE_COLOR",
    "SECTION_TITLE_COLOR",
    "TONE_BADGE_COLORS",
    "AffectInterpretation",
    "HabitPattern",
    "NeuroProfile",
    "NowaInterpretation",
    "PersonalityReadout",
    "RecentEpisode",
    "ValueLayerSnapshot",
    "build_nowa_interpretation",
    "build_personality_readout",
    "extract_significant_episodes",
    "extract_top_habits",
    "extract_value_layers",
    "get_axis_label",
    "interpret_affect",
    "interpret_neuro",
    "reward_label",
]
