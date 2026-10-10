# Semantic Action Consolidation (SAC)

Russian version: [spec_semantic_action_consolidation.ru.md](spec_semantic_action_consolidation.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Implementation note (March 3, 2026)

Runtime SAC behavior is extended with SWS/REM/TRANSITIONAL phase separation and strict hard constraints.
Canonical phase rules are documented in:
- `Docs/spec_sws_rem_phase_separation.md`

Current runtime additions aligned with code/tests:
- global and optional local phase mode (`local_phase_mode`)
- hard constraints: `sac_alpha_slow <= 0.01`, `sac_alpha_base <= 0.01`, `sac_lambda_sws > sac_lambda_rem`
- explicit one-phase-per-action rule (`SWS xor REM xor TRANSITIONAL`)
- REM stability floor (`sac_stability_floor_rem`)
- structural alert calm-cycle reset (`sac_structural_alert_reset_cycles`)
- semantic confidence per-cycle step cap (`sac_semantic_confidence_step_cap`)


**Version:** 1.1  
**Status:** Integrated in runtime (`SleepManager`, sleep-only)  
**Purpose:** Slow consolidation of the semantic action model from stable episodic experience during sleep.

---

## 1. Purpose of the module

To provide:

- Slow updating of `action_metadata`
- Protection against confirmation bias
- Robustness to anomalies (high `prediction_shock`)
- Two-speed dynamics (episodic fast / semantic slow)
- Biologically plausible sleep-gated consolidation

---

## 2. Scope of responsibility

SAC:

- Operates **only during sleep**
- Updates **only the semantic layer**
- Uses aggregated replay signals
- Does not intervene in online TD

---

## 3. Inputs

### 3.1 From Hippocampus 2.0 (replay buffer)

For each replay episode:

```
action_id
TD_error
prediction_shock
confidence_score
stability_score
observed_outcome
predicted_outcome
consolidation_probability
```

### 3.2 From ValueLayer (semantic store)

```python
action_metadata[action_id] = {
    expected_effect_mean,    # μ
    expected_effect_variance, # σ²
    success_alpha,
    success_beta,
    risk_estimate,
    semantic_confidence
}
```

---

## 4. Consolidation gating

An episode is admitted to semantic update if:

```
confidence_score       > θ_conf
stability_score        > θ_stab
prediction_shock       < θ_shock
consolidation_probability > θ_cons
```

**Recommended thresholds:**

| Threshold  | Value    |
|------------|----------|
| `θ_conf`   | 0.6      |
| `θ_stab`   | 0.5      |
| `θ_shock`  | 0.4      |
| `θ_cons`   | 0.5      |

> If the condition is not met, the episode is ignored.

---

## 5. Signal aggregation

For each `action_id`:

1. Collect all gated replay episodes.
2. Compute the episode weight:

```
w_i = stability_score_i × confidence_score_i × (1 - prediction_shock_i)
```

3. Compute:

```
TD_semantic       = weighted_mean(TD_error_i, w_i)
μ_observed        = weighted_mean(observed_outcome_i, w_i)
σ_observed        = weighted_variance(observed_outcome_i, w_i)
success_rate_obs  = weighted_mean(success_flag_i, w_i)
```

> If the total weight is below `θ_min_weight`, the update is skipped.

---

## 6. Semantic model update

### 6.1 Two-speed learning coefficient

```
α_fast  ∈ [0.05, 0.2]    # episodic, not in SAC
α_slow  ∈ [0.001, 0.01]  # semantic, used in SAC
```

### 6.2 Expected-effect update

```
μ_new = μ_old + α_slow * (μ_observed - μ_old)
```

### 6.3 Variance update

```
σ²_new = σ²_old + α_slow * (σ²_observed - σ²_old)
σ²_new = max(σ_floor, σ²_new)
```

Adaptation rule:

- if the mean shock across episodes is greater than 0.3, `σ²` is increased further by `ε_var`
- if stability is high, `σ²` decreases
- anti-crystallization: `σ_floor ≈ 0.01` (protection against semantic crystallization)

### 6.4 Success-probability update (Beta model)

```
success_alpha_new = success_alpha_old + α_slow * weighted_successes
success_beta_new  = success_beta_old  + α_slow * weighted_failures
```

### 6.5 Risk update

```
risk_estimate_new = f(σ²_new, failure_rate)
```

Where:

```
risk_estimate ∝ σ² × failure_probability
```

---

## 7. Anti-Confirmation Bias Constraint

A semantic update is permitted only if:

```
|μ_old - μ_observed| > ε_divergence
```

Where `ε_divergence ≈ 0.05–0.1` (on a normalized scale).

> If the divergence is small, the update is suppressed.

---

## 8. Constraints (Hard Constraints)

- SAC cannot be invoked in the wake state
- SAC cannot modify episodic values
- `α_slow ≤ 0.01` is a hard limit
- If `prediction_shock_mean > 0.6`, the update is forbidden
- If `replay_count < N_min` (for example 3), the update is forbidden

---

## 9. System invariants

After any SAC step:

- `σ²_new ≥ σ_floor` (`σ_floor` defaults to `0.01`)
- `success_alpha > 0`
- `success_beta > 0`
- `risk_estimate ∈ [0, 1]`
- `semantic_confidence ∈ [0, 1]`

---

## 10. Monitoring metrics

- Semantic Drift Rate
- Stability Growth Rate
- Divergence Reduction Index
- Overconfidence Index

---

## 11. Test cases

### Test 1 — Confirmed action

**Given:** 10 replay episodes, low shock, high stability, `μ_observed > μ_old`.

**Expected:** `μ_new > μ_old`, `σ²_new` decreases, `success_alpha` increases, `risk_estimate` decreases.

### Test 2 — Anomalous episode

**Given:** high `prediction_shock` (> 0.7).

**Expected:** the update is not performed; the semantic layer is unchanged.

### Test 3 — Insufficient data

**Given:** `replay_count = 1`.

**Expected:** the update is not performed.

### Test 4 — High instability

**Given:** `stability_score < θ_stab`.

**Expected:** the episode is excluded from aggregation.

### Test 5 — Divergence is small

**Given:** `|μ_old - μ_observed| < ε_divergence`.

**Expected:** `μ` does not change.

### Test 6 — Catastrophic drift

**Given:** `α_slow` is artificially set to 0.1.

**Expected:** the system rejects the configuration (Hard Constraint violation).

### Test 7 — Shock-driven variance expansion

**Given:** mean shock = 0.4.

**Expected:** `σ²_new > σ²_old`.

### Test 8 — Variance floor (anti-crystallization)

**Given:** `σ²_old` is very small (`< 0.01`) and stability is high.

**Expected:** after SAC, `σ²_new ≥ σ_floor`.

---

## 12. Failure Modes

| Failure mode                | Monitoring                        |
|-----------------------------|-----------------------------------|
| Semantic Rigidity           | Divergence Reduction Index        |
| Semantic Drift              | Semantic Drift Rate               |
| Overconfidence Collapse     | Overconfidence Index              |
| Replay Bias Amplification   | Stability Growth Rate             |

> Each must be tracked by the metrics of section 10.

---

## 13. Resulting architectural position

SAC provides:

- preservation of the agent as a learning organism
- gradual formation of long-term capacities
- robustness to environmental noise
- the possibility of learning from external data
- the possibility of predicting the world

> Without turning the system into a static world-model.
