# Adaptive "Mouth" — Short Reference

Russian version: [ADAPTIVE_MOUTH_QUICK_REFERENCE.ru.md](ADAPTIVE_MOUTH_QUICK_REFERENCE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Principal idea (one sentence)

**NOWA selects what to say (the intention); the system selects how to say it (the form).**

---

## New components

### ActionIntent

```python
from action_intent import ActionIntent, IntentType

intent = ActionIntent(IntentType.GREET_USER, {"formality": "casual"})
```

- **What it is:** an intention selected by the selector (not text)
- **Types:** RESPOND_ABOUT_SELF, GREET_USER, REFUSE, HELP_USER, ASK_QUESTION, EXPRESS_CONFUSION, ACKNOWLEDGE

### RealizationExperience

```python
from action_intent import RealizationExperience, IntentType

real = RealizationExperience(
    intent_type=IntentType.GREET_USER,
    output="Привет!",
    context=["user:привет"],
    intensity=1.0
)
```

- **What it is:** one concrete form of expressing an intention
- **Principal fields:**
  - `intent_type` — which intention it realises
  - `output` — the text that is emitted
  - `intensity` — significance or preference (0–2)
  - `activation_energy` — how often it is used (increases on use, degrades during sleep)

### ActionRealizer

```python
from action_realizer import ActionRealizer
from action_intent import RealizationMemory

memory = RealizationMemory()
realizer = ActionRealizer(memory)

response = realizer.realize(intent, context=["user:привет"])
```

- **What it is:** the adaptive "mouth" — it selects a form of expression
- **How it works:** it selects among `RealizationExperience` by activation pressure
- **Important:** it does not generate text; it only selects from experience

### ActionRealizerWithSelector

```python
from action_realizer import ActionRealizerWithSelector

converter = ActionRealizerWithSelector(realizer)
response = converter.convert_and_realize("помочь", context)
```

- **What it is:** an adapter for integration with the selector
- **Use:** it converts action names into `ActionIntent`, then into text

---

## Typical flow

```
1. Agent.step(context)           ← Агент выбирает действие
   ↓
2. ActionSelector.choose()       ← "помочь"
   ↓
3. convert_and_realize()         ← Преобразование
   ↓
4. ActionIntent(HELP_USER)       ← Создание намерения
   ↓
5. ActionRealizer.realize()      ← Выбор формы
   ↓
6. RealizationExperience         ← Какая форма использовать?
   ↓
7. "Я здесь, чтобы помочь"      ← Результат!
```

---

## Loading realisations

### From a dataset

```python
from loader import load_realizations_from_datasets

realizations = load_realizations_from_datasets()
for real in realizations:
    memory.store(real)
```

### By hand

```python
from action_intent import RealizationExperience, IntentType

real = RealizationExperience(
    intent_type=IntentType.GREET_USER,
    output="Привет!",
    intensity=1.0
)
memory.store(real)
```

### Dataset format

```json
[
  {
    "context": ["user:привет"],
    "intent_type": "greet_user",
    "output": "Привет!",
    "intensity": 1.0,
    "parameters": {}
  }
]
```

---

## Selection mechanism

### 1. Computation of pressure

For each realisation:

```
давление = activation_energy × релевантность_контекста
```

### 2. Selection by confidence

```python
confidence = max_pressure / total_pressure

if confidence > 0.7:
    # Уверены - выбираем максимум (детерминированно)
    chosen = max_pressure_realization
else:
    # Неуверены - выбираем вероятностно
    chosen = random.choices(realizations, weights=pressures)
```

### 3. Activation of the chosen form

```python
chosen_realization.activate()  # activation_energy растет
```

---

## Sleep and degradation

```python
# Во время сна
memory.degrade_all(factor=0.95)

# Каждая реализация теряет 5% активации
# Редко используемые формы забываются

for real in all_realizations:
    real.activation_energy *= 0.95  # Деградация
```

---

## What was removed

### Hardcoded if/else (former state)

```python
def get_response(action):
    if action == "ответить_кто_я":
        return "Я NOWA"
    if action == "сказать_привет":
        return "Привет!"
    return "Я не знаю"
```

### In its place (present state)

```python
response = realizer_with_selector.convert_and_realize(action)
# Автоматически выбирает из RealizationExperience
```

---

## Quick start

```python
from action_intent import RealizationMemory
from action_realizer import ActionRealizer, ActionRealizerWithSelector
from loader import load_realizations_from_datasets

# 1. Инициализация
memory = RealizationMemory()
realizer = ActionRealizer(memory)
converter = ActionRealizerWithSelector(realizer)

# 2. Загрузка реализаций
for real in load_realizations_from_datasets():
    memory.store(real)

# 3. Использование
action = "помочь"  # От селектора
response = converter.convert_and_realize(action)
print(response)  # Выведет одну из форм реализации
```

---

## Activation pressure

**What is activation_energy?**

- Initial value: 1.0
- Increases on use: +0.1 at a time (maximum 2.0)
- Degrades during sleep: ×0.95
- Is hidden at a low value: below 0.3

**Example:**

```
Реализация 1: "Привет!"              activation_energy = 1.5 (часто используется)
Реализация 2: "Привет! Как дела?"    activation_energy = 0.8 (редко)
Реализация 3: "Привет, друг!"        activation_energy = 0.2 (почти забыта)

Выбор при высокой уверенности → Реализация 1 (максимальное давление)
Выбор при низкой уверенности → Вероятностный выбор между 1 и 2
```

---

## Principal principles

1. **NOWA selects the intention** — the system selects the form
2. **The form is experience** — not logic, not code, not generation
3. **No if/else** — adaptive selection from memory
4. **Extensibility** — new datasets, no code changes
5. **Degradation** — rare forms are forgotten during sleep

---

## Related files

- [Full plan](refactoring_plan_adaptive_mouth.en.md)
- [Closing report](ADAPTIVE_MOUTH_REFACTORING_COMPLETE.en.md)
- [Tests](test_adaptive_mouth.py) — run: `python test_adaptive_mouth.py`
- [Datasets](datasets/) — `realizations_basic.json`, `realizations_advanced.json`

---

## Status

- The architecture is implemented
- Every component is created
- The tests passed (7/7)
- The GUI is integrated
- The datasets load
- Ready for use
