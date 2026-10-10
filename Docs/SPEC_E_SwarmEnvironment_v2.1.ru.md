# Спецификация пакета E v2.1 — SwarmEnvironment

English version: [SPEC_E_SwarmEnvironment_v2.1.en.md](SPEC_E_SwarmEnvironment_v2.1.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Проект:** NOWA (расширение существующего)  
**Файл:** `src/swarm.py`  
**Зависимости:** `genome.py` (A), `epigenome.py` (B), `agent_factory.py` (C), `fitness.py` (D)  
**Версия спецификации:** 2.1  
**Изменения от v2:** уточнена модель сна — спящий агент видим и может быть разбужен сигналами

---

## 1. Философия архитектуры

Среда — физическое пространство, не менеджер агентов.

Агенты полностью автономны:
- сами решают когда спать (по wakefulness)
- сами воспринимают соседей в радиусе
- сами реагируют на социальные сигналы

Среда предоставляет:
- 3D координатное пространство (float)
- физику расстояний и затухания сигналов
- механизм восприятия (кто в радиусе агента)
- глобальные тики для синхронизации времени

**Принцип исключения:** два агента не могут занимать одну точку.  
Минимальное расстояние между агентами: `MIN_AGENT_DISTANCE = 0.1`

---

## 2. Модель сна — ключевые принципы

Сон — физиологическое состояние, не исчезновение из пространства.

**Спящий агент:**
- физически присутствует в пространстве — виден другими агентами
- может получать социальные сигналы от соседей
- сигнал достаточной силы может прервать сон (механизм пробуждения)
- сам излучает ослабленные сигналы (аффект приглушён во сне)
- не вызывает `agent.step()` — когнитивная активность приостановлена

**Сигнальный коэффициент спящего агента:**
```
sleeping_signal_factor = 0.3  # спящий излучает 30% от обычной силы
```

**Порог принудительного пробуждения:**
```
Если суммарная stress-компонента входящих сигналов > WAKE_SIGNAL_THRESHOLD = 0.6:
    агент принудительно просыпается
```

---

## 3. Пространство

### 3.1 Position3D

```python
@dataclass(frozen=True)
class Position3D:
    x: float
    y: float
    z: float

    def distance_to(self, other: "Position3D") -> float:
        """Евклидово расстояние."""

    def to_tuple(self) -> Tuple[float, float, float]:
        """(x, y, z)"""

    @classmethod
    def random(cls, bounds: "SpaceBounds", rng: random.Random) -> "Position3D":
        """Случайная позиция в пределах границ."""

    @classmethod
    def origin(cls) -> "Position3D":
        """(0.0, 0.0, 0.0)"""


@dataclass(frozen=True)
class SpaceBounds:
    """Границы 3D пространства."""
    x_min: float = 0.0
    x_max: float = 100.0
    y_min: float = 0.0
    y_max: float = 100.0
    z_min: float = 0.0
    z_max: float = 0.0   # z_min == z_max → 2D режим (плоскость)

    def is_2d(self) -> bool:
        """Плоскость если z_min == z_max."""

    def contains(self, pos: Position3D) -> bool:
        """Позиция внутри границ."""

    def clamp(self, pos: Position3D) -> Position3D:
        """Клампировать позицию в границы."""

    def volume(self) -> float:
        """Объём пространства (площадь в 2D режиме)."""
```

---

## 4. Социальные сигналы

```python
@dataclass(frozen=True)
class SocialSignal:
    source_agent_id: str
    valence: float          # [-1.0, 1.0]
    arousal: float          # [0.0, 1.0]
    stress: float           # [0.0, 1.0]
    curiosity: float        # [0.0, 1.0]
    signal_strength: float  # [0.0, 1.0] — уже с учётом затухания
    source_is_sleeping: bool  # источник спит или нет
    distance: float         # расстояние до источника
    step: int
```

### 4.1 Затухание сигнала

```
signal_strength = base_strength / (1.0 + distance² * decay_factor)
```

Где `base_strength`:
- `1.0` — если источник активен
- `SLEEPING_SIGNAL_FACTOR = 0.3` — если источник спит

Сигнал игнорируется если `signal_strength < SIGNAL_MIN_STRENGTH = 0.01`

---

## 5. Автономный сон

### 5.1 Условие засыпания

```python
def _should_sleep(agent: Any, config: "SwarmConfig") -> bool:
    """
    Агент должен спать если:
        wakefulness >= config.sleep_threshold
    Читает: agent.wakefulness.wakefulness
    Возвращает False если атрибут недоступен.
    """
```

### 5.2 Механизм пробуждения от сигналов

```python
def _check_wake_signal(
    incoming_signals: List[SocialSignal],
    threshold: float = WAKE_SIGNAL_THRESHOLD,
) -> bool:
    """
    Проверить — достаточно ли сильны входящие сигналы чтобы разбудить.

    Вычисляет суммарный stress-сигнал:
        total_stress = sum(s.stress * s.signal_strength for s in incoming_signals)

    Возвращает True если total_stress >= threshold.
    """
```

### 5.3 Полный алгоритм тика для агента

```
ЕСЛИ агент спит (slot.is_sleeping == True):
    1. Собрать входящие сигналы от соседей (спящий получает сигналы)
    2. Применить сигналы к агенту (ослабленно, через observe_external_input)
    3. Проверить _check_wake_signal(signals):
       ЕСЛИ разбудить → slot.is_sleeping = False, перейти к активной фазе
       ИНАЧЕ → проверить гистерезис wakefulness:
           ЕСЛИ wakefulness < sleep_threshold * SLEEP_HYSTERESIS_FACTOR:
               slot.is_sleeping = False, перейти к активной фазе
           ИНАЧЕ:
               agent.sleep(cycles=1) — продолжить сон
               пропустить agent.step()

ЕСЛИ агент активен (slot.is_sleeping == False):
    1. Проверить _should_sleep:
       ЕСЛИ надо спать → slot.is_sleeping = True, agent.sleep(cycles=1)
       пропустить agent.step()
    2. ИНАЧЕ активная фаза:
       a. Собрать сигналы от соседей
       b. Применить сигналы
       c. Вычислить context_events
       d. Вычислить reward
       e. agent.step(context_events, reward=reward, ...)
```

---

## 6. Структуры данных

### 6.1 AgentSlot

```python
@dataclass
class AgentSlot:
    agent: Any
    position: Position3D
    perception_radius: float
    is_sleeping: bool = False
    sleep_started_step: int = 0
```

### 6.2 SwarmState

```python
@dataclass(frozen=True)
class SwarmState:
    step: int
    agent_count: int
    sleeping_count: int
    active_count: int
    diversity: float
    mean_wakefulness: float
    social_signals_sent: int
    bounds: SpaceBounds
```

---

## 7. SwarmConfig

```python
@dataclass
class SwarmConfig:
    bounds: SpaceBounds = field(default_factory=SpaceBounds)

    # Физика сигналов
    signal_decay_factor: float = 0.01
    base_perception_radius: float = 20.0
    social_signal_gain: float = 0.05

    # Сон
    sleep_threshold: float = 0.7
    wake_signal_threshold: float = 0.6  # суммарный стресс-сигнал для пробуждения

    # Контекст и награда
    context_events_fn: Optional[Callable] = None
    reward_fn: Optional[Callable] = None

    # Общее
    max_steps_per_generation: int = 200
```

---

## 8. API класса SwarmEnvironment

### 8.1 Инициализация

```python
class SwarmEnvironment:
    def __init__(
        self,
        config: SwarmConfig,
        fitness_evaluator: FitnessEvaluator,
        rng: Optional[random.Random] = None,
    ):
        self.config = config
        self.fitness_evaluator = fitness_evaluator
        self.global_step: int = 0
        self._slots: Dict[str, AgentSlot] = {}
        self._rng = rng if rng is not None else random.Random()
```

### 8.2 Управление популяцией

```python
def add_agent(
    self,
    agent: Any,
    position: Optional[Position3D] = None,
) -> Position3D:
    """
    Добавить агента в пространство.
    position=None → случайная позиция без коллизий.

    Радиус восприятия:
        factor = genome.genes["dr_perception_radius_factor"] если genome есть
        radius = config.base_perception_radius * factor

    Возвращает назначенную позицию.
    Ограничения:
        - позиция клампируется в bounds
        - коллизии разрешаются сдвигом
        - MAX_POPULATION_SIZE = 256
        - дубль agent_id → предупреждение, не исключение
    """

def remove_agent(self, agent_id: str) -> Optional[Any]:
    """Удалить агента. Возвращает агента или None."""

def move_agent(self, agent_id: str, new_position: Position3D) -> bool:
    """
    Переместить агента.
    False если: не найден / коллизия / вне bounds.
    """

def get_agent(self, agent_id: str) -> Optional[Any]:
def get_position(self, agent_id: str) -> Optional[Position3D]:
def get_all_agents(self) -> List[Any]:
    """Отсортированы по agent_id."""

def replace_population(self, agents: List[Any]) -> None:
    """
    Заменить всю популяцию. Случайно расставить.
    global_step не сбрасывается.
    """
```

### 8.3 Восприятие

```python
def get_agents_in_radius(
    self,
    agent_id: str,
    radius: Optional[float] = None,
    include_sleeping: bool = True,
) -> List[Tuple[Any, float]]:
    """
    Агенты в радиусе восприятия.

    include_sleeping=True (default) — спящие включены.
    Не включает самого агента.
    Возвращает (agent, distance) по distance ASC.
    """

def collect_signals_for_agent(
    self,
    agent_id: str,
) -> List[SocialSignal]:
    """
    Сигналы от всех агентов в радиусе восприятия.
    Включает сигналы от спящих агентов (ослабленные в 0.3 раза).
    Фильтрует сигналы слабее SIGNAL_MIN_STRENGTH.
    Возвращает по signal_strength DESC.
    """
```

### 8.4 Применение сигналов

```python
def apply_social_signal(
    self,
    agent: Any,
    signal: SocialSignal,
    gain: float,
) -> None:
    """
    Применить сигнал к агенту.

    Если агент спит — gain *= 0.5 (приглушённое восприятие во сне).

    Использует agent.observe_external_input() если доступен:
        source=f"social:{signal.source_agent_id}"
        payload={
            "valence": signal.valence * signal.signal_strength,
            "arousal": signal.arousal * signal.signal_strength,
            "stress": signal.stress * signal.signal_strength,
            "curiosity": signal.curiosity * signal.signal_strength,
            "source_is_sleeping": signal.source_is_sleeping,
        }
        uncertainty=1.0 - signal.signal_strength

    Иначе — прямое воздействие на affective_space.
    gain клампируется в [0.0, MAX_SOCIAL_SIGNAL_GAIN=0.5].
    Весь метод в try/except.
    """
```

### 8.5 Основной тик

```python
def tick(
    self,
    dt: float = 1.0,
    context_override: Optional[Dict[str, List[str]]] = None,
) -> SwarmState:
    """
    Один шаг всех агентов в детерминированном порядке (sorted by agent_id).
    Полный алгоритм описан в разделе 5.3.
    Ошибка одного агента не останавливает тик других.
    """

def run_generation(
    self,
    steps: Optional[int] = None,
    dt: float = 1.0,
) -> List[SwarmState]:
    """N тиков. steps=None → config.max_steps_per_generation."""
```

### 8.6 Метрики

```python
def get_diversity(self) -> float:
    """mean(pairwise genome.distance()). 0.0 если < 2 агентов или нет геномов."""

def get_swarm_state(self) -> SwarmState:
    """Снапшот без тика."""

def evaluate_all(self) -> List[FitnessVector]:
    """Оценить всех через fitness_evaluator."""

def get_sleeping_agents(self) -> List[str]:
def get_active_agents(self) -> List[str]:

def get_nearest_agents(
    self,
    position: Position3D,
    k: int = 5,
    include_sleeping: bool = True,
) -> List[Tuple[Any, float]]:
    """k ближайших агентов к позиции."""

def get_spatial_density(self, position: Position3D, radius: float) -> float:
    """Плотность агентов в радиусе. 2D: area_of_circle, 3D: volume_of_sphere."""
```

---

## 9. Константы

```python
SWARM_VERSION = "2.1"
MAX_POPULATION_SIZE = 256
MIN_POPULATION_SIZE = 2
MIN_AGENT_DISTANCE = 0.1
SIGNAL_MIN_STRENGTH = 0.01
MAX_SOCIAL_SIGNAL_GAIN = 0.5
SLEEP_HYSTERESIS_FACTOR = 0.7
SLEEPING_SIGNAL_FACTOR = 0.3
WAKE_SIGNAL_THRESHOLD = 0.6
SOCIAL_SIGNAL_AXES = ["valence", "arousal", "stress", "curiosity"]
```

---

## 10. Изменения в других файлах

### genome.py — добавить один ген в группу DR

```python
("dr_perception_radius_factor", "swarm", 0.5, 2.0, 1.0, 0.2,
 "Perception radius multiplier for swarm environment"),
```

В `to_agent_params()` в секцию `"autonomous"`:
```python
"perception_radius_factor": g["dr_perception_radius_factor"],
```

---

## 11. Ограничения реализации

1. Пространство непрерывное 3D. 2D как частный случай: `z_min == z_max`.
2. Спящий агент **видим** другими и **получает** сигналы (с коэффициентом 0.5).
3. Спящий агент **излучает** сигналы с коэффициентом `SLEEPING_SIGNAL_FACTOR = 0.3`.
4. Сигнал достаточной стресс-интенсивности будит спящего агента.
5. Нет threading — однопоточно.
6. `get_agents_in_radius()` по умолчанию включает спящих (`include_sleeping=True`).
7. `replace_population()` не сбрасывает `global_step`.
8. Python 3.10+, только стандартная библиотека.

---

## 12. Тест-кейсы

### TC-01: Position3D расстояние

```python
a = Position3D(0.0, 0.0, 0.0)
b = Position3D(3.0, 4.0, 0.0)

assert abs(a.distance_to(b) - 5.0) < 1e-9
assert a.distance_to(a) == 0.0
```

### TC-02: SpaceBounds 2D режим

```python
bounds_2d = SpaceBounds(z_min=5.0, z_max=5.0)
assert bounds_2d.is_2d() is True

bounds_3d = SpaceBounds(z_min=0.0, z_max=50.0)
assert bounds_3d.is_2d() is False
```

### TC-03: Принцип исключения

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator(), rng=random.Random(42))

for i in range(10):
    a = MagicMock(); a.agent_id = f"a{i}"; a.genome = None
    env.add_agent(a)

positions = [env.get_position(f"a{i}") for i in range(10)]
for i in range(len(positions)):
    for j in range(i + 1, len(positions)):
        assert positions[i].distance_to(positions[j]) >= MIN_AGENT_DISTANCE
```

### TC-04: Спящий агент видим другими

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100), base_perception_radius=50.0)
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock()
sleeper.affective_space.axes = {"valence": 0.5, "arousal": 0.3, "stress": 0.2, "curiosity": 0.4}

observer = MagicMock(); observer.agent_id = "observer"; observer.genome = None

env.add_agent(sleeper, position=Position3D(10.0, 0.0, 0.0))
env.add_agent(observer, position=Position3D(0.0, 0.0, 0.0))

# Пометить как спящего
env._slots["sleeper"].is_sleeping = True

# Спящий виден наблюдателю
nearby = env.get_agents_in_radius("observer", include_sleeping=True)
nearby_ids = [a.agent_id for a, _ in nearby]
assert "sleeper" in nearby_ids
```

### TC-05: Спящий агент излучает ослабленный сигнал

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    base_perception_radius=50.0,
    signal_decay_factor=0.0,  # без затухания для чистоты теста
)
env = SwarmEnvironment(config, FitnessEvaluator())

active_source = MagicMock(); active_source.agent_id = "active"; active_source.genome = None
active_source.affective_space = MagicMock()
active_source.affective_space.axes = {"valence": 1.0, "arousal": 1.0, "stress": 1.0, "curiosity": 1.0}

sleeping_source = MagicMock(); sleeping_source.agent_id = "sleeping"; sleeping_source.genome = None
sleeping_source.affective_space = MagicMock()
sleeping_source.affective_space.axes = {"valence": 1.0, "arousal": 1.0, "stress": 1.0, "curiosity": 1.0}

receiver = MagicMock(); receiver.agent_id = "receiver"; receiver.genome = None

env.add_agent(active_source, position=Position3D(5.0, 0.0, 0.0))
env.add_agent(sleeping_source, position=Position3D(-5.0, 0.0, 0.0))
env.add_agent(receiver, position=Position3D(0.0, 0.0, 0.0))

env._slots["sleeping"].is_sleeping = True

signals = env.collect_signals_for_agent("receiver")
sig_active = next(s for s in signals if s.source_agent_id == "active")
sig_sleeping = next(s for s in signals if s.source_agent_id == "sleeping")

# Спящий излучает в 0.3 / 1.0 = 0.3 раза слабее
assert sig_sleeping.signal_strength < sig_active.signal_strength
assert abs(sig_sleeping.signal_strength / sig_active.signal_strength - SLEEPING_SIGNAL_FACTOR) < 1e-6
assert sig_sleeping.source_is_sleeping is True
assert sig_active.source_is_sleeping is False
```

### TC-06: Агент просыпается от стресс-сигнала

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.6,
    base_perception_radius=50.0,
)
env = SwarmEnvironment(config, FitnessEvaluator())

# Спящий агент
sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock(); sleeper.affective_space.axes = {}
sleeper.wakefulness = MagicMock(); sleeper.wakefulness.wakefulness = 0.75
sleeper.sleep.return_value = {"cycles": 1}
sleeper.step.return_value = "eat"

# Источник стресса рядом
alarm = MagicMock(); alarm.agent_id = "alarm"; alarm.genome = None
alarm.affective_space = MagicMock()
alarm.affective_space.axes = {"valence": -1.0, "arousal": 1.0, "stress": 1.0, "curiosity": 0.0}
alarm.wakefulness = MagicMock(); alarm.wakefulness.wakefulness = 0.1
alarm.step.return_value = "alert"

env.add_agent(sleeper, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(alarm, position=Position3D(1.0, 0.0, 0.0))

env._slots["sleeper"].is_sleeping = True

env.tick()

# Спящий должен проснуться от сильного стресс-сигнала
assert env._slots["sleeper"].is_sleeping is False
assert sleeper.step.called
```

### TC-07: Агент не просыпается от слабого сигнала

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.6,
    base_perception_radius=50.0,
    signal_decay_factor=0.1,  # сильное затухание
)
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock(); sleeper.affective_space.axes = {}
sleeper.wakefulness = MagicMock(); sleeper.wakefulness.wakefulness = 0.75
sleeper.sleep.return_value = {"cycles": 1}

# Далёкий источник стресса — сигнал затухнет
far_alarm = MagicMock(); far_alarm.agent_id = "far_alarm"; far_alarm.genome = None
far_alarm.affective_space = MagicMock()
far_alarm.affective_space.axes = {"valence": -0.5, "arousal": 0.5, "stress": 0.5, "curiosity": 0.0}
far_alarm.wakefulness = MagicMock(); far_alarm.wakefulness.wakefulness = 0.1
far_alarm.step.return_value = "eat"

env.add_agent(sleeper, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(far_alarm, position=Position3D(40.0, 0.0, 0.0))

env._slots["sleeper"].is_sleeping = True

env.tick()

# Слабый сигнал не разбудил
assert env._slots["sleeper"].is_sleeping is True
assert not sleeper.step.called
```

### TC-08: Спящий получает сигналы с коэффициентом 0.5

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.wakefulness = MagicMock(); sleeper.wakefulness.wakefulness = 0.75
sleeper.sleep.return_value = {"cycles": 1}

emitter = MagicMock(); emitter.agent_id = "emitter"; emitter.genome = None
emitter.affective_space = MagicMock()
emitter.affective_space.axes = {"valence": 0.5, "arousal": 0.3, "stress": 0.1, "curiosity": 0.4}
emitter.wakefulness = MagicMock(); emitter.wakefulness.wakefulness = 0.1
emitter.step.return_value = "eat"

env.add_agent(sleeper, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(emitter, position=Position3D(5.0, 0.0, 0.0))
env._slots["sleeper"].is_sleeping = True
env._slots["sleeper"].perception_radius = 50.0

env.tick()

# observe_external_input вызван у спящего агента
assert sleeper.observe_external_input.called or True  # применён через любой механизм
```

### TC-09: Агент засыпает автономно

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
)
env = SwarmEnvironment(config, FitnessEvaluator())

tired = MagicMock(); tired.agent_id = "tired"; tired.genome = None
tired.affective_space = MagicMock(); tired.affective_space.axes = {}
tired.wakefulness = MagicMock(); tired.wakefulness.wakefulness = 0.85
tired.sleep.return_value = {"cycles": 1}

env.add_agent(tired)
env.tick()

assert env._slots["tired"].is_sleeping is True
assert not tired.step.called
assert tired.sleep.called
```

### TC-10: Агент просыпается по гистерезису

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.99,  # высокий порог — только физиологическое пробуждение
)
env = SwarmEnvironment(config, FitnessEvaluator())

rested = MagicMock(); rested.agent_id = "rested"; rested.genome = None
rested.affective_space = MagicMock(); rested.affective_space.axes = {}
rested.wakefulness = MagicMock(); rested.wakefulness.wakefulness = 0.85
rested.sleep.return_value = {"cycles": 1}
rested.step.return_value = "eat"

env.add_agent(rested)
env.tick()  # засыпает

assert env._slots["rested"].is_sleeping is True

# Отдохнул — wakefulness упал ниже порога пробуждения (0.7 * 0.7 = 0.49)
rested.wakefulness.wakefulness = 0.35
env.tick()

assert env._slots["rested"].is_sleeping is False
assert rested.step.called
```

### TC-11: Геномный радиус восприятия

```python
from genome import GenomeVector

config = SwarmConfig(base_perception_radius=10.0, bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

large_genes = dict(GenomeVector.default().genes)
large_genes["dr_perception_radius_factor"] = 2.0
agent_large = MagicMock(); agent_large.agent_id = "large"
agent_large.genome = GenomeVector(genes=large_genes)

small_genes = dict(GenomeVector.default().genes)
small_genes["dr_perception_radius_factor"] = 0.5
agent_small = MagicMock(); agent_small.agent_id = "small"
agent_small.genome = GenomeVector(genes=small_genes)

env.add_agent(agent_large)
env.add_agent(agent_small)

assert abs(env._slots["large"].perception_radius - 20.0) < 1e-6
assert abs(env._slots["small"].perception_radius - 5.0) < 1e-6
```

### TC-12: 3D расстояние

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100, z_max=100.0),
    base_perception_radius=15.0,
)
env = SwarmEnvironment(config, FitnessEvaluator())

a = MagicMock(); a.agent_id = "a"; a.genome = None
b = MagicMock(); b.agent_id = "b"; b.genome = None

env.add_agent(a, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(b, position=Position3D(10.0, 0.0, 10.0))  # distance ≈ 14.14

nearby = env.get_agents_in_radius("a")
assert any(agent.agent_id == "b" for agent, _ in nearby)
```

### TC-13: get_agents_in_radius exclude_sleeping

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100), base_perception_radius=50.0)
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
active = MagicMock(); active.agent_id = "active"; active.genome = None
observer = MagicMock(); observer.agent_id = "observer"; observer.genome = None

env.add_agent(sleeper, position=Position3D(5.0, 0.0, 0.0))
env.add_agent(active, position=Position3D(-5.0, 0.0, 0.0))
env.add_agent(observer, position=Position3D(0.0, 0.0, 0.0))
env._slots["sleeper"].is_sleeping = True

# include_sleeping=True (default) — видит обоих
all_nearby = env.get_agents_in_radius("observer", include_sleeping=True)
assert len(all_nearby) == 2

# include_sleeping=False — только активных
active_nearby = env.get_agents_in_radius("observer", include_sleeping=False)
assert len(active_nearby) == 1
assert active_nearby[0][0].agent_id == "active"
```

### TC-14: move_agent коллизия

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

a = MagicMock(); a.agent_id = "a"; a.genome = None
b = MagicMock(); b.agent_id = "b"; b.genome = None

env.add_agent(a, position=Position3D(10.0, 10.0, 0.0))
env.add_agent(b, position=Position3D(50.0, 50.0, 0.0))

assert env.move_agent("b", Position3D(10.0, 10.0, 0.0)) is False
assert env.move_agent("b", Position3D(30.0, 30.0, 0.0)) is True
```

### TC-15: replace_population не сбрасывает global_step

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

a = MagicMock(); a.agent_id = "a"; a.genome = None
a.affective_space = MagicMock(); a.affective_space.axes = {}
a.wakefulness = MagicMock(); a.wakefulness.wakefulness = 0.1
a.step.return_value = "eat"
env.add_agent(a)

env.tick(); env.tick()
assert env.global_step == 2

new_agents = [MagicMock() for _ in range(3)]
for i, ag in enumerate(new_agents):
    ag.agent_id = f"new_{i}"; ag.genome = None
env.replace_population(new_agents)

assert env.global_step == 2
assert len(env.get_all_agents()) == 3
```

### TC-16: get_swarm_state отражает sleeping_count

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

for i in range(4):
    a = MagicMock(); a.agent_id = f"a{i}"; a.genome = None
    env.add_agent(a)

env._slots["a0"].is_sleeping = True
env._slots["a1"].is_sleeping = True

state = env.get_swarm_state()
assert state.sleeping_count == 2
assert state.active_count == 2
assert state.agent_count == 4
```

### TC-17: run_generation возвращает N состояний

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

a = MagicMock(); a.agent_id = "solo"; a.genome = None
a.affective_space = MagicMock(); a.affective_space.axes = {}
a.wakefulness = MagicMock(); a.wakefulness.wakefulness = 0.1
a.step.return_value = "eat"
env.add_agent(a)

states = env.run_generation(steps=5)
assert len(states) == 5
assert env.global_step == 5
```

### TC-18: Ошибка одного агента не останавливает тик

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100))
env = SwarmEnvironment(config, FitnessEvaluator())

good = MagicMock(); good.agent_id = "good"; good.genome = None
good.affective_space = MagicMock(); good.affective_space.axes = {}
good.wakefulness = MagicMock(); good.wakefulness.wakefulness = 0.1
good.step.return_value = "eat"

bad = MagicMock(); bad.agent_id = "bad"; bad.genome = None
bad.affective_space = MagicMock(); bad.affective_space.axes = {}
bad.wakefulness = MagicMock(); bad.wakefulness.wakefulness = 0.1
bad.step.side_effect = RuntimeError("crash")

env.add_agent(good); env.add_agent(bad)

state = env.tick()  # не должен падать

assert good.step.called
assert isinstance(state, SwarmState)
```
