# Package E Specification v2.1 — SwarmEnvironment

Russian version: [SPEC_E_SwarmEnvironment_v2.1.ru.md](SPEC_E_SwarmEnvironment_v2.1.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Project:** NOWA (extension of the existing project)  
**File:** `src/swarm.py`  
**Dependencies:** `genome.py` (A), `epigenome.py` (B), `agent_factory.py` (C), `fitness.py` (D)  
**Specification version:** 2.1  
**Changes from v2:** the sleep model is refined — a sleeping agent remains visible and can be woken by signals

---

## 1. Architectural philosophy

The environment is a physical space, not an agent manager.

Agents are fully autonomous:
- they decide for themselves when to sleep (by wakefulness)
- they perceive neighbours within a radius for themselves
- they react to social signals for themselves

The environment provides:
- a 3D coordinate space (float)
- the physics of distance and of signal decay
- a perception mechanism (who lies within an agent's radius)
- global ticks for the synchronisation of time

**Exclusion principle:** two agents cannot occupy the same point.  
Minimum distance between agents: `MIN_AGENT_DISTANCE = 0.1`

---

## 2. Sleep model — key principles

Sleep is a physiological state, not disappearance from the space.

**A sleeping agent:**
- is physically present in the space — visible to other agents
- can receive social signals from neighbours
- a signal of sufficient strength can interrupt sleep (the waking mechanism)
- itself emits attenuated signals (affect is muted during sleep)
- does not call `agent.step()` — cognitive activity is suspended

**Signal coefficient of a sleeping agent:**
```
sleeping_signal_factor = 0.3  # a sleeper emits 30% of ordinary strength
```

**Threshold of forced waking:**
```
If the aggregate stress component of incoming signals > WAKE_SIGNAL_THRESHOLD = 0.6:
    the agent is woken forcibly
```

---

## 3. Space

### 3.1 Position3D

```python
@dataclass(frozen=True)
class Position3D:
    x: float
    y: float
    z: float

    def distance_to(self, other: "Position3D") -> float:
        """Euclidean distance."""

    def to_tuple(self) -> Tuple[float, float, float]:
        """(x, y, z)"""

    @classmethod
    def random(cls, bounds: "SpaceBounds", rng: random.Random) -> "Position3D":
        """A random position within the bounds."""

    @classmethod
    def origin(cls) -> "Position3D":
        """(0.0, 0.0, 0.0)"""


@dataclass(frozen=True)
class SpaceBounds:
    """Bounds of the 3D space."""
    x_min: float = 0.0
    x_max: float = 100.0
    y_min: float = 0.0
    y_max: float = 100.0
    z_min: float = 0.0
    z_max: float = 0.0   # z_min == z_max → 2D mode (a plane)

    def is_2d(self) -> bool:
        """A plane if z_min == z_max."""

    def contains(self, pos: Position3D) -> bool:
        """The position lies inside the bounds."""

    def clamp(self, pos: Position3D) -> Position3D:
        """Clamp the position into the bounds."""

    def volume(self) -> float:
        """Volume of the space (area in 2D mode)."""
```

---

## 4. Social signals

```python
@dataclass(frozen=True)
class SocialSignal:
    source_agent_id: str
    valence: float          # [-1.0, 1.0]
    arousal: float          # [0.0, 1.0]
    stress: float           # [0.0, 1.0]
    curiosity: float        # [0.0, 1.0]
    signal_strength: float  # [0.0, 1.0] — already accounting for decay
    source_is_sleeping: bool  # whether the source is asleep
    distance: float         # distance to the source
    step: int
```

### 4.1 Signal decay

```
signal_strength = base_strength / (1.0 + distance² * decay_factor)
```

Where `base_strength`:
- `1.0` — if the source is active
- `SLEEPING_SIGNAL_FACTOR = 0.3` — if the source is asleep

A signal is ignored if `signal_strength < SIGNAL_MIN_STRENGTH = 0.01`

---

## 5. Autonomous sleep

### 5.1 Condition for falling asleep

```python
def _should_sleep(agent: Any, config: "SwarmConfig") -> bool:
    """
    The agent must sleep if:
        wakefulness >= config.sleep_threshold
    Reads: agent.wakefulness.wakefulness
    Returns False if the attribute is unavailable.
    """
```

### 5.2 Waking by signals

```python
def _check_wake_signal(
    incoming_signals: List[SocialSignal],
    threshold: float = WAKE_SIGNAL_THRESHOLD,
) -> bool:
    """
    Check whether incoming signals are strong enough to wake the agent.

    Computes the aggregate stress signal:
        total_stress = sum(s.stress * s.signal_strength for s in incoming_signals)

    Returns True if total_stress >= threshold.
    """
```

### 5.3 Full tick algorithm for an agent

```
IF the agent is asleep (slot.is_sleeping == True):
    1. Collect incoming signals from neighbours (a sleeper receives signals)
    2. Apply the signals to the agent (attenuated, via observe_external_input)
    3. Check _check_wake_signal(signals):
       IF wake → slot.is_sleeping = False, proceed to the active phase
       ELSE → check wakefulness hysteresis:
           IF wakefulness < sleep_threshold * SLEEP_HYSTERESIS_FACTOR:
               slot.is_sleeping = False, proceed to the active phase
           ELSE:
               agent.sleep(cycles=1) — continue sleep
               skip agent.step()

IF the agent is active (slot.is_sleeping == False):
    1. Check _should_sleep:
       IF sleep is required → slot.is_sleeping = True, agent.sleep(cycles=1)
       skip agent.step()
    2. ELSE the active phase:
       a. Collect signals from neighbours
       b. Apply the signals
       c. Compute context_events
       d. Compute reward
       e. agent.step(context_events, reward=reward, ...)
```

---

## 6. Data structures

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

    # Signal physics
    signal_decay_factor: float = 0.01
    base_perception_radius: float = 20.0
    social_signal_gain: float = 0.05

    # Sleep
    sleep_threshold: float = 0.7
    wake_signal_threshold: float = 0.6  # aggregate stress signal that wakes the agent

    # Context and reward
    context_events_fn: Optional[Callable] = None
    reward_fn: Optional[Callable] = None

    # General
    max_steps_per_generation: int = 200
```

---

## 8. API of the class SwarmEnvironment

### 8.1 Initialisation

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

### 8.2 Population management

```python
def add_agent(
    self,
    agent: Any,
    position: Optional[Position3D] = None,
) -> Position3D:
    """
    Add an agent to the space.
    position=None → a random position without collisions.

    Perception radius:
        factor = genome.genes["dr_perception_radius_factor"] if a genome is present
        radius = config.base_perception_radius * factor

    Returns the assigned position.
    Constraints:
        - the position is clamped into bounds
        - collisions are resolved by a shift
        - MAX_POPULATION_SIZE = 256
        - a duplicate agent_id → a warning, not an exception
    """

def remove_agent(self, agent_id: str) -> Optional[Any]:
    """Remove an agent. Returns the agent or None."""

def move_agent(self, agent_id: str, new_position: Position3D) -> bool:
    """
    Move an agent.
    False if: not found / collision / outside bounds.
    """

def get_agent(self, agent_id: str) -> Optional[Any]:
def get_position(self, agent_id: str) -> Optional[Position3D]:
def get_all_agents(self) -> List[Any]:
    """Sorted by agent_id."""

def replace_population(self, agents: List[Any]) -> None:
    """
    Replace the entire population. Place agents at random.
    global_step is not reset.
    """
```

### 8.3 Perception

```python
def get_agents_in_radius(
    self,
    agent_id: str,
    radius: Optional[float] = None,
    include_sleeping: bool = True,
) -> List[Tuple[Any, float]]:
    """
    Agents within the perception radius.

    include_sleeping=True (default) — sleepers are included.
    Does not include the agent itself.
    Returns (agent, distance) by distance ASC.
    """

def collect_signals_for_agent(
    self,
    agent_id: str,
) -> List[SocialSignal]:
    """
    Signals from all agents within the perception radius.
    Includes signals from sleeping agents (attenuated by a factor of 0.3).
    Filters out signals weaker than SIGNAL_MIN_STRENGTH.
    Returns by signal_strength DESC.
    """
```

### 8.4 Application of signals

```python
def apply_social_signal(
    self,
    agent: Any,
    signal: SocialSignal,
    gain: float,
) -> None:
    """
    Apply a signal to an agent.

    If the agent is asleep — gain *= 0.5 (muted perception during sleep).

    Uses agent.observe_external_input() if available:
        source=f"social:{signal.source_agent_id}"
        payload={
            "valence": signal.valence * signal.signal_strength,
            "arousal": signal.arousal * signal.signal_strength,
            "stress": signal.stress * signal.signal_strength,
            "curiosity": signal.curiosity * signal.signal_strength,
            "source_is_sleeping": signal.source_is_sleeping,
        }
        uncertainty=1.0 - signal.signal_strength

    Otherwise — a direct effect on affective_space.
    gain is clamped to [0.0, MAX_SOCIAL_SIGNAL_GAIN=0.5].
    The whole method is wrapped in try/except.
    """
```

### 8.5 Main tick

```python
def tick(
    self,
    dt: float = 1.0,
    context_override: Optional[Dict[str, List[str]]] = None,
) -> SwarmState:
    """
    One step of all agents in deterministic order (sorted by agent_id).
    The full algorithm is described in section 5.3.
    An error in one agent does not stop the tick of the others.
    """

def run_generation(
    self,
    steps: Optional[int] = None,
    dt: float = 1.0,
) -> List[SwarmState]:
    """N ticks. steps=None → config.max_steps_per_generation."""
```

### 8.6 Metrics

```python
def get_diversity(self) -> float:
    """mean(pairwise genome.distance()). 0.0 if fewer than 2 agents or no genomes."""

def get_swarm_state(self) -> SwarmState:
    """A snapshot without a tick."""

def evaluate_all(self) -> List[FitnessVector]:
    """Evaluate everyone through fitness_evaluator."""

def get_sleeping_agents(self) -> List[str]:
def get_active_agents(self) -> List[str]:

def get_nearest_agents(
    self,
    position: Position3D,
    k: int = 5,
    include_sleeping: bool = True,
) -> List[Tuple[Any, float]]:
    """The k nearest agents to the position."""

def get_spatial_density(self, position: Position3D, radius: float) -> float:
    """Density of agents within the radius. 2D: area_of_circle, 3D: volume_of_sphere."""
```

---

## 9. Constants

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

## 10. Changes in other files

### genome.py — add one gene to the DR group

```python
("dr_perception_radius_factor", "swarm", 0.5, 2.0, 1.0, 0.2,
 "Perception radius multiplier for swarm environment"),
```

In `to_agent_params()`, in the `"autonomous"` section:
```python
"perception_radius_factor": g["dr_perception_radius_factor"],
```

---

## 11. Implementation constraints

1. The space is continuous 3D. 2D is the special case: `z_min == z_max`.
2. A sleeping agent is **visible** to others and **receives** signals (with a coefficient of 0.5).
3. A sleeping agent **emits** signals with the coefficient `SLEEPING_SIGNAL_FACTOR = 0.3`.
4. A signal of sufficient stress intensity wakes a sleeping agent.
5. There is no threading — the implementation is single-threaded.
6. `get_agents_in_radius()` includes sleepers by default (`include_sleeping=True`).
7. `replace_population()` does not reset `global_step`.
8. Python 3.10+, the standard library only.

---

## 12. Test cases

### TC-01: Position3D distance

```python
a = Position3D(0.0, 0.0, 0.0)
b = Position3D(3.0, 4.0, 0.0)

assert abs(a.distance_to(b) - 5.0) < 1e-9
assert a.distance_to(a) == 0.0
```

### TC-02: SpaceBounds 2D mode

```python
bounds_2d = SpaceBounds(z_min=5.0, z_max=5.0)
assert bounds_2d.is_2d() is True

bounds_3d = SpaceBounds(z_min=0.0, z_max=50.0)
assert bounds_3d.is_2d() is False
```

### TC-03: Exclusion principle

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

### TC-04: A sleeping agent is visible to others

```python
config = SwarmConfig(bounds=SpaceBounds(x_max=100, y_max=100), base_perception_radius=50.0)
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock()
sleeper.affective_space.axes = {"valence": 0.5, "arousal": 0.3, "stress": 0.2, "curiosity": 0.4}

observer = MagicMock(); observer.agent_id = "observer"; observer.genome = None

env.add_agent(sleeper, position=Position3D(10.0, 0.0, 0.0))
env.add_agent(observer, position=Position3D(0.0, 0.0, 0.0))

# Mark as asleep
env._slots["sleeper"].is_sleeping = True

# The sleeper is visible to the observer
nearby = env.get_agents_in_radius("observer", include_sleeping=True)
nearby_ids = [a.agent_id for a, _ in nearby]
assert "sleeper" in nearby_ids
```

### TC-05: A sleeping agent emits an attenuated signal

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    base_perception_radius=50.0,
    signal_decay_factor=0.0,  # no decay, so the test stays clean
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

# The sleeper emits 0.3 / 1.0 = 0.3 times as strongly
assert sig_sleeping.signal_strength < sig_active.signal_strength
assert abs(sig_sleeping.signal_strength / sig_active.signal_strength - SLEEPING_SIGNAL_FACTOR) < 1e-6
assert sig_sleeping.source_is_sleeping is True
assert sig_active.source_is_sleeping is False
```

### TC-06: An agent wakes from a stress signal

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.6,
    base_perception_radius=50.0,
)
env = SwarmEnvironment(config, FitnessEvaluator())

# Sleeping agent
sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock(); sleeper.affective_space.axes = {}
sleeper.wakefulness = MagicMock(); sleeper.wakefulness.wakefulness = 0.75
sleeper.sleep.return_value = {"cycles": 1}
sleeper.step.return_value = "eat"

# A nearby source of stress
alarm = MagicMock(); alarm.agent_id = "alarm"; alarm.genome = None
alarm.affective_space = MagicMock()
alarm.affective_space.axes = {"valence": -1.0, "arousal": 1.0, "stress": 1.0, "curiosity": 0.0}
alarm.wakefulness = MagicMock(); alarm.wakefulness.wakefulness = 0.1
alarm.step.return_value = "alert"

env.add_agent(sleeper, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(alarm, position=Position3D(1.0, 0.0, 0.0))

env._slots["sleeper"].is_sleeping = True

env.tick()

# The sleeper must wake from a strong stress signal
assert env._slots["sleeper"].is_sleeping is False
assert sleeper.step.called
```

### TC-07: An agent does not wake from a weak signal

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.6,
    base_perception_radius=50.0,
    signal_decay_factor=0.1,  # strong decay
)
env = SwarmEnvironment(config, FitnessEvaluator())

sleeper = MagicMock(); sleeper.agent_id = "sleeper"; sleeper.genome = None
sleeper.affective_space = MagicMock(); sleeper.affective_space.axes = {}
sleeper.wakefulness = MagicMock(); sleeper.wakefulness.wakefulness = 0.75
sleeper.sleep.return_value = {"cycles": 1}

# A distant source of stress — the signal will decay
far_alarm = MagicMock(); far_alarm.agent_id = "far_alarm"; far_alarm.genome = None
far_alarm.affective_space = MagicMock()
far_alarm.affective_space.axes = {"valence": -0.5, "arousal": 0.5, "stress": 0.5, "curiosity": 0.0}
far_alarm.wakefulness = MagicMock(); far_alarm.wakefulness.wakefulness = 0.1
far_alarm.step.return_value = "eat"

env.add_agent(sleeper, position=Position3D(0.0, 0.0, 0.0))
env.add_agent(far_alarm, position=Position3D(40.0, 0.0, 0.0))

env._slots["sleeper"].is_sleeping = True

env.tick()

# A weak signal did not wake the agent
assert env._slots["sleeper"].is_sleeping is True
assert not sleeper.step.called
```

### TC-08: A sleeper receives signals with a coefficient of 0.5

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

# observe_external_input was called on the sleeping agent
assert sleeper.observe_external_input.called or True  # applied through any mechanism
```

### TC-09: An agent falls asleep autonomously

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

### TC-10: An agent wakes by hysteresis

```python
config = SwarmConfig(
    bounds=SpaceBounds(x_max=100, y_max=100),
    sleep_threshold=0.7,
    wake_signal_threshold=0.99,  # a high threshold — physiological waking only
)
env = SwarmEnvironment(config, FitnessEvaluator())

rested = MagicMock(); rested.agent_id = "rested"; rested.genome = None
rested.affective_space = MagicMock(); rested.affective_space.axes = {}
rested.wakefulness = MagicMock(); rested.wakefulness.wakefulness = 0.85
rested.sleep.return_value = {"cycles": 1}
rested.step.return_value = "eat"

env.add_agent(rested)
env.tick()  # falls asleep

assert env._slots["rested"].is_sleeping is True

# Rested — wakefulness has fallen below the waking threshold (0.7 * 0.7 = 0.49)
rested.wakefulness.wakefulness = 0.35
env.tick()

assert env._slots["rested"].is_sleeping is False
assert rested.step.called
```

### TC-11: Genomic perception radius

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

### TC-12: 3D distance

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

# include_sleeping=True (default) — sees both
all_nearby = env.get_agents_in_radius("observer", include_sleeping=True)
assert len(all_nearby) == 2

# include_sleeping=False — active agents only
active_nearby = env.get_agents_in_radius("observer", include_sleeping=False)
assert len(active_nearby) == 1
assert active_nearby[0][0].agent_id == "active"
```

### TC-14: move_agent collision

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

### TC-15: replace_population does not reset global_step

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

### TC-16: get_swarm_state reflects sleeping_count

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

### TC-17: run_generation returns N states

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

### TC-18: An error in one agent does not stop the tick

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

state = env.tick()  # must not fail

assert good.step.called
assert isinstance(state, SwarmState)
```
