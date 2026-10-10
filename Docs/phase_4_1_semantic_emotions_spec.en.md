# Phase 4.1 — Semantic Emotions

Russian version: [phase_4_1_semantic_emotions_spec.ru.md](phase_4_1_semantic_emotions_spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Purpose of the Phase

Phase 4.1 introduces a **semantic emotion layer** that:

- does NOT generate affect
- does NOT influence action selection directly
- does NOT regulate other subsystems

Its only function is the **interpretation of the continuous affective space (Phase 4)** as stable, overlapping **emotional attractors**.

This is a layer of *awareness*, not of *reaction*.

---

## Inputs

### Required

- `AffectiveSpace.axes` — an 8-dimensional vector:
  - pleasure
  - pain
  - arousal
  - relaxation
  - attachment
  - rejection
  - focus
  - vulnerability

- `AffectiveSpace.inertia`
- `AffectiveSpace.fall_rate`
- `AffectiveSpace.speed()`

### Optional

- `wakefulness`
- `agent_lifetime` (total time the agent has existed)

---

## Outputs

A list of active semantic emotions:

```json
{
  "emotion": "love",
  "activation": 0.73,
  "stability": 0.61,
  "obsessive": true
}
```

The output is NOT used by the action selector.

---

## Basic Definition: the Emotional Attractor

An **attractor** is a region in 8D space, specified by:

- a centre (prototype vector)
- tolerance radii along the axes
- axis weights

### Formally

Activation of emotion E:

```
E = clamp( Σ w_i * f_i(A_i), 0..1 )
```

where `f_i` are nonlinear functions (ReLU, sigmoid, abs).

---

## Canonical Emotions (v1)

### Joy

- pleasure rises
- arousal rises
- pain falls

```python
joy = pleasure*0.5 + arousal*0.4 - pain*0.4
```

---

### Sadness

- pain rises
- arousal falls
- attachment rises

```python
sadness = pain*0.5 + (1-arousal)*0.3 + attachment*0.3
```

---

### Love

- attachment rises strongly
- pleasure rises
- vulnerability rises

```python
love = attachment*0.5 + pleasure*0.3 + vulnerability*0.3
```

---

### Hate

- rejection rises
- arousal rises
- focus rises

```python
hate = rejection*0.5 + arousal*0.3 + focus*0.3
```

---

### Fear

- pain rises
- arousal rises
- vulnerability rises

---

### Pleasure at rest (pleasure_rest)

- pleasure rises
- relaxation rises

---

## Obsessiveness of Emotions

An emotion is obsessive if:

```
obsessive = inertia_high AND fall_rate_low AND focus_high
```

Obsessiveness is **not an error**. It is a personality characteristic.

---

## Stability

```
stability = 1 - AffectiveSpace.speed()
```

High stability means emotional "sticking".

---

## System Properties

- emotions may coexist
- emotions may contradict one another
- there is no normalization across emotions
- there is no suppression

---

## Test Cases

### TC-1: Love plus pain

```
attachment=0.9
pleasure=0.7
pain=0.6
vulnerability=0.8
```

Expected:
- love > 0.6
- sadness > 0.3

---

### TC-2: Obsessive hate

```
rejection=0.8
arousal=0.9
focus=1.0
inertia.high
fall_rate.low
```

Expected:
- hate.active
- hate.obsessive = true

---

### TC-3: Emotional rest

```
pleasure=0.6
relaxation=0.7
arousal=0.1
pain=0.0
```

Expected:
- pleasure_rest > 0.6

---

## Anti-patterns

Forbidden:

- Emotions as switches
- Suppression of conflicting emotions
- Normalization of the sum of emotions
- Direct use of emotions in the selector

---

## Philosophical Remark

Phase 4.1 is the first layer in which the agent **can say something to itself**, rather than to the world:

> "I am in pain"
> "I am attached"
> "I want to, but I am afraid"

This is not the end.
It is the beginning of subjectivity.

---

## Implementation Notes (2026-02-10)

- Implemented as `SemanticEmotionsLayer` with canonical emotions (joy, sadness, love, hate, fear, pleasure_rest).
- Integrated in `Agent.step()` after affective space update.
- Persisted via save/load as `semantic_emotions`.
- GUI shows a brief textual summary plus a detailed list.
- Layer remains non-decisional: no action selection influence.
