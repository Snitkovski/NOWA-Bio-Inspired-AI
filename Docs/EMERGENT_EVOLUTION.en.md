# Emergent Evolution Implementation Guide (Package F)

Russian version: [EMERGENT_EVOLUTION.ru.md](EMERGENT_EVOLUTION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 27, 2026.

---

## Scope

Package F introduces decentralized emergent evolution on top of existing Packages A–E. There is no global evolution orchestrator: each agent updates local vitality and reproduction systems, and the environment only mediates resources, mortality checks, and birth events.

Implemented modules:
1. `src/reproduction.py`
2. `src/mortality.py`
3. `src/ecology.py`
4. `src/population_observer.py`

---

## Core Components

### `ReproductiveSystem` (`src/reproduction.py`)

1. Maintains an autonomous `reproductive_drive` with an age gate and a cooldown.
2. Uses local state signals:
   - energy
   - valence
   - cortisol
   - lived steps
   - resource share
3. Provides:
   - `update(...)`
   - `is_ready()`
   - `register_reproduction(...)`
   - `snapshot()`, `to_dict()`, `from_dict()`
4. Includes a pure compatibility function:
   - `compute_compatibility(snapshot_a, snapshot_b)`

### `MortalitySystem` (`src/mortality.py`)

1. Tracks age-based senescence and an irreversible death state.
2. Death priorities:
   - exhaustion
   - sleep deprivation
   - old age
   - senescence
3. Provides:
   - `update(...) -> bool`
   - `is_dead()`
   - `get_age_fraction(...)`
   - `snapshot()`, `to_dict()`, `from_dict()`

### `EcologyLayer` (`src/ecology.py`)

1. Maintains a finite shared resource pool.
2. Computes per-agent resource pressure via:
   - `compute_resource_share(agent_count)`
3. Updates the pool per tick via:
   - `consume(agent_count)`

### `PopulationObserver` (`src/population_observer.py`)

1. A passive observer (read-only, no control decisions).
2. Produces a history of `PopulationSnapshot` with:
   - population size and diversity
   - vitality, drive, and age aggregates
   - birth and death counters
   - the current resource level and share
   - optional mean-fitness aggregation
3. Supports:
   - `observe()`
   - `save(path)`
   - `load(path, environment)`

---

## Integration Points

### Genome (Package A)

`src/genome.py`:
1. Added the gene `lt_max_lifespan_factor` (group `LT`).
2. Added `mortality.max_lifespan_factor` in `GenomeVector.to_agent_params()`.

### AgentFactory (Package C)

`src/agent_factory.py`:
1. `AgentConfig` now includes `base_lifespan_steps`.
2. `spawn(...)` now attaches:
   - `agent.reproductive_system = ReproductiveSystem(...)`
   - `agent.mortality_system = MortalitySystem(...)`
3. Lifespan is computed from:
   - `base_lifespan_steps * genome.genes["lt_max_lifespan_factor"]`

### SwarmEnvironment (Package E)

`src/swarm.py`:
1. `SwarmConfig` is extended with ecology and reproduction fields.
2. `SwarmState` is extended with resource and birth/death statistics.
3. `SwarmEnvironment` now includes:
   - `ecology`
   - an optional `factory`
   - `births_this_step`, `deaths_this_step`, `total_births`, `total_deaths`
4. New internal lifecycle methods:
   - `_update_agent_vitality(...)`
   - `_check_mortality(...)`
   - `_check_reproduction_pairs(...)`
   - `_reproduce(...)`

---

## Test Coverage

Primary Package F suite:
1. `tests/test_emergent_evolution_v2.py`

Focused checks:
1. reproduction dynamics and compatibility
2. mortality causes and senescence
3. ecological resource pressure
4. swarm integration (birth, death, and resource updates)
5. passive observer behaviour and persistence

Latest runs (excluding Demo):

```text
python -m pytest tests/test_emergent_evolution_v2.py -q
20 passed in 0.08s

python -m pytest tests -q
723 passed, 3 skipped
```
