# Phase 4 — Dopaminergic TD-Learning Layer

Russian version: [spec_dopaminergic_td_learning.ru.md](spec_dopaminergic_td_learning.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**Duration:** 1 month  
**Role:** global prediction-error driver of learning and behavioral adaptation

---

## 1. Biological reference

Functional analogue:

- Temporal difference learning
- Reward prediction error
- Ventral tegmental area
- Substantia nigra

The aim is to implement:

- phasic dopamine burst/dip
- signed prediction error
- learning of value and policy
- modulation of downstream plasticity (BG, ACC)

---

## 2. Architectural position in the system

Pipeline after Phase 4:

```
Hippocampus
→ CER (tonic affect)
→ ACC (control arbitration)
→ BG (action gating)
→ Action
→ Environment
→ Reward

→ Dopaminergic TD Layer
→ updates:
    Value model
    BG synapses
    ACC learning scale
    Exploration policy
```

---

## 3. Functional requirements

### 3.1 Computation of TD-error

```
δt = rt + γ * V(st+1) − V(st)
```

Where:

- `r_t` — actual reward
- `V(s)` — state-value
- `γ` — discount factor

### 3.2 Phasic versus tonic separation

The TD layer must separate:

| Component       | Role                      |
|-----------------|---------------------------|
| `phasic_delta`  | fast burst/dip            |
| `mean_phasic`   | running filtered phasic mean |
| `tonic_level`   | slow baseline drift       |

- Tonic is regulated by CER
- Phasic is the instantaneous prediction error

### 3.3 Signed dopamine logic

- `δ > 0` → burst → strengthening of the Go pathway
- `δ < 0` → dip → strengthening of the NoGo pathway

**Forbidden:**

- taking the absolute value
- ignoring the sign

### 3.4 Interaction with BG

The TD layer does not select actions. It:

- updates synaptic weights
- modulates Go/NoGo learning rates

### 3.5 Interaction with ACC

ACC uses `|δ|` as `error_likelihood` and a history window for conflict.

The TD layer must return:

```json
{
    "phasic_delta": "δ",
    "abs_delta": "abs(δ)",
    "delta_sign": "sign(δ)"
}
```

---

## 4. Constraints (System Constraints)

### 4.1 No direct modification of reward

The TD layer is not permitted to:

- rewrite `r_t`
- scale reward post hoc

> Reward is an external signal of the environment.

### 4.2 No intervention in Hippocampus

Do not change:

- novelty
- pattern completion

### 4.3 Saturation cap

Phasic delta must be bounded:

```
δ_clipped = clamp(δ, −δ_max, +δ_max)
```

> Otherwise learning runs away.

### 4.4 Stability constraint

The learning rate must depend on `ACC learning_boost` and `CER stress_level`, but **not** directly on the magnitude of `δ`.

---

## 5. API specification

```python
class DopaminergicTDLayer:

    def compute_td_error(
        self,
        reward: float,
        value_current: float,
        value_next: float,
        gamma: float
    ) -> dict:

        """
        Returns:
            {
                "delta": float,
                "delta_clipped": float,
                "abs_delta": float,
                "delta_sign": int,
                "phasic_burst": float,
                "mean_phasic": float,
                "tonic_level": float
            }
        """
```

---

## 6. Value-function update

```
V(st) ← V(st) + α * δ_clipped
```

Where:

```
α = base_alpha × acc_learning_boost
```

---

## 7. Exploration coupling

**Positive burst:** slightly reduces exploration (confidence grows).

**Negative dip:** increases exploration.

Constraint:

```
exploration modulation ≤ 0.2 от baseline
```

---

## 8. Test cases

### 8.1 Positive surprise

**Input:** `reward = 10`, `V(st) = 2`, `V(st+1) = 4`, `γ = 0.9`

**Expected:** `δ > 0`, burst > 0, Go-learning is strengthened.

### 8.2 Negative surprise

**Input:** reward below expectation.

**Expected:** `δ < 0`, dip, strengthening of NoGo.

### 8.3 Zero error

**Input:** reward matches expectation.

**Expected:** `δ ≈ 0`, no burst/dip, tonic remains stable and changes only slowly.

### 8.4 Large error saturation

**Input:** extreme reward.

**Expected:** `δ_clipped ≤ δ_max`, learning does not explode.

### 8.5 Repeated negative streak

Several consecutive steps with `δ < 0`.

**Expected:** ACC receives a high `abs_delta`, ACC strengthens deliberative mode, the TD layer does not run away.

### 8.6 CER stress modulation

If CER stress is high: `learning_rate` decreases, burst magnitude does not grow.

---

## 9. Success metrics

After introduction:

- Value convergence is stable
- No oscillatory explosion
- Exploration is adaptive
- ACC receives a correct error signal
- BG policy becomes more stable

---

## 10. Risks

### 10.1 Positive feedback loop

TD burst → learning boost → still larger burst.

**Remedy:** cap `learning_boost`, clip `δ`.

### 10.2 Catastrophic forgetting

If `γ` is too low, the agent becomes myopic.

### 10.3 Conflict amplification

Large `δ` values put ACC into permanent deliberation.

**Remedy:** smooth `abs_delta` through an EMA.

---

## 11. What changes systemically

After Phase 4 the architecture becomes a **self-regulating reinforcement organism**:

```
Hippocampus  →  memory + novelty
CER          →  affective tone
ACC          →  control arbitration
BG           →  action gating
Dopamine     →  plasticity engine
```

This is a complete closed adaptive reinforcement-learning architecture.
