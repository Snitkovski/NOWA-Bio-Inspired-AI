# План B: реализация темпоральных цепей — краткое начало

English version: [PLAN_B_QUICK_START.en.md](PLAN_B_QUICK_START.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Что нового

**Темпоральные цепи** позволяют агенту NOWA проявлять протостратегическое поведение через ретроспективное приписывание заслуги. Обучения нет, градиентов нет, планирования нет — только лёгкая память последовательностей и смещение по исходу.

## Краткое начало

### 1. Включение цепей (автоматически)

Цепи формируются автоматически во время сна, если инициализирован `SleepManager` с `ChainMemory`:

```python
from sleep import SleepManager

sleep_mgr = SleepManager(hip, cortex, intent_memory)
# chain_memory is created automatically
```

### 2. Обычное обучение агента

```python
agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

# Waking behavior (no chains yet)
for i in range(50):
    context = ["user:question"]
    reward = 1.0 if i < 25 else -1.0
    action = agent.step(context, reward=reward)
    response = agent.realize_action(action)  # or similar
    
    print(f"Action: {action}, Reward: {reward}")
```

### 3. Сон для консолидации (формирует цепи)

```python
# Chain formation happens here!
stats = agent.sleep(cycles=3)

print(f"Chains formed: {stats.get('chains_formed', 0)}")
print(f"Patterns consolidated: {stats['patterns_consolidated']}")
```

### 4. Наблюдение протостратегии

После сна агент проявляет протостратегические предпочтения без явного планирования:

```python
# Agent now slightly prefers action sequences that led to reward
action = agent.step(["user:question"])  # May differ from pure random
```

## Отображение в интерфейсе

### Панель памяти (правая сторона)

Добавленный раздел:

```text
Temporal Chains:
  Цепей: 8
  Ср. стабильность: 0.38
```

### Окно инспектора

Новая область на вкладке сна:
- показывает общее число цепей и метрики стабильности
- отображает подробности процесса формирования

## Как работают цепи

### Формирование (во время сна)

1. Извлечь все имена событий из недавних опытов
2. Построить все подпоследовательности (длиной 2–7 событий)
3. Вычислить ретроспективный **net_affect**:
   - из последствия, если оно доступно
   - иначе из интенсивности опыта
4. Сохранить или обновить цепь вместе с net_affect

### Смещение (во время выбора действия)

1. Сопоставить недавнюю историю событий со всеми цепями
2. Для совпавших цепей: `bias[action] += net_affect × (0.5 + 0.5×stability)`
3. Если других давлений нет, выбрать действие с наибольшим смещением
4. Иначе включить смещение в обычный расчёт давления

## Пример: отложенная оценка

```python
# Scenario A: Positive reward path
agent.step(["user:greeting"], reward=+1.0)  # Context
agent.step(["user:greeting"], reward=+1.0)  # Action A
agent.sleep(cycles=3)  # Forms chain: ("user:greeting", "action:A") → net_affect +1.0

# Scenario B: Same context, different action
agent.step(["user:greeting"], reward=-1.0)  # Action B
agent.sleep(cycles=3)  # Forms chain: ("user:greeting", "action:B") → net_affect -1.0

# Result: Agent now slightly prefers A over B in greeting context
# WITHOUT being told about the connection or learning weights
```

## Основные характеристики

| Свойство | Значение |
| --- | --- |
| **Длина цепи** | 2–7 событий (настраивается) |
| **Триггер формирования** | Только сон |
| **Источник net affect** | Последствие или интенсивность опыта |
| **Сила смещения** | Умеренная (база 0.5 + 0.5×stability) |
| **Тип решения** | Протостратегический (смещённый, не детерминированный) |
| **Требование градиента** | Отсутствует |
| **Требуется планирование** | Нет |
| **Самоописание** | Нарратива нет |

## Испытания

Полные тесты находятся в `tests/test_temporal_chains.py`:

```bash
pytest tests/test_temporal_chains.py -q
```

Все тесты проходят:
- формирование цепей во время сна
- вычисление и применение смещения
- селектор корректно использует смещение цепи
- интеграция с остальными модулями

## Изменённые файлы

- **Новый:** `src/temporal_chains.py` — классы `TemporalChain` и `ChainMemory`
- **Новый:** `tests/test_temporal_chains.py` — модульные тесты плана B
- **Новый:** `Docs/PLAN_B_IMPLEMENTATION.md` — полная техническая документация
- **Изменён:** `src/sleep.py` — шаг формирования цепей
- **Изменён:** `src/selector.py` — логика смещения цепи
- **Изменён:** `src/agent.py` — вычисление смещения цепи
- **Изменён:** `src/gui.py` — отображение статистики цепей

## Статус

Завершено и испытано:
- проходят 168/168 тестов
- полная обратная совместимость
- все требования спецификации выполнены
- документация завершена

## Далее: план C

Ландшафты ценности, дрейф на длинном горизонте и динамика аттракторов T3

---

Подробная техническая документация: [PLAN_B_IMPLEMENTATION.md](PLAN_B_IMPLEMENTATION.ru.md)
