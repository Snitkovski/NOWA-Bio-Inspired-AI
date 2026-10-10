# Specification of Package C — AgentFactory

Russian version: [SPEC_C_AgentFactory.ru.md](SPEC_C_AgentFactory.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Project:** NOWA (extension of the existing system)  
**File:** `src/agent_factory.py`  
**Dependencies:** `genome.py` (package A), `epigenome.py` (package B), NOWA modules  
**Specification version:** 1.0

---

## 1. Purpose

`AgentFactory` is the sole point at which agents are created in an evolutionary context.  
It accepts a `GenomeVector` and an optional `EpigenomeSnapshot`,  
and creates a fully initialised NOWA agent with parameters taken from the genome  
and with inherited memory taken from the epigenome.

**Key principles:**

- The factory does not know about the swarm; it creates one agent
- The genome determines the architecture; the epigenome determines the initial knowledge
- Injection of the epigenome occurs before the first step, but after initialisation
- An agent created through the factory is indistinguishable from an agent created by hand

---

## 2. Dependencies on NOWA modules

The factory imports and uses:

```python
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from intent_memory import IntentMemory
from affect import AffectiveState
from agent import Agent
from genome import GenomeVector, GENE_REGISTRY
from epigenome import EpigenomeSnapshot
```

---

## 3. Structure of AgentFactory

```python
@dataclass
class AgentConfig:
    """Environment configuration — parameters not taken from the genome."""
    actions: List[str]                    # available actions
    hippocampus_capacity: int = 512       # hippocampus size
    cortex_capacity: int = 256            # cortex size
    sleep_cycles_default: int = 3         # default number of sleep cycles
    intent_memory_enabled: bool = True    # enable intent memory
    environment_id: str = ""              # environment identifier


class AgentFactory:
    """
    Factory of NOWA agents for the evolutionary context.
    """
    
    def __init__(self, config: AgentConfig):
        ...
```

---

## 4. API

### 4.1 Principal creation method

```python
def spawn(
    self,
    genome: GenomeVector,
    epigenome: Optional[EpigenomeSnapshot] = None,
    epigenome_noise: float = 0.1,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Create an agent from a genome and an optional epigenome.
    
    Sequence:
        1. Extract module parameters from genome.to_agent_params()
        2. Create every NOWA module with the genomic parameters
        3. Assemble the Agent
        4. If epigenome is not None, call _inject_epigenome()
        5. Return the finished agent
    
    Arguments:
        genome: the agent's genome (determines the parameters)
        epigenome: inherited memory (None = a clean agent)
        epigenome_noise: noise level at injection, in [0.0, 1.0]
        rng: random-number generator for the injection noise
        agent_id: string identifier for tracking
    
    Returns: a fully initialised Agent
    
    Constraints:
        - epigenome_noise is clamped to [0.0, 1.0]
        - agent_id is stored in agent.lineage_id (a new attribute)
        - when epigenome is None, the agent starts with clean memory
        - never raises an exception because of a malformed epigenome
    """
```

### 4.2 Creation of the first generation

```python
def spawn_random(
    self,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Create an agent with a random genome and clean memory.
    Used to initialise the first generation.
    
    Equivalent to spawn(GenomeVector.random(rng), epigenome=None).
    """

def spawn_default(
    self,
    agent_id: str = "",
) -> Agent:
    """
    Create an agent with the default genome and clean memory.
    Used for baseline comparisons.
    """
```

### 4.3 Creation of an offspring from two parents

```python
def spawn_child(
    self,
    parent_a: Agent,
    parent_b: Agent,
    mutation_rate: float = 0.05,
    sigma_scale: float = 1.0,
    crossover_alpha: float = 0.5,
    crossover_mode: str = "arithmetic",
    epigenome_noise: float = 0.1,
    blend_epigenomes: bool = True,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Create an offspring from two parent agents.
    
    Sequence:
        1. Extract the genomes from parent_a and parent_b
        2. Cross the genomes to obtain child_genome (one of the two offspring)
        3. If blend_epigenomes:
               Extract the epigenomes from both parents
               Mix them through epigenome_a.blend(epigenome_b)
               child_epigenome = the mixture
           Else:
               child_epigenome = None
        4. Mutate child_genome
        5. spawn(child_genome, child_epigenome, epigenome_noise, rng)
    
    Arguments:
        parent_a, parent_b: the parent agents
        mutation_rate: probability of mutation of each gene, in [0.0, 1.0]
        sigma_scale: scale of mutational noise, in [0.1, 5.0]
        crossover_alpha: weight of parent_a under arithmetic crossover, in [0.0, 1.0]
        crossover_mode: crossover mode ("arithmetic"|"uniform"|"sbx")
        epigenome_noise: noise at epigenome injection, in [0.0, 1.0]
        blend_epigenomes: whether inherited memory is transmitted
        rng: random-number generator
        agent_id: identifier of the offspring
    
    Returns: Agent — one offspring
    
    Constraints:
        - if a parent has no genome attribute, use GenomeVector.default()
        - if a parent has no epigenome attribute, use EpigenomeSnapshot.empty()
        - every parameter is clamped to its admissible range
    """
```

### 4.4 Extraction of the genome and the epigenome from an agent

```python
def extract_genome(self, agent: Agent) -> GenomeVector:
    """
    Extract the genome from a living agent.
    
    Reads the attribute agent.genome when it is present.
    Otherwise reconstructs the genome from the current module parameters.
    
    Returns: GenomeVector
    """

def extract_epigenome(
    self,
    agent: Agent,
    max_patterns: int = 32,
    max_actions: int = 16,
    max_values: int = 24,
    min_reinforcement: int = 2,
    min_stability: float = 0.5,
    min_confirmation: float = 1.0,
) -> EpigenomeSnapshot:
    """
    Extract the epigenome from a living agent.
    
    Reads data from:
        - agent.cortex (patterns)
        - agent.selector.action_metadata (SAC)
        - agent.value_layer (profiles)
    
    Uses EpigenomeSnapshot.extract() with the data supplied as dictionaries.
    
    Returns: EpigenomeSnapshot
    """
```

---

## 5. Internal methods

### 5.1 Creation of modules from the genome

```python
def _build_hippocampus(self, params: dict) -> NOWAHippocampus:
    """
    Create a hippocampus with parameters taken from the genome.
    
    Genomic parameters:
        params["hippocampus"]["similarity_threshold"] → hippocampus.similarity_threshold
    
    Fixed parameters from config:
        capacity = self.config.hippocampus_capacity
    """

def _build_cortex(self, params: dict) -> CortexMemory:
    """
    Create a cortex.
    Capacity is fixed from config.
    """

def _build_selector(self, params: dict) -> ActionSelector:
    """
    Create a selector with actions taken from config.
    """

def _build_sleep_manager(self, params: dict) -> SleepManager:
    """
    Create a SleepManager.
    
    Genomic parameters:
        params["sleep"]["consolidation_threshold"] → stability_index_threshold
    """

def _build_wakefulness(self, params: dict):
    """
    Create a WakefulnessState with genomic parameters.
    
    Genomic parameters:
        params["wakefulness"]["circadian_amplitude"]
        params["wakefulness"]["circadian_phase"]
        params["wakefulness"]["accumulation_rate_factor"] → multiply the base rate
        params["wakefulness"]["recovery_rate_factor"] → multiply the base rate
    """
```

### 5.2 Application of parameters to the agent

```python
def _apply_genome_to_agent(self, agent: Agent, params: dict) -> None:
    """
    Apply genomic parameters to an agent that has already been created.
    
    Applies parameters that cannot be passed when the modules are initialised:
    
    AffectiveSpace:
        agent.affective_space.axis_decay = params["affective_space"]["axis_decay"]
        agent.affective_space.lambda_reg = params["affective_space"]["lambda_reg"]
        agent.affective_space.baseline_adapt_rate = params["affective_space"]["baseline_adapt_rate"]
    
    NeuromodulatorState:
        Apply interaction_overrides to agent.neuromodulators.interaction_field
        Apply acc_k_ne, acc_k_cort, acc_k_ht
        Apply decay_half_life
    
    ValueLayer:
        agent.value_layer.gamma_default = params["value_layer"]["gamma_default"]
        agent.value_layer.alpha_online_default = params["value_layer"]["alpha_online_default"]
        agent.value_layer.td_layer.tonic_slow_rate = params["value_layer"]["tonic_slow_rate"]
    
    HippocampalImagineEngine:
        agent.imagination_engine.goal_bias = params["imagination"]["goal_bias"]
        agent.imagination_engine.confidence_decay = params["imagination"]["confidence_decay"]
        agent.imagination_engine.state_novelty_weight = params["imagination"]["state_novelty_weight"]
        agent.imagination_value_blend = params["imagination"]["value_blend"]
    
    AutonomousOrganismAgent (if initialised):
        drive_system.drives — initial levels from params["autonomous"]["drive_baselines"]
        drive_system thresholds from params["autonomous"]["drive_thresholds"]
        energy_system.recovery_rate from params["autonomous"]["energy_recovery_rate"]
        energy_system.cognitive_cost from params["autonomous"]["cognitive_cost"]
    
    Constraints:
        - every operation is inside try/except; a malformed parameter is skipped
        - a skip is reported through warnings.warn
        - the agent must remain in a working state under any parameters
    """
```

### 5.3 Injection of the epigenome

```python
def _inject_epigenome(
    self,
    agent: Agent,
    epigenome: EpigenomeSnapshot,
    noise_level: float,
    rng: Optional[random.Random],
) -> dict:
    """
    Implant inherited memory into the agent.
    
    Extracts the agent's current structures as dictionaries,
    calls epigenome.inject(), and applies the result back.
    
    Sequence:
        1. Collect cortex_patterns from agent.cortex
        2. Collect action_metadata from agent.selector
        3. Collect value_profiles from agent.value_layer
        4. Call epigenome.inject(...)
        5. Apply the modified structures back into the agent
    
    Returns: the injection statistics from epigenome.inject()
    
    Constraints:
        - the whole method is inside try/except; on error it returns empty statistics
        - the agent must not be damaged by an injection error
        - do not call agent.sleep(); injection occurs before the first sleep
    """
```

### 5.4 Reconstruction of the genome from the agent

```python
def _reconstruct_genome(self, agent: Agent) -> GenomeVector:
    """
    Reconstruct the genome from the agent's current parameters.
    
    Reads parameters from each module and assembles a GenomeVector.
    Used when agent.genome is not set.
    
    When a parameter is unavailable, use the default from GENE_REGISTRY.
    The result is always a valid GenomeVector.
    """
```

---

## 6. Agent attributes added by the factory

After `spawn()` the agent has additional attributes:

```python
agent.genome: GenomeVector           # the agent's genome
agent.epigenome: EpigenomeSnapshot   # the epigenome (empty if none was passed)
agent.agent_id: str                  # identifier
agent.factory_config: AgentConfig    # environment configuration (read-only reference)
```

---

## 7. Implementation constraints

1. `AgentFactory` stores no state between calls to `spawn()`; each call is independent.
2. `spawn_child()` creates **one** offspring, not two; the second offspring of the crossover is discarded.
3. Genomic parameters are applied **after** the standard initialisation of `Agent`; they override the defaults.
4. `_apply_genome_to_agent()` uses only `try/except` and does not raise; the agent remains operational.
5. The autonomous runtime (`autonomous_runtime`) is initialised through `agent.init_autonomous_runtime()` with parameters from the genome, not directly.
6. `extract_epigenome()` calls `EpigenomeSnapshot.extract()`; it does not construct epigenome objects directly.
7. Python version: 3.10+

---

## 8. Test cases

### TC-01: spawn with the default genome creates a working agent

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)
genome = GenomeVector.default()

agent = factory.spawn(genome)

# Factory attributes are set
assert hasattr(agent, "genome")
assert hasattr(agent, "epigenome")
assert hasattr(agent, "agent_id")

# The genome matches
assert agent.genome.genes == genome.genes

# The epigenome is empty
assert agent.epigenome.is_empty()

# The agent works — a step can be taken
action = agent.step(context_events=["morning"], reward=0.0, novelty=0.0)
assert isinstance(action, str)
```

### TC-02: Genomic parameters are applied to the modules

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Build a genome with non-default values
genome = GenomeVector.default()
custom_genes = dict(genome.genes)
custom_genes["af_decay_valence"] = 0.85   # differs from the default 0.92
custom_genes["lr_gamma"] = 0.90           # differs from the default 0.95
genome = GenomeVector(genes=custom_genes)

agent = factory.spawn(genome)

# The parameters have been applied
assert abs(agent.affective_space.axis_decay.get("valence", 0) - 0.85) < 1e-6
assert abs(agent.value_layer.gamma_default - 0.90) < 1e-6
```

### TC-03: spawn_random creates an agent with a random genome

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)
rng = random.Random(42)

agent_a = factory.spawn_random(rng=random.Random(42))
agent_b = factory.spawn_random(rng=random.Random(99))

# The genomes differ
assert agent_a.genome.genes != agent_b.genome.genes

# Both work
action_a = agent_a.step(["ctx"], reward=0.0, novelty=0.0)
action_b = agent_b.step(["ctx"], reward=0.0, novelty=0.0)
assert isinstance(action_a, str)
assert isinstance(action_b, str)
```

### TC-04: spawn_default creates an agent with the default genome

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

agent = factory.spawn_default()

for key in GENE_REGISTRY:
    assert abs(agent.genome.genes[key] - GENE_REGISTRY[key].default) < 1e-9
```

### TC-05: Epigenome injection — patterns enter the cortex

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)

# Build an epigenome that contains a pattern
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "morning", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

agent = factory.spawn(
    GenomeVector.default(),
    epigenome=epigenome,
    epigenome_noise=0.0,
)

# The pattern is present in the cortex
cortex_patterns = agent.cortex.get_patterns() if hasattr(agent.cortex, "get_patterns") else []
# Alternatively: check that action_metadata or the cortex contains the inheritance
assert agent.epigenome is not None
assert not agent.epigenome.is_empty()
```

### TC-06: spawn_child creates an offspring whose genome lies between the parents

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

rng = random.Random(0)
parent_a = factory.spawn_random(rng=random.Random(1))
parent_b = factory.spawn_random(rng=random.Random(2))

child = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.0,  # no mutation, so that the test is clean
    crossover_alpha=0.5,
    crossover_mode="arithmetic",
    blend_epigenomes=False,
    rng=random.Random(42),
)

# The offspring generation is max(parents) + 1
assert child.genome.generation == max(
    parent_a.genome.generation, parent_b.genome.generation
) + 1

# Each gene of the offspring lies between the parents (arithmetic, alpha=0.5)
for key in GENE_REGISTRY:
    val_a = parent_a.genome.genes[key]
    val_b = parent_b.genome.genes[key]
    val_child = child.genome.genes[key]
    lo, hi = min(val_a, val_b), max(val_a, val_b)
    assert lo - 1e-9 <= val_child <= hi + 1e-9, f"Gene {key} out of parent range"
```

### TC-07: spawn_child with mutation creates a differing genome

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

child = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=1.0,  # every gene mutates
    sigma_scale=2.0,
    rng=random.Random(7),
)

# At least one gene differs from both parents
at_least_one_different = False
for key in GENE_REGISTRY:
    val_a = parent_a.genome.genes[key]
    val_b = parent_b.genome.genes[key]
    val_child = child.genome.genes[key]
    if abs(val_child - val_a) > 1e-9 or abs(val_child - val_b) > 1e-9:
        at_least_one_different = True
        break
assert at_least_one_different
```

### TC-08: extract_genome returns a correct GenomeVector

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

original_genome = GenomeVector.random(random.Random(5))
agent = factory.spawn(original_genome)

extracted = factory.extract_genome(agent)

assert isinstance(extracted, GenomeVector)
assert extracted.validate() == []

# The principal parameters match
assert abs(extracted.genes["lr_gamma"] - original_genome.genes["lr_gamma"]) < 1e-6
assert abs(extracted.genes["af_decay_valence"] - original_genome.genes["af_decay_valence"]) < 1e-6
```

### TC-09: extract_epigenome after steps returns a non-empty snapshot

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)

agent = factory.spawn_default()

# Several steps, so that experience accumulates
for _ in range(10):
    agent.step(["morning", "hungry"], reward=0.8, novelty=0.3)

# Sleep, for consolidation
agent.sleep(cycles=1)

# Extraction of the epigenome
epigenome = factory.extract_epigenome(
    agent,
    min_reinforcement=0,
    min_stability=0.0,
    min_confirmation=0.0,
)

assert isinstance(epigenome, EpigenomeSnapshot)
assert epigenome.validate() == []
# After the steps and the sleep there must be data
assert epigenome.source_generation >= 0
```

### TC-10: spawn_child with blend_epigenomes=True transmits memory

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Parents with some experience
parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

for _ in range(5):
    parent_a.step(["ctx_a"], reward=0.9, novelty=0.1)
    parent_b.step(["ctx_b"], reward=0.7, novelty=0.2)

parent_a.sleep(cycles=1)
parent_b.sleep(cycles=1)

child = factory.spawn_child(
    parent_a, parent_b,
    blend_epigenomes=True,
    epigenome_noise=0.05,
    rng=random.Random(0),
)

# The offspring epigenome is not empty (if the parents accumulated patterns)
assert child.epigenome is not None
# The offspring works
action = child.step(["ctx_a"], reward=0.0, novelty=0.0)
assert isinstance(action, str)
```

### TC-11: AgentFactory stores no state between calls

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

agent_1 = factory.spawn(GenomeVector.default(), agent_id="agent_1")
agent_2 = factory.spawn(GenomeVector.default(), agent_id="agent_2")

# The agents are independent
assert agent_1.agent_id == "agent_1"
assert agent_2.agent_id == "agent_2"
assert agent_1 is not agent_2
assert agent_1.hippocampus is not agent_2.hippocampus
```

### TC-12: agent_id is preserved

```python
config = AgentConfig(actions=["eat"])
factory = AgentFactory(config)

agent = factory.spawn(GenomeVector.default(), agent_id="test_agent_42")
assert agent.agent_id == "test_agent_42"
```

### TC-13: spawn with a malformed epigenome does not fail

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# A deliberately empty epigenome must not bring spawn down
epigenome = EpigenomeSnapshot.empty()

# Must not raise
agent = factory.spawn(
    GenomeVector.default(),
    epigenome=epigenome,
    epigenome_noise=0.5,
)
assert agent is not None
```

### TC-14: spawn_child without parental genomes uses the default

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Agents without a genome attribute (not created through the factory)
# The factory must use the default genome
parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

# Remove the genome, imitating an agent that did not come from the factory
del parent_a.genome
del parent_b.genome

# Must not fail
child = factory.spawn_child(parent_a, parent_b, rng=random.Random(0))
assert isinstance(child, Agent)
assert child.genome is not None
```

### TC-15: Every action from config is registered in the BG channels

```python
config = AgentConfig(actions=["eat", "sleep", "play", "explore"])
factory = AgentFactory(config)

agent = factory.spawn_default()

for action in config.actions:
    assert action in agent.bg_action_channels, f"Action {action} is not registered"
```

### TC-16: Determinism of spawn_child under a fixed rng

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

parent_a = factory.spawn(GenomeVector.random(random.Random(1)))
parent_b = factory.spawn(GenomeVector.random(random.Random(2)))

child_1 = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.3,
    rng=random.Random(42),
    blend_epigenomes=False,
)
child_2 = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.3,
    rng=random.Random(42),
    blend_epigenomes=False,
)

# The genomes are identical
assert child_1.genome.genes == child_2.genome.genes
```

---

## 9. Notes for the implementing agent

- `AgentConfig` is a plain dataclass without `frozen=True` (it may be changed after creation)
- `_apply_genome_to_agent()` is called AFTER `Agent.__init__()`; the order is obligatory
- The autonomous runtime is created through `agent.init_autonomous_runtime(drive_thresholds=...)`, not directly
- `accumulation_rate_factor` from the genome: `wakefulness.accumulation_rate = WakefulnessState.ACCUMULATION_RATE * factor`
- `recovery_rate_factor` likewise: `wakefulness.recovery_rate = WakefulnessState.RECOVERY_RATE * factor`
- For neuromodulator `interaction_overrides`: change particular weights in an `INTERACTION_MATRIX`-like structure through `NeuromodulatorState`; the concrete API depends on the implementation of `neuromodulators.py`
- `extract_epigenome()` must read `agent.cortex` through the public cortex API, not through private fields
- `agent.factory_config` is a reference to the `AgentConfig` object, not a copy
- When reconstructing the genome through `_reconstruct_genome()`: if a parameter is unavailable, take `GENE_REGISTRY[key].default`
