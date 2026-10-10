# Phase 5 — Experience-Driven Predictive Consolidation (EDPC)

Russian version: [spec_phase5_edpc.ru.md](spec_phase5_edpc.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Architectural aim

Add a mechanism:

> **repeatable experience → stable expectation → confidence → selective plasticity**

Without introducing a centralised "world model".

---

## 1. Position in the architecture

```
External Input
    ↓
Perceptual Encoding
    ↓
Hippocampus (novelty)
    ↓
CER (affect)
    ↓
ACC (conflict)
    ↓
TD (adaptive)
    ↓
Phase 5 (EDPC)
    ↓
Sleep Replay
    ↓
Value Storage
```

Phase 5 operates after the TD delta, but it affects:

- `effective_alpha`
- `consolidation_weight`
- `replay priority`
- `stability_score`

---

## 2. Central idea

Introduce not a "world model", but an **Expectation Memory**.

For each `(state, action)` or abstract pattern the following are stored:

```
expected_reward_mean
expected_reward_var
confirmation_count
confidence_score
stability_score
```

---

## 3. Module 1 — Expectation Tracker (ET)

Updated on every TD step.

**Update of the mean:**

```
expected_reward_mean ← EMA(reward)
```

**Update of the variance:**

```
expected_reward_var ← EMA((reward - mean)^2)
```

**Confirmation:**

```python
if abs(delta) < confirmation_threshold:
    confirmation_count++
else:
    # частичный decay
```

---

## 4. Module 2 — Confidence Accumulator (CA)

Confidence expresses: *"I expect this with high confidence"*.

```
confidence_score = sigmoid(
    k1 * confirmation_count
    - k2 * expected_reward_var
)
```

**Invariants:**

- `confidence ∈ [0, 1]`
- it does not grow without repeated confirmations
- it falls under systematic violations of expectations

---

## 5. Module 3 — Stability Reinforcement (SR)

Stability expresses how firmly the knowledge is fixed.

```
stability_score ←
    stability_score
    + stability_growth_rate * confidence
    - stability_decay_rate * surprise
```

Where:

```
surprise = abs(delta) * confidence
```

> If `confidence` is low, surprise barely strikes stability.

---

## 6. Modification of learning

### Effective alpha

```
effective_alpha =
    alpha * (1 - confidence * stability_damping)
```

This means:

- stable expectations are learned **more slowly**
- new patterns are learned **quickly**

---

## 7. Shock detection (organismic)

Condition:

```python
if confidence > high_threshold and abs(delta) > shock_threshold:
    # регистрируется "prediction shock"
```

**Effects:**

- a temporary rise in plasticity
- a temporary strengthening of replay
- CER stress increases

> This is an analogue of cognitive dissonance.

---

## 8. Replay prioritisation

```
priority =
    abs(delta)
    * (1 + shock_flag)
    * (1 - stability_score)
```

> What is repeatable and stable does not dominate replay.

---

## 9. What occurs in the end

### Repeatable stable experience

`confidence` increases → `stability` increases → `alpha` decreases → `surprise` decreases

→ an expectation is formed → the agent "knows" that the sun will rise.

### New experience

`novelty` increases, `confidence` is low, `alpha` is high → rapid learning.

### Violation of a stable expectation

shock → stress → `plasticity` increases → `replay` increases → a deep reorganisation.

---

## 10. Why this remains an organism

- everything is bound to the experience of `delta`
- there is no external volatility calculator
- there is no centralised world map
- prediction = stabilised experience

---

## 11. Test scenarios with external data

### Test 1 — Stable external stream

A synthetic time series with low noise and identical reward events.

**Expected:** `confidence → 1`, `stability → 1`, `alpha → minimal`.

### Test 2 — Noisy series without a trend

`reward = mean + random noise`.

**Expected:** `expected_mean` stabilises, variance is high, confidence is moderate, stability is medium.

### Test 3 — Structural shift

100 steps of `reward = 1`, then `reward = 5`.

**Expected:** confidence is first high → then shock → stability is partly destroyed → `alpha` rises temporarily.

### Test 4 — Reading a book (simulated)

External text is encoded as: `novelty_score`, semantic similarity to existing patterns, `affect_valence`.

- If the text repeats known ideas: `confidence` increases, `stability` increases
- If it contradicts them: `conflict` increases, shock is possible

### Test 5 — Learning a new skill

A series of new `state → action → reward` triplets.

**Expected:** rapid formation of an expectation → gradual growth of confidence → decline of plasticity.

---

## 12. Metrics for validation

The following must be logged:

- the distribution of `confidence`
- the distribution of `stability`
- shock frequency
- the trajectory of `effective_alpha`
- the replay diversity index

---

## 13. Criterion of success for the phase

Phase 5 is successful if:

- The agent does not overfit to noise
- It forms stable expectations
- It reacts sharply to the violation of stable expectations
- It can learn from a textual or numerical external stream

---

## 14. Important

We do not build a world model. We build:

> a system that becomes less and less surprised in repeating situations and more sensitive to genuine change.

**This is biological predictivity.**
