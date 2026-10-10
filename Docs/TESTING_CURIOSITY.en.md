# Instruction: Testing Curiosity in NOWA

Russian version: [TESTING_CURIOSITY.ru.md](TESTING_CURIOSITY.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Where to see information about curiosity in the GUI

### In the main window (right panel, middle part):

```
❤️ Аффективное состояние
...
Любопытство:    [████░░░░░░] 0.45
```

The progress bar shows the current value of curiosity (0.0 to 1.0).

### In the Inspector (right panel, button "Inspector"):

The "Consolidation" tab shows the affective state after every step.

---

## How to test curiosity

### Method 1: send new (unusual) messages

**Step 1:** Open the main window of the NOWA GUI.

**Step 2:** Send several identical messages:

```
Ввод: "привет"
(NOWA отвечает)

Ввод: "привет"
(NOWA отвечает)

Ввод: "привет"
(NOWA отвечает)
```

Curiosity falls (repeated content = low novelty).

**Step 3:** Send a different (new) message:

```
Ввод: "как дела?"
```

Curiosity rises (new content = high novelty).

---

### Method 2: use a programmatic test

Create the file `test_curiosity.py`:

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

**Run:**

```bash
python test_curiosity.py
```

**Expected output:**

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

## Where to see information about temporal chains in the GUI

### 1. Main window, right panel, Memory (lower part):

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

### 2. Inspector (button "Inspector"), tab "Consolidation":

Scroll down; the following appears:

```
Temporal Chains:
  Total chains: 12
  Avg stability: 0.42
```

---

## How to measure success

### Test 1: curiosity grows with novelty

```python
novelty = 0.0 → curiosity ≈ 0.10 (без изменений)
novelty = 0.5 → curiosity +0.20 (растет)
novelty = 1.0 → curiosity +0.40 (максимальный рост)
```

### Test 2: curiosity decrements over time

```python
# После 100 шагов без новизны
curiosity = 0.10 → 0.08 → 0.06 → 0.04 ...
```

### Test 3: chains form under novelty

```python
# Ввести разные сообщения
sleep() # Сон для консолидации

# Проверить:
sleep_mgr.chain_memory.statistics()
# {'total_chains': 10+, 'avg_stability': 0.3+, 'avg_net_affect': 0.2+}
```

---

## What was corrected (defects)

1. **Curiosity began at 0.0** — it now begins at **0.1** (a slight encouragement of exploration)
2. **Curiosity grew slowly** (×0.25) — it now grows faster (×0.4 for each novelty signal)
3. **The chain display had no marker** — it now shows **Temporal Chains**

---

## Practical advice

### What to do

- Send **different** messages in order to raise curiosity
- Use the `novelty` parameter in `agent.step()`
- Check curiosity through the GUI (the progress bar)
- Sleep (call `agent.sleep()`) in order to consolidate chains

### What to avoid

- Sending the **same** message many times (curiosity will fall)
- Omitting the `novelty` parameter (the default is 0.0)
- Expecting chains without sleep (they form only during sleep)

---

## How it works, in brief

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

## Example messages for testing

### Low novelty (curiosity falls):

```
"привет"
"привет"
"привет"
```

### High novelty (curiosity rises):

```
"привет"
"как ты?"
"какие новости?"
"расскажи о себе"
"у тебя есть мечты?"
"что ты думаешь о космосе?"
```

---

The procedure is ready. Curiosity can now be tested.
