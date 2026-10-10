# AgentFactory Implementation Guide (Package C)

Russian version: [AGENT_FACTORY.ru.md](AGENT_FACTORY.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 27, 2026.

---

## Scope

`src/agent_factory.py` implements a single-entry factory for creating NOWA agents in evolutionary workflows.

Key goals:
1. construct a fully initialized `Agent` from `GenomeVector`
2. optionally inject inherited memory from `EpigenomeSnapshot`
3. support parent-based offspring generation (`spawn_child`)
4. provide robust extraction APIs (`extract_genome`, `extract_epigenome`)
5. keep agent creation resilient (invalid payloads never crash factory paths)

---

## Implemented Objects

### `AgentConfig`

Environment-level configuration:
- `actions`
- `hippocampus_capacity`
- `cortex_capacity`
- `sleep_cycles_default`
- `intent_memory_enabled`
- `environment_id`
- `base_lifespan_steps`

### `AgentFactory`

Core public methods:
- `spawn(genome, epigenome=None, epigenome_noise=0.1, rng=None, agent_id="")`
- `spawn_random(rng=None, agent_id="")`
- `spawn_default(agent_id="")`
- `spawn_child(parent_a, parent_b, ..., rng=None, agent_id="")`
- `extract_genome(agent)`
- `extract_epigenome(agent, ..., min_confirmation=1.0)`

---

## Spawn Behavior

`spawn(...)` sequence:
1. resolve genome (`GenomeVector` fallback to `GenomeVector.default()`)
2. expand params via `genome.to_agent_params()`
3. build modules (`hippocampus`, `cortex`, `selector`, `sleep_manager`, `wakefulness`)
4. construct `Agent`
5. apply post-init genome overrides to runtime modules
6. attach factory metadata:
   - `agent.genome`
   - `agent.epigenome`
   - `agent.agent_id`
   - `agent.lineage_id`
   - `agent.factory_config`
7. attach evolution subsystems:
   - `agent.reproductive_system`
   - `agent.mortality_system`
   - `agent.expected_lifetime_steps` (derived from genome lifespan factor)
8. if epigenome is provided, run safe pre-step injection

Safety constraints:
1. `epigenome_noise` is clamped to `[0.0, 1.0]`
2. invalid epigenome payload never crashes spawn
3. per-parameter application failures emit `warnings.warn(...)` and continue

---

## Child Generation

`spawn_child(...)` behavior:
1. extracts genomes from both parents (with reconstruction fallback)
2. crossover (`arithmetic` / `uniform` / `sbx`) with clamped args
3. keeps one child genome
4. applies mutation with clamped `mutation_rate` and `sigma_scale`
5. optionally blends parent epigenomes
6. delegates final creation to `spawn(...)`

Fallback behavior:
1. parent without valid `genome` → reconstructed or default genome path
2. parent without valid `epigenome` → `EpigenomeSnapshot.empty()`
3. invalid crossover mode → arithmetic fallback

---

## Extraction and Round-Trip

### `extract_genome(agent)`

1. returns `agent.genome` when present and valid
2. otherwise reconstructs from live module parameters

### `_reconstruct_genome(agent)`

Rebuilds genes from:
- neuromodulator interaction matrix and ACC parameters
- affective-space decay and regulation parameters
- wakefulness and circadian rates
- autonomous runtime drives, thresholds, and energy
- value layer and TD parameters
- hippocampus and sleep thresholds
- imagination parameters

The neuromodulator matrix convention is explicit and shared by the write and read paths:
- the matrix is used as `W[target][source]`
- one mapping table is used in both:
  - `_apply_neuromodulator_overrides(...)`
  - `_reconstruct_genome(...)`

This prevents index-convention drift in genome → agent → genome round-trips.

### `extract_epigenome(agent)`

Uses public module state to build dictionaries and delegates to:
- `EpigenomeSnapshot.extract(...)`

Sources:
- `agent.cortex` patterns
- `agent.selector.action_metadata`
- `agent.value_layer.expectation_memory`

---

## Test Coverage

Primary suite:
- `tests/test_agent_factory.py`

Coverage:
- TC-01..TC-16 from `Docs/SPEC_C_AgentFactory.md`
- an additional round-trip consistency test for neuromodulator matrix mapping
- Package F integration checks for reproduction and mortality subsystem attachment

Latest local run:

```text
python -m pytest tests/test_agent_factory.py -q
19 passed in 0.26s
```

Project-wide regression (excluding Demo):

```text
python -m pytest tests -q
723 passed, 3 skipped
```
