# Адаптивный «рот» — краткая справка

English version: [ADAPTIVE_MOUTH_QUICK_REFERENCE.en.md](ADAPTIVE_MOUTH_QUICK_REFERENCE.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Основная идея (одно предложение)

**NOWA выбирает, что сказать (намерение); система выбирает, как это сказать (форма).**

---

## Новые компоненты

### ActionIntent

```python
from action_intent import ActionIntent, IntentType

intent = ActionIntent(IntentType.GREET_USER, {"formality": "casual"})
```

- **Что это:** намерение, выбранное селектором (не текст)
- **Типы:** RESPOND_ABOUT_SELF, GREET_USER, REFUSE, HELP_USER, ASK_QUESTION, EXPRESS_CONFUSION, ACKNOWLEDGE

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

- **Что это:** одна конкретная форма выражения намерения
- **Ключевые поля:**
  - `intent_type` — какое намерение реализует
  - `output` — текст, который выводится
  - `intensity` — значимость или предпочтение (0–2)
  - `activation_energy` — как часто используется (увеличивается при использовании, деградирует при сне)

### ActionRealizer

```python
from action_realizer import ActionRealizer
from action_intent import RealizationMemory

memory = RealizationMemory()
realizer = ActionRealizer(memory)

response = realizer.realize(intent, context=["user:привет"])
```

- **Что это:** адаптивный «рот» — выбирает форму выражения
- **Как работает:** выбирает из `RealizationExperience` по давлению активации
- **Важно:** не генерирует текст, только выбирает из опыта

### ActionRealizerWithSelector

```python
from action_realizer import ActionRealizerWithSelector

converter = ActionRealizerWithSelector(realizer)
response = converter.convert_and_realize("помочь", context)
```

- **Что это:** адаптер для интеграции с селектором
- **Использование:** преобразует имена действий в `ActionIntent`, затем в текст

---

## Типичный поток

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

## Загрузка реализаций

### Из датасета

```python
from loader import load_realizations_from_datasets

realizations = load_realizations_from_datasets()
for real in realizations:
    memory.store(real)
```

### Вручную

```python
from action_intent import RealizationExperience, IntentType

real = RealizationExperience(
    intent_type=IntentType.GREET_USER,
    output="Привет!",
    intensity=1.0
)
memory.store(real)
```

### Формат датасета

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

## Механизм выбора

### 1. Расчёт давления

Для каждой реализации:

```
давление = activation_energy × релевантность_контекста
```

### 2. Выбор по уверенности

```python
confidence = max_pressure / total_pressure

if confidence > 0.7:
    # Уверены - выбираем максимум (детерминированно)
    chosen = max_pressure_realization
else:
    # Неуверены - выбираем вероятностно
    chosen = random.choices(realizations, weights=pressures)
```

### 3. Активация выбранной формы

```python
chosen_realization.activate()  # activation_energy растет
```

---

## Сон и деградация

```python
# Во время сна
memory.degrade_all(factor=0.95)

# Каждая реализация теряет 5% активации
# Редко используемые формы забываются

for real in all_realizations:
    real.activation_energy *= 0.95  # Деградация
```

---

## Что удалено

### Жёсткие if/else (прежнее состояние)

```python
def get_response(action):
    if action == "ответить_кто_я":
        return "Я NOWA"
    if action == "сказать_привет":
        return "Привет!"
    return "Я не знаю"
```

### Вместо этого (текущее состояние)

```python
response = realizer_with_selector.convert_and_realize(action)
# Автоматически выбирает из RealizationExperience
```

---

## Быстрый старт

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

## Давление активации

**Что такое activation_energy?**

- Начальное значение: 1.0
- Увеличивается при использовании: +0.1 за раз (максимум 2.0)
- Деградирует при сне: ×0.95
- Скрывается при низком значении: ниже 0.3

**Пример:**

```
Реализация 1: "Привет!"              activation_energy = 1.5 (часто используется)
Реализация 2: "Привет! Как дела?"    activation_energy = 0.8 (редко)
Реализация 3: "Привет, друг!"        activation_energy = 0.2 (почти забыта)

Выбор при высокой уверенности → Реализация 1 (максимальное давление)
Выбор при низкой уверенности → Вероятностный выбор между 1 и 2
```

---

## Ключевые принципы

1. **NOWA выбирает намерение** — система выбирает форму
2. **Форма — это опыт** — не логика, не код, не генерация
3. **Нет if/else** — адаптивный выбор из памяти
4. **Расширяемость** — новые датасеты, нет изменений кода
5. **Деградация** — редкие формы забываются при сне

---

## Связанные файлы

- [Полный план](refactoring_plan_adaptive_mouth.ru.md)
- [Итоговый отчёт](ADAPTIVE_MOUTH_REFACTORING_COMPLETE.ru.md)
- [Тесты](test_adaptive_mouth.py) — запуск: `python test_adaptive_mouth.py`
- [Датасеты](datasets/) — `realizations_basic.json`, `realizations_advanced.json`

---

## Статус

- Архитектура реализована
- Все компоненты созданы
- Тесты пройдены (7/7)
- GUI интегрирована
- Датасеты загружаются
- Готово к использованию
