# Инструкция: тестирование любопытства в NOWA

English version: [TESTING_CURIOSITY.en.md](TESTING_CURIOSITY.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Где смотреть информацию о любопытстве в GUI

### В главном окне (правая панель, средняя часть):

```
❤️ Аффективное состояние
...
Любопытство:    [████░░░░░░] 0.45
```

Прогресс-бар показывает текущее значение любопытства (0.0 до 1.0).

### В инспекторе (правая панель, кнопка «Инспектор»):

Вкладка «Консолидация» показывает аффективное состояние после каждого шага.

---

## Как тестировать любопытство

### Метод 1: отправлять новые (необычные) сообщения

**Шаг 1:** откройте главное окно NOWA GUI.

**Шаг 2:** отправьте несколько одинаковых сообщений:

```
Ввод: "привет"
(NOWA отвечает)

Ввод: "привет"
(NOWA отвечает)

Ввод: "привет"
(NOWA отвечает)
```

Любопытство будет падать (повторяющееся содержание = низкая новизна).

**Шаг 3:** отправьте другое (новое) сообщение:

```
Ввод: "как дела?"
```

Любопытство вырастет (новое содержание = высокая новизна).

---

### Метод 2: использовать программный тест

Создайте файл `test_curiosity.py`:

```python
import sys
sys.path.insert(0, 'src')

from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from affect import AffectiveState

# Setup
hip = NOWAHippocampus()
cortex = CortexMemory()
sel = ActionSelector(actions=['say_hello', 'ask_question', 'refuse'])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, sel, sleep_manager=sleep_mgr)

print("=== CURIOSITY TEST ===\n")

# Step 1: Повторяющиеся сообщения (низкая новизна)
print("1️⃣ ПОВТОРЯЮЩИЕСЯ СООБЩЕНИЯ (низкая новизна):")
for i in range(3):
    action = agent.step(["user:hello"], novelty=0.0)  # novelty=0.0 (no new info)
    curiosity = agent.affect_state.curiosity
    print(f"   Шаг {i+1}: curiosity={curiosity:.2f}, action={action}")

print()

# Step 2: НОВЫЕ сообщения (высокая новизна)
print("2️⃣ НОВЫЕ СООБЩЕНИЯ (высокая новизна):")
for i in range(5):
    contexts = [
        ["user:question"],  # Новый контекст
        ["user:greeting"],  # Новый контекст
        ["user:help"],      # Новый контекст
        ["user:joke"],      # Новый контекст
        ["user:puzzle"],    # Новый контекст
    ]
    action = agent.step(contexts[i], novelty=0.8)  # novelty=0.8 (high novelty!)
    curiosity = agent.affect_state.curiosity
    print(f"   Шаг {i+1}: curiosity={curiosity:.2f}, action={action}")

print()

# Step 3: Сон (консолидация)
print("3️⃣ СОН (консолидация цепочек):")
sleep_stats = agent.sleep(cycles=2)
print(f"   Цепочек сформировано: {sleep_stats.get('chains_formed', 0)}")
print(f"   Curiosity после сна: {agent.affect_state.curiosity:.2f}")

print("\n✅ Тест завершен!")
```

**Запуск:**

```bash
python test_curiosity.py
```

**Ожидаемый вывод:**

```
=== CURIOSITY TEST ===

1️⃣ ПОВТОРЯЮЩИЕСЯ СООБЩЕНИЯ (низкая новизна):
   Шаг 1: curiosity=0.10, action=say_hello
   Шаг 2: curiosity=0.10, action=say_hello
   Шаг 3: curiosity=0.10, action=say_hello

2️⃣ НОВЫЕ СООБЩЕНИЯ (высокая новизна):
   Шаг 1: curiosity=0.42, action=ask_question
   Шаг 2: curiosity=0.60, action=ask_question
   Шаг 3: curiosity=0.74, action=help
   Шаг 4: curiosity=0.85, action=ask_question
   Шаг 5: curiosity=0.94, action=ask_question

3️⃣ СОН (консолидация цепочек):
   Цепочек сформировано: 23
   Curiosity после сна: 0.94

✅ Тест завершен!
```

---

## Где посмотреть информацию о временных цепочках в GUI

### 1. Главное окно, правая панель, память (нижняя часть):

```
🧠 Память:

Эпизодическая память:
  Опытов: 15
  Ср. подкр.: 1.20

Семантическая память:
  Паттернов: 3
  Ср. сила: 0.65

Память привычек (IntentMemory):
  Привычек: 8

Процесс сна:
  Циклов: 2

🔗 Temporal Chains:
  Цепей: 12
  Ср. стабильность: 0.42
```

### 2. Инспектор (кнопка «Инспектор»), вкладка «Консолидация»:

Прокрутите вниз; появится:

```
Temporal Chains:
  Total chains: 12
  Avg stability: 0.42
```

---

## Как измерить успех

### Тест 1: любопытство растёт с новизной

```python
novelty = 0.0 → curiosity ≈ 0.10 (без изменений)
novelty = 0.5 → curiosity +0.20 (растет)
novelty = 1.0 → curiosity +0.40 (максимальный рост)
```

### Тест 2: любопытство убывает со временем

```python
# После 100 шагов без новизны
curiosity = 0.10 → 0.08 → 0.06 → 0.04 ...
```

### Тест 3: цепочки формируются при новизне

```python
# Ввести разные сообщения
sleep() # Сон для консолидации

# Проверить:
sleep_mgr.chain_memory.statistics()
# {'total_chains': 10+, 'avg_stability': 0.3+, 'avg_net_affect': 0.2+}
```

---

## Что было исправлено (дефекты)

1. **Любопытство начиналось с 0.0** — теперь начинается с **0.1** (слегка поощряет исследование)
2. **Любопытство росло медленно** (×0.25) — теперь растёт быстрее (×0.4 за каждый сигнал новизны)
3. **Отображение цепочек было без пометки** — теперь показывает **Temporal Chains**

---

## Практические советы

### Что делать

- Отправлять **разные** сообщения для повышения любопытства
- Использовать параметр `novelty` в `agent.step()`
- Проверять любопытство через GUI (прогресс-бар)
- Спать (вызвать `agent.sleep()`) для консолидации цепочек

### Чего избегать

- Отправлять **одно и то же** сообщение много раз (любопытство упадёт)
- Забывать передавать параметр `novelty` (по умолчанию 0.0)
- Ожидать цепочек без сна (они формируются только во сне)

---

## Как это работает, вкратце

```
Новый контекст
     ↓
novelty = 0.8
     ↓
curiosity += 0.8 × 0.4 = +0.32
     ↓
Arousal тоже растет
     ↓
Selector.choose() использует curiosity для выбора
     ↓
action = select_with_higher_arousal()
```

---

## Примеры сообщений для тестирования

### Низкая новизна (любопытство падает):

```
"привет"
"привет"
"привет"
```

### Высокая новизна (любопытство растёт):

```
"привет"
"как ты?"
"какие новости?"
"расскажи о себе"
"у тебя есть мечты?"
"что ты думаешь о космосе?"
```

---

Процедура готова. Любопытство можно тестировать.
