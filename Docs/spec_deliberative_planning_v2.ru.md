# Делиберативное планирование v2

English version: [spec_deliberative_planning_v2.en.md](spec_deliberative_planning_v2.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Эпизодический rollout + бонус исследования + глубина, адаптивная к неопределённости + древесное наложение HIE-003**

---

## 1. Цель

Усилить делиберативный режим агента за счёт:

- **Эпизодический rollout траектории** — использование последовательностей опыта из hippocampus
- **Глубина планирования, адаптивная к неопределённости** — глубина планирования зависит от глобальной неопределённости
- **Бонус исследования по ценности информации** — стимулирование действий в состояниях с низкой уверенностью

Цель — повысить: скорость обучения, качество решений в новых состояниях, эффективность делиберативного режима.

---

## 2. Ограничения

### Архитектурные ограничения

Решение не должно изменять:

- `BasalGangliaGate`
- `ThalamicGate`
- конвейер обучения `SleepManager`
- правила обновления `ValueLayer`

> Планирование может только модифицировать `pressure_vector`.

### Вычислительные ограничения

Планирование должно оставаться лёгким:

```
max_rollout_samples_per_action  ≤ 8
max_rollout_depth               ≤ 6
max_actions_per_planning        ≤ 32
```

Сложность в худшем случае: `O(actions × samples × depth)`.  
Типично: < 500 операций.

### Ограничения памяти

Планирование не должно:

- создавать новые постоянные структуры
- модифицировать память hippocampus
- хранить траектории

> Используются только существующие объекты `Experience`.

---

## 3. Конфигурационные параметры

Добавляются в `Agent`:

```python
planning_rollout_depth           = 3
planning_rollout_samples         = 6
planning_uncertainty_depth_gain  = 2.0
planning_exploration_gain        = 0.15
planning_min_confidence          = 0.2
```

### Семантика параметров

| Параметр                          | Описание                                                |
|-----------------------------------|---------------------------------------------------------|
| `planning_rollout_depth`          | Базовая глубина симуляции (`depth_base = 3`)            |
| `planning_rollout_samples`        | Сколько эпизодических траекторий использовать (`= 6`)   |
| `planning_uncertainty_depth_gain` | Увеличивает глубину при высокой неопределённости        |
| `planning_exploration_gain`       | Вес бонуса исследования                                 |

---

## 4. Конвейер планирования

Планирование выполняется только если:

```
decision_mode == DELIBERATIVE
```

**Полный алгоритм:**

```
1  retrieve experiences per action
2  estimate reward_mean
3  compute rollout value
4  combine with model value
5  add exploration bonus
6  bias pressure_vector
```

---

## 5. Оценка rollout

### Определение

Rollout — симуляция последовательности награды через граф воспроизведения.

### Алгоритм

```python
for each experience:
    simulate trajectory
    accumulate discounted reward
return max trajectory value
```

### Формула

```
trajectory_value = Σ γ^t * reward_t
```

Где `γ = value_layer.gamma_default`.

---

### 5.A Древесное наложение HIE-003 (реализовано, с откатом на HIE-002)

Оценка rollout планирования теперь строится из двух источников:

1. `memory_rollout_value` из эпизодических траекторий воспроизведения.
2. `imagined_value` из гиппокампального воображения:
   - режим дерева HIE-003 (`imagination_enable_action_sequences=True`):
     `generate_action_tree_imagination(...)` и `action_values[action_id]`.
   - режим отката HIE-002 (`imagination_enable_action_sequences=False`):
     `generate_structured_imagination(...)` с `quantile(values, 0.7)`.

Правило агрегации:

```python
blend = imagination_value_blend
rollout_value = (
    (1 - blend) * memory_rollout_value
    + blend * imagined_value
)
```

Жёсткие пределы пути дерева HIE-003:

```text
imagination_action_branching <= 4
imagination_max_tree_nodes   <= 128
imagination_depth            <= 5
```

Жёсткие пределы пути отката HIE-002:

```text
imagination_samples          <= 8
imagination_depth            <= 5
imagination_branching        <= 4
imagination_max_graph_nodes  <= 96
imagination_max_graph_edges  <= 192
imagination_max_nodes        <= 96
trajectory_confidence        in [0, 1]
discount_stop                < 0.02
```

Члены ценности воображения:

```text
value_estimate =
    discounted_reward
    + imagination_goal_bias * V(last_state)
    + imagination_state_novelty_weight * novelty_score

trajectory_value = value_estimate * confidence * (imagination_value_backup ** (depth - 1))
```

## 6. Оценка Q-ценности

Для каждого действия вычисляется:

```
Q(action) =
      reward_mean
    + γ * max(model_value, rollout_value)
    + edpc_bias
    + exploration_bonus
```

### Компоненты

**`reward_mean`** — средняя награда из похожих состояний.

**`model_value`** — предсказание ValueLayer: `V(s')`.

**`rollout_value`** — агрегированная оценка из rollout памяти и воображаемого rollout:
`(1 - imagination_value_blend) * memory_rollout_value + imagination_value_blend * imagined_value`.

**`exploration_bonus`:**

```
exploration_bonus = exploration_gain × (1 − confidence)
```

Где `confidence ∈ [0, 1]`.

---

## 7. Глубина, адаптивная к неопределённости

Глубина rollout зависит от `global_uncertainty`:

```
rollout_depth =
    planning_rollout_depth
  + global_uncertainty × planning_uncertainty_depth_gain
```

**Пример:**

| неопределённость | глубина |
|------------------|---------|
| 0.0              | 3       |
| 0.5              | 4       |
| 1.0              | 5       |

---

## 8. Смещение давления

После вычисления значений Q:

```
1  normalize Q
2  scale by support
3  add to pressure_vector
```

**Формула:**

```
pressure[action] += gain × Q_norm × support
```

---

## 9. Безопасность и защита от деградации

Планирование должно игнорировать действия, если:

```
support < 0.05
```

или:

```
confidence < planning_min_confidence
```

> Это предотвращает усиление шума.

---

## 10. Телеметрия

Добавляется в `Agent._last_decision_arbitration_output`.

**Новые поля:**

- `planning_rollout_depth`
- `planning_rollout_samples`
- `planning_rollout_used`
- `planning_exploration_bonus_mean`
- `planning_imagination_enabled`
- `planning_imagination_samples`
- `planning_imagination_depth`
- `planning_imagined_rollouts_used`
- `planning_imagined_value_mean`
- `planning_imagined_value_max`
- `planning_imagined_trajectory_count`
- `planning_imagined_confidence_mean`
- `planning_imagined_novelty_mean`
- `planning_imagination_novelty_hits`
- `planning_imagination_tree_nodes`
- `planning_imagination_tree_edges`
- `planning_imagination_action_count`
- `planning_imagination_branching`

---

## 11. Тест-кейсы

### Тест 1 — Rollout улучшает решение

**Постановка:**

```
A1: immediate reward = 0.2
A2: immediate reward = 0.0, trajectory → reward 0.8
```

**Ожидается:** планировщик выбирает A2.

### Тест 2 — Неопределённость увеличивает глубину

**Постановка:** `uncertainty = 0.9`, `base_depth = 3`, `gain = 2`.

**Ожидается:** `depth = 4` или `5`.

### Тест 3 — Бонус исследования

**Постановка:** `confidence = 0.1`, `exploration_gain = 0.15`.

**Ожидается:** `bonus ≈ 0.135`.

### Тест 4 — Планирование выключено

**Постановка:** `deliberative_planning_enabled = False`.

**Ожидается:** `pressure_vector` не изменяется.

### Тест 5 — Память отсутствует

**Постановка:** hippocampus пуст.

**Ожидается:** планирование пропускается.

### Тест 6 — Телеметрия режима дерева HIE-003

**Постановка:** `imagination_enable_action_sequences = True`, кандидаты из нескольких действий.

**Ожидается:** метаданные содержат неотрицательные:
`planning_imagination_tree_nodes`,
`planning_imagination_tree_edges`,
`planning_imagination_action_count`,
`planning_imagination_branching`.

---

## 12. Производительность

- Ожидаемые накладные расходы на шаг: **< 1 мс**
- Накладные расходы памяти: **0**

---

## 13. Обратная совместимость

Полная. Если параметры отсутствуют — откат к текущему поведению.

---

## 14. Критерии принятия

Возможность считается реализованной, если:

- все тесты проходят
- делиберативные решения меняются, когда траектории существуют
- накладные расходы времени выполнения < 2 мс
- обучение во время бодрствования не изменяется
- память hippocampus не модифицируется

---

## 15. Ожидаемый эффект

| Метрика                    | До        | После      |
|----------------------------|-----------|------------|
| скорость обучения          | базовая   | ↑          |
| эффективность исследования | низкая    | ↑↑         |
| глубина планирования       | фиксированная | адаптивная |
| качество решений           | среднее   | ↑          |
