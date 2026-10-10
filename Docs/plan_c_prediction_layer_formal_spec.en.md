# Prediction Layer — Prediction Circuit (Formal Specification)

Russian version: [plan_c_prediction_layer_formal_spec.ru.md](plan_c_prediction_layer_formal_spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## 0. Document status

**Purpose:** to fix the architectural role of the prediction circuit (formerly named "Plan C"), its interface with the NOWA system, the permitted dependencies, and the anti-patterns of implementation.

**Key system invariant:**
> The system contains **exactly one** module that returns `action` — `ActionSelector.choose()`.

The Prediction Layer **never** violates this invariant.

---


## 1. Role of the Prediction Layer in the architecture

**Prediction Layer = the circuit that predicts the consequences of actions.**

It answers the question:
> *"What is likely to happen if I perform action X in the current context?"*

And it translates the answer **into the form of pressure**, not of a decision.

### The Prediction Layer does not:
 - select actions
 - cancel the selector's decisions
 - control the flow of execution
 - have access to motor primitives

### The Prediction Layer does:
 - build short-term forward predictions
 - estimate expected affect / reward
 - return **bias / pressure** over actions

---

## 2. Place of Plan C in the decision flow

```
Context + Memory + Affect + Neuromodulators
                ↓
          Plan C (Prediction)
                ↓
     expected_pressure[action]
                ↓
        ActionSelector.choose()
                ↓
              action
```

Plan C is a **source of pressure**, not an executor.

---

## 3. Formal interface of the Prediction Layer

### 3.1 Inputs (read-only)

The Prediction Layer **does not mutate** its inputs.

```python
PredictionLayer.predict(
  context: dict,
  recent_events: List[str],
  affect_state: AffectiveState,
  neuromodulators: NeuromodulatorState,
  temporal_levels: TemporalLevels
) -> Dict[str, float]
```

#### Description of the inputs:
- `context` — current context (situational features)
- `recent_events` — flat sequence of recent events
- `affect_state` — current affective state (T0/T1)
- `neuromodulators` — global modulators (DA, NE, 5-HT, CORT)
- `temporal_levels` — T1/T2/T3 (for discounting and stability)

---

### 3.2 Output

```python
Dict[action_name: str, pressure: float]
```

Semantics:
- `pressure > 0` — the action becomes preferable
- `pressure < 0` — the action is suppressed
- `0` — Plan C has no opinion

Plan C is **not obliged** to return pressure for every action.

---

## 4. What the Prediction Layer predicts

Minimum composition (v1):

For each action `a`:
 - probability of the principal outcomes
 - expected net_affect
 - expected change of affect

Formally:
```
E[a] = Σ P(outcome_i | a, context) × affect(outcome_i)
```

Then:
```
pressure[a] = f(E[a], neuromodulators, temporal_discount)
```

Implementation note for v1 in the repository:
- `src/prediction_layer.py` implements a compact, pure `PredictionLayer`.
- It builds pressure from simple statistics of recent events (finding tokens `action:<name>` in `recent_events`) and proxies global valence through the neuromodulators (DA/5-HT) for the sign of pressure.
- Returned pressures are bounded in magnitude (by default |p| ≤ 0.3) and serve only as advisory bias.

---

## 5. Constraints and invariants (strict)
### Architectural invariants

1. The Prediction Layer **does not call** `ActionSelector.choose()`
2. The Prediction Layer **does not know** which action will be selected
3. The Prediction Layer **does not store selection state** (state may be stored in ChainMemory/TemporalChains, but not in predict())
4. The Prediction Layer **does not modify memory directly**
5. The Prediction Layer **does not start learning** (learning occurs only in sleep/consolidation)

Violation of any item is an architectural error.

---

## 6. Anti-patterns (what must not be done)

### Anti-pattern 1: "A second selector"
```python
# ЗАПРЕЩЕНО
best_action = max(predictions, key=predictions.get)
return best_action
```
**Why this is bad:**
- a second decision center appears

---

### Anti-pattern 2: Override of the action
```python
if predicted_pain > threshold:
    return 'avoid'
```
**Why this is bad:**
- Plan C begins to control behavior directly

---

### Anti-pattern 3: Hard rules
```python
if context == 'fire':
    pressure['touch'] = -999
```
**Why this is bad:**
- the logic turns into an expert system
- learnability is lost

---

### Anti-pattern 4: Learning at the moment of prediction
```python
self.model.update(error)
```
**Why this is bad:**
- inference and learning are mixed
- the separation of phases is violated

---

### Anti-pattern 5: Direct work with affect
```python
affect_state.valence -= 0.5
```
**Why this is bad:**
- feelings become an executive mechanism

---

## 7. Permitted dependencies

Plan C may:
- read Temporal Chains (Plan B)
- take neuromodulators into account as coefficients
- take T2/T3 into account for discounting

Plan C may not:
- modify them directly

---

## 8. Minimal implementation (v1)

Recommended start and notes on the repository:

- `src/prediction_layer.py` implements v1 (see above): statistics over `recent_events` yield aggregated pressure
- Use `ChainMemory` / `temporal_chains.py` as training material for future versions
- Return soft pressure (|pressure| ≤ 0.3)

Integration into Agent/Selector:
- `Agent.step()` collects `recent_events` (the last N events from `hippocampus.experiences`) and calls `prediction_layer.predict(...)`.
- The resulting `prediction_pressure` is passed to `selector.choose(..., prediction_pressure=...)`.
- In the selector the pressure is applied in an advisory manner (multiplication by a weight of about 0.8), then combined with the other sources (hippocampus, cortex, intent_memory, temporal_chains).

---

## 9. Criteria of correctness of the Prediction Layer

The Prediction Layer is correct if:

 - when it is disabled, the system continues to work
 - `ActionSelector` remains the only source of `action`
 - behavior becomes **more anticipatory**, but not rigid
 - errors of the Prediction Layer **do not break** behavior; they only distort priorities

Additionally (tests and validation in the repository):
 - A specification test set `tests/test_prediction_layer_spec_compliance.py` has been added (TC-C-01..TC-C-A3)
 - Unit and integration tests have been added for `PredictionLayer` and affect dynamics
 - Full test run in the repository: `pytest` yields **193 passed** (including the new tests)

---

## 10. Relation to later stages

- After Plan C the following become possible:
  - a more complex forward model
  - free-energy / prediction error
  - a transition to feelings as dynamic regulators

Plan C is a **bridge**, not an endpoint.

---

## Summary

The Prediction Layer is *foresight*, not *will*.

It whispers to the selector, but never speaks for it.

## How to run the tests and verify the changes

1. Install the dependencies (if necessary) and activate the virtual environment.
2. Run all tests:

```bash
pytest -q
```

3. Specification tests for the Prediction Layer:

```bash
pytest tests/test_prediction_layer_spec_compliance.py -q
```

4. Unit and integration tests of curiosity behavior:

```bash
pytest tests/test_affect_curiosity.py tests/test_affect_curiosity_integration.py -q
```

## Migration notes

- If your system mentioned `PlanC`, replace those mentions with `PredictionLayer` and `prediction_pressure`.
- The new `Agent.__init__` API accepts an optional `prediction_layer`.
- `selector.choose()` now supports the `prediction_pressure` keyword argument (a backwards-compatible fallback is implemented).

If pull-request notes or a changelog entry are needed, a separate file `Docs/CHANGELOG_PREDICTION_LAYER.md` can be prepared.
