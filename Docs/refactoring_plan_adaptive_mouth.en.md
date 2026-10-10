# NOWA — Refactoring Plan for the "Mouth" (Adaptive Realization of Actions)

Russian version: [refactoring_plan_adaptive_mouth.ru.md](refactoring_plan_adaptive_mouth.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

The document is intended for the **transition from hard-coded actions (if/else)** to an **adaptive mechanism for expressing intentions**, compatible with the ideology of NOWA.

---

## 0. Key Principle (fixed strictly)

> **NOWA chooses an intention, not a text.**  
> **The form of expression is the experience of the body, not the logic of behaviour.**

Any code in which an action is mapped directly onto text through `if/else` is an architectural defect.

---

## 1. What Counts as the "Mouth"

The "mouth" is all code that:
- converts an internal action into external output
- forms a text, a message, a signal, or a reply

This layer:
- **does not make decisions**
- **is not optimized**
- **does not influence the selector**

---

## 2. Remove Rigid Constructions

### To be removed

```python
def respond(action):
    if action == "ответить_кто_я":
        return "Я NOWA"
```

### Reason

- the set of reactions is fixed
- new actions are impossible without rewriting the code
- experience cannot extend the repertoire

---

## 3. Introduce ActionIntent (the intention)

### New object

```python
class ActionIntent:
    type: str
    parameters: dict
```

### Examples

- `type="respond_about_self"`
- `type="greet_user"`
- `type="express_confusion"`

NOWA **chooses only an ActionIntent**.

---

## 4. Introduce ActionRealizer (the adaptive "mouth")

### Role

ActionRealizer:
- receives an ActionIntent
- looks up ways of realization in memory
- chooses a form of expression

### Interface

```python
class ActionRealizer:
    def realize(self, intent: ActionIntent, context: list[str]) -> str:
        ...
```

---

## 5. Realization as Experience, Not as a Rule

### New memory type

```python
class RealizationExperience:
    intent_type: str
    parameters: dict
    output: str
    intensity: float
    timestamp: float
```

Each way of expressing something is a **separate experience**.

---

## 6. Loading Datasets (permitted and required)

Datasets may contain **new forms of expression**, even for old intentions.

### Format

```json
{
  "context": ["user:кто ты"],
  "intent": {
    "type": "respond_about_self",
    "parameters": {"style": "neutral"}
  },
  "output": "Я экспериментальный агент NOWA",
  "intensity": 1.0
}
```

This is interpreted as:
> "The agent lived through an experience in which it expressed the intention in this way"

---

## 7. Choosing the Form of Expression (analogue of the selector)

### Algorithm

1. Activate the relevant RealizationExperience records
2. Aggregate pressure by output
3. Compute confidence
4. If one form dominates, choose it deterministically
5. If there is conflict, allow variability

There is no learning, no weights, and no optimization.

---

## 8. Sleep and Degradation (required)

During sleep:
- rarely used forms weaken
- repeated forms build patterns of expression
- noisy realizations are forgotten

This prevents the "cluttering of speech".

---

## 9. What Is Forbidden in ActionRealizer

- generating text from scratch
- optimization against reward
- choosing the "best" reply
- any ML models

---

## 10. Minimal Test Datasets

### Dataset A — basic (deterministic)

```json
[
  {
    "context": ["user:кто ты"],
    "intent": {"type": "respond_about_self"},
    "output": "Я NOWA",
    "intensity": 1.0
  }
]
```

Expectation: always the same reply.

---

### Dataset B — variable style

```json
[
  {
    "context": ["user:кто ты"],
    "intent": {"type": "respond_about_self"},
    "output": "Я NOWA",
    "intensity": 0.8
  },
  {
    "context": ["user:кто ты"],
    "intent": {"type": "respond_about_self"},
    "output": "Я экспериментальный агент NOWA",
    "intensity": 0.7
  }
]
```

Expectation:
- variability at first
- stabilization over time

---

### Dataset C — a new repertoire

```json
[
  {
    "context": ["user:привет"],
    "intent": {"type": "greet_user"},
    "output": "Привет!",
    "intensity": 1.0
  }
]
```

Expectation:
- a new action appears without a change of code

---

## 11. Criterion of a Successful Refactoring

The system must satisfy the following.

Forbidden:

- if/else on actions
- hard-coded reply strings

Required:

- new forms appear through experience
- old forms degrade

---

## 12. Final Check

Control question:

> "Can the agent begin to answer differently
> if I give it a new dataset,
> without changing either the selector or the code?"

If **yes**, the "mouth" is implemented correctly.

---

**This document is intended to be handed directly to the refactoring agent.**
