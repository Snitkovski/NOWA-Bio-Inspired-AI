# Conflict and Arbitration Layer (ACC-like)

Russian version: [spec_conflict_arbitration_layer.ru.md](spec_conflict_arbitration_layer.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


*(taking into account the already implemented BG, Hippocampus 2.0, and CER)*

**Functional analogue:** anterior cingulate cortex.  
This is neither an emotional layer nor a value layer. It is a layer that monitors conflict and governs the control regime.

---

## 1. Objectives of the layer

The ACC-like layer must:

- Detect conflict between alternatives
- Estimate the probability of error
- Estimate the necessity of strengthening control
- Arbitrate among: Habitual (BG fast path), Goal-directed (value recompute), Exploration, Inhibition
- Govern: the BG threshold, control gain, working-memory allocation, and exploration override

---

## 2. Position in the architecture

```
Hippocampus 2.0 → novelty, pattern completion
CER             → tonic modulation
BG              → action gating
ACC-like        → control regime arbitration
```

**Decision loop:**

```
Inputs
  ↓
HPC → novelty
  ↓
CER → tone
  ↓
BG → action candidates
  ↓
ACC → evaluate conflict
  ↓
ACC modifies BG parameters
  ↓
Final action
```

> The ACC does not select an action directly. It changes the selection regime.

---

## 3. Input signals

### 3.1 From BG

- `go_signals[]`
- `top2_gap`
- `policy_entropy`
- `decision_latency`
- `threshold_current`

### 3.2 From CER

- `arousal`
- `stress_level`
- `valence`

### 3.3 From the hippocampus

- `novelty_score`
- `pattern_completion_confidence`

### 3.4 From the learning system

- `prediction_error`
- `recent_failure_rate`
- `error_history_window`

### 3.5 From the cognitive layer

- `working_memory_load`
- `task_complexity`

---

## 4. Computed metrics

### 4.1 Conflict Score

A combination of: a low `top2_gap`, high entropy, high working-memory load, and low pattern confidence.

```
conflict_score =
  w1*(1 - top2_gap_norm)
+ w2*entropy_norm
+ w3*wm_load_norm
+ w4*(1 - pattern_confidence)
```

Constraints:

- Normalized to 0–1
- Does not depend directly on valence (so as not to duplicate CER)

### 4.2 Error Likelihood

```
error_likelihood =
  a1*prediction_error_norm
+ a2*recent_failure_rate
+ a3*conflict_score
```

### 4.3 Control Demand

```
control_demand =
  b1*conflict_score
+ b2*error_likelihood
+ b3*task_complexity_norm
```

---

## 5. Outputs of the layer

| Output                   | Description                                  |
|--------------------------|----------------------------------------------|
| `control_mode`           | `habitual` / `balanced` / `deliberative` / `inhibit` |
| `threshold_delta`        | Change of the BG decision threshold          |
| `control_gain_multiplier`| Multiplier of value-layer influence          |
| `wm_boost_flag`          | Flag for reallocating resources into working memory |
| `exploration_override`   | Permission for forced exploration            |

---

## 6. Operating regimes

### 6.1 Habitual

**Conditions:** `conflict_score < T1`, error likelihood low, novelty low.

**Behaviour:** threshold decreases, fast gating, no working-memory boost.

### 6.2 Balanced

Medium control. A neutral regime.

### 6.3 Deliberative

**Conditions:** `conflict_score > T2`, error likelihood high.

**Behaviour:**
- threshold increases
- `wm_boost = true`
- value is recomputed
- higher latency is admitted

### 6.4 Inhibit

**Conditions:** conflict high, error likelihood high, recent failure high.

**Behaviour:**
- temporary blocking of the action
- a request for additional information

---

## 7. Constraints (hard constraints)

### 7.1 The ACC cannot:

- select an action directly
- change reward directly
- change CER parameters
- overwrite the hippocampus

### 7.2 Control-cost penalty

Each elevation of regime increases cost:

```
control_cost += k * regime_intensity
```

If cost exceeds the limit, a forced downshift follows.

### 7.3 Refractory period

After the `deliberative` regime, deliberative cannot be activated again for N steps.  
This prevents oscillation.

### 7.4 Hysteresis

Regime transitions require `T_up ≠ T_down`.  
This prevents flickering.

---

## 8. Potential failures

### 8.1 Chronic deliberation

The system remains constantly in `deliberative`.  
**Cause:** inflated weights of `conflict_score`, absence of `cost_penalty`.

### 8.2 Emotional hijack

If CER arousal is high, the ACC may constantly see conflict.  
**Remedy:** exclude arousal from conflict directly.

### 8.3 Paralysis

The `inhibit` regime is activated too often.  
**Constraint:** at most K consecutive inhibit episodes.

### 8.4 Mode oscillation

Switching `balanced` and `deliberative` on every step.  
**Remedy:** hysteresis and a refractory period.

---

## 9. Test cases

### 9.1 Low-conflict scenario

**Input:** a large `top2_gap`, low entropy, low prediction error.  
**Expected:** `habitual`, threshold decreases.

### 9.2 High conflict, high novelty

**Input:** a small gap, high entropy, high novelty, moderate prediction error.  
**Expected:** `deliberative`, `wm_boost = true`, exploration permitted.

### 9.3 Repeated failure

**Input:** a high `recent_failure_rate`, a high `error_likelihood`.  
**Expected:** `inhibit`, threshold increases sharply, a request for additional evaluation.

### 9.4 Emotional stress but low conflict

**Input:** high arousal, a low `conflict_score`.  
**Expected:** the regime does not switch to `deliberative`. This checks the separation of CER and ACC.

### 9.5 Oscillation test

Alternating conflict and non-conflict steps.  
**Expected:** absence of frequent regime flicker.

### 9.6 Resource exhaustion

Many consecutive `deliberative` episodes.  
**Expected:** the `control_cost` limit forces `balanced`.

---

## 10. Quality metrics

- Percentage of regimes by distribution
- Average decision latency
- Performance under conflict
- Reduction of error after conflict detection
- Oscillation index
- Control-cost utilization

---

## 11. Biological plausibility

Functionally it corresponds to conflict monitoring, effort allocation, and error detection.

It is associated with the anterior cingulate cortex, but it is implemented as a computational module, not as a neural model.

---

## 12. Principal architectural rule

> **The ACC is a module that estimates the necessity of control, not a source of control.**

Control is realized by changing the parameters of the BG and of the cognitive layers.

---

## 13. Implementation clarifications (as-built, 2026-02-25)

1. **Coupling to the learning rate**
   - The ACC does not raise the online learning rate merely because the regime is `deliberative`.
   - The increase of alpha in the value layer is bound to `error_likelihood` (when error likelihood is low, the boost is not applied).
2. **Inhibit pathway**
   - The `inhibit` regime is implemented by strengthening the decision threshold in the BG.
   - Direct suppression of `pressure_vector` (nearly to zero) is not used.
3. **Latency in control demand**
   - `decision_latency` is taken into account in `control_demand` with a separate small weight.
4. **CER/ACC resonance guard**
   - The summed `decision_threshold_shift` from CER and ACC is limited by a separate cap,
     in order to avoid over-suppression under joint instability.
