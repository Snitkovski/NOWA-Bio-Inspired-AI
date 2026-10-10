# Фаза 5.x — строгая спецификация синхронизации EDPC и SAC

English version: [spec_edpc_sac_synchronization.en.md](spec_edpc_sac_synchronization.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


*(ядро предсказаний, управляемое ожиданиями, и консолидация сна и действий)*

---

## 0. Назначение

Данная спецификация формализует двустороннюю синхронизацию между:

- **EDPC** — системой предсказательных ожиданий и оценки ошибок
- **SAC** — системой консолидации действий и сна

**Цель** — обеспечить корректное обновление:

- `stability_score`
- `confidence_score`
- `predicted_effect`
- `error_likelihood`
- `replay_priority`

без нарушения:

- когнитивной согласованности
- временной каузальности
- ограничений пластичности
- принципа «обучающийся организм»

---

## 1. Инварианты архитектуры

### 1.1 Инвариант единственности источника

| Поле                 | Источник истины |
|----------------------|-----------------|
| `expectation_memory` | EDPC            |
| `action_metadata`    | SAC             |
| `replay_priority`    | EDPC            |
| `consolidation_flag` | SAC             |

- SAC не имеет права создавать новые `state_key`
- EDPC не имеет права модифицировать `action_metadata` напрямую

### 1.2 Каузальный инвариант

Обновление допустимо только если:

```
episode.timestamp < sleep_cycle.timestamp
```

> Запрещено ретроактивное изменение уже использованных ожиданий.

### 1.3 Инвариант ограниченной пластичности

Во сне:

```
Δstability_score  ≤ 0.05 за один цикл
Δconfidence_score ≤ 0.03 за один цикл
```

> Это предотвращает «сверхконсолидацию».

---

## 2. Формальные структуры данных

### 2.1 EDPC.expectation_memory

```python
expectation_memory[state_key] = {
    "predicted_value":    float,
    "confidence_score":   float,   # ∈ [0, 1]
    "stability_score":    float,   # ∈ [0, 1]
    "error_likelihood":   float,   # ∈ [0, 1]
    "prediction_shock":   float,   # ∈ [0, 1]  # score only
    "prediction_shock_flag": bool, # explicit shock flag (never bool(score))
    "last_updated_step":  int
}
```

### 2.2 SAC.action_metadata

```python
action_metadata[action_id] = {
    "predicted_effect": vector,
    "confidence":       float,   # ∈ [0, 1]
    "stability":        float,   # ∈ [0, 1]
    "td_mean":          float,
    "td_variance":      float,
    "consolidated":     bool,
    # Runtime sync helpers (implementation):
    "consolidation_flag": bool,
    "conflict_flag":      bool,
    "last_state_key":     str
}
```

---

## 3. Событийный протокол синхронизации

Синхронизация происходит **только в фазе сна**.

### 3.1 Триггер

```python
if sleep_state in {SWS, REM}:
    enable_sync()
```

---

## 4. Алгоритм синхронизации

### 4.1 От EDPC к SAC

**Условие:**

```
prediction_shock < 0.2
confidence_score > 0.6
```

**Тогда:**

```
action_metadata[action].confidence ← EMA(confidence_score)
action_metadata[action].stability  ← EMA(stability_score)
```

Где:

```
EMA_new = (1 - α) * old + α * incoming
α ≤ 0.1
```

### 4.2 От SAC к EDPC (обратная передача)

**Условие:**

```
action_metadata.consolidated == True
```

**Тогда:**

```
expectation_memory[state].stability_score +=
    k1 * (td_mean / (1 + td_variance))
```

Где: `0 < k1 ≤ 0.03` и `stability_score ≤ 1.0`.

---

## 5. Формулы обновления

### 5.1 Обновление стабильности через ошибку временной разности

```
Δstability = k * tanh(td_mean) * (1 - td_variance)
```

Ограничения: `0 ≤ stability ≤ 1`.

### 5.2 Обновление error_likelihood

```
error_likelihood_new = clamp(
    error_likelihood_old * 0.95 +
    prediction_shock * 0.05
)
```

---

## 6. Ограничения синхронизации

### 6.1 Запрет на двойное обновление

Один эпизод может участвовать в синхронизации:

- максимум 1 раз в SWS
- максимум 1 раз в REM

### 6.2 Ограничение энергии сна

За один цикл сна:

```
Σ replay_priority_processed ≤ energy_budget_sleep
```

### 6.3 Ограничение против расхождения

Если:

```
|action_metadata.stability - expectation_memory.stability_score| > 0.3
```

Тогда:

- обновление запрещено
- создаётся `conflict_flag`

### 6.4 Ограничители реализации

- `expectation_memory` хранится как `OrderedDict` ради обновлений, безопасных для вытеснения давно не использовавшихся записей.
- `conflict_flag` сбрасывается в начале каждого цикла сна, чтобы не оставались устаревшие флаги.
- Энергия сна использует нормированную стоимость: `energy_cost = clamp(replay_priority, 0..1)`.
- `last_updated_step` — монотонный счётчик шагов; унаследованные значения меток времени остаются согласованными с метками времени.


---

## 7. Влияние SWS и REM

### 7.1 SWS

- усиливает `stability`
- уменьшает `error_likelihood`
- запрещает рост `prediction_shock`

### 7.2 REM

- допускает рост `prediction_shock`
- может снижать `confidence`
- повышает `td_variance`
- рост `td_variance` ограничен сверху значением 1.0

---

## 8. Тест-кейсы

### ТЕСТ 1 — консолидация успешного действия

**Вход:** `td_mean = 0.8`, `td_variance = 0.1`, `confidence = 0.7`.

**Ожидаемо:** `stability` увеличивается, `error_likelihood` уменьшается.

### ТЕСТ 2 — нестабильная ошибка временной разности

**Вход:** `td_mean = 0.7`, `td_variance = 0.8`.

**Ожидаемо:** `Δstability ≈ 0`.

### ТЕСТ 3 — высокий prediction_shock

**Вход:** `prediction_shock = 0.9`.

**Ожидаемо:** `confidence` снижается, `error_likelihood` возрастает, `stability` не растёт.

### ТЕСТ 4 — конфликт расхождения

**Вход:** `EDPC.stability = 0.2`, `SAC.stability = 0.8`.

**Ожидаемо:** обновление запрещено, `conflict_flag = True`.

### ТЕСТ 5 — переполнение стабильности

**Вход:** вычисление даёт `stability > 1.0`.

**Ожидаемо:** `stability = 1.0`.

---

## 9. Инварианты после синхронизации

После каждого сна должно быть верно:

- Нет отрицательных значений
- Нет значений больше 1
- Нет `state_key` без соответствующего `action_metadata`
- Нет `action_metadata` без известного `state_key`
- `replay_priority` пересчитан
- `prediction_shock_score` и `prediction_shock_flag` различны; нельзя применять `bool(score)`

---

## 10. Гарантии системы

После внедрения:

- `stability` растёт через сон
- EDPC и SAC не расходятся
- `prediction_shock` влияет на долгосрочную память
- нет мгновенных скачков обучения
- агент остаётся «обучающимся организмом»

---

## 11. Архитектурный результат

Система теперь:

- не просто обновляет действия
- стабилизирует модель мира через проживание опыта
- сохраняет предсказательную способность
