## Abstract

Russian version: [SPEC_SwarmAnalyticsOverlay.ru.md](SPEC_SwarmAnalyticsOverlay.ru.md)

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

This document specifies the swarm-analytics subsystem of the chinchilla-colony graphical interface. Its subject is the `SwarmAnalyticsOverlay` together with the aggregation module `swarm_analytics`, which read the current slice of living agents, the death registry with complete genomes, and the time series maintained by `ColonyPopulationObserver`. The subsystem treats the colony as one evolving organism and is concerned with change across generations, the present condition of the swarm, the direction of gene selection, colony-level behavioural patterns, and whether the swarm is moving toward stability or toward extinction.

The overlay is divided into five tabs: state, evolution, genomes, behaviour, and prognosis. The data module defines per-generation aggregates, evolutionary tracks for individual genes with an assessment of directional shift, action-frequency profiles, and measures of social structure, including kinship, rivalry, and isolation. Data are gathered when the overlay is opened rather than on every simulation tick, and a failure in one section does not stop the others.

Within the multi-agent NOWA installation, the specification establishes an observation protocol that is separate from action selection. The overlay does not alter agent data. It thereby states the conditions under which demographic, affective, genetic, and social processes of the colony can be compared over time, without the measurement feeding back into the simulated individuals.

# Specification: SwarmAnalyticsOverlay

**Files:**
- `colony_gui/swarm_analytics.py` — new analytics module (without pygame)
- `colony_gui/swarm_analytics_overlay.py` — tabbed overlay (pygame)
- changes in `colony_gui/colony_gui.py` — integration
- changes in `colony_gui/app.py` — key binding and drawing

**Version:** 1.0

---

## 1. Concept

`SwarmAnalyticsOverlay` is an analytical instrument for understanding the evolution of the colony as a single organism. It answers the following questions:

- What changed from generation to generation, and why?
- What is the present condition of the swarm — is it healthy?
- Which genes are under selection, and which are neutral?
- Are there behavioural patterns at the level of the whole colony?
- Where is the swarm moving — toward stability or toward extinction?

**Data sources:**
- `runner.agents` — living agents (the current slice)
- `runner.death_registry` — all deceased agents, with complete genomes
- `runner.observer` / `ColonyPopulationObserver` — temporal trends of snapshots

**Principles:**
- Read-only: the overlay mutates no data
- Lazy: data are gathered when the overlay is opened, not on every tick
- Tolerant: an error in one section does not bring down the others

---

## 2. Overlay tabs

```
┌─────────────────────────────────────────────────────────────────┐
│  Аналитика роя  │  живых: 47  умерших: 312  поколений: 8       │
│                                              [ESC / A закрыть]  │
├──────────┬──────────┬──────────┬──────────┬────────────────────┤
│  Состояние│ Эволюция │  Геномы  │Поведение │    Прогноз         │
├──────────┴──────────┴──────────┴──────────┴────────────────────┤
│  [содержимое активной вкладки]                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Five tabs:**

| # | Name | Content |
|---|---|---|
| 0 | State | Current slice: demography, affect, neuromodulators, resources |
| 1 | Evolution | Trends across generations: stress, cortisol, longevity, energy |
| 2 | Genomes | Gene selection: what has shifted, what is stable, what has diverged |
| 3 | Behaviour | Action patterns, social structure, characters of the swarm |
| 4 | Prognosis | Risks, trends, and an interpretation of where the swarm is moving |

---

## 3. swarm_analytics.py — the data module

### 3.1 Data structures

```python
@dataclass
class GenerationSummary:
    """Агрегат по одному поколению (из мемориалов + живых)."""
    generation: int
    agent_count: int              # сколько агентов в поколении
    alive_count: int              # сколько ещё живы
    dead_count: int               # сколько умерли
    mean_lived_steps: float       # средняя продолжительность жизни
    mean_stress_at_death: float   # средний стресс при смерти
    mean_cortisol_at_death: float
    mean_energy_at_death: float
    mean_vitality_at_death: float
    cause_distribution: dict[str, int]   # {cause: count}
    mean_genome: dict[str, float]        # средние значения генов
    genome_std: dict[str, float]         # стандартное отклонение генов
    total_offspring: int                 # суммарно потомков
    mean_total_offspring: float


@dataclass
class GeneEvolutionTrack:
    """Эволюционный трек одного гена по поколениям."""
    gene_key: str
    group: str                           # "af", "nm", "wk" и т.д.
    values_by_gen: dict[int, float]      # {generation: mean_value}
    std_by_gen: dict[int, float]         # {generation: std_value}
    trend_label: str                     # "↗ растёт" | "↘ снижается" | "↔ стабильно"
    trend_magnitude: float               # насколько сильно изменился [0..1]
    interpretation: str                  # что это означает для колонии
    is_under_selection: bool             # есть ли значимый направленный сдвиг


@dataclass
class BehaviorPattern:
    """Частота действия в текущей популяции."""
    action: str
    count: int
    fraction: float             # [0..1] доля агентов с этим действием
    label_ru: str


@dataclass
class SocialStructure:
    """Социальная структура текущей колонии."""
    total_known_pairs: int
    bonded_pairs: int
    rival_pairs: int
    kin_pairs: int
    mean_affinity: float
    cohesion_index: float       # из ColonyPopulationObserver
    isolation_count: int        # агенты без единой связи


@dataclass
class ColonyHealthIndex:
    """Интегральный индекс здоровья колонии [0..1]."""
    overall: float
    components: dict[str, float]   # {компонент: значение}
    verdict: str                   # текстовый вывод
    color: tuple[int, int, int]    # RGB для отображения


@dataclass
class EvolutionaryForecast:
    """Прогноз на основе текущих трендов."""
    extinction_risk: float          # [0..1]
    extinction_risk_label: str
    dominant_pressure: str          # главный селективный фактор
    adapting_traits: list[str]      # что адаптируется
    stagnant_traits: list[str]      # что не меняется
    key_risks: list[str]            # главные риски
    key_opportunities: list[str]    # позитивные тренды
    summary: str                    # 3-4 предложения


@dataclass
class SwarmAnalytics:
    """Полный аналитический снапшот роя."""
    # Мета
    snapshot_time: float            # sim_time сбора
    total_ever_lived: int
    living_count: int
    dead_count: int
    generation_range: tuple[int, int]

    # По поколениям
    generation_summaries: list[GenerationSummary]

    # Генетика
    gene_tracks: list[GeneEvolutionTrack]
    most_evolved_genes: list[str]       # топ-5 сильнее всего изменившихся
    most_stable_genes: list[str]        # топ-5 самых стабильных

    # Текущее состояние
    current_action_distribution: list[BehaviorPattern]
    current_social: SocialStructure
    health_index: ColonyHealthIndex

    # Тренды из observer
    observer_stress_trend: list[float]
    observer_energy_trend: list[float]
    observer_population_trend: list[float]
    observer_cohesion_trend: list[float]

    # Прогноз
    forecast: EvolutionaryForecast
```

---

### 3.2 Construction of GenerationSummary

```python
def build_generation_summaries(
    living_agents: list[Any],
    death_registry: Any,
) -> list[GenerationSummary]:
    """
    Агрегировать данные по поколениям из живых агентов и мемориалов.

    Алгоритм:
    1. Сгруппировать живых по generation
    2. Сгруппировать мемориалов по generation
    3. Объединить — для каждого поколения:
       a. Посчитать mean/std для всех числовых полей
       b. Собрать cause_distribution из мемориалов
       c. Вычислить mean_genome как среднее genome_genes по мемориалам
       d. genome_std — стандартное отклонение по тем же генам
    4. Отсортировать по generation ASC

    Живые агенты не имеют final_stress/cortisol/energy —
    для них использовать текущие значения (stress, cortisol, energy).
    """
```

---

### 3.3 Construction of GeneEvolutionTrack

```python
TRACKED_GENE_GROUPS = {
    "af": ["af_decay_stress", "af_decay_curiosity", "af_decay_attachment",
           "af_decay_trust", "af_lambda_reg"],
    "nm": ["nm_acc_k_cort", "nm_acc_k_ht", "nm_decay_half_life"],
    "wk": ["wk_recovery_factor", "wk_accumulation_factor"],
    "dr": ["dr_social_drive_baseline", "dr_curiosity_baseline",
           "dr_perception_radius_factor"],
    "lr": ["lr_alpha", "lr_gamma"],
    "lt": ["lt_max_lifespan_factor"],
}

ALL_TRACKED_GENES: list[str] = [gene for genes in TRACKED_GENE_GROUPS.values() for gene in genes]


def build_gene_tracks(
    generation_summaries: list[GenerationSummary],
    min_generations: int = 2,
) -> list[GeneEvolutionTrack]:
    """
    Построить эволюционный трек для каждого отслеживаемого гена.

    Для каждого гена:
    1. Собрать values_by_gen из generation_summaries[i].mean_genome
    2. Собрать std_by_gen аналогично
    3. Вычислить trend_label через compare_first_last_third()
    4. Вычислить trend_magnitude = abs(last_mean - first_mean) / gene_range
    5. is_under_selection если trend_magnitude > 0.08 и направление стабильно
    6. interpretation из GENE_EVOLUTION_INTERPRETATIONS

    Возвращать только гены с данными в >= min_generations поколениях.
    """


def compare_first_last_third(values: list[float], gene_range: float) -> tuple[str, float]:
    """
    Сравнить первую и последнюю треть значений.
    Возвращает (trend_label, normalized_magnitude).

    Правила:
        change = (last_mean - first_mean) / max(gene_range, 1e-6)
        if change > +0.05: "↗ растёт"
        if change < -0.05: "↘ снижается"
        else: "↔ стабильно"
    """
```

---

### 3.4 Interpretations of gene evolution

```python
GENE_EVOLUTION_INTERPRETATIONS: dict[str, dict[str, str]] = {
    # gene_key → {trend_direction → interpretation}

    "af_decay_stress": {
        "up":   ("Стресс держится дольше. Колония адаптируется к хроническому стрессу, "
                 "но риск подавления репродукции растёт."),
        "down": ("Стресс рассеивается быстрее. Позитивный тренд: "
                 "агенты восстанавливаются после стрессовых событий эффективнее."),
        "flat": ("Скорость рассеивания стресса стабильна. "
                 "Нет выраженного отбора по этому признаку."),
    },
    "nm_acc_k_cort": {
        "up":   ("Кортизол-чувствительность растёт. Стресс сильнее влияет на физиологию — "
                 "популяция становится более уязвимой к кортизоловому давлению."),
        "down": ("Кортизол-чувствительность снижается. "
                 "Колония адаптируется к высокому стрессу через сниженную реактивность."),
        "flat": ("Кортизол-чувствительность стабильна."),
    },
    "lt_max_lifespan_factor": {
        "up":   ("Потенциальная продолжительность жизни растёт. "
                 "Отбор выявил преимущество долгожителей — вероятно, ресурсов достаточно "
                 "и кортизол снизился до уровня где ген реализуется."),
        "down": ("Продолжительность жизни сокращается. "
                 "Возможен отбор на быстрое размножение в ущерб долголетию."),
        "flat": ("Потенциальная продолжительность жизни не меняется. "
                 "Ген не находится под значимым отбором."),
    },
    "wk_recovery_factor": {
        "up":   ("Восстановление после сна ускоряется. "
                 "Агенты с эффективным сном имеют преимущество в активном времени."),
        "down": ("Восстановление после сна замедляется. "
                 "Возможно контринтуитивный отбор — агенты со сниженной потребностью в сне."),
        "flat": ("Скорость восстановления стабильна."),
    },
    "wk_accumulation_factor": {
        "up":   ("Усталость накапливается быстрее. "
                 "Агенты нуждаются в более частом сне — возможно давление высокой активности."),
        "down": ("Усталость накапливается медленнее. "
                 "Колония эволюционирует к большей выносливости."),
        "flat": ("Скорость накопления усталости стабильна."),
    },
    "dr_social_drive_baseline": {
        "up":   ("Социальный инстинкт усиливается. "
                 "Колония становится более сплочённой, социальные связи укрепляются."),
        "down": ("Социальный инстинкт ослабевает. "
                 "Рост индивидуализма — возможно следствие конкуренции за ресурсы."),
        "flat": ("Социальный инстинкт стабилен."),
    },
    "dr_curiosity_baseline": {
        "up":   ("Любопытство растёт. Агенты активнее исследуют среду — "
                 "возможно это помогает находить ресурсы."),
        "down": ("Любопытство снижается. "
                 "Консервативные стратегии поведения получают преимущество."),
        "flat": ("Базовый уровень любопытства стабилен."),
    },
    "lr_alpha": {
        "up":   ("Скорость обучения растёт. Быстрая адаптация выгодна, "
                 "но слишком высокое значение делает поведение нестабильным."),
        "down": ("Скорость обучения снижается. "
                 "Отбор на консервативное, предсказуемое поведение."),
        "flat": ("Скорость обучения стабильна."),
    },
    "lr_gamma": {
        "up":   ("Горизонт планирования растёт. Агенты учитывают долгосрочные последствия."),
        "down": ("Горизонт планирования сокращается. "
                 "Краткосрочные стратегии получают преимущество."),
        "flat": ("Горизонт планирования стабилен."),
    },
    "af_lambda_reg": {
        "up":   ("Эмоциональная саморегуляция усиливается. "
                 "Агенты лучше гасят аффективные всплески."),
        "down": ("Эмоциональная саморегуляция слабеет. "
                 "Аффект развивается более свободно."),
        "flat": ("Саморегуляция стабильна."),
    },
    "nm_acc_k_ht": {
        "up":   ("Серотониновый тонус растёт. Базовый уровень благополучия повышается."),
        "down": ("Серотониновый тонус снижается. "
                 "Негативный аффект становится более частым."),
        "flat": ("Серотониновый тонус стабилен."),
    },
    "dr_perception_radius_factor": {
        "up":   ("Поле восприятия расширяется. Агенты замечают больше событий вокруг."),
        "down": ("Поле восприятия сужается. Агенты фокусируются на ближайшем окружении."),
        "flat": ("Радиус восприятия стабилен."),
    },
    # Для остальных генов — генерический fallback
    "_default": {
        "up":   "Значение гена растёт по поколениям.",
        "down": "Значение гена снижается по поколениям.",
        "flat": "Ген стабилен — без выраженного отбора.",
    },
}
```

---

### 3.5 Colony health index

```python
HEALTH_COMPONENTS = {
    "stress":       (0.25, True),   # (вес, lower_is_better)
    "cortisol":     (0.20, True),
    "energy":       (0.20, False),
    "social":       (0.15, False),  # cohesion_index
    "lifespan":     (0.10, False),  # mean_lived_steps / max_lifespan
    "diversity":    (0.10, False),  # genome diversity из swarm
}


def compute_health_index(
    living_agents: list[Any],
    observer: Any,
    swarm: Any,
) -> ColonyHealthIndex:
    """
    Вычислить интегральный индекс здоровья [0..1].

    Для каждого компонента:
    1. Получить значение из соответствующего источника
    2. Нормировать в [0..1]
    3. Если lower_is_better: перевернуть (1 - norm_value)
    4. Взвешенная сумма

    Вердикты:
        > 0.75: "Колония здорова и активно развивается"
        > 0.55: "Колония стабильна с умеренными рисками"
        > 0.35: "Колония под давлением, требует внимания"
        <= 0.35: "Колония в критическом состоянии"

    Цвета:
        > 0.75: (90, 175, 110)    зелёный
        > 0.55: (185, 165, 65)    жёлтый
        > 0.35: (210, 120, 60)    оранжевый
        <= 0.35: (200, 65, 55)    красный
    """
```

---

### 3.6 Evolutionary forecast

```python
FORECAST_RISKS: list[tuple[Callable, str]] = [
    (lambda d: d["mean_cortisol"] > 0.80,
     "Хронический кортизол блокирует репродукцию"),
    (lambda d: d["lt_trend"] == "↘ снижается",
     "Потенциальная продолжительность жизни сокращается"),
    (lambda d: d["diversity"] < 0.15,
     "Низкое генетическое разнообразие — founder effect"),
    (lambda d: d["female_fraction"] < 0.35 or d["female_fraction"] > 0.65,
     "Половой дисбаланс угрожает размножению"),
    (lambda d: d["mean_energy_at_death"] < 0.15,
     "Агенты умирают с истощёнными энергетическими резервами"),
    (lambda d: d["cohesion"] < 0.10,
     "Слабая социальная сплочённость — изоляция особей"),
    (lambda d: d["extinction_risk"] > 0.50,
     "Высокий риск вымирания по оценке ColonyPopulationObserver"),
]

FORECAST_OPPORTUNITIES: list[tuple[Callable, str]] = [
    (lambda d: d["lt_trend"] == "↗ растёт",
     "Ген долголетия под положительным отбором"),
    (lambda d: d["stress_trend"] == "↘ снижается",
     "Стресс снижается — репродуктивный потенциал растёт"),
    (lambda d: d["cortisol_trend"] == "↘ снижается",
     "Кортизол снижается — адаптация к стрессу работает"),
    (lambda d: d["social_trend"] == "↗ растёт",
     "Социальная сплочённость растёт — колония укрепляется"),
    (lambda d: d["diversity"] > 0.30,
     "Высокое генетическое разнообразие — хороший эволюционный потенциал"),
    (lambda d: d["mean_offspring_per_agent"] > 2.5,
     "Высокая репродуктивная успешность"),
]
```

---

### 3.7 Principal function

```python
def build_swarm_analytics(
    runner: Any,
    observer: Any,
    generation_index_map: dict[str, int] | None = None,
) -> SwarmAnalytics:
    """
    Построить полный аналитический снапшот роя.

    Никогда не вызывает исключений.
    При любой ошибке компонент заполняется дефолтными значениями.

    Аргументы:
        runner: SimulationRunner с .agents, .death_registry, .swarm
        observer: ColonyPopulationObserver с .history, .get_trend()
        generation_index_map: для отображения имён агентов

    Время выполнения: O(N * G) где N = кол-во агентов, G = кол-во генов.
    При N=500, G=20 ≈ 10ms — допустимо при открытии overlay.
    """
```

---

## 4. swarm_analytics_overlay.py

### 4.1 SwarmAnalyticsOverlay

```python
OVERLAY_WIDTH  = 900
OVERLAY_HEIGHT = 680
TABS = ["Состояние", "Эволюция", "Геномы", "Поведение", "Прогноз"]

# Цвета
OVERLAY_BG        = (242, 236, 225, 248)
OVERLAY_HEADER    = (218, 208, 192)
OVERLAY_BORDER    = (115, 100, 82)
SECTION_LINE      = (195, 182, 165)
SECTION_TITLE_CLR = (108, 95, 78)
TAB_ACTIVE        = (198, 185, 168)
TAB_INACTIVE      = (228, 220, 208)
TAB_TEXT_ACTIVE   = (35, 28, 20)
TAB_TEXT_INACTIVE = (100, 88, 70)

GEN_COLORS: list[tuple[int, int, int]] = [
    (100, 155, 210), (90, 185, 125), (215, 145, 60),
    (185, 90, 175),  (80, 175, 175), (210, 80, 80),
    (165, 160, 65),  (130, 100, 195),(70, 140, 80),
    (200, 120, 90),  (90, 130, 200), (170, 175, 75),
]  # Цвет поколения = GEN_COLORS[gen % len(GEN_COLORS)]


class SwarmAnalyticsOverlay:
    """
    Full-screen analytics overlay для анализа эволюции роя.

    Управление:
        A или Tab — открыть/закрыть
        ESC       — закрыть
        ←→        — переключить вкладки
        Колёсо    — скролл содержимого
    """

    def __init__(self) -> None:
        self._visible: bool = False
        self._active_tab: int = 0
        self._scroll: int = 0
        self._data: SwarmAnalytics | None = None
        self._panel_rect: Any = None
        self._tab_rects: list[Any] = []
        self._needs_rebuild: bool = True

    @property
    def visible(self) -> bool: ...

    def toggle(self) -> None:
        """Открыть/закрыть. При открытии помечает данные как устаревшие."""

    def close(self) -> None: ...

    def mark_dirty(self) -> None:
        """Пометить данные как требующие пересборки."""

    def refresh(self, runner: Any, observer: Any) -> None:
        """
        Пересобрать SwarmAnalytics из актуальных данных.
        Вызывать при открытии если _needs_rebuild == True.
        Блокирующий — занимает ~10-50ms.
        """

    def handle_event(self, event: Any) -> bool:
        """
        Обработать pygame событие.
        Возвращает True если поглощено.

        Поглощает:
        - ESC → close()
        - A/Tab → close()
        - ← → → переключить вкладку
        - MOUSEWHEEL → скролл
        - MOUSEBUTTONDOWN → клик по вкладке
        - Все события если visible (кроме QUIT)
        """

    def draw(
        self,
        screen: Any,
        font: Any,
        font_small: Any,
        font_mono: Any,
    ) -> None:
        """Нарисовать overlay поверх screen."""
```

---

## 5. Contents of the tabs

### 5.1 Tab 0: State

```
ТЕКУЩИЙ СРЕЗ КОЛОНИИ
sim_time: 01:42:07  |  живых: 47  (23♀ 24♂)  |  умерших за всё время: 312
Поколения: G0–G8   |  Средний возраст: 00:08:23  |  Спящих: 12 (26%)

── АФФЕКТИВНЫЙ СРЕЗ ─────────────────────────────────────────────────
[Итоговый аффективный тон роя: ХРОНИЧЕСКАЯ ТРЕВОГА]

стресс       █████████░  0.87  ±0.09   критический у 38 из 47
кортизол     ████████░░  0.76  ±0.13
энергия      ███████░░░  0.71  ±0.18
социал. драйв ████░░░░░  0.42  ±0.22
любопытство  ██░░░░░░░░  0.21  ±0.15

── НЕЙРОХИМИЯ ПОПУЛЯЦИИ ─────────────────────────────────────────────
дофамин      ██░░░░░░░░  0.18  ±0.22   87% агентов < 0.2
серотонин    ███░░░░░░░  0.24  ±0.19
норадреналин ██████░░░░  0.61  ±0.17
кортизол     ████████░░  0.76
ацетилхолин  ██████░░░░  0.64

── РЕСУРСЫ ──────────────────────────────────────────────────────────
корм   ████░░░░░░  0.42   сено  ████░░░░░░  0.38   вода  ████░░░░░░  0.41
```

**Implementation:** `_draw_tab_state()`

Only current data from `runner.agents` and `runner.resources` are shown.
For each metric: the mean ± the standard deviation, a mini-bar, and a textual comment when the value is critical.

---

### 5.2 Tab 1: Evolution

```
ЭВОЛЮЦИОННЫЕ ТРЕНДЫ ПО ПОКОЛЕНИЯМ
8 поколений  |  312 умерших агентов в базе  |  данные полные

── СТРЕСС И КОРТИЗОЛ ────────────────────────────────────────────────
поколение  G0    G1    G2    G3    G4    G5    G6    G7    G8(жив)
стресс    0.21  0.58  0.76  0.84  0.86  0.90  0.93  0.88  0.87
          [мини-бар каждого поколения, цветной по GEN_COLORS]
тренд: ↗ растёт  (Δ+0.66 за 8 поколений)
"Хронический стресс нарастал первые 6 поколений, сейчас стабилизировался."

кортизол  0.29  0.74  0.91  0.99  1.00  1.00  1.00  1.00  0.76
тренд: ↗ быстрый рост → стабилизация
"Кортизол достиг максимума в G3-G7 и начал снижаться в G8."

── ПРОДОЛЖИТЕЛЬНОСТЬ ЖИЗНИ ──────────────────────────────────────────
ср. прожито шагов:
          G0    G1    G2    G3    G4    G5    G6    G7
         1241  1997  4220 11646 17556 17127 17547 17544
тренд: ↗ быстрый рост → плато
"Стремительный рост от G0 к G4, затем стабилизация вблизи максимума."

── ЭНЕРГИЯ ПРИ СМЕРТИ ───────────────────────────────────────────────
          G0    G1    G2    G3    G4    G5    G6    G7
         0.58  0.11  0.11  0.17  0.20  0.19  0.21  0.21
тренд: ↔ стабильно на низком уровне
"Агенты умирают с израсходованной энергией — исчерпание ресурсов не критично."

── РЕПРОДУКЦИЯ ──────────────────────────────────────────────────────
среднее потомков на агента:
G0: 9.2  G1: 3.4  G2: 2.8  G3: 2.1  G4: 1.8  G5: 1.9  G6: 2.0  G7: 1.9
тренд: ↘ снижается (нормально: G0 был основатели с особым статусом)
```

**Implementation:** `_draw_tab_evolution()`

For each trend, a horizontal row of mini-bars (one per generation), coloured according to `GEN_COLORS`. Beneath the row: the `trend_label` and the interpretation taken from the analytics.

---

### 5.3 Tab 2: Genomes

```
ЭВОЛЮЦИЯ ГЕНОМА ПО ПОКОЛЕНИЯМ
20 отслеживаемых генов  |  под отбором: 7  |  стабильных: 13

── ГЕНЫ ПОД АКТИВНЫМ ОТБОРОМ ────────────────────────────────────────
● lt_max_lifespan_factor    ↗ растёт     Δ+0.24  (1.00 → 1.24)
  "Потенциальная продолжительность жизни растёт."
  G0 ░░░░░░░░░░ G3 ░░░░░░░░░░ G6 ██████░░░░ G8 ███████░░░

● af_decay_stress           ↘ снижается  Δ-0.08  (0.75 → 0.67)
  "Стресс рассеивается быстрее — позитивный тренд."
  G0 ████████░░ G3 ███████░░░ G6 ██████░░░░ G8 █████░░░░░

● nm_acc_k_cort             ↘ снижается  Δ-0.12  (0.92 → 0.80)
  "Кортизол-чувствительность снижается — адаптация к стрессу."
  [мини-бары по поколениям]

── СТАБИЛЬНЫЕ ГЕНЫ ──────────────────────────────────────────────────
~ wk_circadian_amplitude    ↔ стабильно  Δ±0.02
~ dr_perception_radius      ↔ стабильно  Δ±0.01
~ lr_gamma                  ↔ стабильно  Δ±0.03
[ещё 10 генов...]

── ГЕНЕТИЧЕСКОЕ РАЗНООБРАЗИЕ ────────────────────────────────────────
Текущий индекс: 0.31  (умеренное)
Самый однородный: nm_acc_k_cort    std=0.03
Самый разнородный: wk_recovery_factor  std=0.18
"Разнообразие достаточное для продолжения отбора."
```

**Implementation:** `_draw_tab_genomes()`

Genes under selection (`is_under_selection=True`) are emphasised, with mini-bars by generation.
Stable genes are shown as a compact list.

---

### 5.4 Tab 3: Behaviour

```
ПОВЕДЕНЧЕСКИЙ ПРОФИЛЬ КОЛОНИИ

── ТЕКУЩЕЕ РАСПРЕДЕЛЕНИЕ ДЕЙСТВИЙ ───────────────────────────────────
  eat       ████████░░░  18 (38%)
  sleep     ████░░░░░░░  9  (19%)
  explore   ███░░░░░░░░  7  (15%)
  hide      ██░░░░░░░░░  5  (11%)
  rest      █░░░░░░░░░░  4  ( 9%)
  socialize ░░░░░░░░░░░  2  ( 4%)
  другие    ░░░░░░░░░░░  2  ( 4%)

  "Доминирует питание и сон. Социальная активность подавлена."

── СОЦИАЛЬНАЯ СТРУКТУРА ─────────────────────────────────────────────
  Всего известных пар: 312
  Bonded:  48 (15%)   Rival:  12 ( 4%)
  Kin:     87 (28%)   Mate:   31 (10%)
  Без связей: 6 агентов (изолированы)
  Индекс сплочённости: 0.18  ↘ низкий

── ХАРАКТЕРЫ РОЯ ────────────────────────────────────────────────────
  ТРЕВОЖНЫЙ ОДИНОЧКА   ████████░░  17 агентов (36%)
  РЕСУРСНЫЙ ПРАГМАТИК  █████░░░░░  12 агентов (26%)
  ИССЛЕДОВАТЕЛЬ        ███░░░░░░░   8 агентов (17%)
  ПАССИВНЫЙ            ██░░░░░░░░   6 агентов (13%)
  СОЦИАЛЬНЫЙ АГЕНТ     ░░░░░░░░░░   4 агентов ( 8%)

  "Рой доминантно тревожный. Социальный тип в меньшинстве."

── ГИППОКАМП И КОРТЕКС ──────────────────────────────────────────────
  Средний размер гиппокампа:   423 эпизода  (±187)
  Средний размер кортекса:      89 паттернов (±54)
  Консолидация: 89/423 = 21%

  Топ-3 доминирующих привычки роя:
  ● eat ← food_low         встречается у 31 из 47 (66%)
  ● hide ← high_stress     встречается у 28 из 47 (60%)
  ● sleep ← wakefulness    встречается у 24 из 47 (51%)
```

**Implementation:** `_draw_tab_behavior()`

The action distribution is drawn as horizontal bars with percentages.
Characters are taken from `nowa_interpretation.personality` of each living agent.
Dominant habits of the swarm are an aggregation of `cortex_patterns_detail` over all agents: the top-N patterns by frequency of occurrence.

---

### 5.5 Tab 4: Prognosis

```
ЭВОЛЮЦИОННЫЙ ПРОГНОЗ

── ИНДЕКС ЗДОРОВЬЯ КОЛОНИИ ──────────────────────────────────────────
  [████████░░]  0.61  КОЛОНИЯ СТАБИЛЬНА С УМЕРЕННЫМИ РИСКАМИ

  Компоненты:
  стресс       [████░░░░░░]  0.13  (инвертирован: 1-0.87)
  кортизол     [████░░░░░░]  0.24
  энергия      [████████░░]  0.71
  социальность [██░░░░░░░░]  0.18
  долголетие   [████████░░]  0.78
  разнообразие [████████░░]  0.31 (нормировано)

── РИСКИ ─────────────────────────────────────────────────────────────
  ✗ Хронический кортизол блокирует репродукцию
  ✗ Слабая социальная сплочённость — изоляция особей
  ~ Стресс стабилизировался на высоком уровне

── ПОЗИТИВНЫЕ ТРЕНДЫ ────────────────────────────────────────────────
  ✓ Ген долголетия под положительным отбором
  ✓ Кортизол снижается — адаптация к стрессу работает
  ✓ Стресс начал снижаться в последних поколениях

── ДАВЛЕНИЕ ОТБОРА ──────────────────────────────────────────────────
  Главный фактор: хронический стресс
  Адаптируется: af_decay_stress, nm_acc_k_cort, lt_max_lifespan_factor
  Без отбора: wk_circadian_amplitude, lr_tonic_slow_rate

── ИТОГОВЫЙ ВЫВОД ───────────────────────────────────────────────────
  "Колония прошла острый кризис G0-G3 и стабилизировалась.
   Ключевые гены стрессоустойчивости под положительным отбором.
   Главный риск: кортизол ещё высок, подавляет репродукцию.
   При сохранении текущих трендов через 3-5 поколений возможна
   стабилизация с низким стрессом."
```

**Implementation:** `_draw_tab_forecast()`

`ColonyHealthIndex` is a widget with a large bar and its components.
Risks are shown in red with the mark ✗; opportunities in green with the mark ✓.
The concluding statement is wrapped text of four to five lines.

---

## 6. Integration

### 6.1 ColonyGUI

```python
class ColonyGUI:
    def __init__(self, runner: Any) -> None:
        ...
        self.swarm_analytics = SwarmAnalyticsOverlay()   # НОВОЕ

    def close_all_overlays(self) -> None:
        self.inspector.close()
        self.lineage.close()
        self.swarm_analytics.close()                     # НОВОЕ

    def _sim_tick(self, real_dt: float) -> None:
        ...
        # При рождениях/смертях пометить аналитику устаревшей
        # (вызывать из обработчика событий runner)
```

### 6.2 app.py — key and overlay

```python
# В handle_event():
elif event.key == pygame.K_a:
    if gui.inspector.visible or gui.lineage.visible:
        gui.close_all_overlays()
    gui.swarm_analytics.toggle()
    if gui.swarm_analytics.visible and gui.swarm_analytics._needs_rebuild:
        gui.swarm_analytics.refresh(runner, getattr(runner, "_observer", None))

# После отрисовки правой панели:
if gui.swarm_analytics.visible:
    gui.swarm_analytics.draw(screen, font, font_small, font_mono)
```

### 6.3 Update on events

```python
# В главном цикле app.py, после проверки рождений/смертей:
if current_births != lineage_births_seen or current_deaths != lineage_deaths_seen:
    gui.lineage.mark_dirty()
    gui.swarm_analytics.mark_dirty()    # ДОБАВИТЬ
```

---

## 7. Implementation constraints

1. `swarm_analytics.py` uses no pygame; only the standard library.
2. `build_swarm_analytics()` blocks the caller for about 10–50 ms, which is acceptable when the overlay is opened.
3. Data are not updated in real time: a snapshot is taken at opening. The key R requests a manual refresh.
4. At least two generations must be present in the DeathRegistry before evolutionary trends are displayed. With fewer generations, a placeholder is shown.
5. If `ColonyPopulationObserver` is unavailable, the observer trends are empty and those sections are hidden.
6. Generation mini-bars occupy at most 12 columns on screen. With a larger number of generations, every N-th generation is shown.
7. `SwarmAnalyticsOverlay` and `LineageOverlay` may be open simultaneously; they do not exclude one another.
8. `AgentInspectorOverlay` is closed when `SwarmAnalyticsOverlay` is opened (the two overlays analyse at different scales).
9. Scrolling is the mouse wheel while the overlay is visible.
10. Python 3.10+.

---

## 8. Test cases

### TC-01: build_swarm_analytics does not fail on an empty runner

```python
runner = SimulationRunner()
analytics = build_swarm_analytics(runner, observer=None)

assert analytics is not None
assert analytics.living_count == 0
assert analytics.generation_summaries == []
assert analytics.gene_tracks == []
assert analytics.forecast.extinction_risk >= 0.0
```

### TC-02: GenerationSummary from memorials

```python
registry = DeathRegistry()
for gen in [0, 0, 1, 1, 1]:
    a = ChinchillaAgent(sex="F", generation=gen)
    a.genome = GenomeVector.default()
    registry.register_birth(a, 0.0)
    registry.register_death(a, 1000.0, {})

runner = SimulationRunner()
runner.death_registry = registry
analytics = build_swarm_analytics(runner, None)

assert len(analytics.generation_summaries) == 2
g0 = next(s for s in analytics.generation_summaries if s.generation == 0)
g1 = next(s for s in analytics.generation_summaries if s.generation == 1)
assert g0.dead_count == 2
assert g1.dead_count == 3
```

### TC-03: GeneEvolutionTrack — the trend rises

```python
summaries = [
    GenerationSummary(generation=i, mean_genome={"lt_max_lifespan_factor": 1.0 + i * 0.05}, ...)
    for i in range(5)
]
tracks = build_gene_tracks(summaries)
lt_track = next(t for t in tracks if t.gene_key == "lt_max_lifespan_factor")

assert lt_track.trend_label == "↗ растёт"
assert lt_track.is_under_selection is True
assert lt_track.trend_magnitude > 0.05
```

### TC-04: GeneEvolutionTrack — a stable gene

```python
summaries = [
    GenerationSummary(generation=i, mean_genome={"lr_gamma": 0.85 + (i % 2) * 0.01}, ...)
    for i in range(6)
]
tracks = build_gene_tracks(summaries)
lr_track = next((t for t in tracks if t.gene_key == "lr_gamma"), None)

if lr_track:
    assert lr_track.trend_label == "↔ стабильно"
    assert lr_track.is_under_selection is False
```

### TC-05: ColonyHealthIndex — a normal colony

```python
runner = SimulationRunner()
for i in range(10):
    a = ChinchillaAgent(sex="F" if i%2==0 else "M")
    a.affective_space.axes["stress"] = 0.2
    runner.add_agent(a)
runner.resources.food_pellets = 0.8

analytics = build_swarm_analytics(runner, None)
assert analytics.health_index.overall > 0.50
```

### TC-06: ColonyHealthIndex — a colony in crisis

```python
runner = SimulationRunner()
a = ChinchillaAgent(sex="F")
a.affective_space.axes["stress"] = 0.95
runner.add_agent(a)

analytics = build_swarm_analytics(runner, None)
assert analytics.health_index.overall < 0.50
assert analytics.health_index.color[0] > 150  # красноватый
```

### TC-07: BehaviorPattern from living agents

```python
runner = SimulationRunner()
actions = ["eat", "eat", "sleep", "hide", "eat", "explore"]
for i, action in enumerate(actions):
    a = ChinchillaAgent(sex="F" if i%2==0 else "M")
    a.current_action = action
    runner.add_agent(a)

analytics = build_swarm_analytics(runner, None)
eat_pattern = next(p for p in analytics.current_action_distribution if p.action == "eat")

assert eat_pattern.count == 3
assert abs(eat_pattern.fraction - 0.5) < 0.01
```

### TC-08: Forecast risks — cortisol risk

```python
runner = SimulationRunner()
for i in range(5):
    a = ChinchillaAgent(sex="F" if i%2==0 else "M")
    a.neuromodulators.cortisol = 0.90
    runner.add_agent(a)

analytics = build_swarm_analytics(runner, None)
risk_texts = " ".join(analytics.forecast.key_risks).lower()
assert "кортизол" in risk_texts or "репродукц" in risk_texts
```

### TC-09: Observer trends are integrated

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
observer = ColonyPopulationObserver(runner, observe_every_n_ticks=1)
for _ in range(10):
    runner.tick(0.1)
    observer.observe_tick()

analytics = build_swarm_analytics(runner, observer)
assert len(analytics.observer_stress_trend) > 0
assert len(analytics.observer_population_trend) > 0
```

### TC-10: SwarmAnalyticsOverlay opens and closes

```python
overlay = SwarmAnalyticsOverlay()
assert not overlay.visible
overlay.toggle()
assert overlay.visible
overlay.toggle()
assert not overlay.visible
```

### TC-11: SwarmAnalyticsOverlay.handle_event — ESC closes the overlay

```python
import pygame
pygame.init()

overlay = SwarmAnalyticsOverlay()
overlay._visible = True
esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""})
consumed = overlay.handle_event(esc)

assert consumed is True
assert not overlay.visible
```

### TC-12: SocialStructure — isolated agents

```python
runner = SimulationRunner()
for i in range(5):
    runner.add_agent(ChinchillaAgent(sex="F" if i%2==0 else "M"))
# Агенты без knowledge = без связей

analytics = build_swarm_analytics(runner, None)
assert analytics.current_social.isolation_count == 5
assert analytics.current_social.total_known_pairs == 0
```

### TC-13: Mini-bars — at most twelve generations on screen

```python
# При 20 поколениях показываем каждое второе
summaries = [GenerationSummary(generation=i, ...) for i in range(20)]
analytics = SwarmAnalyticsOverlay()
analytics._data = SwarmAnalytics(generation_summaries=summaries, ...)

# Внутренний метод должен возвращать не более 12 точек
display_points = analytics._select_display_generations(summaries)
assert len(display_points) <= 12
```

### TC-14: Forecast summary — non-empty text

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))

analytics = build_swarm_analytics(runner, None)
assert len(analytics.forecast.summary) > 20
assert isinstance(analytics.forecast.summary, str)
```

### TC-15: The A key in the application opens the overlay and closes the inspector

```python
# Интеграционный тест
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
gui = ColonyGUI(runner)
gui.open_inspector(runner.agents[0].agent_id)
assert gui.inspector.visible

# Симулируем нажатие A
gui.inspector.close()
gui.swarm_analytics.toggle()

assert gui.swarm_analytics.visible
assert not gui.inspector.visible
```

---

## 9. Notes for the implementing agent

- `swarm_analytics.py` is an independent module. It imports from `death_registry` and `genome_portrait` (for `GENE_REGISTRY` and the interpretations) and from `nowa_interpreter` (for agent characters). It does not import pygame.
- Call `build_swarm_analytics()` only when the overlay is opened, not on every tick.
- A generation mini-bar has width `(OVERLAY_WIDTH - margins) / max(1, n_generations)`, height 10 px, and colour `GEN_COLORS[gen % len(GEN_COLORS)]`.
- `_select_display_generations()`: if there are more than 12 generations, take every `ceil(n/12)`-th generation, and always include the first and the last.
- Swarm characters (Behaviour tab): for each living agent, take `agent.nowa_interpretation.personality.character_label` when it is available; otherwise compute it through `build_personality_readout()`.
- Dominant habits of the swarm: unite `cortex_patterns_detail` of all agents, group by `action`, and count in how many agents each action occurs.
- Observer trends: use `observer.get_trend("mean_stress", last_n=50)` and the analogous methods. If `observer` is `None`, the lists are empty.
- Call `mark_dirty()` on every birth and every death from the main loop of `app.py`.
- The key A is chosen so that it does not conflict with the existing bindings (SPACE, +/-, M, L, ESC).
- `refresh()` is a synchronous call before the first draw after `toggle`. Display `Загрузка...` for the duration of the call (at 50 agents the call is instantaneous).
