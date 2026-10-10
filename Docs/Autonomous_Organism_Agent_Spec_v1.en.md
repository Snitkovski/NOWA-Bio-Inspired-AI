# Autonomous Organism Agent Specification

Russian version: [Autonomous_Organism_Agent_Spec_v1.ru.md](Autonomous_Organism_Agent_Spec_v1.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


Version: 1.1  
Status: Implemented (current runtime contract)

---

## 1. Purpose

Define autonomous continuous behavior with:
- internal time loop
- bounded drives and energy
- affect-aware internal simulation
- controlled speech
- strict invariants and logging

This runtime integrates existing modules through controlled interfaces and does not bypass core agent architecture.

---

## 2. Top-Level Components

1. `LifeLoopController`
2. `DriveSystem`
3. `EnergySystem`
4. `InternalSimulationLoop`
5. `SpeechGovernor`

---

## 3. Time Model

State:
- `t_current`
- `t_last_tick`
- `dt > 0`

Tick loop:
```text
while alive:
    dt = now - t_last_tick
    organism_step(dt)
    sleep(min_interval)
```

---

## 4. Drive Taxonomy (Current)

All drives are bounded to `[0, 1]`:
- `curiosity`
- `social_drive`
- `goal_tension`
- `exploration`
- `energy_need`

Not drives:
- `self_reflection` -> represented by `agent_mode="REFLECTION"`
- `emotional_discharge` -> represented by affect regulation trigger path

Drive update (bounded):
```text
drive(t+dt) = drive(t)
           + accumulation*dt
           + affect_modulation
           - discharge*dt
           - decay*dt
```

---

## 5. Energy Model

State:
- `energy in [0,1]`
- `fatigue in [0,1]`

Update:
```text
energy -= cognitive_cost * dt
energy += recovery_rate * rest_time
```

If energy is below threshold -> suppress internal cycles.

---

## 6. Internal Simulation Loop

Trigger:
```text
max(drive_i * weight_i) > threshold
```

Constraints:
1. Uses hypothetical state copies only.
2. Must not mutate live state during evaluation.
3. One internal cycle per tick maximum.
4. Internal cycles per window are hard-limited.

Pipeline:
1. bounded memory recall
2. hypothesis generation
3. action proposal
4. hypothetical action simulation
5. utility evaluation
6. variant ranking

Proposal / evaluation split:
- proposer: `ActionSelector.choose(...)`
- evaluator: `ActionSelector.evaluate(hypothetical_state)` (utility-only)

Shared utility:
- centralized in `src/simulation_utility.py`
- reused by selector and simulation runtime

Drive seed for hypothetical state:
- taken from live `DriveSystem` snapshot when available
- no forced `active_drive=1.0`

Output contract:
```json
{
  "best_action": "string",
  "confidence": 0.0,
  "evaluated_variants": 0
}
```

---

## 7. Speech Governor

Speech is allowed only if:
- communication drive above threshold
- relevance above minimum
- cooldown passed
- interval limit not exceeded

Cooldown invariant is mandatory.

---

## 8. Affect Regulation and Mode

`agent_mode` values:
- `IDLE`
- `ACTIVE`
- `REFLECTION`

`REFLECTION` mode is entered by low external stimulation + high prediction-error/uncertainty signals.

Affect regulation:
- triggered by overload threshold
- reduces affect intensity/overload
- does not create drives
- does not participate in drive ranking

---

## 9. Core Invariants

1. Affective core is mutated only through defined affect interface.
2. Drives remain in `[0,1]`.
3. Energy/fatigue remain in `[0,1]`.
4. Deprecated meta-drives are absent.
5. Speech cooldown is enforced.
6. Internal simulation does not evaluate live state directly.

Violation is logged as runtime failure.

---

## 10. Failure Modes (Observable)

- `drive_runaway_growth`
- `infinite_internal_cycle_loop`
- `speech_spam`
- `dt_anomaly`
- `internal_affect_apply_failed`
- `internal_decision_eval_failed`
- `decision_engine_choose_disallowed`
- `invariant_violation`
- `energy_deadlock`

---

## 11. Tick Contract

Minimum per-tick fields:
- `timestamp`
- `dt`
- `active_drive`
- `energy_level`
- `speech_event`
- `internal_cycle_triggered`

Extended diagnostics:
- `dt_input`, `dt_clamped`
- `physiology_mode`
- `agent_mode`, `mode_signals`
- `regulation`
- `cognitive_load`, `load_components`
- `energy_update`

---

## 12. Validation Status

Current project suite:
- `pytest -q`
- `428 passed, 3 skipped`

Autonomous runtime coverage:
- `tests/test_autonomous_organism.py`
- `tests/test_agent_lifetime_save_load.py`
