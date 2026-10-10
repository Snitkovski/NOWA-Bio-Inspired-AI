# Specification of Package D — FitnessEvaluator

Russian version: [SPEC_D_FitnessEvaluator.ru.md](SPEC_D_FitnessEvaluator.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Project:** NOWA (an extension of the existing system)  
**File:** `src/fitness.py`  
**Dependencies:** the Python standard library only (`math`, `dataclasses`, `typing`)  
**External dependencies:** none (the agent is passed as an object; data are read through attributes)  
**Specification version:** 1.0

---

## 1. Purpose

`FitnessEvaluator` computes a multi-criterion fitness vector of an agent.  
It is used by `EvolutionLoop` (package F) for selection between generations.

**Key principles:**

- Fitness is a vector, not a scalar. Aggregation is by Pareto dominance.
- Each criterion is normalised to [0.0, 1.0]. Higher is better.
- Evaluation takes place **after the agent's sleep** — consolidation is taken into account.
- The evaluator reads the agent's data through public attributes and methods.
- There are no side effects — evaluation does not alter the agent's state.

---

## 2. Fitness criteria

### 2.1 longevity — length of life

```
longevity = min(1.0, lived_steps / expected_lifetime_steps)
```

An agent that has lived longer without degradation is fitter.  
Source: `agent.lived_steps`, `agent.expected_lifetime_steps`.

### 2.2 affective_range — richness of affective experience

```
affective_range = std(history of affective axes values)
```

An agent with a rich affective history has not become stuck in a single state.  
Normalisation: `std / 0.5` (the maximum expected standard deviation for the [-1, 1] range).  
Source: `agent.affective_space.axes` — snapshots over the lifetime.

**Important:** the evaluator does not store the history — it must accumulate in the agent.  
The agent must have `affective_history: List[dict]` — a list of axis snapshots.  
If the attribute is absent, the criterion is 0.0.

### 2.3 prediction_skill — quality of predictions

```
prediction_skill = 1.0 - mean(abs(td_errors))
```

An agent that predicts consequences well is fitter.  
Normalisation is by a clamp to [0.0, 1.0].  
Source: `agent.value_layer.snapshot()["last_td_error"]` — the current TD error,  
and `td_error_history: List[float]` on the agent if present.

### 2.4 stress_resilience — resilience to stress

```
stress_resilience = 1.0 - mean(cortisol_history)
```

An agent with low chronic cortisol is fitter.  
Normalisation: cortisol lies in [0.0, 1.0] and is inverted.  
Source: `agent.neuromodulators.cortisol` — the current level,  
and `cortisol_history: List[float]` on the agent if present.

### 2.5 behavioral_diversity — diversity of behaviour

```
behavioral_diversity = entropy(action_counts) / log(num_actions)
```

An agent that has not become stuck on a single action is fitter.  
Normalised entropy: 0.0 = one action, 1.0 = a uniform distribution.  
Source: `agent.bg_action_channels` — the `selection_count` of each channel.

### 2.6 learning_efficiency — efficiency of learning

```
learning_efficiency = sleep_update_count / (online_update_count + 1)
normalized = min(1.0, learning_efficiency / 3.0)
```

An agent that consolidates actively during sleep is fitter.  
Source: `agent.value_layer.snapshot()`.

### 2.7 memory_quality — quality of memory

```
memory_quality = mean(consolidation_weight) over hippocampus experiences
```

An agent with high-quality consolidated memories is fitter.  
Source: `agent.hippocampus.experiences` → the `consolidation_weight` attribute of each.

---

## 3. Data structures

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
    agent_id: str               # identifier of the agent
    generation: int             # generation of the agent
    evaluation_step: int        # lived_steps at the moment of evaluation
```

### 3.2 ParetoRank

```python
@dataclass(frozen=True)
class ParetoRank:
    agent_id: str
    rank: int           # 1 = Pareto front, 2 = the next layer, ...
    crowding_distance: float  # for niching within a layer
    fitness: FitnessVector
```

---

## 4. API of the class FitnessEvaluator

### 4.1 Initialisation

```python
@dataclass
class FitnessEvaluator:
    weights: Dict[str, float] = None  # optional weights for scalar aggregation
    
    def __post_init__(self):
        """
        If weights are not supplied, all criteria are equal (1.0 each).
        Normalise the weights so that sum = 1.0.
        """
```

### 4.2 Principal evaluation

```python
def evaluate(self, agent: Any) -> FitnessVector:
    """
    Compute the fitness vector of an agent.
    
    Reads the agent's data through getattr, with a fallback to 0.0/[].
    Never raises — malformed data yield 0.0 on the criterion.
    Does not alter the agent's state.
    
    Arguments:
        agent: a NOWA agent (any object with the required attributes)
    
    Returns: a FitnessVector with every criterion in [0.0, 1.0]
    """

def evaluate_population(self, agents: List[Any]) -> List[FitnessVector]:
    """
    Evaluate a list of agents.
    Returns a list of FitnessVector in the same order.
    """
```

### 4.3 Pareto ranking

```python
def pareto_rank(self, fitness_vectors: List[FitnessVector]) -> List[ParetoRank]:
    """
    Rank agents by Pareto dominance.
    
    NSGA-II algorithm:
        1. Find every non-dominated solution → rank=1 (the Pareto front)
        2. Remove them from the set and repeat → rank=2, ...
        3. Within each rank, compute crowding_distance
    
    Definition of dominance:
        A dominates B if:
            - on every criterion A >= B
            - on at least one criterion A > B
    
    Crowding distance:
        For each criterion, sort the agents.
        Assign distance = infinity to the extremes (min/max).
        For the rest: distance += (next - prev) / (max - min) on each criterion.
    
    Returns: a list of ParetoRank, sorted by (rank, -crowding_distance)
    
    Constraints:
        - an empty list → an empty list
        - one agent → rank=1, crowding_distance=inf
        - when criterion values are equal, the crowding contribution is 0
    """
```

### 4.4 Scalar aggregation (auxiliary)

```python
def scalar_score(self, fitness: FitnessVector) -> float:
    """
    Weighted sum of the criteria.
    Used for a quick comparison when Pareto ranking is excessive.
    
    score = sum(weight[criterion] * value[criterion]) / sum(weights)
    
    Returns: a float in [0.0, 1.0]
    """

def dominates(self, a: FitnessVector, b: FitnessVector) -> bool:
    """
    Returns True if a dominates b.
    Used in pareto_rank and in the tests.
    """
```

### 4.5 Diagnostics

```python
def criteria_names(self) -> List[str]:
    """List of criterion names in a deterministic order."""

def fitness_to_dict(self, fitness: FitnessVector) -> dict:
    """Serialise a FitnessVector to a dictionary."""

def fitness_from_dict(self, data: dict) -> FitnessVector:
    """Restore a FitnessVector from a dictionary. Missing fields are 0.0."""
```

---

## 5. Accumulation of history on the agent

The evaluator expects the following attributes on the agent (all optional):

```python
agent.affective_history: List[dict]   # a list of {"valence": f, "arousal": f, ...}
agent.td_error_history: List[float]   # a list of TD errors
agent.cortisol_history: List[float]   # a list of cortisol levels
```

These attributes must be filled by **the agent itself** during `step()`.  
The evaluator only reads them.

**Recommended history size:** the last 256 steps (a rolling buffer).  
If the history is empty, the current value is used as the single point.

---

## 6. Constants

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

# Normalisation constants
AFFECTIVE_RANGE_NORM = 0.5      # max expected std for [-1, 1]
LEARNING_EFFICIENCY_NORM = 3.0  # expected ratio of sleep to online
MEMORY_QUALITY_SAMPLE_LIMIT = 128  # maximum number of experiences for the evaluation
```

---

## 7. Implementation constraints

1. `FitnessVector` is `frozen=True`, immutable after creation.
2. No imports of NOWA modules — only `getattr` on the agent object.
3. `evaluate()` never raises — all of the code is in try/except with a fallback of 0.0.
4. `pareto_rank()` is deterministic given identical data.
5. The crowding distance of the extreme agents is `float("inf")`.
6. `scalar_score()` returns a value in [0.0, 1.0].
7. Python version: 3.10+.
8. No numpy — the standard library only.

---

## 8. Test cases

### TC-01: evaluate returns a correct FitnessVector

```python
# Minimal mock of an agent
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

# Every criterion is in [0, 1]
for criterion in CRITERIA_ORDER:
    value = getattr(fitness, criterion)
    assert 0.0 <= value <= 1.0, f"{criterion} out of range: {value}"

# longevity = 500/1000 = 0.5
assert abs(fitness.longevity - 0.5) < 1e-6

# agent_id and generation
assert fitness.agent_id == "test_agent"
assert fitness.generation == 2
assert fitness.evaluation_step == 500
```

### TC-02: evaluate with an empty agent does not fail

```python
class EmptyAgent:
    pass

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(EmptyAgent())

assert isinstance(fitness, FitnessVector)
for criterion in CRITERIA_ORDER:
    assert 0.0 <= getattr(fitness, criterion) <= 1.0
```

### TC-03: longevity does not exceed 1.0

```python
class LongLivedAgent:
    lived_steps = 99999
    expected_lifetime_steps = 1000

evaluator = FitnessEvaluator()
fitness = evaluator.evaluate(LongLivedAgent())
assert fitness.longevity == 1.0
```

### TC-04: behavioral_diversity — a uniform distribution yields 1.0

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

### TC-05: behavioral_diversity — a single action yields 0.0

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

### TC-06: dominates — a correct definition

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

assert evaluator.dominates(a, b) is True   # a is better than b on every criterion
assert evaluator.dominates(b, a) is False  # b is worse than a
assert evaluator.dominates(a, c) is False  # a and c are incomparable (c is better on affective_range)
assert evaluator.dominates(c, a) is False  # c and a are incomparable (a is better on prediction_skill)
```

### TC-07: dominates — equal vectors do not dominate each other

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

### TC-08: pareto_rank — one agent

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

### TC-09: pareto_rank — explicit dominance

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

### TC-10: pareto_rank — incomparable agents on one front

```python
evaluator = FitnessEvaluator()

# A is better on the first criteria, B is better on the last
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
# Both are on the front — incomparable
assert rank_map["a"] == 1
assert rank_map["b"] == 1
```

### TC-11: pareto_rank — the crowding_distance of the extreme agents is inf

```python
evaluator = FitnessEvaluator()

# Three agents on one front, with different values on a single criterion
vectors = [
    FitnessVector(longevity=v, affective_range=0.5, prediction_skill=0.5,
                  stress_resilience=0.5, behavioral_diversity=0.5,
                  learning_efficiency=0.5, memory_quality=0.5,
                  agent_id=f"a{i}", generation=0, evaluation_step=0)
    for i, v in enumerate([0.1, 0.5, 0.9])
]

ranks = evaluator.pareto_rank(vectors)

# The extremes (longevity=0.1 and longevity=0.9) have inf crowding_distance
crowding = {r.agent_id: r.crowding_distance for r in ranks}
assert crowding["a0"] == float("inf")
assert crowding["a2"] == float("inf")
assert crowding["a1"] < float("inf")
```

### TC-12: scalar_score lies in [0, 1]

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
# With equal weights this is the mean of all criteria
expected = (0.7 + 0.6 + 0.8 + 0.9 + 0.5 + 0.4 + 0.6) / 7
assert abs(score - expected) < 1e-6
```

### TC-13: scalar_score with custom weights

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
# longevity weight = 2 out of 8 in total = 2/8 = 0.25
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

### TC-15: evaluate_population preserves order

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

### TC-16: pareto_rank of an empty list

```python
evaluator = FitnessEvaluator()
ranks = evaluator.pareto_rank([])
assert ranks == []
```

### TC-17: stress_resilience inverts cortisol

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

### TC-18: criteria_names has a deterministic order

```python
evaluator = FitnessEvaluator()
names = evaluator.criteria_names()

assert names == CRITERIA_ORDER
assert len(names) == 7
```

---

## 9. Notes for the implementing agent

- `FitnessVector` is a `frozen=True` dataclass; every field is clamped in `__post_init__`
- `pareto_rank()` returns a list sorted by `(rank ASC, -crowding_distance DESC)`
- When computing `affective_range`: if `affective_history` is non-empty, take the standard deviation on each axis and average across the axes. If it is empty, use the current `agent.affective_space.axes` as the single point → std = 0 → range = 0
- `memory_quality`: iterate over at most `MEMORY_QUALITY_SAMPLE_LIMIT` of the most recent experiences
- `behavioral_diversity`: if every `selection_count` is 0, entropy = 0 and diversity = 0
- When computing crowding distance: if `max == min` on a criterion, the contribution is 0 for every agent on that criterion (do not divide by zero)
- `fitness_from_dict()`, when fields are missing, sets them to 0.0; when `agent_id` is absent, to the empty string; `generation` and `evaluation_step` to 0
- The order of criteria in `CRITERIA_ORDER` is used so that `pareto_rank()` is deterministic
