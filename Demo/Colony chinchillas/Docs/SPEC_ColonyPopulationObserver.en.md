# ColonyPopulationObserver Specification

Russian version: [SPEC_ColonyPopulationObserver.ru.md](SPEC_ColonyPopulationObserver.ru.md)

## Abstract

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

This document specifies `ColonyPopulationObserver`, a passive observer of chinchilla-colony dynamics. On request, the module takes a metric slice, accumulates a history of snapshots, and provides for export. Agents and the simulation runner are not modified. Reading proceeds through public attributes, and missing fields of incomplete agents are replaced by zero or empty values.

The snapshot `ColonySnapshot` covers demography and age classes, births and deaths relative to the previous slice, mean affect, neuromodulators, and wakefulness, the structure of social pairs, reproductive and vitality measures, hippocampal size and mean temporal-difference error, genome diversity, cage resources, the distribution of actions and zones, and the identifiers of individuals at the extremes of age, offspring, sociality, and stress. The sampling interval is set by skipping ticks.

In the multi-agent NOWA installation, the observer is the measurement layer for the colony as a population. The specification separates the accumulation of longitudinal series from action selection and thereby states the conditions under which demographic, affective, social, and genetic processes can be compared over time without measurement feeding back into the simulated agents.

**File:** `Demo/Colony chinchillas/src/colony_population_observer.py`  
**Version:** 1.0

---

## 1. Purpose

`ColonyPopulationObserver` is a passive observer of chinchilla-colony dynamics.  
It collects metric snapshots on request, stores the history, and supports export.

**Principles:**

- It never mutates agents or the runner
- It reads data through public attributes and properties
- Every operation is inside `try/except`: an unavailable attribute yields 0.0 or `""`
- It works with incomplete agents (no NOWA, no mortality: those fields are simply skipped)

---

## 2. ColonySnapshot — snapshot structure

```python
@dataclass(frozen=True)
class ColonySnapshot:
    # Время
    sim_time: float
    tick_number: int                    # сколько observe() вызвано

    # Демография
    agent_count: int
    female_count: int
    male_count: int
    juvenile_count: int
    adult_count: int
    elder_count: int
    pregnant_count: int
    sleeping_count: int

    # Рождения и смерти (с последнего снапшота)
    births_since_last: int
    deaths_since_last: int
    total_births: int
    total_deaths: int

    # Аффективное состояние популяции (средние)
    mean_stress: float                  # [0, 1]
    mean_valence: float                 # [-1, 1]
    mean_arousal: float                 # [0, 1]
    mean_energy: float                  # [0, 1]
    mean_social_drive: float            # [0, 1]

    # Нейромодуляторы (средние по популяции)
    mean_dopamine: float                # [0, 1]
    mean_serotonin: float               # [0, 1]
    mean_cortisol: float                # [0, 1]
    mean_wakefulness: float             # [0, 1]

    # Социальная структура
    mean_affinity: float                # среднее affinity по всем парам в knowledge
    mean_familiarity: float             # среднее familiarity
    total_known_pairs: int              # количество пар (a знает b)
    bonded_pairs: int                   # relationship_type == "bonded"
    rival_pairs: int                    # relationship_type == "rival"
    kin_pairs: int                      # relationship_type == "kin"
    mate_pairs: int                     # relationship_type == "mate"

    # Репродукция
    mean_reproductive_drive: float      # из reproductive_system
    mean_heat_cycle_value: float        # только самки с heat_cycle
    mean_vitality: float                # из mortality_system
    mean_age: float                     # sim-секунды

    # NOWA когниция (средние)
    mean_lived_steps: float             # agent.lived_steps
    mean_hippocampus_size: float        # len(agent.hippocampus.experiences)
    mean_td_error: float                # из td_error_history
    mean_genome_diversity: float        # из swarm.get_diversity() если доступен

    # Ресурсы клетки
    food_pellets: float                 # [0, 1]
    hay: float                          # [0, 1]
    water: float                        # [0, 1]
    wheel_occupied: bool
    dustbath_occupied: bool
    house_occupant_count: int

    # Активность
    action_distribution: Dict[str, int]  # {action: count}
    position_distribution: Dict[str, int]  # {zone: count}

    # Агент-рекордсмены
    oldest_agent_id: str               # максимальный age
    most_offspring_agent_id: str       # максимальный total_offspring
    most_social_agent_id: str          # максимальный len(knowledge)
    most_stressed_agent_id: str        # максимальный stress
```

---

## 3. API of the class ColonyPopulationObserver

### 3.1 Initialisation

```python
class ColonyPopulationObserver:
    def __init__(
        self,
        runner: SimulationRunner,
        observe_every_n_ticks: int = 1,
    ) -> None:
        """
        Аргументы:
            runner: SimulationRunner для чтения состояния
            observe_every_n_ticks: пропускать тики между снапшотами
                                   (1 = каждый observe(), 10 = каждый 10-й)
        """
        self.runner = runner
        self.observe_every_n_ticks = max(1, int(observe_every_n_ticks))
        self.history: List[ColonySnapshot] = []
        self._tick_counter: int = 0
        self._total_births_last: int = 0
        self._total_deaths_last: int = 0
        self._prev_agent_ids: Set[str] = set()
```

### 3.2 Principal method

```python
def observe(self) -> Optional[ColonySnapshot]:
    """
    Собрать снапшот текущего состояния колонии.
    
    Если текущий тик не кратен observe_every_n_ticks — вернуть None.
    Иначе — собрать ColonySnapshot, добавить в history, вернуть.
    
    Никогда не вызывает исключений — весь код в try/except.
    При любой ошибке соответствующее поле = 0.0 / "" / False / {}.
    """

def observe_force(self) -> ColonySnapshot:
    """
    Принудительно собрать снапшот независимо от счётчика тиков.
    Всегда добавляет в history.
    """

def observe_tick(self) -> Optional[ColonySnapshot]:
    """
    Удобный метод для вызова из SimulationRunner.tick().
    Инкрементирует внутренний счётчик и вызывает observe().
    """
```

### 3.3 History analysis

```python
def get_latest(self) -> Optional[ColonySnapshot]:
    """Последний снапшот или None."""

def get_trend(
    self,
    field: str,
    last_n: int = 10,
) -> List[float]:
    """
    Значения поля за последние N снапшотов.
    
    Аргументы:
        field: имя поля ColonySnapshot (строка)
        last_n: сколько последних снапшотов брать
    
    Возвращает: список float в хронологическом порядке.
    При недоступном поле — пустой список.
    """

def get_population_peak(self) -> Optional[ColonySnapshot]:
    """Снапшот с максимальным agent_count."""

def get_extinction_risk(self) -> float:
    """
    Оценка риска вымирания [0.0, 1.0].
    
    Высокий риск если:
    - agent_count <= 2
    - все агенты одного пола
    - mean_stress > 0.7
    - food_pellets < 0.1
    - нет беременных и нет пар готовых к спариванию
    
    Формула:
        risk = weighted_sum(факторы) / max_weight
    Каждый фактор вносит вклад в [0, 1]:
        - agent_count <= 2: +0.4
        - single_sex: +0.3
        - mean_stress > 0.7: +0.2
        - food_pellets < 0.1: +0.2
        - no_reproduction_potential: +0.3
    
    Возвращает: float в [0.0, 1.0]. 0.0 если нет истории.
    """

def get_social_cohesion(self) -> float:
    """
    Индекс социальной сплочённости [0.0, 1.0].
    
    cohesion = (mean_affinity + 1) / 2 * bonded_fraction
    где bonded_fraction = bonded_pairs / max(1, total_known_pairs)
    
    Возвращает: float в [0.0, 1.0]. 0.0 если нет снапшотов.
    """
```

### 3.4 Export

```python
def to_dict(self) -> dict:
    """
    Сериализовать всю историю в JSON-совместимый словарь.
    
    Формат:
    {
        "version": "1.0",
        "snapshot_count": int,
        "snapshots": [
            {все поля ColonySnapshot как float/int/str/bool/dict}
        ]
    }
    """

def save(self, path: str) -> None:
    """
    Сохранить историю в JSON файл.
    Создаёт директорию если не существует.
    При ошибке записи — warnings.warn, не исключение.
    """

def load(self, path: str) -> None:
    """
    Загрузить историю из JSON файла.
    Добавляет к существующей истории (не заменяет).
    При ошибке парсинга — warnings.warn, история не меняется.
    """

def clear(self) -> None:
    """Очистить историю снапшотов и сбросить счётчики."""

def summary_text(self) -> str:
    """
    Краткая текстовая сводка текущего состояния.
    
    Пример:
        "Colony: 4 agents (2F/2M) | stress: 0.23 | affinity: 0.41 | births: 1 deaths: 0"
    
    Пустая строка если нет снапшотов.
    """
```

---

## 4. Helper functions

```python
def _read_neuromodulator(agent: Any, nm_name: str) -> float:
    """Читать нейромодулятор через agent.neuromodulators.{nm_name}."""

def _read_affective_axis(agent: Any, axis: str) -> float:
    """Читать ось через agent.affective_space.axes.get(axis, 0.0)."""

def _collect_knowledge_stats(
    agents: List[Any],
) -> Tuple[float, float, int, int, int, int, int]:
    """
    Вернуть:
        (mean_affinity, mean_familiarity, total_pairs,
         bonded, rival, kin, mate)
    """

def _build_action_distribution(agents: List[Any]) -> Dict[str, int]:
    """Подсчитать {action: count} по всем агентам."""

def _build_position_distribution(agents: List[Any]) -> Dict[str, int]:
    """Подсчитать {zone: count} по всем агентам."""
```

---

## 5. Integration with SimulationRunner

`ColonyPopulationObserver` is used as an external observer and is not built into the runner:

```python
# Типичное использование:
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner, observe_every_n_ticks=10)

for _ in range(1000):
    runner.tick(0.1)
    snapshot = observer.observe_tick()
    if snapshot:
        print(observer.summary_text())
```

Optionally, integration into `ColonyGUI.get_render_state()`:

```python
# В ColonyGUI:
if hasattr(runner, "_observer"):
    swarm_stats["extinction_risk"] = runner._observer.get_extinction_risk()
    swarm_stats["social_cohesion"] = runner._observer.get_social_cohesion()
```

---

## 6. Constants

```python
OBSERVER_VERSION = "1.0"
MAX_HISTORY_LENGTH = 10000      # максимум снапшотов в памяти
EXTINCTION_RISK_WEIGHTS = {
    "low_population": 0.4,
    "single_sex": 0.3,
    "high_stress": 0.2,
    "food_critical": 0.2,
    "no_reproduction": 0.3,
}
EXTINCTION_RISK_MAX_WEIGHT = sum(EXTINCTION_RISK_WEIGHTS.values())
```

---

## 7. Implementation constraints

1. `ColonyPopulationObserver` is read-only. It does not call methods of agents.
2. `observe()` places all of its code in `try/except`. An exception in one field does not break the snapshot: each field is computed independently in its own `try/except`.
3. `history` is bounded by `MAX_HISTORY_LENGTH`; when the bound is exceeded, the oldest snapshots are removed.
4. `get_trend()`: if the field does not exist on `ColonySnapshot`, the result is an empty list and no exception is raised.
5. `births_since_last` and `deaths_since_last` are the difference of the runner’s `total_births` / `total_deaths` between snapshots.
6. `mean_genome_diversity` is read from `runner.swarm.get_diversity()` when `runner.swarm` exists.
7. Python 3.10 or newer, and the standard library only.

---

## 8. Test cases

### TC-01: `observe()` on an empty runner

```python
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner)

snapshot = observer.observe_force()

assert snapshot is not None
assert snapshot.agent_count == 0
assert snapshot.mean_stress == 0.0
assert snapshot.action_distribution == {}
assert snapshot.food_pellets >= 0.0
```

### TC-02: `observe_every_n_ticks` filters

```python
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner, observe_every_n_ticks=3)

results = [observer.observe_tick() for _ in range(9)]
non_none = [r for r in results if r is not None]

assert len(non_none) == 3
assert len(observer.history) == 3
```

### TC-03: Demographic counters

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F", is_mature=True))
runner.add_agent(ChinchillaAgent(sex="F", is_mature=False))
runner.add_agent(ChinchillaAgent(sex="M", is_mature=True))

observer = ColonyPopulationObserver(runner)
snapshot = observer.observe_force()

assert snapshot.agent_count == 3
assert snapshot.female_count == 2
assert snapshot.male_count == 1
assert snapshot.juvenile_count == 1
assert snapshot.adult_count == 2
```

### TC-04: `mean_stress` is read from AffectiveSpace

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F")
agent.affective_space.axes["stress"] = 0.6
runner.add_agent(agent)

observer = ColonyPopulationObserver(runner)
snapshot = observer.observe_force()

assert abs(snapshot.mean_stress - 0.6) < 1e-6
```

### TC-05: `social_cohesion` rises when pairs are bonded

```python
runner = SimulationRunner()
a = ChinchillaAgent(sex="F")
b = ChinchillaAgent(sex="M")

# Настроить знание
a._ensure_known(b.agent_id, b.get_public_state())
a.knowledge[b.agent_id].affinity = 0.8
a.knowledge[b.agent_id].familiarity = 0.9
a.knowledge[b.agent_id].relationship_type = "bonded"

runner.add_agent(a)
runner.add_agent(b)

observer = ColonyPopulationObserver(runner)
observer.observe_force()

cohesion = observer.get_social_cohesion()
assert cohesion > 0.3
```

### TC-06: `extinction_risk` with a single agent

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))

observer = ColonyPopulationObserver(runner)
observer.observe_force()

risk = observer.get_extinction_risk()
assert risk >= 0.4   # low_population вносит 0.4 при agent_count <= 2
```

### TC-07: `extinction_risk` in a healthy population

```python
runner = SimulationRunner()
for i in range(4):
    sex = "F" if i % 2 == 0 else "M"
    a = ChinchillaAgent(sex=sex, is_mature=True)
    a.affective_space.axes["stress"] = 0.1
    runner.add_agent(a)
runner.resources.food_pellets = 0.8

observer = ColonyPopulationObserver(runner)
observer.observe_force()

risk = observer.get_extinction_risk()
assert risk < 0.3
```

### TC-08: `births_since_last` is counted correctly

```python
runner = SimulationRunner()
runner.total_births = 0
runner.total_deaths = 0

observer = ColonyPopulationObserver(runner)
observer.observe_force()

runner.total_births = 2
snapshot2 = observer.observe_force()

assert snapshot2.births_since_last == 2
assert snapshot2.total_births == 2
```

### TC-09: `get_trend` returns the correct values

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F")
runner.add_agent(agent)
observer = ColonyPopulationObserver(runner)

stress_levels = [0.1, 0.3, 0.5, 0.2, 0.4]
for stress in stress_levels:
    agent.affective_space.axes["stress"] = stress
    observer.observe_force()

trend = observer.get_trend("mean_stress", last_n=5)
assert len(trend) == 5
for expected, actual in zip(stress_levels, trend):
    assert abs(expected - actual) < 1e-5
```

### TC-10: `get_trend` of an unknown field

```python
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner)
observer.observe_force()

trend = observer.get_trend("nonexistent_field_xyz")
assert trend == []
```

### TC-11: save / load round-trip

```python
import tempfile, os

runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
observer = ColonyPopulationObserver(runner)
observer.observe_force()
observer.observe_force()

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    path = f.name

try:
    observer.save(path)

    observer2 = ColonyPopulationObserver(runner)
    observer2.load(path)

    assert len(observer2.history) == 2
    assert abs(observer2.history[0].mean_stress - observer.history[0].mean_stress) < 1e-6
finally:
    os.unlink(path)
```

### TC-12: `action_distribution` counts correctly

```python
runner = SimulationRunner()
actions = ["eat", "eat", "sleep", "explore"]
for i, action in enumerate(actions):
    a = ChinchillaAgent(sex="F" if i % 2 == 0 else "M")
    a.current_action = action
    runner.add_agent(a)

observer = ColonyPopulationObserver(runner)
snapshot = observer.observe_force()

assert snapshot.action_distribution["eat"] == 2
assert snapshot.action_distribution["sleep"] == 1
assert snapshot.action_distribution["explore"] == 1
```

### TC-13: `summary_text` format

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
runner.add_agent(ChinchillaAgent(sex="M"))

observer = ColonyPopulationObserver(runner)
observer.observe_force()

text = observer.summary_text()
assert "2" in text           # agent_count
assert "stress" in text.lower()
assert len(text) > 10
```

### TC-14: `get_population_peak`

```python
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner)

for n in [1, 3, 2, 4, 2]:
    runner.agents = [ChinchillaAgent(sex="F") for _ in range(n)]
    observer.observe_force()

peak = observer.get_population_peak()
assert peak is not None
assert peak.agent_count == 4
```

### TC-15: history is bounded by `MAX_HISTORY_LENGTH`

```python
runner = SimulationRunner()
observer = ColonyPopulationObserver(runner)

for _ in range(MAX_HISTORY_LENGTH + 50):
    observer.observe_force()

assert len(observer.history) == MAX_HISTORY_LENGTH
```

### TC-16: An agent without NOWA does not break the observer

```python
class MinimalAgent:
    agent_id = "test"
    sex = "F"
    age = 0.0
    current_action = "idle"
    position = "floor"
    is_sleeping = False
    is_mature = True
    is_pregnant = False

runner = SimulationRunner()
runner.agents = [MinimalAgent()]

observer = ColonyPopulationObserver(runner)
snapshot = observer.observe_force()

assert snapshot is not None
assert snapshot.agent_count == 1
assert snapshot.mean_stress == 0.0   # нет AffectiveSpace → 0.0
```

---

## 9. Notes for the implementing agent

- Read `total_births` and `total_deaths` from `getattr(runner, "total_births", 0)` and `getattr(runner, "total_deaths", 0)`. These attributes are added to `SwarmEnvironment` through the bridge.
- Read `mean_genome_diversity` through `getattr(getattr(runner, "swarm", None), "get_diversity", lambda: lambda: 0.0)()()`. The call is double: first obtain the method, then call it.
- Read `sleeping_count` from `runner.swarm.get_sleeping_agents()` when that is available; otherwise count through `agent.is_sleeping`.
- `ColonySnapshot` is a dataclass with `frozen=True`. Every field must have a default through `field(default=...)` so that partial construction remains possible when errors occur.
- `births_since_last` = `total_births_now - self._total_births_last`, then `self._total_births_last = total_births_now`.
- `position_distribution`: the keys are zone strings (`"floor"`, `"house"`, and so on); the values are agent counts.
- Read `most_offspring_agent_id` through `agent.reproductive_system.total_offspring` when that is available.
- When `len(history) > MAX_HISTORY_LENGTH`, delete `history[:-MAX_HISTORY_LENGTH]` in place.
- `clear()` resets `_tick_counter`, `_total_births_last`, `_total_deaths_last`, and `_prev_agent_ids`.
