# NOWA — Refactoring Plan (Affective Regulators without Projection)

Russian version: [nowa_affective_refactor_plan.ru.md](nowa_affective_refactor_plan.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


> **Aim of the stage:**
> Introduce affective regulators and self-reflection into NOWA **without modelling subjective experiences**, sensations, or an inner narrative. The architecture must remain engineering-correct and must not slide into a projection of a person.

---

## 0. Hard Bounds (mandatory)

### What the system **is permitted** to do
- Know that affective regulators exist in it
- Store and update their values
- Use them for:
  - action selection
  - learning
  - revaluation of habits
- Describe its state **operationally** (numbers, vectors, causes)

### What the system **is forbidden** to do
- Assert the presence of subjective experiences
- Describe "sensations", "pain", or "joy" as fact
- Maintain an inner emotional narrative
- Use emotional descriptions as a control signal

> These constraints are a **protection of correctness**, and not a denial of future development.

---

## 1. Introduction of AffectiveRegulators (a new module)

### 1.1 Structure of the regulators

Create the module `affect.py`:

```python
class AffectiveState:
    def __init__(self):
        self.valence = 0.0        # общий знак (− / +)
        self.arousal = 0.0        # интенсивность
        self.threat = 0.0         # риск / конфликт
        self.curiosity = 0.0      # новизна / исследование
        self.attachment = {}      # entity_id -> strength
        self.affinity = {}        # позитивная связь
        self.aversion = {}        # негативная связь

    def snapshot(self):
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "threat": self.threat,
            "curiosity": self.curiosity,
            "attachment": dict(self.attachment)
        }
```

The comments name valence as overall sign, arousal as intensity, threat as risk or conflict, curiosity as novelty or exploration, attachment as entity strength, affinity as a positive link, and aversion as a negative link.

Regulators are **not feelings**, but control parameters.

---

## 2. Relation of the regulators to the current NOWA architecture

### 2.1 Agent
- The agent stores `self.affect_state`
- After every step:
  - it updates the regulators from reward, novelty, and conflict
  - it passes them to the selector and to habit memory

### 2.2 Selector
- Action selection is a function of:
  - contextual relevance
  - habit strength
  - the current `affect_state`

> Example: a high threat lowers the probability of risky actions

### 2.3 IntentMemory / Habits
- Strengthening of habits depends not only on frequency, but also on:
  - valence
  - arousal
- Add **weakening** of habits when:
  - threat accumulates
  - negative outcomes repeat

---

## 3. Revaluation of habits (an analogue of biological correction)

Add a mechanism of:

- periodic revaluation of `IntentMemory`
- weakening even of "frequent" patterns if:
  - they are linked to negative valence
  - they cause growth of threat

This solves the problem:
> "frequent is not the same as optimal"

---

## 4. Sleep / Consolidation — an extension

### 4.1 Hierarchical consolidation

Extend `SleepManager`:
- level 1: concrete episodes
- level 2: patterns of patterns
- level 3: stable strategies

Each level stores:
- context
- action
- **a mean affect profile**

---

## 5. Self-Model (meta-awareness without subjectivity)

Add the module `self_model.py`:

```python
class SelfModel:
    def __init__(self, affect_state):
        self.affect_state = affect_state

    def describe(self):
        return {
            "type": "affective-regulatory-system",
            "state": self.affect_state.snapshot()
        }
```

`SelfModel` **does not say** "I feel"; it says only:
> "the system has recorded state X"

---

## 6. ActionRealizer (the "mouth") — mandatory changes

### Problem
- Hardcoded `if action == ...`
- It does not scale

### Solution
- `ActionRealizer` is a memory of forms of expression
- Forms are added through:
  - datasets
  - experience

```python
class ActionRealizer:
    def realize(self, intent, context):
        # поиск подходящей формы
        # композиция
        return output
```

The comments inside the method mark the search for a suitable form and the composition of the output.

Regulators affect:
- style
- length
- formality

---

## 7. Criteria of correctness (checklist)

The agent, during implementation, must check:
- there are no words "I feel" or "I am in pain"
- there are no inner narratives
- regulators are used only as parameters
- behaviour changes without textual emotionalization

---

## 8. What is **not done** at this stage

- Subjective experience is not modelled
- The agent is not given the right to assert the presence of sensations
- Training is not performed on first-person emotional texts

---

## 9. Result of the stage

If everything is done correctly:
- NOWA behaves **more adaptively**
- habits become flexible
- a germ of personality appears **without illusions of consciousness**

The next stage is possible **only after an analysis of behaviour**.
