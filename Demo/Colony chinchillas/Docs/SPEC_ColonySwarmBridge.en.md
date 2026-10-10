# SPEC: Colony Swarm Bridge (Current Implementation)

Russian version: [SPEC_ColonySwarmBridge.ru.md](SPEC_ColonySwarmBridge.ru.md)

## Abstract

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

This specification describes the current implementation of `ColonySwarmBridge`, which connects `SimulationRunner` to the NOWA swarm environment `SwarmEnvironment`. The bridge aligns string zone positions of agents with three-dimensional swarm coordinates, updates social signals, detects mortality and frees the slots of the dead, checks reproductive compatibility when a factory is present, and recomputes the ecology and resource share.

The document states the order of calls inside the runner tick. Synchronisation of positions and signals precedes the agent step; a second synchronisation and the mortality check follow it, after which reproduction, the appearance of offspring, and ecology are processed. Placement in zones is deterministic, overflow is offset without divergence between runs, and coordinates are clamped to the cage bounds. The bridge does not execute an individual's step and does not assign action policy.

The scientific role of the bridge in the installation is to keep the spatial, social, and ecological organisation of the colony consistent with the life cycle of individuals. The specification separates swarm geometry and the detection of birth and death from cognitive action selection, preserving a single tick in which position, signals, and population composition remain mutually consistent.

Version: 2.2
Updated: 2026-04-08

## 1. Purpose

`ColonySwarmBridge` connects `SimulationRunner` with NOWA `SwarmEnvironment`.

Responsibilities:
- synchronize zone string positions (`agent.position`) with 3D swarm positions;
- update social signals between agents;
- detect mortality and remove dead agents from swarm slots;
- check reproduction compatibility (when factory is provided);
- update ecology/resource share.

Non-responsibilities:
- bridge does not execute `agent.sim_step(...)`;
- bridge does not decide action policy for agents.

## 2. Source Files

- `src/colony_swarm_bridge.py`
- integration callsite: `src/simulation_runner.py`

## 3. Tick Integration in Runner

Current `SimulationRunner.tick(dt)` order:
1. increment `sim_time`
2. `swarm.sync_positions()`
3. `swarm.update_signals()`
4. run `agent.sim_step(dt)` in shuffled order
5. `swarm.sync_positions()` again
6. `dead_ids = swarm.check_mortality()`
7. runner removes dead agents and appends death log entries
8. `swarm.check_reproduction()`
9. spawn `pending_offspring_list`
10. `swarm.update_ecology(len(agents))`
11. optional resource refill

## 4. Position Model

Bridge maps zone names to 3D base points through `ZONE_POSITIONS_3D`.

Placement rules:
- zone occupants are separated by `ZONE_OCCUPANT_OFFSETS`;
- overflow uses deterministic seeded jitter;
- unknown zone fallback uses `DEFAULT_3D` plus deterministic unknown-zone offset;
- all coordinates are clamped to cage bounds.

## 5. Public API

Main methods:
- `add_agent(agent)`
- `remove_agent(agent_id)`
- `get_all_agents()`
- `sync_positions()`
- `update_signals() -> int`
- `check_mortality() -> list[str]`
- `check_reproduction() -> list[Any]`
- `update_ecology(agent_count) -> float`
- `get_swarm_state()`
- `get_diversity()`
- `get_sleeping_agents()`

## 6. Reproduction Logic

Bridge-side rules:
- if `self._swarm.factory is None`, `check_reproduction()` returns `[]` immediately;
- only ready, non-sleeping agents are considered (`reproductive_system.is_ready()`);
- neighbors are checked by radius;
- compatibility computed via `compute_compatibility(...)`;
- threshold controlled by `MIN_COMPATIBILITY_THRESHOLD`;
- successful compatible pair starts pregnancy through mother `_start_pregnancy(...)`.

## 7. Mortality and Logging

Bridge detects dead agents with `mortality_system.is_dead()`.
In current colony mode, no separate seconds-based colony lifetime cap is used.

Runner then:
- removes dead agent from runner list;
- appends extended entry to in-memory `runner._death_log`;
- appends JSONL line to death journal file.

Default journal path:
- `Demo/Colony chinchillas/logs/deaths.jsonl`

Typical death entry fields:
- `agent_id`, `sim_time`, `recorded_at_utc`
- `cause_of_death`, `death_step`, `vitality`
- `name`, `sex`, `generation`, `age`, `position`, `last_action`
- physiology/affect values (`energy`, `wakefulness`, `stress`, `arousal`, `valence`, `cortisol`)

Journal write errors are intentionally non-fatal.

## 8. Tests

```bash
cd "Demo/Colony chinchillas"
pytest -q tests/test_colony_swarm_bridge.py
```

Related persistence verification:

```bash
pytest -q tests/test_storage.py
```
