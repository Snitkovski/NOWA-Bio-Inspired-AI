# Phase 5 — Experience-Driven Predictive Consolidation (EDPC)

English version: [spec_phase5_edpc.en.md](spec_phase5_edpc.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Архитектурная цель

Добавить механизм:

> **повторяемый опыт → устойчивое ожидание → уверенность → селективная пластичность**

Без введения централизованной "модели мира".

---

## 1. Позиция в архитектуре

```
External Input
    ↓
Perceptual Encoding
    ↓
Hippocampus (novelty)
    ↓
CER (affect)
    ↓
ACC (conflict)
    ↓
TD (adaptive)
    ↓
Phase 5 (EDPC)
    ↓
Sleep Replay
    ↓
Value Storage
```

Phase 5 работает после TD delta, но влияет на:

- `effective_alpha`
- `consolidation_weight`
- `replay priority`
- `stability_score`

---

## 2. Ключевая идея

Ввести не "модель мира", а **Expectation Memory**.

Для каждого `(state, action)` или абстрактного паттерна хранится:

```
expected_reward_mean
expected_reward_var
confirmation_count
confidence_score
stability_score
```

---

## 3. Модуль 1 — Expectation Tracker (ET)

Обновляется при каждом TD шаге.

**Обновление среднего:**

```
expected_reward_mean ← EMA(reward)
```

**Обновление дисперсии:**

```
expected_reward_var ← EMA((reward - mean)^2)
```

**Подтверждение:**

```python
if abs(delta) < confirmation_threshold:
    confirmation_count++
else:
    # частичный decay
```

---

## 4. Модуль 2 — Confidence Accumulator (CA)

Confidence отражает: *"я ожидаю это с высокой уверенностью"*.

```
confidence_score = sigmoid(
    k1 * confirmation_count
    - k2 * expected_reward_var
)
```

**Инварианты:**

- `confidence ∈ [0, 1]`
- не растёт без повторных подтверждений
- падает при систематических нарушениях ожиданий

---

## 5. Модуль 3 — Stability Reinforcement (SR)

Stability отражает закреплённость знания.

```
stability_score ←
    stability_score
    + stability_growth_rate * confidence
    - stability_decay_rate * surprise
```

Где:

```
surprise = abs(delta) * confidence
```

> Если `confidence` низкая → surprise почти не бьёт по stability.

---

## 6. Модификация Learning

### Effective Alpha

```
effective_alpha =
    alpha * (1 - confidence * stability_damping)
```

Это означает:

- устойчивые ожидания учатся **медленнее**
- новые паттерны учатся **быстро**

---

## 7. Shock Detection (организмическое)

Условие:

```python
if confidence > high_threshold and abs(delta) > shock_threshold:
    # регистрируется "prediction shock"
```

**Эффекты:**

- временный рост plasticity
- временное усиление replay
- CER стресс ↑

> Это аналог когнитивного диссонанса.

---

## 8. Replay Prioritization

```
priority =
    abs(delta)
    * (1 + shock_flag)
    * (1 - stability_score)
```

> Повторяемое и стабильное не доминирует replay.

---

## 9. Что в итоге происходит

### Повторяемый стабильный опыт

`confidence` ↑ → `stability` ↑ → `alpha` ↓ → `surprise` ↓

→ формируется ожидание → агент "знает", что солнце взойдёт.

### Новый опыт

`novelty` ↑, `confidence` низкая, `alpha` высокий → быстрое обучение.

### Нарушение устойчивого ожидания

shock → стресс → `plasticity` ↑ → `replay` ↑ → глубокая перестройка.

---

## 10. Почему это остаётся организмом

- всё завязано на переживание `delta`
- нет внешнего volatility вычислителя
- нет централизованной world map
- предсказание = стабилизированный опыт

---

## 11. Тест-сценарии с внешними данными

### Тест 1 — Стабильный внешний поток

Синтетическая временная серия с низким шумом, одинаковые reward события.

**Ожидаем:** `confidence → 1`, `stability → 1`, `alpha → минимальный`.

### Тест 2 — Шумная серия без тренда

`reward = mean + random noise`.

**Ожидаем:** `expected_mean` стабилизируется, variance высокая, confidence умеренная, stability средняя.

### Тест 3 — Структурный сдвиг

100 шагов `reward = 1`, затем `reward = 5`.

**Ожидаем:** сначала confidence высокая → затем shock → stability частично разрушается → `alpha` временно ↑.

### Тест 4 — Чтение книги (симулированно)

Внешний текст кодируется как: `novelty_score`, semantic similarity к существующим паттернам, `affect_valence`.

- Если текст повторяет известные идеи: `confidence` ↑, `stability` ↑
- Если противоречит: `conflict` ↑, shock возможен

### Тест 5 — Обучение новому навыку

Серия новых `state → action → reward` триплетов.

**Ожидаем:** быстрое формирование expectation → постепенный рост confidence → снижение plasticity.

---

## 12. Метрики для валидации

Необходимо логировать:

- `confidence` distribution
- `stability` distribution
- shock frequency
- `effective_alpha` trajectory
- replay diversity index

---

## 13. Критерий успешности фазы

Фаза 5 успешна если:

- Агент не переобучается на шум
- Формирует устойчивые ожидания
- Реагирует резко на нарушение устойчивых ожиданий
- Может учиться из текстового или числового внешнего потока

---

## 14. Важно

Мы не строим модель мира. Мы строим:

> систему, которая становится всё менее удивляемой в повторяющихся ситуациях и более чувствительной к настоящим изменениям.

**Это и есть биологическая предсказательность.**
