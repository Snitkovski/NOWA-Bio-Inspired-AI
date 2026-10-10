# Спецификация пакета D — FitnessEvaluator

English version: [SPEC_D_FitnessEvaluator.en.md](SPEC_D_FitnessEvaluator.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Проект:** NOWA (расширение существующего)  
**Файл:** `src/fitness.py`  
**Зависимости:** только стандартная библиотека Python (`math`, `dataclasses`, `typing`)  
**Внешние зависимости:** нет (агент передаётся как объект, данные читаются через атрибуты)  
**Версия спецификации:** 1.0

---

## 1. Назначение

`FitnessEvaluator` вычисляет многокритериальный вектор приспособленности агента.  
Используется `EvolutionLoop` (пакет F) для отбора между поколениями.

**Ключевые принципы:**

- Фитнес — вектор, не скаляр. Агрегация через Pareto-доминирование.
- Каждый критерий нормирован в [0.0, 1.0]. Выше = лучше.
- Оценка происходит **после сна** агента — консолидация учитывается.
- Evaluator читает данные агента через публичные атрибуты и методы.
- Нет side effects — оценка не изменяет состояние агента.

---

## 2. Критерии приспособленности

### 2.1 longevity — долгота жизни

```
longevity = min(1.0, lived_steps / expected_lifetime_steps)
```

Агент который прожил дольше без деградации — приспособленнее.  
Источник: `agent.lived_steps`, `agent.expected_lifetime_steps`.

### 2.2 affective_range — богатство аффективного опыта

```
affective_range = std(history of affective axes values)
```

Агент с богатой аффективной историей — не застрявший в одном состоянии.  
Нормировка: `std / 0.5` (max ожидаемое std для [-1,1] диапазона).  
Источник: `agent.affective_space.axes` — снапшоты за время жизни.

**Важно:** evaluator не хранит историю — она должна накапливаться в агенте.  
Агент должен иметь `affective_history: List[dict]` — список снапшотов осей.  
Если атрибут отсутствует — критерий = 0.0.

### 2.3 prediction_skill — качество предсказаний

```
prediction_skill = 1.0 - mean(abs(td_errors))
```

Агент который хорошо предсказывает последствия — приспособленнее.  
Нормировка через clamp в [0.0, 1.0].  
Источник: `agent.value_layer.snapshot()["last_td_error"]` — текущий TD error,  
и `td_error_history: List[float]` на агенте если есть.

### 2.4 stress_resilience — устойчивость к стрессу

```
stress_resilience = 1.0 - mean(cortisol_history)
```

Агент с низким хроническим кортизолом приспособленнее.  
Нормировка: cortisol в [0.0, 1.0], инвертируется.  
Источник: `agent.neuromodulators.cortisol` — текущий уровень,  
и `cortisol_history: List[float]` на агенте если есть.

### 2.5 behavioral_diversity — разнообразие поведения

```
behavioral_diversity = entropy(action_counts) / log(num_actions)
```

Агент который не застрял в одном действии — приспособленнее.  
Нормализованная энтропия: 0.0 = одно действие, 1.0 = равномерное распределение.  
Источник: `agent.bg_action_channels` — `selection_count` каждого канала.

### 2.6 learning_efficiency — эффективность обучения

```
learning_efficiency = sleep_update_count / (online_update_count + 1)
normalized = min(1.0, learning_efficiency / 3.0)
```

Агент который активно консолидирует во сне — приспособленнее.  
Источник: `agent.value_layer.snapshot()`.

### 2.7 memory_quality — качество памяти

```
memory_quality = mean(consolidation_weight) over hippocampus experiences
```

Агент с высококачественными консолидированными воспоминаниями — приспособленнее.  
Источник: `agent.hippocampus.experiences` → `consolidation_weight` атрибут каждого.

---

## 3. Структуры данных

### 3.1 FitnessVector

```python
@dataclass(frozen=True)
class FitnessVector:
    longevity: float            # [0.0, 1.0]
    affective_range: float      # [0.0, 1.0]
    prediction_skill: float     # [0.0, 1.0]
    stress_resilience: float    # [0.0, 1.0]
    behavioral_diversity: float # [0.0, 1.0]
    learning_efficiency: float  # [0.0, 1.0]
    memory_quality: float       # [0.0, 1.0]
    agent_id: str               # идентификатор агента
    generation: int             # поколение агента
    evaluation_step: int        # lived_steps на момент оценки
```

### 3.2 ParetoRank

```python
@dataclass(frozen=True)
class ParetoRank:
    agent_id: str
    rank: int           # 1 = Pareto-фронт, 2 = следующий слой, ...
    crowding_distance: float  # для ниширования внутри слоя
    fitness: FitnessVector
```

---

## 4. API класса FitnessEvaluator

### 4.1 Инициализация

```python
@dataclass
class FitnessEvaluator:
    weights: Dict[str, float] = None  # опциональные веса для скалярной агрегации
    
    def __post_init__(self):
        """
        Если weights не переданы — все критерии равновесны (1.0 каждый).
        Нормировать веса так чтобы sum = 1.0.
        """
```

### 4.2 Основная оценка

```python
def evaluate(self, agent: Any) -> FitnessVector:
    """
    Вычислить вектор приспособленности агента.
    
    Читает данные агента через getattr с fallback на 0.0/[].
    Никогда не вызывает исключений — некорректные данные дают 0.0 по критерию.
    Не изменяет состояние агента.
    
    Аргументы:
        agent: агент NOWA (любой объект с нужными атрибутами)
    
    Возвращает: FitnessVector со всеми критериями в [0.0, 1.0]
    """

def evaluate_population(self, agents: List[Any]) -> List[FitnessVector]:
    """
    Оценить список агентов.
    Возвращает список FitnessVector в том же порядке.
    """
```

### 4.3 Pareto-ранжирование

```python
def pareto_rank(self, fitness_vectors: List[FitnessVector]) -> List[ParetoRank]:
    """
    Ранжировать агентов по Pareto-доминированию.
    
    Алгоритм NSGA-II:
        1. Найти все недоминируемые решения → rank=1 (Pareto-фронт)
        2. Убрать их из множества, повторить → rank=2, ...
        3. Внутри каждого ранга вычислить crowding_distance
    
    Определение доминирования:
        A доминирует B если:
            - по всем критериям A >= B
            - по хотя бы одному критерию A > B
    
    Crowding distance:
        Для каждого критерия отсортировать агентов.
        Крайним (min/max) назначить distance = infinity.
        Остальным: distance += (next - prev) / (max - min) по каждому критерию.
    
    Возвращает: список ParetoRank, отсортированный по (rank, -crowding_distance)
    
    Ограничения:
        - пустой список → пустой список
        - один агент → rank=1, crowding_distance=inf
        - при равных значениях критерия crowding contribution = 0
    """
```

### 4.4 Скалярная агрегация (вспомогательная)

```python
def scalar_score(self, fitness: FitnessVector) -> float:
    """
    Взвешенная сумма критериев.
    Используется для быстрого сравнения когда Pareto избыточен.
    
    score = sum(weight[criterion] * value[criterion]) / sum(weights)
    
    Возвращает: float в [0.0, 1.0]
    """

def dominates(self, a: FitnessVector, b: FitnessVector) -> bool:
    """
    Возвращает True если a доминирует b.
    Используется в pareto_rank и в тестах.
    """
```

### 4.5 Диагностика

```python
def criteria_names(self) -> List[str]:
    """Список имён критериев в детерминированном порядке."""

def fitness_to_dict(self, fitness: FitnessVector) -> dict:
    """Сериализовать FitnessVector в словарь."""

def fitness_from_dict(self, data: dict) -> FitnessVector:
    """Восстановить FitnessVector из словаря. Отсутствующие поля = 0.0."""
```

---

## 5. Накопление истории на агенте

Evaluator ожидает следующие атрибуты на агенте (все опциональны):

```python
agent.affective_history: List[dict]   # список {"valence": f, "arousal": f, ...}
agent.td_error_history: List[float]   # список TD ошибок
agent.cortisol_history: List[float]   # список уровней кортизола
```

Эти атрибуты должны заполняться **самим агентом** в процессе `step()`.  
Evaluator только читает их.

**Рекомендуемый размер истории:** последние 256 шагов (rolling buffer).  
Если история пустая — используется текущее значение как единственная точка.

---

## 6. Константы

```python
FITNESS_VERSION = "1.0"

CRITERIA_ORDER = [
    "longevity",
    "affective_range",
    "prediction_skill",
    "stress_resilience",
    "behavioral_diversity",
    "learning_efficiency",
    "memory_quality",
]

DEFAULT_WEIGHTS = {criterion: 1.0 for criterion in CRITERIA_ORDER}

# Нормировочные константы
AFFECTIVE_RANGE_NORM = 0.5      # max ожидаемое std для [-1,1]
LEARNING_EFFICIENCY_NORM = 3.0  # ожидаемый ratio sleep/online
MEMORY_QUALITY_SAMPLE_LIMIT = 128  # макс опытов для оценки
```

---

## 7. Ограничения реализации

1. `FitnessVector` — `frozen=True`, неизменяемый после создания.
2. Никаких импортов модулей NOWA — только `getattr` на объекте агента.
3. `evaluate()` никогда не вызывает исключений — весь код в try/except с fallback 0.0.
4. `pareto_rank()` — детерминированный при одинаковых данных.
5. Crowding distance для крайних агентов = `float("inf")`.
6. `scalar_score()` возвращает значение в [0.0, 1.0].
7. Python версия: 3.10+
8. Нет numpy — только стандартная библиотека.

---

## 8. Тест-кейсы

### TC-01: evaluate возвращает корректный FitnessVector

```python
# Минимальный mock агента
class MockAgent:
    lived_steps = 500
    expected_lifetime_steps = 1000
    affective_history = [{"valence": 0.3, "arousal": 0.5}] * 10
    td_error_history = [0.1, 0.2, 0.15]
    cortisol_history = [0.05, 0.08, 0.06]
    bg_action_channels = {
        "eat": type("Ch", (), {"selection_count": 5, "get_success_rate": lambda s: 0.8})(),
        "sleep": type("Ch", (), {"selection_count": 3, "get_success_rate": lambda s: 0.9})(),
        "play": type("Ch", (), {"selection_count": 2, "get_success_rate": lambda s: 0.7})(),
    }
    
    class _ValueLayer:
        def snapshot(self):
            return {
                "last_td_error": 0.1,
                "online_update_count": 100,
                "sleep_update_count": 50,
            }
    value_layer = _ValueLayer()
    
    class _Hippocampus:
        experiences = []
    hippocampus = _Hippocampus()
    
    class _Neuromodulators:
        cortisol = 0.07
    neuromodulators = _Neuromodulators()
    
    agent_id = "test_agent"
    genome = type("G", (), {"generation": 2})()

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(MockAgent())

# Все критерии в [0, 1]
for criterion in CRITERIA_ORDER:
    value = getattr(fitness, criterion)
    assert 0.0 <= value <= 1.0, f"{criterion} out of range: {value}"

# longevity = 500/1000 = 0.5
assert abs(fitness.longevity - 0.5) < 1e-6

# agent_id и generation
assert fitness.agent_id == "test_agent"
assert fitness.generation == 2
assert fitness.evaluation_step == 500
```

### TC-02: evaluate с пустым агентом не падает

```python
class EmptyAgent:
    pass

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(EmptyAgent())

assert isinstance(fitness, FitnessVector)
for criterion in CRITERIA_ORDER:
    assert 0.0 <= getattr(fitness, criterion) <= 1.0
```

### TC-03: longevity не превышает 1.0

```python
class LongLivedAgent:
    lived_steps = 99999
    expected_lifetime_steps = 1000

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(LongLivedAgent())
assert fitness.longevity == 1.0
```

### TC-04: behavioral_diversity — равномерное распределение даёт 1.0

```python
class UniformAgent:
    bg_action_channels = {
        f"action_{i}": type("Ch", (), {"selection_count": 10})()
        for i in range(4)
    }

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(UniformAgent())
assert abs(fitness.behavioral_diversity - 1.0) < 1e-6
```

### TC-05: behavioral_diversity — одно действие даёт 0.0

```python
class SingleActionAgent:
    bg_action_channels = {
        "eat": type("Ch", (), {"selection_count": 100})(),
        "sleep": type("Ch", (), {"selection_count": 0})(),
        "play": type("Ch", (), {"selection_count": 0})(),
    }

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(SingleActionAgent())
assert abs(fitness.behavioral_diversity - 0.0) < 1e-6
```

### TC-06: dominates — корректное определение

```python
evaluator = FitnessEvaluator()

a = FitnessVector(
    longevity=0.9, affective_range=0.8, prediction_skill=0.7,
    stress_resilience=0.9, behavioral_diversity=0.8,
    learning_efficiency=0.7, memory_quality=0.8,
    agent_id="a", generation=1, evaluation_step=100,
)
b = FitnessVector(
    longevity=0.8, affective_range=0.7, prediction_skill=0.6,
    stress_resilience=0.8, behavioral_diversity=0.7,
    learning_efficiency=0.6, memory_quality=0.7,
    agent_id="b", generation=1, evaluation_step=100,
)
c = FitnessVector(
    longevity=0.9, affective_range=0.9, prediction_skill=0.5,
    stress_resilience=0.9, behavioral_diversity=0.8,
    learning_efficiency=0.7, memory_quality=0.8,
    agent_id="c", generation=1, evaluation_step=100,
)

assert evaluator.dominates(a, b) is True   # a лучше b по всем критериям
assert evaluator.dominates(b, a) is False  # b хуже a
assert evaluator.dominates(a, c) is False  # a и c несравнимы (c лучше по affective_range)
assert evaluator.dominates(c, a) is False  # c и a несравнимы (a лучше по prediction_skill)
```

### TC-07: dominates — равные векторы не доминируют друг друга

```python
evaluator = FitnessEvaluator()

a = FitnessVector(
    longevity=0.8, affective_range=0.8, prediction_skill=0.8,
    stress_resilience=0.8, behavioral_diversity=0.8,
    learning_efficiency=0.8, memory_quality=0.8,
    agent_id="a", generation=0, evaluation_step=0,
)
b = FitnessVector(
    longevity=0.8, affective_range=0.8, prediction_skill=0.8,
    stress_resilience=0.8, behavioral_diversity=0.8,
    learning_efficiency=0.8, memory_quality=0.8,
    agent_id="b", generation=0, evaluation_step=0,
)

assert evaluator.dominates(a, b) is False
assert evaluator.dominates(b, a) is False
```

### TC-08: pareto_rank — один агент

```python
evaluator = FitnessEvaluator()
fitness = FitnessVector(
    longevity=0.5, affective_range=0.5, prediction_skill=0.5,
    stress_resilience=0.5, behavioral_diversity=0.5,
    learning_efficiency=0.5, memory_quality=0.5,
    agent_id="solo", generation=1, evaluation_step=100,
)

ranks = evaluator.pareto_rank([fitness])

assert len(ranks) == 1
assert ranks[0].rank == 1
assert ranks[0].crowding_distance == float("inf")
```

### TC-09: pareto_rank — явное доминирование

```python
evaluator = FitnessEvaluator()

dominant = FitnessVector(
    longevity=0.9, affective_range=0.9, prediction_skill=0.9,
    stress_resilience=0.9, behavioral_diversity=0.9,
    learning_efficiency=0.9, memory_quality=0.9,
    agent_id="dominant", generation=1, evaluation_step=100,
)
dominated = FitnessVector(
    longevity=0.5, affective_range=0.5, prediction_skill=0.5,
    stress_resilience=0.5, behavioral_diversity=0.5,
    learning_efficiency=0.5, memory_quality=0.5,
    agent_id="dominated", generation=1, evaluation_step=100,
)

ranks = evaluator.pareto_rank([dominant, dominated])

rank_map = {r.agent_id: r.rank for r in ranks}
assert rank_map["dominant"] == 1
assert rank_map["dominated"] == 2
```

### TC-10: pareto_rank — несравнимые агенты в одном фронте

```python
evaluator = FitnessEvaluator()

# A лучше по первым критериям, B лучше по последним
a = FitnessVector(
    longevity=0.9, affective_range=0.9, prediction_skill=0.9,
    stress_resilience=0.1, behavioral_diversity=0.1,
    learning_efficiency=0.1, memory_quality=0.1,
    agent_id="a", generation=1, evaluation_step=100,
)
b = FitnessVector(
    longevity=0.1, affective_range=0.1, prediction_skill=0.1,
    stress_resilience=0.9, behavioral_diversity=0.9,
    learning_efficiency=0.9, memory_quality=0.9,
    agent_id="b", generation=1, evaluation_step=100,
)

ranks = evaluator.pareto_rank([a, b])

rank_map = {r.agent_id: r.rank for r in ranks}
# Оба на фронте — несравнимы
assert rank_map["a"] == 1
assert rank_map["b"] == 1
```

### TC-11: pareto_rank — crowding_distance крайних агентов = inf

```python
evaluator = FitnessEvaluator()

# Три агента на одном фронте с разными значениями по одному критерию
vectors = [
    FitnessVector(longevity=v, affective_range=0.5, prediction_skill=0.5,
                  stress_resilience=0.5, behavioral_diversity=0.5,
                  learning_efficiency=0.5, memory_quality=0.5,
                  agent_id=f"a{i}", generation=0, evaluation_step=0)
    for i, v in enumerate([0.1, 0.5, 0.9])
]

ranks = evaluator.pareto_rank(vectors)

# Крайние (longevity=0.1 и longevity=0.9) имеют inf crowding_distance
crowding = {r.agent_id: r.crowding_distance for r in ranks}
assert crowding["a0"] == float("inf")
assert crowding["a2"] == float("inf")
assert crowding["a1"] < float("inf")
```

### TC-12: scalar_score в [0, 1]

```python
evaluator = FitnessEvaluator()
fitness = FitnessVector(
    longevity=0.7, affective_range=0.6, prediction_skill=0.8,
    stress_resilience=0.9, behavioral_diversity=0.5,
    learning_efficiency=0.4, memory_quality=0.6,
    agent_id="test", generation=1, evaluation_step=50,
)
score = evaluator.scalar_score(fitness)
assert 0.0 <= score <= 1.0
# При равных весах = mean всех критериев
expected = (0.7 + 0.6 + 0.8 + 0.9 + 0.5 + 0.4 + 0.6) / 7
assert abs(score - expected) < 1e-6
```

### TC-13: scalar_score с пользовательскими весами

```python
weights = {
    "longevity": 2.0,
    "affective_range": 1.0,
    "prediction_skill": 1.0,
    "stress_resilience": 1.0,
    "behavioral_diversity": 1.0,
    "learning_efficiency": 1.0,
    "memory_quality": 1.0,
}
evaluator = FitnessEvaluator(weights=weights)
fitness = FitnessVector(
    longevity=1.0, affective_range=0.0, prediction_skill=0.0,
    stress_resilience=0.0, behavioral_diversity=0.0,
    learning_efficiency=0.0, memory_quality=0.0,
    agent_id="test", generation=0, evaluation_step=0,
)
score = evaluator.scalar_score(fitness)
# longevity weight=2 из 8 total = 2/8 = 0.25
assert abs(score - (2.0 / 8.0)) < 1e-6
```

### TC-14: fitness_to_dict / fitness_from_dict round-trip

```python
evaluator = FitnessEvaluator()
original = FitnessVector(
    longevity=0.7, affective_range=0.6, prediction_skill=0.8,
    stress_resilience=0.9, behavioral_diversity=0.5,
    learning_efficiency=0.4, memory_quality=0.6,
    agent_id="agent_42", generation=3, evaluation_step=150,
)

data = evaluator.fitness_to_dict(original)
restored = evaluator.fitness_from_dict(data)

for criterion in CRITERIA_ORDER:
    assert abs(getattr(original, criterion) - getattr(restored, criterion)) < 1e-9

assert restored.agent_id == original.agent_id
assert restored.generation == original.generation
assert restored.evaluation_step == original.evaluation_step
```

### TC-15: evaluate_population сохраняет порядок

```python
class SimpleAgent:
    def __init__(self, steps, agent_id):
        self.lived_steps = steps
        self.expected_lifetime_steps = 1000
        self.agent_id = agent_id

evaluator = FitnessEvaluator()
agents = [SimpleAgent(100 * i, f"agent_{i}") for i in range(5)]
results = evaluator.evaluate_population(agents)

assert len(results) == 5
for i, result in enumerate(results):
    assert result.agent_id == f"agent_{i}"
```

### TC-16: pareto_rank пустой список

```python
evaluator = FitnessEvaluator()
ranks = evaluator.pareto_rank([])
assert ranks == []
```

### TC-17: stress_resilience инвертирует кортизол

```python
class HighCortisolAgent:
    cortisol_history = [0.9] * 20
    class _NM:
        cortisol = 0.9
    neuromodulators = _NM()

class LowCortisolAgent:
    cortisol_history = [0.05] * 20
    class _NM:
        cortisol = 0.05
    neuromodulators = _NM()

evaluator = FitnessEvaluator()
high = evaluator.evaluate(HighCortisolAgent())
low = evaluator.evaluate(LowCortisolAgent())

assert high.stress_resilience < low.stress_resilience
assert high.stress_resilience < 0.2
assert low.stress_resilience > 0.8
```

### TC-18: criteria_names детерминированный порядок

```python
evaluator = FitnessEvaluator()
names = evaluator.criteria_names()

assert names == CRITERIA_ORDER
assert len(names) == 7
```

---

## 9. Примечания для реализующего агента

- `FitnessVector` — `frozen=True` dataclass, все поля клампируются в `__post_init__`
- `pareto_rank()` возвращает список отсортированный по `(rank ASC, -crowding_distance DESC)`
- При вычислении `affective_range`: если `affective_history` непустой — брать std по каждой оси, усреднять по осям. Если пустой — использовать текущие `agent.affective_space.axes` как единственную точку → std=0 → range=0
- `memory_quality`: перебирать не более `MEMORY_QUALITY_SAMPLE_LIMIT` последних опытов
- `behavioral_diversity`: если все `selection_count=0` — entropy=0, diversity=0
- При вычислении crowding distance: если `max == min` по критерию — вклад = 0 для всех агентов по этому критерию (не делить на ноль)
- `fitness_from_dict()` при отсутствующих полях устанавливает 0.0, при `agent_id` отсутствии — пустая строка, `generation` и `evaluation_step` — 0
- Порядок критериев в `CRITERIA_ORDER` используется для детерминированности `pareto_rank()`
