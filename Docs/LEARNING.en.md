# NOWA — A Neurosymbolic Agent with Memory

Russian version: [LEARNING.ru.md](LEARNING.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Two-tier plasticity (current core)

The `Agent` in `src/` separates **fast labile tags** (written while awake, exponential decay) from **stable parameters** (Q/V, habits, Go/NoGo, cortex, slow affect — written only in `Agent.sleep()`). Selection uses effective values = stable + labile. The host passes `dt` (or calls `advance_time`) and `PlasticityConfig.expected_wake_interval_s`, and calls `sleep()` on its own schedule.

Canonical reference: [Docs/architecture/two-tier-plasticity.en.md](../Docs/architecture/two-tier-plasticity.en.md). Sleep ordering: [SLEEP.en.md](SLEEP.en.md). Normative spec: [Docs/specs/issue-13-two-tier-plasticity.md](../Docs/specs/issue-13-two-tier-plasticity.en.md).

Sections below describe an older selector-weight tutorial and the legacy GUI trainer; they do **not** define the core `Agent` learning contract after issue #13.

## Двухуровневая пластичность (актуальное ядро)

В `src/` **лабильные метки** пишутся днём и затухают; **стабильные параметры** — только в `Agent.sleep()`. Выбор по stable + labile. Хост передаёт `dt` / `advance_time`, задаёт `expected_wake_interval_s` и вызывает `sleep()`.

Справочник: [two-tier-plasticity.ru.md](../Docs/architecture/two-tier-plasticity.ru.md), [SLEEP.ru.md](SLEEP.ru.md), спека #13. Разделы ниже — устаревший tutorial по весам селектора, не контракт ядра.

## How does it work?

### 1. **System architecture**

```
┌─────────────────────────────────────────────┐
│            NOWA Agent                        │
├─────────────────────────────────────────────┤
│ Входные данные: "кто ты"                    │
│         ↓                                    │
│ ┌──────────────────────────────────────┐    │
│ │ Гиппокамп (Episodic Memory)          │    │
│ │ Хранит конкретные опыты с наградой   │    │
│ └──────────────────────────────────────┘    │
│         ↓                                    │
│ ┌──────────────────────────────────────┐    │
│ │ Селектор действий (Action Selector)  │    │
│ │ Выбирает лучшее действие             │    │
│ │ на основе:                           │    │
│ │ • Весов действий (обучение)          │    │
│ │ • Активных опытов (память)           │    │
│ └──────────────────────────────────────┘    │
│         ↓                                    │
│ Выходные данные: "Я NOWA..."                │
└─────────────────────────────────────────────┘
```

The diagram above is the original interface sketch. In prose: input data such as "who are you" enter the hippocampus (episodic memory), which stores concrete experiences together with reward. The action selector then chooses the best action from action weights (learning) and active experiences (memory). The output is a reply such as "I am NOWA...".

### 2. **Loading experience from a dataset**

When a dataset is loaded (for example, `dialog_experience.json`):

```json
[
  {
    "context": "как дела",
    "action": "сказать_привет",
    "reward": 1.0
  },
  {
    "context": "кто ты",
    "action": "ответить_кто_я",
    "reward": 1.0
  }
]
```

**The system transforms this into:**

```python
# Experience #1
Context: "user:как дела"
Action: "action:сказать_привет"
Reward: 1.0
↓ Сохраняется в гиппокампе
```

The stored record is an experience whose context is the user utterance, whose action is the reply intent, and whose reward is `1.0`. It is written into the hippocampus.

### 3. **How is an action chosen?**

On the input "who are you":

1. **Activation**: the hippocampus finds every experience whose context contains "user:кто ты"
2. **Scoring**: for each possible action a score is computed:
   - `score = action_weight + bonus_from_experiences`
3. **Selection**: the selector chooses the action with the maximum score

```python
Scores:
  ответить_кто_я:  0.5 + 0.8 (бонус) = 1.3  ← ВЫБРАНО
  сказать_привет:  0.4 + 0.0           = 0.4
  отказаться:      0.3 + 0.0           = 0.3
  помочь:          0.2 + 0.0           = 0.2
```

In this example the reply-about-self action is selected because its score is `1.3`.

### 4. **Learning from ratings**

When a rating is given (five stars):

```
Оценка = +2
↓
reward += 2 * alpha (обычно 0.1)
↓
Вес "ответить_кто_я" увеличивается на 0.2
↓
Следующий раз это действие будет выбранного чаще
```

The rating equals `+2`. The reward is increased by `2 * alpha` (usually `0.1`). The weight of the reply-about-self action increases by `0.2`. On the next occasion that action is chosen more often.

### 5. **Automatic training of the selector**

The system can train itself on a dataset.

```
Датасет
  ↓
Для каждого опыта:
  ├─ Активируем контекст
  ├─ Выбираем действие селектором
  ├─ Сравниваем с правильным из датасета
  ├─ Даем награду если совпадает (+1.0)
  └─ Даем штраф если не совпадает (-1.0)
  ↓
Веса действий обновляются
  ↓
Повторяем несколько эпох
  ↓
Accuracy повышается!
```

For each experience the context is activated, the selector chooses an action, the choice is compared with the dataset label, a reward of `+1.0` is given on a match and a penalty of `-1.0` on a mismatch, action weights are updated, and several epochs are repeated so that accuracy rises.

**How to use it:**
1. Load a dataset (the "Load dataset" button).
2. Press "Auto-training".
3. Set the parameters:
   - **Number of epochs**: 5–10 is usually sufficient
   - **Learning rate**: 0.5 balances the speed of learning
4. Press "Start training".
5. Watch the results: accuracy should rise.

### 6. **Why does the system behave differently for different questions?**

- **Question: "who are you?"** activates the experience for "ответить_кто_я" and yields an answer about NOWA
- **Question: "how are you?"** activates the experience for "сказать_привет" and yields a greeting
- **Question: "help me"** activates the experience for "отказаться" and yields an evasive answer

## Running the tests

```bash
# Все тесты
python -m pytest tests/ -v

# Только селектор
python -m pytest tests/test_selector.py -v

# Только тренер
python -m pytest tests/test_trainer.py -v

# С кратким выводом ошибок
python -m pytest tests/ -v --tb=short
```

The commands run all tests, the selector tests only, the trainer tests only, and all tests with a short traceback.

### Example tests (23 in total)

- **test_selector.py** (5 tests): checks action selection
- **test_hippocampus.py** (6 tests): checks storage and activation of experience
- **test_agent.py** (5 tests): checks integration of all components
- **test_trainer.py** (7 tests): checks automatic training

## How to correct problems

### Problem: all answers are the same
**Remedy**:
1. Use "Auto-training" so that the selector learns to distinguish contexts.
2. Or supply many ratings by hand (stars).

### Problem: the system does not learn from ratings
**Remedy**: confirm that ratings are given through the star buttons in the interface.

### Problem: experiences do not affect the choice
**Remedy**:
1. Use "Auto-training" for rapid learning.
2. Or use "Refresh" in the "Training" window to see the statistics.

## Dataset structure

```json
[
  {
    "context": "строка или список контекста",
    "action": "одно из возможных действий",
    "reward": число (положительное = хорошо, отрицательное = плохо)
  }
]
```

The context is a string or a list. The action is one of the admissible actions. The reward is a number: positive means good, negative means bad.

**Important**:
- Positive rewards strengthen the action.
- Negative rewards weaken the action.
- At selection time the system prefers experiences with positive rewards.

## Architectural components

### `experience.py`
- `Event`: an event with a timestamp
- `Path`: a sequence of events
- `Experience`: an experience with a path and a reward

### `hippocampus.py`
- `NOWAHippocampus`: episodic memory
- Stores concrete experiences
- Activates experiences by context

### `selector.py`
- `ActionSelector`: action selection
- Uses weights and experiences for the choice
- Learns through the method `learn()`

### `trainer.py` (new)
- `SelectorTrainer`: automatic training
- `train_epoch()`: one pass over the dataset
- `train_full()`: many epochs
- `get_accuracy()`: computes accuracy

## Graphical interface

- **Load dataset**: loads experiences from JSON
- **Training**: shows statistics of the loaded experiences
- **Auto-training**: the selector trains itself on the dataset
- **Inspector**: shows detailed information about memory
- **Save/Load**: saves the agent state
