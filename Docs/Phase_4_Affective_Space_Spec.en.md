# Phase 4 (pre): Affective Space Specification

Russian version: [Phase_4_Affective_Space_Spec.ru.md](Phase_4_Affective_Space_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Formal Specification of the Affective Space (Prior to Feelings)

### Aim

To create a continuous, multidimensional affective space in which:
- feelings are not flags or classes,
- contradictory and obsessive states are admissible,
- subjectivity and character arise naturally from the dynamics,
- the architecture is compatible with the preceding phases (3, 3.5, 3.75).

---

## 1. General Model

The affective state of the agent is described by a vector **A(t)** in the space ℝ⁸.

Each axis is independent and has its own dynamics, inertia, and noise.

No normalization of the sum of the values is applied.

---

## 2. Axes of the Affective Space (8)

All axes have the range **[0.0 .. 1.0]**.

| Axis | Description |
| --- | --- |
| pleasure | pleasure / positive hedonics |
| pain | pain (not negative pleasure) |
| arousal | arousal / activation |
| relaxation | relaxation |
| attachment | attachment |
| rejection | rejection |
| focus | focus / cognitive fixation |
| vulnerability | vulnerability / openness to influence |

All axes are **equal in status**.  
Any axis may participate in any feeling.

---

## 3. Basic Dynamics of an Axis

For each axis `i`:

```text
dA_i/dt =
    input_i
  - decay_i * A_i
  + inertia_i
  + noise_i
```

---

## 4. Inertia (the Key to Obsessiveness)

Obsessiveness is not an error. It is a parameter.

```text
obsessiveness_i =
    high inertia_i
  + low fall_rate_i
  + high focus
```

---

## 5. Noise

Noise is necessary for subjectivity.

```text
noise_i ~ N(0, σ_i)
```

σ depends on:
- wakefulness
- uncertainty
- conflicts among axes

---

## 6. Metrics

1. Distance:

```text
D(A,B)=Σ w_i|A_i-B_i|
```

2. Speed:

```text
V=|A(t)-A(t-1)|
```

---

## 7. Relation to Phase 3.75

The background field:
- modifies decay, inertia, and noise
- does not set values directly

---

## 7.1 Implementation Note (Agent)

In the base implementation (Agent), the coupling `reward → pain` is made contextual:

```text
pain = clamp(
    max(0.0, -reward) * intensity * (0.5 + 0.5 * vulnerability)
)
```

This means:
- under high vulnerability, pain is amplified,
- under resilience, a negative reward is not always equivalent to pain.

---

## 8. Prohibitions

- Emotion labels
- Feeling classes
- Influence on the selector

---

## 9. Result

- Contradictory states are admissible
- Character arises
- A basis for feelings is formed

---

## 10. Next

Phase 4: Emergent Feelings
