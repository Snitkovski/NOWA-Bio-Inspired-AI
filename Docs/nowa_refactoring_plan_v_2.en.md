# NOWA — Refactoring Plan (final version)

Russian version: [nowa_refactoring_plan_v_2.ru.md](nowa_refactoring_plan_v_2.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

The document is intended for a **practical reworking of the NOWA project** without loss of its ideology.
It is not a description of "how things ought to be", but an **engineering plan of action**, meant for stepwise implementation.

---

## 0. Basic Principle (not open to discussion)

> **Behaviour is not learned. It emerges.**  
> **Only memory is learned, through lived experience and sleep.**

Any code that violates this principle is an architectural error.

---

## 1. Architectural Aim of the Refactoring

Move the project:

- out of an ML-like or RL-like system
- out of the optimization of behaviour
- out of training the selector

into a **historical cognitive architecture**, in which:
- experience is irreversible
- memory is conflictual
- behaviour is nondeterministic only when it must be

---

## 2. Global Prohibitions (remove or isolate)

### Wholly forbidden concepts

If they appear in the code, that is an error:

- `epoch`, `accuracy`, `loss`
- `train()`, `retrain()`
- `selector.learn()`
- optimization of weights
- selection of the "best" experience

---

## 3. Path / Experience — fixing the ontology

### What to do

1. Declare `Path` / `Experience` **immutable** after completion
2. Each experience stores:
   - context
   - action
   - consequence (event)
   - intensity (not reward)
   - timestamp

### What is forbidden

- updating weights inside a Path
- strengthening a Path directly
- aggregating Paths by context

---

## 4. Reward to Consequence

### Refactoring

- `reward` is no longer used as a number for learning
- it is converted into an `Event`:

```python
Event(type="positive" | "negative", magnitude, timestamp)
```

- the event affects only the **intensity of the experience**

---

## 5. Hippocampus — a journal of a life

### Permitted functions

- storage of recent Experience records
- degradation over time
- strengthening of repeated patterns
- selection for sleep

### Forbidden

- training the selector
- choosing an action
- aggregation of the "best" experiences

---

## 6. Sleep — the only path of generalization

### Obligatory steps of sleep

1. Clustering of repeated Experience records
2. Formation of abstract patterns
3. Transfer of patterns into the Cortex
4. Weakening of singleton and noisy experiences

### Principle

> **Without sleep there is no learning.**

---

## 7. Cortex — slow memory

### Properties

- it does not react instantly
- it does not store raw Paths
- it degrades slowly

### Functions

- bias toward actions
- stabilization of behaviour
- formation of habits

---

## 8. Selector — a mechanism that is NOT trained

### The selector:

- has no weights
- has no memory
- is not updated

### It only:

1. Receives active Experience records
2. Receives cortical patterns
3. Aggregates pressure
4. Checks dominance
5. Under conflict, allows variability

---

## 9. Confidence Mechanism (required)

Add:

```text
confidence = max_pressure / total_pressure
```

- if `confidence > threshold`, the choice is deterministic
- if it is lower, the choice is probabilistic

This removes "random behaviour".

---

## 10. Dataset / Loading of Experience (permitted)

### Interpretation

A dataset is an accelerated childhood, or innate reflexes.

### Conditions of admissibility

- it is played **once**
- it is not used for optimization
- it passes through the Hippocampus and Sleep

---

## 11. Project Files: what to do with each

### Remove or isolate

- `trainer.py`

### Rewrite

- `selector.py` — remove learning
- `experience.py` — make it immutable
- `hippocampus.py` — remove optimization
- `sleep.py` / `sleep_manager.py` — make this the only learning mechanism

### Keep, with minimal edits

- `dataset.py`
- `loader.py`
- `train_from_dataset.py`

---

## 12. Order of Implementation (strict)

1. Remove selector learning
2. Remove the trainer
3. Fix Experience
4. Correct the hippocampus
5. Implement a confidence-based selector
6. Strengthen sleep and consolidation

---

## 13. Criterion of a Correct Implementation

The system:

Forbidden:

- retraining
- optimization
- a reset that does not lose identity

But it is possible:

- to live through new experience
- to change behaviour over time

---

## 14. Final Check

Ask this question:

> "If I freeze the selector and give the agent new experience, will behaviour change?"

- If **yes**, this is NOWA
- If **no**, this is machine learning

---

**This document is a contract.**
Any departure from it must be conscious and explicitly recorded.
