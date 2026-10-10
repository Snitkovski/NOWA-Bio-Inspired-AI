# SPEC-011A — Credit Assignment Stabilization

Russian version: [spec_011a_credit_assignment.ru.md](spec_011a_credit_assignment.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Extension of:** SPEC-011
**Status:** REQUIRED
**Priority:** HIGH

---

## 1. Problem

After the introduction of replay, deliberative planning, and an uncertainty-driven policy, a **credit assignment collapse** appears.

**Symptoms:**

1. reward is distributed onto states that are too early
2. TD-error propagates along a long chain
3. replay amplifies spurious correlations
4. EDPC begins to overvalue accidental actions

**As a result:** policy drift, unstable habits, oscillating value estimates.

---

## 2. Cause

In the current architecture:

```
reward → TD update → replay → EDPC stability
```

There is no mechanism that limits the depth of credit propagation.

---

## 3. Solution

Three mechanisms are introduced:

- Temporal Credit Window
- Eligibility Traces
- Replay Causality Filter

---

## 4. Temporal Credit Window

### 4.1 Definition

Reward may propagate only onto a limited number of preceding states:

```
credit_window = 6
```

### 4.2 Constraint

```
reward propagation depth ≤ credit_window
```

### 4.3 Implementation

TD updates must be applied only to the last N events in `Path.events`, where `N = credit_window`.

---

## 5. Eligibility Traces

### 5.1 Definition

Each state-action is assigned a trace:

```
eligibility_trace ∈ [0, 1]
```

### 5.2 Trace update

When an action is executed: `trace = 1`.
For the others:

```
trace ← trace * λ
```

### 5.3 Parameters

```
λ = 0.85
```

### 5.4 TD update

```
ΔV = α * TD_error * eligibility_trace
```

### 5.5 Constraint

```
trace ≤ 1
```

---

## 6. Replay Causality Filter

Replay must not amplify spurious correlations.

### 6.1 Replay condition

An episode is admitted to replay only if:

```
causality_score ≥ threshold
```

### 6.2 Formula

```
causality_score =
    reward_magnitude
    * (1 - state_distance)
    * action_stability
```

Where: `state_distance = normalized_state_delta`, `action_stability = SAC stability_score`.

### 6.3 Threshold

```
causality_threshold = 0.15
```

---

## 7. Reward Backpropagation Decay

Reward must weaken over time.

### 7.1 Formula

```
credit_weight(step) = exp(-step / τ)
```

### 7.2 Parameter

```
τ = 3
```

### 7.3 Constraint

```
credit_weight ≥ 0.05
```

---

## 8. Replay Stability Gate

Replay must amplify only stable knowledge.

### 8.1 Condition

```
replay_allowed if stability_score > 0.25
```

### 8.2 Exception

If `prediction_shock_score > 0.7`, replay is permitted regardless of stability.

---

## 9. TD Error Clipping

To avoid runaway TD.

### 9.1 Constraint

```
TD_error ∈ [-1.0, 1.0]
```

### 9.2 Application

Applied to: the online update and sleep replay.

---

## 10. Replay Diversity Constraint

Replay must not repeat the same state-action.

```
max_replay_per_state = 3   # за один sleep цикл
```

---

## 11. Memory Causality Tracking

Every experience must store `causal_depth`.

### 11.1 Definition

```
causal_depth = distance_from_reward_event
```

### 11.2 Constraint

```
causal_depth ≤ credit_window
```

---

## 12. Integration with DecisionArbitrator

### 12.1 New metric

```
policy_reliability =
    mean(action_stability)
    * (1 - global_uncertainty)
    * mean(causality_score)
```

### 12.2 Use

If `policy_reliability < 0.35`, `DELIBERATIVE` mode is forced on.

---

## 13. Constraints

| Parameter            | Constraint              |
|----------------------|-------------------------|
| Trace decay `λ`      | `∈ [0, 1]`              |
| `credit_window`      | `∈ [3, 10]`             |
| `causality_score`    | `∈ [0, 1]`              |
| TD clipping          | `|TD_error| ≤ 1`        |

---

## 14. Telemetry

Agent telemetry must contain:

- `eligibility_trace_mean`
- `credit_window_usage`
- `replay_causality_mean`
- `policy_reliability`

---

## 15. Test cases

### TEST 1 — Long chain reward

**Input:** a 10-step episode, reward on step 10.

**Expected:** only the last 6 states are updated.

### TEST 2 — Trace decay

**Input:** `λ = 0.85`.

**Expected:** monotone decrease: `1.0 → 0.85 → 0.72 → 0.61`.

### TEST 3 — Replay causality filter

**Input:** `reward = 0.2`, `state_distance = 0.8`, `stability = 0.4`.

**Score:**

```
0.2 * (1 - 0.8) * 0.4 = 0.016
```

**Expected:** replay rejected.

### TEST 4 — Shock override

**Input:** `shock_score = 0.8`, `stability = 0.1`.

**Expected:** replay allowed.

### TEST 5 — TD clipping

**Input:** `TD_error = 3.5`.

**Expected:** `TD_error = 1.0`.

### TEST 6 — Policy reliability collapse

**Input:** `uncertainty = 0.7`, `stability = 0.3`, `causality = 0.2`.

**Expected:** `policy_reliability < 0.35`, `mode = DELIBERATIVE`.

---

## 16. Acceptance Criteria

The change is successful if:

1. TD propagation is limited
2. replay does not amplify spurious chains
3. the policy does not collapse under rare reward
4. value estimates stabilise

---

## 17. Architectural result

After SPEC-011 and SPEC-011A are introduced, the system obtains:

- an uncertainty-aware policy
- stable credit assignment
- controlled replay learning
- generalized state memory
