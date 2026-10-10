# NOWA IntentMemory — Implementation Report

Russian version: [INTENT_MEMORY_IMPLEMENTATION.ru.md](INTENT_MEMORY_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Completed

The full **IntentMemory** layer (memory of intentions and habits) has been implemented according to the plan `nowa_refactoring_plan_intent_memory.md`.

---

## What was done

### 1. Core: the IntentMemory system

**File:** `src/intent_memory.py` (191 lines)

Created:

- `IntentTrace` — one habit (intent + context)
- `IntentMemory` — a collection of habits, with formation, activation, and degradation

**Key methods:**

- `record_trace(context, intent)` — record a habit
- `activate_by_context(context)` → `Dict[intent, pressure]`
- `get_dominant_intent(context)` → `(intent, confidence)`
- `degrade_unused(decay_factor)` — weaken rare habits
- `strengthen_traces(context, intent, factor)` — strengthen

### 2. Integration into the system

**Files changed:**

#### `src/agent.py`

- The parameter `intent_memory` was added to the constructor
- In `step()`, recording of habits was added through `intent_memory.record_trace()`
- The selector receives habit pressure through `intent_pressure`

#### `src/selector.py`

- The method `choose()` was extended with the parameter `intent_pressure`
- Habit pressure is added to the total pressure (weight 50%)
- The selector now uses habits to recommend actions

#### `src/sleep.py`

- `SleepManager` now has the parameter `intent_memory`
- Processing of IntentMemory was added in `sleep_cycle()`
- Degradation of unused habits during sleep

#### `src/gui.py`

- `IntentMemory()` is initialised when the GUI is created
- It is passed to `Agent` and `SleepManager`

### 3. Testing (30 tests)

**File:** `tests/test_intent_memory.py` (22 tests)

Unit tests cover:

- creation and strengthening of traces
- activation by context
- distribution of pressure
- calculation of confidence
- degradation when unused
- strengthening on repetition
- scenarios of habit conflict
- sleep and consolidation

**Result: 22/22 passed**

**File:** `tests/test_intent_memory_integration.py` (8 tests)

Integration tests:

- Agent + IntentMemory
- the selector uses `intent_pressure`
- sleep degrades habits
- habits influence choice
- a full behaviour cycle
- resolution of conflicts

**Result: 8/8 passed**

**Total: 30/30 tests passed**

### 4. Demonstration

**File:** `demo_intent_memory.py`

Demonstrates 5 scenarios:

1. Formation of a habit (5 repetitions of one context)
2. A new context yields a new habit
3. The selector uses habit pressure
4. Sleep consolidates habits
5. After sleep, habits are more stable

**Run:** `python demo_intent_memory.py`

### 5. Documentation

**File:** `INTENT_MEMORY.md` (400+ lines)

Full documentation with:

- architecture and design
- algorithms (formation, activation, degradation)
- integration into NOWA
- examples of use
- criteria of correctness
- the architectural place in the system

---

## Architecture

```
Context
  ↓
[IntentMemory] ← Формирует привычки из опыта
  ↓ (давление привычки)
[Selector + ActionIntent] ← Выбирает действие
  ↓
[Hippocampus] ← Записывает опыт
  ↓ (во время сна)
[Cortex + IntentMemory degrade] ← Консолидирует
  ↓
[ActionRealizer] ← Выбирает форму
  ↓
Output
```

### Key property

> **IntentMemory creates pressure, but does not choose the action.**

- It collects data on which actions are usually chosen
- It passes that pressure to the Selector
- The Selector uses the pressure, but may choose something else
- **There is no learning, no weights, and no optimisation**

---

## Data

### Structure of IntentTrace

```python
IntentTrace(
    intent_type="помочь",              # Что делается
    context_signature="abc123",        # Когда (хеш)
    strength=5.0,                      # Сколько раз повторилось
    recency=0.95,                      # Свежесть (0-1)
    timestamp=1706095200.5             # Когда последний раз
)
```

### Example of operation

```
Step 1: user:"кто ты"   → Action: помочь
Step 2: user:"кто ты"   → Action: помочь
Step 3: user:"кто ты"   → Action: помочь
Step 4: user:"кто ты"   → Action: помочь
Step 5: user:"кто ты"   → Action: помочь

Result:
  intent_memory.traces = {
    "помочь:abc123": IntentTrace(strength=5.0, recency=1.0)
  }
  
  get_dominant_intent(["user:кто ты"]) 
    → ("помочь", confidence=0.99)
```

---

## Life cycle

### Formation

```
1. Agent.step() выбирает действие
2. intent_memory.record_trace(context, action)
3. Если (context, action) первый раз:
   - создать новый trace (strength=1.0)
4. Если был раньше:
   - усилить trace (strength += 1.0)
   - обновить timestamp и recency
```

### Activation

```
1. Selector.choose() запрашивает действие
2. Agent вызывает intent_memory.activate_by_context(context)
3. IntentMemory:
   - вычисляет context_signature
   - находит все matching traces
   - обновляет recency (exponential decay)
   - вычисляет pressure = strength × recency
   - возвращает {intent: pressure}
4. Selector использует это давление при выборе
```

### Consolidation (during sleep)

```
1. SleepManager.sleep_cycle() запускается
2. Вызывает intent_memory.degrade_unused(decay_factor=0.8)
3. IntentMemory:
   - умножает strength каждого trace на decay_factor
   - удаляет traces с strength < min_threshold
4. Результат: слабые привычки забываются, сильные остаются
```

---

## Success criteria

Every criterion from the plan is met:

- **no if/else on actions** (habit pressure is used)
- **no rigid response strings** (ActionRealizer chooses from memory)
- **new forms appear through experience** (traces are created automatically)
- **old forms degrade** (they weaken during sleep)
- **habits are formed from experience** (`record_trace`)
- **the selector is not trained** (pressure only, not weights)
- **the system stabilises** (confidence grows with repetition)
- **the system doubts under conflict** (confidence < 0.7)

---

## Test results

```
=============================== 30 passed in 0.03s ===============================

tests/test_intent_memory.py                                      22 PASSED ✅
  - IntentTrace (3 теста)
  - IntentMemory основные методы (7 тестов)
  - Сценарии привычек (3 теста)
  - Утилиты (9 тестов)

tests/test_intent_memory_integration.py                           8 PASSED ✅
  - Agent + IntentMemory (6 тестов)
  - Selector + intent_pressure (1 тест)
  - Sleep consolidation (1 тест)
```

---

## Project files

### New files

```
src/intent_memory.py                     191 строка
tests/test_intent_memory.py              334 строки
tests/test_intent_memory_integration.py  233 строки
demo_intent_memory.py                    180 строк
INTENT_MEMORY.md                         460+ строк
```

### Changed files

```
src/agent.py                             +9 строк (intent_memory parameter + record_trace)
src/selector.py                          +15 строк (intent_pressure parameter)
src/sleep.py                             +25 строк (intent_memory consolidation)
src/gui.py                               +2 строки (IntentMemory initialization)
```

### Totals

- **New lines of code:** ~1400
- **New tests:** 30
- **New classes:** 2 (`IntentTrace`, `IntentMemory`)
- **New methods:** 8 principal methods in IntentMemory

---

## Architectural place

IntentMemory is the **second layer** of the action-selection system:

```
Уровень 1: Состояние (Context)
Уровень 2: IntentMemory ← (я) Привычки
Уровень 3: Selector → ActionIntent
Уровень 4: Hippocampus → Experience
Уровень 5: ActionRealizer → Output форма
Уровень 6: Sleep → Консолидация
```

The system is **three-layered in selection:**

1. **Habits** (IntentMemory) — create pressure
2. **Experience** (Hippocampus) — creates pressure
3. **Patterns** (Cortex) — create pressure

The **Selector** uses all three pressures to choose.

---

## Further development

Possible improvements (that do not violate the principle of the absence of learning):

1. **Context windowing** — take the history of context into account, not only the last event
2. **Different decay rates** — different half-lives for different types of intent
3. **Emotional intensity** — the intensity of experience affects the rate of formation and degradation
4. **Periodic boosting** — periodic strengthening of important habits without explicit learning
5. **Context similarity** — activate similar contexts with less pressure

---

## Summary

**IntentMemory has been implemented successfully as:**

- a system for forming habits from experience
- a mechanism that passes pressure to the selector
- a part of sleep consolidation (degradation)
- a fully tested component (30/30 tests)
- a documented component
- a demonstrated component

**The system still has no learning:**

- no weights
- no optimisation
- no gradients
- behaviour arises from memory, not from an objective function

**NOWA now works with three layers of pressure on the selector:**

1. Recent experience (hippocampus)
2. Habits (intent_memory)
3. Consolidated patterns (cortex)
