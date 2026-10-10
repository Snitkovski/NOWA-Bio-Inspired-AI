# Per-Axis Affective Decay

Russian version: [spec_per_axis_affective_decay.ru.md](spec_per_axis_affective_decay.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Problem

`AffectiveSpace` already uses 8 canonical axes:

```text
valence
arousal
dominance
stress
trust
curiosity
stability
attachment
```

Previously the inertial part was described by a single `alpha`, which made the temporal dynamics of the axes too homogeneous.

---

## Biology

The axes have different time scales, so a distinct decay coefficient is required:

| Axis | Behaviour |
| --- | --- |
| stress | falls quickly |
| curiosity | falls quickly without reinforcement |
| arousal | falls quickly (spike-like) |
| valence | intermediate |
| trust | slowly |
| dominance | very slowly |

---

## Solution

Use per-axis coefficients `axis_decay`, with the alias `affective_decay`.

### Default values

```python
affective_decay = {
    "valence":   0.92,
    "arousal":   0.80,
    "dominance": 0.97,
    "stress":    0.75,
    "curiosity": 0.78,
    "trust":     0.95
}
```

For the remaining axes, the fallback is `alpha` (legacy behaviour).

### Legacy compatibility of inputs

Legacy keys are supported in `affective_decay`:

- `pleasure -> valence`
- `arousal -> arousal`
- `dominance -> dominance`

### State update (inertial part)

```python
inertial_component = baseline[axis] + axis_decay[axis] * (current[axis] - baseline[axis])
```

---

## Effect

The resulting behaviour is natural:

```text
arousal   → spikes
valence   → lingers
stress    → fast drop
curiosity → fades without reinforcement
trust     → inertial
dominance → stable
```
