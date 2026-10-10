## Аннотация

English version: [SPEC_SwarmAnalyticsOverlay.en.md](SPEC_SwarmAnalyticsOverlay.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Настоящий документ задаёт спецификацию подсистемы аналитического наблюдения за роем в графическом контуре колонии шиншилл. Предметом являются оверлей `SwarmAnalyticsOverlay` и модуль агрегации `swarm_analytics`, которые читают текущий срез живых агентов, реестр умерших с полными геномами и временные ряды `ColonyPopulationObserver`. Подсистема описывает колонию как единый эволюционирующий организм и фиксирует вопросы о межпоколенческих сдвигах, текущем состоянии роя, направленности отбора генов, поведенческих паттернах и движении к устойчивости либо к вымиранию.

Оверлей разделён на пять вкладок: состояние, эволюция, геномы, поведение и прогноз. Модуль данных определяет агрегаты поколения, эволюционные треки отдельных генов с оценкой направленного сдвига, частотные профили действий и показатели социальной структуры, включая связи родства, соперничества и случаи изоляции. Сбор выполняется при открытии оверлея, а не на каждом такте симуляции; сбой одной секции не прекращает разбор остальных.

В многоагентной установке NOWA спецификация закрепляет протокол наблюдения, отделённый от контура выбора действия. Оверлей не изменяет данные агентов. Тем самым документ задаёт условия, при которых демографические, аффективные, генетические и социальные процессы колонии могут быть сопоставлены продольно, без обратного влияния измерения на симулируемых особей.

# Спецификация: SwarmAnalyticsOverlay

**Файлы:**
- `colony_gui/swarm_analytics.py` — новый модуль аналитики (без pygame)
- `colony_gui/swarm_analytics_overlay.py` — overlay с вкладками (pygame)
- изменения в `colony_gui/colony_gui.py` — интеграция
- изменения в `colony_gui/app.py` — клавиша и отрисовка

**Версия:** 1.0

---

## 1. Концепция

`SwarmAnalyticsOverlay` — аналитический инструмент для понимания эволюции колонии
как единого организма. Отвечает на вопросы:

- Что изменилось от поколения к поколению и почему?
- Какое текущее состояние роя — здоров ли он?
- Какие гены отбираются, какие нейтральны?
- Есть ли паттерны поведения на уровне всей колонии?
- Куда движется рой — к стабильности или к вымиранию?

**Источники данных:**
- `runner.agents` — живые агенты (текущий срез)
- `runner.death_registry` — все умершие агенты с полными геномами
- `runner.observer` / `ColonyPopulationObserver` — временные тренды снапшотов

**Принципы:**
- Read-only: overlay не мутирует никакие данные
- Lazy: данные собираются при открытии overlay, не на каждом тике
- Tolerant: любая ошибка в одной секции не роняет остальные

---

## 2. Вкладки overlay

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

**5 вкладок:**

| # | Название | Содержание |
|---|---|---|
| 0 | Состояние | Текущий срез: демография, аффект, нейромодуляторы, ресурсы |
| 1 | Эволюция | Тренды по поколениям: стресс, кортизол, долголетие, энергия |
| 2 | Геномы | Отбор генов: что сдвинулось, что стабильно, что разошлось |
| 3 | Поведение | Паттерны действий, социальная структура, характеры роя |
| 4 | Прогноз | Риски, тренды, интерпретация куда движется рой |

---

## 3. swarm_analytics.py — модуль данных

### 3.1 Структуры данных

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

### 3.2 Построение GenerationSummary

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

### 3.3 Построение GeneEvolutionTrack

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

### 3.4 Интерпретации эволюции генов

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

### 3.5 Индекс здоровья колонии

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

### 3.6 Эволюционный прогноз

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

### 3.7 Главная функция

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

## 5. Содержимое вкладок

### 5.1 Вкладка 0: Состояние

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

**Реализация:** `_draw_tab_state()`

Показывает только текущие данные из `runner.agents` и `runner.resources`.
Для каждой метрики: среднее ± std + мини-бар + текстовый комментарий если критично.

---

### 5.2 Вкладка 1: Эволюция

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

**Реализация:** `_draw_tab_evolution()`

Для каждого тренда — горизонтальный ряд мини-баров (один на поколение),
цветных по `GEN_COLORS`. Под рядом — trend_label + interpretation из analytics.

---

### 5.3 Вкладка 2: Геномы

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

**Реализация:** `_draw_tab_genomes()`

Гены под отбором (`is_under_selection=True`) — выделены, с мини-барами по поколениям.
Стабильные — компактным списком.

---

### 5.4 Вкладка 3: Поведение

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

**Реализация:** `_draw_tab_behavior()`

Распределение действий — горизонтальные бары с процентами.
Характеры — из `nowa_interpretation.personality` каждого живого агента.
Доминирующие привычки роя — агрегация `cortex_patterns_detail` всех агентов,
топ-N паттернов по частоте встречаемости.

---

### 5.5 Вкладка 4: Прогноз

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

**Реализация:** `_draw_tab_forecast()`

`ColonyHealthIndex` — виджет с большим баром и компонентами.
Риски — красным ✗, возможности — зелёным ✓.
Итоговый вывод — wrapped text, 4-5 строк.

---

## 6. Интеграция

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

### 6.2 app.py — клавиша и overlay

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

### 6.3 Обновление при событиях

```python
# В главном цикле app.py, после проверки рождений/смертей:
if current_births != lineage_births_seen or current_deaths != lineage_deaths_seen:
    gui.lineage.mark_dirty()
    gui.swarm_analytics.mark_dirty()    # ДОБАВИТЬ
```

---

## 7. Ограничения реализации

1. `swarm_analytics.py` — без pygame, только стандартная библиотека.
2. `build_swarm_analytics()` блокирует вызов ~10-50ms — приемлемо при открытии overlay.
3. Данные не обновляются в реальном времени — snapshot при открытии. Кнопка R для ручного обновления.
4. Минимум 2 поколения в DeathRegistry для отображения эволюционных трендов. При меньшем — показать заглушку.
5. Если ColonyPopulationObserver недоступен — тренды из observer пустые, секции скрыты.
6. Мини-бары поколений — максимум 12 колонок на экране. При большем числе поколений — показывать каждое N-е.
7. `SwarmAnalyticsOverlay` и `LineageOverlay` могут быть открыты одновременно — они не исключают друг друга.
8. `AgentInspectorOverlay` закрывается при открытии `SwarmAnalyticsOverlay` (разные масштабы анализа).
9. Скролл — колёсико мыши когда overlay видим.
10. Python 3.10+.

---

## 8. Тест-кейсы

### TC-01: build_swarm_analytics не падает на пустом runner

```python
runner = SimulationRunner()
analytics = build_swarm_analytics(runner, observer=None)

assert analytics is not None
assert analytics.living_count == 0
assert analytics.generation_summaries == []
assert analytics.gene_tracks == []
assert analytics.forecast.extinction_risk >= 0.0
```

### TC-02: GenerationSummary из мемориалов

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

### TC-03: GeneEvolutionTrack — тренд растёт

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

### TC-04: GeneEvolutionTrack — стабильный ген

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

### TC-05: ColonyHealthIndex — нормальная колония

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

### TC-06: ColonyHealthIndex — кризисная колония

```python
runner = SimulationRunner()
a = ChinchillaAgent(sex="F")
a.affective_space.axes["stress"] = 0.95
runner.add_agent(a)

analytics = build_swarm_analytics(runner, None)
assert analytics.health_index.overall < 0.50
assert analytics.health_index.color[0] > 150  # красноватый
```

### TC-07: BehaviorPattern из живых агентов

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

### TC-08: Forecast risks — кортизольный риск

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

### TC-09: Observer trends интегрируются

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

### TC-10: SwarmAnalyticsOverlay открывается и закрывается

```python
overlay = SwarmAnalyticsOverlay()
assert not overlay.visible
overlay.toggle()
assert overlay.visible
overlay.toggle()
assert not overlay.visible
```

### TC-11: SwarmAnalyticsOverlay.handle_event — ESC закрывает

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

### TC-12: SocialStructure — изолированные агенты

```python
runner = SimulationRunner()
for i in range(5):
    runner.add_agent(ChinchillaAgent(sex="F" if i%2==0 else "M"))
# Агенты без knowledge = без связей

analytics = build_swarm_analytics(runner, None)
assert analytics.current_social.isolation_count == 5
assert analytics.current_social.total_known_pairs == 0
```

### TC-13: Мини-бары — максимум 12 поколений на экране

```python
# При 20 поколениях показываем каждое второе
summaries = [GenerationSummary(generation=i, ...) for i in range(20)]
analytics = SwarmAnalyticsOverlay()
analytics._data = SwarmAnalytics(generation_summaries=summaries, ...)

# Внутренний метод должен возвращать не более 12 точек
display_points = analytics._select_display_generations(summaries)
assert len(display_points) <= 12
```

### TC-14: Forecast summary — непустой текст

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))

analytics = build_swarm_analytics(runner, None)
assert len(analytics.forecast.summary) > 20
assert isinstance(analytics.forecast.summary, str)
```

### TC-15: Клавиша A в app — открывает overlay, закрывает inspector

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

## 9. Примечания для реализующего агента

- `swarm_analytics.py` — независимый модуль. Импортирует из `death_registry`, `genome_portrait` (для GENE_REGISTRY и интерпретаций), `nowa_interpreter` (для характеров агентов). Не импортирует pygame.
- `build_swarm_analytics()` вызывать только при открытии overlay, не на каждом тике.
- Мини-бар поколения: ширина = `(OVERLAY_WIDTH - margins) / max(1, n_generations)`, высота 10px, цвет из `GEN_COLORS[gen % len(GEN_COLORS)]`.
- `_select_display_generations()` — если поколений > 12, брать каждое `ceil(n/12)`-е плюс всегда первое и последнее.
- Характеры роя (вкладка Поведение): для каждого живого агента взять `agent.nowa_interpretation.personality.character_label` если доступен, иначе вычислить через `build_personality_readout()`.
- Доминирующие привычки роя: объединить `cortex_patterns_detail` всех агентов, сгруппировать по `action`, посчитать в скольких агентах встречается каждое действие.
- Observer trends: использовать `observer.get_trend("mean_stress", last_n=50)` и аналогичные методы. Если observer=None — пустые списки.
- `mark_dirty()` вызывать при каждом рождении/смерти из главного цикла app.py.
- Клавиша A выбрана чтобы не конфликтовать с существующими (SPACE, +/-, M, L, ESC).
- `refresh()` — синхронный вызов перед первой отрисовкой после toggle. Показать "Загрузка..." на время выполнения (хотя при 50 агентах это мгновенно).
