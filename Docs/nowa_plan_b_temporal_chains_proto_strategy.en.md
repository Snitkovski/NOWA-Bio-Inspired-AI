# NOWA — Plan B

Russian version: [nowa_plan_b_temporal_chains_proto_strategy.ru.md](nowa_plan_b_temporal_chains_proto_strategy.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Temporal Chains, Proto-Strategy, and Credit Assignment (No Gradients)

---

## 0. Preconditions (what already exists)

Plan A is complete and fixed:
- T0 — instantaneous reaction
- T1 — short-term trend
- T2 — baseline (slow drift)
- T3 — attractor (very slow)

Plan B **does not change** these levels. It adds **structures on top of them**.

---

## 1. Purpose of Plan B

Introduce **temporal depth of behaviour** without:
- gradients
- planning of the future
- symbolic goals

The result of Plan B:
- the agent begins to distinguish **sequences**
- **delayed value** appears
- a **proto-strategy** is formed (strategicity without forecasts)

---

## 2. Basic Notion: Temporal Chain (TC)

### 2.1 Definition

A **temporal chain** is a linkage:

```
(context₁ → action₁) → (context₂ → action₂) → … → outcome
```

Properties:
- finite length (3–7 steps)
- does not store a goal
- does not store an expected result
- knows only: "how this usually ends"

---

## 3. New Entity: ChainMemory

### 3.1 Structure

```python
class TemporalChain:
    events: List[Event]
    net_affect: Dict[str, float]
    stability: float
    usage_count: int
```

- `events` — a sequence of context and action
- `net_affect` — the integral of T1/T2 at the end of the chain
- `stability` — stability of the result
- `usage_count` — how many times the chain was lived through

---

## 4. Formation of Chains (without Learning)

### 4.1 During Wakefulness

- the agent stores a **rolling window** of the last N steps
- each step is added as `(context, action, affect_snapshot)`
- the window is not analysed

### 4.2 During Sleep (the key moment)

Only during sleep:
1. the window is cut into subsequences
2. subsequences are grouped by form
3. **net_affect** is computed at the end
4. temporal chains are created or updated

No optimization. Statistics only.

---

## 5. Credit Assignment without Gradients

### 5.1 Principle

> "Good or bad is not the action, but **how it ended**"

### 5.2 Mechanism

- the final affect (T1/T2) is distributed **backward along the chain**
- with exponential decay

```text
step −1: 1.0
step −2: 0.6
step −3: 0.3
```

This is **not reward propagation**, but retrospective correlation.

---

## 6. Use of Chains in Action Selection

### 6.1 Selector (extension)

When an action is selected:
1. the standard `ActionSelector`
2. if suitable temporal chains exist:
   - a **bias** is added, proportional to `net_affect`

Important:
- chains **do not command**
- they slightly incline the choice

---

## 7. Proto-Strategy (what it is and what it is not)

### 7.1 What appears

- preference for sequences
- avoidance of chains with a bad ending
- repeatable "routes of behaviour"

### 7.2 What does not appear

- goals
- plans
- expectations of the future
- a self-description of the strategy

The strategy **is manifested**, but it is not modelled.

---

## 8. Relation to Affective Levels

| Level | Role in Plan B |
|------|----------------|
| T0 | not used |
| T1 | local outcome of the chain |
| T2 | stability of `net_affect` |
| T3 | not used yet |

T3 will be engaged **only in Plan C**.

---

## 9. Constraints (critical)

Forbidden:
- to use future steps
- to use a forecast
- to use goals
- to strengthen chains without sleep

If any of this appears, Plan B is considered violated.

---

## 10. Tests of Plan B

### Test 1 — Delayed Value

- A → B → C → good
- A → D → bad

Expectation:
- over time the agent more often selects B after A

---

### Test 2 — Contextual Strategy

- the same actions
- different contexts

Expectation:
- the chains differ

---

### Test 3 — Without Sleep

- a long session
- without sleep

Expectation:
- chains are not formed

---

## 11. Readiness Criterion for Plan B

Plan B is complete if:
- the agent demonstrates a distinction among chains
- delayed preference appears
- the architecture remains without gradients
- there is no self-narrative

---

## End of Plan B

The next stage is **Plan C: Value Landscapes and Long-Horizon Drift**
