# NOWA — Refactoring Plan for IntentMemory (Intention Memory)

Russian version: [nowa_refactoring_plan_intent_memory.ru.md](nowa_refactoring_plan_intent_memory.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


This document describes the **missing layer of the NOWA architecture**, required for correct operation of the selector **without learning and without weights**.

---

## 0. Why this layer is needed (the reason is fixed)

After the selector's learning was removed, the system became:
- honest
- nondeterministic under conflict
- but it **lost the stability of habitual reactions**

The reason:
> the memory of links "context → intention" is absent.

`IntentMemory` **does not teach behaviour**; it **accumulates habits**.

---

## 1. Ontological place of IntentMemory

```
Context
  ↓
IntentMemory  ← (формируется из опыта)
  ↓
Selector (stateless)
  ↓
ActionIntent
```

The diagram states that context feeds intention memory, which is formed from experience, which then feeds a stateless selector, which yields an action intent.

`IntentMemory`:
- does not select
- does not optimize
- does not realize actions

It **creates the pressure of habit**.

---

## 2. New object: IntentTrace

### Structure

```python
class IntentTrace:
    intent_type: str
    context_signature: str
    strength: float
    recency: float
    timestamp: float
```

### Meaning of the fields

- `intent_type` — what is usually done
- `context_signature` — when it is done
- `strength` — frequency and stability
- `recency` — freshness

There is no reward, no weights, and no gradients.

---

## 3. Formation of IntentTrace

An `IntentTrace` is created:
- on every completed `Experience`
- from the pair:

```
(context, action_intent)
```

If a trace with the same `context_signature + intent_type` already exists:
- `strength += 1`
- `recency = now`

If it does not:
- a new one is created

---

## 4. Activation of IntentMemory

On a new input context:

1. `context_signature` is computed
2. every `IntentTrace` with a similar signature is activated
3. pressure is computed:

```
pressure = strength × recency_decay × context_similarity
```

The result is a **distribution of pressure over `intent_type`**.

---

## 5. Passage to the selector

The selector receives:

```python
{
  intent_type_1: pressure_1,
  intent_type_2: pressure_2
}
```

And:
- if there is dominance → a deterministic choice
- if there is conflict → variability

The selector still does not learn.

---

## 6. Sleep and IntentMemory (mandatory)

During sleep:

- rarely used traces weaken
- repeated ones strengthen
- conflicting ones may merge

This forms:
> "usually, in such a situation, I do this"

---

## 7. What IntentMemory does not do

Forbidden:

- to choose an action
- to store text
- to optimize the result
- to have a reward

`IntentMemory` is **a memory of habits, not intelligence**.

---

## 8. Minimal test scenarios

### Scenario A — a habit is formed

Dataset:
```json
[
  {"context": ["user:кто ты"], "intent": "respond_about_self"},
  {"context": ["user:кто ты"], "intent": "respond_about_self"},
  {"context": ["user:кто ты"], "intent": "respond_about_self"}
]
```

Expectation:
- a confident, deterministic choice

---

### Scenario B — a conflict of habits

```json
[
  {"context": ["user:кто ты"], "intent": "respond_about_self"},
  {"context": ["user:кто ты"], "intent": "greet_user"}
]
```

Expectation:
- lowered confidence
- variability

---

## 9. Criterion of a correct implementation

The system must:

- not have learning of the selector
- not have weights
- stabilize under repetition
- doubt under conflict

---

## 10. Control question

> "If I freeze the selector completely, but continue to supply experience, will the behaviour change?"

If **yes**, `IntentMemory` is implemented correctly.

---

**This document is intended for direct handover to the refactoring agent.**
