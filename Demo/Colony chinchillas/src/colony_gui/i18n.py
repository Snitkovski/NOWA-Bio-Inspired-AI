"""English / Russian strings for the colony demo.

Default language is English. ``--lang`` and ``NOWA_LANG`` override it, and the
in-window EN/RU control calls :func:`set_language`.
"""

from __future__ import annotations

import os
from typing import Mapping

SUPPORTED = ("en", "ru")
DEFAULT_LANG = "en"

_override: str | None = None


def set_language(lang: str) -> None:
    global _override
    if lang not in SUPPORTED:
        raise ValueError(f"Unsupported language: {lang}")
    _override = lang


def reset_language() -> None:
    global _override
    _override = None


def get_language() -> str:
    if _override in SUPPORTED:
        return _override
    env = os.environ.get("NOWA_LANG", "").strip().lower()
    if env in SUPPORTED:
        return env
    return DEFAULT_LANG


def toggle_language() -> str:
    nxt = "ru" if get_language() == "en" else "en"
    set_language(nxt)
    return nxt


# Keyed catalogs. EN and RU must contain the same keys.
TABLES: dict[str, dict[str, dict[str, str]]] = {
    "action": {
        "en": {
            "explore": "exploring",
            "eat": "eating",
            "drink": "drinking",
            "sleep": "sleeping",
            "groom_self": "grooming",
            "run_wheel": "running the wheel",
            "hide": "hiding",
            "socialize": "socializing",
            "play": "playing",
            "allogroom": "allogrooming",
            "play_invite": "inviting play",
            "share_knowledge": "sharing knowledge",
            "chase": "chasing",
            "sleep_together": "sleeping together",
            "mount_display": "courtship",
            "nurse": "nursing a juvenile",
            "rest": "resting",
            "idle": "idle",
            "dead": "dead",
            "sniff_greet": "sniff greeting",
        },
        "ru": {
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
            "play_invite": "приглашает играть",
            "share_knowledge": "делится знанием",
            "chase": "преследует",
            "sleep_together": "спят вместе",
            "mount_display": "брачное поведение",
            "nurse": "ухаживает за детёнышем",
            "rest": "отдыхает",
            "idle": "бездействует",
            "dead": "мертв",
            "sniff_greet": "обнюхивание-приветствие",
        },
    },
    "action_short": {
        "en": {
            "eat": "food",
            "drink": "water",
            "sleep": "sleep",
            "hide": "hiding",
            "explore": "exploring",
            "rest": "rest",
            "socialize": "socializing",
            "play": "play",
            "groom_self": "grooming",
            "run_wheel": "wheel",
            "idle": "waiting",
        },
        "ru": {
            "eat": "еда",
            "drink": "вода",
            "sleep": "сон",
            "hide": "укрытие",
            "explore": "исследование",
            "rest": "отдых",
            "socialize": "социализация",
            "play": "игра",
            "groom_self": "самоуход",
            "run_wheel": "колесо",
            "idle": "ожидание",
        },
    },
    "zone": {
        "en": {
            "floor": "floor",
            "corner": "corner",
            "litter": "litter box",
            "toy": "toy",
            "object": "object",
            "house": "house",
            "dustbath": "dust bath",
            "waterer": "water bottle",
            "bowl_pellets": "pellet bowl",
            "bowl_hay": "hay bowl",
            "mineral": "mineral stone",
            "wheel": "wheel",
            "shelf_lower": "lower shelf",
            "shelf_mid": "middle shelf",
            "shelf_upper": "upper shelf",
            "bars": "bars",
            "bars_top": "top of the bars",
            "door": "door",
            "current": "current spot",
        },
        "ru": {
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
        },
    },
    "furniture": {
        "en": {
            "door": "door",
            "house": "house",
            "dustbath": "dust bath",
            "waterer": "water",
            "bowl_pellets": "pellets",
            "bowl_hay": "hay",
            "mineral": "mineral",
            "litter": "litter",
            "wheel": "wheel",
            "toy": "toy",
            "object": "object",
        },
        "ru": {
            "door": "дверь",
            "house": "домик",
            "dustbath": "купалка",
            "waterer": "поилка",
            "bowl_pellets": "корм",
            "bowl_hay": "сено",
            "mineral": "минерал",
            "litter": "лоток",
            "wheel": "колесо",
            "toy": "игрушка",
            "object": "объект",
        },
    },
    "age": {
        "en": {"juvenile": "juvenile", "adult": "adult"},
        "ru": {"juvenile": "детёныш", "adult": "взрослый"},
    },
    "context": {
        "en": {
            "food_critical": "critically low food",
            "food_low": "low food",
            "food_ok": "enough food",
            "water_critical": "critically low water",
            "stranger_nearby": "a stranger nearby",
            "alarm_call": "alarm call",
            "pregnant": "pregnant",
            "estrus": "estrus",
            "juvenile": "juvenile",
            "high_stress": "high stress",
            "bored": "bored",
            "hunger_high": "very hungry",
            "hunger_critical": "critically hungry",
            "thirst_high": "very thirsty",
            "thirst_critical": "critically thirsty",
            "wakefulness_high": "very sleepy",
            "wakefulness_critical": "critically sleepy",
        },
        "ru": {
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
        },
    },
    "relationship": {
        "en": {
            "stranger": "stranger",
            "acquaintance": "acquaintance",
            "bonded": "bonded",
            "rival": "rival",
            "mate": "mate",
            "kin": "kin",
            "archived": "archived",
        },
        "ru": {
            "stranger": "незнакомец",
            "acquaintance": "знакомый",
            "bonded": "связанный",
            "rival": "соперник",
            "mate": "партнёр",
            "kin": "родня",
            "archived": "архив",
        },
    },
    "outcome": {
        "en": {
            "accepted": "accepted",
            "completed": "completed",
            "rejected": "rejected",
            "timeout": "timeout",
            "interrupted": "interrupted",
        },
        "ru": {
            "accepted": "принято",
            "completed": "завершено",
            "rejected": "отклонено",
            "timeout": "таймаут",
            "interrupted": "прервано",
        },
    },
    "consequence": {
        "en": {
            "none": "no consequence",
            "success": "success",
            "failure": "failure",
            "accepted": "accepted",
            "rejected": "rejected",
            "completed": "completed",
        },
        "ru": {
            "none": "без последствий",
            "success": "успех",
            "failure": "неудача",
            "accepted": "принято",
            "rejected": "отклонено",
            "completed": "завершено",
        },
    },
    "affect": {
        "en": {
            "stress": "stress",
            "valence": "valence",
            "arousal": "arousal",
            "attachment": "attachment",
            "curiosity": "curiosity",
            "trust": "trust",
            "dominance": "dominance",
            "energy": "energy",
            "social_drive": "social need",
        },
        "ru": {
            "stress": "стресс",
            "valence": "валентность",
            "arousal": "возбуждение",
            "attachment": "привязанность",
            "curiosity": "любопытство",
            "trust": "доверие",
            "dominance": "доминантность",
            "energy": "энергия",
            "social_drive": "соц. потребность",
        },
    },
    "neuro": {
        "en": {
            "dopamine": "dopamine",
            "serotonin": "serotonin",
            "norepinephrine": "norepinephrine",
            "cortisol": "cortisol",
            "acetylcholine": "acetylcholine",
        },
        "ru": {
            "dopamine": "дофамин",
            "serotonin": "серотонин",
            "norepinephrine": "норадреналин",
            "cortisol": "кортизол",
            "acetylcholine": "ацетилхолин",
        },
    },
    "wake": {
        "en": {
            "wakefulness": "wakefulness",
            "sleep_pressure": "sleep pressure",
            "circadian": "circadian rhythm",
            "alertness": "alertness",
        },
        "ru": {
            "wakefulness": "бодрствование",
            "sleep_pressure": "давление сна",
            "circadian": "циркадный ритм",
            "alertness": "бдительность",
        },
    },
    "memory": {
        "en": {
            "lived_steps": "steps lived",
            "hippocampus_size": "hippocampus (episodes)",
            "cortex_patterns": "cortical patterns",
            "td_error": "TD error",
        },
        "ru": {
            "lived_steps": "прожито шагов",
            "hippocampus_size": "гиппокамп (эпизоды)",
            "cortex_patterns": "корковые паттерны",
            "td_error": "TD-ошибка",
        },
    },
    "trait": {
        "en": {
            "temperament": "Temperament",
            "social": "Sociability",
            "endurance": "Endurance",
            "cognition": "Cognition",
            "lifespan": "Longevity",
        },
        "ru": {
            "temperament": "Темперамент",
            "social": "Социальность",
            "endurance": "Выносливость",
            "cognition": "Когниция",
            "lifespan": "Долгожитие",
        },
    },
    "lineage_gene": {
        "en": {
            "lt_max_lifespan_factor": "Longevity",
            "af_decay_stress": "Stress retention",
            "nm_acc_k_cort": "Cortisol sensitivity",
            "dr_social_drive_baseline": "Sociability",
            "wk_recovery_factor": "Recovery",
            "lr_alpha": "Learning rate",
        },
        "ru": {
            "lt_max_lifespan_factor": "Долгожитие",
            "af_decay_stress": "Накопление стресса",
            "nm_acc_k_cort": "Чувствительность к кортизолу",
            "dr_social_drive_baseline": "Социальность",
            "wk_recovery_factor": "Восстановление",
            "lr_alpha": "Темп обучения",
        },
    },
    "trend_meaning": {
        "en": {
            "lt_max_lifespan_factor.up": "lifespan potential is increasing",
            "lt_max_lifespan_factor.down": "lifespan potential is decreasing",
            "lt_max_lifespan_factor.flat": "lifespan potential is stable",
            "af_decay_stress.up": "stress lingers longer",
            "af_decay_stress.down": "stress fades faster",
            "af_decay_stress.flat": "the stress response is stable",
            "nm_acc_k_cort.up": "the cortisol response is strengthening",
            "nm_acc_k_cort.down": "the cortisol response is softening",
            "nm_acc_k_cort.flat": "the cortisol response is stable",
            "dr_social_drive_baseline.up": "social drive is rising",
            "dr_social_drive_baseline.down": "social drive is falling",
            "dr_social_drive_baseline.flat": "social drive is stable",
            "wk_recovery_factor.up": "recovery is speeding up",
            "wk_recovery_factor.down": "recovery is slowing down",
            "wk_recovery_factor.flat": "recovery is stable",
            "lr_alpha.up": "learning is getting sharper",
            "lr_alpha.down": "learning is getting more cautious",
            "lr_alpha.flat": "the learning rate is stable",
        },
        "ru": {
            "lt_max_lifespan_factor.up": "потенциал жизни усиливается",
            "lt_max_lifespan_factor.down": "потенциал жизни снижается",
            "lt_max_lifespan_factor.flat": "потенциал жизни стабилен",
            "af_decay_stress.up": "стресс держится дольше",
            "af_decay_stress.down": "стресс рассеивается быстрее",
            "af_decay_stress.flat": "стрессовая реакция стабильна",
            "nm_acc_k_cort.up": "реакция на кортизол усиливается",
            "nm_acc_k_cort.down": "реакция на кортизол смягчается",
            "nm_acc_k_cort.flat": "кортизоловая реакция стабильна",
            "dr_social_drive_baseline.up": "социальный драйв растёт",
            "dr_social_drive_baseline.down": "социальный драйв снижается",
            "dr_social_drive_baseline.flat": "социальный драйв стабилен",
            "wk_recovery_factor.up": "восстановление ускоряется",
            "wk_recovery_factor.down": "восстановление замедляется",
            "wk_recovery_factor.flat": "восстановление стабильно",
            "lr_alpha.up": "обучение становится резче",
            "lr_alpha.down": "обучение становится осторожнее",
            "lr_alpha.flat": "темп обучения стабилен",
        },
    },
    "tab": {
        "en": {
            "nowa": "NOWA",
            "social": "Social",
            "repro": "Repro",
            "genome": "Genome",
            "history": "History",
            "state": "State",
            "evolution": "Evolution",
            "genomes": "Genomes",
            "behavior": "Behavior",
            "forecast": "Forecast",
        },
        "ru": {
            "nowa": "NOWA",
            "social": "Социум",
            "repro": "Репро",
            "genome": "Геном",
            "history": "История",
            "state": "Состояние",
            "evolution": "Эволюция",
            "genomes": "Геномы",
            "behavior": "Поведение",
            "forecast": "Прогноз",
        },
    },
}


def label(table: str, key: str, default: str | None = None) -> str:
    """Look up a keyed UI string in the active language."""

    books = TABLES[table]
    lang = get_language()
    chosen = books.get(lang) or books["en"]
    if key in chosen:
        return chosen[key]
    if key in books["en"]:
        return books["en"][key]
    if default is not None:
        return default
    return str(key)


def has_label(table: str, key: str) -> bool:
    books = TABLES[table]
    return key in books["en"] or key in books["ru"]


# Free-text catalog. The Russian phrase is the lookup key for :func:`tr`.
# Both sides are stored so parity tests can compare key sets.
PHRASES: dict[str, dict[str, str]] = {}


def _add(ru: str, en: str) -> None:
    PHRASES[ru] = {"en": en, "ru": ru}


def tr(text: str, **kwargs: object) -> str:
    """Translate a Russian source phrase when the UI language is English."""

    if text is None:
        return ""
    raw = str(text)
    if get_language() == "en":
        entry = PHRASES.get(raw)
        if entry is not None:
            raw = entry["en"]
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return raw
    return raw


def tone_id(label_text: str) -> str:
    return _CANON.get(label_text, label_text)


def profile_id(label_text: str) -> str:
    return _CANON.get(label_text, label_text)


def character_id(label_text: str) -> str:
    return _CANON.get(label_text, label_text)


def assert_catalog_parity() -> None:
    """Raise if any EN/RU table is missing a key or an empty string."""

    errors: list[str] = []
    for name, books in TABLES.items():
        en_keys = set(books.get("en", {}))
        ru_keys = set(books.get("ru", {}))
        if en_keys != ru_keys:
            errors.append(
                f"{name}: missing ru={sorted(en_keys - ru_keys)} missing en={sorted(ru_keys - en_keys)}"
            )
        for key in en_keys & ru_keys:
            if not str(books["en"][key]).strip() or not str(books["ru"][key]).strip():
                errors.append(f"{name}.{key}: empty translation")
    for ru, entry in PHRASES.items():
        if set(entry) != {"en", "ru"}:
            errors.append(f"phrase {ru!r}: keys {sorted(entry)}")
        if not str(entry.get("en", "")).strip() or not str(entry.get("ru", "")).strip():
            errors.append(f"phrase {ru!r}: empty translation")
        if entry.get("ru") != ru:
            errors.append(f"phrase {ru!r}: ru value drifted")
    if errors:
        raise AssertionError("i18n parity failed:\n" + "\n".join(errors))


_CANON: dict[str, str] = {}


def _canon(kind: str, ru: str, en: str) -> None:
    _add(ru, en)
    _CANON[ru] = f"{kind}"
    _CANON[en] = f"{kind}"


# Tones, profiles, characters — also stable ids for logic.
_canon("panic", "ПАНИКА", "PANIC")
_canon("acute_stress", "ОСТРЫЙ СТРЕСС", "ACUTE STRESS")
_canon("chronic_anxiety", "ХРОНИЧЕСКАЯ ТРЕВОГА", "CHRONIC ANXIETY")
_canon("aggression", "АГРЕССИЯ", "AGGRESSION")
_canon("excitement", "ВОЗБУЖДЕНИЕ", "EXCITEMENT")
_canon("boredom", "СКУКА", "BOREDOM")
_canon("loneliness", "ОДИНОЧЕСТВО", "LONELINESS")
_canon("curiosity", "ЛЮБОПЫТСТВО", "CURIOSITY")
_canon("attachment", "ПРИВЯЗАННОСТЬ", "ATTACHMENT")
_canon("calm", "СПОКОЙСТВИЕ", "CALM")
_canon("fatigue", "УСТАЛОСТЬ", "FATIGUE")
_canon("balance", "РАВНОВЕСИЕ", "BALANCE")
_canon("stress_activation", "СТРЕССОВАЯ АКТИВАЦИЯ", "STRESS ACTIVATION")
_canon("da_depletion", "ДОФАМИНОВОЕ ИСТОЩЕНИЕ", "DOPAMINE DEPLETION")
_canon("da_peak", "ДОФАМИНОВЫЙ ПИК", "DOPAMINE PEAK")
_canon("ht_deficit", "СЕРОТОНИНОВЫЙ ДЕФИЦИТ", "SEROTONIN DEFICIT")
_canon("ach_activation", "ХОЛИНЕРГИЧЕСКАЯ АКТИВАЦИЯ", "CHOLINERGIC ACTIVATION")
_canon("cort_peak", "КОРТИЗОЛЬНЫЙ ПИК", "CORTISOL PEAK")
_canon("balanced_profile", "СБАЛАНСИРОВАННЫЙ ПРОФИЛЬ", "BALANCED PROFILE")
_canon("depression", "ОБЩАЯ ДЕПРЕССИЯ", "GENERAL DEPRESSION")
_canon("hyperactivation", "ГИПЕРАКТИВАЦИЯ", "HYPERACTIVATION")
_canon("standard", "СТАНДАРТНЫЙ", "STANDARD")
_canon("anxious_loner", "ТРЕВОЖНЫЙ ОДИНОЧКА", "ANXIOUS LONER")
_canon("resource_pragmatist", "РЕСУРСНЫЙ ПРАГМАТИК", "RESOURCE PRAGMATIST")
_canon("social_agent", "СОЦИАЛЬНЫЙ АГЕНТ", "SOCIAL AGENT")
_canon("explorer", "ИССЛЕДОВАТЕЛЬ", "EXPLORER")
_canon("passive", "ПАССИВНЫЙ", "PASSIVE")
_canon("withdrawn", "ЗАМКНУТЫЙ", "WITHDRAWN")
_canon("undefined", "НЕОПРЕДЕЛЁННЫЙ", "UNDETERMINED")

# Axis words.
for _ru, _en in {
    "критический": "critical",
    "высокий": "high",
    "умеренный": "moderate",
    "низкий": "low",
    "минимальный": "minimal",
    "экстремальное": "extreme",
    "высокое": "high",
    "умеренное": "moderate",
    "слабое": "weak",
    "фоновое": "background",
    "радостный": "joyful",
    "позитивный": "positive",
    "нейтральный": "neutral",
    "негативный": "negative",
    "тяжёлый": "heavy",
    "отчуждение": "alienated",
    "глубокая": "deep",
    "есть связи": "has bonds",
    "слабая": "weak",
    "активное": "active",
    "подавлено": "suppressed",
    "отсутствует": "absent",
    "недоверие": "distrust",
    "открытый": "open",
    "осторожный": "cautious",
    "закрытый": "closed",
    "подчинённое": "submissive",
    "доминирует": "dominant",
    "уверенный": "confident",
    "уступает": "yielding",
    "полная": "full",
    "достаточная": "sufficient",
    "низкая": "low",
    "критическая": "critical",
    "ищет контактов": "seeking contact",
    "открыт к общению": "open to contact",
    "замкнутый": "withdrawn",
    "избегает": "avoiding",
    "критическое": "critical",
    "повышенное": "elevated",
    "низкое": "low",
    "сонливость": "drowsiness",
    "сильное": "strong",
    "нарастает": "building",
    "активная фаза": "active phase",
    "переходная фаза": "transition phase",
    "вечерняя фаза": "evening phase",
    "высокая": "high",
    "повышенная": "elevated",
    "умеренная": "moderate",
    "активная мотивация": "active motivation",
    "умеренная тяга": "moderate drive",
    "слабая мотивация": "weak motivation",
    "нет мотивации": "no motivation",
    "эмоциональная стабильность": "emotional stability",
    "умеренная стабильность": "moderate stability",
    "нестабильность": "instability",
    "нет стабилизации": "no stabilization",
    "высокая готовность": "high readiness",
    "умеренная активация": "moderate activation",
    "низкая реактивность": "low reactivity",
    "подавленная реакция": "suppressed reaction",
    "хронический стресс": "chronic stress",
    "стрессовая нагрузка": "stress load",
    "лёгкий тонус": "light tone",
    "повышенное внимание": "heightened attention",
    "умеренное внимание": "moderate attention",
    "рассеянность": "scattered attention",
    "когнитивный минимум": "cognitive minimum",
    "очень высокое": "very high",
    "выше среднего": "above average",
    "ниже среднего": "below average",
    "слабо выражено": "weakly expressed",
    "нет данных": "no data",
    "неизвестно": "unknown",
    "да": "yes",
    "нет": "no",
    "вкл": "on",
    "выкл": "off",
}.items():
    _add(_ru, _en)

# Affect / neuro / personality summaries (single-line keys; whitespace preserved).
_add(
    "Агент находится в состоянии острого стресса с экстремальным возбуждением. Все когнитивные ресурсы направлены на выживание, социальные и исследовательские функции подавлены.",
    "The agent is in acute stress with extreme arousal. Cognitive resources are aimed at survival; social and exploratory functions are suppressed.",
)
_add(
    "Высокий стресс при повышенном возбуждении. Агент воспринимает окружение как угрозу. Репродуктивный потенциал и социальность снижены.",
    "High stress with elevated arousal. The agent treats the surroundings as a threat. Reproductive potential and sociability are reduced.",
)
_add(
    "Устойчивый стресс без острого возбуждения - признак хронического состояния. Агент привык к фоновой тревоге, но это истощает ресурсы со временем.",
    "Sustained stress without acute arousal — a chronic pattern. The agent is used to background anxiety, but it drains resources over time.",
)
_add(
    "Высокое возбуждение с доминантной позицией. Агент готов к конфронтации и активно отстаивает территорию или ресурсы.",
    "High arousal with a dominant stance. The agent is ready to confront and actively defends territory or resources.",
)
_add(
    "Высокая активность без стресса - состояние игры или исследования. Агент открыт к новым взаимодействиям и готов к риску.",
    "High activity without stress — play or exploration. The agent is open to new interactions and willing to take risks.",
)
_add(
    "Низкое любопытство и возбуждение при отсутствии стресса. Агент не нашёл стимулирующих занятий. Риск развития апатичного поведения.",
    "Low curiosity and arousal without stress. The agent has not found anything stimulating. Risk of apathetic behavior.",
)
_add(
    "Слабая привязанность и минимальный социальный драйв. Агент изолирован эмоционально, даже если физически находится в колонии.",
    "Weak attachment and minimal social drive. The agent is emotionally isolated even while physically in the colony.",
)
_add(
    "Активное исследовательское состояние без стресса. Агент охотно взаимодействует с окружением и открыт к новому опыту.",
    "Active exploration without stress. The agent readily engages the environment and is open to new experience.",
)
_add(
    "Сильные эмоциональные связи с другими особями. Агент ориентирован на социальные взаимодействия и поддержание отношений.",
    "Strong emotional bonds with other animals. The agent is oriented toward social interaction and maintaining relationships.",
)
_add(
    "Низкий стресс и умеренное возбуждение - оптимальное базовое состояние. Агент доступен для всех типов взаимодействий.",
    "Low stress and moderate arousal — a good baseline. The agent is available for every kind of interaction.",
)
_add(
    "Критически низкий уровень энергии. Все поведенческие стратегии подчинены восстановлению.",
    "Critically low energy. Every behavioral strategy is subordinated to recovery.",
)
_add(
    "Сбалансированный аффективный профиль без выраженных крайностей. Агент находится в стабильном состоянии средней активности.",
    "A balanced affective profile without sharp extremes. The agent is in a stable state of medium activity.",
)
_add(
    "Кортизол подавляет выработку дофамина. Агент лишён мотивационного подкрепления - любые действия воспринимаются как бессмысленные.",
    "Cortisol is suppressing dopamine. The agent has no motivational reinforcement — actions feel pointless.",
)
_add(
    "Норадреналин доминирует при подавленном дофамине. Характерно для состояния угрозы без вознаграждения: агент готов реагировать, но не мотивирован к продуктивным действиям.",
    "Norepinephrine dominates while dopamine is suppressed. Typical of threat without reward: the agent is ready to react but not motivated to act productively.",
)
_add(
    "Высокий дофамин при низком кортизоле. Агент находится в состоянии позитивного предвкушения и высокой мотивации.",
    "High dopamine with low cortisol. The agent is in a state of positive anticipation and high motivation.",
)
_add(
    "Низкий серотонин при высоком кортизоле. Агент лишён эмоциональной стабилизации, что усиливает негативный аффект.",
    "Low serotonin with high cortisol. The agent lacks emotional stabilization, which amplifies negative affect.",
)
_add(
    "Высокий ацетилхолин при подавленном дофамине. Агент сфокусирован и внимателен, но без мотивационного компонента.",
    "High acetylcholine with suppressed dopamine. The agent is focused and attentive, but without a motivational component.",
)
_add(
    "Экстремально высокий кортизол подавляет большинство функций. Хронический стресс ускоряет сенесценцию и блокирует репродуктивную систему.",
    "Extremely high cortisol suppresses most functions. Chronic stress speeds senescence and blocks the reproductive system.",
)
_add(
    "Все нейромодуляторы в рабочем диапазоне без крайностей. Состояние оптимально для обучения и социализации.",
    "All neuromodulators are in a working range without extremes. A good state for learning and socialization.",
)
_add(
    "Все стимулирующие нейромодуляторы на минимуме. Агент в состоянии глубокого торможения.",
    "All stimulating neuromodulators are at a minimum. The agent is deeply inhibited.",
)
_add(
    "Избыточная нейрохимическая активация через норадреналин и ацетилхолин. Агент истощает когнитивные ресурсы быстрее нормы.",
    "Excess neurochemical activation through norepinephrine and acetylcholine. The agent burns cognitive resources faster than usual.",
)
_add(
    "Нейромодуляторный профиль не выявил выраженного паттерна. Состояние умеренной активации.",
    "The neuromodulator profile shows no strong pattern. A state of moderate activation.",
)
_add("Кортизол подавляет выработку дофамина - нет мотивации при стрессе", "Cortisol is suppressing dopamine — no motivation under stress")
_add("Норадреналин без дофамина - тревожная готовность без вознаграждения", "Norepinephrine without dopamine — anxious readiness without reward")
_add("Дефицит серотонина при высоком кортизоле - хроническое негативное состояние", "Serotonin deficit with high cortisol — a chronic negative state")
_add("Ацетилхолин и норадреналин - гиперфокус и тревожная бдительность", "Acetylcholine and norepinephrine — hyperfocus and anxious vigilance")
_add("Дофамин и серотонин - устойчивое позитивное состояние", "Dopamine and serotonin — a stable positive state")
_add("Кортизол и норадреналин - острая стрессовая реакция", "Cortisol and norepinephrine — an acute stress reaction")
_add("Общее истощение нейромодуляторов - апатия и снижение всех функций", "General neuromodulator depletion — apathy and a drop in every function")
_add(
    "Агент выработал стратегию выживания через избегание контактов и укрытие. Хронический стресс подавил любопытство и социальные мотивы. Паттерны питания и укрытия доминируют над всеми другими.",
    "The agent survives by avoiding contact and hiding. Chronic stress has suppressed curiosity and social motives. Feeding and hiding patterns dominate everything else.",
)
_add(
    "Поведение агента максимально ориентировано на ресурсы. Социальные взаимодействия происходят только когда не конкурируют с добычей еды. Стратегия стабильная, но ограниченная.",
    "The agent's behavior is aimed at resources. Social interaction happens only when it does not compete with getting food. A stable but narrow strategy.",
)
_add(
    "Агент сформировал выраженные социальные паттерны. Взаимодействия с колонией являются главным источником подкрепления. Высокий вклад в социальную сплочённость группы.",
    "The agent has formed clear social patterns. Colony interactions are the main source of reinforcement. A large contribution to group cohesion.",
)
_add(
    "Паттерны исследования и физической активности доминируют. Агент активно картирует клетку и тестирует новые стратегии. Когнитивная активность повышена.",
    "Exploration and physical activity dominate. The agent is actively mapping the cage and testing new strategies. Cognitive activity is elevated.",
)
_add(
    "Поведенческий репертуар агента сужен до минимума. Сон и отдых занимают большую часть активного времени. Это может быть признаком хронического истощения.",
    "The agent's behavioral repertoire has narrowed to a minimum. Sleep and rest take most of the active time. This can be a sign of chronic exhaustion.",
)
_add(
    "Агент избегает контактов через самоизоляцию и самоуход. Набор привычек стабилен, но почти не включает социальную компоненту.",
    "The agent avoids contact through self-isolation and self-care. The habit set is stable but almost has no social component.",
)
_add(
    "Достаточно данных для определения устойчивого характера не обнаружено. Агент ещё формирует поведенческий репертуар.",
    "Not enough data for a stable character. The agent is still forming a behavioral repertoire.",
)
_add("агент устойчиво ориентирован на питание", "the agent is steadily oriented toward feeding")
_add("водный дефицит доминирует в решениях", "water deficit dominates decisions")
_add("усталость определяет приоритеты", "fatigue sets the priorities")
_add("исследовательский мотив преобладает", "the exploratory motive prevails")
_add("социальная потребность в центре", "social need is central")
_add("самоуход - текущая стратегия комфорта", "self-care is the current comfort strategy")
_add("физическая активность приоритетна", "physical activity is the priority")
_add("агент в защитной стратегии", "the agent is in a defensive strategy")
_add("игровое поведение доминирует", "play behavior dominates")
_add("восстановление - текущий приоритет", "recovery is the current priority")

# HUD, inspector, lineage, swarm chrome.
for _ru, _en in {
    "Закрыть симуляцию": "Close the simulation",
    "Вы действительно хотите закрыть окно симуляции? Несохранённые данные будут потеряны.": "Close the simulation window? Unsaved data will be lost.",
    "КОЛОНИЯ ({n} живых)": "COLONY ({n} living)",
    "[L] Родословная": "[L] Lineage",
    "стресс": "stress",
    "энергия": "energy",
    "── умершие ({n}) ──": "── deceased ({n}) ──",
    "прожил {lived}": "lived {lived}",
    "потомков {n}": "offspring {n}",
    "Время: {time}   Агентов: {n} (самок: {f}, самцов: {m})   Средний возраст: {age}": "Time: {time}   Agents: {n} (females: {f}, males: {m})   Mean age: {age}",
    "Половозрелые: самки {f}, самцы {m}   Эструс (самки): {estrus}   Беременные: {preg}   Рождений/смертей: {births}/{deaths}   Связи/крепкие пары: {pairs}/{bonded}": "Mature: females {f}, males {m}   Estrus (females): {estrus}   Pregnant: {preg}   Births/deaths: {births}/{deaths}   Bonds/strong pairs: {pairs}/{bonded}",
    "Скорость: x{speed:.1f}   Пауза: {paused}   Звук: {sound}   Управление: SPACE пауза, +/- скорость, M звук, L родословная, A анализ роя, G язык, ESC выход": "Speed: x{speed:.1f}   Pause: {paused}   Sound: {sound}   Controls: SPACE pause, +/- speed, M sound, L lineage, A swarm analysis, G language, ESC quit",
    "Стресс": "Stress",
    "Энергия": "Energy",
    "Сплоченность": "Cohesion",
    "Риск вымирания": "Extinction risk",
    "Корм": "Pellets",
    "Сено": "Hay",
    "Вода": "Water",
    "Родословная | {living} живых {dead} умерших | ESC закрыть": "Lineage | {living} living {dead} dead | ESC to close",
    "Возраст: {age:.1f}s": "Age: {age:.1f}s",
    "Потомков: {n}": "Offspring: {n}",
    "Жив": "Alive",
    "Умер: {cause}": "Died: {cause}",
    "зона: {name}": "zone: {name}",
    "действие: {name}": "action: {name}",
    "последствие: {name}": "consequence: {name}",
    "обратная связь {value}": "feedback {value}",
    "обратная связь": "feedback",
    "социальных контактов рядом: {n}": "social contacts nearby: {n}",
    "социальный контакт рядом": "a social contact nearby",
    "Итоговый аффективный тон: {label}": "Overall affective tone: {label}",
    "Профиль: {label}": "Profile: {label}",
    "Характер: {label}": "Character: {label}",
    "Аффективное состояние": "Affective state",
    "Нейромодуляторы": "Neuromodulators",
    "Бодрость": "Wakefulness",
    "Память": "Memory",
    "Ценностные слои": "Value layers",
    "Привычки": "Habits",
    "Недавние эпизоды": "Recent episodes",
    "Личность": "Personality",
    "NOWA (при смерти)": "NOWA (at death)",
    "NOWA": "NOWA",
    "{title} (при смерти)": "{title} (at death)",
    "Портрет личности": "Personality portrait",
    "Сильные стороны:": "Strengths:",
    "Слабые стороны:": "Weaknesses:",
    "Нейтральные:": "Neutral:",
    "Изменения в генах": "Gene changes",
    "Тренд линии": "Lineage trend",
    "Стресс при смерти:": "Stress at death:",
    "Кортизол при смерти:": "Cortisol at death:",
    "Линия:": "Line:",
    "Линия: -": "Line: -",
    "v все гены": "v all genes",
    "> все гены": "> all genes",
    "Геном недоступен": "Genome unavailable",
    "Esc или клик вне окна": "Esc or click outside",
    "Нет данных.": "No data.",
    "эмоциональная устойчивость": "emotional stability",
    "социальный инстинкт": "social instinct",
    "физическая выносливость": "physical endurance",
    "когнитивные способности": "cognitive ability",
    "потенциал долгожития": "longevity potential",
    "нестабильный темперамент": "unstable temperament",
    "слабые социальные драйвы": "weak social drives",
    "низкая выносливость": "low endurance",
    "ограниченные когнитивные ресурсы": "limited cognitive resources",
    "укороченный жизненный потенциал": "shortened lifespan potential",
    "растёт": "rising",
    "снижается": "falling",
    "стабильно": "stable",
    "↗ растёт": "↗ rising",
    "↘ снижается": "↘ falling",
    "↔ стабильно": "↔ stable",
    "↗ стабильно растёт": "↗ rising steadily",
    "↘ стабильно снижается": "↘ falling steadily",
    "↔": "↔",
    "недостаточно данных": "not enough data",
    "линия без выраженного сдвига": "the line has no clear shift",
    "{direction}: {meaning}": "{direction}: {meaning}",
    "Генетические данные недоступны.": "Genetic data is unavailable.",
    "↑ сдвиг гена {key}": "↑ gene shift {key}",
    "↓ сдвиг гена {key}": "↓ gene shift {key}",
    "Изменение на {delta} относительно родительского среднего.": "Change of {delta} relative to the parental midpoint.",
    "Сдвиг {delta} относительно родительского среднего.": "Shift of {delta} relative to the parental midpoint.",
    "Аналитика роя": "Swarm analytics",
    "Данные ещё не собраны. Нажмите A заново или R для обновления.": "No data yet. Press A again or R to refresh.",
    "ТЕКУЩИЙ СРЕЗ КОЛОНИИ": "CURRENT COLONY SNAPSHOT",
    "sim_time: {time}  |  живых: {living} ({female}F {male}M)  |  умерших: {dead}": "sim_time: {time}  |  living: {living} ({female}F {male}M)  |  dead: {dead}",
    "Поколения: G{a}-G{b}  |  средний возраст: {age}  |  спящих: {sleeping}": "Generations: G{a}-G{b}  |  mean age: {age}  |  sleeping: {sleeping}",
    "Аффективный срез": "Affective snapshot",
    "Итоговый аффективный тон роя: {tone}": "Overall swarm affective tone: {tone}",
    "СТАБИЛЬНЫЙ ФОН": "STABLE BACKGROUND",
    "критический у {n} из {total}": "critical in {n} of {total}",
    "кортизол": "cortisol",
    "социал. драйв": "social drive",
    "любопытство": "curiosity",
    "Нейрохимия популяции": "Population neurochemistry",
    "дофамин": "dopamine",
    "серотонин": "serotonin",
    "норадреналин": "norepinephrine",
    "ацетилхолин": "acetylcholine",
    "Ресурсы": "Resources",
    "корм": "pellets",
    "сено": "hay",
    "вода": "water",
    "тренд: {trend}  Δ{magnitude:.2f}": "trend: {trend}  Δ{magnitude:.2f}",
    "ЭВОЛЮЦИОННЫЕ ТРЕНДЫ ПО ПОКОЛЕНИЯМ": "EVOLUTIONARY TRENDS ACROSS GENERATIONS",
    "{n} поколений  |  {dead} умерших агентов в базе": "{n} generations  |  {dead} dead agents on record",
    "Для эволюционных трендов нужно минимум два поколения.": "Evolutionary trends need at least two generations.",
    "Стресс и кортизол": "Stress and cortisol",
    "Продолжительность жизни": "Lifespan",
    "ср. прожито шагов": "mean steps lived",
    "Энергия при смерти": "Energy at death",
    "Репродукция": "Reproduction",
    "потомков/агента": "offspring/agent",
    "ЭВОЛЮЦИЯ ГЕНОМА ПО ПОКОЛЕНИЯМ": "GENOME EVOLUTION ACROSS GENERATIONS",
    "{n} отслеживаемых генов | под отбором: {sel} | стабильных: {stable}": "{n} tracked genes | under selection: {sel} | stable: {stable}",
    "Гены под активным отбором": "Genes under active selection",
    "Выраженного направленного отбора пока не видно.": "No clear directional selection yet.",
    "Стабильные гены": "Stable genes",
    "Генетическое разнообразие": "Genetic diversity",
    "Текущий индекс: {value:.2f}": "Current index: {value:.2f}",
    "Данных пока нет.": "No data yet.",
    "ПОВЕДЕНЧЕСКИЙ ПРОФИЛЬ КОЛОНИИ": "COLONY BEHAVIORAL PROFILE",
    "Текущее распределение действий": "Current action distribution",
    "Социальная структура": "Social structure",
    "Всего известных пар: {n}": "Known pairs: {n}",
    "Крепкие пары: {n}": "Strong pairs: {n}",
    "Без связей: {n} агентов": "Without bonds: {n} agents",
    "Индекс сплочённости: {value:.2f}": "Cohesion index: {value:.2f}",
    "Характеры роя": "Swarm characters",
    "Гиппокамп и кортекс": "Hippocampus and cortex",
    "Средний размер гиппокампа: {mean:.0f} эпизодов (±{std:.0f})": "Mean hippocampus size: {mean:.0f} episodes (±{std:.0f})",
    "Средний размер кортекса: {mean:.0f} паттернов (±{std:.0f})": "Mean cortex size: {mean:.0f} patterns (±{std:.0f})",
    "Топ доминирующих привычек роя:": "Top dominant swarm habits:",
    "ЭВОЛЮЦИОННЫЙ ПРОГНОЗ": "EVOLUTIONARY FORECAST",
    "Индекс здоровья колонии": "Colony health index",
    "Риски": "Risks",
    "Позитивные тренды": "Positive trends",
    "Давление отбора": "Selection pressure",
    "Главный фактор: {name}": "Main factor: {name}",
    "Адаптируется: {names}": "Adapting: {names}",
    "Без отбора: {names}": "Not under selection: {names}",
    "Итоговый вывод": "Summary",
    "Аналитика роя  |  живых: {living}  умерших: {dead}  поколений: {gens}": "Swarm analytics  |  living: {living}  dead: {dead}  generations: {gens}",
    "ESC / A закрыть   ← → вкладки   R обновить": "ESC / A close   ← → tabs   R refresh",
    "Критических рисков не выявлено": "No critical risks detected",
    "Позитивные тренды пока не выражены": "No clear positive trends yet",
    "Хронический кортизол блокирует репродукцию": "Chronic cortisol is blocking reproduction",
    "Потенциальная продолжительность жизни сокращается": "Potential lifespan is shrinking",
    "Низкое генетическое разнообразие - founder effect": "Low genetic diversity — founder effect",
    "Половой дисбаланс угрожает размножению": "Sex imbalance threatens breeding",
    "Агенты умирают с истощёнными энергетическими резервами": "Agents are dying with depleted energy reserves",
    "Слабая социальная сплочённость - изоляция особей": "Weak social cohesion — individuals are isolated",
    "Высокий риск вымирания по оценке ColonyPopulationObserver": "High extinction risk according to ColonyPopulationObserver",
    "Ген долголетия под положительным отбором": "The longevity gene is under positive selection",
    "Стресс снижается - репродуктивный потенциал растёт": "Stress is falling — reproductive potential is rising",
    "Кортизол снижается - адаптация к стрессу работает": "Cortisol is falling — stress adaptation is working",
    "Социальная сплочённость растёт - колония укрепляется": "Social cohesion is rising — the colony is strengthening",
    "Высокое генетическое разнообразие - хороший эволюционный потенциал": "High genetic diversity — good evolutionary potential",
    "Высокая репродуктивная успешность": "High reproductive success",
    "социальная изоляция": "social isolation",
    "энергетический дефицит": "energy deficit",
    "умеренный отбор по устойчивости": "moderate selection for resilience",
    "высокий": "high",
    "Колония здорова и активно развивается": "The colony is healthy and developing actively",
    "Колония стабильна с умеренными рисками": "The colony is stable with moderate risks",
    "Колония под давлением, требует внимания": "The colony is under pressure and needs attention",
    "Колония в критическом состоянии": "The colony is in a critical state",
    "Колония сейчас оценивается как: {verdict}. Главный фактор отбора - {pressure}. Активно адаптируются: {adapting}. Ключевой риск: {risk}.": "The colony is currently rated: {verdict}. Main selection factor — {pressure}. Actively adapting: {adapting}. Key risk: {risk}.",
    "выраженных генов под отбором нет": "no genes clearly under selection",
    "критических рисков не выявлено": "no critical risks detected",
    "EN": "EN",
    "RU": "RU",
    "дверь": "door",
    "домик": "house",
    "купалка": "dust bath",
    "поилка": "water",
    "минерал": "mineral",
    "лоток": "litter",
    "колесо": "wheel",
    "игрушка": "toy",
    "объект": "object",
    "Социум": "Social",
    "Репро": "Repro",
    "закрыть x": "close x",
    "собственные потомки:": "own offspring:",
    "Нет социальных данных": "No social data",
    "Подробная история недоступна": "Detailed history is unavailable",
    "сено": "hay",
    "энергия": "energy",
}.items():
    _add(_ru, _en)

for _ru, _en in {
    "Гиппокамп: эпизоды памяти": "Hippocampus: memory episodes",
    "Кортекс: паттерны консолидации": "Cortex: consolidation patterns",
    "Данные отсутствуют.": "No data.",
    "Всего эпизодов (на момент смерти): {total}": "Total episodes (at death): {total}",
    "Детальный снимок эпизодов для умершего агента не хранится.": "A detailed episode snapshot is not kept for a dead agent.",
    "Эпизоды гиппокампа отсутствуют.": "No hippocampal episodes.",
    "Всего эпизодов: {total}": "Total episodes: {total}",
    "Показаны последние {n} эпизодов.": "Showing the last {n} episodes.",
    "#{idx} | t={timestamp:.1f}с | действие={action} | результат={consequence}": "#{idx} | t={timestamp:.1f}s | action={action} | result={consequence}",
    "контекст: {text}": "context: {text}",
    "shock={value}": "shock={value}",
    "Всего паттернов (на момент смерти): {total}": "Total patterns (at death): {total}",
    "Детальный снимок паттернов для умершего агента не хранится.": "A detailed pattern snapshot is not kept for a dead agent.",
    "Корковые паттерны отсутствуют.": "No cortical patterns.",
    "Всего паттернов: {total}": "Total patterns: {total}",
    "Показаны {n} наиболее сильных паттернов.": "Showing the {n} strongest patterns.",
    "#{idx} | сила={strength:.3f} | источники={sources} | активации={activations}": "#{idx} | strength={strength:.3f} | sources={sources} | activations={activations}",
    "последствие: {name}": "consequence: {name}",
    "{sex} | G{generation} | возраст {age:.1f}с | шаги {steps}": "{sex} | G{generation} | age {age:.1f}s | steps {steps}",
    "Детали памяти": "Memory details",
    "Нейрохимический профиль": "Neurochemical profile",
    "Бодрствование и энергия": "Wakefulness and energy",
    "Активные привычки": "Active habits",
    "{n} устойчивых паттерна из {total}:": "{n} stable patterns of {total}:",
    "Недавний опыт": "Recent experience",
    "Последние {n} значимых эпизодов из {total}:": "Last {n} significant episodes of {total}:",
    "Интерпретация личности": "Personality interpretation",
    "известных: {known} | слухов получено: {hearsay}": "known: {known} | hearsay received: {hearsay}",
    "{name} [{rel}] симпатия {affinity:.2f} поз. {pos} нег. {neg}": "{name} [{rel}] affinity {affinity:.2f} pos. {pos} neg. {neg}",
    "пол: {sex}": "sex: {sex}",
    "репродуктивный драйв: {value:.3f}": "reproductive drive: {value:.3f}",
    "шаги восстановления: {n}": "cooldown steps: {n}",
    "всего потомков: {n}": "total offspring: {n}",
    "витальность: {value:.3f}": "vitality: {value:.3f}",
    "темп старения: {value:.4f}": "senescence rate: {value:.4f}",
    "беременна: {value}": "pregnant: {value}",
    "причина смерти: {cause}": "cause of death: {cause}",
    "Геном G{generation}": "Genome G{generation}",
    "История (при смерти)": "History (at death)",
    "История": "History",
    "всего взаимодействий: {n}": "total interactions: {n}",
    "[{time:.1f}] {kind} с {name} -> {outcome} Δ{delta:+.2f}": "[{time:.1f}] {kind} with {name} -> {outcome} Δ{delta:+.2f}",
    "(архив)": "(archive)",
    "Решения агента устойчиво направлены к еде.": "The agent's decisions stay aimed at food.",
    "Решения агента вращаются вокруг воды и восстановления баланса.": "The agent's decisions revolve around water and restoring balance.",
    "Сон и восстановление доминируют над прочими действиями.": "Sleep and recovery dominate other actions.",
    "Исследование окружения сейчас является ведущей стратегией.": "Exploring the surroundings is the leading strategy right now.",
    "Защитная стратегия заметно сильнее остальных вариантов.": "A defensive strategy is clearly stronger than the other options.",
    "Агент выбирает экономию сил и восстановление.": "The agent chooses to save energy and recover.",
    "Доминирующее действие задаёт текущую стратегию агента.": "The dominant action sets the agent's current strategy.",
    "• {action} ← {context}     сила {strength:.2f}  ×{count}": "• {action} ← {context}     strength {strength:.2f}  ×{count}",
    "ХРОНИЧЕСКАЯ ТРЕВОГА": "CHRONIC ANXIETY",
    "Связанные: {bonded}   Соперники: {rival}   Родня: {kin}": "Bonded: {bonded}   Rivals: {rival}   Kin: {kin}",
    "Colony GUI — симуляция шиншилл": "Colony GUI — chinchilla simulation",
}.items():
    _add(_ru, _en)

# Gene labels and mutation copy. Imported lazily so this module stays import-safe.
def _load_genome_phrases() -> None:
    from . import i18n_genome

    for ru, en in i18n_genome.GENOME_PHRASES.items():
        if ru not in PHRASES:
            _add(ru, en)


_load_genome_phrases()


def phrase_tables() -> Mapping[str, Mapping[str, str]]:
    """EN and RU views of the free-text catalog, keyed by the Russian phrase."""

    return {
        "en": {ru: entry["en"] for ru, entry in PHRASES.items()},
        "ru": {ru: entry["ru"] for ru, entry in PHRASES.items()},
    }


__all__ = [
    "DEFAULT_LANG",
    "PHRASES",
    "SUPPORTED",
    "TABLES",
    "assert_catalog_parity",
    "character_id",
    "get_language",
    "has_label",
    "label",
    "phrase_tables",
    "profile_id",
    "reset_language",
    "set_language",
    "toggle_language",
    "tone_id",
    "tr",
]
