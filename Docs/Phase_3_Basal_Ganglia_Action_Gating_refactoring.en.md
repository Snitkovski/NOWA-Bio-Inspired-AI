**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

# Phase 3: Basal Ganglia / Action Gating (BG-AG)

Russian version: [Phase_3_Basal_Ganglia_Action_Gating_refactoring.ru.md](Phase_3_Basal_Ganglia_Action_Gating_refactoring.ru.md)

## Biologically plausible action selection

Version: v1.0 (final, with the architect's remarks)  
Status: **Implemented at about 85–90%; contracts and scales still need polishing**

---

## 1. Aim of the Phase

Phase 3 implements the agent's **central action-selection mechanism** on the principles of the basal ganglia:

- competition of alternatives (Go / NoGo)
- stochastic choice
- modulation by neuromodulators
- advisory influence of the prefrontal cortex (PFC)
- learning **exclusively in sleep**

Key idea:  
> **The BG choose, the PFC advises, neuromodulators modulate, and sleep teaches.**

---

## 2. Architectural Principles (invariants)

### 2.1 Separation of responsibility
- `Agent` is an orchestrator and does not make decisions
- `BasalGangliaGate` ONLY selects an action
- `BasalGangliaLearning` ONLY learns in sleep
- `ActionChannel` is the local state of one action

Forbidden:
- training the BG during wakefulness
- making decisions outside `BasalGangliaGate`

---

### 2.2 The PFC as advisory (not the centre of the system)
The PFC:
- may strengthen or weaken a choice
- **may be ignored**
- its influence falls with fatigue

This is a biological and architectural safeguard against a psychotic centre.

---

## 3. System Components

### 3.1 ActionChannel

The minimal unit of choice.

**Fields:**
- `go_weight ∈ [0,1]`
- `nogo_weight ∈ [0,1]`
- `habit_strength ∈ [0,1]`
- statistics (selection_count, success_rate)

**Invariants:**
- a channel does not know about other channels
- weights are not required to sum to 1

---

### 3.2 BasalGangliaGate

Implements action selection.

#### Formula (simplified):

```
Go = go_weight * (1 + DA_mod) * (1 + affect_mod)
NoGo = nogo_weight * (1 + CORT_mod)

Net = Go - 0.5 * NoGo
Net += PFC_pressure * wakefulness_modifier
Net += habit_strength * HABIT_GAIN   # RECOMMENDED TO ADD
```

Then:
- softmax(Net / temperature)
- temperature follows norepinephrine

---

### 3.3 Neuromodulation

| Modulator | Role in the BG |
|--------|----------|
| Dopamine | strengthens Go and plasticity |
| Cortisol | strengthens NoGo and inhibition |
| Norepinephrine | entropy of choice |
| Serotonin | habits and stabilization |

**Remark:**  
The current implementation risks a **mismatch of scales**.

**Requirement:**
- either the BG normalizes DA/CORT
- or the contract states that the BG expects normalized values

---

### 3.4 Wakefulness

Used to:
- weaken the PFC
- raise decision noise under fatigue

This is the foundation for:
> Sleep, then offline PFC dampening

---

### 3.5 BasalGangliaLearning (sleep)

Learning is applied:
- ONLY in sleep
- from stored (outcome, DA, CORT, 5-HT)

**Rules:**
- success raises Go and lowers NoGo
- error lowers Go and raises NoGo
- repetition plus 5-HT raises habit
- forgetting is always applied

---

## 4. Architectural Remarks (must be taken into account)

### 1. Inconsistency of scales
The BG expects DA/CORT near 1.0; Phase 2 supplies a baseline near 0.1.

**Solution (one of the following):**
- normalize inside the BG
- fix the contract explicitly

---

### 2. Habit_strength does not take part in selection
Habits are learned, but they **do not affect** Net.

**Minimal correction:**
```
Net += habit_strength * 0.3
```

---

### 3. There is no NO-OP action
The BG always selects an action.

**Recommendation:**
- add a `NO_OP` channel
- high NoGo, low Go
- this allows "doing nothing"

---

## 5. Anti-patterns (forbidden)

- if-else selection of actions
- a direct PFC override of the choice
- BG learning outside sleep
- deterministic choice without temperature
- global state shared across channels

---

## 6. Test Cases

### 6.1 Unit tests

1. **Go dominates**
- DA rises, CORT falls
- the channel with maximal go_weight is expected to be chosen

2. **NoGo dominates**
- CORT rises
- the channel with high nogo_weight is suppressed

3. **PFC advisory**
- identical channels
- PFC_pressure influences the choice but does not guarantee it

4. **Fatigue**
- wakefulness falls
- the influence of the PFC decreases

---

### 6.2 Behavioural tests

5. **Habit**
- repetition of a successful action
- habit_strength rises
- the action is chosen more often even at low DA

6. **Exploration**
- NE rises
- the distribution of choice flattens

7. **Sleep**
- after sleep:
  - successful actions raise Go
  - erroneous actions raise NoGo

8. **NO_OP**
- at high CORT the agent often chooses NO_OP

---

## 7. Status and Readiness

Phase 3:
- architecturally: **complete**
- engineering: **scale and habit corrections are still needed**
- integration: **ready for Phase 4**

---

## 8. What Follows

Recommended order:
1. Polish Phase 3 (the remarks above)
2. Sleep, then offline PFC dampening (deepening of sleep)
3. Phase 4: prediction and forward models
4. Plan C v2 (above the BG, not in place of it)

---

End of the specification.
