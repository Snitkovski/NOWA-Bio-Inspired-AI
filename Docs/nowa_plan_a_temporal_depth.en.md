# NOWA — Plan A: Temporal Depth (Time as an Architectural Factor)

Russian version: [nowa_plan_a_temporal_depth.ru.md](nowa_plan_a_temporal_depth.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

> **Aim of stage A**
> Introduce into NOWA a representation of time as a *structural dimension of behaviour*, rather than as a timestamp.
> Temporal depth must make it possible to distinguish fluctuations, tendencies, and stable attractors.

---

## I. Architectural Invariants (Mandatory)

1. Time is not a clock and is not a date
2. Time is represented by *levels of aggregation*
3. The same signal is interpreted differently at different levels
4. No level knows the “future”
5. Higher levels influence lower levels **only through a shift of probabilities**

---

## II. Temporal Levels of NOWA

### T0 — Instantaneous Level

**Purpose:** reaction

- current context
- current affect_state
- current intent

Used by:
- Selector
- ActionRealizer

---

### T1 — Short-Term Dynamics

**Purpose:** local adaptation

- the last N episodes (sliding window)
- aggregates:
  - mean reward
  - success frequency
  - mean threat
  - variance of affect

Stored:
- in Hippocampus

---

### T2 — Medium-Term Patterns

**Purpose:** habits and tendencies

- consolidated patterns
- stable couplings of context to intent
- mean affect profiles of patterns
- slow drift during wakefulness (micro-consolidation)
- strengthening and stabilisation during sleep (deep consolidation)

Stored:
- Cortex
- IntentMemory (with a temporal weight)

---

### T3 — Long-Term Attractors

**Purpose:** character and preferences

- stable biases of choice
- inertial parameters
- incipient relations (without narrative)

Stored:
- a separate module `temporal_attractors.py`

---

## III. Changes by Module

### 1. Agent

- holds references to all temporal levels
- at each step:
  - updates T0
  - logs into T1
  - when the T1 window is full, performs micro-consolidation T1 → T2
  - during sleep, performs deep consolidation T1 → T2 → T3

---

### 2. AffectState

Add temporal aggregates:

- affect_now (T0)
- affect_trend (T1)
- affect_baseline (T2)

Update:
- T0 — every step
- T1 — sliding window
- T2 — slow drift in wakefulness, plus strengthening in sleep

---

### 3. Selector

Action selection is a function of:

- T0 signals (reaction)
- T1 tendencies (correction)
- T2/T3 inertia (bias)

The Selector does not know the names of the levels — only the coefficients.

---

### 4. SleepManager

Sleep becomes an **operator of time**:

- smooths T1 noise
- strengthens trends
- strengthens and stabilises T2 (it does not create T2 from nothing)
- updates T3

Sleep does not optimise; it **stabilises**.

---

## IV. Temporal Attractors (T3)

### Definition

A temporal attractor is
> a parameter that slowly biases action selection over a long time

Examples:
- stable avoidance of risk
- stable interest in dialogue
- elevated caution

These are not emotions.
These are not assertions.
These are not goals.

---

## V. Criteria of a Correct Implementation

An agent is regarded as having implemented Plan A correctly if:

- the same context with a different history yields different responses
- a brief negative episode does not break long-term behaviour
- a prolonged negative episode changes tendencies
- behaviour is more stable after sleep
- there is not a single textual description “in time”

---

## VI. Test Scenarios (Mandatory)

1. Brief negativity, then recovery
2. Prolonged negativity, then a change of tendency
3. Random noise is ignored
4. Repeated success is consolidated
5. Sleep reduces variance

---

## VII. What Is Strictly Prohibited at Stage A

- strategies
- goals
- planning of the future
- subjective temporal narratives

---

## VIII. Result of Stage A

NOWA:
- begins to “remember duration”
- distinguishes the moment from the tendency
- becomes stable in time

**Only after this** is the transition to stage B (strategies) admissible.
