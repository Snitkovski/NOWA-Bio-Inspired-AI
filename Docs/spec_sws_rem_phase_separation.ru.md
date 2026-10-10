# Спецификация разделения фаз SWS и REM, версия 1.0

English version: [spec_sws_rem_phase_separation.en.md](spec_sws_rem_phase_separation.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


---

## 1. Область действия

Спецификация определяет:

- Формальные критерии классификации фазы сна: `SWS`, `REM`, `TRANSITIONAL`
- Различные режимы обновления SAC (семантические центроиды действий)
- Правила изменения `mu`, `sigma`, `stability_score`, `semantic_confidence`
- Жёсткие инварианты
- Набор тест-кейсов для верификации

> Фаза определяется только во время `sleep_consolidation()`.

---

## 2. Входные сигналы

Каждый эпизод сна обязан содержать:

```
confidence_score         ∈ [0, 1]
stability_score          ∈ [0, 1]
prediction_shock         ≥ 0
arousal                  ∈ [0, 1]
consolidation_probability ∈ [0, 1]
replay_priority          ≥ 0
```

> Если любой сигнал отсутствует — эпизод не участвует в фазовой логике.

---

## 3. Агрегация батча

Для батча сна `B`:

```
mean_confidence
mean_stability
mean_shock
mean_arousal
mean_consolidation_prob
shock_fraction_high = fraction(prediction_shock > θ_shock_high)
```

---

## 4. Пороговые параметры

Обязательные параметры:

```
θ_arousal_low
θ_arousal_high
θ_shock_low
θ_shock_high
θ_conf_high
θ_cons_high
θ_stability_high
```

**Инвариант:**

```
θ_arousal_low < θ_arousal_high
θ_shock_low   < θ_shock_high
```

---

## 5. Фазовая классификация

### 5.1 SWS

Батч классифицируется как `SWS`, если:

```
mean_arousal            < θ_arousal_low
AND mean_shock          < θ_shock_low
AND mean_confidence     > θ_conf_high
AND mean_consolidation_prob > θ_cons_high
```

### 5.2 REM

Батч классифицируется как `REM`, если выполняется **хотя бы одно**:

```
mean_arousal        > θ_arousal_high
OR mean_shock       > θ_shock_high
OR shock_fraction_high > 0.25
```

### 5.3 TRANSITIONAL

Если не выполнено ни одно условие выше — фаза `TRANSITIONAL`.

---

## 6. Локальная фазовая переоценка (необязательно)

Если включён режим `local_phase_mode = True`, фаза вычисляется для каждого действия отдельно на основе его локальных агрегатов.

По умолчанию используется глобальная фаза батча.

---

## 7. Правила обновления SAC по фазе

**Общие обозначения:**

```
mu_old
sigma_old
sigma_floor
stability_old
alpha_base
```

### 7.1 Режим SWS

#### 7.1.1 Обновление mu

```
alpha_mu_sws = alpha_base * 0.5
mu_new = mu_old + alpha_mu_sws * (mu_observed - mu_old)
```

#### 7.1.2 Обновление sigma

```
sigma_new = sigma_old + α_sigma * (sigma_observed - sigma_old)
sigma_new *= (1 - sigma_decay_sws)
sigma_new = max(sigma_floor, sigma_new)
```

Инвариант: `sigma_new ≤ sigma_old` (если `shock_low`).

#### 7.1.3 Обновление стабильности

Если действие обновлено:

```
stability_new = min(1.0, stability_old + β_stability_sws)
```

> **Запрещено:** снижение стабильности в SWS.

#### 7.1.4 Семантическая уверенность

Экспоненциальное скользящее среднее с повышенным коэффициентом:

```
semantic_confidence_new =
    EMA(semantic_confidence_old, semantic_signal, λ_sws)
```

Где `λ_sws > λ_rem`.

---

### 7.2 Режим REM

#### 7.2.1 Обновление mu

```
alpha_mu_rem = alpha_base * 1.5
mu_new = mu_old + alpha_mu_rem * (mu_observed - mu_old)
```

#### 7.2.2 Обновление sigma

```
sigma_new = sigma_old + α_sigma * (sigma_observed - sigma_old)
sigma_new += ε_var_rem
sigma_new = max(sigma_floor, sigma_new)
```

Инвариант: `sigma_new ≥ sigma_old` (если `shock_high`).

#### 7.2.3 Обновление стабильности

**Разрешено:**

```
stability_new = stability_old * (1 - δ_rem)
```

> **Запрещено:** рост стабильности в REM.

#### 7.2.4 Структурное предупреждение

Если `prediction_shock > θ_structural`:

```python
meta["structural_alert"] = True
```

---

### 7.3 Режим TRANSITIONAL

Консервативная динамика:

- `alpha_mu = alpha_base`
- обновление sigma без принудительного сжатия или расширения
- стабильность не изменяется

---

## 8. Жёсткие ограничения

| #   | Ограничение |
|-----|-------------|
| HC1 | Фаза вычисляется только внутри `sleep_consolidation()` |
| HC2 | Обучение временной разности в бодрствовании не зависит от фазы сна |
| HC3 | `sigma ≥ sigma_floor` всегда |
| HC4 | В SWS стабильность никогда не снижается |
| HC5 | В REM стабильность никогда не возрастает |
| HC6 | Нельзя одновременно применять правила SWS и REM к одному действию в одном цикле сна |

---

## 9. Метрики валидации

После сна вычисляются:

- `phase_distribution`
- `mean_sigma_change`
- `mean_stability_change`
- `structural_alert_count`

---

## 10. Тест-кейсы

### Тест 1 — чистый SWS

**Вход:**

```
mean_arousal           = 0.1
mean_shock             = 0.05
mean_confidence        = 0.85
mean_consolidation_prob = 0.9
```

**Ожидается:** `phase == SWS`, `sigma_new ≤ sigma_old`, `stability_new ≥ stability_old`, `structural_alert_count == 0`.

### Тест 2 — чистый REM (высокий шок)

**Вход:**

```
mean_arousal         = 0.8
mean_shock           = 0.4
shock_fraction_high  = 0.5
```

**Ожидается:** `phase == REM`, `sigma_new ≥ sigma_old`, `stability_new ≤ stability_old`, возможны структурные предупреждения.

### Тест 3 — смешанный батч

**Вход:**

```
mean_arousal = 0.3
mean_shock   = 0.15
```

**Ожидается:** `phase == TRANSITIONAL`, sigma без принудительного сжатия или расширения, стабильность не изменяется.

### Тест 4 — защита нижней границы sigma

**Вход:** `sigma_old = 0.02`, `sigma_floor = 0.01`, сжатие в SWS.

**Ожидается:** `sigma_new ≥ 0.01`.

### Тест 5 — монотонность стабильности

**Цикл SWS:** `stability_old = 0.7` → `stability_new ≥ 0.7`.

**Цикл REM:** `stability_old = 0.7` → `stability_new ≤ 0.7`.

### Тест 6 — срабатывание структурного предупреждения

**Вход:** `prediction_shock = 0.9`, `θ_structural = 0.8`.

**Ожидается:** `meta["structural_alert"] == True`.

---

## 11. Системные эффекты

Эта спецификация гарантирует:

- Разделение консолидации и восстановления
- Отсутствие осцилляторного дрейфа
- Защиту от коллапса дисперсии
- Контролируемый рост стабильности
- Возможность перестройки модели через REM
