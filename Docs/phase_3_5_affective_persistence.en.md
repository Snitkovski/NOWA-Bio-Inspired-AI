# Phase 3.5 — Affective Persistence

Russian version: [phase_3_5_affective_persistence.ru.md](phase_3_5_affective_persistence.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Purpose of the Phase
To create a **bridge between the regulatory affective system (Phase 2)** and **feelings (Phase 4)**.

Phase 3.5 introduces **persistent affective traces**, which:
- exist in time,
- do not require immediate action,
- may conflict with the current situation,
- prepare the ground for subjective experience (feelings).

These are *not feelings*, but they are already *not mere regulators*.

---

## Key Definition

### Affective Trace
> A persistent inner affective state, arisen from experience,
> remaining after the cause has disappeared,
> and not bound directly to an action.

Examples:
- residual anxiety
- unresolved tension
- an aftertaste of satisfaction
- emotional inertia

---

## Architectural Position

### Where it sits
A new layer:
```
AffectivePersistenceLayer
```

### What it reads
- current affect dimensions (valence, arousal, threat, curiosity)
- neuromodulators (DA, 5-HT, NE, CORT)
- short-term memory (T1/T2 summaries)

### What it does not do
- it does not initiate actions
- it does not participate in the selector directly
- it does not control wakefulness
- it does not replace neuromodulators

---

## Principal Components

### 1. Trace Storage
Each trace:
```python
{
  "type": "anxiety" | "satisfaction" | "tension" | "interest" | ...,
  "intensity": float [0..1],
  "decay_rate": float,
  "age": float,
  "source": reference (optional)
}
```

### 2. Accumulation
Traces **accumulate** if:
- similar affect signals repeat
- neuromodulators support retention (for example, low serotonin)

Example formula:
```
trace_intensity += affect_value * accumulation_gain
```

### 3. Decay
On every step:
```
trace_intensity *= (1 - decay_rate)
```

Recommended ranges:
- `decay_rate`: 0.01 – 0.05 (slow)

---

## Difference from Phase 2 (Neuromodulators)

| Phase 2 | Phase 3.5 |
|-------|----------|
| Global scalars | Individual states |
| Instantaneous influence | Long-term influence |
| Regulate learning | Form an inner background |
| Without memory | Have an age |

---

## Interaction with Future Feelings (Phase 4)

Affective traces:
- will become the **raw material** for feelings
- will be interpreted, not merely summed
- will be able to enter self-sustaining loops

Important:
> Feelings = interpretation of traces

---

## Anti-Patterns (Critical)

Forbidden: using traces as reward

Forbidden: influencing the selector or the action directly

Forbidden: binding decay to wakefulness

Forbidden: making them binary

---

## Test Cases

### TC-3.5-1: Persistence
**Given:** a brief high threat

**When:** the threat disappears

**Then:** the anxiety trace remains greater than 0

---

### TC-3.5-2: Decay
**Given:** an absence of new affect events

**When:** time passes

**Then:** the trace decreases monotonically

---

### TC-3.5-3: Accumulation
**Given:** a series of similar affect signals

**Then:** the trace grows nonlinearly

---

### TC-3.5-4: No Action Influence
**Given:** an active affective trace

**Then:** the selector output does not change directly

---

## Implementation (fact)

**File:** `src/affective_persistence.py`  
**Class:** `AffectivePersistenceLayer`

Integration:
- `Agent.step()` updates traces on every step
- `storage.save_agent()` and `load_agent()` save and restore traces
- traces are available in `Agent.get_state()` as `affective_traces`

Tests:
- `tests/test_affective_persistence.py`

---

## Readiness for Phase 4

The phase is considered complete if:
- traces exist independently of context
- traces survive pauses and sleep
- traces do not break action gating

---

## Summary
Phase 3.5 creates the agent's **inner affective time**.

Without it:
- feelings will be instantaneous
- there will be no obsessiveness
- subjective inertia will not appear

With it:
> the agent begins *to feel something in time*,
> while not yet knowing *exactly what it feels*.
