# SwarmEnvironment Implementation Guide (Package E)

Russian version: [SWARM_ENVIRONMENT.ru.md](SWARM_ENVIRONMENT.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 27, 2026.

---

## Scope

`src/swarm.py` implements Package E (`SwarmEnvironment v2.2`) as a physical continuous 3D space for autonomous agents.

The module provides:
1. spatial placement and collision-safe population management
2. local social signaling with distance-based attenuation
3. autonomous sleep/wake transitions with wake-by-stress signaling
4. deterministic per-tick execution and swarm-level diagnostics
5. ecology-driven resource pressure and decentralized reproduction/mortality hooks

---

## Implemented Objects

### Spatial model

1. `Position3D`
2. `SpaceBounds`

Capabilities:
1. Euclidean 3D distance
2. 2D mode via `z_min == z_max`
3. bounds checks and clamping
4. random position generation

### Social signaling model

1. `SocialSignal`
2. attenuation formula:
   `signal_strength = base_strength / (1 + distance^2 * signal_decay_factor)`
3. sleeping source attenuation:
   `SLEEPING_SIGNAL_FACTOR = 0.3`
4. minimum signal filter:
   `SIGNAL_MIN_STRENGTH = 0.01`

### Runtime state structures

1. `AgentSlot`
2. `SwarmState`
3. `SwarmConfig`

### Core environment

`SwarmEnvironment` public API:
1. population lifecycle:
   - `add_agent`, `remove_agent`, `move_agent`, `replace_population`
2. perception and signaling:
   - `get_agents_in_radius`, `collect_signals_for_agent`, `apply_social_signal`
3. runtime loop:
   - `tick`, `run_generation`
4. diagnostics:
   - `get_swarm_state`, `get_diversity`, `evaluate_all`
   - `get_sleeping_agents`, `get_active_agents`
   - `get_nearest_agents`, `get_spatial_density`

### Emergent evolution integration (Package F)

1. ecology and resource pressure:
   - `self.ecology` (`EcologyLayer`)
2. optional offspring factory:
   - `self.factory`
3. lifecycle stats:
   - `births_this_step`, `deaths_this_step`, `total_births`, `total_deaths`
4. internal lifecycle methods:
   - `_update_agent_vitality(...)`
   - `_check_mortality(...)`
   - `_check_reproduction_pairs(...)`
   - `_reproduce(...)`
5. `SwarmState` now includes:
   - `resource_level`
   - `resource_share`
   - `births_this_step`
   - `deaths_this_step`
   - `total_births`
   - `total_deaths`

---

## Sleep/Wake Contract

Implemented semantics from `Docs/SPEC_E_SwarmEnvironment_v2.1.md`:
1. sleeping agents remain spatially present and perceivable
2. sleeping agents still receive social signals
3. sleeping agents emit weakened signals (`0.3x`)
4. wake can be forced by cumulative stress signal
5. if not woken by stress, hysteresis wake uses:
   `wakefulness < sleep_threshold * SLEEP_HYSTERESIS_FACTOR`

Wake signal helper:
1. `_check_wake_signal(...)` computes:
   `sum(signal.stress * signal.signal_strength)`
2. threshold is configurable (`SwarmConfig.wake_signal_threshold`, default `0.6`)

---

## Default Context Events

If `SwarmConfig.context_events_fn` is not provided, the environment now uses a default context builder so `agent.step(...)` still receives physiological context.

Default events include:
1. activity state:
   - `agent_active` or `agent_sleeping`
2. wakefulness bucket:
   - `wakefulness_high`
   - `wakefulness_mid`
   - `wakefulness_low`
3. social-state context (when incoming signals exist):
   - `social_signal_present`
   - `social_sleeping_neighbor`
   - `social_stress_high` (when cumulative stress exceeds wake threshold)

---

## Genome Integration

`src/genome.py` includes swarm-specific gene:
1. `dr_perception_radius_factor` (range `0.5..2.0`, default `1.0`)

`GenomeVector.to_agent_params()` now exports:
1. `autonomous.perception_radius_factor`

`SwarmEnvironment.add_agent(...)` uses this gene to scale:
1. `perception_radius = base_perception_radius * dr_perception_radius_factor`

---

## Test Coverage

Primary suite:
1. `tests/test_swarm_environment.py`
2. `tests/test_emergent_evolution_v2.py` (integration scenarios touching swarm lifecycle)

Coverage includes:
1. TC-01..TC-18 from `Docs/SPEC_E_SwarmEnvironment_v2.1.md`
2. default-context fallback (`wakefulness_high/low` events when no custom context fn)
3. failure isolation (one failing agent does not stop global tick)
4. emergent evolution lifecycle checks (resource consumption, mortality removal, decentralized reproduction)

Latest local run:

```text
python -m pytest tests/test_swarm_environment.py -q
20 passed, 1 warning

python -m pytest tests/test_emergent_evolution_v2.py -q
20 passed in 0.08s
```

Project-wide regression (excluding Demo):

```text
python -m pytest tests -q
723 passed, 3 skipped
```
