## Аннотация

English version: [SPEC_NowaTab_Extended.en.md](SPEC_NowaTab_Extended.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Документ специфицирует расширение вкладки NOWA в `AgentInspectorOverlay` и вводит модуль интерпретации `nowa_interpreter`. Предмет спецификации — представление мгновенного когнитивно-аффективного состояния отдельного агента. Числовые оси перестают составлять самодостаточную таблицу: каждое значение получает семантическую метку, пояснение сложившегося состояния и указание на поведенческие следствия.

Расширенная вкладка охватывает итоговый аффективный тон, нейрохимический профиль и взаимодействия модуляторов, бодрствование и циркадную фазу, слои ценности таламического контура, устойчивые кортикальные паттерны как привычки и значимые эпизоды гиппокампа как недавний опыт. Завершающий блок сводит эти сведения к интерпретации личности, выводимой из текущих паттернов. Спецификация задаёт структуры интерпретации аффекта, нейрохимического профиля, слоёв ценности и привычек, а также правила их построения из состояния агента.

В установке колонии шиншилл документ определяет инспекционный слой индивидуального состояния NOWA. Он не изменяет выбор действия и не подменяет когнитивный цикл. Его роль состоит в том, чтобы сделать внутренние переменные агента сопоставимыми для наблюдателя в рассматриваемый момент, в том числе когда снимок относится к состоянию на момент смерти.

# Спецификация: Расширенная вкладка NOWA в AgentInspectorOverlay

**Файл:** `colony_gui/agent_inspector.py` — изменения в методе `_draw_tab_nowa()`  
**Новый модуль:** `colony_gui/nowa_interpreter.py`  
**Версия:** 1.0

---

## 1. Концепция

Вкладка NOWA перестаёт быть таблицей чисел.  
Она становится **психологическим портретом** агента в текущий момент времени.

Каждое значение получает интерпретацию: что оно означает для поведения,
почему сложилось такое состояние, каковы его последствия.

Дополнительно отображаются:
- Уровни Thalamic/Value (T0, T1, T2...) если доступны
- Паттерны консолидации как «привычки» агента
- Эпизоды гиппокампа как «недавний опыт»
- Нейрохимический профиль с интерпретацией взаимодействий

---

## 2. Структура расширенной вкладки

```
┌─────────────────────────────────────────────────────────┐
│  NOWA (при смерти)                                       │
│                                                          │
│  ── АФФЕКТИВНОЕ СОСТОЯНИЕ ─────────────────────────────  │
│  [Итоговый аффективный тон: ПАНИКА]     [цвет: красный] │
│  "Агент находится в состоянии острого стресса.           │
│   Высокое возбуждение блокирует социальные контакты."   │
│                                                          │
│  стресс      ████████████░  0.999  критический           │
│  возбуждение ████████████░  0.999  экстремальное         │
│  валентность ████░░░░░░░░░ -0.473  негативный            │
│  привязанность  ░░░░░░░░░░ -0.073  отчуждение            │
│  любопытство    █░░░░░░░░░  0.039  подавлено             │
│  доверие        ░░░░░░░░░░ -0.286  недоверие             │
│  доминантность  ░░░░░░░░░░ -0.252  подчинённое           │
│                                                          │
│  ── НЕЙРОХИМИЧЕСКИЙ ПРОФИЛЬ ───────────────────────────  │
│  [Профиль: СТРЕССОВАЯ АКТИВАЦИЯ]                        │
│  "Норадреналин доминирует при подавленном дофамине.      │
│   Характерно для состояния угрозы без вознаграждения."  │
│                                                          │
│  дофамин       ░░░░░░░░░░  0.000  нет мотивации         │
│  серотонин     ░░░░░░░░░░  0.000  нет стабилизации      │
│  норадреналин  █████████░  0.873  высокая готовность     │
│  кортизол      ████████░░  0.776  хронический стресс     │
│  ацетилхолин   █████████░  0.908  повышенное внимание    │
│                                                          │
│  ── БОДРСТВОВАНИЕ И ЭНЕРГИЯ ───────────────────────────  │
│  бодрствование  ██████░░░  0.625  умеренное              │
│  давление сна   ██████░░░  0.625  нарастает              │
│  циркадный ритм ██░░░░░░░  0.284  вечерняя фаза          │
│  бдительность   ██████░░░  0.659  повышенная             │
│                                                          │
│  ── VALUE LAYERS (T0 → T2) ────────────────────────────  │
│  T0  [████░░░░]  eat: 0.72  drink: 0.43  sleep: 0.28    │
│  T1  [███░░░░░]  eat: 0.68  explore: 0.31               │
│  T2  [██░░░░░░]  eat: 0.61                               │
│  "Решения агента устойчиво направлены к еде."           │
│                                                          │
│  ── АКТИВНЫЕ ПРИВЫЧКИ (кортекс) ───────────────────────  │
│  3 устойчивых паттерна из 109:                          │
│  ● еда ← миска_корм + голод       сила 0.89  ×47        │
│  ● сон ← усталость + дом          сила 0.71  ×31        │
│  ● избегание ← стресс + незнак.   сила 0.64  ×28        │
│                                                          │
│  ── НЕДАВНИЙ ОПЫТ (гиппокамп) ────────────────────────  │
│  Последние 5 значимых эпизодов из 442:                  │
│  [t=13099] ел ← миска_корм → успех      R=+0.41        │
│  [t=13087] прятался ← стресс → успех    R=+0.12        │
│  [t=13074] социал. ← незнак → отказ     R=−0.23        │
│  [t=13061] пил ← жажда → успех          R=+0.19        │
│  [t=13049] исслед. ← скука → нейтр.     R= 0.00        │
│                                                          │
│  ── ИНТЕРПРЕТАЦИЯ ЛИЧНОСТИ ────────────────────────────  │
│  Характер (из паттернов): ТРЕВОЖНЫЙ ОДИНОЧКА            │
│  "Агент развил стратегию выживания через избегание       │
│   контактов. Паттерны питания доминируют над             │
│   социальными. Хронический стресс подавил любопытство." │
└─────────────────────────────────────────────────────────┘
```

---

## 3. nowa_interpreter.py — новый модуль

### 3.1 Структуры данных

```python
@dataclass
class AffectInterpretation:
    """Интерпретация аффективного состояния агента."""
    tone_label: str           # "ПАНИКА" | "СТРЕСС" | "СПОКОЙСТВИЕ" и т.д.
    tone_color: tuple         # RGB цвет для отображения
    summary: str              # 2-3 предложения описания состояния
    axis_labels: dict[str, str]  # {axis_key: label} краткий ярлык для каждой оси


@dataclass
class NeuroProfile:
    """Интерпретация нейрохимического профиля."""
    profile_label: str        # "СТРЕССОВАЯ АКТИВАЦИЯ" | "ДОФАМИНОВОЕ ИСТОЩЕНИЕ" и т.д.
    summary: str              # 1-2 предложения
    modulator_labels: dict[str, str]  # {nm_key: label}
    interactions: list[str]   # выявленные взаимодействия между нейромодуляторами


@dataclass
class ValueLayerSnapshot:
    """Снапшот одного уровня value/thalamic layer."""
    level: int                # 0, 1, 2...
    top_actions: list[tuple[str, float]]  # [(action, value)] топ-3
    raw_values: dict[str, float]


@dataclass
class HabitPattern:
    """Одна устойчивая привычка из кортекса."""
    context_tokens: list[str]   # условия активации
    action: str                 # действие
    strength: float             # сила паттерна
    activation_count: int       # сколько раз активировался
    consequence: str            # последствие


@dataclass
class RecentEpisode:
    """Один значимый эпизод из гиппокампа."""
    timestamp: float
    action: str
    context_tokens: list[str]
    reward: float
    consequence: str
    encoding_strength: float


@dataclass
class PersonalityReadout:
    """Интерпретация характера по паттернам поведения."""
    character_label: str      # "ТРЕВОЖНЫЙ ОДИНОЧКА" | "ИССЛЕДОВАТЕЛЬ" и т.д.
    summary: str              # 2-3 предложения


@dataclass
class NowaInterpretation:
    """Полная интерпретация вкладки NOWA."""
    affect: AffectInterpretation
    neuro: NeuroProfile
    value_layers: list[ValueLayerSnapshot]   # может быть пустым
    habits: list[HabitPattern]               # топ-5 из кортекса
    recent_episodes: list[RecentEpisode]     # топ-5 значимых из гиппокампа
    personality: PersonalityReadout
```

---

### 3.2 Интерпретация аффекта

#### Тональные состояния

```python
AFFECT_TONES: list[tuple[str, tuple, Callable[[dict], bool]]] = [
    # (label, rgb_color, condition_fn)
    ("ПАНИКА",        (210, 60,  50),  lambda a: a["stress"] > 0.85 and a["arousal"] > 0.80),
    ("ОСТРЫЙ СТРЕСС", (215, 100, 60),  lambda a: a["stress"] > 0.70 and a["arousal"] > 0.60),
    ("ХРОНИЧЕСКАЯ ТРЕВОГА", (200, 140, 70), lambda a: a["stress"] > 0.55 and a["arousal"] < 0.55),
    ("АГРЕССИЯ",      (200, 70,  70),  lambda a: a["arousal"] > 0.75 and a["dominance"] > 0.60),
    ("ВОЗБУЖДЕНИЕ",   (220, 185, 65),  lambda a: a["arousal"] > 0.65 and a["stress"] < 0.45),
    ("СКУКА",         (155, 145, 130), lambda a: a["curiosity"] < 0.20 and a["arousal"] < 0.30),
    ("ОДИНОЧЕСТВО",   (110, 140, 185), lambda a: a["attachment"] < 0.10 and a["social_drive"] < 0.20),
    ("ЛЮБОПЫТСТВО",   (90,  170, 150), lambda a: a["curiosity"] > 0.55 and a["stress"] < 0.40),
    ("ПРИВЯЗАННОСТЬ", (190, 130, 200), lambda a: a["attachment"] > 0.60 and a["trust"] > 0.50),
    ("СПОКОЙСТВИЕ",   (100, 175, 110), lambda a: a["stress"] < 0.25 and a["arousal"] < 0.45),
    ("УСТАЛОСТЬ",     (140, 155, 175), lambda a: a.get("energy", 1.0) < 0.25),
    ("РАВНОВЕСИЕ",    (150, 165, 140), lambda a: True),  # fallback
]
```

#### Ярлыки осей

```python
AXIS_LABELS: dict[str, dict[str, str]] = {
    "stress": {
        "critical":   "критический",     # > 0.85
        "high":       "высокий",          # > 0.65
        "moderate":   "умеренный",        # > 0.40
        "low":        "низкий",           # > 0.15
        "minimal":    "минимальный",      # <= 0.15
    },
    "arousal": {
        "critical":   "экстремальное",
        "high":       "высокое",
        "moderate":   "умеренное",
        "low":        "слабое",
        "minimal":    "фоновое",
    },
    "valence": {
        # valence диапазон [-1, 1]
        "very_neg":   "тяжёлый",          # < -0.60
        "neg":        "негативный",        # < -0.25
        "neutral":    "нейтральный",       # [-0.25, 0.25]
        "pos":        "позитивный",        # > 0.25
        "very_pos":   "радостный",         # > 0.60
    },
    "attachment": {
        "high":       "глубокая",
        "moderate":   "есть связи",
        "low":        "слабая",
        "negative":   "отчуждение",        # < 0
    },
    "curiosity": {
        "high":       "активное",
        "moderate":   "умеренное",
        "low":        "подавлено",
        "minimal":    "отсутствует",
    },
    "trust": {
        "high":       "открытый",
        "moderate":   "осторожный",
        "low":        "закрытый",
        "negative":   "недоверие",
    },
    "dominance": {
        "high":       "доминирует",
        "moderate":   "уверенный",
        "low":        "уступает",
        "negative":   "подчинённое",
    },
    "energy": {
        "high":       "полная",
        "moderate":   "достаточная",
        "low":        "низкая",
        "critical":   "критическая",
    },
    "social_drive": {
        "high":       "ищет контактов",
        "moderate":   "открыт к общению",
        "low":        "замкнутый",
        "minimal":    "избегает",
    },
}
```

#### Summary-тексты для аффекта

```python
AFFECT_SUMMARIES: dict[str, str] = {
    "ПАНИКА": (
        "Агент находится в состоянии острого стресса с экстремальным возбуждением. "
        "Все когнитивные ресурсы направлены на выживание, "
        "социальные и исследовательские функции подавлены."
    ),
    "ОСТРЫЙ СТРЕСС": (
        "Высокий стресс при повышенном возбуждении. "
        "Агент воспринимает окружение как угрозу. "
        "Репродуктивный потенциал и социальность снижены."
    ),
    "ХРОНИЧЕСКАЯ ТРЕВОГА": (
        "Устойчивый стресс без острого возбуждения — признак хронического состояния. "
        "Агент привык к фоновой тревоге, но это истощает ресурсы со временем."
    ),
    "АГРЕССИЯ": (
        "Высокое возбуждение с доминантной позицией. "
        "Агент готов к конфронтации и активно отстаивает территорию или ресурсы."
    ),
    "ВОЗБУЖДЕНИЕ": (
        "Высокая активность без стресса — состояние игры или исследования. "
        "Агент открыт к новым взаимодействиям и готов к риску."
    ),
    "СКУКА": (
        "Низкое любопытство и возбуждение при отсутствии стресса. "
        "Агент не нашёл стимулирующих занятий. "
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
        "Низкий стресс и умеренное возбуждение — оптимальное базовое состояние. "
        "Агент доступен для всех типов взаимодействий."
    ),
    "УСТАЛОСТЬ": (
        "Критически низкий уровень энергии. "
        "Все поведенческие стратегии подчинены восстановлению."
    ),
    "РАВНОВЕСИЕ": (
        "Сбалансированный аффективный профиль без выраженных крайностей. "
        "Агент находится в стабильном состоянии средней активности."
    ),
}
```

---

### 3.3 Интерпретация нейромодуляторов

#### Профили

```python
NEURO_PROFILES: list[tuple[str, Callable[[dict], bool]]] = [
    # (label, condition)
    ("ДОФАМИНОВОЕ ИСТОЩЕНИЕ",
     lambda n: n["dopamine"] < 0.05 and n["cortisol"] > 0.50),
    ("СТРЕССОВАЯ АКТИВАЦИЯ",
     lambda n: n["norepinephrine"] > 0.65 and n["dopamine"] < 0.20 and n["cortisol"] > 0.40),
    ("ДОФАМИНОВЫЙ ПИК",
     lambda n: n["dopamine"] > 0.60 and n["cortisol"] < 0.30),
    ("СЕРОТОНИНОВЫЙ ДЕФИЦИТ",
     lambda n: n["serotonin"] < 0.10 and n["cortisol"] > 0.40),
    ("ХОЛИНЕРГИЧЕСКАЯ АКТИВАЦИЯ",
     lambda n: n["acetylcholine"] > 0.75 and n["dopamine"] < 0.30),
    ("КОРТИЗОЛЬНЫЙ ПИК",
     lambda n: n["cortisol"] > 0.85),
    ("СБАЛАНСИРОВАННЫЙ ПРОФИЛЬ",
     lambda n: all(0.20 < v < 0.75 for v in n.values())),
    ("ОБЩАЯ ДЕПРЕССИЯ",
     lambda n: n["dopamine"] < 0.10 and n["serotonin"] < 0.10 and n["norepinephrine"] < 0.20),
    ("ГИПЕРАКТИВАЦИЯ",
     lambda n: n["norepinephrine"] > 0.80 and n["acetylcholine"] > 0.75),
    ("СТАНДАРТНЫЙ",  # fallback
     lambda n: True),
]
```

#### Ярлыки нейромодуляторов

```python
NM_LABELS: dict[str, dict[str, str]] = {
    "dopamine": {
        "high":    "активная мотивация",
        "moderate":"умеренная тяга",
        "low":     "слабая мотивация",
        "minimal": "нет мотивации",
    },
    "serotonin": {
        "high":    "эмоциональная стабильность",
        "moderate":"умеренная стабильность",
        "low":     "нестабильность",
        "minimal": "нет стабилизации",
    },
    "norepinephrine": {
        "high":    "высокая готовность",
        "moderate":"умеренная активация",
        "low":     "низкая реактивность",
        "minimal": "подавленная реакция",
    },
    "cortisol": {
        "high":    "хронический стресс",
        "moderate":"стрессовая нагрузка",
        "low":     "лёгкий тонус",
        "minimal": "минимальный",
    },
    "acetylcholine": {
        "high":    "повышенное внимание",
        "moderate":"умеренное внимание",
        "low":     "рассеянность",
        "minimal": "когнитивный минимум",
    },
}
```

#### Взаимодействия нейромодуляторов

```python
NM_INTERACTIONS: list[tuple[Callable[[dict], bool], str]] = [
    (lambda n: n["dopamine"] < 0.05 and n["cortisol"] > 0.50,
     "↓ Кортизол подавляет выработку дофамина → нет мотивации при стрессе"),
    (lambda n: n["norepinephrine"] > 0.70 and n["dopamine"] < 0.15,
     "↑ Норадреналин без дофамина → тревожная готовность без вознаграждения"),
    (lambda n: n["serotonin"] < 0.10 and n["cortisol"] > 0.50,
     "↓ Дефицит серотонина при высоком кортизоле → хроническое негативное состояние"),
    (lambda n: n["acetylcholine"] > 0.75 and n["norepinephrine"] > 0.65,
     "↑ Ацетилхолин + норадреналин → гиперфокус и тревожная бдительность"),
    (lambda n: n["dopamine"] > 0.55 and n["serotonin"] > 0.40,
     "↑ Дофамин + серотонин → устойчивое позитивное состояние"),
    (lambda n: n["cortisol"] > 0.80 and n["norepinephrine"] > 0.70,
     "↑ Кортизол + норадреналин → острая стрессовая реакция"),
    (lambda n: n["dopamine"] < 0.10 and n["serotonin"] < 0.10 and n["norepinephrine"] < 0.25,
     "↓ Общее истощение нейромодуляторов → апатия и снижение всех функций"),
]
```

#### Summary-тексты для нейропрофилей

```python
NEURO_SUMMARIES: dict[str, str] = {
    "ДОФАМИНОВОЕ ИСТОЩЕНИЕ": (
        "Кортизол подавляет выработку дофамина. "
        "Агент лишён мотивационного подкрепления — любые действия воспринимаются "
        "как бессмысленные. Репродуктивный драйв и социальность заблокированы."
    ),
    "СТРЕССОВАЯ АКТИВАЦИЯ": (
        "Норадреналин доминирует при подавленном дофамине. "
        "Характерно для состояния угрозы без вознаграждения: агент готов реагировать, "
        "но не мотивирован к продуктивным действиям."
    ),
    "ДОФАМИНОВЫЙ ПИК": (
        "Высокий дофамин при низком кортизоле. "
        "Агент находится в состоянии позитивного предвкушения и высокой мотивации. "
        "Оптимальный момент для социальных взаимодействий и исследований."
    ),
    "СЕРОТОНИНОВЫЙ ДЕФИЦИТ": (
        "Низкий серотонин при высоком кортизоле. "
        "Агент лишён эмоциональной стабилизации, что усиливает негативный аффект "
        "и делает поведение непредсказуемым."
    ),
    "ХОЛИНЕРГИЧЕСКАЯ АКТИВАЦИЯ": (
        "Высокий ацетилхолин при подавленном дофамине. "
        "Агент сфокусирован и внимателен, но без мотивационного компонента. "
        "Часто наблюдается во время исследования угрожающей среды."
    ),
    "КОРТИЗОЛЬНЫЙ ПИК": (
        "Экстремально высокий кортизол подавляет большинство функций. "
        "Хронический стресс в этом диапазоне приводит к ускоренной сенесценции "
        "и блокировке репродуктивной системы."
    ),
    "СБАЛАНСИРОВАННЫЙ ПРОФИЛЬ": (
        "Все нейромодуляторы в рабочем диапазоне без крайностей. "
        "Агент находится в состоянии нейрохимического равновесия — "
        "оптимально для обучения и социализации."
    ),
    "ОБЩАЯ ДЕПРЕССИЯ": (
        "Все стимулирующие нейромодуляторы на минимуме. "
        "Агент в состоянии глубокого торможения. "
        "Требует позитивных социальных событий или ресурсного насыщения для выхода."
    ),
    "ГИПЕРАКТИВАЦИЯ": (
        "Избыточная нейрохимическая активация через норадреналин и ацетилхолин. "
        "Агент истощает когнитивные ресурсы быстрее нормы."
    ),
    "СТАНДАРТНЫЙ": (
        "Нейромодуляторный профиль не выявил выраженного паттерна. "
        "Состояние умеренной активации."
    ),
}
```

---

### 3.4 Интерпретация Value Layers (T0, T1, T2...)

Value layers — иерархия принятия решений в NOWA. T0 — текущий выбор действия,
T1 — краткосрочная стратегия, T2 — долгосрочная.

```python
def extract_value_layers(agent: Any) -> list[ValueLayerSnapshot]:
    """
    Читает value layers из agent.value_layer или agent.thalamic_layer.
    
    Источники (пробовать по порядку):
    1. agent.value_layer.get_layer_snapshots() → list[dict]
    2. agent.value_layer.action_values → dict[str, list[float]] (T0, T1...)
    3. agent.thalamic_layer.levels → list[dict]
    4. agent._value_history → list[dict]
    
    Для каждого уровня:
    - Взять топ-3 action по значению
    - Нормировать в [0,1] если нужно
    
    Возвращает пустой список если данные недоступны.
    Весь код в try/except.
    """
```

#### Интерпретация доминирующего действия

```python
VALUE_ACTION_INTERPRETATIONS: dict[str, str] = {
    "eat":        "агент устойчиво ориентирован на питание",
    "drink":      "водный дефицит доминирует в решениях",
    "sleep":      "усталость определяет приоритеты",
    "explore":    "исследовательский мотив преобладает",
    "socialize":  "социальная потребность в центре",
    "groom_self": "самоуход — текущая стратегия комфорта",
    "run_wheel":  "физическая активность приоритетна",
    "hide":       "агент в защитной стратегии",
    "play":       "игровое поведение доминирует",
    "rest":       "восстановление — текущий приоритет",
}
```

---

### 3.5 Интерпретация привычек (кортекс)

Паттерны кортекса интерпретируются как устойчивые «привычки» агента.

```python
def extract_top_habits(cortex_patterns: list[dict]) -> list[HabitPattern]:
    """
    Из cortex_patterns_detail взять топ-5 по strength.
    
    Для каждого паттерна:
    - context_tokens → условия активации (humanized)
    - action → действие (humanized)
    - strength → сила привычки [0,1]
    - activation_count → сколько раз сработала
    - consequence → последствие
    
    Если паттернов нет → вернуть пустой список.
    """


HABIT_STRENGTH_LABELS: dict[str, str] = {
    # По strength
    "dominant":  "доминирующая",   # > 0.80
    "strong":    "сильная",         # > 0.60
    "moderate":  "умеренная",       # > 0.40
    "weak":      "слабая",          # > 0.20
    "nascent":   "зарождающаяся",   # <= 0.20
}


HABIT_PERSONALITY_MAP: list[tuple[list[str], str]] = [
    # (actions_that_dominate, personality_label)
    (["hide", "rest"],                    "ТРЕВОЖНЫЙ ОДИНОЧКА"),
    (["eat", "drink"],                    "РЕСУРСНЫЙ ПРАГМАТИК"),
    (["socialize", "play", "allogroom"],  "СОЦИАЛЬНЫЙ АГЕНТ"),
    (["explore", "run_wheel"],            "ИССЛЕДОВАТЕЛЬ"),
    (["sleep", "rest"],                   "ПАССИВНЫЙ"),
    (["groom_self", "rest", "hide"],      "ЗАМКНУТЫЙ"),
]
```

---

### 3.6 Интерпретация недавнего опыта (гиппокамп)

```python
def extract_significant_episodes(
    hippocampus_episodes: list[dict],
    n: int = 5,
) -> list[RecentEpisode]:
    """
    Из hippocampus_episodes взять N самых значимых.
    
    Критерий значимости: abs(reward) > 0.05 OR encoding_strength > 0.50
    Среди них — самые свежие по timestamp.
    
    Если нет значимых → взять просто последние N.
    """
```

---

### 3.7 Интерпретация характера

```python
def build_personality_readout(
    habits: list[HabitPattern],
    affect: AffectInterpretation,
    neuro: NeuroProfile,
) -> PersonalityReadout:
    """
    Определить характер агента по комбинации:
    - Доминирующие привычки из кортекса
    - Текущий аффективный тон
    - Нейропрофиль
    
    Алгоритм:
    1. Определить dominant_actions из топ-3 привычек
    2. Найти совпадение в HABIT_PERSONALITY_MAP
    3. Если нет совпадения — использовать affect.tone_label как подсказку
    4. Сформировать summary из шаблонов PERSONALITY_SUMMARIES
    """


PERSONALITY_SUMMARIES: dict[str, str] = {
    "ТРЕВОЖНЫЙ ОДИНОЧКА": (
        "Агент выработал стратегию выживания через избегание контактов и укрытие. "
        "Хронический стресс подавил любопытство и социальные мотивы. "
        "Паттерны питания и укрытия доминируют над всеми другими."
    ),
    "РЕСУРСНЫЙ ПРАГМАТИК": (
        "Поведение агента максимально ориентировано на ресурсы. "
        "Социальные взаимодействия происходят только когда не конкурируют с добычей еды. "
        "Стабильная но ограниченная стратегия."
    ),
    "СОЦИАЛЬНЫЙ АГЕНТ": (
        "Агент сформировал выраженные социальные паттерны. "
        "Взаимодействия с колонией — главный источник позитивного подкрепления. "
        "Высокий вклад в социальную сплочённость группы."
    ),
    "ИССЛЕДОВАТЕЛЬ": (
        "Паттерны исследования и физической активности доминируют. "
        "Агент активно картирует клетку и тестирует новые стратегии. "
        "Высокая когнитивная активность."
    ),
    "ПАССИВНЫЙ": (
        "Поведенческий репертуар агента сужен до минимума. "
        "Сон и отдых занимают большую часть активного времени. "
        "Может быть признаком хронического истощения."
    ),
    "ЗАМКНУТЫЙ": (
        "Агент избегает контактов через самоизоляцию и самоуход. "
        "Небольшой набор стабильных привычек без социальной компоненты."
    ),
    "НЕОПРЕДЕЛЁННЫЙ": (
        "Достаточно данных для определения устойчивого характера не обнаружено. "
        "Агент ещё формирует поведенческий репертуар."
    ),
}
```

---

### 3.8 Главная функция

```python
def build_nowa_interpretation(data: "InspectorData") -> NowaInterpretation:
    """
    Построить полную интерпретацию NOWA из данных инспектора.
    
    Аргументы:
        data: InspectorData — текущий снапшот агента
    
    Алгоритм:
        1. interpret_affect(data.affective_axes) → AffectInterpretation
        2. interpret_neuro(data.neuromodulators) → NeuroProfile
        3. extract_value_layers(data) → list[ValueLayerSnapshot]
        4. extract_top_habits(data.cortex_patterns_detail) → list[HabitPattern]
        5. extract_significant_episodes(data.hippocampus_episodes) → list[RecentEpisode]
        6. build_personality_readout(habits, affect, neuro) → PersonalityReadout
        7. Собрать NowaInterpretation и вернуть
    
    Никогда не вызывает исключений.
    При любой ошибке — fallback к нейтральным значениям.
    """
```

---

## 4. Изменения в agent_inspector.py

### 4.1 Изменения в InspectorData

```python
@dataclass
class InspectorData:
    ...
    nowa_interpretation: NowaInterpretation | None = None   # НОВОЕ
    ...
```

### 4.2 Изменения в build_inspector_data_from_agent()

```python
# В конце, перед return:
from .nowa_interpreter import build_nowa_interpretation

nowa_interp = None
try:
    nowa_interp = build_nowa_interpretation(inspector_data)
except Exception:
    pass

# Передать nowa_interpretation=nowa_interp в InspectorData(...)
```

### 4.3 Полная новая _draw_tab_nowa()

Метод разбивается на секции с заголовками-разделителями.

```python
def _draw_tab_nowa(self, surface, font, font_small) -> int:
    """
    Расширенная вкладка NOWA с интерпретациями.
    
    Секции (каждая отделена горизонтальной линией):
    1. АФФЕКТИВНОЕ СОСТОЯНИЕ — тон + summary + оси с ярлыками
    2. НЕЙРОХИМИЧЕСКИЙ ПРОФИЛЬ — профиль + summary + НМ + взаимодействия
    3. БОДРСТВОВАНИЕ И ЭНЕРГИЯ — 4 показателя
    4. VALUE LAYERS — T0/T1/T2 если доступны
    5. АКТИВНЫЕ ПРИВЫЧКИ — топ-5 из кортекса
    6. НЕДАВНИЙ ОПЫТ — топ-5 значимых эпизодов
    7. ИНТЕРПРЕТАЦИЯ ХАРАКТЕРА — итоговый вывод
    """
```

#### Вспомогательные методы отрисовки

```python
def _draw_nowa_section_header(self, surface, font_small, y: int, title: str) -> int:
    """
    Нарисовать заголовок секции: тонкая линия + ТЕКСТ ЗАГОЛОВКА.
    """

def _draw_affect_tone_badge(
    self,
    surface,
    font,
    font_small,
    y: int,
    interp: AffectInterpretation,
) -> int:
    """
    Нарисовать цветной бейдж с тоном состояния и summary.
    
    Бейдж: закруглённый прямоугольник с цветом фона interp.tone_color.
    Текст: interp.tone_label крупным шрифтом.
    Под бейджем: wrapped summary текст (2-3 строки).
    """

def _draw_neuro_profile_badge(
    self,
    surface,
    font,
    font_small,
    y: int,
    profile: NeuroProfile,
) -> int:
    """
    Нарисовать бейдж нейропрофиля и взаимодействия.
    """

def _draw_axis_row(
    self,
    surface,
    font_small,
    y: int,
    *,
    label: str,
    value: float,
    short_label: str,
    value_range: tuple[float, float] = (0.0, 1.0),
    bar_color: tuple[int, int, int] = (103, 148, 195),
) -> int:
    """
    Нарисовать одну строку с баром:
    [label]  [бар]  [value:.3f]  [short_label]
    """

def _draw_value_layers(
    self,
    surface,
    font_small,
    y: int,
    layers: list[ValueLayerSnapshot],
) -> int:
    """
    Нарисовать T0, T1... с топ-3 действиями каждого.
    """

def _draw_habit(
    self,
    surface,
    font_small,
    y: int,
    habit: HabitPattern,
) -> int:
    """
    Нарисовать одну привычку:
    ● [action]  ←  [context]     [сила XXXX  ×NNN]
    """

def _draw_episode(
    self,
    surface,
    font_small,
    y: int,
    episode: RecentEpisode,
) -> int:
    """
    Нарисовать один эпизод:
    [t=XXXXX]  [action]  ←  [context]  →  R=±X.XX
    """

def _draw_personality_readout(
    self,
    surface,
    font,
    font_small,
    y: int,
    personality: PersonalityReadout,
) -> int:
    """
    Нарисовать итоговую интерпретацию характера.
    Заголовок + wrapped summary.
    """
```

---

## 5. Цветовая схема секций

```python
# Цвета разделителей и заголовков секций
SECTION_LINE_COLOR  = (195, 182, 165)
SECTION_TITLE_COLOR = (110, 98, 82)

# Цвет баров по оси (разные от дефолтного синего)
AXIS_COLORS: dict[str, tuple[int, int, int]] = {
    "stress":       (210, 90,  70),   # красный
    "arousal":      (215, 150, 60),   # оранжевый
    "valence":      (90,  175, 115),  # зелёный
    "attachment":   (180, 120, 200),  # фиолетовый
    "curiosity":    (80,  170, 200),  # голубой
    "trust":        (110, 175, 140),  # бирюзовый
    "dominance":    (200, 130, 80),   # коричневый
    "energy":       (80,  155, 220),  # синий
    "social_drive": (155, 100, 190),  # лавандовый
    # нейромодуляторы
    "dopamine":      (100, 160, 220),
    "serotonin":     (90,  190, 130),
    "norepinephrine":(215, 140, 65),
    "cortisol":      (205, 80,  70),
    "acetylcholine": (140, 110, 200),
    # бодрствование
    "wakefulness":   (110, 155, 200),
    "sleep_pressure":(155, 125, 195),
    "circadian":     (185, 165, 90),
    "alertness":     (100, 180, 160),
}

# Цвета бейджей тональных состояний
TONE_BADGE_COLORS: dict[str, tuple[int, int, int]] = {
    "ПАНИКА":               (200, 55,  45),
    "ОСТРЫЙ СТРЕСС":        (210, 95,  55),
    "ХРОНИЧЕСКАЯ ТРЕВОГА":  (195, 135, 65),
    "АГРЕССИЯ":             (195, 65,  65),
    "ВОЗБУЖДЕНИЕ":          (215, 178, 60),
    "СКУКА":                (148, 138, 125),
    "ОДИНОЧЕСТВО":          (105, 133, 178),
    "ЛЮБОПЫТСТВО":          (85,  163, 143),
    "ПРИВЯЗАННОСТЬ":        (183, 123, 193),
    "СПОКОЙСТВИЕ":          (95,  168, 105),
    "УСТАЛОСТЬ":            (135, 148, 168),
    "РАВНОВЕСИЕ":           (143, 158, 133),
}

# Ярлыки reward в эпизодах
def reward_label(reward: float) -> tuple[str, tuple[int, int, int]]:
    if reward > 0.30:  return (f"R=+{reward:.2f} ✓", (70, 150, 75))
    if reward > 0.05:  return (f"R=+{reward:.2f}",   (100, 170, 110))
    if reward < -0.20: return (f"R={reward:.2f} ✗",  (180, 75, 60))
    if reward < -0.05: return (f"R={reward:.2f}",    (200, 110, 90))
    return             (f"R={reward:.2f}",            (130, 120, 110))
```

---

## 6. Ограничения реализации

1. `nowa_interpreter.py` — независимый модуль без pygame.
2. `build_nowa_interpretation()` никогда не падает — все блоки в try/except.
3. Value layers показываются **только если доступны** — секция скрыта если `layers == []`.
4. Привычки показываются только если `cortex_patterns_detail` не пуст.
5. Эпизоды показываются только если `hippocampus_episodes` не пуст.
6. Для умершего агента (`is_deceased=True`): все секции с пометкой "(при смерти)",
   value layers и живые ссылки не показываются.
7. Максимум строк для wrapped text: 4 строки для summary, 2 строки для взаимодействий.
8. Бары аффекта теперь цветные (из `AXIS_COLORS`), не единый синий.
9. Существующие кликабельные ссылки на гиппокамп и кортекс сохраняются.
10. `_draw_axis_row()` обрабатывает valence в диапазоне [-1, 1]: бар нормирует до [0, 1].
11. Python 3.10+.

---

## 7. Тест-кейсы

### TC-01: Определение тонального состояния ПАНИКА

```python
from colony_gui.nowa_interpreter import interpret_affect

axes = {
    "stress": 0.92, "arousal": 0.88, "valence": -0.55,
    "attachment": -0.07, "curiosity": 0.04,
    "trust": -0.29, "dominance": -0.25,
    "energy": 0.96, "social_drive": 0.00,
}
result = interpret_affect(axes)

assert result.tone_label == "ПАНИКА"
assert result.tone_color[0] > 170          # красноватый
assert "стресс" in result.summary.lower()
assert result.axis_labels["stress"] == "критический"
assert result.axis_labels["curiosity"] in ("подавлено", "отсутствует")
```

### TC-02: Нейропрофиль СТРЕССОВАЯ АКТИВАЦИЯ

```python
from colony_gui.nowa_interpreter import interpret_neuro

nm = {
    "dopamine": 0.00, "serotonin": 0.00,
    "norepinephrine": 0.87, "cortisol": 0.78,
    "acetylcholine": 0.91,
}
result = interpret_neuro(nm)

assert result.profile_label == "СТРЕССОВАЯ АКТИВАЦИЯ"
assert "норадреналин" in result.summary.lower()
assert len(result.interactions) >= 1
assert any("кортизол" in i.lower() for i in result.interactions)
```

### TC-03: Нейропрофиль ДОФАМИНОВЫЙ ПИК

```python
nm = {
    "dopamine": 0.72, "serotonin": 0.48,
    "norepinephrine": 0.35, "cortisol": 0.18,
    "acetylcholine": 0.42,
}
result = interpret_neuro(nm)

assert result.profile_label == "ДОФАМИНОВЫЙ ПИК"
assert result.modulator_labels["dopamine"] == "активная мотивация"
assert result.modulator_labels["cortisol"] in ("минимальный", "лёгкий тонус")
```

### TC-04: Ярлыки осей для экстремального стресса

```python
from colony_gui.nowa_interpreter import get_axis_label

assert get_axis_label("stress", 0.95)  == "критический"
assert get_axis_label("stress", 0.72)  == "высокий"
assert get_axis_label("stress", 0.45)  == "умеренный"
assert get_axis_label("stress", 0.20)  == "низкий"
assert get_axis_label("stress", 0.05)  == "минимальный"
```

### TC-05: Ярлыки для valence ([-1, 1])

```python
assert get_axis_label("valence", -0.75)  == "тяжёлый"
assert get_axis_label("valence", -0.40)  == "негативный"
assert get_axis_label("valence",  0.10)  == "нейтральный"
assert get_axis_label("valence",  0.40)  == "позитивный"
assert get_axis_label("valence",  0.75)  == "радостный"
```

### TC-06: Извлечение привычек

```python
from colony_gui.nowa_interpreter import extract_top_habits

patterns = [
    {"context_tokens": ["food_low"], "action": "eat", "consequence": "success",
     "strength": 0.89, "activation_count": 47},
    {"context_tokens": ["wakefulness_high"], "action": "sleep", "consequence": "success",
     "strength": 0.71, "activation_count": 31},
    {"context_tokens": ["stress"], "action": "hide", "consequence": "success",
     "strength": 0.64, "activation_count": 28},
]
habits = extract_top_habits(patterns)

assert len(habits) == 3
assert habits[0].action == "eat"
assert habits[0].strength == 0.89
assert habits[0].activation_count == 47
assert habits[1].action == "sleep"
```

### TC-07: Определение характера ТРЕВОЖНЫЙ ОДИНОЧКА

```python
from colony_gui.nowa_interpreter import build_personality_readout

habits = [
    HabitPattern(["стресс"], "hide", 0.85, 47, "success"),
    HabitPattern(["усталость"], "rest", 0.71, 31, "success"),
    HabitPattern(["скука"], "groom_self", 0.58, 22, "success"),
]
affect = AffectInterpretation("ПАНИКА", (210,60,50), "...", {})
neuro  = NeuroProfile("СТРЕССОВАЯ АКТИВАЦИЯ", "...", {}, [])

result = build_personality_readout(habits, affect, neuro)

assert result.character_label == "ТРЕВОЖНЫЙ ОДИНОЧКА"
assert "избегани" in result.summary.lower() or "стресс" in result.summary.lower()
```

### TC-08: Значимые эпизоды — отбор по reward

```python
from colony_gui.nowa_interpreter import extract_significant_episodes

episodes = [
    {"timestamp": 100.0, "action": "eat",    "reward": 0.41, "encoding_strength": 0.8,
     "context_tokens": ["food_low"], "consequence": "success"},
    {"timestamp": 90.0,  "action": "explore","reward": 0.01, "encoding_strength": 0.2,
     "context_tokens": ["bored"], "consequence": "neutral"},
    {"timestamp": 80.0,  "action": "socialize","reward": -0.23,"encoding_strength": 0.6,
     "context_tokens": ["stranger_nearby"], "consequence": "rejected"},
    {"timestamp": 70.0,  "action": "drink",  "reward": 0.19, "encoding_strength": 0.5,
     "context_tokens": ["water_critical"], "consequence": "success"},
    {"timestamp": 60.0,  "action": "hide",   "reward": 0.12, "encoding_strength": 0.4,
     "context_tokens": ["stress"], "consequence": "success"},
    {"timestamp": 50.0,  "action": "rest",   "reward": 0.00, "encoding_strength": 0.1,
     "context_tokens": [], "consequence": "neutral"},
]
result = extract_significant_episodes(episodes, n=5)

# Незначимый эпизод (reward=0.01, encoding=0.2) должен быть последним или отсутствовать
assert result[0].action == "eat"    # самый значимый и свежий
assert len(result) == 5
significant_actions = [e.action for e in result]
# Нейтральный незначимый explore — в конце если вообще есть
if "explore" in significant_actions:
    assert significant_actions.index("explore") > 2
```

### TC-09: build_nowa_interpretation не падает на пустых данных

```python
from colony_gui.nowa_interpreter import build_nowa_interpretation

empty_data = InspectorData(
    agent_id="test", display_name="G0A1", is_deceased=False,
    sex="F", generation=0, parents=(None,None), age=100.0,
    lived_steps=100, cause_of_death="",
    # все остальные поля — дефолтные пустые
)

result = build_nowa_interpretation(empty_data)

assert result is not None
assert result.affect is not None
assert result.neuro is not None
assert isinstance(result.habits, list)
assert isinstance(result.recent_episodes, list)
assert result.personality is not None
```

### TC-10: Цвета баров — каждая ось получает свой цвет

```python
from colony_gui.nowa_interpreter import AXIS_COLORS

required_axes = [
    "stress", "arousal", "valence", "attachment", "curiosity",
    "trust", "dominance", "energy", "social_drive",
    "dopamine", "serotonin", "norepinephrine", "cortisol", "acetylcholine",
    "wakefulness", "sleep_pressure", "circadian", "alertness",
]
for axis in required_axes:
    assert axis in AXIS_COLORS, f"Missing color for {axis}"
    color = AXIS_COLORS[axis]
    assert len(color) == 3
    assert all(0 <= c <= 255 for c in color)
```

### TC-11: Взаимодействия НМ для состояния G0A1SF

```python
nm_g0a1sf = {
    "dopamine": 0.00, "serotonin": 0.00,
    "norepinephrine": 0.87, "cortisol": 0.78,
    "acetylcholine": 0.91,
}
result = interpret_neuro(nm_g0a1sf)

# Ожидаем как минимум 2 выявленных взаимодействия
assert len(result.interactions) >= 2
interaction_text = " ".join(result.interactions).lower()
assert "кортизол" in interaction_text
assert "дофамин" in interaction_text
```

### TC-12: Value layer snapshot — топ-3 действия

```python
from colony_gui.nowa_interpreter import ValueLayerSnapshot

snap = ValueLayerSnapshot(
    level=0,
    top_actions=[("eat", 0.72), ("drink", 0.43), ("sleep", 0.28)],
    raw_values={"eat": 0.72, "drink": 0.43, "sleep": 0.28, "explore": 0.15},
)

assert snap.top_actions[0] == ("eat", 0.72)
assert len(snap.top_actions) <= 3
```

### TC-13: Умерший агент — value layers не отображаются

```python
data = build_inspector_data_from_memorial(memorial, "G0A1SF")
interp = build_nowa_interpretation(data)

# Для умершего value layers должны быть пустыми
assert interp.value_layers == []
```

### TC-14: Характер ИССЛЕДОВАТЕЛЬ по паттернам

```python
habits = [
    HabitPattern(["bored"], "explore", 0.82, 55, "neutral"),
    HabitPattern(["energy_high"], "run_wheel", 0.74, 42, "success"),
    HabitPattern(["food_ok"], "explore", 0.61, 38, "neutral"),
]
affect = AffectInterpretation("ЛЮБОПЫТСТВО", (85,163,143), "...", {})
neuro  = NeuroProfile("ДОФАМИНОВЫЙ ПИК", "...", {}, [])

result = build_personality_readout(habits, affect, neuro)

assert result.character_label == "ИССЛЕДОВАТЕЛЬ"
```

### TC-15: Reward-ярлыки корректны

```python
from colony_gui.nowa_interpreter import reward_label

text, color = reward_label(0.45)
assert "+" in text
assert color[1] > color[0]  # зелёный доминирует

text2, color2 = reward_label(-0.30)
assert "✗" in text2 or "-" in text2
assert color2[0] > color2[1]  # красный доминирует

text3, color3 = reward_label(0.02)
# нейтральный — серый
assert color3[0] > 100 and abs(color3[0] - color3[1]) < 40
```

---

## 8. Примечания для реализующего агента

- `nowa_interpreter.py` — без pygame, без colony-специфичных импортов. Только стандартная библиотека + `InspectorData`.
- `AFFECT_TONES` проверять в порядке списка, брать первое совпадение — порядок важен.
- `NM_INTERACTIONS` — проверять все, добавлять все совпадения (не только первое).
- Ярлык оси `get_axis_label(axis, value)` — простая switch-функция по thresholds, не словарь.
- Для valence: нормировать в [0,1] только для бара: `bar_value = (valence + 1.0) / 2.0`.
- `extract_value_layers()` — если ни один источник не дал данных, вернуть `[]` без ошибок.
- `extract_top_habits()` — сортировать по `strength` DESC, брать топ-5, если меньше — брать все.
- `extract_significant_episodes()` — сортировать кандидатов по `timestamp` DESC перед обрезкой до N.
- `_draw_axis_row()` — ширина бара 120px, ярлык после числа, всё на одной строке.
- `_draw_habit()` — строка-пуля, не блок. Максимум 2 строки на привычку.
- `_draw_episode()` — строка-пуля. Максимум 1 строка на эпизод.
- Бейдж тонального состояния: закруглённый прямоугольник с полупрозрачным фоном, текст метки поверх. Высота бейджа ~24px.
- При `is_deceased=True` в заголовке каждой секции добавить суффикс "(при смерти)".
- `_genome_table_expanded` сбрасывается при смене вкладки — аналогично сделать если понадобится toggle в NOWA.
