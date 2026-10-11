# Спецификация пакета B — EpigenomeSnapshot

English version: [SPEC_B_EpigenomeSnapshot.en.md](SPEC_B_EpigenomeSnapshot.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Проект:** NOWA (расширение существующего)  
**Файл:** `src/epigenome.py`  
**Зависимости:** только стандартная библиотека Python (`math`, `random`, `dataclasses`, `typing`)  
**Внешние зависимости:** нет (данные передаются как словари — без прямого импорта модулей NOWA)  
**Версия спецификации:** 1.0

---

## 1. Назначение

`EpigenomeSnapshot` — частичная передача консолидированной памяти от родителей к потомку.  
В отличие от генома (архитектурные параметры), эпигеном несёт **приобретённые знания**:  
паттерны поведения, семантические действия, оценки ценности состояний.

Биологическая аналогия: эпигенетическое наследование + культурная передача.  
Агент рождается не с чистой памятью, а с "воспоминаниями предков" — зашумлёнными,  
частичными, но реальными.

**Ключевой принцип:** инъекция эпигенома происходит **до первого сна** нового агента.  
Сон консолидирует унаследованные паттерны наравне с собственным опытом.

Путь рождения в колонии копирует геном кроссовером и мутацией. Вкладка «Геном» инспектора в прогоне с зерном 11 показывает этот портрет и сдвиги от середины родителей: [Эволюция в действии](../README.md#evolyutsiya-v-deystvii).

---

## 2. Источники данных

Эпигеном извлекается из трёх модулей NOWA:

### 2.1 CortexMemory — стабильные паттерны

Источник: `agent.cortex` — паттерны с высоким `reinforcement_count`.  
Что передаётся: контекст → действие + сила паттерна.

```python
# Структура одной записи паттерна
@dataclass
class InheritedPattern:
    context_signature: str    # хеш контекста
    action: str               # предпочтительное действие
    strength: float           # сила паттерна [0.0, 1.0]
    reinforcement_count: int  # сколько раз был подкреплён
```

### 2.2 ActionSelector SAC metadata — семантические действия

Источник: `agent.selector.action_metadata` — записи с высоким `stability_score`.  
Что передаётся: `predicted_effect`, `semantic_confidence`, `stability_score`.

```python
# Структура одной записи действия
@dataclass
class InheritedAction:
    action_id: str                       # идентификатор действия
    predicted_effect: Dict[str, float]   # ожидаемые эффекты
    semantic_confidence: float           # уверенность [0.0, 1.0]
    stability_score: float               # стабильность [0.0, 1.0]
    success_rate: float                  # историческая успешность [0.0, 1.0]
```

### 2.3 ValueLayer — оценки ценности состояний

Источник: `agent.value_layer` — записи с высокой `confirmation_count`.  
Что передаётся: ключ состояния + оценка ценности + уверенность.

```python
# Структура одной записи ценности
@dataclass
class InheritedValue:
    state_key: str          # ключ состояния (строка-хеш)
    value: float            # оценка ценности [-1.0, 1.0]
    confidence: float       # уверенность [0.0, 1.0]
    confirmation_count: float  # количество подтверждений
```

---

## 3. Структура EpigenomeSnapshot

```python
@dataclass(frozen=True)
class EpigenomeSnapshot:
    patterns: Tuple[InheritedPattern, ...]    # паттерны из cortex
    actions: Tuple[InheritedAction, ...]      # SAC metadata
    values: Tuple[InheritedValue, ...]        # оценки value_layer
    source_generation: int                    # поколение источника
    source_lineage_id: str                    # линия источника
    extraction_timestamp: float               # время извлечения
```

**Ограничения:**
- `len(patterns) <= MAX_PATTERNS` (default: 32)
- `len(actions) <= MAX_ACTIONS` (default: 16)
- `len(values) <= MAX_VALUES` (default: 24)
- все числовые поля в указанных диапазонах
- `source_generation >= 0`

---

## 4. API

### 4.1 Извлечение

```python
@classmethod
def extract(
    cls,
    cortex_patterns: List[dict],
    action_metadata: Dict[str, dict],
    value_profiles: Dict[str, dict],
    source_generation: int = 0,
    source_lineage_id: str = "",
    max_patterns: int = 32,
    max_actions: int = 16,
    max_values: int = 24,
    min_reinforcement: int = 2,
    min_stability: float = 0.5,
    min_confirmation: float = 1.0,
) -> "EpigenomeSnapshot":
    """
    Извлечь эпигеном из сырых данных модулей NOWA.

    Принимает данные как словари — без прямого импорта модулей NOWA.
    
    Аргументы:
        cortex_patterns: список словарей паттернов cortex
            ожидаемые ключи: "context_signature", "action",
                             "strength", "reinforcement_count"
        action_metadata: словарь {action_id: metadata_dict}
            ожидаемые ключи: "predicted_effect", "semantic_confidence",
                             "stability_score", "success_rate"
        value_profiles: словарь {state_key: profile_dict}
            ожидаемые ключи: "value", "confidence", "confirmation_count"
        source_generation: поколение агента-источника
        source_lineage_id: lineage_id агента-источника
        max_patterns: максимум паттернов для сохранения
        max_actions: максимум действий для сохранения
        max_values: максимум оценок ценности для сохранения
        min_reinforcement: минимальный reinforcement_count для включения паттерна
        min_stability: минимальный stability_score для включения действия
        min_confirmation: минимальная confirmation_count для включения ценности

    Отбор:
        patterns: топ-N по reinforcement_count (убывание)
        actions: топ-N по stability_score (убывание), только consolidated=True
        values: топ-N по confirmation_count (убывание)

    Возвращает: EpigenomeSnapshot
    
    Ограничения:
        - пустые источники дают пустые коллекции (не ошибка)
        - некорректные записи пропускаются молча
        - max_* клампируется в [1, 256]
    """
```

### 4.2 Инъекция

```python
def inject(
    self,
    target_cortex_patterns: list,
    target_action_metadata: dict,
    target_value_profiles: dict,
    noise_level: float = 0.1,
    rng: random.Random = None,
) -> dict:
    """
    Внедрить унаследованные данные в структуры нового агента.
    
    Принимает и возвращает словари — без прямого импорта модулей NOWA.
    Модифицирует переданные структуры IN-PLACE и возвращает статистику.
    
    Механизм шума:
        - числовые значения: value += N(0, noise_level * value_range)
        - действия: semantic_confidence *= (1 - noise_level * U(0,1))
        - ценности: value += N(0, noise_level), confidence *= (1 - noise_level/2)
    
    Приоритет при конфликтах:
        - если ключ уже существует в target: НЕ перезаписывать
        - наследство добавляется только для отсутствующих ключей
        - исключение: паттерны с strength > existing_strength заменяют
    
    Аргументы:
        target_cortex_patterns: список паттернов нового агента (может быть пустым)
        target_action_metadata: metadata нового агента (может быть пустым)
        target_value_profiles: value profiles нового агента (может быть пустым)
        noise_level: уровень шума при инъекции [0.0, 1.0]
            0.0 = точная копия (клонирование, не рекомендуется)
            0.1 = номинальный (рекомендуется)
            1.0 = максимальный шум (почти потеря наследства)
        rng: генератор случайных чисел
    
    Возвращает: dict со статистикой
    {
        "patterns_injected": int,
        "patterns_skipped": int,
        "actions_injected": int,
        "actions_skipped": int,
        "values_injected": int,
        "values_skipped": int,
        "noise_level": float,
    }
    
    Ограничения:
        - noise_level клампируется в [0.0, 1.0]
        - при noise_level=0.0 возвращает точные копии
        - числовые значения после шума клампируются в допустимые диапазоны
        - никогда не вызывает исключений от некорректных данных
    """
```

### 4.3 Скрещивание эпигеномов

```python
def blend(
    self,
    other: "EpigenomeSnapshot",
    alpha: float = 0.5,
    rng: random.Random = None,
) -> "EpigenomeSnapshot":
    """
    Скрестить два эпигенома в один.
    
    Используется когда у потомка два родителя.
    
    Алгоритм:
        patterns: объединить, при дубликатах взять с большим strength
                  итоговый размер <= MAX_PATTERNS (отбор по strength)
        actions:  объединить, при дубликатах взять с большим stability_score
                  итоговый размер <= MAX_ACTIONS
        values:   при совпадении state_key:
                      value = alpha * self.value + (1-alpha) * other.value
                      confidence = min(self.confidence, other.confidence)
                  уникальные добавляются как есть
                  итоговый размер <= MAX_VALUES (отбор по confirmation_count)
    
    Аргументы:
        other: второй эпигеном
        alpha: вес первого эпигенома для values [0.0, 1.0]
        rng: не используется сейчас, зарезервирован для будущих режимов
    
    Возвращает: новый EpigenomeSnapshot
        source_generation = max(self.source_generation, other.source_generation)
        source_lineage_id = f"{self.source_lineage_id}+{other.source_lineage_id}"[:64]
    
    Ограничения:
        - alpha клампируется в [0.0, 1.0]
        - результат не превышает MAX_* лимиты
        - все числовые значения клампируются в допустимые диапазоны
    """
```

### 4.4 Сериализация

```python
def to_dict(self) -> dict:
    """
    Сериализовать в словарь.
    
    Возвращает:
    {
        "version": "1.0",
        "source_generation": int,
        "source_lineage_id": str,
        "extraction_timestamp": float,
        "patterns": [
            {
                "context_signature": str,
                "action": str,
                "strength": float,
                "reinforcement_count": int,
            },
            ...
        ],
        "actions": [
            {
                "action_id": str,
                "predicted_effect": dict,
                "semantic_confidence": float,
                "stability_score": float,
                "success_rate": float,
            },
            ...
        ],
        "values": [
            {
                "state_key": str,
                "value": float,
                "confidence": float,
                "confirmation_count": float,
            },
            ...
        ],
    }
    """

@classmethod
def from_dict(cls, data: dict) -> "EpigenomeSnapshot":
    """
    Восстановить из словаря.
    
    Некорректные записи пропускаются с предупреждением.
    Отсутствующие поля заполняются нейтральными значениями.
    Размеры коллекций клампируются в MAX_* лимиты.
    """

@classmethod
def empty(cls) -> "EpigenomeSnapshot":
    """Создать пустой эпигеном (для первого поколения)."""
```

### 4.5 Диагностика

```python
def is_empty(self) -> bool:
    """Все коллекции пустые."""

def size(self) -> dict:
    """
    {
        "patterns": int,
        "actions": int,
        "values": int,
        "total": int,
    }
    """

def validate(self) -> List[str]:
    """
    Проверить корректность эпигенома.
    Возвращает список предупреждений (пустой = всё ок).
    Проверяет: диапазоны, NaN/Inf, дубликаты ключей.
    """

def summary(self) -> dict:
    """
    Краткая статистика.
    {
        "patterns_count": int,
        "actions_count": int,
        "values_count": int,
        "mean_pattern_strength": float,
        "mean_action_stability": float,
        "mean_value_confidence": float,
        "source_generation": int,
    }
    """
```

---

## 5. Константы

```python
EPIGENOME_VERSION = "1.0"

MAX_PATTERNS = 32   # максимум паттернов в эпигеноме
MAX_ACTIONS = 16    # максимум действий
MAX_VALUES = 24     # максимум оценок ценности

# Диапазоны числовых полей
PATTERN_STRENGTH_RANGE = (0.0, 1.0)
ACTION_CONFIDENCE_RANGE = (0.0, 1.0)
ACTION_STABILITY_RANGE = (0.0, 1.0)
ACTION_SUCCESS_RANGE = (0.0, 1.0)
VALUE_RANGE = (-1.0, 1.0)
VALUE_CONFIDENCE_RANGE = (0.0, 1.0)
```

---

## 6. Ограничения реализации

1. `EpigenomeSnapshot`, `InheritedPattern`, `InheritedAction`, `InheritedValue` — все `frozen=True`.
2. Коллекции хранятся как `Tuple`, не `List` — для неизменяемости.
3. Никаких импортов модулей NOWA — данные приходят как словари.
4. Никакого numpy — только стандартная библиотека.
5. `inject()` модифицирует переданные структуры IN-PLACE — вызывающий код несёт ответственность за копирование если нужно.
6. `extract()` никогда не вызывает исключений при некорректных данных — только пропускает записи.
7. Файл `epigenome.py` не импортирует `genome.py` — нулевые зависимости между пакетами A и B.
8. Python версия: 3.10+

---

## 7. Тест-кейсы

### TC-01: Пустой эпигеном

```python
epigenome = EpigenomeSnapshot.empty()

assert epigenome.is_empty() is True
assert len(epigenome.patterns) == 0
assert len(epigenome.actions) == 0
assert len(epigenome.values) == 0
assert epigenome.source_generation == 0
assert epigenome.validate() == []
```

### TC-02: Извлечение из корректных данных

```python
cortex_patterns = [
    {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5},
    {"context_signature": "ctx_b", "action": "sleep", "strength": 0.7, "reinforcement_count": 3},
    {"context_signature": "ctx_c", "action": "play", "strength": 0.3, "reinforcement_count": 1},
]
action_metadata = {
    "eat": {
        "predicted_effect": {"hunger": -0.5},
        "semantic_confidence": 0.85,
        "stability_score": 0.9,
        "success_rate": 0.8,
        "consolidated": True,
    },
    "play": {
        "predicted_effect": {"energy": -0.3},
        "semantic_confidence": 0.4,
        "stability_score": 0.3,  # ниже min_stability
        "success_rate": 0.6,
        "consolidated": True,
    },
}
value_profiles = {
    "state_abc": {"value": 0.7, "confidence": 0.8, "confirmation_count": 5.0},
    "state_def": {"value": -0.2, "confidence": 0.3, "confirmation_count": 0.5},  # ниже min_confirmation
}

epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=cortex_patterns,
    action_metadata=action_metadata,
    value_profiles=value_profiles,
    min_reinforcement=2,
    min_stability=0.5,
    min_confirmation=1.0,
)

# Паттерны: ctx_a (5) и ctx_b (3) прошли, ctx_c (1) — нет
assert len(epigenome.patterns) == 2
assert any(p.context_signature == "ctx_a" for p in epigenome.patterns)
assert any(p.context_signature == "ctx_b" for p in epigenome.patterns)

# Действия: "eat" (stability 0.9) прошло, "play" (0.3) — нет
assert len(epigenome.actions) == 1
assert epigenome.actions[0].action_id == "eat"

# Ценности: state_abc (confirmation 5.0) прошла, state_def (0.5) — нет
assert len(epigenome.values) == 1
assert epigenome.values[0].state_key == "state_abc"
```

### TC-03: Отбор топ-N паттернов по reinforcement_count

```python
# 10 паттернов, max_patterns=3
patterns = [
    {"context_signature": f"ctx_{i}", "action": "eat",
     "strength": 0.5, "reinforcement_count": i}
    for i in range(10)
]

epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=patterns,
    action_metadata={},
    value_profiles={},
    max_patterns=3,
    min_reinforcement=0,
)

assert len(epigenome.patterns) == 3
# Топ-3 по reinforcement_count = 9, 8, 7
counts = [p.reinforcement_count for p in epigenome.patterns]
assert sorted(counts, reverse=True) == counts
assert counts[0] == 9
```

### TC-04: Инъекция с шумом не изменяет оригинал

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

original_strength = epigenome.patterns[0].strength

target_patterns = []
target_actions = {}
target_values = {}

stats = epigenome.inject(
    target_cortex_patterns=target_patterns,
    target_action_metadata=target_actions,
    target_value_profiles=target_values,
    noise_level=0.3,
    rng=random.Random(42),
)

# Оригинал не изменён
assert epigenome.patterns[0].strength == original_strength

# Что-то было инъецировано
assert stats["patterns_injected"] == 1
assert len(target_patterns) == 1
```

### TC-05: Инъекция не перезаписывает существующие ключи

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[],
    action_metadata={
        "eat": {
            "predicted_effect": {"hunger": -0.5},
            "semantic_confidence": 0.9,
            "stability_score": 0.8,
            "success_rate": 0.7,
            "consolidated": True,
        }
    },
    value_profiles={},
    min_reinforcement=0,
    min_stability=0.0,
)

# Уже существующее действие в target
existing_confidence = 0.3
target_actions = {
    "eat": {
        "semantic_confidence": existing_confidence,
        "stability_score": 0.1,
    }
}

epigenome.inject(
    target_cortex_patterns=[],
    target_action_metadata=target_actions,
    target_value_profiles={},
    noise_level=0.0,
)

# Существующий ключ не перезаписан
assert target_actions["eat"]["semantic_confidence"] == existing_confidence
```

### TC-06: Инъекция с noise_level=0 — точные значения

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[],
    action_metadata={},
    value_profiles={
        "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
    },
    min_reinforcement=0,
    min_stability=0.0,
    min_confirmation=0.0,
)

target_values = {}
epigenome.inject(
    target_cortex_patterns=[],
    target_action_metadata={},
    target_value_profiles=target_values,
    noise_level=0.0,
    rng=random.Random(0),
)

# Точное значение без шума
assert abs(target_values["state_x"]["value"] - 0.6) < 1e-9
assert abs(target_values["state_x"]["confidence"] - 0.8) < 1e-9
```

### TC-07: Скрещивание — объединение паттернов

```python
epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5},
    ],
    action_metadata={}, value_profiles={},
    min_reinforcement=0,
)

epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_b", "action": "sleep",
         "strength": 0.7, "reinforcement_count": 3},
    ],
    action_metadata={}, value_profiles={},
    min_reinforcement=0,
)

blended = epi_a.blend(epi_b, alpha=0.5)

# Оба паттерна присутствуют
sigs = {p.context_signature for p in blended.patterns}
assert "ctx_a" in sigs
assert "ctx_b" in sigs
```

### TC-08: Скрещивание — дубликаты по state_key усредняются

```python
epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=[], action_metadata={},
    value_profiles={
        "state_x": {"value": 0.8, "confidence": 0.9, "confirmation_count": 4.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
)

epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=[], action_metadata={},
    value_profiles={
        "state_x": {"value": 0.2, "confidence": 0.7, "confirmation_count": 2.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
)

blended = epi_a.blend(epi_b, alpha=0.5)

assert len(blended.values) == 1
blended_val = blended.values[0]
# alpha=0.5: 0.5*0.8 + 0.5*0.2 = 0.5
assert abs(blended_val.value - 0.5) < 1e-9
# confidence = min(0.9, 0.7) = 0.7
assert abs(blended_val.confidence - 0.7) < 1e-9
```

### TC-09: Сериализация round-trip

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5},
    ],
    action_metadata={
        "eat": {
            "predicted_effect": {"hunger": -0.5},
            "semantic_confidence": 0.85,
            "stability_score": 0.9,
            "success_rate": 0.8,
            "consolidated": True,
        }
    },
    value_profiles={
        "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
    source_generation=3,
    source_lineage_id="abc",
)

data = epi.to_dict()
restored = EpigenomeSnapshot.from_dict(data)

assert len(restored.patterns) == len(epi.patterns)
assert len(restored.actions) == len(epi.actions)
assert len(restored.values) == len(epi.values)
assert restored.source_generation == epi.source_generation
assert restored.source_lineage_id == epi.source_lineage_id

# Числовые значения сохранены
assert abs(restored.patterns[0].strength - epi.patterns[0].strength) < 1e-9
assert abs(restored.values[0].value - epi.values[0].value) < 1e-9
```

### TC-10: from_dict с некорректными записями не падает

```python
data = {
    "version": "1.0",
    "source_generation": 1,
    "source_lineage_id": "test",
    "extraction_timestamp": 0.0,
    "patterns": [
        {"context_signature": "good", "action": "eat",
         "strength": 0.8, "reinforcement_count": 3},
        {"context_signature": None, "action": None,  # некорректная
         "strength": "bad", "reinforcement_count": -1},
    ],
    "actions": [],
    "values": [],
}

# Не должен вызывать исключений
epi = EpigenomeSnapshot.from_dict(data)

# Корректная запись принята
assert len(epi.patterns) == 1
assert epi.patterns[0].context_signature == "good"
```

### TC-11: validate обнаруживает проблемы

```python
# Создаём через from_dict с намеренно плохими данными
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    data = {
        "version": "1.0",
        "source_generation": -1,  # нарушение
        "source_lineage_id": "",
        "extraction_timestamp": 0.0,
        "patterns": [
            {"context_signature": "ctx", "action": "eat",
             "strength": 1.5,  # вне [0,1]
             "reinforcement_count": 3},
        ],
        "actions": [],
        "values": [],
    }
    epi = EpigenomeSnapshot.from_dict(data)

issues = epi.validate()
assert len(issues) > 0
```

### TC-12: Скрещивание не превышает MAX_* лимиты

```python
# Создаём два эпигенома с MAX_PATTERNS паттернами каждый
patterns_a = [
    {"context_signature": f"ctx_a_{i}", "action": "eat",
     "strength": 0.9, "reinforcement_count": 10}
    for i in range(MAX_PATTERNS)
]
patterns_b = [
    {"context_signature": f"ctx_b_{i}", "action": "sleep",
     "strength": 0.8, "reinforcement_count": 8}
    for i in range(MAX_PATTERNS)
]

epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=patterns_a, action_metadata={}, value_profiles={},
    min_reinforcement=0, max_patterns=MAX_PATTERNS,
)
epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=patterns_b, action_metadata={}, value_profiles={},
    min_reinforcement=0, max_patterns=MAX_PATTERNS,
)

blended = epi_a.blend(epi_b)

assert len(blended.patterns) <= MAX_PATTERNS
```

### TC-13: summary содержит ожидаемые ключи

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.8, "reinforcement_count": 4}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

s = epi.summary()

required_keys = [
    "patterns_count", "actions_count", "values_count",
    "mean_pattern_strength", "mean_action_stability",
    "mean_value_confidence", "source_generation",
]
for key in required_keys:
    assert key in s, f"Отсутствует ключ: {key}"

assert s["patterns_count"] == 1
assert abs(s["mean_pattern_strength"] - 0.8) < 1e-9
```

### TC-14: Детерминизм при фиксированном rng

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

target1, target2 = [], []

epi.inject(target_cortex_patterns=target1, target_action_metadata={},
           target_value_profiles={}, noise_level=0.3, rng=random.Random(42))

epi.inject(target_cortex_patterns=target2, target_action_metadata={},
           target_value_profiles={}, noise_level=0.3, rng=random.Random(42))

assert target1[0]["strength"] == target2[0]["strength"]
```

### TC-15: empty() проходит validate

```python
epi = EpigenomeSnapshot.empty()
assert epi.validate() == []
assert epi.is_empty() is True
assert epi.size()["total"] == 0
```

### TC-16: lineage_id при blend обрезается до 64 символов

```python
long_id = "x" * 100
epi_a = EpigenomeSnapshot.empty()
epi_b = EpigenomeSnapshot.empty()

# Заменяем lineage_id через from_dict
data_a = epi_a.to_dict()
data_a["source_lineage_id"] = long_id
epi_a = EpigenomeSnapshot.from_dict(data_a)

data_b = epi_b.to_dict()
data_b["source_lineage_id"] = long_id
epi_b = EpigenomeSnapshot.from_dict(data_b)

blended = epi_a.blend(epi_b)
assert len(blended.source_lineage_id) <= 64
```

---

## 8. Примечания для реализующего агента

- `InheritedPattern`, `InheritedAction`, `InheritedValue` — `frozen=True` dataclasses
- Коллекции в `EpigenomeSnapshot` хранить как `tuple`, не `list`
- `extract()` — classmethod, принимает только словари (dict), никаких прямых ссылок на объекты NOWA
- При инъекции паттернов: добавлять как словарь `{"context_signature": ..., "action": ..., "strength": ..., "reinforcement_count": ...}` в список `target_cortex_patterns`
- При инъекции actions: добавлять/пропускать ключи в `target_action_metadata` dict
- При инъекции values: добавлять ключи в `target_value_profiles` dict
- Шум для `strength` паттерна: `N(0, noise_level * 0.1)`, клампировать в [0, 1]
- Шум для `value` ценности: `N(0, noise_level * 0.2)`, клампировать в [-1, 1]
- Шум для `confidence`: умножить на `(1 - noise_level * U(0, 0.5))`, клампировать в [0, 1]
- `extraction_timestamp` заполнять через `time.time()` при вызове `extract()`
- `from_dict()` при восстановлении: если `source_generation < 0` — установить 0
- Порядок паттернов/actions/values в `to_dict()` — убывание по strength/stability/confirmation соответственно
