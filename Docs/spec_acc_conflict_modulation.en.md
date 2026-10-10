# Specification: ACC Conflict Modulation with Protection against Dynamic Instability

Russian version: [spec_acc_conflict_modulation.ru.md](spec_acc_conflict_modulation.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

---

## 1. Goal

Remove an architectural defect:

> ACC arousal/stress lies outside the `conflict_score` formulas

and introduce a two-way dynamic between conflict and the neuromodulators.

At the same time ensure:

- stability of the system
- absence of runaway dynamics
- backward compatibility of agent behaviour

---

## 2. Biological Model

The ACC encodes cognitive conflict and is amplified by the LC-NE system (arousal) and by stress (cortisol):

```
perceived_conflict =
    raw_conflict
    × arousal_gain
    × stress_gain
```

---

## 3. Architectural Position

Modulation is performed inside `NeuromodulatorState`.

**Signal flow:**

```
Environment
    ↓
raw_conflict
    ↓
ACC modulation
    ↓
effective_conflict
    ↓
neuromodulator update
```

---

## 4. Formula

```
effective_conflict =
    raw_conflict
    × (1 + k_NE   × (NE − baseline_NE))
    × (1 + k_CORT × cortisol)
```

| Parameter | Value |
|-----------|----------|
| `k_NE`    | 0.5      |
| `k_CORT`  | 0.7      |

---

## 5. Constraints

### 5.1 Ranges of input signals

```
0 ≤ raw_conflict    ≤ 1
0 ≤ norepinephrine  ≤ 1
0 ≤ cortisol        ≤ 1
```

Every value passes through: `clamp(x, 0, 1)`.

### 5.2 Output constraint

After the computation:

```
effective_conflict = clamp(effective_conflict, 0, 1)
```

### 5.3 Gain constraint

```
0.5 ≤ arousal_gain ≤ 2.0
0.5 ≤ stress_gain  ≤ 2.0
```

> This prevents runaway dynamics.

---

## 6. Algorithm

**Step 1 — normalize conflict:**

```
conflict_v = clamp(conflict, 0, 1)
```

**Step 2 — compute `arousal_gain`:**

```
arousal_gain = 1 + k_NE × (NE − baseline_NE)
arousal_gain = clamp(arousal_gain, 0.5, 2.0)
```

**Step 3 — compute `stress_gain`:**

```
stress_gain = 1 + k_CORT × cortisol
stress_gain = clamp(stress_gain, 0.5, 2.0)
```

**Step 4 — compute `effective_conflict`:**

```
effective_conflict = conflict_v × arousal_gain × stress_gain
```

**Step 5 — constrain the range:**

```
effective_conflict = clamp(effective_conflict, 0, 1)
```

---

## 7. Use of effective_conflict

**Before:**

```python
NE   += NE_CONFLICT   × conflict
CORT += CORT_CONFLICT × conflict
```

**After:**

```python
NE   += NE_CONFLICT   × effective_conflict
CORT += CORT_CONFLICT × effective_conflict
```

---

## 8. Protection against Systemic Risks

### 8.1 Positive loop stress → conflict → stress

**Risk:** `conflict → cortisol → conflict amplification → cortisol`.

**Remedy:** `stress_gain ≤ 2` and a small coefficient `CORT_CONFLICT`.

### 8.2 Runaway dynamics of NE

**Risk:** `conflict → NE → conflict`.

**Remedy:** bound `arousal_gain`, and use baseline centering `NE − baseline_NE`.

### 8.3 Destruction of TD learning

Conflict must not affect dopamine directly:

```
conflict → NE, CORT    permitted
conflict → dopamine    forbidden
```

### 8.4 Instability of the affective system

**Risk:** `NE → arousal → conflict → NE`.

**Remedy:** `arousal_gain ≤ 2` and clamping of the affective axes.

---

## 9. Implementation Requirements

**Method:** `NeuromodulatorState._compute_effective_conflict()`

**Signature:**

```python
_compute_effective_conflict(conflict: float) -> float
```

**Requirements:**

- a pure function
- does not modify state
- uses the current values of NE and cortisol

---

## 10. System Invariants

After an update the following must hold:

```
0 ≤ dopamine        ≤ 1
0 ≤ norepinephrine  ≤ 1
0 ≤ serotonin       ≤ 1
0 ≤ cortisol        ≤ 1
0 ≤ acetylcholine   ≤ 1
```

---

## 11. Test Cases

### Test 1 — Baseline

**Input:** `conflict = 0.5`, `NE = 0.1`, `cortisol = 0`.

**Expected:** `effective_conflict = 0.5`.

### Test 2 — High arousal

**Input:** `conflict = 0.5`, `NE = 0.6`, `cortisol = 0`.

**Expected:** `effective_conflict ≈ 0.625`.

### Test 3 — High stress

**Input:** `conflict = 0.5`, `cortisol = 0.5`.

**Expected:** `effective_conflict ≈ 0.675`.

### Test 4 — Combined effect

**Input:** `conflict = 0.5`, `NE = 0.6`, `cortisol = 0.5`.

**Expected:** `effective_conflict ≈ 0.84`.

### Test 5 — Saturation

**Input:** `conflict = 1`, `NE = 1`, `cortisol = 1`.

Before clamp: `2.46`. After clamp: `1.0`.

### Test 6 — Zero conflict

**Input:** `conflict = 0`.

**Result:** `effective_conflict = 0`.

---

## 12. Integration Tests

### Stability test

1,000 iterations with `conflict = 0.6`.

**Checked:** NE does not run away to saturation, and cortisol does not run away to saturation.

### Stress-dynamics test

10 steps with `conflict = 0.8`.

**Expected:** a smooth rise of cortisol, then stabilization.

---

## 13. Acceptance Criteria

The implementation is correct if:

- all tests pass
- the dynamics of the system are stable
- baseline behaviour of the agent does not change
- neuromodulators remain in the range `[0, 1]`

---

## 14. Result

**After the change:**

```
conflict
    ↓
ACC modulation
    ↓
effective_conflict
    ↓
NE / cortisol
```

**Instead of the former:**

```
conflict → neuromodulators
```

---

## 15. Implementation in Code (current as of 2026-03-24)

File: `src/neuromodulators.py`, class `NeuromodulatorState`.

The current implementation extends the base formula of this specification with additional stabilization:

1. A nonlinear bound on gain sensitivity:
```python
bounded_delta(x) = x / (1 + abs(x))
arousal_gain = 1 + k_NE * bounded_delta(NE - baseline_NE)
stress_gain  = 1 + k_CORT * max(0, bounded_delta(CORT - baseline_CORT))
```

2. Serotonergic inhibition and soft normalization:
```python
inhibition_gain = clamp(1 - k_HT * max(0, HT - baseline_HT), ACC_INHIBITION_MIN, 1.0)
modulated = conflict * arousal_gain * stress_gain * inhibition_gain
effective_conflict = modulated / (1 + ACC_SOFT_NORM * modulated)
```

3. Temporal dynamics of the ACC (low-pass):
```python
alpha = 1 - exp(-dt / ACC_CONFLICT_TAU)
trace_next = trace + alpha * (target - trace)
```

4. Separation of conflict channels:
- `cognitive_conflict` affects the `NE` branch,
- `affective_conflict` affects the `CORT` branch,
- `combined_conflict` is carried by a separate trace as an integral ACC metric and is used in the 5-HT gate.

5. Symmetric `None` semantics for split conflicts:
- if both channels are `None`, both are taken from `conflict`,
- if one channel is `None`, it is copied from the other.

6. Homeostatic stabilization:
```python
NE   += ACC_NE_HOMEOSTATIC_DECAY   * (BASELINE_NE   - NE)
CORT += ACC_CORT_HOMEOSTATIC_DECAY * (BASELINE_CORT - CORT)
```

7. The time step is consistent within one update:
- `dt` is used both in ACC smoothing and in `interaction_field.update(..., dt=dt)`.

8. `cortisol` is deliberately kept outside the fast interaction field (`DA/5HT/NE/ACh`) as a slow stress axis.

### Test coverage of the implementation

- `tests/test_acc_conflict_modulation.py`:
  - the ACC formula and invariants,
  - purity of `_compute_effective_conflict`,
  - low-pass dynamics of traces,
  - split conflicts and `None` semantics,
  - bounded long-run dynamics.
- `tests/test_neuromodulators_phase2.py`:
  - legacy Phase 2 scenarios, synchronized with ACC modulation.
