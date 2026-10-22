## Abstract

Russian version: [SPEC_ChinchillaAgent_NOWA.ru.md](SPEC_ChinchillaAgent_NOWA.ru.md)

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

Two-tier plasticity for this demo (game `dt`, labile waking writes, stable writes only in `Agent.sleep`) is specified in [issue-13-demo-colony.md](../../../Docs/specs/issue-13-demo-colony.en.md).

This document describes the current implementation of `ChinchillaAgent`, which extends the base NOWA agent into an autonomous individual of the chinchilla colony. An instance joins the cognitive action-selection cycle to colony-specific social and reproductive behaviour, to the physiological constraints of hunger, thirst, and wakefulness, and to interaction with the cage's shared resources. Each individual is an agent in its own right, not an outer wrapper around a decision made elsewhere.

The specification states the constructor contract, the composition of the hippocampal, cortical, action-selection, intention-memory, and sleep modules, and the loading of a behavioural profile. The order of `sim_step` carries perception and context events, reward evaluation, action selection by the NOWA stack, reflex and homeostatic override, zone interpretation, the social step, metabolism, ageing, reproduction, and the sleep-transition check. Critical needs force an action, and actions are blocked when the corresponding need is absent.

In the multi-agent installation, `ChinchillaAgent` is the unit of observation and of hereditary transmission. Public state is exported to the runner and to the graphical layer, while action policy remains inside the individual. The document draws the boundary between the NOWA cognitive stack and the colony constraints, so that individual dynamics can be compared with the population processes of the colony.

# SPEC: ChinchillaAgent with NOWA Stack (Current Implementation)

Version: 2.2
Updated: 2026-04-08

File: `src/colony_agent.py`

## 1. Overview

`ChinchillaAgent` extends base NOWA `Agent` and combines:
- cognitive loop (`step`) from NOWA stack;
- colony-specific social and reproductive behavior;
- physiological constraints (hunger/thirst/wakefulness);
- shared resource interaction (`SharedResources`);
- public state export for runner/GUI.

Each instance is one autonomous individual (not a proxy wrapper).

## 2. Constructor Contract

Required:
- `sex`: `"M"` or `"F"` (validated)

Optional key fields:
- `name`, `agent_id`
- `age`, `generation`, `parents`
- `colony`, `resources`, `position`
- `is_mature`
- `rng`
- `hippocampus_capacity`, `cortex_capacity`
- `genome`

NOWA modules are created and passed to `super().__init__`:
- `NOWAHippocampus`
- `CortexMemory`
- `ActionSelector`
- `IntentMemory`
- `SleepManager`

Behavior profile is loaded from dataset (`load_colony_behavior_profile`) and seeds:
- `base_abilities`
- unconditioned reflexes
- habit traces in `intent_memory`

## 3. Naming

Generated default names follow:
- `G<generation>A<index>S<sex>`

Regex accepted by parser:
- `^G(?P<generation>[0-9]+)A(?P<index>[0-9]+)(?:S(?P<sex>[MFU]))?$`

This keeps compatibility with legacy names while migrating to explicit sex suffix.

## 4. Core Tick (`sim_step`)

`sim_step(dt)` order:
1. advance time and exclusive timers
2. perceive environment and neighbors
3. build context events
4. compute reward/novelty/conflict
5. call NOWA `step(...)` to pick action
6. apply reflex override if triggered
7. apply homeostatic action policy (mandatory guardrail)
8. interpret action into zone/resource effects
9. process social step
10. resource metabolism
11. age/reproduction/mortality update
12. autonomous runtime tick (if present)
13. sleep/wake transition checks

## 5. Homeostatic Policy (Action Guardrail)

Internal needs:
- `hunger`
- `thirst`
- wakefulness (from NOWA wakefulness module)

Critical thresholds force action:
- critical thirst -> `drink`
- critical hunger -> `eat`
- critical wakefulness -> `sleep`

Non-critical conflicts are resolved by urgency ranking among:
- `drink`, `eat`, `sleep`

Safety blocks:
- `sleep` is rejected when sleep need is absent
- `eat` is rejected when hunger need is absent
- `drink` is rejected when thirst need is absent

This prevents biologically inconsistent behavior (for example, sleeping while fully rested).

## 6. Context Events

Examples emitted by `_build_context_events()`:
- spatial: `zone:<position>`
- resources: `food_ok`, `food_low`, `food_critical`, `water_critical`
- social: `social_contact:N`, `stranger_nearby`, `alarm_call`
- lifecycle: `pregnant`, `estrus`, `juvenile`
- affect: `high_stress`, `bored`
- physiology: `hunger_high`, `hunger_critical`, `thirst_high`, `thirst_critical`, `wakefulness_high`, `wakefulness_critical`

## 7. Movement and Position Behavior

Action interpretation supports:
- directed movement to target zones (`_move_towards_any`);
- shortest-path next hop through zone graph (`ADJACENT_ZONES`);
- optional relocation inside allowed target set;
- anti-stuck fallback movement after timeout (`_unstick_position`), except for sleeping/dead.

Wheel-specific logic:
- wheel lock is exclusive;
- blocked wheel access triggers fallback movement (not freeze);
- continuous wheel-running has max duration and then releases lock.

## 8. Resources and Physiology

Metabolism tick:
- accumulates hunger and thirst over time;
- applies stress/valence penalties at critical levels;
- consumes small shared food/water background amounts.

Resource acquisition effects:
- successful `food_pellets` acquisition decreases internal hunger;
- successful `water` acquisition decreases internal thirst;
- failure can add frustration and stress impulse.

## 9. Social and Reproduction

Implemented:
- offer/response protocol with cooldowns and timeouts;
- known-agent memory updates (`knowledge`);
- hearsay transfer and confidence decay;
- mating constraints by sex, maturity, affinity, stress, resources, estrus.

Birth:
- pregnancy timer completion creates offspring in `pending_offspring_list`;
- offspring inherit affective/neuromodulator traits and optional genome crossover/mutation.

## 10. Mortality

`MortalitySystem.update(...)` is called from `_age_step`.

Current colony mode:
- does not enforce a separate hard lifespan in seconds;
- uses physiological death conditions (`exhaustion`, `sleep_deprivation`);
- uses aging dynamics (`old_age` by step budget and `senescence`).

If dead:
- `current_action` set to `"dead"`
- `is_sleeping` set `True`

Actual removal from population is performed by runner via swarm mortality check.

## 11. Public State Contract

`get_public_state()` returns:
- `agent_id`, `name`, `position`
- `affect_tone`
- `current_action`
- `is_receptive`
- `sex`, `age_category`, `scent_signature`

This state is consumed by:
- `SimulationRunner.snapshot()`
- GUI render model
- social perception of other agents.

## 12. Validation

Primary test suite:

```bash
cd "Demo/Colony chinchillas"
pytest -q tests/test_nowa_agent.py
```

Key covered scenarios:
- NOWA stack initialization
- reflex/action override pipeline
- homeostatic action gating
- wheel exclusivity and timeout behavior
- anti-stuck movement
- context event emission
- inheritance and reproduction-related behavior
