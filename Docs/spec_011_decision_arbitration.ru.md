# SPEC-011 — Арбитраж решений, глобальная неопределённость и обобщение состояния

English version: [spec_011_decision_arbitration.en.md](spec_011_decision_arbitration.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Версия:** 1.0
**Статус:** обязательный
**Область:** архитектура ядра агента

---

## 1. Цель

Устранить рассинхронизацию между EDPC, SAC и Policy, возникающую из-за того, что:

- TD-error интерпретируется разными подсистемами независимо
- политика решений не учитывает неопределённость модели
- состояние кодируется слишком жёстко (фрагментация состояния)

Ввести:

- Decision Arbitration Layer
- Global Uncertainty Model
- State Similarity Kernel

---

## 2. Архитектура после изменения

**До:**

```
State
  ↓
ValueLayer (EDPC)
  ↓
ActionSelector (policy)
```

**После:**

```
State
  ↓
ValueLayer (EDPC)
  ↓
Sleep SAC update
  ↓
DecisionArbitrator
  ↓
ActionSelector
```

---

## 3. Новый компонент

### 3.1 DecisionArbitrator

**Файл:** `src/decision_arbitrator.py`
**Класс:** `class DecisionArbitrator`

**Назначение** — объединить сигналы EDPC, SAC, аффективной системы и неопределённости и определить:

- режим `habitual` относительно режима `deliberative`
- температуру политики

---

## 4. Модель глобальной неопределённости

### 4.1 Определение

Вводится переменная:

```
global_uncertainty ∈ [0, 1]
```

**Формула:**

```
global_uncertainty =
    w_td      * normalized_td_variance
  + w_error   * EDPC.error_likelihood
  + w_surprise * EDPC.surprise
```

Веса:

```
w_td       = 0.40
w_error    = 0.35
w_surprise = 0.25
```

Ограничение: `0 ≤ global_uncertainty ≤ 1`.

### 4.2 Источники сигналов

| Сигнал              | Источник                                          |
|---------------------|---------------------------------------------------|
| дисперсия TD        | `selector.action_metadata[action]["td_variance"]` |
| правдоподобие ошибки | `value_layer.last_error_likelihood`              |
| сюрприз             | `value_layer.last_surprise`                       |

### 4.3 Нормализация дисперсии TD

```
normalized_td_variance = clamp(td_variance / TD_VAR_SCALE, 0, 1)
```

Где `TD_VAR_SCALE = 0.5`.

---

## 5. Арбитраж решений

### 5.1 Режимы

Система имеет 2 режима: `HABITUAL` и `DELIBERATIVE`.

### 5.2 Переключение режимов

```python
if global_uncertainty > 0.55:
    mode = DELIBERATIVE
else:
    mode = HABITUAL
```

### 5.3 Влияние стресса

Стресс ACC снижает порог делиберации:

```
effective_threshold = base_threshold - (0.25 * stress)
```

Где: `base_threshold = 0.55`, `stress ∈ [0, 1]`.

Ограничение: `threshold ≥ 0.25`.

### 5.4 Температура политики

```
temperature = base_temp + (uncertainty_gain * global_uncertainty)
```

Где: `base_temp = 0.6`, `uncertainty_gain = 0.8`.

Ограничение: `0.4 ≤ temperature ≤ 1.5`.

---

## 6. Интеграция с ActionSelector

ActionSelector должен принимать `temperature` и `decision_mode`.

**Новый интерфейс:**

```python
select_action(
    state,
    pressure_vector,
    temperature,
    decision_mode
)
```

---

## 7. Делиберативный режим

Если режим `DELIBERATIVE`, ActionSelector обязан:

1. Увеличить энтропию политики
2. Учитывать предсказания EDPC
3. Штрафовать неустойчивые действия

**Штраф:**

```
action_score =
    base_score
    * action_confidence
    * action_stability
```

---

## 8. Обобщение состояния

**Текущая проблема:**

```
state_key = hash(snapshot)
```

Это вызывает взрыв числа состояний.

### 8.1 Ядро сходства состояний

Добавить функцию `state_similarity(s1, s2)` с метрикой косинусного сходства.

### 8.2 Использование

При доступе к `expectation_memory`, если точный `state_key` не найден — искать k наиболее сходных состояний:

```
k = 3
similarity_threshold = 0.85
```

### 8.3 Агрегация

Если найдено несколько состояний:

```
expected_reward_mean = weighted_mean(similarity)
```

---

## 9. Ограничения

| Параметр             | Ограничение                  |
|----------------------|------------------------------|
| `global_uncertainty` | `∈ [0, 1]`, ограничение при нарушении |
| `temperature`        | `∈ [0.4, 1.5]`               |
| `similarity`         | `∈ [0, 1]`                   |
| `k` (агрегация состояний) | `≤ 5`                   |

---

## 10. Производительность

Поиск по сходству должен быть `O(k log N)` или лучше.

> Полный перебор запрещён при `N > 500`.

---

## 11. Телеметрия

Телеметрия агента должна содержать:

- `decision_mode`
- `global_uncertainty`
- `policy_temperature`
- `similar_state_count`

---

## 12. Граничные случаи

| Ситуация                    | Поведение                              |
|-----------------------------|----------------------------------------|
| Нет метаданных SAC          | `td_variance = 0`                      |
| Нет профиля EDPC            | `error_likelihood = 0.5`, `surprise = 0` |
| Нет похожих состояний       | откат к профилю ожидания по умолчанию |

---

## 13. Тест-кейсы

### ТЕСТ 1 — Низкая неопределённость

**Вход:** `td_variance = 0.05`, `error_likelihood = 0.1`, `surprise = 0.05`, `stress = 0`.

**Ожидается:** `global_uncertainty < 0.3`, `mode = HABITUAL`, `temperature ≈ 0.65`.

### ТЕСТ 2 — Высокая дисперсия TD

**Вход:** `td_variance = 0.8`, `error_likelihood = 0.2`, `surprise = 0.1`.

**Ожидается:** `mode = DELIBERATIVE`, `temperature > 1.0`.

### ТЕСТ 3 — Делиберация, вызванная стрессом

**Вход:** `uncertainty = 0.45`, `stress = 0.8`.

**Порог:** `0.55 - 0.25 * 0.8 = 0.35`.

**Ожидается:** `mode = DELIBERATIVE`.

### ТЕСТ 4 — Сходство состояний

**Память:** сходство S1 равно 0.92, сходство S2 равно 0.88, сходство S3 равно 0.84.

**Ожидается:** использовать S1 и S2, игнорировать S3.

### ТЕСТ 5 — Границы температуры

**Вход:** `uncertainty = 1`.

**Ожидается:** `temperature ≤ 1.5`.

### ТЕСТ 6 — Нет метаданных SAC

**Ожидается:** `td_variance = 0`, неопределённость зависит только от EDPC.

---

## 14. Обратная совместимость

Все новые поля должны иметь безопасные значения по умолчанию.

> Агент должен работать даже если `DecisionArbitrator` отключён.

---

## 15. Требуемые файлы

**Новые:**

```
src/decision_arbitrator.py
```

**Изменения:**

```
agent.py
selector.py
value_layer.py
```

---

## 16. Критерии приёмки

Изменение считается успешным если:

1. `decision_mode` переключается корректно
2. `uncertainty` влияет на policy
3. обобщение состояния уменьшает рост памяти
4. устойчивость SAC влияет на выбор действия
