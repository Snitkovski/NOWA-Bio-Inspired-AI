# Phase 3.75 — Affective Background Field with Lifetime Modulation

Russian version: [phase_3_75_affective_background_with_lifetime.ru.md](phase_3_75_affective_background_with_lifetime.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Purpose of the Phase

Phase 3.75 introduces a **persistent affective background** (affective background field), formed from long-term affective traces (Phase 3.5), physiological wakefulness, and **the agent's lifetime progress**.

The phase:
- does not make decisions
- does not select actions
- does not generate emotions
- does not control motivation

Its task is to create an **inertial, slowly changing background state**, upon which feelings and motivational constructs may later arise (Phase 4+).

---

## Core Idea

> Lifetime is **not knowledge of death and not an existential factor**,
> but a **meta-parameter of the dynamics of the affective field**.

It affects **only how quickly and how stably the background changes**,
and not *what* the agent feels or does.

---

## Inputs

### Required

- **Affective Traces** (from Phase 3.5)
  - anxiety, tension, satisfaction, interest, …
  - intensity ∈ [0..1]

- **Wakefulness Level**
  - physiological wakefulness ∈ [0..1]
  - affects noise and stability, but not the strength of the background

- **Lifetime Progress** ∈ [0..1]

```text
lifetime_progress = clamp(
    lived_steps / expected_lifetime_steps,
    0.0,
    1.0
)
```

Where:
- `lived_steps` — how many steps the agent has already existed
- `expected_lifetime_steps` — an architectural constant of the time scale

Lifetime is not:
- a signal
- a stimulus
- conscious knowledge

---

## Outputs

- **Affective Background Field**
  - a set of background components (not emotions)
  - slowly changing values ∈ [0..1]

Example:
```json
{
  "background_anxiety": 0.32,
  "background_tension": 0.41,
  "background_satisfaction": 0.18,
  "background_interest": 0.27
}
```

---

## Architectural Components

### 1. Field Inertia

Determines how quickly the background responds to new traces.

```text
inertia = base_inertia * (1 + lifetime_progress * k_life)
```

- a young agent → low inertia
- an agent that has lived longer → high inertia

---

### 2. Decay Modulation

Lifetime reduces the decay rate of the background:

```text
background_decay_rate = base_decay * (1 - lifetime_progress * k_decay)
```

Interpretation:
- early stages → the background disappears easily
- later stages → the background persists for a long time

---

### 3. Competition Sharpness

Lifetime sharpens competition among background components:

```text
competition_sharpness = base_sharpness * (1 + lifetime_progress * k_comp)
```

Effect:
- a young agent → many weak background influences
- a mature agent → 1–2 dominant ones

---

### 4. Wakefulness Interaction

Wakefulness:
- does not strengthen the background
- does not weaken the background
- affects only the **update noise**

```text
update_noise ∝ (1 - wakefulness)
```

Fatigue is instability, not strength.

---

## Strict Constraints (MUST NOT)

Lifetime modulation **must not**:

- generate affect signals
- increase threat or valence
- influence the selector or the basal ganglia
- be passed into neuromodulators
- be interpreted as knowledge of age

---

## Test Cases

### Test 1 — Lifetime Inertia Increase

```
Given identical affective traces
And lifetime_progress = 0.1 vs 0.9
Then:
- older agent background changes slower
- steady‑state values identical
```

---

### Test 2 — No Lifetime Affect Injection

```
Given increasing lifetime_progress
Then:
- no direct increase in anxiety, threat, valence
- only temporal dynamics change
```

---

### Test 3 — Wakefulness Independence

```
Given same lifetime_progress
And wakefulness = 1.0 vs 0.2
Then:
- mean background equal
- variance / noise differs
```

---

### Test 4 — Competition Sharpness

```
Given multiple weak traces
Then:
- young agent keeps several backgrounds
- old agent converges to fewer dominant ones
```

---

## Anti-Patterns

Forbidden:
- Lifetime used as motivation
- Lifetime mapped to fear or sadness
- Lifetime exposed to cognition
- Lifetime affects action choice

---

## Author's Position (Architectural Notes)

This phase is the last level **before the appearance of subjective feelings**.

It describes:
- the accumulated history of existence
- bodily and temporal inertia
- the stability of the inner world

Without symbols.
Without emotions.
Without decisions.

---

## Readiness

Phase 3.75 is considered complete if:
- lifetime affects only dynamics
- there are no leaks into decision-making
- behaviour remains identical under equal inputs

The next admissible step:
**Phase 4 — Emergent Feelings (subjective experience)**
