# Phase 2 — Neuromodulators (Neuromodulation v2)

Russian version: [phase_2_neuromodulators_v_2.ru.md](phase_2_neuromodulators_v_2.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Status
**Architectural specification.**
Binding on the agent at implementation.

---

## 0. Purpose of the phase

Phase 2 introduces a **biologically motivated neuromodulator system** as *global regulators* of:

- learning rate
- time horizon
- stability / plasticity
- response to reward, uncertainty, and conflict

Neuromodulators do **not**:
- make decisions
- select actions
- replace affect / intent / selector

They **modulate**, but do not control directly.

---

## 1. Principled position in the architecture

```
[ Environment ]
      ↓
[ Signals: reward / novelty / conflict ]
      ↓
[ Neuromodulators ]  ← медленные, глобальные
      ↓
[ Affect / Learning / Consolidation / Prediction ]
      ↓
[ Selector / Action ]
```

Key idea:
> **Neuromodulators change the rules by which the system changes, but not its choice at the moment.**

---

## 2. Set of neuromodulators (mandatory minimum)

### 2.1 Dopamine (DA)
**Function:** reward prediction error, reinforcement

- strengthens consolidation
- raises the probability of repeating patterns
- accelerates learning

### 2.2 Serotonin (5-HT)
**Function:** stability, time horizon

- reduces impulsivity
- increases the value of long-term states
- stabilizes habits

### 2.3 Norepinephrine (NE)
**Function:** uncertainty, wakefulness

- strengthens the response to novelty
- raises exploratory behavior
- increases sensitivity to signals

### 2.4 Cortisol (CORT)
**Function:** stress, threat

- strengthens forgetting of weak traces
- reduces learning under overload
- raises avoidance

---

## 3. Common properties of neuromodulators

- Value range: **[0.0 – 1.0]**
- There is a baseline (by default ~0.1)
- There is temporal decay
- They change **slowly**

No jumps greater than 0.3 in a single step.

---

## 4. Formal update rules

### 4.1 Input signals

- `reward` ∈ [-1.0 ; +1.0]
- `novelty` ∈ [0.0 ; 1.0]
- `conflict` ∈ [0.0 ; 1.0]

---

### 4.2 Dopamine

```python
if reward > 0:
    DA += 0.25 * reward
elif reward < 0:
    DA -= 0.10 * abs(reward)
```

Additionally:
- DA up implies learning_rate up
- DA up implies consolidation_strength up

---

### 4.3 Serotonin

```python
if reward > 0 and conflict == 0:
    HT += 0.05 * reward

if stable_repetition:
    HT += 0.01
```

Effects:
- learning_rate down
- temporal_discount down (long horizon)

---

### 4.4 Norepinephrine

```python
NE += 0.30 * novelty
NE += 0.15 * conflict
```

Effects:
- exploration up
- temporal_chain_generation up

---

### 4.5 Cortisol

```python
if reward < 0:
    CORT += 0.20 * abs(reward)

CORT += 0.25 * conflict
```

Effects:
- forgetting_rate up
- consolidation_threshold up

---

### 4.6 Temporal decay

Each step:

```python
X = X - (X - baseline) * decay_rate
```

Recommendation:
- `decay_half_life ≈ 60–120` seconds

---

## 5. Integration into the existing system

### 5.1 Affect

- affect does **not control** neuromodulators
- affect **uses** them as coefficients

Example:
```python
effective_arousal = arousal * (1 + NE)
```

---

### 5.2 Sleep / Consolidation

During sleep:
- DA → strengthening of cortical patterns
- HT → stabilization
- CORT → removal of weak traces
- NE → additional formation of chains

---

### 5.3 Selector

Direct influence is forbidden.

Permitted **only indirectly**:
- through affect_modifier
- through prediction_pressure

---

## 6. Hard constraints (anti-abuse)

Forbidden:
- selecting an action on the basis of DA
- writing if DA > X then action
- storing preferences in neuromodulators
- using them as emotions

Permitted:
- changing coefficients
- influencing the rate of forgetting
- changing the weight of prediction

---

## 7. Differences of Phase 2 from the current implementation (v1)

| Criterion | v1 | Phase 2 |
|--------|----|---------|
| Causality | heuristic | reward prediction error |
| Time | nearly static | decay + baseline |
| Role | cosmetic | systemic |
| Link to the future | weak | foundation of Plan C |

---

## 8. Test cases (mandatory)

### TC-1: Positive reinforcement
- reward = +1.0
- expectation: DA up, HT up (weakly)

### TC-2: Negative outcome plus conflict
- reward = -0.8, conflict = 0.6
- expectation: CORT strongly up, DA down

### TC-3: Novelty
- novelty = 1.0
- expectation: NE up, exploration up

### TC-4: Temporal decay
- no signals for 120 seconds
- expectation: all return to baseline

### TC-5: Sleep plus high DA
- expectation: strengthening of cortical patterns

---

## 9. Criterion of phase success

The phase is considered implemented if:

- the system exhibits different behavioral regimes
- without changing the selector
- without hard-coded strategies
- with reproducible tests

---

## 10. Architectural reminder

> Neuromodulators are a **meta-level of regulation**,
> not intelligence and not feelings.

Without them the following are impossible:
- strategy
- prediction
- feelings as processes

---

**End of the Phase 2 specification**
