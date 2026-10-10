# NOWA × Warriner Validation Demo — Техническая спецификация

English version: [NOWA_Warriner_Validation_Spec.en.md](NOWA_Warriner_Validation_Spec.en.md)


**Статус.** Нормативная спецификация. Научное описание установки: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md).

Документ задаёт исходную техническую спецификацию лексической валидации. Стимул проводится через предварительную инициализацию `NOWAHippocampus` аффективно окрашенными эпизодами корпуса Warriner et al. (2013); целевой контур сохраняет путь гиппокамп — корковое давление — базальные ганглии — аффективное пространство. Мера связи — ранговая корреляция Спирмена между средним сдвигом валентности колонии и оценками `V.Mean.Sum`.

Специфицированы модули `hippocampus_seeder.py`, `word_stimulus_encoder.py` (режимы `lexical`, `sbert_neighbors`, `direct_vad`), `nowa_colony.py`, `warriner_validator.py`, интерфейс Streamlit и CLI. Зафиксированы пороги интерпретации ρ, требование непересечения seed- и тестового корпусов, порядок реализации и перечень проверок перед публикацией результатов.

---

**Версия:** 1.0  
**Статус:** Готово к реализации  
**Цель:** Получить Spearman ρ между средним валентным сдвигом колонии NOWA и человеческими оценками `V.Mean.Sum` из Warriner et al. (2013)

---

## 1. Концептуальная модель

### Ключевое архитектурное решение

**Использовать NOWAHippocampus с предварительной инициализацией эпизодической памяти**, а не обходить гиппокамп через прямую инъекцию в AffectiveSpace.

**Обоснование:**
- Биологически правдоподобно: слово-стимул активирует ассоциативную память, которая уже содержит эмоциональные следы
- Не нарушает архитектурные инварианты NOWA (pipeline hippocampus → cortical pressure → BG → affective space остаётся нетронутым)
- Если подать `["happy"]` в пустой гиппокамп — активации не будет, ρ ≈ 0. Решение: заполнить гиппокамп аффективно-окрашенными эпизодами до запуска стимула

### Механизм работы

```
Warriner CSV (13 915 слов с V/A/D)
    ↓ sample_words(n=300, stratified)
    ↓
[ИНИЦИАЛИЗАЦИЯ] HippocampusSeeder
    ├── Warriner → seed_experiences (аффективно окрашенные эпизоды)
    ├── Каждый агент получает N_SEED эпизодов из Warriner
    └── Эпизоды покрывают весь диапазон V/A/D (low/mid/high)
    ↓
WordStimulusEncoder
    ├── word → context_events: List[str]  (формат NOWA)
    ├── Режим A: ["word:happy", "valence:positive", "arousal:high"]
    └── Режим B: sentence-BERT → nearest Warriner neighbors → токены
    ↓
NOWAColony.run_stimulus(context_events)
    ├── hippocampus.activate(context_events) → active_experiences
    ├── selector.compute_pressures(active_experiences, ...) → pressure_vector
    ├── agent.step(context_events) × N_TICKS
    └── measure: affective_space.axes delta
    ↓
SpearmanCorrelation(nowa_valence_shifts, warriner_V)
    ↓
ValidationReport + Streamlit Dashboard
```

---

## 2. Пороговые значения и критерии успеха

| ρ (Spearman, valence) | Интерпретация | Действие |
|---|---|---|
| ≥ 0.6 | Сильный сигнал | Двигаться к EmoBank |
| 0.4–0.6 | Признак жизнеспособности | Оптимизировать encoder |
| 0.2–0.4 | Слабый сигнал | Проверить seed-стратегию |
| < 0.2 | Нет сигнала | Пересмотреть context_event формат |

---

## 3. Новые модули (файлы к созданию)

```
nowa_validation/
├── hippocampus_seeder.py      # Инициализация памяти из Warriner
├── word_stimulus_encoder.py   # word → context_events: List[str]
├── nowa_colony.py             # Управление колонией + прогон стимула
├── warriner_validator.py      # Оркестратор + корреляции
├── demo_app.py                # Streamlit UI
├── run_quick.py               # CLI запуск без UI
├── data/
│   └── Ratings_Warriner_et_al.csv   # скачать с XANEW
└── requirements.txt
```

---

## 4. Модуль `hippocampus_seeder.py`

### Назначение

Заполняет `NOWAHippocampus` каждого агента аффективно-окрашенными эпизодами перед запуском стимула. Это «долгосрочная семантическая память» агента о том, что слова могут значить эмоционально.

### Структура seed-эпизода

Каждый seed-эпизод — это `Experience` в гиппокампе, созданный из Warriner-строки:

```
word: "happy"
V.Mean.Sum: 8.21  →  valence: +0.821 (normalized)
A.Mean.Sum: 6.11  →  arousal: 0.639
D.Mean.Sum: 7.34  →  dominance: 0.793

→ Path с событиями:
  Event("word:happy",        EventType.CONTEXT)
  Event("valence:positive",  EventType.CONTEXT)
  Event("arousal:high",      EventType.CONTEXT)
  Event("dominance:high",    EventType.CONTEXT)

→ consequence: Event("affect_positive", EventType.CONSEQUENCE)
→ intensity: abs(valence) = 0.821
→ reward: valence = +0.821
```

### Стратегия покрытия

Seed-корпус должен покрывать весь диапазон валентности равномерно, иначе гиппокамп будет смещён:

```
N_SEED_PER_AGENT = 500  # минимум для значимой активации
Стратификация:
  - 100 слов из нижнего квартиля V (negative: "murder", "cancer", "torture")
  - 300 слов из среднего диапазона V (neutral/mixed)
  - 100 слов из верхнего квартиля V (positive: "happy", "love", "victory")
```

### Интерфейс

```python
class HippocampusSeeder:
    def __init__(
        self,
        warriner_df: pd.DataFrame,
        n_seed: int = 500,
        seed_strategy: Literal['stratified', 'random', 'full'] = 'stratified',
        rng: random.Random = None,
    )

    def build_seed_corpus(self) -> List[dict]:
        """
        Возвращает список seed-записей.
        Каждая запись: {'word': str, 'v': float, 'a': float, 'd': float}
        Нормализованные значения: v ∈ [-1,+1], a ∈ [0,1], d ∈ [0,1]
        """

    def seed_agent(self, agent: Any) -> int:
        """
        Заполняет hippocampus агента seed-эпизодами.
        Возвращает количество добавленных эпизодов.
        
        Для каждого seed-слова:
        1. Создать Path с context_events (см. формат ниже)
        2. Создать consequence Event на основе valence знака
        3. Вызвать hippocampus.store(path, consequence, intensity, reward)
        4. Если слово часто встречается (|v| > 0.7): вызвать hippocampus.reinforce()
        """

    def seed_colony(self, agents: List[Any]) -> Dict[str, int]:
        """
        Заполняет всю колонию. Каждый агент получает одинаковый корпус
        (но с разным порядком — для разнообразия активации).
        Возвращает {agent_id: n_episodes_added}
        """
```

### Формат context_events для seed-эпизода

```python
def _word_to_events(word: str, v: float, a: float, d: float) -> List[str]:
    """
    Конвертирует слово + VAD в список event-токенов для Path.
    
    Обязательные токены:
    - f"word:{word}"                    # лексическая идентичность
    
    Валентностные токены (по порогам):
    - "valence:very_positive"  if v > 0.6
    - "valence:positive"       if 0.2 < v <= 0.6
    - "valence:neutral"        if -0.2 <= v <= 0.2
    - "valence:negative"       if -0.6 <= v < -0.2
    - "valence:very_negative"  if v < -0.6
    
    Активационные токены:
    - "arousal:high"           if a > 0.6
    - "arousal:medium"         if 0.4 <= a <= 0.6
    - "arousal:low"            if a < 0.4
    
    Доминантностные токены:
    - "dominance:high"         if d > 0.6
    - "dominance:low"          if d < 0.4
    
    Категориальные (NRC-style, опционально если nrclex доступен):
    - "emotion:joy", "emotion:fear", etc.
    """
```

### Параметры интенсивности и reward

```python
intensity = abs(v)                    # [0, 1] — насколько «сильный» эпизод
reward = v                            # [-1, +1] — валентность напрямую
encoding_strength = abs(v) * 0.8 + 0.2  # минимум 0.2 чтобы войти в память

# Consequence Event:
if v > 0.1:
    consequence = Event("positive_valence_outcome", EventType.CONSEQUENCE)
elif v < -0.1:
    consequence = Event("negative_valence_outcome", EventType.CONSEQUENCE)
else:
    consequence = Event("neutral_outcome", EventType.CONSEQUENCE)

# Reinforcement для сильных эпизодов:
if abs(v) > 0.7:
    hippocampus.reinforce(path, consequence, intensity=intensity)
    # дополнительное усиление — слово "murder" или "love" должны 
    # оставить более глубокий след
```

---

## 5. Модуль `word_stimulus_encoder.py`

### Назначение

Конвертирует тестовое слово (из Warriner) в `context_events: List[str]` — именно тот формат, который принимает `agent.step()` и `hippocampus.activate()`.

**Критически важно:** тестовые слова НЕ должны содержать валентностные токены ("valence:positive") — иначе мы тривиально активируем правильные эпизоды и получим артефактную корреляцию. Тестовый вход должен быть только лексическим.

### Три режима

#### Режим A: `lexical` (рекомендуемый базовый)

```python
def encode_lexical(word: str) -> List[str]:
    """
    Только лексические токены — никакой валентностной информации.
    Это честный тест: знает ли агент, что "happy" — позитивное слово,
    только по факту наличия "word:happy" в памяти.
    
    Возвращает:
    - [f"word:{word}"]
    
    Опционально, если nrclex доступен (не раскрывает VAD):
    - добавить дискретные эмоции из NRC как дополнительные токены
    - [f"word:{word}", "emotion:joy", "emotion:trust"]
    """
```

#### Режим B: `sbert_neighbors` (рекомендуемый продвинутый)

```python
def encode_sbert_neighbors(word: str, warriner_df: pd.DataFrame, k: int = 5) -> List[str]:
    """
    1. Получить SBERT-embedding слова
    2. Найти K ближайших соседей в Warriner по cosine similarity
       (из seed-корпуса, который уже загружен в гиппокамп)
    3. Добавить их как co-activation токены
    
    Возвращает:
    - [f"word:{word}", f"word:{neighbor1}", f"word:{neighbor2}", ...]
    
    Логика: если "happy" семантически близко к "joyful" и "cheerful",
    и те слова уже есть в памяти агента — они помогут активировать
    правильные аффективные следы.
    
    ВАЖНО: соседей искать только по лексическому смыслу (SBERT),
    а НЕ по валентности — иначе cheating.
    """
```

#### Режим C: `direct_vad` (только для baseline/отладки)

```python
def encode_direct_vad(word: str, warriner_row: dict) -> List[str]:
    """
    ТОЛЬКО для сравнения — раскрывает VAD агенту.
    Если этот режим даёт высокое ρ, а 'lexical' — низкое,
    проблема в семантическом покрытии seed-корпуса.
    
    НЕ использовать для реальной валидации.
    """
```

### Интерфейс

```python
class WordStimulusEncoder:
    def __init__(
        self,
        mode: Literal['lexical', 'sbert_neighbors', 'direct_vad'] = 'lexical',
        warriner_df: Optional[pd.DataFrame] = None,
        sbert_model=None,
        k_neighbors: int = 5,
    )

    def encode(
        self,
        word: str,
        warriner_row: Optional[dict] = None,
    ) -> List[str]:
        """Main entry point. Returns context_events: List[str]"""

    def encode_batch(
        self,
        words: List[str],
        warriner_rows: Optional[List[dict]] = None,
    ) -> List[List[str]]:
        """Batch encoding for efficiency."""
```

---

## 6. Модуль `nowa_colony.py`

### Назначение

Управляет N агентами NOWA, запускает стимул через каждого, агрегирует результаты.

### Классы данных

```python
@dataclass
class AgentResponse:
    agent_id: str
    archetype: str              # "explorer" | "passive" | "resource_pragmatist" | "anxious_loner"
    valence_before: float       # pleasure - pain перед стимулом
    valence_after: float        # pleasure - pain после N тиков
    valence_shift: float        # after - before
    arousal_shift: float
    da_delta: float             # dopamine delta
    ne_delta: float             # norepinephrine delta
    cortisol_delta: float
    serotonin_delta: float
    n_activated_memories: int   # сколько эпизодов активировал стимул
    stimulus_word: str
    raw_axes_before: dict
    raw_axes_after: dict


@dataclass
class ColonyResponse:
    word: str
    n_agents: int
    mean_valence_shift: float
    std_valence_shift: float    # ВАЖНО: проверять на collapse (SD << SD_human)
    mean_arousal_shift: float
    mean_da_delta: float
    mean_ne_delta: float
    mean_cortisol_delta: float
    mean_n_activated_memories: float
    per_archetype: Dict[str, float]     # archetype → mean valence shift
    agent_responses: List[AgentResponse]
    processing_time_s: float
```

### Инициализация агентов

```python
class NOWAColony:
    def __init__(
        self,
        n_agents: int = 100,
        ticks_per_stimulus: int = 10,
        seed: int = 42,
    )

    def initialize(
        self,
        warriner_df: pd.DataFrame,
        n_seed: int = 500,
        agent_factory=None,
    ) -> None:
        """
        1. Создать N агентов (через AgentFactory если доступен, иначе напрямую)
        2. Применить геномные параметры (GenomeVector.random() для каждого)
        3. Присвоить архетипы на основе геномных параметров
        4. Запустить HippocampusSeeder для каждого агента
        5. Зафиксировать baseline состояние (affective_space.axes snapshot)
        
        После initialize() агенты готовы к run_stimulus().
        """
```

### Присвоение архетипов

Архетип определяется по двум геномным параметрам агента:

```
Ось X: nm_acc_k_cort (чувствительность к кортизолу: 0.3..1.2)
Ось Y: dr_curiosity_baseline (базовый уровень любопытства: 0.05..0.40)

Квадранты:
  low_cort  + high_curiosity  → "explorer"
  low_cort  + low_curiosity   → "passive"
  high_cort + high_curiosity  → "resource_pragmatist"
  high_cort + low_curiosity   → "anxious_loner"

Порог: медиана распределения по колонии (не фиксированная константа)
```

### Запуск стимула

```python
def run_stimulus(self, context_events: List[str]) -> ColonyResponse:
    """
    Для каждого агента:
    1. RESET: восстановить affective_space.axes из baseline snapshot
       (НЕ пересоздавать агента — только аффективное состояние)
    2. INJECT: вызвать agent.step(context_events)
       - это активирует hippocampus.activate(context_events)
       - получает active_experiences
       - вычисляет cortical pressure
       - проходит через BG → ThalamicGate
       - обновляет affective_space
    3. TICK: запустить ещё (N_TICKS - 1) тиков с пустым контекстом []
       (decay аффективного состояния, без нового стимула)
    4. MEASURE: снять affective_space.axes, вычислить deltas
    5. NM: снять neuromodulators snapshot, вычислить deltas
    
    ВАЖНО: НЕ запускать sleep() между стимулами — только waking ticks
    ВАЖНО: НЕ обновлять ValueLayer во время прогона (reward=0 для ticks 2..N)
    """
```

### Сброс аффективного состояния между стимулами

```python
def _reset_agent_affective_state(self, agent: Any) -> None:
    """
    Сбрасывает ТОЛЬКО аффективное состояние агента к baseline.
    НЕ трогает: hippocampus, cortex, neuromodulators, value_layer.
    
    Алгоритм:
    1. Получить baseline_snapshot из self._baseline_states[agent_id]
    2. Для affective_space: перезаписать axes из snapshot
    3. Для affect_state (legacy): перезаписать valence/arousal/threat/curiosity
    4. НЕ сбрасывать affective_background, affective_persistence —
       они моделируют долгосрочный фон, который должен оставаться
    
    Обоснование: между словами "happy" и "murder" у агента должен 
    быть одинаковый стартовый аффективный фон. Но долгосрочные 
    характеристики личности (background field) — остаются.
    """
```

---

## 7. Модуль `warriner_validator.py`

### Загрузка и сэмплинг

```python
class WarrinerValidator:
    def __init__(
        self,
        warriner_csv_path: str,
        colony: NOWAColony,
        encoder: WordStimulusEncoder,
        n_words: int = 300,
        stratify_bins: bool = True,
        test_split_ratio: float = 0.2,  # 20% held-out test set
        seed: int = 42,
    )

    def load_warriner(self) -> pd.DataFrame:
        """
        Загружает CSV. Ожидаемые колонки:
        - 'Word' (или 'word', 'lemma')
        - 'V.Mean.Sum' (или 'valence', 'V')
        - 'A.Mean.Sum' (или 'arousal', 'A')
        - 'D.Mean.Sum' (или 'dominance', 'D')
        
        Нормализация:
        - V: (v - 5.0) / 4.0  → [-1, +1]
        - A: (a - 1.0) / 8.0  → [0, 1]
        - D: (d - 1.0) / 8.0  → [0, 1]
        """

    def sample_words(self) -> Tuple[List[dict], List[dict]]:
        """
        Стратифицированная выборка.
        
        Документ рекомендует: 50 low-V, 200 mid-V, 50 high-V
        для n_words=300.
        
        Возвращает (calibration_rows, test_rows).
        calibration_rows используются HippocampusSeeder для seed.
        test_rows — слова для валидации (НЕ должны пересекаться с seed).
        
        ВАЖНО: seed-корпус и test-корпус должны быть непересекающимися.
        Иначе агент "видел" слово при инициализации → тривиальная корреляция.
        """
```

### Разделение обучающей и тестовой выборок

```
Warriner (13 915 слов)
    ↓ стратифицированный split
    ├── seed_corpus (80% = ~11 132 слова)  → HippocampusSeeder
    │   Агент знает эти слова "с рождения"
    └── test_corpus (20% = ~2 783 слова)  → Validation
        Агент никогда не видел эти слова напрямую.
        Тест проверяет генерализацию через семантическое сходство.

Из test_corpus сэмплируем n_words=300 (стратифицировано).
```

### Вычисление корреляций

```python
@dataclass
class ValidationResult:
    n_words: int
    encoder_mode: str
    
    # Основные метрики (valence)
    spearman_rho_valence: float
    spearman_p_valence: float
    pearson_r_valence: float
    ccc_valence: float          # Concordance Correlation Coefficient
    
    # Arousal
    spearman_rho_arousal: float
    spearman_p_arousal: float
    
    # Per-archetype
    archetype_correlations: Dict[str, float]   # archetype → ρ
    archetype_n_agents: Dict[str, int]          # archetype → count
    
    # Variance check (anti-collapse)
    sd_nowa_valence: float
    sd_human_valence: float
    sd_ratio: float             # должен быть > 0.1, иначе collapse
    
    # Memory activation stats
    mean_activated_memories: float   # среднее число активированных эпизодов
    zero_activation_ratio: float     # доля слов с нулевой активацией памяти
    
    # Raw data для plotting
    words: List[str]
    warriner_valence_norm: List[float]
    nowa_valence_shifts: List[float]
    warriner_arousal_norm: List[float]
    nowa_arousal_shifts: List[float]
    colony_responses: List[ColonyResponse]
    
    def summary(self) -> str:
        """Human-readable summary с интерпретацией."""


def compute_ccc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Concordance Correlation Coefficient.
    CCC = 2 * cov(x,y) / (var(x) + var(y) + (mean_x - mean_y)^2)
    Учитывает и корреляцию, и сдвиг среднего.
    CCC > 0.3 для arousal = SOTA уровень (по документу).
    """
```

### Диагностика нулевых активаций

```python
def diagnose_zero_activations(
    self,
    result: ValidationResult,
    threshold: float = 0.3,
) -> dict:
    """
    Если zero_activation_ratio > threshold:
    - Seed-корпус не покрывает тестовые слова семантически
    - Нужно увеличить n_seed или переключиться на sbert_neighbors encoder
    
    Возвращает диагностический отчёт:
    {
        'zero_activation_ratio': float,
        'worst_words': List[str],  # слова с минимальной активацией
        'recommendation': str,
    }
    """
```

---

## 8. Модуль `demo_app.py` — Streamlit UI

### Структура страниц

```
Streamlit App
├── Sidebar: Configuration
│   ├── Warriner CSV path
│   ├── Encoder mode (lexical | sbert_neighbors | direct_vad)
│   ├── Colony size (50..500, default 100)
│   ├── Words to test (50..1000, default 300)
│   ├── Ticks per stimulus (5..30, default 10)
│   ├── Seed size (100..2000, default 500)
│   └── [▶️ Run Validation]
│
└── Main area (Tabs)
    ├── 📊 Main Results
    │   ├── Metric cards: ρ(V), r(V), CCC(V), ρ(A)
    │   ├── Variance check: SD_NOWA vs SD_human
    │   ├── Memory activation: mean activated memories per word
    │   └── Signal badge: ✅ PROOF OF LIFE / ⚠️ WEAK / ❌ NO SIGNAL
    │
    ├── 🔵 Scatter Plot
    │   ├── NOWA valence shift vs Warriner V (with trendline)
    │   ├── Hover: word name + both values
    │   └── Color: by archetype
    │
    ├── 🎭 Per-Archetype Analysis
    │   ├── Bar chart: ρ per archetype
    │   ├── Distribution: valence shift histograms per archetype
    │   └── Key test: anxious_loner более негативен на neg-V словах?
    │
    ├── 🧠 Memory Diagnostics
    │   ├── Scatter: n_activated_memories vs |warriner_V|
    │   ├── Zero-activation words list
    │   └── Seed coverage visualization
    │
    ├── 📋 Word-Level Data
    │   ├── Sortable table: word, warriner_V, nowa_shift, residual
    │   ├── Top 20 outliers (worst predictions)
    │   └── Download CSV button
    │
    └── 🔬 Neuromodulators
        ├── DA delta vs Warriner V scatter
        ├── NE delta vs Warriner A scatter
        └── Cortisol delta vs Warriner V (негативные слова → cortisol up?)
```

### Ключевые визуализации

#### Проверка на схлопывание (обязательно показывать клиенту)

```
SD check:
  SD(Human Warriner V) = X.XXX
  SD(NOWA valence shift) = X.XXX
  Ratio = X.XX  [зелёный если > 0.1, красный если < 0.05]

"Если ratio < 0.1 — агенты отвечают почти одинаково (collapse).
 Корреляция может быть артефактом, а не реальным сигналом."
```

#### Проверка гипотезы по архетипам

```
H0: NOWA(anxious_loner | neg_V_words).valence_shift 
  = NOWA(explorer | neg_V_words).valence_shift

Тест: t-test между двумя группами на подмножестве neg-V слов (V < -0.3)
Показывать: t-statistic, p-value, effect size Cohen's d

"Если d > 0.5 и p < 0.05 — архетипы биологически различимы."
```

### Нижний дисклеймер (обязателен на каждой странице)

```
⚠️ This report was generated by a computational simulation (NOWA synthetic 
respondent platform). It does NOT involve real human respondents. Findings are 
directional and intended to support hypothesis generation, creative triage, and 
pre-research exploration. They should NOT be used as the sole basis for 
high-stakes marketing decisions or substituted for human consumer research.

Validation correlation with Warriner et al. (2013) benchmark:
Spearman ρ = {result.spearman_rho_valence:.3f} (n={result.n_words} words, 
encoder={result.encoder_mode}).
```

---

## 9. CLI `run_quick.py`

```
Использование:
  python run_quick.py \
    --warriner data/Ratings_Warriner_et_al.csv \
    --words 300 \
    --agents 100 \
    --seed-size 500 \
    --ticks 10 \
    --encoder lexical \
    --output results.json

Вывод (stdout):
  [Colony] Initializing 100 agents...
  [Seeder] Loading 500 seed episodes per agent...
  [Seeder] Seed coverage: low_V=100, mid_V=300, high_V=100
  [Validation] Processing word 1/300: abandon
  ...
  [Validation] Processing word 300/300: zest

  === NOWA × Warriner Validation ===
  Words tested: 300
  Encoder: lexical
  Seed size: 500

  VALENCE:
    Spearman ρ = 0.XXX  (p = X.XXXe-XX)
    Pearson  r = 0.XXX
    CCC        = 0.XXX
    ✅ PROOF OF LIFE  [или соответствующий статус]

  AROUSAL:
    Spearman ρ = 0.XXX  (p = X.XXXe-XX)

  VARIANCE CHECK:
    SD(human)  = 0.XXX
    SD(NOWA)   = 0.XXX
    Ratio      = 0.XX  [OK / COLLAPSE WARNING]

  MEMORY DIAGNOSTICS:
    Mean activated memories per word: X.X
    Zero-activation words: XX (XX.X%)

  PER-ARCHETYPE correlations (valence):
    explorer:            ρ = 0.XXX
    passive:             ρ = 0.XXX
    resource_pragmatist: ρ = 0.XXX
    anxious_loner:       ρ = 0.XXX
```

---

## 10. `requirements.txt`

```
# Core
streamlit>=1.30
pandas>=2.0
numpy>=1.24
scipy>=1.10
plotly>=5.15
scikit-learn>=1.3

# NLP (для encoder)
sentence-transformers>=2.2   # режим sbert_neighbors
nrclex>=3.0                  # режим lexical с NRC эмоциями

# Stats
pingouin>=0.5                # CCC, ICC расчёты

# Optional (для ускорения)
torch>=2.0                   # если используется SBERT
```

---

## 11. Порядок реализации

### День 1 (4 часа)

1. `hippocampus_seeder.py` — базовая версия (stratified, lexical tokens)
2. `word_stimulus_encoder.py` — только режим `lexical`
3. `nowa_colony.py` — инициализация + `run_stimulus()` + reset
4. `run_quick.py` — CLI без UI
5. Прогон 300 слов, 100 агентов → первое число ρ

### День 2–3

6. Анализ outliers: какие слова модель предсказывает хуже всего
7. `word_stimulus_encoder.py` — режим `sbert_neighbors`
8. Сравнение: `lexical` vs `sbert_neighbors` vs `direct_vad`
9. Per-archetype диагностика

### День 4–5

10. `demo_app.py` — Streamlit UI
11. Проверка гипотезы по архетипам (t-критерий)
12. Вкладка диагностики памяти
13. Экспорт и нижний дисклеймер

---

## 12. Критические проверки перед публикацией результатов

- [ ] seed_corpus ∩ test_corpus = ∅ (нет утечки данных)
- [ ] SD(NOWA) / SD(human) > 0.1 (нет collapse)
- [ ] zero_activation_ratio < 0.3 (гиппокамп активируется)
- [ ] p-value < 0.01 при n=300 (статистическая значимость)
- [ ] Проверен `direct_vad` baseline: если ρ_direct >> ρ_lexical, нужен лучший encoder
- [ ] Per-archetype: anxious_loner даёт более негативный сдвиг на neg-V словах
- [ ] Disclaimer присутствует в каждом экране и в CSV-экспорте

---

## 13. Ожидаемые результаты и риски

### Оптимистичный сценарий (ρ ≥ 0.5)

Seed-корпус даёт достаточное покрытие. SBERT-соседи усиливают активацию редких слов. Архетипы показывают значимо различные отклики. → Готово к демонстрации первым клиентам.

### Реалистичный сценарий (ρ 0.3–0.5)

Слабые слова (абстрактные, редкие, культурно-специфичные) дают нулевую активацию. Решение: увеличить seed до 2000+, добавить `sbert_neighbors` encoder.

### Пессимистичный сценарий (ρ < 0.2)

Формат `context_events` не совпадает с тем, как гиппокамп индексирует эпизоды. Диагностика: проверить `NOWAHippocampus._build_query_signature()` — как он хэширует `"word:happy"` vs как хранятся seed-эпизоды. Возможно, нужна нормализация токенов (lowercase, strip пробелов).

---

*Спецификация готова к передаче агенту-разработчику. Все зависимости от существующих модулей NOWA указаны явно. Новые модули не модифицируют существующий код — только используют публичный API.*
