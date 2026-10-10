# SWS / REM Phase Separation Specification v1.0

Russian version: [spec_sws_rem_phase_separation.ru.md](spec_sws_rem_phase_separation.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


---

## 1. Scope

The specification defines:

- Formal criteria for classifying the sleep phase: `SWS`, `REM`, `TRANSITIONAL`
- Distinct update regimes for SAC (Semantic Action Centroids)
- Rules for changing `mu`, `sigma`, `stability_score`, `semantic_confidence`
- Hard constraints
- A set of test cases for verification

> The phase is determined only during `sleep_consolidation()`.

---

## 2. Input signals

Every sleep episode must contain:

```
confidence_score         ∈ [0, 1]
stability_score          ∈ [0, 1]
prediction_shock         ≥ 0
arousal                  ∈ [0, 1]
consolidation_probability ∈ [0, 1]
replay_priority          ≥ 0
```

> If any signal is absent, the episode does not participate in the phase logic.

---

## 3. Batch aggregation

For a sleep batch `B`:

```
mean_confidence
mean_stability
mean_shock
mean_arousal
mean_consolidation_prob
shock_fraction_high = fraction(prediction_shock > θ_shock_high)
```

---

## 4. Threshold parameters

Mandatory parameters:

```
θ_arousal_low
θ_arousal_high
θ_shock_low
θ_shock_high
θ_conf_high
θ_cons_high
θ_stability_high
```

**Invariant:**

```
θ_arousal_low < θ_arousal_high
θ_shock_low   < θ_shock_high
```

---

## 5. Phase classification

### 5.1 SWS

A batch is classified as `SWS` if:

```
mean_arousal            < θ_arousal_low
AND mean_shock          < θ_shock_low
AND mean_confidence     > θ_conf_high
AND mean_consolidation_prob > θ_cons_high
```

### 5.2 REM

A batch is classified as `REM` if **at least one** of the following holds:

```
mean_arousal        > θ_arousal_high
OR mean_shock       > θ_shock_high
OR shock_fraction_high > 0.25
```

### 5.3 TRANSITIONAL

If none of the conditions above holds, the phase is `TRANSITIONAL`.

---

## 6. Local phase re-evaluation (optional)

If `local_phase_mode = True` is enabled, the phase is computed for each action separately from its local aggregates.

By default the global phase of the batch is used.

---

## 7. SAC Update Rules by Phase

**Common notation:**

```
mu_old
sigma_old
sigma_floor
stability_old
alpha_base
```

### 7.1 SWS regime

#### 7.1.1 Mu update

```
alpha_mu_sws = alpha_base * 0.5
mu_new = mu_old + alpha_mu_sws * (mu_observed - mu_old)
```

#### 7.1.2 Sigma update

```
sigma_new = sigma_old + α_sigma * (sigma_observed - sigma_old)
sigma_new *= (1 - sigma_decay_sws)
sigma_new = max(sigma_floor, sigma_new)
```

Invariant: `sigma_new ≤ sigma_old` (if `shock_low`).

#### 7.1.3 Stability update

If the action was updated:

```
stability_new = min(1.0, stability_old + β_stability_sws)
```

> **Forbidden:** a decrease of stability in SWS.

#### 7.1.4 Semantic confidence

An exponential moving average with an elevated coefficient:

```
semantic_confidence_new =
    EMA(semantic_confidence_old, semantic_signal, λ_sws)
```

Where `λ_sws > λ_rem`.

---

### 7.2 REM regime

#### 7.2.1 Mu update

```
alpha_mu_rem = alpha_base * 1.5
mu_new = mu_old + alpha_mu_rem * (mu_observed - mu_old)
```

#### 7.2.2 Sigma update

```
sigma_new = sigma_old + α_sigma * (sigma_observed - sigma_old)
sigma_new += ε_var_rem
sigma_new = max(sigma_floor, sigma_new)
```

Invariant: `sigma_new ≥ sigma_old` (if `shock_high`).

#### 7.2.3 Stability update

**Permitted:**

```
stability_new = stability_old * (1 - δ_rem)
```

> **Forbidden:** an increase of stability in REM.

#### 7.2.4 Structural alert

If `prediction_shock > θ_structural`:

```python
meta["structural_alert"] = True
```

---

### 7.3 TRANSITIONAL regime

Conservative dynamics:

- `alpha_mu = alpha_base`
- sigma update without forced contraction or expansion
- stability unchanged

---

## 8. Hard Constraints

| #   | Constraint |
|-----|-------------|
| HC1 | The phase is computed only inside `sleep_consolidation()` |
| HC2 | Wake TD-learning does not depend on the sleep phase |
| HC3 | `sigma ≥ sigma_floor` always |
| HC4 | In SWS: stability never decreases |
| HC5 | In REM: stability never increases |
| HC6 | SWS and REM rules cannot be applied simultaneously to the same action in one sleep cycle |

---

## 9. Validation metrics

After sleep the following are computed:

- `phase_distribution`
- `mean_sigma_change`
- `mean_stability_change`
- `structural_alert_count`

---

## 10. Test cases

### Test 1 — Pure SWS

**Input:**

```
mean_arousal           = 0.1
mean_shock             = 0.05
mean_confidence        = 0.85
mean_consolidation_prob = 0.9
```

**Expected:** `phase == SWS`, `sigma_new ≤ sigma_old`, `stability_new ≥ stability_old`, `structural_alert_count == 0`.

### Test 2 — Pure REM (high shock)

**Input:**

```
mean_arousal         = 0.8
mean_shock           = 0.4
shock_fraction_high  = 0.5
```

**Expected:** `phase == REM`, `sigma_new ≥ sigma_old`, `stability_new ≤ stability_old`, structural alerts are possible.

### Test 3 — Mixed batch

**Input:**

```
mean_arousal = 0.3
mean_shock   = 0.15
```

**Expected:** `phase == TRANSITIONAL`, sigma without forced contraction or expansion, stability unchanged.

### Test 4 — Sigma floor protection

**Input:** `sigma_old = 0.02`, `sigma_floor = 0.01`, SWS contraction.

**Expected:** `sigma_new ≥ 0.01`.

### Test 5 — Stability monotonicity

**SWS cycle:** `stability_old = 0.7` → `stability_new ≥ 0.7`.

**REM cycle:** `stability_old = 0.7` → `stability_new ≤ 0.7`.

### Test 6 — Structural alert trigger

**Input:** `prediction_shock = 0.9`, `θ_structural = 0.8`.

**Expected:** `meta["structural_alert"] == True`.

---

## 11. System effects

This specification guarantees:

- Separation of consolidation and repair
- Absence of oscillatory drift
- Protection against variance collapse
- Controlled growth of stability
- The possibility of model restructuring through REM
