# Habits in the GUI — Full Integration

Russian version: [GUI_HABITS_IMPLEMENTATION.ru.md](GUI_HABITS_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## What was done

### 1. Dataset of habits

**File:** `datasets/habits.json` (15 habits)

It contains the initial habits in the form:

```json
{
  "context": ["user:кто ты"],
  "action": "ответить_кто_я",
  "strength": 3.0
}
```

**Loaded habits:**

- `user:кто ты` → `ответить_кто_я` (strength=3.0)
- `user:привет` → `сказать_привет` (strength=3.0)
- `user:помощь` → `помочь` (strength=2.0)
- `user:помоги` → `помочь` (strength=2.0)
- `user:не понимаю` → `выразить_замешательство` (strength=2.0)
- `user:скажи что-нибудь` → `задать_вопрос` (strength=1.0)
- `user:стоп` → `отказаться` (strength=2.0)
- and others

### 2. Habit-loading functions

**File:** `src/loader.py`

Functions added:

```python
def load_habits_from_dataset(path: str) -> list
    # Загружает привычки из одного JSON файла

def load_habits_from_datasets(base_path: str = None) -> list
    # Загружает все привычки из папки datasets
```

### 3. Integration into the GUI

**File:** `src/gui.py`

Changes:

1. **Import of the loading function:**

   ```python
   from loader import load_habits_from_datasets
   ```

2. **Loading at initialisation:**

   ```python
   def _load_initial_realizations(self):
       # Load realizations (формы ответов)
       realizations = load_realizations_from_datasets()
       
       # Load habits (привычки контекст->действие)
       habits = load_habits_from_datasets()
       for habit in habits:
           self.intent_memory.record_trace(habit['context'], habit['action'])
   ```

3. **Update of the memory panel:**

   ```
   Память привычек (IntentMemory):
     Привычек: 15
   ```

4. **New tab in the inspector:** "Привычки (IntentMemory)"
   - Full statistics of every habit
   - Detail for each trace
   - Grouping by action type

### 4. Testing

**File:** `test_habits_loading.py`

Check:

```
✅ Загружено 15 привычек из датасета
✅ Записано 15 traces в IntentMemory
✅ Статистика по действиям работает
✅ Инспектор отображает все привычки
```

---

## Current state

### What is loaded when the GUI starts

```
Инициализация NOWA:
  1. ✅ Реализации (91 форм выражения)
  2. ✅ Привычки (15 начальных привычек)
  3. ✅ IntentMemory готова с привычками
```

### Information about habits is available

1. **Main window:**
   - Habit memory (IntentMemory): shows the number of habits

2. **Inspector (button):**
   - **Tab "Привычки (IntentMemory)":**
     - Statistics of the number of traces
     - List of every action type
     - Detail of each trace (strength, recency, age)
   - **Tab "Статистика":**
     - Total number of habits

---

## How the system now works

### Initialisation (when the GUI starts)

```
1. Загружаются 91 реализация (формы ответов)
2. Загружаются 15 привычек из habits.json
3. Каждая привычка создаёт 1+ trace в IntentMemory
   (количество = strength)
4. Система готова к работе
```

### Use of habits

```
user:кто ты
  ↓
Agent вызывает selector.choose()
  ↓
intent_memory.activate_by_context() 
  → returns {ответить_кто_я: 3.0}
  ↓
Selector видит давление привычки
  → выбирает ответить_кто_я с высокой вероятностью
```

### Consolidation (during sleep)

```
1. Частые привычки укрепляются
2. Редкие привычки ослабевают и забываются
3. Новые привычки формируются из опыта
```

---

## Information about habits in the inspector

The tab "Привычки (IntentMemory)" shows:

```
ПАМЯТЬ ПРИВЫЧЕК (IntentMemory)
============================

СТАТИСТИКА:
  Всего привычек (traces): 15
  
  По типам действий:
    • ответить_кто_я:
        Traces: 2
        Всего strength: 5.0
        Средняя strength: 2.50
    
    • сказать_привет:
        Traces: 3
        Всего strength: 6.0
        Средняя strength: 2.00
    
    • помочь:
        Traces: 3
        Всего strength: 5.0
        Средняя strength: 1.67

ДЕТАЛИ ПРИВЫЧЕК:
--------
🎯 ответить_кто_я:
  [1] Context: abc123
      Strength: 3.0
      Recency: 1.00
      Age: 45s

🎯 сказать_привет:
  [1] Context: def456
      Strength: 3.0
      Recency: 0.99
      Age: 32s
```

---

## Check: is everything loaded?

The check was performed:

```
[Loader] Загружено 15 привычек из habits.json
✅ Загружено 15 привычек из датасета
✅ Записано 15 traces в IntentMemory
✅ Статистика по действиям работает
✅ Все привычки доступны в инспекторе
```

---

## How to use

1. **Run the GUI:**

   ```bash
   python src/gui.py
   ```

2. **Habits are loaded automatically**
   - In the status line: "Память привычек (IntentMemory): Привычек: 15"

3. **Open the inspector:**
   - The inspector button in the interface
   - Go to the tab "Привычки (IntentMemory)"
   - See every habit, its statistics, and its detail

4. **Send a message:**
   - Typical contexts already have habits
   - The selector chooses actions under the guidance of habits
   - New habits form from experience

---

## Example of operation

**Scenario:**

```
User: "кто ты?"
  ↓
Context: ["user:кто ты"]
  ↓
IntentMemory.activate_by_context() 
  → {ответить_кто_я: 3.0}
  ↓
Selector выбирает "ответить_кто_я" (привычка помогла!)
  ↓
ActionRealizer выбирает форму из 14 реализаций
  ↓
Output: "Я NOWA" (или другая форма из датасета)
```

---

## Summary

- **Habits are loaded from the dataset** (15 habits)
- **The information is visible in the inspector** (tab "Привычки")
- **It is shown in the main window** (habit counter)
- **It is used by the selector** (pressure at selection)
- **Testing confirms it** (everything works)
