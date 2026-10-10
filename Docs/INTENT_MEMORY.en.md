# NOWA IntentMemory — Implementation of the Intention-Memory Layer

Russian version: [INTENT_MEMORY.ru.md](INTENT_MEMORY.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Overview

**IntentMemory** is a layer of the NOWA architecture that forms **habits** from repeated context-to-intention links.

### Key properties

- It **does not learn** (no gradients, weights, or optimization)
- It **does not select** actions (the Selector does that)
- It **accumulates** habits from experience
- It **creates pressure** on the selector
- It **weakens** when unused (during sleep)
- It **strengthens** on repetition

---

## Architecture

### 1. IntentTrace — one habit

```python
class IntentTrace:
    intent_type: str           # Что делается ("помочь", "сказать_привет")
    context_signature: str     # Когда это делается (хеш контекста)
    strength: float            # Устойчивость (как часто происходило)
    recency: float             # Свежесть (0-1, затухает со временем)
    timestamp: float           # Когда было последнее использование
```

**Meaning of the fields:**
- `strength` = number of repetitions (starts at 1.0 by default)
- `recency` = exponential decay over time (half-life through hour_life)
- **No reward, no value, no weights.**

### 2. IntentMemory — a collection of habits

```python
class IntentMemory:
    traces: Dict[str, IntentTrace]  # Ключ: intent_type:context_signature
    
    # Методы
    record_trace(context, intent)           # Записать привычку
    activate_by_context(context)            # Получить давление для контекста
    get_dominant_intent(context)            # Главная привычка
    degrade_unused(decay_factor)            # Ослабить редкие
    strengthen_traces(context, intent)      # Укрепить частые
```

---

## Algorithms

### Formation of a habit

```
1. When Agent.step() selects an action:
   - intent_memory.record_trace(context, action) is called

2. If (context, action) is already in memory:
   - strength += 1.0
   - recency = 1.0
   - timestamp = now()

3. Otherwise:
   - a new IntentTrace is created with strength=1.0
```

### Activation by context

```
activate_by_context(context):
    1. Compute context_signature (a hash of the context)
    2. Find every IntentTrace with that signature
    3. For each trace:
       - update recency (exponential decay)
       - compute pressure = strength × recency
    4. Aggregate pressure by intent_type
    5. Return dict: {intent_type: pressure}
```

### Confidence calculation

```
get_dominant_intent(context):
    pressure = activate_by_context(context)
    
    if not pressure:
        return None, 0.0
    
    dominant_intent = max(pressure)
    confidence = dominant_pressure / sum(all_pressures)
    
    return dominant_intent, confidence
```

**Interpretation of confidence:**
- `confidence > 0.95` — very confident, a stable habit
- `0.7 < confidence < 0.95` — confident, a habit is present
- `0.5 < confidence < 0.7` — uncertain, competing habits are present
- `confidence < 0.5` — low confidence, variability is possible

### Degradation (during sleep)

```
degrade_unused(decay_factor=0.8):
    for trace in all_traces:
        trace.strength *= decay_factor  # Слабеет
        
        if trace.strength < min_threshold:
            delete(trace)  # Забывается
```

**Effect:**
- Frequently used habits (`strength > 10`) remain
- Rarely used habits (`strength < 0.5`) are forgotten
- Intermediate habits (`0.5`–`10`) weaken gradually

---

## Integration

### 1. The Agent uses IntentMemory

```python
# В gui.py
self.intent_memory = IntentMemory()
self.agent = Agent(
    hippocampus, cortex, selector, 
    sleep_manager, 
    intent_memory  # ← Добавлено
)

# В agent.py Agent.step()
def step(self, context_events, ...):
    # Запросить давление привычек
    intent_pressure = self.intent_memory.activate_by_context(context_events)
    
    # Передать селектору
    action = self.selector.choose(
        hip_exps, ctx_patterns, 
        intent_pressure=intent_pressure  # ← Используется
    )
    
    # Записать привычку
    self.intent_memory.record_trace(context_events, action)
    
    return action
```

### 2. The Selector uses intent_pressure

```python
# В selector.py
def choose(self, hippocampal_exps, cortical_patterns, 
           intent_pressure=None, ...):
    pressure = {}  # Инициализировать
    
    # ... добавить давление из hippocampus и cortex ...
    
    # Добавить давление из intent_memory (вес 50%)
    if intent_pressure:
        for intent, p in intent_pressure.items():
            pressure[intent] += p * 0.5
    
    # Выбрать действие
    action = select_by_pressure(pressure)
    
    return action
```

### 3. SleepManager consolidates

```python
# В sleep.py
class SleepManager:
    def __init__(self, hippocampus, cortex, intent_memory=None):
        self.intent_memory = intent_memory

    def sleep_cycle(self):
        # ... консолидация опытов в cortex ...
        
        # Консолидация привычек
        if self.intent_memory:
            self.intent_memory.degrade_unused(decay_factor=0.8)
            # Сильные привычки остаются
            # Слабые забываются
```

---

## Usage Examples

### Scenario 1: A habit forms

```python
agent = Agent(...)
context = ["user:кто ты"]

# 5 повторений одного контекста
for _ in range(5):
    action = agent.step(context)

# Результат: привычка "когда user:кто ты, делай X"
intent, confidence = agent.intent_memory.get_dominant_intent(context)
# → intent="ответить_кто_я", confidence=0.98
```

### Scenario 2: A conflict of habits

```python
context = ["user:кто ты"]

# Mix: иногда "ответить_кто_я", иногда "грит_user"
agent.step(context)  # Action: ответить_кто_я
agent.step(context)  # Action: сказать_привет
agent.step(context)  # Action: ответить_кто_я
agent.step(context)  # Action: ответить_кто_я

# Результат: сомнение
intent, confidence = agent.intent_memory.get_dominant_intent(context)
# → intent="ответить_кто_я", confidence=0.57  (низко!)
```

### Scenario 3: Sleep and consolidation

```python
# До сна
print(len(agent.intent_memory.traces))  # 50 traces

# Спим
agent.sleep(cycles=3)

# После сна
print(len(agent.intent_memory.traces))  # 30 traces (редкие забыты)

# Сильные привычки сохранились
intent, conf = agent.intent_memory.get_dominant_intent(context1)
print(conf)  # 0.99 (даже сильнее, чем до сна!)
```

---

## Testing

### Unit tests (22 tests)

File: `tests/test_intent_memory.py`

**Covers:**
- Creation and strengthening of traces
- Activation by context
- Calculation of confidence
- Degradation
- Strengthening
- Habit scenarios

### Integration tests (8 tests)

File: `tests/test_intent_memory_integration.py`

**Covers:**
- Agent + IntentMemory
- Selector + intent_pressure
- Sleep + degrade
- A full behavioural cycle

### How to run

```bash
# Юнит-тесты
pytest tests/test_intent_memory.py -v

# Интеграция
pytest tests/test_intent_memory_integration.py -v

# Оба
pytest tests/test_intent_memory.py tests/test_intent_memory_integration.py -v
```

**Result: 30/30 tests PASSED**

---

## Demonstration

### Running the demo script

```bash
python demo_intent_memory.py
```

**It shows:**
1. Formation of a habit (5 repetitions)
2. A new context, a new habit
3. The selector uses the pressure
4. Sleep consolidates
5. After sleep the habits are stronger

---

## Correctness Criteria

**The system works correctly if:**

- Habits form when one context is repeated
- The selector chooses actions with high confidence
- Under conflicting choices, confidence is low
- Sleep weakens rarely used habits
- Strong habits remain after sleep
- **No learning occurs** (no weights, gradients, or optimization)

---

## Architectural Place in NOWA

```
Context
  ↓
IntentMemory
  ↓ (habit pressure)
Selector + ActionIntent
  ↓
Hippocampus (experience record)
  ↓ (during sleep)
Cortex (consolidation)
  ↓
ActionRealizer (form of expression)
  ↓
Output text
```

**IntentMemory:**
- Creates a **habit** (which action is usually chosen)
- Passes pressure to the **Selector** (a recommendation)
- **Does not itself select the action** (the Selector does that)
- **Is consolidated during sleep** (strengthens or weakens)

---

## Further Development

**Possible improvements:**
- Context windowing (take history into account, not only the last event)
- Temporal decay patterns (different half-lives for different intents)
- Emotional intensity affects the rate of formation and degradation
- Periodic reminder pulses to strengthen important habits

**All of this remains without learning and without optimization.**

---

## Summary

**IntentMemory is:**
- A memory of habits (context to action)
- A three-layer system: trace, then memory, then pressure
- Formed from experience and consolidated in sleep
- A source of pressure on the selector, which does not itself choose
- A stabilizer of behaviour without learning
