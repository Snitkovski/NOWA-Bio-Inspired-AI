"""Agent inspector data builders and overlay renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from death_registry import AgentMemorial
from .i18n import get_language, has_label, label as ui_label, tr
from .genome_portrait import (
    GENE_REGISTRY,
    LINEAGE_GENE_LABELS_RU,
    LINEAGE_TRACKED_GENES,
    TRAIT_LABELS_RU,
    GenomePortrait,
    analyze_trend,
    build_lineage_trend,
    build_portrait,
    describe_lineage_trend,
    wrap_text,
)
from .nowa_interpreter import (
    AXIS_COLORS,
    SECTION_LINE_COLOR,
    SECTION_TITLE_COLOR,
    NowaInterpretation,
    build_nowa_interpretation,
    get_axis_label,
    reward_label,
)

INSPECTOR_WIDTH = 500
INSPECTOR_HEIGHT = 620
_TAB_KEYS = ["nowa", "social", "repro", "genome", "history"]

INSPECTOR_BG = (245, 239, 229, 245)
INSPECTOR_HEADER = (220, 210, 195)
TAB_ACTIVE = (200, 188, 170)
TAB_INACTIVE = (232, 224, 212)
TAB_TEXT_ACTIVE = (35, 28, 20)
TAB_TEXT_INACTIVE = (100, 88, 70)
INSPECTOR_DECEASED_TINT = (210, 205, 200, 245)
INSPECTOR_BORDER = (120, 105, 85)
INSPECTOR_TEXT = (35, 28, 20)
INSPECTOR_MUTED_TEXT = (110, 100, 90)
BAR_BG = (211, 200, 185)
BAR_FG = (103, 148, 195)
SCROLL_TRACK = (214, 204, 190)
SCROLL_THUMB = (156, 140, 118)
BAR_W = 130
BAR_H = 8
LINK_TEXT = (56, 102, 156)
LINK_TEXT_HOVER = (36, 77, 126)
DETAIL_BG = (246, 241, 233, 250)
DETAIL_HEADER = (226, 216, 201)
DETAIL_BORDER = (124, 108, 88)
DETAIL_LINE = (70, 60, 50)
MEMORY_DETAIL_BUILD_LIMIT = 220
MEMORY_DETAIL_SHOW_LIMIT = 80

_MEMORY_LINK_KEYS = {"hippocampus_size", "cortex_patterns"}
_SIGNATURE_ACTION_PREFIX = "action:"
_SIGNATURE_CONSEQUENCE_PREFIX = "consequence:"

_AFFECT_KEYS = [
    "stress",
    "valence",
    "arousal",
    "attachment",
    "curiosity",
    "trust",
    "dominance",
]

_AFFECT_LABELS_RU: dict[str, str] = {
    "stress": "стресс",
    "valence": "валентность",
    "arousal": "возбуждение",
    "attachment": "привязанность",
    "curiosity": "любопытство",
    "trust": "доверие",
    "dominance": "доминантность",
    "energy": "энергия",
    "social_drive": "соц. потребность",
}

_NEURO_LABELS_RU: dict[str, str] = {
    "dopamine": "дофамин",
    "serotonin": "серотонин",
    "norepinephrine": "норадреналин",
    "cortisol": "кортизол",
    "acetylcholine": "ацетилхолин",
}

_WAKE_LABELS_RU: dict[str, str] = {
    "wakefulness": "бодрствование",
    "sleep_pressure": "давление сна",
    "circadian": "циркадный ритм",
    "alertness": "бдительность",
}

_MEMORY_LABELS_RU: dict[str, str] = {
    "lived_steps": "прожито шагов",
    "hippocampus_size": "гиппокамп (эпизоды)",
    "cortex_patterns": "корковые паттерны",
    "td_error": "TD-ошибка",
}

_RELATIONSHIP_LABELS_RU: dict[str, str] = {
    "stranger": "незнакомец",
    "acquaintance": "знакомый",
    "bonded": "связанный",
    "rival": "соперник",
    "mate": "партнёр",
    "kin": "родня",
    "archived": "архив",
}

_OUTCOME_LABELS_RU: dict[str, str] = {
    "accepted": "принято",
    "completed": "завершено",
    "rejected": "отклонено",
    "timeout": "таймаут",
    "interrupted": "прервано",
}

_ACTION_LABELS_RU: dict[str, str] = {
    "explore": "исследует",
    "eat": "ест",
    "drink": "пьёт",
    "sleep": "спит",
    "groom_self": "ухаживает за собой",
    "run_wheel": "бежит в колесе",
    "hide": "прячется",
    "socialize": "общается",
    "play": "играет",
    "allogroom": "взаимный груминг",
    "play_invite": "приглашение к игре",
    "share_knowledge": "обмен знанием",
    "chase": "преследование",
    "sleep_together": "сон вместе",
    "mount_display": "брачное поведение",
    "nurse": "ухаживает за детёнышем",
    "rest": "отдыхает",
    "idle": "бездействует",
    "dead": "мертв",
    "sniff_greet": "обнюхивание-приветствие",
}

_ZONE_LABELS_RU: dict[str, str] = {
    "floor": "пол",
    "corner": "угол",
    "litter": "лоток",
    "toy": "игрушка",
    "object": "объект",
    "house": "домик",
    "dustbath": "купалка",
    "waterer": "поилка",
    "bowl_pellets": "миска с гранулами",
    "bowl_hay": "миска с сеном",
    "mineral": "минеральный камень",
    "wheel": "колесо",
    "shelf_lower": "нижняя полка",
    "shelf_mid": "средняя полка",
    "shelf_upper": "верхняя полка",
    "bars": "прутья",
    "bars_top": "верх прутьев",
    "door": "дверь",
    "current": "текущая позиция",
}

_CONTEXT_LABELS_RU: dict[str, str] = {
    "food_critical": "критически мало еды",
    "food_low": "мало еды",
    "food_ok": "еды достаточно",
    "water_critical": "критически мало воды",
    "stranger_nearby": "рядом незнакомец",
    "alarm_call": "тревожный сигнал",
    "pregnant": "беременна",
    "estrus": "эструс",
    "juvenile": "ювенильный возраст",
    "high_stress": "высокий стресс",
    "bored": "скука",
    "hunger_high": "высокий голод",
    "hunger_critical": "критический голод",
    "thirst_high": "высокая жажда",
    "thirst_critical": "критическая жажда",
    "wakefulness_high": "высокая сонливость",
    "wakefulness_critical": "критическая сонливость",
}

_CONSEQUENCE_LABELS_RU: dict[str, str] = {
    "none": "без последствий",
    "success": "успех",
    "failure": "неудача",
    "accepted": "принято",
    "rejected": "отклонено",
    "completed": "завершено",
}

_LINEAGE_TOKEN_PATTERN = re.compile(r"^G[0-9]+A[0-9]+(?:S[MFU])?$", re.IGNORECASE)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return float(default)
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return float(default)
    return parsed


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _safe_parents(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, (list, tuple)):
        return (None, None)
    raw = list(value)
    if len(raw) < 2:
        raw += [None] * (2 - len(raw))
    left = None if raw[0] in (None, "") else _safe_str(raw[0], "")
    right = None if raw[1] in (None, "") else _safe_str(raw[1], "")
    return (left, right)


def _safe_dict_floats(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {_safe_str(key, ""): _safe_float(item, 0.0) for key, item in value.items()}


def _safe_list_str(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value:
        text = _safe_str(item, "")
        if text:
            out.append(text)
    return out


def _extract_value_layer_sources(agent: Any) -> dict[str, Any]:
    """Collect serializable NOWA value sources without retaining the live agent."""

    sources: dict[str, Any] = {}
    value_layer = getattr(agent, "value_layer", None)
    if value_layer is not None:
        get_layer_snapshots = getattr(value_layer, "get_layer_snapshots", None)
        if callable(get_layer_snapshots):
            try:
                sources["layer_snapshots"] = get_layer_snapshots()
            except Exception:
                pass
        try:
            action_values = getattr(value_layer, "action_values", None)
            if isinstance(action_values, dict):
                sources["action_values"] = dict(action_values)
        except Exception:
            pass

    thalamic_layer = getattr(agent, "thalamic_layer", None)
    if thalamic_layer is not None:
        try:
            levels = getattr(thalamic_layer, "levels", None)
            if isinstance(levels, (list, tuple)):
                sources["thalamic_levels"] = list(levels)
        except Exception:
            pass

    try:
        value_history = getattr(agent, "_value_history", None)
        if isinstance(value_history, (list, tuple)):
            sources["value_history"] = list(value_history[-5:])
    except Exception:
        pass

    thalamic_gate = getattr(agent, "thalamic_gate", None)
    if thalamic_gate is not None:
        try:
            probabilities = getattr(thalamic_gate, "last_probabilities", None)
            if isinstance(probabilities, dict):
                sources["thalamic_probabilities"] = dict(probabilities)
        except Exception:
            pass

    return sources


def _episode_to_dict(episode: Any, known: Any, name_registry: Any | None = None) -> dict[str, Any]:
    known_id = _safe_str(getattr(known, "agent_id", ""), "")
    # Resolve human-readable name exclusively from the birth registry when available.
    with_name = ""
    try:
        if name_registry is not None and known_id:
            with_name = name_registry.get_human_name(known_id) or ""
    except Exception:
        with_name = ""
    if not with_name:
        with_name = known_id

    return {
        "time": _safe_float(getattr(episode, "time", 0.0), 0.0),
        "type": _safe_str(getattr(episode, "interaction_type", "social"), "social"),
        "with_agent_id": known_id,
        "with_name": with_name,
        "outcome": _safe_str(getattr(episode, "outcome", ""), ""),
        "affect_delta": _safe_float(getattr(episode, "affect_delta", 0.0), 0.0),
        "context": _safe_str(getattr(episode, "context", ""), ""),
        "initiated_by": _safe_str(getattr(episode, "initiated_by", ""), ""),
    }


def _extract_signature_tokens(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, dict):
        raw_signature = value.get("signature")
        if raw_signature is not None:
            return _extract_signature_tokens(raw_signature)

        tokens: list[str] = []
        context_signature = _safe_str(value.get("context_signature", ""), "")
        if context_signature:
            for token in context_signature.split("|"):
                parsed = _safe_str(token, "").strip()
                if parsed:
                    tokens.append(parsed)

        action = _safe_str(value.get("action", ""), "")
        if action:
            tokens.append(f"{_SIGNATURE_ACTION_PREFIX}{action}")
        return tokens

    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            token = _safe_str(item, "").strip()
            if token:
                out.append(token)
        return out

    if hasattr(value, "signature"):
        try:
            signature = getattr(value, "signature")()
        except Exception:
            signature = []
        return _extract_signature_tokens(signature)

    token = _safe_str(value, "").strip()
    if token:
        return [token]
    return []


def _split_signature_tokens(tokens: list[str]) -> tuple[list[str], str, str]:
    context_tokens: list[str] = []
    action = ""
    consequence = ""
    for token in list(tokens or []):
        text = _safe_str(token, "").strip()
        if not text:
            continue
        if text.startswith(_SIGNATURE_ACTION_PREFIX):
            candidate = _safe_str(text[len(_SIGNATURE_ACTION_PREFIX) :], "").strip()
            if candidate:
                action = candidate
            continue
        if text.startswith(_SIGNATURE_CONSEQUENCE_PREFIX):
            candidate = _safe_str(text[len(_SIGNATURE_CONSEQUENCE_PREFIX) :], "").strip()
            if candidate:
                consequence = candidate
            continue
        context_tokens.append(text)
    return (context_tokens, action, consequence)


def _humanize_raw_phrase(value: Any) -> str:
    text = _safe_str(value, "").strip()
    if not text:
        return ""
    return text.replace("_", " ")


def _humanize_action(value: Any) -> str:
    raw = _safe_str(value, "").strip()
    if not raw:
        return "-"
    key = raw.lower()
    if has_label("action", key):
        return ui_label("action", key)
    return _humanize_raw_phrase(raw)


def _humanize_zone(value: Any) -> str:
    raw = _safe_str(value, "").strip()
    if not raw:
        return tr("неизвестно")
    key = raw.lower()
    if has_label("zone", key):
        return ui_label("zone", key)
    return _humanize_raw_phrase(raw)


def _humanize_consequence(value: Any) -> str:
    raw = _safe_str(value, "").strip()
    if not raw:
        return "-"
    key = raw.lower()
    if has_label("consequence", key):
        return ui_label("consequence", key)
    if has_label("outcome", key):
        return ui_label("outcome", key)
    if key.startswith("feedback:"):
        payload = raw.split(":", 1)[1].strip()
        parsed = _safe_float(payload, float("nan"))
        if parsed == parsed:
            return tr("обратная связь {value}").format(value=f"{parsed:+.2f}")
        if payload:
            return tr("обратная связь {value}").format(value=payload)
        return tr("обратная связь")
    if ":" in raw:
        prefix, rest = raw.split(":", 1)
        p = prefix.strip().lower()
        r = rest.strip()
        if p == "zone":
            return tr("зона: {name}").format(name=_humanize_zone(r))
        if p == "action":
            return tr("действие: {name}").format(name=_humanize_action(r))
        if p == "consequence":
            return tr("последствие: {name}").format(name=_humanize_consequence(r))
        if p == "social_contact":
            count = _safe_int(r, 0)
            if count > 0:
                return tr("социальных контактов рядом: {n}").format(n=count)
            return tr("социальный контакт рядом")
        if p == "feedback":
            return _humanize_consequence(raw)
        if r:
            return f"{_humanize_raw_phrase(prefix)}: {_humanize_raw_phrase(r)}"
        return _humanize_raw_phrase(prefix)
    return _humanize_raw_phrase(raw)


def _humanize_context_token(value: Any) -> str:
    raw = _safe_str(value, "").strip()
    if not raw:
        return ""
    key = raw.lower()
    if has_label("context", key):
        return ui_label("context", key)
    if has_label("action", key):
        return ui_label("action", key)
    if has_label("outcome", key):
        return ui_label("outcome", key)
    if has_label("consequence", key):
        return ui_label("consequence", key)
    if ":" not in raw:
        return _humanize_raw_phrase(raw)

    prefix, rest = raw.split(":", 1)
    p = prefix.strip().lower()
    r = rest.strip()
    if p == "zone":
        return tr("зона: {name}").format(name=_humanize_zone(r))
    if p == "action":
        return tr("действие: {name}").format(name=_humanize_action(r))
    if p == "consequence":
        return tr("последствие: {name}").format(name=_humanize_consequence(r))
    if p == "social_contact":
        count = _safe_int(r, 0)
        if count > 0:
            return tr("социальных контактов рядом: {n}").format(n=count)
        return tr("социальный контакт рядом")
    if p == "feedback":
        return _humanize_consequence(raw)
    if r:
        return f"{_humanize_raw_phrase(prefix)}: {_humanize_raw_phrase(r)}"
    return _humanize_raw_phrase(prefix)


def _humanize_context_tokens(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in list(values or []):
        text = _humanize_context_token(value)
        if text:
            out.append(text)
    return out


def _episode_memory_to_dict(index: int, episode: Any) -> dict[str, Any]:
    signature_tokens = _extract_signature_tokens(getattr(episode, "path", None))
    context_tokens, action_from_signature, consequence_from_signature = _split_signature_tokens(signature_tokens)
    consequence_obj = getattr(episode, "consequence", None)
    consequence = _safe_str(getattr(consequence_obj, "name", ""), "")
    if not consequence:
        consequence = consequence_from_signature
    action = _safe_str(getattr(episode, "replay_action_id", ""), "")
    if not action:
        action = action_from_signature

    return {
        "index": _safe_int(index, 0),
        "timestamp": _safe_float(getattr(episode, "timestamp", 0.0), 0.0),
        "action": action,
        "consequence": consequence,
        "context_tokens": context_tokens,
        "intensity": _safe_float(getattr(episode, "intensity", 0.0), 0.0),
        "reward": _safe_float(getattr(episode, "reward", 0.0), 0.0),
        "encoding_strength": _safe_float(getattr(episode, "encoding_strength", 0.0), 0.0),
        "reinforcement_count": _safe_int(getattr(episode, "reinforcement_count", 0), 0),
        "activation_energy": _safe_float(getattr(episode, "activation_energy", 0.0), 0.0),
        "stability": _safe_float(getattr(episode, "stability", 0.0), 0.0),
        "replay_priority": _safe_float(getattr(episode, "replay_priority", 0.0), 0.0),
        "consolidation_weight": _safe_float(getattr(episode, "consolidation_weight", 0.0), 0.0),
        "prediction_shock": bool(getattr(episode, "prediction_shock_flag", False)),
    }


def _pattern_memory_to_dict(index: int, pattern: Any) -> dict[str, Any]:
    if isinstance(pattern, dict):
        signature_tokens = _extract_signature_tokens(pattern)
        raw_strength = pattern.get("strength", 0.0)
        raw_source = pattern.get("source_experiences", pattern.get("reinforcement_count", 0))
        raw_activation = pattern.get("activation_count", pattern.get("reinforcement_count", 0))
        raw_created_at = pattern.get("created_at", 0.0)
        raw_last_activated = pattern.get("last_activated", 0.0)
    else:
        signature_tokens = _extract_signature_tokens(getattr(pattern, "signature", pattern))
        raw_strength = getattr(pattern, "strength", 0.0)
        raw_source = getattr(pattern, "source_experiences", 0)
        raw_activation = getattr(pattern, "activation_count", 0)
        raw_created_at = getattr(pattern, "created_at", 0.0)
        raw_last_activated = getattr(pattern, "last_activated", 0.0)

    context_tokens, action, consequence = _split_signature_tokens(signature_tokens)
    return {
        "index": _safe_int(index, 0),
        "context_tokens": context_tokens,
        "action": action,
        "consequence": consequence,
        "signature_tokens": signature_tokens,
        "strength": _safe_float(raw_strength, 0.0),
        "source_experiences": _safe_int(raw_source, 0),
        "activation_count": _safe_int(raw_activation, 0),
        "created_at": _safe_float(raw_created_at, 0.0),
        "last_activated": _safe_float(raw_last_activated, 0.0),
    }


def _safe_mean(values: Any) -> float:
    if not isinstance(values, (list, tuple)):
        return 0.0
    items = [_safe_float(item, 0.0) for item in values]
    if not items:
        return 0.0
    return float(sum(items) / len(items))


def _resolve_offspring_display_names(agent: Any, knowledge: dict[str, Any], name_registry: Any | None = None) -> list[str]:
    """Return human-readable offspring labels using only the birth registry."""
    offspring_ids = _safe_list_str(getattr(agent, "own_offspring", []))
    if not offspring_ids:
        return []

    display_names: list[str] = []
    for child_id in offspring_ids:
        # Prefer the authoritative birth registry name. Do not synthesize
        # canonical names here — registry is the single source of truth.
        name = ""
        try:
            if name_registry is not None and child_id:
                name = name_registry.get_human_name(child_id) or ""
        except Exception:
            name = ""
        if name:
            display_names.append(name)
            continue

        display_names.append(child_id)
    return display_names


def _bool_ru(value: Any) -> str:
    return tr("да") if bool(value) else tr("нет")


def _relationship_ru(value: Any) -> str:
    key = _safe_str(value, "")
    return ui_label("relationship", key, tr("неизвестно") if not key else key)


def _outcome_ru(value: Any) -> str:
    key = _safe_str(value, "")
    return ui_label("outcome", key, tr("неизвестно") if not key else key)


def _lineage_rows_from_lineage_id(lineage_id: Any) -> list[str]:
    raw = _safe_str(lineage_id, "").strip()
    if not raw:
        return []

    normalized = raw.replace("X", "x")
    raw_parts = [part.strip() for part in normalized.split("x")]
    # First, collect valid tokens (upper-cased) while respecting truncation rules.
    tokens: list[str] = []
    for idx, part in enumerate(raw_parts):
        token = _safe_str(part, "").strip()
        if not token:
            continue
        token_up = token.upper()
        if _LINEAGE_TOKEN_PATTERN.match(token_up):
            tokens.append(token_up)
            continue
        # lineage_id in genome is hard-capped, so tail can be truncated mid-token.
        if idx == len(raw_parts) - 1 and len(normalized) >= 64:
            continue
        if len(token_up) < 3:
            continue
        tokens.append(token_up)

    if not tokens:
        return []

    # Group tokens in pairs to represent parental pairs per generation.
    rows: list[str] = []
    i = 0
    while i < len(tokens):
        left = tokens[i]
        right = tokens[i + 1] if i + 1 < len(tokens) else None
        if right:
            rows.append(f"{left} × {right}")
        else:
            rows.append(left)
        i += 2
    return rows


def _build_parent_lineage_rows(agent: Any, name_registry: Any | None = None) -> list[str]:
    parent_ids = [item for item in _safe_parents(getattr(agent, "parents", (None, None))) if item]
    if not parent_ids:
        return []

    colony = getattr(agent, "colony", None)
    if not isinstance(colony, list) or not colony:
        return []

    by_id: dict[str, Any] = {}
    for member in colony:
        member_id = _safe_str(getattr(member, "agent_id", ""), "")
        if member_id:
            by_id[member_id] = member
    if not by_id:
        return []

    try:
        from .utils import build_generation_index_map
    except Exception:
        return []

    index_map = build_generation_index_map(by_id.values())
    rows: list[str] = []
    current_ids = [_safe_str(pid, "").strip() for pid in parent_ids if _safe_str(pid, "").strip()]
    visited_frontiers: set[tuple[str, ...]] = set()
    max_depth = max(1, _safe_int(getattr(agent, "generation", 0), 0) + 2)
    depth = 0
    while current_ids and depth < max_depth:
        frontier = tuple(current_ids)
        if frontier in visited_frontiers:
            break
        visited_frontiers.add(frontier)

        labels: list[str] = []
        next_ids_raw: list[str] = []
        for parent_id in current_ids:
            parent = by_id.get(parent_id)
            # Prefer the authoritative birth registry name when provided.
            label = ""
            if name_registry is not None and parent_id:
                try:
                    label = name_registry.get_human_name(parent_id) or ""
                except Exception:
                    label = ""

            # If registry is not provided (e.g., in tests), fall back to the
            # in-memory parent's `name` when the parent object exists.
            if not label:
                if parent is not None:
                    label = _safe_str(getattr(parent, "name", ""), "") or parent_id
                else:
                    label = parent_id

            labels.append(label.upper())

            # Only walk grandparents if we have the parent object available
            if parent is None:
                continue
            for grandparent_id in _safe_parents(getattr(parent, "parents", (None, None))):
                gp = _safe_str(grandparent_id, "").strip()
                if gp:
                    next_ids_raw.append(gp)

        if not labels:
            break
        rows.append(" × ".join(labels))

        next_ids: list[str] = []
        seen_next: set[str] = set()
        for item in next_ids_raw:
            if item in seen_next:
                continue
            seen_next.add(item)
            next_ids.append(item)
        current_ids = next_ids
        depth += 1
    return rows


def _resolve_genome_lineage_rows_for_agent(agent: Any, lineage_id: Any, name_registry: Any | None = None) -> list[str]:
    rows = _build_parent_lineage_rows(agent, name_registry=name_registry)
    if rows:
        return rows
    return _lineage_rows_from_lineage_id(lineage_id)


@dataclass
class InspectorData:
    """Normalized payload for AgentInspectorOverlay."""

    agent_id: str
    display_name: str
    is_deceased: bool

    sex: str
    generation: int
    parents: tuple[str | None, str | None]
    age: float
    lived_steps: int
    cause_of_death: str

    affective_axes: dict[str, float] = field(default_factory=dict)
    neuromodulators: dict[str, float] = field(default_factory=dict)
    wakefulness: dict[str, float] = field(default_factory=dict)
    autonomous_drives: dict[str, float] = field(default_factory=dict)
    memory: dict[str, float | int] = field(default_factory=dict)
    hippocampus_episodes: list[dict[str, Any]] = field(default_factory=list)
    cortex_patterns_detail: list[dict[str, Any]] = field(default_factory=list)
    value_layer_sources: dict[str, Any] = field(default_factory=dict)
    nowa_interpretation: NowaInterpretation | None = None

    known_agents: list[dict[str, Any]] = field(default_factory=list)
    hearsay_received: int = 0
    hearsay_sent: int = 0

    sex_specific: dict[str, Any] = field(default_factory=dict)
    reproductive_drive: float = 0.0
    cooldown_steps: int = 0
    total_offspring_count: int = 0
    own_offspring_ids: list[str] = field(default_factory=list)
    vitality: float = 0.0
    senescence_rate: float = 0.0

    genome_genes: dict[str, float] = field(default_factory=dict)
    genome_generation: int = 0
    genome_lineage_id: str = ""
    genome_lineage_rows: list[str] = field(default_factory=list)
    genome_inheritance_meta: dict[str, Any] = field(default_factory=dict)
    genome_portrait: GenomePortrait | None = None

    recent_interactions: list[dict[str, Any]] = field(default_factory=list)


def build_inspector_data_from_agent(
    agent: Any,
    display_name: str,
    name_registry: Any | None = None,
    death_registry: Any | None = None,
    generation_index_map: dict[str, int] | None = None,
) -> InspectorData:
    """Build robust inspector payload from a living agent.

    Names in the inspector must come exclusively from `name_registry` when
    provided. If a name is not recorded, the id is used as a fallback.
    """

    affective_axes = getattr(getattr(agent, "affective_space", None), "axes", {}) or {}
    neuromodulators = getattr(agent, "neuromodulators", None)
    wakefulness = getattr(agent, "wakefulness", None)
    runtime = getattr(agent, "autonomous_runtime", None)
    drive_system = getattr(runtime, "drive_system", None)
    energy_system = getattr(runtime, "energy_system", None)
    reproductive = getattr(agent, "reproductive_system", None)
    mortality = getattr(agent, "mortality_system", None)
    heat_cycle = getattr(agent, "heat_cycle", None)
    genome = getattr(agent, "genome", None)
    knowledge = getattr(agent, "knowledge", {}) or {}
    if not isinstance(knowledge, dict):
        knowledge = {}

    known_agents: list[dict[str, Any]] = []
    all_interactions: list[dict[str, Any]] = []
    hearsay_received = 0
    hearsay_sent = 0
    for known in knowledge.values():
        interactions = list(getattr(known, "interaction_history", []) or [])
        hearsay = list(getattr(known, "hearsay", []) or [])
        hearsay_received += len(hearsay)
        hearsay_sent += sum(1 for item in hearsay if _safe_str(getattr(item, "source_id", ""), "") == str(getattr(agent, "agent_id", "")))
        known_id = _safe_str(getattr(known, "agent_id", ""), "")
        try:
            known_name = ""
            if name_registry is not None and known_id:
                known_name = name_registry.get_human_name(known_id) or ""
        except Exception:
            known_name = ""
        if not known_name:
            known_name = known_id
        known_agents.append(
            {
                "agent_id": known_id,
                "name": known_name,
                "relationship_type": _safe_str(getattr(known, "relationship_type", "stranger"), "stranger"),
                "affinity": _safe_float(getattr(known, "affinity", 0.0), 0.0),
                "familiarity": _safe_float(getattr(known, "familiarity", 0.0), 0.0),
                "trust": _safe_float(getattr(known, "trust", 0.0), 0.0),
                "positive_count": _safe_int(getattr(known, "positive_count", 0), 0),
                "negative_count": _safe_int(getattr(known, "negative_count", 0), 0),
                "interactions": len(interactions),
            }
        )
        for episode in interactions:
            all_interactions.append(_episode_to_dict(episode, known, name_registry=name_registry))

    all_interactions.sort(key=lambda item: _safe_float(item.get("time", 0.0), 0.0), reverse=True)
    known_agents.sort(key=lambda item: _safe_float(item.get("affinity", 0.0), 0.0), reverse=True)
    hippocampus = getattr(agent, "hippocampus", None)
    cortex = getattr(agent, "cortex", None)
    raw_episodes = list(getattr(hippocampus, "experiences", []) or [])
    raw_patterns = list(getattr(cortex, "patterns", []) or [])
    episode_start = max(0, len(raw_episodes) - MEMORY_DETAIL_BUILD_LIMIT)
    pattern_start = max(0, len(raw_patterns) - MEMORY_DETAIL_BUILD_LIMIT)
    hippocampus_episodes = [
        _episode_memory_to_dict(index, episode)
        for index, episode in enumerate(raw_episodes[episode_start:], start=episode_start + 1)
    ]
    cortex_patterns_detail = [
        _pattern_memory_to_dict(index, pattern)
        for index, pattern in enumerate(raw_patterns[pattern_start:], start=pattern_start + 1)
    ]

    genome_genes = _safe_dict_floats(getattr(genome, "genes", {}) or {})
    genome_inheritance_meta = dict(getattr(agent, "genome_inheritance_meta", {}) or {})
    portrait = None
    if genome_genes:
        try:
            portrait = build_portrait(genome_genes, genome_inheritance_meta, display_name=display_name)
            trend = build_lineage_trend(agent, death_registry, generation_index_map or {})
            if trend is not None:
                portrait.lineage_trend = trend
        except Exception:
            portrait = None
    inspector_data = InspectorData(
        agent_id=_safe_str(getattr(agent, "agent_id", ""), ""),
        display_name=_safe_str(display_name, ""),
        is_deceased=False,
        sex=_safe_str(getattr(agent, "sex", ""), ""),
        generation=_safe_int(getattr(agent, "generation", 0), 0),
        parents=_safe_parents(getattr(agent, "parents", (None, None))),
        age=_safe_float(getattr(agent, "age", 0.0), 0.0),
        lived_steps=_safe_int(getattr(agent, "lived_steps", 0), 0),
        cause_of_death="",
        affective_axes={
            key: _safe_float(affective_axes.get(key, 0.0), 0.0) for key in _AFFECT_KEYS
        }
        | {
            "energy": _safe_float(getattr(agent, "energy", 0.0), 0.0),
            "social_drive": _safe_float(getattr(agent, "social_drive", 0.0), 0.0),
        },
        neuromodulators={
            "dopamine": _safe_float(getattr(neuromodulators, "dopamine", 0.0), 0.0),
            "serotonin": _safe_float(getattr(neuromodulators, "serotonin", 0.0), 0.0),
            "norepinephrine": _safe_float(getattr(neuromodulators, "norepinephrine", 0.0), 0.0),
            "cortisol": _safe_float(getattr(neuromodulators, "cortisol", 0.0), 0.0),
            "acetylcholine": _safe_float(getattr(neuromodulators, "acetylcholine", 0.0), 0.0),
        },
        wakefulness={
            "wakefulness": _safe_float(getattr(wakefulness, "wakefulness", 0.0), 0.0),
            "sleep_pressure": _safe_float(getattr(wakefulness, "get_sleep_pressure", lambda: 0.0)(), 0.0),
            "circadian": _safe_float(getattr(wakefulness, "get_circadian_signal", lambda: 0.0)(), 0.0),
            "alertness": _safe_float(getattr(wakefulness, "get_alertness", lambda: 0.0)(), 0.0),
        },
        autonomous_drives={
            "curiosity": _safe_float((getattr(drive_system, "drives", {}) or {}).get("curiosity", 0.0), 0.0),
            "social_drive": _safe_float(getattr(agent, "social_drive", 0.0), 0.0),
            "exploration": _safe_float((getattr(drive_system, "drives", {}) or {}).get("exploration", 0.0), 0.0),
            "energy": _safe_float(getattr(energy_system, "energy", getattr(agent, "energy", 0.0)), 0.0),
        },
        memory={
            "lived_steps": _safe_int(getattr(agent, "lived_steps", 0), 0),
            "hippocampus_size": _safe_int(len(raw_episodes), 0),
            "cortex_patterns": _safe_int(len(raw_patterns), 0),
            "td_error": _safe_mean(list(getattr(agent, "td_error_history", []) or [])),
        },
        hippocampus_episodes=hippocampus_episodes,
        cortex_patterns_detail=cortex_patterns_detail,
        value_layer_sources=_extract_value_layer_sources(agent),
        known_agents=known_agents,
        hearsay_received=hearsay_received,
        hearsay_sent=hearsay_sent,
        sex_specific={
            "is_mature": bool(getattr(agent, "is_mature", False)),
            "is_pregnant": bool(getattr(agent, "is_pregnant", False)),
            "gestation_timer": _safe_float(getattr(agent, "gestation_timer", 0.0), 0.0),
            "heat_cycle_phase": _safe_str(getattr(heat_cycle, "phase", ""), ""),
            "heat_cycle_value": _safe_float(getattr(heat_cycle, "value", 0.0), 0.0),
        },
        reproductive_drive=_safe_float(getattr(reproductive, "reproductive_drive", 0.0), 0.0),
        cooldown_steps=_safe_int(getattr(reproductive, "cooldown_steps", 0), 0),
        total_offspring_count=_safe_int(getattr(reproductive, "total_offspring", 0), 0),
        own_offspring_ids=_resolve_offspring_display_names(agent, knowledge, name_registry=name_registry),
        vitality=_safe_float(getattr(mortality, "vitality", 0.0), 0.0),
        senescence_rate=_safe_float(getattr(mortality, "senescence_rate", 0.0), 0.0),
        genome_genes=genome_genes,
        genome_generation=_safe_int(getattr(genome, "generation", 0), 0),
        genome_lineage_id=_safe_str(getattr(genome, "lineage_id", ""), ""),
        genome_lineage_rows=_resolve_genome_lineage_rows_for_agent(
            agent,
            _safe_str(getattr(genome, "lineage_id", ""), ""),
            name_registry=name_registry,
        ),
        genome_inheritance_meta=genome_inheritance_meta,
        genome_portrait=portrait,
        recent_interactions=all_interactions[:20],
    )
    try:
        inspector_data.nowa_interpretation = build_nowa_interpretation(inspector_data)
    except Exception:
        inspector_data.nowa_interpretation = None
    return inspector_data


def _lineage_rows_from_memorial_parents(
    memorial: AgentMemorial,
    death_registry: Any | None = None,
    name_registry: Any | None = None,
) -> list[str]:
    """Build readable lineage rows by walking recorded parents from a memorial.

    Prefer authoritative `name_registry` for names; fall back to memorials' stored
    names or raw ids. Stop branches when parent memorials are unavailable.
    """
    if death_registry is None:
        return []

    raw_parents = memorial.parents if isinstance(memorial.parents, (list, tuple)) else (None, None)
    current_ids = [_safe_str(pid, "").strip() for pid in raw_parents if _safe_str(pid, "").strip()]
    if not current_ids:
        return []

    rows: list[str] = []
    visited_frontiers: set[tuple[str, ...]] = set()
    depth = 0
    max_depth = max(1, _safe_int(getattr(memorial, "generation", 0), 0) + 4)
    while current_ids and depth < max_depth:
        frontier = tuple(current_ids)
        if frontier in visited_frontiers:
            break
        visited_frontiers.add(frontier)

        labels: list[str] = []
        next_ids_raw: list[str] = []
        for pid in current_ids:
            label = ""
            try:
                if name_registry is not None and pid:
                    label = name_registry.get_human_name(pid) or ""
            except Exception:
                label = ""

            parent_mem = None
            try:
                if death_registry is not None and pid:
                    parent_mem = death_registry.get_memorial(pid)
            except Exception:
                parent_mem = None

            if not label:
                if parent_mem is not None:
                    label = _safe_str(getattr(parent_mem, "name", ""), "") or pid
                else:
                    label = pid

            labels.append(label.upper())

            # queue grandparents if memorial data exists
            if parent_mem is not None:
                for gp in parent_mem.parents if isinstance(parent_mem.parents, (list, tuple)) else (None, None):
                    gp_s = _safe_str(gp, "").strip()
                    if gp_s:
                        next_ids_raw.append(gp_s)

        if not labels:
            break

        # If there are multiple labels in this frontier, join by ' × ' to show pairs/groups
        rows.append(" × ".join(labels))

        # dedupe next level while preserving order
        next_ids: list[str] = []
        seen_next: set[str] = set()
        for item in next_ids_raw:
            if item in seen_next:
                continue
            seen_next.add(item)
            next_ids.append(item)
        current_ids = next_ids
        depth += 1

    return rows


def build_inspector_data_from_memorial(
    memorial: AgentMemorial,
    display_name: str,
    name_registry: Any | None = None,
    death_registry: Any | None = None,
) -> InspectorData:
    """Build inspector payload from memorial snapshot.

    For genome lineage rows, prefer walking memorial parents (via DeathRegistry)
    to produce accurate per-generation parent pairs. Fall back to parsing
    `genome_lineage_id` when memorial parent data or registry access is not
    available.
    """

    social_row = {
        "agent_id": "",
        "name": "(архив)",
        "relationship_type": "archived",
        "affinity": 0.0,
        "familiarity": 0.0,
        "trust": 0.0,
        "positive_count": memorial.positive_interactions,
        "negative_count": memorial.negative_interactions,
        "interactions": memorial.total_interactions,
    }
    chosen_display = _safe_str(display_name, "") or _safe_str(memorial.agent_id, "")
    try:
        if name_registry is not None and memorial.agent_id:
            chosen_display = name_registry.get_human_name(memorial.agent_id) or chosen_display
    except Exception:
        pass

    # Prefer building lineage rows from memorial parent chains when a DeathRegistry
    # is available (more accurate than heuristic parsing of genome_lineage_id).
    genome_rows = _lineage_rows_from_memorial_parents(memorial, death_registry=death_registry, name_registry=name_registry)
    if not genome_rows:
        genome_rows = _lineage_rows_from_lineage_id(memorial.genome_lineage_id)

    genome_portrait = None
    genome_genes = dict(memorial.genome_genes)
    if genome_genes:
        try:
            genome_portrait = build_portrait(genome_genes, {}, display_name=chosen_display)
            if death_registry is not None:
                memorial_agent = type(
                    "MemorialAgent",
                    (),
                    {
                        "agent_id": memorial.agent_id,
                        "name": chosen_display,
                        "display_name": chosen_display,
                        "generation": memorial.generation,
                        "parents": memorial.parents,
                        "genome_genes": genome_genes,
                        "lived_steps": memorial.lived_steps,
                    },
                )()
                trend = build_lineage_trend(memorial_agent, death_registry, {})
                if trend is not None:
                    genome_portrait.lineage_trend = trend
        except Exception:
            genome_portrait = None

    inspector_data = InspectorData(
        agent_id=memorial.agent_id,
        display_name=chosen_display,
        is_deceased=True,
        sex=memorial.sex,
        generation=memorial.generation,
        parents=memorial.parents,
        age=memorial.age_at_death,
        lived_steps=memorial.lived_steps,
        cause_of_death=memorial.cause_of_death,
        affective_axes={
            "stress": memorial.final_stress,
            "valence": memorial.final_valence,
            "arousal": memorial.final_arousal,
            "attachment": memorial.final_attachment,
            "curiosity": memorial.final_curiosity,
            "trust": memorial.final_trust,
            "dominance": memorial.final_dominance,
            "energy": memorial.final_energy,
            "social_drive": memorial.final_social_drive,
        },
        neuromodulators={
            "dopamine": memorial.final_dopamine,
            "serotonin": memorial.final_serotonin,
            "norepinephrine": memorial.final_norepinephrine,
            "cortisol": memorial.final_cortisol,
            "acetylcholine": memorial.final_acetylcholine,
        },
        wakefulness={
            "wakefulness": memorial.final_wakefulness,
            "sleep_pressure": memorial.final_wakefulness,
            "circadian": 0.0,
            "alertness": max(0.0, 1.0 - memorial.final_wakefulness),
        },
        autonomous_drives={
            "curiosity": memorial.final_curiosity,
            "social_drive": memorial.final_social_drive,
            "exploration": 0.0,
            "energy": memorial.final_energy,
        },
        memory={
            "lived_steps": memorial.lived_steps,
            "hippocampus_size": memorial.final_hippocampus_size,
            "cortex_patterns": memorial.final_cortex_patterns,
            "td_error": memorial.final_mean_td_error,
        },
        hippocampus_episodes=[],
        cortex_patterns_detail=[],
        known_agents=[social_row] if memorial.known_agents_count > 0 else [],
        hearsay_received=0,
        hearsay_sent=0,
        sex_specific={"is_mature": True, "is_pregnant": False, "gestation_timer": 0.0},
        reproductive_drive=0.0,
        cooldown_steps=0,
        total_offspring_count=memorial.total_offspring,
        own_offspring_ids=list(memorial.own_offspring),
        vitality=memorial.final_vitality,
        senescence_rate=0.0,
        genome_genes=genome_genes,
        genome_generation=memorial.genome_generation,
        genome_lineage_id=memorial.genome_lineage_id,
        genome_lineage_rows=genome_rows,
        genome_inheritance_meta={},
        genome_portrait=genome_portrait,
        recent_interactions=[],
    )
    try:
        inspector_data.nowa_interpretation = build_nowa_interpretation(inspector_data)
    except Exception:
        inspector_data.nowa_interpretation = None
    return inspector_data


class AgentInspectorOverlay:
    """Interactive inspector overlay."""

    def __init__(self) -> None:
        self._visible: bool = False
        self._active_tab_index: int = 0
        self._active_tab: int = 0
        self._scroll: int = 0
        self._data: InspectorData | None = None
        self._surface: Any = None
        self._panel_rect: Any = None
        self._tab_rects: list[Any] = []
        self._agent_id: str = ""
        self._is_deceased: bool = False
        self._memory_link_local_rects: dict[str, Any] = {}
        self._memory_link_screen_rects: dict[str, Any] = {}
        self._hovered_memory_link: str | None = None
        self._memory_detail_visible: bool = False
        self._memory_detail_kind: str = ""
        self._memory_detail_title: str = ""
        self._memory_detail_lines: list[str] = []
        self._memory_detail_scroll: int = 0
        self._memory_detail_rect: Any = None
        self._memory_detail_close_rect: Any = None
        self._genome_table_expanded: bool = False
        self._genome_table_toggle_rect_y: int | None = None

    @property
    def _active_tab(self) -> int:
        return self._active_tab_index

    @_active_tab.setter
    def _active_tab(self, value: int) -> None:
        old_value = getattr(self, "_active_tab_index", 0)
        self._active_tab_index = int(value)
        if self._active_tab_index != 3 or old_value != self._active_tab_index:
            self._genome_table_expanded = False
            self._genome_table_toggle_rect_y = None

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def agent_id(self) -> str:
        if self._data is None:
            return ""
        return _safe_str(self._data.agent_id, "")

    def _coerce_legacy_payload(self, payload: dict[str, Any], is_deceased: bool) -> InspectorData:
        identity = payload.get("identity", {}) if isinstance(payload, dict) else {}
        if not isinstance(identity, dict):
            identity = {}
        return InspectorData(
            agent_id=_safe_str(identity.get("agent_id", ""), ""),
            display_name=_safe_str(identity.get("name", ""), "") or _safe_str(identity.get("agent_id", ""), ""),
            is_deceased=bool(is_deceased),
            sex=_safe_str(identity.get("sex", ""), ""),
            generation=_safe_int(identity.get("generation", 0), 0),
            parents=_safe_parents(identity.get("parents", (None, None))),
            age=_safe_float(identity.get("age", 0.0), 0.0),
            lived_steps=_safe_int(identity.get("lived_steps", 0), 0),
            cause_of_death=_safe_str(identity.get("cause_of_death", ""), ""),
        )

    def open(self, data: InspectorData | dict[str, Any], is_deceased: bool | None = None) -> None:
        if isinstance(data, InspectorData):
            self._data = data
        else:
            self._data = self._coerce_legacy_payload(data, bool(is_deceased))
        self._visible = True
        self._active_tab = 0
        self._scroll = 0
        self._surface = None
        self._agent_id = self._data.agent_id
        self._is_deceased = bool(self._data.is_deceased)
        self._memory_link_local_rects = {}
        self._memory_link_screen_rects = {}
        self._hovered_memory_link = None
        self._genome_table_expanded = False
        self._genome_table_toggle_rect_y = None
        self._close_memory_detail()

    def close(self) -> None:
        self._visible = False
        self._surface = None
        self._tab_rects = []
        self._data = None
        self._agent_id = ""
        self._is_deceased = False
        self._memory_link_local_rects = {}
        self._memory_link_screen_rects = {}
        self._hovered_memory_link = None
        self._close_memory_detail()

    def _compute_rect(self, screen_w: int, screen_h: int) -> Any:
        import pygame  # type: ignore

        x = max(16, (screen_w - INSPECTOR_WIDTH) // 2 + 140)
        x = min(x, max(16, screen_w - INSPECTOR_WIDTH - 16))
        y = max(12, (screen_h - INSPECTOR_HEIGHT) // 2)
        return pygame.Rect(x, y, INSPECTOR_WIDTH, INSPECTOR_HEIGHT)

    def _close_memory_detail(self) -> None:
        self._memory_detail_visible = False
        self._memory_detail_kind = ""
        self._memory_detail_title = ""
        self._memory_detail_lines = []
        self._memory_detail_scroll = 0
        self._memory_detail_rect = None
        self._memory_detail_close_rect = None
        self._genome_table_expanded = False
        self._genome_table_toggle_rect_y = None

    def _memory_link_at(self, pos: Any) -> str | None:
        if not isinstance(pos, tuple) or len(pos) != 2:
            return None
        for key in ("hippocampus_size", "cortex_patterns"):
            rect = self._memory_link_screen_rects.get(key)
            if rect is not None and rect.collidepoint(pos):
                return key
        return None

    def _open_memory_detail(self, key: str) -> None:
        if self._data is None:
            return
        if key == "hippocampus_size":
            title = tr("Гиппокамп: эпизоды памяти")
            lines = self._build_hippocampus_detail_lines()
        elif key == "cortex_patterns":
            title = tr("Кортекс: паттерны консолидации")
            lines = self._build_cortex_detail_lines()
        else:
            return
        self._memory_detail_kind = key
        self._memory_detail_title = title
        self._memory_detail_lines = lines
        self._memory_detail_scroll = 0
        self._memory_detail_visible = True

    def _build_hippocampus_detail_lines(self) -> list[str]:
        if self._data is None:
            return [tr("Данные отсутствуют.")]
        rows = list(self._data.hippocampus_episodes or [])
        total = _safe_int(self._data.memory.get("hippocampus_size", len(rows)), len(rows))
        if not rows:
            if self._data.is_deceased:
                return [
                    tr("Всего эпизодов (на момент смерти): {total}").format(total=total),
                    tr("Детальный снимок эпизодов для умершего агента не хранится."),
                ]
            return [tr("Эпизоды гиппокампа отсутствуют.")]

        shown_rows = rows[-MEMORY_DETAIL_SHOW_LIMIT:]
        lines = [tr("Всего эпизодов: {total}").format(total=total)]
        if len(rows) > len(shown_rows):
            lines.append(tr("Показаны последние {n} эпизодов.").format(n=len(shown_rows)))
        lines.append("")
        for item in reversed(shown_rows):
            idx = _safe_int(item.get("index", 0), 0)
            timestamp = _safe_float(item.get("timestamp", 0.0), 0.0)
            action = _humanize_action(item.get("action", ""))
            consequence = _humanize_consequence(item.get("consequence", ""))
            context_tokens = _humanize_context_tokens(_safe_list_str(item.get("context_tokens", [])))
            context_text = ", ".join(context_tokens[:8]) if context_tokens else "-"
            lines.append(
                tr("#{idx} | t={timestamp:.1f}с | действие={action} | результат={consequence}").format(
                    idx=idx,
                    timestamp=timestamp,
                    action=action,
                    consequence=consequence,
                )
            )
            lines.append("  " + tr("контекст: {text}").format(text=context_text))
            lines.append(
                "  "
                f"I={_safe_float(item.get('intensity', 0.0), 0.0):.2f} "
                f"R={_safe_float(item.get('reward', 0.0), 0.0):+.2f} "
                f"enc={_safe_float(item.get('encoding_strength', 0.0), 0.0):.2f} "
                f"rep={_safe_int(item.get('reinforcement_count', 0), 0)} "
                f"act={_safe_float(item.get('activation_energy', 0.0), 0.0):.2f} "
                f"stab={_safe_float(item.get('stability', 0.0), 0.0):.2f}"
            )
            replay_priority = _safe_float(item.get("replay_priority", 0.0), 0.0)
            consolidation_weight = _safe_float(item.get("consolidation_weight", 0.0), 0.0)
            prediction_shock = bool(item.get("prediction_shock", False))
            if replay_priority > 0.0 or consolidation_weight > 0.0 or prediction_shock:
                lines.append(
                    "  "
                    f"replay={replay_priority:.2f} "
                    f"cons={consolidation_weight:.2f} "
                    + tr("shock={value}").format(value=tr("да") if prediction_shock else tr("нет"))
                )
            lines.append("")
        return lines

    def _build_cortex_detail_lines(self) -> list[str]:
        if self._data is None:
            return [tr("Данные отсутствуют.")]
        rows = list(self._data.cortex_patterns_detail or [])
        total = _safe_int(self._data.memory.get("cortex_patterns", len(rows)), len(rows))
        if not rows:
            if self._data.is_deceased:
                return [
                    tr("Всего паттернов (на момент смерти): {total}").format(total=total),
                    tr("Детальный снимок паттернов для умершего агента не хранится."),
                ]
            return [tr("Корковые паттерны отсутствуют.")]

        rows.sort(key=lambda item: _safe_float(item.get("strength", 0.0), 0.0), reverse=True)
        shown_rows = rows[:MEMORY_DETAIL_SHOW_LIMIT]
        lines = [tr("Всего паттернов: {total}").format(total=total)]
        if len(rows) > len(shown_rows):
            lines.append(tr("Показаны {n} наиболее сильных паттернов.").format(n=len(shown_rows)))
        lines.append("")
        for item in shown_rows:
            idx = _safe_int(item.get("index", 0), 0)
            strength = _safe_float(item.get("strength", 0.0), 0.0)
            source_experiences = _safe_int(item.get("source_experiences", 0), 0)
            activation_count = _safe_int(item.get("activation_count", 0), 0)
            action = _humanize_action(item.get("action", ""))
            context_tokens = _humanize_context_tokens(_safe_list_str(item.get("context_tokens", [])))
            context_text = ", ".join(context_tokens[:8]) if context_tokens else "-"
            lines.append(
                tr("#{idx} | сила={strength:.3f} | источники={sources} | активации={activations}").format(
                    idx=idx,
                    strength=strength,
                    sources=source_experiences,
                    activations=activation_count,
                )
            )
            lines.append("  " + tr("контекст: {text}").format(text=context_text))
            if action and action != "-":
                lines.append("  " + tr("действие: {name}").format(name=action))
            consequence = _humanize_consequence(item.get("consequence", ""))
            if consequence and consequence != "-":
                lines.append("  " + tr("последствие: {name}").format(name=consequence))
            lines.append("")
        return lines

    def handle_event(self, event: Any) -> bool:
        if not self._visible:
            return False
        event_type = getattr(event, "type", None)
        try:
            import pygame  # type: ignore
        except Exception:
            return False

        if event_type == pygame.QUIT:
            return False

        if event_type == pygame.KEYDOWN:
            if getattr(event, "key", None) == pygame.K_ESCAPE:
                if self._memory_detail_visible:
                    self._close_memory_detail()
                else:
                    self.close()
                return True
            return False

        if self._panel_rect is None:
            self._panel_rect = self._compute_rect(1024, 768)

        if event_type == pygame.MOUSEWHEEL:
            if self._memory_detail_visible:
                self._memory_detail_scroll = max(0, self._memory_detail_scroll - int(getattr(event, "y", 0) * 28))
                return True
            self._scroll = max(0, self._scroll - int(getattr(event, "y", 0) * 28))
            return True

        if event_type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            pos = getattr(event, "pos", None)
            if not isinstance(pos, tuple) or len(pos) != 2:
                return True
            if self._memory_detail_visible:
                if self._memory_detail_close_rect is not None and self._memory_detail_close_rect.collidepoint(pos):
                    self._close_memory_detail()
                    return True
                if self._memory_detail_rect is not None and not self._memory_detail_rect.collidepoint(pos):
                    self._close_memory_detail()
                    return True
                return True
            for idx, rect in enumerate(self._tab_rects):
                if rect.collidepoint(pos):
                    self._active_tab = idx
                    self._scroll = 0
                    self._hovered_memory_link = None
                    return True
            link_key = self._memory_link_at(pos)
            if link_key is not None:
                self._open_memory_detail(link_key)
                return True
            if self._active_tab == 3 and self._genome_table_toggle_rect_y is not None and self._panel_rect is not None:
                import pygame  # type: ignore

                content_x = self._panel_rect.x + 10
                content_y = self._panel_rect.y + 62 + 28 + 8
                toggle_rect = pygame.Rect(
                    content_x,
                    content_y + int(self._genome_table_toggle_rect_y) - self._scroll,
                    170,
                    18,
                )
                if toggle_rect.collidepoint(pos):
                    self._genome_table_expanded = not self._genome_table_expanded
                    self._scroll = 0
                    return True
            if self._panel_rect.collidepoint(pos):
                return True
            self.close()
            return True

        if event_type == pygame.MOUSEMOTION:
            pos = getattr(event, "pos", (-1, -1))
            if self._memory_detail_visible:
                self._hovered_memory_link = None
                return True
            self._hovered_memory_link = self._memory_link_at(pos)
            return self._panel_rect is not None and self._panel_rect.collidepoint(getattr(event, "pos", (-1, -1)))

        return False

    def draw(self, screen: Any, font: Any, font_small: Any, font_mono: Any) -> None:
        if not self._visible or self._data is None:
            return
        if getattr(self, "_drawn_lang", None) != get_language():
            self._drawn_lang = get_language()
            self._data.nowa_interpretation = None
            if self._data.genome_genes:
                trend = self._data.genome_portrait.lineage_trend if self._data.genome_portrait else None
                try:
                    portrait = build_portrait(
                        self._data.genome_genes,
                        self._data.genome_inheritance_meta or {},
                        display_name=self._data.display_name,
                    )
                    if trend is not None:
                        portrait.lineage_trend = trend
                    self._data.genome_portrait = portrait
                except Exception:
                    pass
            if self._memory_detail_visible and self._memory_detail_kind:
                self._open_memory_detail(self._memory_detail_kind)
        import pygame  # type: ignore

        screen_w, screen_h = screen.get_size()
        self._panel_rect = self._compute_rect(screen_w, screen_h)
        panel_rect = self._panel_rect

        veil = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 80))
        screen.blit(veil, (0, 0))

        panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel.fill(INSPECTOR_DECEASED_TINT if self._data.is_deceased else INSPECTOR_BG)
        pygame.draw.rect(panel, INSPECTOR_BORDER, panel.get_rect(), 2, border_radius=8)

        header_rect = pygame.Rect(0, 0, panel_rect.width, 58)
        pygame.draw.rect(panel, INSPECTOR_HEADER, header_rect, border_radius=8)
        title = self._data.display_name
        if self._data.is_deceased:
            cause = self._data.cause_of_death or tr("неизвестно")
            title = f"† {title} [{cause}]"
        panel.blit(font.render(title, True, INSPECTOR_TEXT), (14, 10))
        sub = tr("{sex} | G{generation} | возраст {age:.1f}с | шаги {steps}").format(
            sex=self._data.sex,
            generation=self._data.generation,
            age=self._data.age,
            steps=self._data.lived_steps,
        )
        panel.blit(font_small.render(sub, True, INSPECTOR_MUTED_TEXT), (14, 33))

        tabs_top = 62
        tab_h = 28
        tab_w = panel_rect.width // len(_TAB_KEYS)
        self._tab_rects = []
        for idx, tab_key in enumerate(_TAB_KEYS):
            tab_label = ui_label("tab", tab_key)
            rect = pygame.Rect(idx * tab_w, tabs_top, tab_w, tab_h)
            self._tab_rects.append(rect.move(panel_rect.x, panel_rect.y))
            active = idx == self._active_tab
            pygame.draw.rect(panel, TAB_ACTIVE if active else TAB_INACTIVE, rect, border_radius=4)
            text = font_small.render(tab_label, True, TAB_TEXT_ACTIVE if active else TAB_TEXT_INACTIVE)
            panel.blit(text, text.get_rect(center=rect.center))

        content_rect = pygame.Rect(10, tabs_top + tab_h + 8, panel_rect.width - 20, panel_rect.height - tabs_top - tab_h - 16)
        estimated_h = self._estimate_active_tab_height()

        # First pass: allocate an estimated surface (at least viewport height)
        temp_h = max(content_rect.height, estimated_h)
        content_surface = pygame.Surface((content_rect.width, temp_h), pygame.SRCALPHA)
        content_surface.fill((0, 0, 0, 0))
        self._memory_link_local_rects = {}
        self._memory_link_screen_rects = {}
        full_h = self._draw_active_tab(content_surface, font, font_small, font_mono)

        # If content was larger than our estimate, re-create surface at exact full height
        if full_h > temp_h:
            content_surface = pygame.Surface((content_rect.width, full_h), pygame.SRCALPHA)
            content_surface.fill((0, 0, 0, 0))
            # reset any local rects before the final draw
            self._memory_link_local_rects = {}
            self._memory_link_screen_rects = {}
            full_h = self._draw_active_tab(content_surface, font, font_small, font_mono)

        max_scroll = max(0, full_h - content_rect.height)
        self._scroll = max(0, min(self._scroll, max_scroll))
        panel.blit(content_surface, content_rect.topleft, area=pygame.Rect(0, self._scroll, content_rect.width, content_rect.height))
        self._rebuild_memory_link_screen_rects(panel_rect=panel_rect, content_rect=content_rect)
        if not self._memory_detail_visible:
            self._hovered_memory_link = self._memory_link_at(pygame.mouse.get_pos())
        self._draw_scroll_indicator(
            panel=panel,
            content_rect=content_rect,
            full_h=full_h,
            max_scroll=max_scroll,
        )

        screen.blit(panel, panel_rect.topleft)
        if self._memory_detail_visible:
            self._draw_memory_detail_window(screen=screen, font=font, font_small=font_small)

    def _draw_bar(self, surface: Any, x: int, y: int, value: float, color: tuple[int, int, int] = BAR_FG) -> None:
        import pygame  # type: ignore

        clamped = max(0.0, min(1.0, float(value)))
        bg = pygame.Rect(x, y + 4, BAR_W, BAR_H)
        pygame.draw.rect(surface, BAR_BG, bg, border_radius=3)
        if clamped > 0.0:
            fg = pygame.Rect(x, y + 4, max(1, int(BAR_W * clamped)), BAR_H)
            pygame.draw.rect(surface, color, fg, border_radius=3)

    def _draw_metric(
        self,
        surface: Any,
        font_small: Any,
        x: int,
        y: int,
        *,
        key: str,
        label: str,
        value: float,
    ) -> int:
        text = f"{label}: {value:.3f}"
        surface.blit(font_small.render(text, True, INSPECTOR_TEXT), (x, y))
        self._draw_bar(surface, x + 165, y, value if key != "valence" else (value + 1.0) * 0.5)
        return y + 18

    def _draw_active_tab(self, surface: Any, font: Any, font_small: Any, font_mono: Any) -> int:
        if self._active_tab == 0:
            return self._draw_tab_nowa(surface, font, font_small)
        if self._active_tab == 1:
            return self._draw_tab_social(surface, font, font_small)
        if self._active_tab == 2:
            return self._draw_tab_repro(surface, font, font_small)
        if self._active_tab == 3:
            return self._draw_tab_genome(surface, font, font_small, font_mono)
        return self._draw_tab_history(surface, font, font_small)

    def _estimate_active_tab_height(self) -> int:
        """Estimate pixel height required for the active tab content."""
        if self._data is None:
            return 0
        if self._active_tab == 0:
            return 560
        if self._active_tab == 1:
            return 52 + (len(self._data.known_agents) * 18) + 16
        if self._active_tab == 2:
            offspring_extra = 0
            if self._data.own_offspring_ids:
                offspring_extra = 18 + (len(self._data.own_offspring_ids) * 16)
            return 24 + (8 * 18) + offspring_extra + 24
        if self._active_tab == 3:
            genes_count = len(self._data.genome_genes) if self._genome_table_expanded else 0
            portrait = self._data.genome_portrait
            portrait_h = 0
            if portrait is not None:
                portrait_h += 22 + (len(portrait.trait_scores) * 18) + 90
                portrait_h += (len(portrait.strengths) + len(portrait.weaknesses) + len(portrait.neutral_traits)) * 16
                portrait_h += 12
                if portrait.mutations:
                    portrait_h += 22 + min(8, len(portrait.mutations)) * 56
                if portrait.lineage_trend and len(portrait.lineage_trend) >= 2:
                    death_rows_h = 40 if self._data.is_deceased else 0
                    portrait_h += 40 + len(LINEAGE_TRACKED_GENES) * 32 + death_rows_h
            lineage_rows = list(self._data.genome_lineage_rows or _lineage_rows_from_lineage_id(self._data.genome_lineage_id))
            lineage_h = 42 if not lineage_rows else 42 + (len(lineage_rows) * 18) + (max(0, len(lineage_rows) - 1) * 16)
            table_h = 18 + (genes_count * 16) + 10
            return lineage_h + portrait_h + table_h + 32
        return 52 + (len(self._data.recent_interactions) * 18) + 16

    def _draw_scroll_indicator(
        self,
        *,
        panel: Any,
        content_rect: Any,
        full_h: int,
        max_scroll: int,
    ) -> None:
        import pygame  # type: ignore

        if full_h <= content_rect.height:
            return

        track_margin = 2
        track_w = 6
        track_h = max(8, int(content_rect.height))
        track_x = int(content_rect.right - track_w - track_margin)
        track_y = int(content_rect.y)
        track = pygame.Rect(track_x, track_y, track_w, track_h)
        pygame.draw.rect(panel, SCROLL_TRACK, track, border_radius=3)

        ratio = max(0.0, min(1.0, float(content_rect.height) / float(max(1, full_h))))
        thumb_h = max(18, int(track_h * ratio))
        if max_scroll <= 0:
            thumb_y = track_y
        else:
            progress = max(0.0, min(1.0, float(self._scroll) / float(max_scroll)))
            thumb_y = track_y + int((track_h - thumb_h) * progress)
        thumb = pygame.Rect(track_x, thumb_y, track_w, thumb_h)
        pygame.draw.rect(panel, SCROLL_THUMB, thumb, border_radius=3)

    def _rebuild_memory_link_screen_rects(self, *, panel_rect: Any, content_rect: Any) -> None:
        try:
            import pygame  # type: ignore
        except Exception:
            self._memory_link_screen_rects = {}
            return

        if self._active_tab != 0 or not self._memory_link_local_rects:
            self._memory_link_screen_rects = {}
            return

        viewport = pygame.Rect(
            int(panel_rect.x + content_rect.x),
            int(panel_rect.y + content_rect.y),
            int(content_rect.width),
            int(content_rect.height),
        )
        projected: dict[str, Any] = {}
        for key, local_rect in self._memory_link_local_rects.items():
            screen_rect = local_rect.move(viewport.x, viewport.y - int(self._scroll))
            visible = screen_rect.clip(viewport)
            if visible.width <= 0 or visible.height <= 0:
                continue
            projected[key] = visible
        self._memory_link_screen_rects = projected

    def _wrap_text_to_width(self, line: str, *, font_small: Any, max_width: int) -> list[str]:
        text = _safe_str(line, "")
        if not text:
            return [""]
        if max_width <= 1 or font_small.size(text)[0] <= max_width:
            return [text]

        words = text.split(" ")
        wrapped: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font_small.size(candidate)[0] <= max_width:
                current = candidate
                continue

            if current:
                wrapped.append(current)
            current = ""

            if font_small.size(word)[0] <= max_width:
                current = word
                continue

            fragment = ""
            for ch in word:
                candidate_fragment = f"{fragment}{ch}"
                if font_small.size(candidate_fragment)[0] <= max_width:
                    fragment = candidate_fragment
                else:
                    if fragment:
                        wrapped.append(fragment)
                    fragment = ch
            current = fragment

        if current:
            wrapped.append(current)
        return wrapped or [text]

    def _draw_memory_detail_window(self, *, screen: Any, font: Any, font_small: Any) -> None:
        if not self._memory_detail_visible:
            return
        try:
            import pygame  # type: ignore
        except Exception:
            return

        screen_w, screen_h = screen.get_size()
        width = min(760, max(420, screen_w - 96))
        height = min(540, max(280, screen_h - 96))
        x = max(12, (screen_w - width) // 2)
        y = max(12, (screen_h - height) // 2)
        popup_rect = pygame.Rect(x, y, width, height)
        self._memory_detail_rect = popup_rect

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill(DETAIL_BG)
        pygame.draw.rect(panel, DETAIL_BORDER, panel.get_rect(), 2, border_radius=10)

        header_h = 44
        header_rect = pygame.Rect(0, 0, width, header_h)
        pygame.draw.rect(panel, DETAIL_HEADER, header_rect, border_radius=10)
        panel.blit(font.render(self._memory_detail_title or tr("Детали памяти"), True, INSPECTOR_TEXT), (14, 10))

        close_surface = font_small.render(tr("закрыть x"), True, LINK_TEXT)
        close_local = close_surface.get_rect(topright=(width - 14, 14))
        panel.blit(close_surface, close_local.topleft)
        self._memory_detail_close_rect = close_local.move(x, y)

        hint = font_small.render(tr("Esc или клик вне окна"), True, INSPECTOR_MUTED_TEXT)
        panel.blit(hint, (14, header_h - 2))

        content_rect = pygame.Rect(12, header_h + 14, width - 24, height - header_h - 24)
        base_lines = list(self._memory_detail_lines or [tr("Нет данных.")])
        wrapped_lines: list[str] = []
        for line in base_lines:
            wrapped_lines.extend(self._wrap_text_to_width(line, font_small=font_small, max_width=content_rect.width - 8))

        line_h = max(14, font_small.get_height() + 2)
        content_h = max(content_rect.height, (len(wrapped_lines) * line_h) + 8)
        content_surface = pygame.Surface((content_rect.width, content_h), pygame.SRCALPHA)
        content_surface.fill((0, 0, 0, 0))
        y_cursor = 4
        for line in wrapped_lines:
            color = DETAIL_LINE
            if not line:
                y_cursor += line_h // 2
                continue
            if line.startswith("  "):
                color = INSPECTOR_MUTED_TEXT
            content_surface.blit(font_small.render(line, True, color), (0, y_cursor))
            y_cursor += line_h

        max_scroll = max(0, content_h - content_rect.height)
        self._memory_detail_scroll = max(0, min(self._memory_detail_scroll, max_scroll))
        panel.blit(
            content_surface,
            content_rect.topleft,
            area=pygame.Rect(0, self._memory_detail_scroll, content_rect.width, content_rect.height),
        )
        if max_scroll > 0:
            track = pygame.Rect(content_rect.right - 4, content_rect.y, 4, content_rect.height)
            pygame.draw.rect(panel, SCROLL_TRACK, track, border_radius=2)
            thumb_h = max(18, int(track.height * (float(content_rect.height) / float(max(1, content_h)))))
            progress = float(self._memory_detail_scroll) / float(max_scroll) if max_scroll > 0 else 0.0
            thumb_y = track.y + int((track.height - thumb_h) * progress)
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
            pygame.draw.rect(panel, SCROLL_THUMB, thumb, border_radius=2)

        screen.blit(panel, popup_rect.topleft)

    def _nowa_section_title(self, title: str) -> str:
        if self._data is not None and self._data.is_deceased:
            return tr("{title} (при смерти)").format(title=title)
        return title

    def _fit_text_to_width(self, text: str, font_small: Any, max_width: int) -> str:
        if max_width <= 0 or font_small.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and font_small.size(f"{trimmed}...")[0] > max_width:
            trimmed = trimmed[:-1]
        return f"{trimmed}..." if trimmed else "..."

    def _draw_nowa_section_header(self, surface: Any, font_small: Any, y: int, title: str) -> int:
        import pygame  # type: ignore

        text = self._nowa_section_title(title).upper()
        rendered = font_small.render(text, True, SECTION_TITLE_COLOR)
        line_y = y + max(7, rendered.get_height() // 2)
        surface.blit(rendered, (0, y))
        start_x = min(surface.get_width() - 1, rendered.get_width() + 8)
        pygame.draw.line(surface, SECTION_LINE_COLOR, (start_x, line_y), (surface.get_width() - 2, line_y), 1)
        return y + rendered.get_height() + 8

    def _draw_summary_text(
        self,
        surface: Any,
        font_small: Any,
        y: int,
        text: str,
        *,
        max_lines: int = 4,
        color: tuple[int, int, int] = INSPECTOR_MUTED_TEXT,
    ) -> int:
        max_width = max(80, surface.get_width() - 8)
        lines = self._wrap_text_to_width(text, font_small=font_small, max_width=max_width)
        for line in lines[:max_lines]:
            surface.blit(font_small.render(line, True, color), (0, y))
            y += 16
        return y

    def _draw_affect_tone_badge(
        self,
        surface: Any,
        font: Any,
        font_small: Any,
        y: int,
        interp: Any,
    ) -> int:
        import pygame  # type: ignore

        badge_text = tr("Итоговый аффективный тон: {label}").format(label=interp.tone_label)
        text_surface = font_small.render(badge_text, True, INSPECTOR_TEXT)
        badge_w = min(surface.get_width() - 4, max(220, text_surface.get_width() + 18))
        badge_rect = pygame.Rect(0, y, badge_w, 24)
        pygame.draw.rect(surface, (*interp.tone_color, 72), badge_rect, border_radius=6)
        pygame.draw.rect(surface, interp.tone_color, badge_rect, 1, border_radius=6)
        surface.blit(text_surface, (9, y + 4))
        y += 30
        return self._draw_summary_text(surface, font_small, y, f'"{interp.summary}"', max_lines=4)

    def _draw_neuro_profile_badge(
        self,
        surface: Any,
        font: Any,
        font_small: Any,
        y: int,
        profile: Any,
    ) -> int:
        import pygame  # type: ignore

        text = tr("Профиль: {label}").format(label=profile.profile_label)
        rendered = font_small.render(text, True, INSPECTOR_TEXT)
        rect = pygame.Rect(0, y, min(surface.get_width() - 4, max(220, rendered.get_width() + 18)), 24)
        pygame.draw.rect(surface, (224, 216, 202, 150), rect, border_radius=6)
        pygame.draw.rect(surface, SECTION_LINE_COLOR, rect, 1, border_radius=6)
        surface.blit(rendered, (9, y + 4))
        y += 30
        y = self._draw_summary_text(surface, font_small, y, f'"{profile.summary}"', max_lines=4)
        for item in list(profile.interactions)[:2]:
            y = self._draw_summary_text(surface, font_small, y, f"• {item}", max_lines=2)
        return y

    def _draw_axis_row(
        self,
        surface: Any,
        font_small: Any,
        y: int,
        *,
        label: str,
        value: float,
        short_label: str,
        value_range: tuple[float, float] = (0.0, 1.0),
        bar_color: tuple[int, int, int] = BAR_FG,
    ) -> int:
        import pygame  # type: ignore

        label_x = 0
        bar_x = 124
        bar_w = 120
        value_x = bar_x + bar_w + 10
        short_x = value_x + 58
        min_value, max_value = value_range
        span = max(1e-9, max_value - min_value)
        bar_value = _safe_float((value - min_value) / span, 0.0)
        bar_value = max(0.0, min(1.0, bar_value))

        label_text = self._fit_text_to_width(label, font_small, bar_x - 6)
        surface.blit(font_small.render(label_text, True, INSPECTOR_TEXT), (label_x, y))
        bg = pygame.Rect(bar_x, y + 5, bar_w, BAR_H)
        pygame.draw.rect(surface, BAR_BG, bg, border_radius=3)
        if bar_value > 0.0:
            fg = pygame.Rect(bar_x, y + 5, max(1, int(bar_w * bar_value)), BAR_H)
            pygame.draw.rect(surface, bar_color, fg, border_radius=3)
        surface.blit(font_small.render(f"{value:.3f}", True, INSPECTOR_TEXT), (value_x, y))
        short = self._fit_text_to_width(short_label, font_small, max(20, surface.get_width() - short_x))
        surface.blit(font_small.render(short, True, INSPECTOR_MUTED_TEXT), (short_x, y))
        return y + 18

    def _draw_memory_link_line(self, surface: Any, font_small: Any, y: int, key: str, text: str) -> int:
        color = INSPECTOR_TEXT
        can_link = self._data is not None and not self._data.is_deceased and key in _MEMORY_LINK_KEYS
        if can_link:
            color = LINK_TEXT_HOVER if self._hovered_memory_link == key else LINK_TEXT
        rendered = font_small.render(text, True, color)
        surface.blit(rendered, (0, y))
        if can_link:
            try:
                import pygame  # type: ignore

                underline_y = y + rendered.get_height() - 1
                pygame.draw.line(surface, color, (0, underline_y), (rendered.get_width(), underline_y), 1)
                self._memory_link_local_rects[key] = pygame.Rect(0, y, rendered.get_width(), rendered.get_height())
            except Exception:
                pass
        return y + 18

    def _draw_value_layers(self, surface: Any, font_small: Any, y: int, layers: list[Any]) -> int:
        import pygame  # type: ignore

        for layer in layers:
            top = list(layer.top_actions[:3])
            if not top:
                continue
            bar_value = max(0.0, min(1.0, float(top[0][1])))
            label = f"T{layer.level}"
            surface.blit(font_small.render(label, True, INSPECTOR_TEXT), (0, y))
            bar_x = 34
            bar_w = 80
            bg = pygame.Rect(bar_x, y + 5, bar_w, BAR_H)
            pygame.draw.rect(surface, BAR_BG, bg, border_radius=3)
            pygame.draw.rect(surface, AXIS_COLORS["dopamine"], pygame.Rect(bar_x, y + 5, max(1, int(bar_w * bar_value)), BAR_H), border_radius=3)
            actions_text = "  ".join(f"{action}: {value:.2f}" for action, value in top)
            surface.blit(font_small.render(self._fit_text_to_width(actions_text, font_small, surface.get_width() - 126), True, INSPECTOR_TEXT), (124, y))
            y += 18
        if layers and layers[0].top_actions:
            action = layers[0].top_actions[0][0]
            interpretations = {
                "eat": tr("Решения агента устойчиво направлены к еде."),
                "drink": tr("Решения агента вращаются вокруг воды и восстановления баланса."),
                "sleep": tr("Сон и восстановление доминируют над прочими действиями."),
                "explore": tr("Исследование окружения сейчас является ведущей стратегией."),
                "hide": tr("Защитная стратегия заметно сильнее остальных вариантов."),
                "rest": tr("Агент выбирает экономию сил и восстановление."),
            }
            fallback = tr("Доминирующее действие задаёт текущую стратегию агента.")
            y = self._draw_summary_text(
                surface,
                font_small,
                y + 2,
                f'"{interpretations.get(action, fallback)}"',
                max_lines=2,
            )
        return y

    def _draw_habit(self, surface: Any, font_small: Any, y: int, habit: Any) -> int:
        action = _humanize_action(habit.action)
        context = " + ".join(_humanize_context_tokens(habit.context_tokens[:3])) or "-"
        text = tr("• {action} ← {context}     сила {strength:.2f}  ×{count}").format(
            action=action,
            context=context,
            strength=habit.strength,
            count=habit.activation_count,
        )
        if habit.consequence:
            text = f"{text}  → {_humanize_consequence(habit.consequence)}"
        lines = self._wrap_text_to_width(text, font_small=font_small, max_width=max(80, surface.get_width() - 4))
        for line in lines[:2]:
            surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
            y += 16
        return y + 2

    def _draw_episode(self, surface: Any, font_small: Any, y: int, episode: Any) -> int:
        action = _humanize_action(episode.action)
        context = " + ".join(_humanize_context_tokens(episode.context_tokens[:2])) or "-"
        consequence = _humanize_consequence(episode.consequence)
        reward_text, reward_color = reward_label(episode.reward)
        prefix = f"[t={episode.timestamp:.0f}] {action} ← {context} → {consequence}"
        reward_w = font_small.size(reward_text)[0]
        prefix = self._fit_text_to_width(prefix, font_small, max(40, surface.get_width() - reward_w - 12))
        surface.blit(font_small.render(prefix, True, INSPECTOR_TEXT), (0, y))
        surface.blit(font_small.render(reward_text, True, reward_color), (surface.get_width() - reward_w, y))
        return y + 18

    def _draw_personality_readout(self, surface: Any, font: Any, font_small: Any, y: int, personality: Any) -> int:
        surface.blit(font_small.render(tr("Характер: {label}").format(label=personality.character_label), True, INSPECTOR_TEXT), (0, y))
        y += 20
        return self._draw_summary_text(surface, font_small, y, f'"{personality.summary}"', max_lines=4)

    def _draw_tab_nowa(self, surface: Any, font: Any, font_small: Any) -> int:
        """Draw the extended interpretive NOWA tab."""

        assert self._data is not None
        interp = self._data.nowa_interpretation
        if interp is None:
            try:
                interp = build_nowa_interpretation(self._data)
                self._data.nowa_interpretation = interp
            except Exception:
                interp = build_nowa_interpretation(None)

        y = 6
        title = tr("NOWA (при смерти)") if self._data.is_deceased else tr("NOWA")
        surface.blit(font.render(title, True, INSPECTOR_TEXT), (0, y))
        y += 28

        y = self._draw_nowa_section_header(surface, font_small, y, tr("Аффективное состояние"))
        y = self._draw_affect_tone_badge(surface, font, font_small, y, interp.affect)
        y += 6
        for key in [*_AFFECT_KEYS, "energy", "social_drive"]:
            value = _safe_float(self._data.affective_axes.get(key, 0.0), 0.0)
            y = self._draw_axis_row(
                surface,
                font_small,
                y,
                label=ui_label("affect", key, key),
                value=value,
                short_label=interp.affect.axis_labels.get(key, get_axis_label(key, value)),
                value_range=(-1.0, 1.0) if key == "valence" else (0.0, 1.0),
                bar_color=AXIS_COLORS.get(key, BAR_FG),
            )

        y += 8
        y = self._draw_nowa_section_header(surface, font_small, y, tr("Нейрохимический профиль"))
        y = self._draw_neuro_profile_badge(surface, font, font_small, y, interp.neuro)
        y += 6
        for key in ["dopamine", "serotonin", "norepinephrine", "cortisol", "acetylcholine"]:
            value = _safe_float(self._data.neuromodulators.get(key, 0.0), 0.0)
            y = self._draw_axis_row(
                surface,
                font_small,
                y,
                label=ui_label("neuro", key, key),
                value=value,
                short_label=interp.neuro.modulator_labels.get(key, ""),
                bar_color=AXIS_COLORS.get(key, BAR_FG),
            )

        y += 8
        y = self._draw_nowa_section_header(surface, font_small, y, tr("Бодрствование и энергия"))
        for key in ["wakefulness", "sleep_pressure", "circadian", "alertness"]:
            value = _safe_float(self._data.wakefulness.get(key, 0.0), 0.0)
            y = self._draw_axis_row(
                surface,
                font_small,
                y,
                label=ui_label("wake", key, key),
                value=value,
                short_label=get_axis_label(key, value),
                bar_color=AXIS_COLORS.get(key, BAR_FG),
            )

        if interp.value_layers:
            y += 8
            y = self._draw_nowa_section_header(surface, font_small, y, tr("Ценностные слои"))
            y = self._draw_value_layers(surface, font_small, y, interp.value_layers)

        if interp.habits:
            y += 8
            y = self._draw_nowa_section_header(surface, font_small, y, tr("Активные привычки"))
            total = _safe_int(self._data.memory.get("cortex_patterns", len(interp.habits)), len(interp.habits))
            y = self._draw_memory_link_line(
                surface,
                font_small,
                y,
                "cortex_patterns",
                tr("{n} устойчивых паттерна из {total}:").format(n=len(interp.habits), total=total),
            )
            for habit in interp.habits:
                y = self._draw_habit(surface, font_small, y, habit)

        if interp.recent_episodes:
            y += 8
            y = self._draw_nowa_section_header(surface, font_small, y, tr("Недавний опыт"))
            total = _safe_int(self._data.memory.get("hippocampus_size", len(interp.recent_episodes)), len(interp.recent_episodes))
            y = self._draw_memory_link_line(
                surface,
                font_small,
                y,
                "hippocampus_size",
                tr("Последние {n} значимых эпизодов из {total}:").format(n=len(interp.recent_episodes), total=total),
            )
            for episode in interp.recent_episodes:
                y = self._draw_episode(surface, font_small, y, episode)

        y += 8
        y = self._draw_nowa_section_header(surface, font_small, y, tr("Интерпретация личности"))
        y = self._draw_personality_readout(surface, font, font_small, y, interp.personality)
        return y + 8

    def _draw_tab_social(self, surface: Any, font: Any, font_small: Any) -> int:
        assert self._data is not None
        y = 6
        surface.blit(font.render(tr("Социум"), True, INSPECTOR_TEXT), (0, y))
        y += 24
        surface.blit(
            font_small.render(
                tr("известных: {known} | слухов получено: {hearsay}").format(
                    known=len(self._data.known_agents),
                    hearsay=self._data.hearsay_received,
                ),
                True,
                INSPECTOR_MUTED_TEXT,
            ),
            (0, y),
        )
        y += 20
        for item in self._data.known_agents:
            rel = _relationship_ru(item.get("relationship_type", "stranger"))
            raw_name = item.get("name", "?")
            if raw_name == "(архив)":
                raw_name = tr("(архив)")
            line = tr("{name} [{rel}] симпатия {affinity:.2f} поз. {pos} нег. {neg}").format(
                name=raw_name,
                rel=rel,
                affinity=float(item.get("affinity", 0.0) or 0.0),
                pos=item.get("positive_count", 0),
                neg=item.get("negative_count", 0),
            )
            surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
            y += 18
        if not self._data.known_agents:
            surface.blit(font_small.render(tr("Нет социальных данных"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 18
        return y + 6

    def _draw_tab_repro(self, surface: Any, font: Any, font_small: Any) -> int:
        assert self._data is not None
        y = 6
        surface.blit(font.render(tr("Репро"), True, INSPECTOR_TEXT), (0, y))
        y += 24
        rows = [
            tr("пол: {sex}").format(sex=self._data.sex),
            tr("репродуктивный драйв: {value:.3f}").format(value=self._data.reproductive_drive),
            tr("шаги восстановления: {n}").format(n=self._data.cooldown_steps),
            tr("всего потомков: {n}").format(n=self._data.total_offspring_count),
            tr("витальность: {value:.3f}").format(value=self._data.vitality),
            tr("темп старения: {value:.4f}").format(value=self._data.senescence_rate),
            tr("беременна: {value}").format(value=_bool_ru(self._data.sex_specific.get("is_pregnant", False))),
            tr("причина смерти: {cause}").format(cause=self._data.cause_of_death or "-"),
        ]
        for line in rows:
            surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
            y += 18
        if self._data.own_offspring_ids:
            surface.blit(font_small.render(tr("собственные потомки:"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 18
            for item in self._data.own_offspring_ids:
                surface.blit(font_small.render(f"- {item}", True, INSPECTOR_TEXT), (12, y))
                y += 16
        return y + 6

    def _draw_tab_genome(self, surface: Any, font: Any, font_small: Any, font_mono: Any) -> int:
        assert self._data is not None
        y = 6
        header = tr("Геном G{generation}").format(generation=self._data.genome_generation)
        surface.blit(font.render(header, True, INSPECTOR_TEXT), (0, y))
        y += 24

        lineage_rows = list(self._data.genome_lineage_rows or _lineage_rows_from_lineage_id(self._data.genome_lineage_id))
        if lineage_rows:
            surface.blit(font_small.render(tr("Линия:"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 18
            for idx, row in enumerate(lineage_rows):
                surface.blit(font_mono.render(row, True, INSPECTOR_TEXT), (0, y))
                y += 18
                if idx < len(lineage_rows) - 1:
                    surface.blit(font_mono.render(" ↓ ", True, INSPECTOR_MUTED_TEXT), (0, y))
                    y += 16
            y += 4
        else:
            surface.blit(font_small.render(tr("Линия: -"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 22

        portrait = self._data.genome_portrait
        if portrait is not None:
            y = self._draw_genome_portrait(surface, font, font_small, y, portrait)
            y += 12
            if portrait.mutations:
                y = self._draw_mutation_effects(surface, font, font_small, y, portrait.mutations)
                y += 12
            if portrait.lineage_trend and len(portrait.lineage_trend) >= 2:
                y = self._draw_lineage_trend(surface, font, font_small, y, portrait.lineage_trend)
                y += 12

        y = self._draw_genome_table_collapsible(surface, font, font_small, font_mono, y)
        return y

    def _draw_genome_portrait(self, surface: Any, font: Any, font_small: Any, y: int, portrait: GenomePortrait) -> int:
        surface.blit(font.render(tr("Портрет личности"), True, INSPECTOR_TEXT), (0, y))
        y += 22
        trait_colors = {
            "temperament": (210, 120, 80),
            "social": (120, 180, 130),
            "endurance": (80, 140, 200),
            "cognition": (160, 100, 200),
            "lifespan": (180, 160, 80),
        }
        for cat in ["temperament", "social", "endurance", "cognition", "lifespan"]:
            ts = portrait.trait_scores.get(cat)
            if ts is None:
                continue
            label = ui_label("trait", cat, cat)
            score = max(0.0, min(1.0, float(ts.score)))
            surface.blit(font_small.render(label, True, INSPECTOR_MUTED_TEXT), (0, y))
            try:
                import pygame  # type: ignore

                pygame.draw.rect(surface, BAR_BG, pygame.Rect(100, y + 4, 120, 8), border_radius=3)
                fill_w = int(120 * score)
                if fill_w > 0:
                    pygame.draw.rect(surface, trait_colors.get(cat, BAR_FG), pygame.Rect(100, y + 4, fill_w, 8), border_radius=3)
            except Exception:
                pass
            surface.blit(font_small.render(ts.label, True, INSPECTOR_TEXT), (228, y))
            y += 18

        y += 8
        for line in wrap_text(portrait.summary, max_chars=58):
            surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
            y += 16

        y += 8
        if portrait.strengths:
            surface.blit(font_small.render(tr("Сильные стороны:"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 16
            for item in portrait.strengths:
                surface.blit(font_small.render(f"  + {item}", True, (80, 150, 80)), (0, y))
                y += 15
        if portrait.weaknesses:
            surface.blit(font_small.render(tr("Слабые стороны:"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 16
            for item in portrait.weaknesses:
                surface.blit(font_small.render(f"  - {item}", True, (180, 80, 60)), (0, y))
                y += 15
        if portrait.neutral_traits:
            surface.blit(font_small.render(tr("Нейтральные:"), True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 16
            for item in portrait.neutral_traits:
                surface.blit(font_small.render(f"  ~ {item}", True, INSPECTOR_MUTED_TEXT), (0, y))
                y += 15
        return y

    def _draw_mutation_effects(self, surface: Any, font: Any, font_small: Any, y: int, mutations: list[Any]) -> int:
        valence_colors = {
            "positive": (80, 150, 80),
            "negative": (180, 80, 60),
            "neutral": INSPECTOR_MUTED_TEXT,
        }
        magnitude_prefix = {"major": "*", "moderate": "+", "minor": "."}
        surface.blit(font.render(tr("Изменения в генах"), True, INSPECTOR_TEXT), (0, y))
        y += 22
        for mut in mutations[:8]:
            color = valence_colors.get(getattr(mut, "valence", "neutral"), INSPECTOR_MUTED_TEXT)
            prefix = magnitude_prefix.get(getattr(mut, "magnitude", "minor"), ".")
            delta = _safe_float(getattr(mut, "delta", 0.0), 0.0)
            header = f"{prefix} {getattr(mut, 'gene_key', ''):<28} {delta:+.3f}"
            surface.blit(font_small.render(header, True, color), (0, y))
            y += 15
            surface.blit(font_small.render(f"  -> {getattr(mut, 'consequence_short', '')}", True, INSPECTOR_TEXT), (0, y))
            y += 14
            for line in wrap_text(f"  {getattr(mut, 'consequence_detail', '')}", max_chars=62):
                surface.blit(font_small.render(line, True, INSPECTOR_MUTED_TEXT), (0, y))
                y += 13
            y += 4
        return y

    def _draw_lineage_trend(self, surface: Any, font: Any, font_small: Any, y: int, trend_points: list[Any]) -> int:
        surface.blit(font.render(tr("Тренд линии"), True, INSPECTOR_TEXT), (0, y))
        y += 22
        names = " → ".join(_safe_str(getattr(point, "display_name", ""), "") for point in trend_points)
        for line in wrap_text(names, max_chars=60):
            surface.blit(font_small.render(line, True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 14
        y += 4

        for gene_key in LINEAGE_TRACKED_GENES:
            values = [point.gene_values[gene_key] for point in trend_points if gene_key in getattr(point, "gene_values", {})]
            if len(values) < 2:
                continue
            label = ui_label("lineage_gene", gene_key, gene_key.replace("_", " "))
            value_chain = " → ".join(f"{float(value):.2f}" for value in values)
            description = describe_lineage_trend(trend_points, gene_key)
            text = f"{label}: {value_chain}; {description}"
            for line in wrap_text(text, max_chars=62):
                surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
                y += 15
            y += 2

        if self._data is not None and self._data.is_deceased:
            y += 4
            stress_vals = [f"{_safe_float(getattr(point, 'stress_at_death', 0.0), 0.0):.2f}" for point in trend_points if _safe_float(getattr(point, "stress_at_death", 0.0), 0.0) > 0]
            if stress_vals:
                surface.blit(font_small.render(tr("Стресс при смерти:"), True, INSPECTOR_MUTED_TEXT), (0, y))
                surface.blit(font_small.render(" → ".join(stress_vals), True, INSPECTOR_TEXT), (148, y))
                y += 16
            cort_vals = [f"{_safe_float(getattr(point, 'cortisol_at_death', 0.0), 0.0):.2f}" for point in trend_points if _safe_float(getattr(point, "cortisol_at_death", 0.0), 0.0) > 0]
            if cort_vals:
                surface.blit(font_small.render(tr("Кортизол при смерти:"), True, INSPECTOR_MUTED_TEXT), (0, y))
                surface.blit(font_small.render(" → ".join(cort_vals), True, INSPECTOR_TEXT), (148, y))
                y += 16
        return y

    def _draw_genome_table_collapsible(self, surface: Any, font: Any, font_small: Any, font_mono: Any, y: int) -> int:
        assert self._data is not None
        genes = sorted(self._data.genome_genes.items(), key=lambda pair: pair[0])
        self._genome_table_toggle_rect_y = y
        label = tr("v все гены") if self._genome_table_expanded else tr("> все гены")
        if genes:
            label = f"{label} ({len(genes)})"
        surface.blit(font_small.render(label, True, INSPECTOR_MUTED_TEXT), (0, y))
        if not genes:
            y += 18
            surface.blit(font_small.render(tr("Геном недоступен"), True, INSPECTOR_MUTED_TEXT), (0, y))
            return y + 22
        if not self._genome_table_expanded:
            return y + 18
        y += 20
        for key, value in genes:
            surface.blit(font_mono.render(f"{key:<28} {value:>8.5f}", True, INSPECTOR_TEXT), (0, y))
            y += 15
        return y + 6

    def _draw_tab_history(self, surface: Any, font: Any, font_small: Any) -> int:
        assert self._data is not None
        y = 6
        title = tr("История (при смерти)") if self._data.is_deceased else tr("История")
        surface.blit(font.render(title, True, INSPECTOR_TEXT), (0, y))
        y += 24
        if not self._data.recent_interactions:
            summary = tr("всего взаимодействий: {n}").format(
                n=sum(item.get("interactions", 0) for item in self._data.known_agents)
            )
            surface.blit(font_small.render(summary, True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 18
            surface.blit(font_small.render(tr("Подробная история недоступна"), True, INSPECTOR_MUTED_TEXT), (0, y))
            return y + 18
        for item in self._data.recent_interactions:
            outcome = _outcome_ru(item.get("outcome", "?"))
            line = tr("[{time:.1f}] {kind} с {name} -> {outcome} Δ{delta:+.2f}").format(
                time=float(item.get("time", 0.0) or 0.0),
                kind=item.get("type", "social"),
                name=item.get("with_name", "?"),
                outcome=outcome,
                delta=float(item.get("affect_delta", 0.0) or 0.0),
            )
            surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
            y += 18
        return y + 6


__all__ = [
    "AgentInspectorOverlay",
    "InspectorData",
    "build_inspector_data_from_agent",
    "build_inspector_data_from_memorial",
]
