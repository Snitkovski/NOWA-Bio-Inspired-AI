# NOWA IntentMemory — Реализация слоя памяти намерений

English version: [INTENT_MEMORY.en.md](INTENT_MEMORY.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Обзор

**IntentMemory** — это слой архитектуры NOWA, который формирует **привычки** из повторяющихся связей контекст → намерение.

### Ключевые характеристики

- **Не обучает** (нет градиентов, весов, оптимизации)
- **Не выбирает** действия (это делает Selector)
- **Накапливает** привычки из опыта
- **Создаёт давление** на селектор
- **Ослабевает** при неиспользовании (во время сна)
- **Укрепляется** при повторении

---

## Архитектура

### 1. IntentTrace — одна привычка

```python
class IntentTrace:
    intent_type: str           # Что делается ("помочь", "сказать_привет")
    context_signature: str     # Когда это делается (хеш контекста)
    strength: float            # Устойчивость (как часто происходило)
    recency: float             # Свежесть (0-1, затухает со временем)
    timestamp: float           # Когда было последнее использование
```

**Смысл полей:**
- `strength` = количество повторений (по умолчанию начинается с 1.0)
- `recency` = экспоненциальный спад со временем (половина через hour_life)
- **Нет награды, нет ценности, нет весов.**

### 2. IntentMemory — коллекция привычек

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

## Алгоритмы

### Формирование привычки

```
1. Когда Agent.step() выбирает действие:
   - вызывается intent_memory.record_trace(context, action)

2. Если (context, action) уже есть в memory:
   - strength += 1.0
   - recency = 1.0
   - timestamp = now()

3. Если нет:
   - создаётся новый IntentTrace с strength=1.0
```

### Активация по контексту

```
activate_by_context(context):
    1. Вычислить context_signature (хеш контекста)
    2. Найти все IntentTrace с этой сигнатурой
    3. Для каждого trace:
       - обновить recency (экспоненциальный спад)
       - рассчитать pressure = strength × recency
    4. Агрегировать давление по intent_type
    5. Вернуть словарь: {intent_type: pressure}
```

### Расчёт уверенности

```
get_dominant_intent(context):
    pressure = activate_by_context(context)
    
    if not pressure:
        return None, 0.0
    
    dominant_intent = max(pressure)
    confidence = dominant_pressure / sum(all_pressures)
    
    return dominant_intent, confidence
```

**Интерпретация уверенности:**
- `confidence > 0.95` — очень уверена, стабильная привычка
- `0.7 < confidence < 0.95` — уверена, есть привычка
- `0.5 < confidence < 0.7` — сомневается, есть конкурирующие привычки
- `confidence < 0.5` — низкая уверенность, может быть вариативность

### Деградация (во время сна)

```
degrade_unused(decay_factor=0.8):
    for trace in all_traces:
        trace.strength *= decay_factor  # Слабеет
        
        if trace.strength < min_threshold:
            delete(trace)  # Забывается
```

**Эффект:**
- Часто используемые привычки (strength > 10) остаются
- Редко используемые (strength < 0.5) забываются
- Средние (0.5–10) постепенно ослабевают

---

## Интеграция

### 1. Agent использует IntentMemory

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

### 2. Selector использует intent_pressure

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

### 3. SleepManager консолидирует

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

## Примеры использования

### Сценарий 1: Привычка формируется

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

### Сценарий 2: Конфликт привычек

```python
context = ["user:кто ты"]

# Смесь: иногда "ответить_кто_я", иногда приветствие
agent.step(context)  # Action: ответить_кто_я
agent.step(context)  # Action: сказать_привет
agent.step(context)  # Action: ответить_кто_я
agent.step(context)  # Action: ответить_кто_я

# Результат: сомнение
intent, confidence = agent.intent_memory.get_dominant_intent(context)
# → intent="ответить_кто_я", confidence=0.57  (низко!)
```

### Сценарий 3: Сон и консолидация

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

## Тестирование

### Модульные тесты (22 теста)

Файл: `tests/test_intent_memory.py`

**Покрывает:**
- Создание и усиление следов
- Активацию по контексту
- Расчёт уверенности
- Деградацию
- Укрепление
- Сценарии привычек

### Интеграционные тесты (8 тестов)

Файл: `tests/test_intent_memory_integration.py`

**Покрывает:**
- Agent + IntentMemory
- Selector + intent_pressure
- Сон + деградацию
- Полный цикл поведения

### Запуск

```bash
# Юнит-тесты
pytest tests/test_intent_memory.py -v

# Интеграция
pytest tests/test_intent_memory_integration.py -v

# Оба
pytest tests/test_intent_memory.py tests/test_intent_memory_integration.py -v
```

**Результат: 30/30 тестов пройдены**

---

## Демонстрация

### Запуск демонстрационного сценария

```bash
python demo_intent_memory.py
```

**Показывает:**
1. Формирование привычки (5 повторений)
2. Новый контекст, новая привычка
3. Селектор использует давление
4. Сон консолидирует
5. После сна привычки сильнее

---

## Критерии корректности

**Система работает правильно, если:**

- Привычки формируются при повторении одного контекста
- Селектор выбирает действия с высокой уверенностью
- При конфликте выборов уверенность низкая
- Сон ослабляет редко используемые привычки
- Сильные привычки остаются после сна
- **Обучения не происходит** (нет весов, градиентов, оптимизации)

---

## Архитектурное место в NOWA

```
Контекст
  ↓
IntentMemory
  ↓ (давление привычки)
Selector + ActionIntent
  ↓
Hippocampus (запись опыта)
  ↓ (во время сна)
Cortex (консолидация)
  ↓
ActionRealizer (форма выражения)
  ↓
Выходной текст
```

**IntentMemory:**
- Создаёт **привычку** (какое действие обычно выбирается)
- Передаёт давление **Selector** (рекомендация)
- **Не выбирает действие сама** (это делает Selector)
- **Консолидируется во время сна** (укрепляется или ослабевает)

---

## Дальнейшее развитие

**Возможные улучшения:**
- Окно контекста (учитывать историю, а не только последнее событие)
- Паттерны временного спада (разный период полураспада для разных намерений)
- Эмоциональная интенсивность влияет на скорость формирования и деградации
- Периодические импульсы напоминания для укрепления важных привычек

**Но всё это остаётся без обучения и оптимизации.**

---

## Резюме

**IntentMemory — это:**
- Память привычек (контекст → действие)
- Трёхслойная система: след, затем память, затем давление
- Формируется из опыта, консолидируется во сне
- Создаёт давление на селектор, но не выбирает
- Стабилизирует поведение без обучения
