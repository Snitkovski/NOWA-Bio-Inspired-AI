"""English / Russian strings for the tamagotchi demo.

Russian subtitle text is the lookup key. Default language is English.
``--lang`` and ``NOWA_LANG`` override it; the in-window control toggles it.
"""

from __future__ import annotations

import os

SUPPORTED = ("en", "ru")
DEFAULT_LANG = "en"
_override: str | None = None

PHRASES: dict[str, dict[str, str]] = {}


def _add(ru: str, en: str) -> None:
    PHRASES[ru] = {"en": en, "ru": ru}


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


def tr(text: str, **kwargs: object) -> str:
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


CHAINS: dict[str, dict[str, str]] = {
    "en": {
        "morning_awakening": "morning awakening",
        "eating_and_grooming": "eating and grooming",
        "activity_burst": "activity burst",
        "exploration": "exploration",
        "full_grooming": "full grooming",
        "dust_bathing": "dust bathing",
        "social_contact": "social contact",
        "mild_fear": "mild fear",
        "extreme_fear": "extreme fear",
        "chronic_stress": "chronic stress",
        "bedtime_routine": "bedtime routine",
        "territorial_patrol": "territorial patrol",
        "nesting": "nesting",
        "hyperactivity": "hyperactivity",
    },
    "ru": {
        "morning_awakening": "утреннее пробуждение",
        "eating_and_grooming": "еда и груминг",
        "activity_burst": "всплеск активности",
        "exploration": "исследование",
        "full_grooming": "полный груминг",
        "dust_bathing": "пылевое купание",
        "social_contact": "социальный контакт",
        "mild_fear": "лёгкий страх",
        "extreme_fear": "сильный страх",
        "chronic_stress": "хронический стресс",
        "bedtime_routine": "отход ко сну",
        "territorial_patrol": "обход территории",
        "nesting": "обустройство гнезда",
        "hyperactivity": "гиперактивность",
    },
}


def chain_label(name: str) -> str:
    """Display name for a behavior-chain id. The id itself is not rewritten."""

    key = str(name or "").strip()
    if not key or key == "-":
        return key
    chosen = CHAINS.get(get_language()) or CHAINS["en"]
    if key in chosen:
        return chosen[key]
    if key in CHAINS["en"]:
        return CHAINS["en"][key]
    return key.replace("_", " ")


def assert_catalog_parity() -> None:
    missing = [ru for ru, entry in PHRASES.items() if not entry.get("en") or not entry.get("ru")]
    if missing:
        raise AssertionError(f"empty tamagotchi translations: {missing[:8]}")
    if len({entry["en"] for entry in PHRASES.values()}) < 10:
        raise AssertionError("tamagotchi English catalog is unexpectedly small")
    if set(CHAINS["en"]) != set(CHAINS["ru"]):
        raise AssertionError("tamagotchi chain labels are out of parity")
    if any(not text.strip() for book in CHAINS.values() for text in book.values()):
        raise AssertionError("tamagotchi chain label is empty")


for _ru, _en in {
    "ест гранулы": "eating pellets",
    "ест сено": "eating hay",
    "ест лакомство": "eating a treat",
    "пьет воду": "drinking water",
    "грызет минерал": "gnawing the mineral",
    "спит в домике": "sleeping in the house",
    "дремлет на полке": "dozing on the shelf",
    "отдыхает": "resting",
    "в туалете": "in the litter box",
    "метит территорию": "marking territory",
    "на колесе": "on the wheel",
    "прыгает на полку": "jumping onto the shelf",
    "прыгает вниз": "jumping down",
    "прыгает и играет": "jumping and playing",
    "патрулирует территорию": "patrolling territory",
    "обнюхивает углы": "sniffing corners",
    "обнюхивает воздух": "sniffing the air",
    "стоит на задних лапах": "standing on hind legs",
    "лазит по прутьям": "climbing the bars",
    "висит на прутьях": "hanging on the bars",
    "исследует угол": "exploring a corner",
    "наблюдает": "watching",
    "играет с игрушкой": "playing with a toy",
    "бросает игрушку": "tossing the toy",
    "гонится за игрушкой": "chasing the toy",
    "грызет игрушку": "gnawing the toy",
    "грызет дерево": "gnawing wood",
    "переделает подстилку": "rearranging bedding",
    "копает подстилку": "digging in the bedding",
    "прячет корм": "hiding food",
    "носит предмет": "carrying an object",
    "осматривает новый предмет": "inspecting a new object",
    "решает задачу": "solving a puzzle",
    "купается в пыли": "taking a dust bath",
    "умывается": "washing its face",
    "чистит шерсть": "grooming its fur",
    "чистит хвост": "grooming its tail",
    "чистит лапы": "grooming its paws",
    "чешет голову": "scratching its head",
    "потягивается": "stretching",
    "зевает": "yawning",
    "встряхивается": "shaking off",
    "чрезмерно чистит шерсть": "over-grooming",
    "грызет собственную шерсть": "chewing its own fur",
    "подходит к двери": "approaching the door",
    "издает звук": "making a sound",
    "пищит": "squeaking",
    "лает": "barking",
    "кричит от страха": "crying out in fear",
    "стучит зубами": "chattering its teeth",
    "обнюхивает руку": "sniffing a hand",
    "берет лакомство": "taking a treat",
    "позволяет себя гладить": "allowing pets",
    "просит поглаживаний": "asking to be petted",
    "избегает руки": "avoiding a hand",
    "наблюдает за хозяином": "watching the owner",
    "следит за пальцем": "following a finger",
    "замирает": "freezing",
    "прячется в домике": "hiding in the house",
    "убегает в угол": "fleeing to a corner",
    "издает тревожный звук": "making an alarm call",
    "барабанит лапами": "drumming its feet",
    "теряет шерсть от страха": "fur-slipping from fear",
    "грызет прутья клетки": "gnawing the cage bars",
    "однообразно ходит по клетке": "pacing the cage",
    "прыгает в стену": "jumping at the wall",
    "уши вперед": "ears forward",
    "уши прижаты": "ears back",
    "вибрирует усами": "whiskers twitching",
    "хвост поднят": "tail up",
    "прижимается к земле": "crouching low",
    "полуприкрытые глаза": "eyes half-closed",
    "вибрирует нос": "nose twitching",
    "дверь": "door",
    "купалка": "dust bath",
    "поилка": "water",
    "корм": "pellets",
    "сено": "hay",
    "минерал": "mineral",
    "лоток": "litter",
    "колесо": "wheel",
    "игрушка": "toy",
    "Самочувствие": "Wellbeing",
    "Оценить:": "Rate:",
    "голод/энергия": "hunger/energy",
    "исследование": "exploration",
    "соц. контакт": "social contact",
    "любопытство": "curiosity",
    "целенаправленность": "goal focus",
    "нет данных": "no data",
    "нет": "none",
    "прокрутка": "scroll",
    "настроение позитивное": "positive mood",
    "настроение негативное": "negative mood",
    "настроение нейтральное": "neutral mood",
    "высокая активация": "high activation",
    "низкая активность": "low activity",
    "стресс": "stress",
    "доверие": "trust",
    "сильная потребность: {label}": "strong need: {label}",
    "умеренная потребность: {label}": "moderate need: {label}",
    "нет сильных желаний": "no strong desires",
    "Симуляция: {time:.1f}с   тик: {tick}": "Simulation: {time:.1f}s   tick: {tick}",
    "пауза": "paused",
    "активен": "running",
    "Режим: {mode}": "Mode: {mode}",
    "Мысли и намерения:": "Thoughts and intentions:",
    "Сценарий: {chain} ({progress}/{length})": "Scenario: {chain} ({progress}/{length})",
    "Следующие шаги: {steps}": "Next steps: {steps}",
    "Чувства:": "Feelings:",
    "Валентность={valence}  Возбуждение={arousal}": "Valence={valence}  Arousal={arousal}",
    "Стресс={stress}  Любопытство={curiosity}": "Stress={stress}  Curiosity={curiosity}",
    "Доверие={trust}  Стабильность={stability}": "Trust={trust}  Stability={stability}",
    "Привязанность={attachment}": "Attachment={attachment}",
    "Интерпретация: {text}": "Reading: {text}",
    "Желания и потребности:": "Wants and needs:",
    "Драйвы:": "Drives:",
    "Бодрость={wake:.2f}   Надёжность когниций={cog:.2f}": "Wakefulness={wake:.2f}   Cognitive reliability={cog:.2f}",
    "Желания:": "Desires:",
    "Поведение сейчас:": "Behavior now:",
    "Действие: {action}": "Action: {action}",
    "Анимация: {anim}   Позиция: {position}": "Animation: {anim}   Position: {position}",
    "До конца действия: {remain:.1f}с   кулдаун цепочки: {cool:.1f}с": "Action remaining: {remain:.1f}s   chain cooldown: {cool:.1f}s",
    "Выполнено действий: {actions}   цепочек: {chains}": "Actions done: {actions}   chains: {chains}",
    "Память и обучение:": "Memory and learning:",
    "Записей памяти: {entries}   успехов: {success:.0f}%   ср. награда: {reward:+.2f}": "Memory entries: {entries}   success: {success:.0f}%   mean reward: {reward:+.2f}",
    "Предпочитаемые цепочки: {chains}": "Preferred chains: {chains}",
    "Скрыть состояние питомца": "Hide pet state",
    "Показать состояние питомца": "Show pet state",
    "Выключить звук": "Mute",
    "Включить звук": "Sound on",
    "Текущее состояние персонажа": "Current character state",
    "Тамагочи — шиншилла": "Tamagotchi — chinchilla",
}.items():
    _add(_ru, _en)
