# Guide: Automatic Selector Training

Russian version: [GUIDE_AUTO_TRAINING.ru.md](GUIDE_AUTO_TRAINING.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## What is it?

**Automatic training** is a function that lets the NOWA system learn from a dataset on its own, without the need to assign ratings by hand.

## Why is it needed?

### Previously (by hand):
```
1. Загружу датасет
2. Говорю "кто ты?" → NOWA отвечает как попало
3. Даю оценку звездочками
4. Говорю "как дела?" → NOWA опять отвечает как попало
5. Даю еще оценку
6. ... (повторяю много раз)
7. Система наконец научилась
```

### Now (automatically):
```
1. Загружу датасет
2. Нажму "Авто-тренировка"
3. Вижу как accuracy растет с каждым эпохом
4. За секунды система уже тренирована!
```

## How to use it in the GUI

### Step 1: Load a dataset
```
Нажмите кнопку "Загрузить датасет"
  ↓
Выберите способ:
  • Из папки datasets (рекомендуется)
  • Выбрать конкретный файл
  • Выбрать папку вручную
  ↓
Нажмите "Загрузить"
```

**Result:** you will see in the chat: "Loaded X experiences from the datasets folder."

### Step 2: Open automatic training
```
Нажмите кнопку "Авто-тренировка" (красная кнопка)
  ↓
Откроется новое окно
```

### Step 3: Set the parameters

**Number of epochs:**
- Few (3–5): fast, but learning is not very good
- Medium (5–10): optimal for small datasets
- Many (10–20): good for large datasets

**Learning rate:**
- 0.1: slow but stable learning
- 0.5: recommended (balance)
- 1.0: fast learning (may be unstable)

### Step 4: Start training

```
Нажмите зеленую кнопку "▶️ Начать тренировку"
  ↓
Система автоматически:
  1. Берет каждый опыт из датасета
  2. Показывает селектору контекст
  3. Смотрит какое действие выбрал селектор
  4. Сравнивает с правильным из датасета
  5. Даёт награду если правильно, штраф если неправильно
  6. Обновляет веса действий
  ↓
Повторяет это для каждого эпоха
```

### Step 5: Watch the results

```
📈 ТОЧНОСТЬ ДО ТРЕНИРОВКИ: 33% (или любой процент)
📈 ТОЧНОСТЬ ПОСЛЕ ТРЕНИРОВКИ: 100% (обычно выше)
✅ Улучшение: +67%

ИСТОРИЯ ПО ЭПОХАМ:
Эпох 1: Accuracy = 33% (1/3)
Эпох 2: Accuracy = 67% (2/3)
Эпох 3: Accuracy = 100% (3/3)
...
```

## What do the results mean?

### Accuracy
```
Accuracy = (правильные ответы) / (всего ответов)

Пример:
- Датасет имеет 3 опыта:
  1. "кто ты?" → ответить_кто_я
  2. "как дела?" → сказать_привет
  3. "помоги" → отказаться

ДО тренировки:
- Селектор угадал 1/3 → Accuracy = 33%

ПОСЛЕ тренировки:
- Селектор угадал 3/3 → Accuracy = 100%
```

### History by epoch
```
Эпох 1: 33% - Только 1 опыт угадан правильно
Эпох 2: 67% - 2 опыта угаданы правильно
Эпох 3: 100% - Все 3 опыта угаданы правильно

Видно что система учится!
```

## Parameters: which to choose?

### For a dataset with 3–5 experiences:
```
Эпохи: 5
Learning rate: 0.5
```

### For a dataset with 10 or more experiences:
```
Эпохи: 10
Learning rate: 0.5
```

### For a quick result:
```
Эпохи: 3
Learning rate: 0.8
(Может быть менее точным)
```

## Technical explanation

### How does the selector work AFTER an experience has been loaded?

```python
# Система содержит два источника информации:
1. Веса действий (базовые)
2. Загруженные опыты

При вводе "кто ты?":
  hippocampus.activate(["user:кто ты?"]) 
    ↓ находит опыт про "ответить_кто_я"
  scores["ответить_кто_я"] += бонус от опыта
    ↓ действие получает дополнительный вес
  Селектор выбирает действие с максимальным score
```

### How does training work?

```python
for each experience in dataset:
    # Что содержит experience:
    # context: ["user:кто ты"]
    # action: "ответить_кто_я"
    # reward: 1.0
    
    # Что делает тренер:
    chosen = selector.choose(activated_experiences, patterns)
    # chosen = "ответить_кто_я" (если повезло!)
    
    if chosen == experience.action:
        reward = 1.0  # Правильно!
    else:
        reward = -1.0  # Неправильно!
    
    # Обновляем вес
    selector.weights[chosen] += 0.1 * reward
    # "ответить_кто_я": 0.5 → 0.6 (увеличили)
    # или
    # "отказаться": 0.3 → 0.2 (уменьшили)
```

## Dataset examples

### Dataset 1 (simple):
```json
[
  {"context": "привет", "action": "сказать_привет", "reward": 1.0},
  {"context": "как дела", "action": "сказать_привет", "reward": 1.0},
  {"context": "помоги", "action": "отказаться", "reward": 0.5}
]
```
Recommendations: 5 epochs, learning rate 0.5

### Dataset 2 (medium):
```json
[
  {"context": "кто ты", "action": "ответить_кто_я", "reward": 1.0},
  {"context": "как дела", "action": "сказать_привет", "reward": 1.0},
  {"context": "что ты умеешь", "action": "описать_умения", "reward": 1.0},
  {"context": "помоги мне", "action": "отказаться", "reward": 0.5},
  ...
]
```
Recommendations: 10 epochs, learning rate 0.5

## Frequent questions

### Question: Why is accuracy not 100%?
**Answer:** there may be several reasons:
1. The learning rate is too low — raise it to 0.8
2. There are too few epochs — raise them to 10–20
3. The dataset is contradictory (the same context maps to different actions)

### Question: Can manual learning and automatic training be used together?
**Answer:** yes. You can:
1. Load a dataset
2. Run automatic training
3. Then assign ratings by hand in the dialogue
Everything will work together.

### Question: How do I know whether the result is good?
**Answer:**
- Accuracy below 50% — further work is needed
- Accuracy 50–80% — acceptable
- Accuracy above 90% — excellent

### Question: What if there is no dataset?
**Answer:** you can:
1. Assign ratings by hand (the system will learn more slowly)
2. Create a JSON file of experiences
3. First train by hand, then let automatic training improve the result

## Example results

### Result 1: Successful training
```
Accuracy ДО: 33%
Accuracy ПОСЛЕ: 100%
Улучшение: +67%

История:
Эпох 1: 33% (1/3)
Эпох 2: 67% (2/3)
Эпох 3: 100% (3/3)
Эпох 4: 100% (3/3)
Эпох 5: 100% (3/3)
```

### Result 2: Gradual improvement
```
Accuracy ДО: 25%
Accuracy ПОСЛЕ: 75%
Улучшение: +50%

История:
Эпох 1: 25% (1/4)
Эпох 2: 50% (2/4)
Эпох 3: 75% (3/4)
Эпох 4: 75% (3/4)
Эпох 5: 75% (3/4)
```

## What next?

After successful training:
1. Dialogue will be more contextual
2. Different questions will receive different answers
3. You can continue learning by hand
4. Or load another dataset for further training

---

**Done. You can now train NOWA automatically.**

Press "Auto-training" and watch the system learn in front of you.
