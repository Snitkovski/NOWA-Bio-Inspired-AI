## Аннотация

English version: [SPEC_GenomePortrait_InspectorTab.en.md](SPEC_GenomePortrait_InspectorTab.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Спецификация описывает преобразование вкладки «Геном» в `AgentInspectorOverlay` в аналитический портрет особи, реализуемый модулем `genome_portrait`. Предмет документа — семантическая интерпретация генома: кем является данный агент по категориям темперамента, социальности, выносливости, когниции и продолжительности жизни, чем его значения отличаются от родительской середины и в какую сторону смещается линия предков.

Модуль вводит реестр генов с диапазонами, полярностью и весами признаков, функцию построения портрета и расчёт тренда по цепочке предков, извлекаемой из реестра смертей. Вкладка разделяет характеристику личности, перечень значимых сдвигов, линейные тренды отдельных генов и свёрнутую полную таблицу. Сырые значения сохраняются, но перестают быть единственной формой представления.

Научная функция спецификации в многоагентной установке NOWA состоит в том, чтобы сделать наследственную изменчивость наблюдаемой на уровне индивида и линии. Документ не заменяет генетический механизм симуляции. Он задаёт словарь признаков, по которому межпоколенческие сдвиги могут быть соотнесены с физиологическим и поведенческим состоянием агента колонии.

# Спецификация: Расширенная вкладка «Геном» в AgentInspectorOverlay

**Файл:** `colony_gui/agent_inspector.py` — изменения в существующем файле  
**Новый модуль:** `colony_gui/genome_portrait.py`  
**Версия:** 1.0

---

## 1. Концепция

Вкладка «Геном» перестаёт быть сырой таблицей значений.  
Она становится **аналитическим портретом агента** — документом который объясняет
*кто этот агент*, *чем он отличается от предков* и *куда движется его линия*.

Структура вкладки после изменений:

```
┌─────────────────────────────────────────────────────────┐
│  Геном G4 | линия G3A3SF × G3A9SM                       │
├─────────────────────────────────────────────────────────┤
│  ПОРТРЕТ ЛИЧНОСТИ                                        │
│  [категория: темперамент]  ███░ чувствительный           │
│  [категория: социальность] ██░░ замкнутый                │
│  [категория: выносливость] ████ долгожитель              │
│  [категория: когниция]     ███░ аналитик                 │
│                                                          │
│  Краткая характеристика (3-4 предложения)                │
│                                                          │
│  Сильные стороны:  [+] [+] [+]                          │
│  Слабые стороны:   [-] [-]                               │
│  Нейтральные:      [~] [~]                               │
├─────────────────────────────────────────────────────────┤
│  ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО РОДИТЕЛЕЙ                        │
│  Ген                 родит. midpoint  текущий   оценка   │
│  wk_recovery_factor     0.82        0.59    ↓ −0.23  ⚠  │
│  lt_max_lifespan        1.05        1.25    ↑ +0.20  ✓  │
│  af_decay_stress        0.75        0.68    ↓ −0.07  ✓  │
├─────────────────────────────────────────────────────────┤
│  ТРЕНД ЛИНИИ (цепочка из DeathRegistry)                  │
│  cortisol:  1.00 → 1.00 → 0.98 → 0.85 ↘ снижение       │
│  stress:    0.94 → 0.90 → 0.87 → 0.81 ↘ адаптация       │
│  lifespan:  1.00 → 1.05 → 1.18 → 1.25 ↗ долголетие      │
│  [мини-графики ASCII или bar-сегменты]                   │
├─────────────────────────────────────────────────────────┤
│  ПОЛНАЯ ТАБЛИЦА ГЕНОВ (свёрнута по умолчанию)            │
│  [▶ показать все 39 генов]                               │
└─────────────────────────────────────────────────────────┘
```

---

## 2. genome_portrait.py — новый модуль

### 2.1 Архитектура

```
genome_portrait.py
├── GeneRange          — диапазон и семантика одного гена
├── GENE_REGISTRY      — словарь всех генов с семантикой
├── TraitScore         — оценка одной черты характера [0..1]
├── GenomePortrait     — полный портрет агента
├── build_portrait()   — главная функция: гены → портрет
├── build_lineage_trend() — тренд по цепочке предков
└── render_portrait_*()   — функции отрисовки в pygame
```

### 2.2 GeneRange

```python
@dataclass(frozen=True)
class GeneRange:
    """Семантика одного гена для портрета."""
    key: str
    group: str           # "af", "nm", "wk", "dr", "lr", "lt", "im"
    default: float       # дефолтное значение
    low: float           # минимум диапазона
    high: float          # максимум диапазона
    low_label: str       # что значит низкое значение (для агента)
    high_label: str      # что значит высокое значение
    trait_category: str  # "temperament"|"social"|"endurance"|"cognition"|"lifespan"
    weight: float        # важность для портрета [0..1]
    polarity: str        # "high_good"|"low_good"|"neutral"|"both_extreme_bad"
```

### 2.3 GENE_REGISTRY

Полный реестр генов с семантикой. Ключевые записи:

```python
GENE_REGISTRY: dict[str, GeneRange] = {

    # ── АФФЕКТ ────────────────────────────────────────────────────────
    "af_decay_stress": GeneRange(
        key="af_decay_stress", group="af", default=0.70, low=0.55, high=0.88,
        low_label="быстро успокаивается",
        high_label="долго носит стресс",
        trait_category="temperament", weight=0.9,
        polarity="low_good",
    ),
    "af_decay_valence": GeneRange(
        key="af_decay_valence", group="af", default=0.92, low=0.80, high=0.98,
        low_label="настроение меняется быстро",
        high_label="стабильное настроение",
        trait_category="temperament", weight=0.6,
        polarity="neutral",
    ),
    "af_decay_curiosity": GeneRange(
        key="af_decay_curiosity", group="af", default=0.78, low=0.60, high=0.90,
        low_label="любопытство быстро угасает",
        high_label="устойчивый интерес к окружению",
        trait_category="cognition", weight=0.7,
        polarity="high_good",
    ),
    "af_decay_attachment": GeneRange(
        key="af_decay_attachment", group="af", default=0.93, low=0.85, high=0.99,
        low_label="привязанности непостоянны",
        high_label="крепко держится за близких",
        trait_category="social", weight=0.8,
        polarity="high_good",
    ),
    "af_decay_trust": GeneRange(
        key="af_decay_trust", group="af", default=0.95, low=0.85, high=0.99,
        low_label="доверие быстро теряется",
        high_label="доверяет надолго",
        trait_category="social", weight=0.7,
        polarity="high_good",
    ),
    "af_lambda_reg": GeneRange(
        key="af_lambda_reg", group="af", default=0.05, low=0.01, high=0.15,
        low_label="слабая аффективная регуляция",
        high_label="сильная эмоциональная саморегуляция",
        trait_category="temperament", weight=0.8,
        polarity="high_good",
    ),

    # ── НЕЙРОМОДУЛЯТОРЫ ───────────────────────────────────────────────
    "nm_decay_half_life": GeneRange(
        key="nm_decay_half_life", group="nm", default=60.0, low=20.0, high=200.0,
        low_label="нейромодуляторы быстро рассеиваются",
        high_label="долгоживущие нейрохимические состояния",
        trait_category="temperament", weight=0.5,
        polarity="neutral",
    ),
    "nm_da_ne_weight": GeneRange(
        key="nm_da_ne_weight", group="nm", default=0.0, low=-0.5, high=0.5,
        low_label="дофамин тормозит норадреналин",
        high_label="дофамин усиливает норадреналин",
        trait_category="temperament", weight=0.4,
        polarity="neutral",
    ),
    "nm_acc_k_cort": GeneRange(
        key="nm_acc_k_cort", group="nm", default=0.7, low=0.3, high=1.0,
        low_label="слабая реакция на кортизол",
        high_label="высокая кортизол-чувствительность",
        trait_category="temperament", weight=0.8,
        polarity="low_good",
    ),

    # ── БОДРСТВОВАНИЕ ─────────────────────────────────────────────────
    "wk_accumulation_factor": GeneRange(
        key="wk_accumulation_factor", group="wk", default=1.0, low=0.5, high=2.0,
        low_label="медленно устаёт",
        high_label="быстро накапливает усталость",
        trait_category="endurance", weight=0.7,
        polarity="low_good",
    ),
    "wk_recovery_factor": GeneRange(
        key="wk_recovery_factor", group="wk", default=0.85, low=0.4, high=1.0,
        low_label="долго восстанавливается после сна",
        high_label="быстро приходит в норму",
        trait_category="endurance", weight=0.8,
        polarity="high_good",
    ),
    "wk_circadian_amplitude": GeneRange(
        key="wk_circadian_amplitude", group="wk", default=0.3, low=0.05, high=0.6,
        low_label="слабый суточный ритм",
        high_label="выраженный суточный цикл",
        trait_category="endurance", weight=0.4,
        polarity="neutral",
    ),
    "wk_circadian_phase": GeneRange(
        key="wk_circadian_phase", group="wk", default=0.0, low=-1.0, high=1.0,
        low_label="ночной тип активности",
        high_label="дневной тип активности",
        trait_category="social", weight=0.3,
        polarity="neutral",
    ),

    # ── ДРАЙВЫ ────────────────────────────────────────────────────────
    "dr_curiosity_baseline": GeneRange(
        key="dr_curiosity_baseline", group="dr", default=0.4, low=0.1, high=0.8,
        low_label="апатичный исследователь",
        high_label="ненасытно любопытный",
        trait_category="cognition", weight=0.7,
        polarity="high_good",
    ),
    "dr_social_drive_baseline": GeneRange(
        key="dr_social_drive_baseline", group="dr", default=0.45, low=0.1, high=0.8,
        low_label="одиночка",
        high_label="выраженный социальный инстинкт",
        trait_category="social", weight=0.9,
        polarity="high_good",
    ),
    "dr_perception_radius_factor": GeneRange(
        key="dr_perception_radius_factor", group="dr", default=1.0, low=0.5, high=2.0,
        low_label="узкое восприятие окружения",
        high_label="широкое поле восприятия",
        trait_category="cognition", weight=0.5,
        polarity="high_good",
    ),

    # ── ОБУЧЕНИЕ ──────────────────────────────────────────────────────
    "lr_gamma": GeneRange(
        key="lr_gamma", group="lr", default=0.85, low=0.5, high=0.99,
        low_label="живёт сегодняшним днём",
        high_label="думает о долгосрочных последствиях",
        trait_category="cognition", weight=0.7,
        polarity="high_good",
    ),
    "lr_alpha": GeneRange(
        key="lr_alpha", group="lr", default=0.05, low=0.005, high=0.2,
        low_label="медленно обучается",
        high_label="быстро адаптируется",
        trait_category="cognition", weight=0.8,
        polarity="both_extreme_bad",
    ),
    "lr_tonic_slow_rate": GeneRange(
        key="lr_tonic_slow_rate", group="lr", default=0.02, low=0.001, high=0.1,
        low_label="стабильные базовые убеждения",
        high_label="быстро пересматривает опыт",
        trait_category="cognition", weight=0.4,
        polarity="neutral",
    ),

    # ── ДОЛГОЛЕТИЕ ────────────────────────────────────────────────────
    "lt_max_lifespan_factor": GeneRange(
        key="lt_max_lifespan_factor", group="lt", default=1.0, low=0.7, high=1.5,
        low_label="короткоживущий",
        high_label="потенциальный долгожитель",
        trait_category="lifespan", weight=1.0,
        polarity="high_good",
    ),
}
```

---

### 2.4 TraitScore и категории

```python
TRAIT_CATEGORIES = [
    "temperament",   # эмоциональный профиль, стресс, регуляция
    "social",        # социальность, привязанность, тип активности
    "endurance",     # выносливость, усталость, сон
    "cognition",     # обучение, любопытство, восприятие
    "lifespan",      # потенциальная продолжительность жизни
]

TRAIT_LABELS_RU = {
    "temperament": "Темперамент",
    "social":      "Социальность",
    "endurance":   "Выносливость",
    "cognition":   "Когниция",
    "lifespan":    "Долгожитие",
}

@dataclass
class TraitScore:
    category: str
    score: float          # [0..1], 1.0 = максимально выражен
    label: str            # текстовый ярлык
    contributing_genes: list[str]   # гены которые сформировали оценку
```

### 2.5 GenomePortrait

```python
@dataclass
class GenomePortrait:
    # Черты характера
    trait_scores: dict[str, TraitScore]   # category → TraitScore

    # Текстовое описание
    summary: str                 # 2-3 предложения, общая характеристика

    # Сильные/слабые/нейтральные стороны
    strengths: list[str]         # максимум 4
    weaknesses: list[str]        # максимум 4
    neutral_traits: list[str]    # максимум 3

    # Мутационный анализ
    mutations: list[MutationEffect]

    # Тренды линии (если доступно)
    lineage_trend: list[LineageTrendPoint] | None
```

### 2.6 MutationEffect

```python
@dataclass
class MutationEffect:
    gene_key: str
    parent_midpoint: float    # среднее значение родителей
    current_value: float      # текущее значение у агента
    delta: float              # current - parent_midpoint
    direction: str            # "up" | "down" | "neutral"
    valence: str              # "positive" | "negative" | "neutral"
    consequence_short: str    # краткое последствие (1 строка)
    consequence_detail: str   # детальное объяснение (1-2 предложения)
    magnitude: str            # "major" | "moderate" | "minor"
```

Пример заполнения:
```python
# wk_recovery_factor: 0.82 → 0.59, Δ−0.23
MutationEffect(
    gene_key="wk_recovery_factor",
    parent_midpoint=0.82,
    current_value=0.59,
    delta=-0.23,
    direction="down",
    valence="negative",
    consequence_short="медленнее восстанавливается после сна",
    consequence_detail=(
        "Агент нуждается в более длительном отдыхе чтобы "
        "достичь полного бодрствования. Риск хронической "
        "усталости при высокой социальной активности."
    ),
    magnitude="major",  # |delta| > 0.15
)

# lt_max_lifespan_factor: 1.05 → 1.25, Δ+0.20
MutationEffect(
    gene_key="lt_max_lifespan_factor",
    parent_midpoint=1.05,
    current_value=1.25,
    delta=+0.20,
    direction="up",
    valence="positive",
    consequence_short="потенциально живёт на 19% дольше родителей",
    consequence_detail=(
        "Увеличенный фактор максимальной продолжительности жизни "
        "означает что сенесценция начнётся позже и будет менее "
        "стремительной. При низком кортизоле этот ген "
        "реализуется в полной мере."
    ),
    magnitude="major",
)
```

### 2.7 LineageTrendPoint

```python
@dataclass
class LineageTrendPoint:
    agent_id: str
    display_name: str     # G0A1SF, G1A3SM и т.д.
    generation: int
    gene_values: dict[str, float]   # только отслеживаемые гены
    stress_at_death: float
    cortisol_at_death: float
    lived_steps: int
```

**Отслеживаемые гены для трендов:**
```python
LINEAGE_TRACKED_GENES = [
    "lt_max_lifespan_factor",
    "af_decay_stress",
    "nm_acc_k_cort",
    "dr_social_drive_baseline",
    "wk_recovery_factor",
    "lr_alpha",
]
```

---

### 2.8 Функция build_portrait()

```python
def build_portrait(
    genes: dict[str, float],
    genome_inheritance_meta: dict[str, Any],
) -> GenomePortrait:
    """
    Построить полный портрет из генома агента.

    Алгоритм:
    1. Для каждого гена в GENE_REGISTRY:
       a. Нормировать значение в [0..1] по диапазону [low..high]
       b. Перевести в "trait score" с учётом polarity
    2. Агрегировать по категориям (weighted average)
    3. Сгенерировать summary через _generate_summary()
    4. Определить strengths/weaknesses через _classify_traits()
    5. Проанализировать мутации через _analyze_mutations()
    """
```

**Нормировка гена:**
```python
def _normalize_gene(value: float, gene: GeneRange) -> float:
    """Нормировать значение в [0..1] в пределах диапазона гена."""
    span = gene.high - gene.low
    if span <= 0:
        return 0.5
    return max(0.0, min(1.0, (value - gene.low) / span))

def _gene_to_trait_score(normalized: float, polarity: str) -> float:
    """
    Перевести нормированное значение в trait score [0..1].
    polarity="high_good"       → score = normalized
    polarity="low_good"        → score = 1 - normalized
    polarity="neutral"         → score = 0.5 (не влияет на силу)
    polarity="both_extreme_bad"→ score = 1 - abs(normalized - 0.5) * 2
    """
```

**Агрегация по категориям:**
```python
def _compute_trait_scores(genes: dict[str, float]) -> dict[str, TraitScore]:
    """
    Для каждой категории: взвешенное среднее trait scores всех генов категории.
    Вес каждого гена = GeneRange.weight.
    """
```

**Генерация summary:**

Summary строится по шаблонной логике на основе доминирующих trait scores:

```python
SUMMARY_TEMPLATES = {
    # (dominant_trait, secondary_trait) → шаблон
    ("temperament_high", "social_high"): (
        "{name} — чувствительная и общительная особь с острой реакцией "
        "на социальные сигналы. Хорошо интегрируется в колонию, "
        "но уязвима к чужому стрессу."
    ),
    ("temperament_low", "endurance_high"): (
        "{name} — хладнокровная и выносливая особь. "
        "Стресс рассеивается быстро, усталость накапливается медленно. "
        "Надёжный член колонии в кризисных ситуациях."
    ),
    ("lifespan_high", "cognition_high"): (
        "{name} несёт гены долгожителя с высоким когнитивным потенциалом. "
        "Если переживёт ранний период высокого кортизола — "
        "станет ценным хранителем опыта для колонии."
    ),
    # ... 12-15 шаблонов для основных комбинаций
    ("default",): (
        "{name} — особь со сбалансированным генетическим профилем "
        "без выраженных крайностей. Хорошо адаптируется "
        "к изменяющимся условиям."
    ),
}
```

**Классификация strengths/weaknesses:**
```python
STRENGTH_THRESHOLD = 0.70   # trait score выше → сильная сторона
WEAKNESS_THRESHOLD = 0.35   # trait score ниже → слабая сторона

STRENGTH_LABELS: dict[str, list[str]] = {
    "temperament": [
        "быстро успокаивается",
        "эмоционально устойчив",
        "низкая кортизол-чувствительность",
    ],
    "social": [
        "сильный социальный инстинкт",
        "крепкие привязанности",
        "хорошо читает колонию",
    ],
    "endurance": [
        "высокая выносливость",
        "эффективный сон",
        "медленно устаёт",
    ],
    "cognition": [
        "любопытный исследователь",
        "быстро адаптируется",
        "широкое восприятие",
    ],
    "lifespan": [
        "потенциальный долгожитель",
        "медленное старение",
    ],
}
```

**Анализ мутаций:**
```python
def _analyze_mutations(
    genes: dict[str, float],
    inheritance_meta: dict[str, Any],
) -> list[MutationEffect]:
    """
    Из genome_inheritance_meta читать:
      - "top_shifted_genes": list[{key, delta}]
      - "parent_midpoint_genes": dict[str, float]

    Для каждого значимого гена (|delta| >= 0.01):
      1. Определить direction ("up"/"down"/"neutral")
      2. Определить valence по GeneRange.polarity
      3. Подобрать consequence_short и consequence_detail из
         MUTATION_CONSEQUENCES[gene_key][direction]
      4. Определить magnitude: |delta| >= 0.15 → "major",
         >= 0.05 → "moderate", иначе "minor"

    Вернуть отсортированные по magnitude DESC.
    Максимум 8 мутаций в списке.
    """
```

**Словарь последствий мутаций:**
```python
MUTATION_CONSEQUENCES: dict[str, dict[str, tuple[str, str]]] = {
    # gene_key → {direction → (short, detail)}
    "af_decay_stress": {
        "down": (
            "стресс рассеивается быстрее",
            "Агент легче восстанавливается после конфликтов и испугов. "
            "Позитивно влияет на репродуктивный потенциал и социальность.",
        ),
        "up": (
            "стресс держится дольше",
            "Однажды испуганный агент долго остаётся в режиме тревоги. "
            "Риск хронического кортизола при частых социальных конфликтах.",
        ),
    },
    "lt_max_lifespan_factor": {
        "up": (
            "потенциально дольше живёт",
            "Сенесценция начнётся позже и будет менее интенсивной. "
            "Ген реализуется в полной мере только при низком кортизоле.",
        ),
        "down": (
            "укороченная жизнь",
            "Агент достигнет сенесценции раньше. "
            "Ускоренное старение может частично компенсироваться "
            "активным размножением в молодом возрасте.",
        ),
    },
    "wk_recovery_factor": {
        "down": (
            "медленнее восстанавливается после сна",
            "Требует более длительного отдыха для полного восстановления. "
            "Уязвим к хронической усталости при высокой активности.",
        ),
        "up": (
            "быстро приходит в форму после сна",
            "Короткий сон даёт полное восстановление. "
            "Больше активного времени для исследования и социализации.",
        ),
    },
    "dr_social_drive_baseline": {
        "up": (
            "высокая потребность в общении",
            "Активно ищет контакты, быстро строит социальные связи. "
            "Риск стресса при вынужденной изоляции.",
        ),
        "down": (
            "низкая социальная потребность",
            "Комфортно в одиночестве, меньше зависит от других агентов. "
            "Может иметь сложности с привлечением партнёра.",
        ),
    },
    "nm_acc_k_cort": {
        "up": (
            "высокая чувствительность к кортизолу",
            "Стресс сильнее влияет на физиологию. "
            "При хроническом стрессе быстрее истощается репродуктивный драйв.",
        ),
        "down": (
            "сниженная чувствительность к кортизолу",
            "Стресс меньше влияет на тело. "
            "Более устойчив к длительному стрессу популяции.",
        ),
    },
    "lr_alpha": {
        "up": (
            "очень быстрое обучение",
            "Быстро адаптируется к новому, но может быть нестабилен — "
            "легко переобучается на случайные события.",
        ),
        "down": (
            "медленное но стабильное обучение",
            "Медленнее адаптируется к изменениям среды, "
            "зато поведение предсказуемо и консервативно.",
        ),
    },
    "wk_accumulation_factor": {
        "up": (
            "быстро устаёт",
            "Требует частого сна. "
            "При высокой активности колонии рискует не успевать восстанавливаться.",
        ),
        "down": (
            "медленно накапливает усталость",
            "Дольше остаётся активным без сна. "
            "Преимущество при напряжённых периодах жизни колонии.",
        ),
    },
    "af_decay_attachment": {
        "up": (
            "крепкие долгосрочные привязанности",
            "Связи с другими агентами устойчивы и долговечны. "
            "Важный вклад в социальную сплочённость колонии.",
        ),
        "down": (
            "привязанности непостоянны",
            "Быстро теряет эмоциональную связь без подкрепления. "
            "Социальные связи требуют частого поддержания.",
        ),
    },
    "lr_gamma": {
        "up": (
            "ориентирован на долгосрочные последствия",
            "При принятии решений учитывает будущее. "
            "Лучше справляется с отложенным вознаграждением.",
        ),
        "down": (
            "живёт настоящим",
            "Фокус на немедленном вознаграждении. "
            "Может упускать долгосрочно выгодные стратегии.",
        ),
    },
    # ... остальные гены
}
```

---

### 2.9 build_lineage_trend()

```python
def build_lineage_trend(
    agent: Any,
    death_registry: Any,
    generation_index_map: dict[str, int],
    max_ancestors: int = 5,
) -> list[LineageTrendPoint] | None:
    """
    Построить тренд по цепочке предков через DeathRegistry.

    Алгоритм:
    1. Начать с agent.parents
    2. Для каждого parent_id: death_registry.get_memorial(parent_id)
    3. Из мемориала взять genome_genes и финальные показатели
    4. Рекурсивно подняться до прародителей (до max_ancestors уровней)
    5. Упорядочить по generation ASC → получить хронологический тренд

    Дополнительно добавить текущего агента в конец цепочки
    (если он жив — из реальных генов, если умер — из мемориала).

    Возвращает None если нет данных ни об одном предке в registry.
    """
```

**Анализ тренда:**
```python
def analyze_trend(points: list[LineageTrendPoint], gene_key: str) -> str:
    """
    Вернуть строку-оценку тренда для одного гена.

    Например:
    - "↘ снижается" если последние 3 значения стабильно падают
    - "↗ растёт" если стабильно растёт
    - "↔ стабильно" если изменения < 5% диапазона
    - "↕ нестабильно" иначе
    """
```

---

## 3. Изменения в agent_inspector.py

### 3.1 Изменения в InspectorData

```python
@dataclass
class InspectorData:
    ...
    genome_portrait: GenomePortrait | None = None    # НОВОЕ
    ...
```

### 3.2 Изменения в build_inspector_data_from_agent()

```python
from .genome_portrait import build_portrait, build_lineage_trend

def build_inspector_data_from_agent(agent, display_name, death_registry=None, generation_index_map=None):
    ...
    genome = getattr(agent, "genome", None)
    genome_genes = _safe_dict_floats(getattr(genome, "genes", {}) or {})
    genome_inheritance_meta = dict(getattr(agent, "genome_inheritance_meta", {}) or {})

    # НОВОЕ: построить портрет
    portrait = None
    if genome_genes:
        try:
            portrait = build_portrait(genome_genes, genome_inheritance_meta)
            if death_registry is not None:
                gim = generation_index_map or {}
                portrait.lineage_trend = build_lineage_trend(
                    agent, death_registry, gim, max_ancestors=5
                )
        except Exception:
            pass
    ...
    return InspectorData(..., genome_portrait=portrait, ...)
```

### 3.3 Изменения в _draw_tab_genome()

```python
def _draw_tab_genome(self, surface, font, font_small, font_mono) -> int:
    assert self._data is not None
    y = 6

    portrait = self._data.genome_portrait

    if portrait is not None:
        y = self._draw_genome_portrait(surface, font, font_small, y, portrait)
        y += 12

    # Мутации
    if portrait and portrait.mutations:
        y = self._draw_mutation_effects(surface, font, font_small, y, portrait.mutations)
        y += 12

    # Тренды линии
    if portrait and portrait.lineage_trend and len(portrait.lineage_trend) >= 2:
        y = self._draw_lineage_trend(surface, font, font_small, y, portrait.lineage_trend)
        y += 12

    # Полная таблица генов (раскрываемая)
    y = self._draw_genome_table_collapsible(surface, font, font_small, font_mono, y)

    return y
```

### 3.4 _draw_genome_portrait()

```python
def _draw_genome_portrait(self, surface, font, font_small, y, portrait) -> int:
    """
    Секция 1: ПОРТРЕТ ЛИЧНОСТИ

    Отрисовывает:
    1. Заголовок "Портрет личности"
    2. Trait bars — 5 категорий с барами и ярлыками
    3. Summary — 2-3 предложения
    4. Strengths/Weaknesses/Neutral блоки
    """
    surface.blit(font.render("Портрет личности", True, INSPECTOR_TEXT), (0, y))
    y += 24

    # Trait bars (5 штук)
    TRAIT_ORDER = ["temperament", "social", "endurance", "cognition", "lifespan"]
    TRAIT_COLORS = {
        "temperament": (210, 120, 80),   # оранжевый
        "social":      (120, 180, 130),  # зелёный
        "endurance":   (80, 140, 200),   # синий
        "cognition":   (160, 100, 200),  # фиолетовый
        "lifespan":    (180, 160, 80),   # золотой
    }

    for cat in TRAIT_ORDER:
        ts = portrait.trait_scores.get(cat)
        if ts is None:
            continue
        label = TRAIT_LABELS_RU.get(cat, cat)
        score = ts.score

        # Метка (60px)
        surface.blit(font_small.render(label, True, INSPECTOR_MUTED_TEXT), (0, y))
        # Бар (120px)
        bar_x = 100
        pygame.draw.rect(surface, BAR_BG, pygame.Rect(bar_x, y+4, 120, 8), border_radius=3)
        fill_w = int(120 * score)
        if fill_w > 0:
            pygame.draw.rect(surface, TRAIT_COLORS[cat], pygame.Rect(bar_x, y+4, fill_w, 8), border_radius=3)
        # Ярлык (65px после бара)
        surface.blit(font_small.render(ts.label, True, INSPECTOR_TEXT), (228, y))
        y += 18

    # Summary
    y += 8
    summary_lines = _wrap_text(portrait.summary, max_chars=58)
    for line in summary_lines:
        surface.blit(font_small.render(line, True, INSPECTOR_TEXT), (0, y))
        y += 16

    # Strengths
    y += 8
    if portrait.strengths:
        surface.blit(font_small.render("Сильные стороны:", True, INSPECTOR_MUTED_TEXT), (0, y))
        y += 16
        for s in portrait.strengths:
            surface.blit(font_small.render(f"  ✓ {s}", True, (80, 150, 80)), (0, y))
            y += 15

    # Weaknesses
    if portrait.weaknesses:
        surface.blit(font_small.render("Слабые стороны:", True, INSPECTOR_MUTED_TEXT), (0, y))
        y += 16
        for w in portrait.weaknesses:
            surface.blit(font_small.render(f"  ✗ {w}", True, (180, 80, 60)), (0, y))
            y += 15

    # Neutral
    if portrait.neutral_traits:
        for n in portrait.neutral_traits:
            surface.blit(font_small.render(f"  ~ {n}", True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 15

    return y
```

### 3.5 _draw_mutation_effects()

```python
def _draw_mutation_effects(self, surface, font, font_small, y, mutations) -> int:
    """
    Секция 2: ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО РОДИТЕЛЕЙ

    Показывает только мутации с magnitude >= "minor".
    Формат строки:
      [иконка] [ген]   [delta]   [consequence_short]
      [detail в виде wrapped text, цвет приглушённый]

    Иконки по valence:
      positive → ✓ зелёный
      negative → ✗ красный
      neutral  → ~ серый
    """
    VALENCE_COLORS = {
        "positive": (80, 150, 80),
        "negative": (180, 80, 60),
        "neutral":  (120, 112, 100),
    }
    MAGNITUDE_PREFIX = {
        "major":    "●",
        "moderate": "◆",
        "minor":    "·",
    }

    surface.blit(font.render("Изменения в генах", True, INSPECTOR_TEXT), (0, y))
    y += 22

    for mut in mutations[:8]:
        icon = MAGNITUDE_PREFIX.get(mut.magnitude, "·")
        color = VALENCE_COLORS.get(mut.valence, INSPECTOR_MUTED_TEXT)
        sign = "+" if mut.delta >= 0 else ""
        header = f"{icon} {mut.gene_key:<28} {sign}{mut.delta:+.3f}"
        surface.blit(font_small.render(header, True, color), (0, y))
        y += 15
        short = f"  → {mut.consequence_short}"
        surface.blit(font_small.render(short, True, INSPECTOR_TEXT), (0, y))
        y += 14
        # Detail (wrapped)
        for line in _wrap_text(f"  {mut.consequence_detail}", max_chars=62):
            surface.blit(font_small.render(line, True, INSPECTOR_MUTED_TEXT), (0, y))
            y += 13
        y += 4

    return y
```

### 3.6 _draw_lineage_trend()

```python
def _draw_lineage_trend(self, surface, font, font_small, y, trend_points) -> int:
    """
    Секция 3: ТРЕНД ЛИНИИ

    Для каждого отслеживаемого гена показывает:
    - Имена предков (G0A1SF → G1A3SM → G2A6SF → [текущий])
    - Значения гена в каждом поколении в виде мини-бара
    - Итоговое направление тренда

    Дополнительно: стресс и кортизол при смерти у предков.
    """
    surface.blit(font.render("Тренд линии", True, INSPECTOR_TEXT), (0, y))
    y += 22

    # Строка имён предков
    names = " → ".join(p.display_name for p in trend_points)
    for line in _wrap_text(names, max_chars=60):
        surface.blit(font_small.render(line, True, INSPECTOR_MUTED_TEXT), (0, y))
        y += 14
    y += 4

    # Для каждого отслеживаемого гена — мини-бары
    from .genome_portrait import LINEAGE_TRACKED_GENES, GENE_REGISTRY, analyze_trend

    for gene_key in LINEAGE_TRACKED_GENES:
        values = []
        for pt in trend_points:
            if gene_key in pt.gene_values:
                values.append(pt.gene_values[gene_key])

        if not values:
            continue

        gene_meta = GENE_REGISTRY.get(gene_key)
        low = gene_meta.low if gene_meta else 0.0
        high = gene_meta.high if gene_meta else 1.0
        span = max(0.001, high - low)

        label = gene_key.replace("_", " ")[:20]
        surface.blit(font_small.render(f"{label}:", True, INSPECTOR_MUTED_TEXT), (0, y))
        bar_start_x = 148
        seg_w = 22   # ширина одного сегмента
        gap = 3

        for idx, val in enumerate(values):
            norm = max(0.0, min(1.0, (val - low) / span))
            is_current = (idx == len(values) - 1)
            # Фон сегмента
            seg_rect = pygame.Rect(bar_start_x + idx * (seg_w + gap), y + 3, seg_w, 9)
            pygame.draw.rect(surface, BAR_BG, seg_rect, border_radius=2)
            fill = int(seg_w * norm)
            if fill > 0:
                fill_color = (80, 140, 200) if not is_current else (180, 140, 60)
                pygame.draw.rect(surface, fill_color,
                    pygame.Rect(seg_rect.x, seg_rect.y, fill, 9), border_radius=2)

        trend_str = analyze_trend(
            [type('P', (), {'gene_values': {gene_key: v}})() for v in values],
            gene_key
        )
        trend_x = bar_start_x + len(values) * (seg_w + gap) + 6
        surface.blit(font_small.render(trend_str, True, INSPECTOR_TEXT), (trend_x, y))
        y += 18

    # Финальная строка: стресс/кортизол предков
    y += 4
    surface.blit(font_small.render("Стресс при смерти:", True, INSPECTOR_MUTED_TEXT), (0, y))
    stress_vals = [f"{p.stress_at_death:.2f}" for p in trend_points if p.stress_at_death > 0]
    surface.blit(font_small.render(" → ".join(stress_vals), True, INSPECTOR_TEXT), (148, y))
    y += 16

    surface.blit(font_small.render("Кортизол при смерти:", True, INSPECTOR_MUTED_TEXT), (0, y))
    cort_vals = [f"{p.cortisol_at_death:.2f}" for p in trend_points if p.cortisol_at_death > 0]
    surface.blit(font_small.render(" → ".join(cort_vals), True, INSPECTOR_TEXT), (148, y))
    y += 16

    return y
```

### 3.7 _draw_genome_table_collapsible()

```python
def _draw_genome_table_collapsible(self, surface, font, font_small, font_mono, y) -> int:
    """
    Раскрываемая таблица всех генов.
    По умолчанию свёрнута.
    Клик на заголовок — toggle.
    """
    # toggle через self._genome_table_expanded: bool = False
    label = "▼ все гены" if self._genome_table_expanded else "▶ все гены"
    surface.blit(font_small.render(label, True, INSPECTOR_MUTED_TEXT), (0, y))
    self._genome_table_toggle_rect_y = y   # для hit-testing клика

    if not self._genome_table_expanded:
        return y + 18

    y += 20
    for key, value in sorted(self._data.genome_genes.items(), key=lambda p: p[0]):
        surface.blit(font_mono.render(f"{key:<28} {value:>8.5f}", True, INSPECTOR_TEXT), (0, y))
        y += 15

    return y + 6
```

---

## 4. Изменения в ColonyGUI

```python
def open_inspector(self, agent_id: str) -> None:
    ...
    if living_agent is not None:
        # ИЗМЕНЕНИЕ: передать death_registry и generation_index_map
        payload = build_inspector_data_from_agent(
            living_agent,
            display_name,
            death_registry=getattr(self.runner, "death_registry", None),
            generation_index_map=self._generation_index_map,
        )
        ...
```

---

## 5. Вспомогательная функция _wrap_text()

```python
def _wrap_text(text: str, max_chars: int = 60) -> list[str]:
    """
    Разбить текст на строки по словам.
    Используется для summary и consequence_detail.
    """
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
```

---

## 6. Ограничения реализации

1. `build_portrait()` — никогда не падает. Все исключения → fallback портрет с пустыми полями.
2. `build_lineage_trend()` — если нет данных ни об одном предке → None.
3. Таблица генов свёрнута по умолчанию — занимает одну строку.
4. Скролл инспектора работает для всего содержимого вкладки.
5. Портрет строится при каждом открытии инспектора — не кэшируется.
6. `_genome_table_expanded = False` сбрасывается при смене вкладки или закрытии.
7. Тренды показываются только при наличии ≥ 2 точек в цепочке.
8. `_wrap_text()` — максимум 8 строк для любого текста (обрезать с "...").
9. Python 3.10+, без внешних зависимостей.

---

## 7. Тест-кейсы

### TC-01: build_portrait из дефолтного генома

```python
from genome import GenomeVector
from colony_gui.genome_portrait import build_portrait

genes = dict(GenomeVector.default().genes)
portrait = build_portrait(genes, {})

assert portrait is not None
assert len(portrait.trait_scores) == 5
for cat in ["temperament", "social", "endurance", "cognition", "lifespan"]:
    assert cat in portrait.trait_scores
    assert 0.0 <= portrait.trait_scores[cat].score <= 1.0
assert len(portrait.summary) > 10
```

### TC-02: Высокий lt_max_lifespan_factor → lifespan trait высокий

```python
genes = dict(GenomeVector.default().genes)
genes["lt_max_lifespan_factor"] = 1.45   # близко к максимуму 1.5

portrait = build_portrait(genes, {})
assert portrait.trait_scores["lifespan"].score > 0.7
assert any("долгожит" in s.lower() for s in portrait.strengths)
```

### TC-03: Высокий af_decay_stress → weakness "долго носит стресс"

```python
genes = dict(GenomeVector.default().genes)
genes["af_decay_stress"] = 0.87   # близко к максимуму 0.88

portrait = build_portrait(genes, {})
assert portrait.trait_scores["temperament"].score < 0.4
assert any("стресс" in w.lower() for w in portrait.weaknesses)
```

### TC-04: MutationEffect подбирается для major мутации

```python
genes = dict(GenomeVector.default().genes)
parent_genes = dict(GenomeVector.default().genes)
parent_genes["wk_recovery_factor"] = 0.85
genes["wk_recovery_factor"] = 0.58   # delta = -0.27

meta = {
    "parent_midpoint_genes": parent_genes,
    "top_shifted_genes": [{"key": "wk_recovery_factor", "delta": -0.27}],
}
portrait = build_portrait(genes, meta)

mut = next((m for m in portrait.mutations if m.gene_key == "wk_recovery_factor"), None)
assert mut is not None
assert mut.magnitude == "major"
assert mut.valence == "negative"
assert mut.direction == "down"
assert "восстанавл" in mut.consequence_short.lower()
```

### TC-05: build_portrait не падает на пустом геноме

```python
portrait = build_portrait({}, {})
assert portrait is not None
assert portrait.summary != ""
assert portrait.mutations == []
```

### TC-06: build_lineage_trend возвращает None без предков в registry

```python
from death_registry import DeathRegistry
from colony_gui.genome_portrait import build_lineage_trend

registry = DeathRegistry()
agent = ChinchillaAgent(sex="F", generation=0)
agent.parents = (None, None)

result = build_lineage_trend(agent, registry, {})
assert result is None
```

### TC-07: build_lineage_trend с одним предком в registry

```python
registry = DeathRegistry()
mother = ChinchillaAgent(sex="F", generation=0)
mother.genome = GenomeVector.default()
registry.register_birth(mother, 0.0)
registry.register_death(mother, 1000.0, {})

child = ChinchillaAgent(sex="M", generation=1)
child.parents = (mother.agent_id, None)
child.genome = GenomeVector.default()

result = build_lineage_trend(child, registry, {})
assert result is not None
assert len(result) >= 2  # мать + текущий
assert result[0].agent_id == mother.agent_id
assert result[-1].agent_id == child.agent_id
```

### TC-08: analyze_trend определяет направление

```python
from colony_gui.genome_portrait import analyze_trend, LineageTrendPoint

# Стабильно снижается
points_down = [
    LineageTrendPoint("a1", "G0A1", 0, {"af_decay_stress": 0.85}, 0.94, 1.0, 18000),
    LineageTrendPoint("a2", "G1A1", 1, {"af_decay_stress": 0.80}, 0.88, 0.95, 18200),
    LineageTrendPoint("a3", "G2A1", 2, {"af_decay_stress": 0.73}, 0.81, 0.82, 18400),
]
trend = analyze_trend(points_down, "af_decay_stress")
assert "↘" in trend or "снижа" in trend.lower()

# Стабильно растёт
points_up = [
    LineageTrendPoint("b1", "G0A2", 0, {"lt_max_lifespan_factor": 1.00}, 0.92, 1.0, 18000),
    LineageTrendPoint("b2", "G1A2", 1, {"lt_max_lifespan_factor": 1.10}, 0.87, 0.92, 18500),
    LineageTrendPoint("b3", "G2A2", 2, {"lt_max_lifespan_factor": 1.23}, 0.81, 0.85, 19000),
]
trend_up = analyze_trend(points_up, "lt_max_lifespan_factor")
assert "↗" in trend_up or "рост" in trend_up.lower()
```

### TC-09: Портрет отрисовывается без ошибок pygame

```python
import pygame
pygame.init()
screen = pygame.Surface((500, 700), pygame.SRCALPHA)
font = pygame.font.SysFont("Arial", 16)
font_small = pygame.font.SysFont("Arial", 12)
font_mono = pygame.font.SysFont("Courier New", 12)

genes = dict(GenomeVector.default().genes)
genes["lt_max_lifespan_factor"] = 1.3
genes["af_decay_stress"] = 0.62

portrait = build_portrait(genes, {})
data = InspectorData(
    agent_id="test", display_name="G2A5SM", is_deceased=False,
    sex="M", generation=2, parents=(None, None), age=5000.0,
    lived_steps=5000, cause_of_death="", genome_portrait=portrait,
    genome_genes=genes,
)
overlay = AgentInspectorOverlay()
overlay.open(data)
overlay._active_tab = 3  # Геном
# Не должно упасть
overlay.draw(screen, font, font_small, font_mono)
```

### TC-10: Таблица генов сворачивается/разворачивается

```python
overlay = AgentInspectorOverlay()
overlay.open(data)
overlay._active_tab = 3
assert overlay._genome_table_expanded is False

# Симулировать клик на toggle
overlay._genome_table_expanded = True
assert overlay._genome_table_expanded is True

# Смена вкладки сбрасывает
overlay._active_tab = 0
overlay._active_tab = 3
assert overlay._genome_table_expanded is False
```

---

## 8. Примечания для реализующего агента

- `genome_portrait.py` — независимый модуль без pygame импортов. Все pygame вещи остаются в `agent_inspector.py`.
- `_wrap_text()` вынести в `utils.py` или в `genome_portrait.py` (не дублировать).
- `MUTATION_CONSEQUENCES` — словарь охватывает ~10 наиболее важных генов. Для остальных: fallback к `low_label`/`high_label` из `GeneRange`.
- При умершем агенте (`is_deceased=True`) портрет строится из `memorial.genome_genes` — те же функции, те же правила.
- `_genome_table_expanded` сбрасывается в `False` при `overlay.open()` и при смене вкладки на не-геном.
- Trait bar ярлыки — короткие (≤ 15 символов): "чувствительный", "замкнутый", "долгожитель", "аналитик".
- `build_lineage_trend()` ищет предков BFS по `parents` — не DFS. При наличии двух родителей берёт обоих и их предков, объединяет по generation, дедуплицирует.
- `analyze_trend()` сравнивает первую и последнюю треть значений. Если `(last_mean - first_mean) / span > 0.05` → рост, `< -0.05` → снижение, иначе стабильно.
