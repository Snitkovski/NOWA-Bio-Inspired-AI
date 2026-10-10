# SPEC: Activation of Internal Simulation and Drive Taxonomy Correction

Russian version: [spec_simulation_drive_taxonomy.ru.md](spec_simulation_drive_taxonomy.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Scope

The document describes:

- Connecting the existing `selector` and `ActionSelector.choose()` to `InternalSimulationLoop` without introducing new modules.
- Removing `self_reflection` and `emotional_discharge` from `DRIVE_NAMES`, with a correct reassignment of their functional role.

The aim is to bring internal simulation to life and to remove the conceptual confusion between biological drives and regulatory mechanisms.

---

## PART 1 — Activation of InternalSimulationLoop

### 1.1 Problem Statement

In the current implementation:

```
InternalSimulationLoop.cognitive_core = None
InternalSimulationLoop.decision_engine = None
```

Consequence:

- the fallback is always used
- hypotheses are not generated
- predictive evaluation is absent
- the system remains reactive

The simulation architecture is formally present, but functionally disabled.

### 1.2 Design Goal

Activate the internal loops without:

- creating new modules
- rewriting `selector`
- changing the external `DecisionEngine` API

Use:

- `selector` as `cognitive_core`
- `selector.evaluate()` as `decision_engine` (utility-only)
- `ActionSelector.choose()` only as a proposer inside the hypothetical loop

### 1.3 Wiring Specification

#### 1.3.1 Dependency Injection

In agent initialization:

```python
internal_loop.cognitive_core = selector
internal_loop.decision_engine = selector  # uses .evaluate(hypothetical_state)
```

> It is **forbidden** to leave them as `None`.

### 1.4 InternalSimulationLoop Execution Contract

#### 1.4.1 Requirement: simulation must run on a copy of state

**Forbidden:**
```python
decision_engine(current_state)
```

**Permitted only:**
```python
decision_engine.evaluate(hypothetical_state)
```

### 1.5 Hypothesis Generation Algorithm

The internal loop must:

1. Create N hypothetical states *(minimum N=1; the maximum is bounded by the existing recall limit)*
2. For each state:
   - apply the proposed action
   - evaluate the change in drives
   - compute utility

#### 1.5.1 Pseudocode

```python
for i in range(simulation_budget):

    hypothetical_state = deepcopy(current_state)

    proposed_action = cognitive_core.propose(hypothetical_state)

    hypothetical_state = simulate_action(hypothetical_state, proposed_action)

    score = decision_engine.evaluate(hypothetical_state)

    collect(score, proposed_action)
```

#### 1.5.2 Unified Utility

The utility calculation must be the same for:
- `selector.evaluate()`
- `InternalSimulationLoop`

It is implemented through a shared module:
```text
src/simulation_utility.py
```

### 1.6 Output Contract

`InternalSimulationLoop` must return:

```json
{
    "best_action": "action",
    "confidence": 0.0,
    "evaluated_variants": 0
}
```

> Fallback is permitted only if no hypothesis was generated.

### 1.7 Invariants

- `current_state` must not be mutated
- `decision_engine` must not be called without a hypothetical state
- the internal loop must not be started unless `simulation_budget > 0`
- `selector` must not be used directly on live state

---

## PART 2 — Drive Taxonomy Correction

### 2.1 Problem Statement

The current `DRIVE_NAMES` contains:

- `self_reflection`
- `emotional_discharge`

These are:

- not physiological needs
- not primary regulators
- not homeostatic deficits

They are higher-level mechanisms.

### 2.2 Design Principle

> **Drive** = a deficit state arising from biological or social primitives.

- Drive is not a cognitive operation
- Drive is not a mode of operation
- Drive is not a protective reaction

### 2.3 Specification Changes

#### 2.3.1 Remove from DRIVE_NAMES

```yaml
remove:
    - self_reflection
    - emotional_discharge
```

### 2.4 Replacement Architecture

#### 2.4.1 Self Reflection to Mode

Instead of the drive `drive.self_reflection`, introduce:

```python
agent_mode = {
    IDLE,
    ACTIVE,
    REFLECTION
}
```

Conditions for entering `REFLECTION`:

- low external stimulation
- high accumulated `prediction_error`
- elevated `uncertainty`

#### 2.4.2 Emotional Discharge to a Regulation Mechanism

Instead of the drive `drive.emotional_discharge`, introduce the function:

```python
regulate_affect()
```

Trigger:

```python
if affect_overload > threshold:
    trigger_discharge()
```

> This is not motivation. It is a protective reaction.

### 2.5 Required Refactor

#### 2.5.1 SpeechGovernor

If `discharge` previously reduced `social_drive`, it must now:

- reduce `affect`
- reduce `overload`
- **not** create a new drive

### 2.6 Invariants

- Regulation cannot generate a new drive
- A drive cannot be a cognitive operation
- Mode does not take part in drive competition
- affect regulation does not take part in decision ranking

---

## Expected System-Level Effects

After the change:

- `InternalSimulationLoop` ceases to be merely declarative
- Predictive evaluation of actions appears
- The system becomes partly proactive
- Meta-drive recursion is removed
- Drive competition becomes clean

---

## Migration Checklist

- [x] `cognitive_core` is connected
- [x] `decision_engine` is connected
- [x] fallback is used only when there are no hypotheses
- [x] `DRIVE_NAMES` is cleared
- [x] `self_reflection` is moved to a mode
- [x] `emotional_discharge` is moved to regulation
- [x] regulation does not take part in drive ranking
- [x] unit tests are updated
