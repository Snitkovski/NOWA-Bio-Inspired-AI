# Ошибка загрузки датасета — исправлена

English version: [DATASET_LOADING_FIX.en.md](DATASET_LOADING_FIX.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Проблема

При попытке загрузить опыты из датасета (файл JSON) интерфейс показывал ошибку:

```text
Ошибка при загрузке: 'Path' object has no attribute 'add'
```

## Корневая причина

Файл `loader.py` использовал прежний интерфейс:

```python
exp_path.add(Event(event_name))  # прежний интерфейс
```

Перестроенная архитектура использует:

```python
exp_path = exp_path.add_event(Event(event_name, EventType.CONTEXT))  # текущий интерфейс
```

Причины:
1. `Path` теперь неизменяем (функциональный стиль)
2. `.add_event()` возвращает **новый Path** и не изменяет путь на месте
3. События теперь требуют параметр `EventType` (`CONTEXT`, `ACTION`, `CONSEQUENCE`)

## Решение

### Исправление `loader.py`

**До:**

```python
exp_path.add(Event(event_name))
exp_path.add(Event(f"action:{action_name}"))
reward = float(row.get("reward", 0))
experience = Experience(exp_path, reward)
```

**После:**

```python
exp_path = exp_path.add_event(Event(event_name, EventType.CONTEXT))
exp_path = exp_path.add_event(Event(f"action:{action_name}", EventType.ACTION))
intensity = max(0, min(2, reward + 1))  # Map reward [-1,1] to intensity [0,2]
experience = Experience(exp_path, intensity=intensity)
```

Основные изменения:
1. Используется `.add_event()` вместо `.add()`
2. Возвращаемое значение сохраняется: `exp_path = exp_path.add_event(...)`
3. Передаются `EventType.CONTEXT` и `EventType.ACTION`
4. `Event` и `EventType` импортируются в начале модуля
5. `reward` преобразуется в `intensity` (диапазон 0–2)

### Исправление `gui.py`

Метод `_add_experiences_to_agent()` обновлён так, чтобы корректно создавать события последствия.

**До:**

```python
self.hippocampus.store(experience.path, experience.intensity)
```

**После:**

```python
consequence = Event('success', EventType.CONSEQUENCE)
self.hippocampus.store(experience.path, consequence=consequence, intensity=intensity)
```

Основные изменения:
1. Создаётся надлежащее событие `consequence` с `EventType.CONSEQUENCE`
2. Оно передаётся именованным аргументом в `hippocampus.store()`
3. `intensity` извлекается из опыта с запасным значением 1.0

## Результаты испытаний

### Испытание загрузки датасета

```text
Загрузка опытов из datasets/test.json...
   Загружено 2 опыта

Запись в hippocampus...
   ['user:кто ты', 'action:ответить_кто_я']
   ['user:привет', 'action:сказать_привет']

Состояние агента:
   Опытов: 2
   Паттернов: 0

Запуск консолидации сна...
   Сон завершён

После сна:
   Опытов: 2
   Циклов сна: 1

ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ ПРОЙДЕН
```

### Все тесты по-прежнему проходят

```text
Ran 81 tests in 0.137s
OK
```

## Изменённые файлы

1. **src/loader.py**
   - Добавлены импорты: `Event`, `EventType`
   - `load_experience_from_dataset()` переведён на новый интерфейс
   - Значения reward отображаются в диапазон intensity [0, 2]

2. **src/gui.py**
   - `_add_experiences_to_agent()` создаёт события последствия
   - `hippocampus.store()` вызывается со всеми необходимыми параметрами

## Порядок использования

Кнопка интерфейса «Загрузить датасет» теперь работает корректно:

1. Нажать **Загрузить датасет**.
2. Выбрать файл JSON формата:

   ```json
   [
     {
       "context": ["user:question"],
       "action": "action_name",
       "reward": 1
     }
   ]
   ```

3. Система загружает опыты в hippocampus.
4. Сообщение: «Загружено N опытов».
5. Нажать **Сон**, чтобы выполнить консолидацию.

## Справка по интерфейсу

### Прежний (сломанный) интерфейс

```python
path = Path()
path.add(Event("name"))  # изменяет на месте
exp = Experience(path, reward=1.0)  # использует reward, а не intensity
```

### Текущий (исправленный) интерфейс

```python
path = Path()
path = path.add_event(Event("name", EventType.CONTEXT))  # возвращает новый Path
exp = Experience(path, intensity=1.0)  # использует intensity в [0, 2]
```

## Статус

Ошибка исправлена. Все тесты проходят. Загрузка датасета работает. Интерфейс функционален и готов к использованию.

---

*Исправлено: 18 января 2026 г.*
