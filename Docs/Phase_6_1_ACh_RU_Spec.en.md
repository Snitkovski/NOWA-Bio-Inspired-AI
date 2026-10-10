# Phase 6.1 — Acetylcholine Layer Specification (ACh)

Russian version: [Phase_6_1_ACh_RU_Spec.ru.md](Phase_6_1_ACh_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## 1. Aim of the Phase

Introduction of the neuromodulator acetylcholine (ACh) as a mechanism of:

- attention gating
- novelty amplification
- modulation of the learning rate
- contextual encoding strength
- replay priority modulation

ACh is NOT a reward system (that role belongs to dopamine). ACh is a regulator of selectivity and plasticity.

---

## 2. Architectural Principles

1. ACh ∈ [0.0, 1.0]
2. It has a baseline
3. It is amplified by novelty
4. It decreases under repetition
5. It tends toward the baseline through exponential decay
6. It does not influence TD error directly
7. It does not influence sleep alpha

---

## 3. Extension of Neuromodulators

### 3.1 New Fields

```python
self.acetylcholine: float = 0.1
self.ach_baseline: float = 0.1
self.ach_decay_rate: float = 0.02
self.ach_novelty_gain: float = 0.25
self.ach_repetition_penalty: float = 0.05
self.ach_alpha_gain: float = 0.4
self.ach_replay_gain: float = 0.5
```

Constraint:

```python
self.acetylcholine = clamp(self.acetylcholine, 0.0, 1.0)
```

---

### 3.2 Update Method

```python
def update_acetylcholine(self, novelty: float, stable_repetition: bool):
    if novelty > 0.5:
        self.acetylcholine += self.ach_novelty_gain * novelty

    if stable_repetition:
        self.acetylcholine -= self.ach_repetition_penalty

    # decay toward baseline
    delta = self.ach_baseline - self.acetylcholine
    self.acetylcholine += self.ach_decay_rate * delta

    self.acetylcholine = clamp(self.acetylcholine, 0.0, 1.0)
```

---

## 4. Integration with ValueLayer

### 4.1 Online Alpha Modulation

In `ValueLayer.update()`:

```python
alpha_effective = alpha_online_default * (1 + ach_alpha_gain * ACh)
alpha_effective = min(alpha_effective, 0.15)
```

Sleep alpha is NOT scaled by ACh.

---

## 5. Integration with Memory Encoding (T1)

When an episode is created:

```python
encoding_strength = base_strength * (1 + 0.5 * ACh)
```

---

## 6. Integration with Replay Priority

In `SleepManager._compute_replay_priority()`:

```python
priority *= (1 + ach_replay_gain * ACh_snapshot)
priority = min(priority, priority_cap)
```

---

## 7. Safety Constraints

1. ACh does not modify TD error.
2. ACh does not influence dopamine directly.
3. ACh does not scale sleep alpha.
4. ACh ≤ 1.0.
5. When ACh > 0.9, a soft alpha cap is engaged.

---

## 8. Test Cases

### Test 1 — Novelty Spike

novelty = 1.0

Expected:
- ACh increases
- alpha_online increases
- replay_priority increases

---

### Test 2 — Repetition

novelty = 0.1
stable_repetition = True

Expected:
- ACh decreases

---

### Test 3 — Saturation Protection

Repeated novelty.

Expected:
- ACh ≤ 1.0
- alpha_online ≤ 0.15

---

### Test 4 — Decay to Baseline

One hundred steps without novelty.

Expected:
- ACh tends to the baseline

---

## 9. Metrics

In the snapshot:

```python
"acetylcholine": self.acetylcholine
```

In the sleep statistics:

```python
"mean_ach_during_cycle": ...
```

---

## 10. Completion Criteria

The phase is complete if:

- ACh is updated correctly
- alpha_online is scaled
- replay priority is scaled
- there is no runaway plasticity
- all tests pass
