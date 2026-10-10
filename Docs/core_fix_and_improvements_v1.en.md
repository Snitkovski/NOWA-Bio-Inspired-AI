# Thin Spots and Anti-Patterns of the Current Architecture

Russian version: [core_fix_and_improvements_v1.ru.md](core_fix_and_improvements_v1.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


This document is intended **for the developer agent**. The aim is to stabilize the foundation (Phase 2–3), remove hidden logical errors, and prevent architectural drift **before further expansion**.

---

## 1. General Principle (Critical)

> **No module may make decisions unless it is a selection module.**

Neuromodulators, sleep, age, affect, and PFC are **modulation modules**, not selection modules.

Any place where:
- a coefficient turns into "pressure",
- a baseline turns into an "opinion",
- memory turns into an "intention",

is an architectural error.

---

## 2. Neuromodulators — Thin Spots

### 2.1 Baseline versus Current Value (a frequent error)

**Problem:**
- the baseline is used as the current state

**Correct:**
- the baseline is the attraction point of decay
- the current value is a dynamic deviation

Anti-pattern:
```text
learning_rate = dopamine_baseline
```

Correct:
```text
learning_rate = f(current_dopamine - baseline_dopamine)
```

---

### 2.2 Accumulation without a Ceiling

Check:
- all updates
- sleep learning
- habit consolidation

Error:
- monotonic growth without a competitive mechanism

Requirement:
- there is always:
  - clamp
  - decay
  - forgetting

---

## 3. Sleep / Consolidation — Hidden Risks

### 3.1 Sleep as a "Second Learning" (Forbidden)

**Sleep must not:**
- make decisions
- strengthen what was not selected

Sleep may:
- strengthen what was selected
- weaken noise

Anti-pattern:
```text
if outcome > 0:
    strengthen_action()
```

without a check that the action was actually selected.

---

### 3.2 REM and Non-REM Must Not Be Mixed

Check:
- REM → habits, associations
- Non-REM → pruning, stabilization

Error:
- a single sleep update for everything

---

## 4. Basal Ganglia — The Most Dangerous Places

### 4.1 Habit as an "Autopilot" (Critical)

A habit:
- **increases probability**
- **does not guarantee selection**

Anti-pattern:
```text
if habit_strength > threshold:
    select_action()
```

Only as an addition to Net:
```text
Net += habit_strength * small_gain
```

---

### 4.2 PFC Pressure Must Not Be Made Absolute

PFC is **advice**, not a command.

Check:
- the scale of the pressure
- the influence of fatigue

Error:
- PFC can completely override the basal ganglia

---

### 4.3 Absence of Negative Learning

Check:
- negative outcomes really:
  - decrease Go
  - strengthen NoGo

If they do not, the agent becomes compulsive.

---

## 5. Wakefulness — a Frequent Logical Error

### 5.1 Fatigue Is Not Weakness

Fatigue:
- increases noise
- reduces precision

Error:
```text
if tired:
    reduce_all_signals()
```

Correct:
- noise increases
- variance increases
- advisory contribution decreases

---

## 6. Temporal Levels — a Hidden Conflict

Check:
- T0 does not use PFC
- T3 does not drive the basal ganglia directly

Error:
- a jump across levels

---

## 7. Lifetime / Age — Preparation (but Not the Introduction of Feelings)

### 7.1 Age Is Context, Not a Signal

Forbidden:
- Age → reward
- Age → threat
- Age → affect

Permitted:
- Age → baseline
- Age → plasticity
- Age → sleep coefficients

---

## 8. General Architectural Prohibitions (Checklist)

The agent must not:
- know that it "acted well" without a reward
- feel without a body or time
- choose without the basal ganglia
- learn without sleep
- have a character without a history

---

## 9. Criterion of Readiness for the Next Phase

One may proceed if:
- there is no module that simultaneously:
  - modulates
  - selects
  - learns

- every coefficient has:
  - a ceiling
  - a floor
  - decay

---

**After these places are fixed, it is safe to move further.**
