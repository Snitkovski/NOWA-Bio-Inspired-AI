# SPEC-011 — Decision Arbitration + Global Uncertainty + State Generalization

Russian version: [spec_011_decision_arbitration.ru.md](spec_011_decision_arbitration.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Version:** 1.0
**Status:** REQUIRED
**Scope:** Agent Core Architecture

---

## 1. Purpose

Remove the desynchronisation between EDPC, SAC, and Policy that arises because:

- TD-error is interpreted independently by different subsystems
- the decision policy does not take model uncertainty into account
- the state is encoded too rigidly (state fragmentation)

Introduce:

- Decision Arbitration Layer
- Global Uncertainty Model
- State Similarity Kernel

---

## 2. Architecture after the change

**Before:**

```
State
  ↓
ValueLayer (EDPC)
  ↓
ActionSelector (policy)
```

**After:**

```
State
  ↓
ValueLayer (EDPC)
  ↓
Sleep SAC update
  ↓
DecisionArbitrator
  ↓
ActionSelector
```

---

## 3. New component

### 3.1 DecisionArbitrator

**File:** `src/decision_arbitrator.py`
**Class:** `class DecisionArbitrator`

**Role** — combine the signals of EDPC, SAC, the affective system, and uncertainty, and determine:

- `habitual` versus `deliberative` mode
- policy temperature

---

## 4. Global Uncertainty Model

### 4.1 Definition

A variable is introduced:

```
global_uncertainty ∈ [0, 1]
```

**Formula:**

```
global_uncertainty =
    w_td      * normalized_td_variance
  + w_error   * EDPC.error_likelihood
  + w_surprise * EDPC.surprise
```

Weights:

```
w_td       = 0.40
w_error    = 0.35
w_surprise = 0.25
```

Constraint: `0 ≤ global_uncertainty ≤ 1`.

### 4.2 Signal sources

| Signal              | Source                                            |
|---------------------|---------------------------------------------------|
| TD variance         | `selector.action_metadata[action]["td_variance"]` |
| error likelihood    | `value_layer.last_error_likelihood`               |
| surprise            | `value_layer.last_surprise`                       |

### 4.3 Normalisation of TD variance

```
normalized_td_variance = clamp(td_variance / TD_VAR_SCALE, 0, 1)
```

Where `TD_VAR_SCALE = 0.5`.

---

## 5. Decision Arbitration

### 5.1 Modes

The system has 2 modes: `HABITUAL` and `DELIBERATIVE`.

### 5.2 Mode switching

```python
if global_uncertainty > 0.55:
    mode = DELIBERATIVE
else:
    mode = HABITUAL
```

### 5.3 Effect of stress

ACC stress lowers the deliberation threshold:

```
effective_threshold = base_threshold - (0.25 * stress)
```

Where: `base_threshold = 0.55`, `stress ∈ [0, 1]`.

Constraint: `threshold ≥ 0.25`.

### 5.4 Policy temperature

```
temperature = base_temp + (uncertainty_gain * global_uncertainty)
```

Where: `base_temp = 0.6`, `uncertainty_gain = 0.8`.

Constraint: `0.4 ≤ temperature ≤ 1.5`.

---

## 6. Integration with ActionSelector

ActionSelector must accept `temperature` and `decision_mode`.

**New interface:**

```python
select_action(
    state,
    pressure_vector,
    temperature,
    decision_mode
)
```

---

## 7. Deliberative Mode

If the mode is `DELIBERATIVE`, ActionSelector must:

1. Increase policy entropy
2. Take EDPC predictions into account
3. Penalize unstable actions

**Penalty:**

```
action_score =
    base_score
    * action_confidence
    * action_stability
```

---

## 8. State Generalization

**Current problem:**

```
state_key = hash(snapshot)
```

This causes state explosion.

### 8.1 State Similarity Kernel

Add the function `state_similarity(s1, s2)` with a cosine similarity metric.

### 8.2 Use

On access to `expectation_memory`, if the exact `state_key` is not found, search for the top-k similar states:

```
k = 3
similarity_threshold = 0.85
```

### 8.3 Aggregation

If several states are found:

```
expected_reward_mean = weighted_mean(similarity)
```

---

## 9. Constraints

| Parameter            | Constraint                       |
|----------------------|----------------------------------|
| `global_uncertainty` | `∈ [0, 1]`, clamp on violation   |
| `temperature`        | `∈ [0.4, 1.5]`                   |
| `similarity`         | `∈ [0, 1]`                       |
| `k` (state agg.)     | `≤ 5`                            |

---

## 10. Performance

Similarity search must be `O(k log N)` or better.

> Full enumeration is forbidden when `N > 500`.

---

## 11. Telemetry

Agent telemetry must contain:

- `decision_mode`
- `global_uncertainty`
- `policy_temperature`
- `similar_state_count`

---

## 12. Edge Cases

| Situation                   | Behaviour                                  |
|-----------------------------|--------------------------------------------|
| No SAC metadata             | `td_variance = 0`                          |
| No EDPC profile             | `error_likelihood = 0.5`, `surprise = 0`   |
| No similar states           | fallback to the default expectation profile |

---

## 13. Test cases

### TEST 1 — Low uncertainty

**Input:** `td_variance = 0.05`, `error_likelihood = 0.1`, `surprise = 0.05`, `stress = 0`.

**Expected:** `global_uncertainty < 0.3`, `mode = HABITUAL`, `temperature ≈ 0.65`.

### TEST 2 — High TD variance

**Input:** `td_variance = 0.8`, `error_likelihood = 0.2`, `surprise = 0.1`.

**Expected:** `mode = DELIBERATIVE`, `temperature > 1.0`.

### TEST 3 — Stress driven deliberation

**Input:** `uncertainty = 0.45`, `stress = 0.8`.

**Threshold:** `0.55 - 0.25 * 0.8 = 0.35`.

**Expected:** `mode = DELIBERATIVE`.

### TEST 4 — State similarity

**Memory:** S1 similarity 0.92, S2 similarity 0.88, S3 similarity 0.84.

**Expected:** use S1 and S2, ignore S3.

### TEST 5 — Temperature bounds

**Input:** `uncertainty = 1`.

**Expected:** `temperature ≤ 1.5`.

### TEST 6 — No SAC metadata

**Expected:** `td_variance = 0`, uncertainty depends only on EDPC.

---

## 14. Backwards Compatibility

All new fields must have safe default values.

> The agent must operate even if `DecisionArbitrator` is disabled.

---

## 15. Required Files

**New:**

```
src/decision_arbitrator.py
```

**Changes:**

```
agent.py
selector.py
value_layer.py
```

---

## 16. Acceptance Criteria

The change is successful if:

1. `decision_mode` switches correctly
2. `uncertainty` affects the policy
3. state generalization reduces memory growth
4. SAC stability affects action selection
