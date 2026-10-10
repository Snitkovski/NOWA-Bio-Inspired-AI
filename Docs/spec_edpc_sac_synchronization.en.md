# Phase 5.x — Strict Specification of EDPC and SAC Synchronization

Russian version: [spec_edpc_sac_synchronization.ru.md](spec_edpc_sac_synchronization.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


*(Expectation-Driven Predictive Core and Sleep and Action Consolidation)*

---

## 0. Purpose

This specification formalizes bidirectional synchronization between:

- **EDPC** — the system of predictive expectations and error evaluation
- **SAC** — the system of action consolidation and sleep

The **objective** is to ensure a correct update of:

- `stability_score`
- `confidence_score`
- `predicted_effect`
- `error_likelihood`
- `replay_priority`

without violating:

- cognitive consistency
- temporal causality
- plasticity constraints
- the principle of a "learning organism"

---

## 1. Architectural invariants

### 1.1 Uniqueness-of-source invariant

| Field                | Source of truth |
|----------------------|-----------------|
| `expectation_memory` | EDPC            |
| `action_metadata`    | SAC             |
| `replay_priority`    | EDPC            |
| `consolidation_flag` | SAC             |

- SAC may not create a new `state_key`
- EDPC may not modify `action_metadata` directly

### 1.2 Causal invariant

An update is admissible only if:

```
episode.timestamp < sleep_cycle.timestamp
```

> Retroactive change of expectations that have already been used is forbidden.

### 1.3 Bounded-plasticity invariant

During sleep:

```
Δstability_score  ≤ 0.05 per cycle
Δconfidence_score ≤ 0.03 per cycle
```

> This prevents "over-consolidation".

---

## 2. Formal data structures

### 2.1 EDPC.expectation_memory

```python
expectation_memory[state_key] = {
    "predicted_value":    float,
    "confidence_score":   float,   # ∈ [0, 1]
    "stability_score":    float,   # ∈ [0, 1]
    "error_likelihood":   float,   # ∈ [0, 1]
    "prediction_shock":   float,   # ∈ [0, 1]  # score only
    "prediction_shock_flag": bool, # explicit shock flag (never bool(score))
    "last_updated_step":  int
}
```

### 2.2 SAC.action_metadata

```python
action_metadata[action_id] = {
    "predicted_effect": vector,
    "confidence":       float,   # ∈ [0, 1]
    "stability":        float,   # ∈ [0, 1]
    "td_mean":          float,
    "td_variance":      float,
    "consolidated":     bool,
    # Runtime sync helpers (implementation):
    "consolidation_flag": bool,
    "conflict_flag":      bool,
    "last_state_key":     str
}
```

---

## 3. Event protocol of synchronization

Synchronization occurs **only in the sleep phase**.

### 3.1 Trigger

```python
if sleep_state in {SWS, REM}:
    enable_sync()
```

---

## 4. Synchronization algorithm

### 4.1 EDPC to SAC

**Condition:**

```
prediction_shock < 0.2
confidence_score > 0.6
```

**Then:**

```
action_metadata[action].confidence ← EMA(confidence_score)
action_metadata[action].stability  ← EMA(stability_score)
```

Where:

```
EMA_new = (1 - α) * old + α * incoming
α ≤ 0.1
```

### 4.2 SAC to EDPC (reverse transfer)

**Condition:**

```
action_metadata.consolidated == True
```

**Then:**

```
expectation_memory[state].stability_score +=
    k1 * (td_mean / (1 + td_variance))
```

Where: `0 < k1 ≤ 0.03` and `stability_score ≤ 1.0`.

---

## 5. Update formulas

### 5.1 Stability update through TD

```
Δstability = k * tanh(td_mean) * (1 - td_variance)
```

Constraints: `0 ≤ stability ≤ 1`.

### 5.2 Update of error_likelihood

```
error_likelihood_new = clamp(
    error_likelihood_old * 0.95 +
    prediction_shock * 0.05
)
```

---

## 6. Synchronization constraints

### 6.1 Prohibition of a double update

One episode may participate in synchronization:

- at most once in SWS
- at most once in REM

### 6.2 Sleep-energy constraint

In one sleep cycle:

```
Σ replay_priority_processed ≤ energy_budget_sleep
```

### 6.3 Constraint against divergence

If:

```
|action_metadata.stability - expectation_memory.stability_score| > 0.3
```

Then:

- the update is forbidden
- a `conflict_flag` is created

### 6.4 Implementation guardrails

- `expectation_memory` is maintained as `OrderedDict` for LRU-safe updates.
- `conflict_flag` is cleared at the start of each sleep cycle to avoid stale flags.
- Sleep energy uses normalized cost: `energy_cost = clamp(replay_priority, 0..1)`.
- `last_updated_step` is a monotonic step counter; legacy timestamp values remain timestamp-consistent.


---

## 7. Influence of SWS and REM

### 7.1 SWS

- strengthens `stability`
- decreases `error_likelihood`
- forbids growth of `prediction_shock`

### 7.2 REM

- permits growth of `prediction_shock`
- may lower `confidence`
- raises `td_variance`
- `td_variance` growth is clamped to <= 1.0

---

## 8. Test cases

### TEST 1 — Consolidation of a successful action

**Input:** `td_mean = 0.8`, `td_variance = 0.1`, `confidence = 0.7`.

**Expected:** `stability` increases, `error_likelihood` decreases.

### TEST 2 — Unstable TD

**Input:** `td_mean = 0.7`, `td_variance = 0.8`.

**Expected:** `Δstability ≈ 0`.

### TEST 3 — High prediction_shock

**Input:** `prediction_shock = 0.9`.

**Expected:** `confidence` falls, `error_likelihood` rises, `stability` does not grow.

### TEST 4 — Divergence conflict

**Input:** `EDPC.stability = 0.2`, `SAC.stability = 0.8`.

**Expected:** the update is forbidden, `conflict_flag = True`.

### TEST 5 — Stability overflow

**Input:** the computation yields `stability > 1.0`.

**Expected:** `stability = 1.0`.

---

## 9. Invariants after synchronization

After every sleep the following must hold:

- There are no negative values
- There are no values greater than 1
- There is no `state_key` without a corresponding `action_metadata`
- There is no `action_metadata` without a known `state_key`
- `replay_priority` has been recomputed
- `prediction_shock_score` and `prediction_shock_flag` are distinct; never use `bool(score)`

---

## 10. System guarantees

After adoption:

- `stability` grows through sleep
- EDPC and SAC do not diverge
- `prediction_shock` affects long-term memory
- there are no instantaneous jumps of learning
- the agent remains a "learning organism"

---

## 11. Architectural result

The system now:

- does not merely update actions
- stabilizes the world model by living through experience
- preserves predictive capacity
