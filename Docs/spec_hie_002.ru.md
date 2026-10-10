# Спецификация HIE-002

English version: [spec_hie_002.en.md](spec_hie_002.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Гиппокампальный движок воображения, версия 2 — структурированная проспективная симуляция

**Статус:** EXTENSION  
**Совместимо с:** HIE-001

---

## Цель

Добавить структурированное воображение:

- **временное сшивание** — соединение несвязанных эпизодов памяти
- **воображение со смещением к цели** — предпочтение траекторий, ведущих к ценным состояниям
- **обнаружение новизны состояния** — обнаружение новых состояний
- **уверенность траектории** — оценка надёжности траектории

---

## 1. Новые возможности

| Функция                    | Описание                                  |
|----------------------------|-------------------------------------------|
| рекомбинация траектории    | соединение разных эпизодов                |
| смещение к цели            | поиск ценностных состояний                |
| уверенность траектории     | оценка надёжности                         |
| оценка новизны             | обнаружение новых состояний               |
| граф воображаемых переходов| внутренний граф симуляции                 |

---

## 2. Новые параметры агента

Добавить в `Agent.__init__`:

```python
# HIE-002 parameters
self.imagination_goal_bias              = 0.35
self.imagination_confidence_decay       = 0.9
self.imagination_state_novelty_weight   = 0.4
self.imagination_value_blend            = 0.6
self.imagination_max_graph_nodes        = 96
self.imagination_max_graph_edges        = 192
```

**Ограничения:**

```
0 ≤ goal_bias            ≤ 1
0 ≤ confidence_decay     ≤ 1
0 ≤ novelty_weight       ≤ 1
0 ≤ value_blend          ≤ 1
```

---

## 3. Новый объект: ImaginedTrajectory

```python
@dataclass
class ImaginedTrajectory:
    states:         list
    actions:        list
    rewards:        list
    value_estimate: float
    novelty_score:  float
    confidence:     float
    depth:          int
```

---

## 4. Новый метод: generate_structured_imagination

Добавить в `HippocampalImagineEngine`.

### Сигнатура

```python
def generate_structured_imagination(
    self,
    *,
    start_state:  Mapping[str, Any],
    action_id:    str,
    experiences:  Sequence[Any],
    depth:        int,
    gamma:        float,
    value_layer:  Optional[ValueLayer],
) -> Dict[str, Any]:
```

### Возвращает

```python
{
    "trajectories":  List[ImaginedTrajectory],
    "values":        List[float],
    "nodes_visited": int,
    "novelty_hits":  int
}
```

---

## 5. Алгоритм

### Шаг 1 — Выбор стартовых эпизодов

```python
seed = choose_top_similar(start_state)  # использует _select_candidates
```

### Шаг 2 — Временное сшивание

Позволить соединять эпизоды по критерию:

```
exp_A.next_state ≈ exp_B.state
similarity >= similarity_threshold
```

### Шаг 3 — Построение траектории

```
state₀ → exp₁ → state₁ → exp₂ → state₂ → ...
```

До достижения `depth` или `max_nodes`.

### Шаг 4 — Накопление награды

```
R = Σ γ^t * reward_t
```

Где: `γ_effective = gamma * reward_decay`.

### Шаг 5 — Новизна

```
novelty_score = count(states not in observed_states) / depth
```

### Шаг 6 — Уверенность

```
confidence = similarity_mean * (confidence_decay ^ depth)
```

### Шаг 7 — Оценка ценности

```
value_estimate =
    R
    + goal_bias * V(last_state)
    + novelty_weight * novelty_score
```

Где: `V(last_state) = value_layer.get_value(...)`.

---

## 6. Итоговая оценка траектории

```
trajectory_value = value_estimate * confidence
```

---

## 7. Возврат значений

```python
values.append(trajectory_value)
```

---

## 8. Ограничения сложности

```
samples   ≤ 8
depth     ≤ 5
branching ≤ 4
nodes     ≤ 96
edges     ≤ 192
```

---

## 9. Интеграция с Agent

В `_apply_deliberative_planning` заменить `_generate_imagined_rollouts` на `generate_structured_imagination`.

**Вычисление `imagined_value`:**

```python
imagined_value = quantile(values, 0.7)
```

**Комбинирование:**

```python
rollout_value = max(memory_rollout_value, imagined_value)
```

---

## 10. Телеметрия

Добавить поля:

- `planning_imagined_trajectory_count`
- `planning_imagined_confidence_mean`
- `planning_imagined_novelty_mean`

---

## 11. Инварианты

| #  | Инвариант                                        |
|----|--------------------------------------------------|
| I1 | `values_count ≤ imagination_samples`             |
| I2 | `nodes_visited ≤ imagination_max_nodes`          |
| I3 | `depth ≤ imagination_depth`                      |
| I4 | `confidence ∈ [0, 1]`                            |

---

## 12. Тест-кейсы

**Файл:** `tests/test_hie_002.py`

### ТЕСТ 1 — Рекомбинация траектории

**Память:** `A → B`, `C → D`.  
**Ожидается:** агент воображает `A → B → D`.

### ТЕСТ 2 — Бонус новизны

Новое состояние должно увеличить `value`.

### ТЕСТ 3 — Затухание уверенности

Длинные траектории дают более низкую `confidence`.

### ТЕСТ 4 — Смещение к цели

Если `value_layer(last_state)` высокий, траектория должна выигрывать.

### ТЕСТ 5 — Ограничитель сложности

**Вход:** `samples = 20`, `depth = 10`.  
**Ожидается:** `samples ≤ 8`, `depth ≤ 5`.

---

## 13. Ожидаемое поведение

После HIE-002 агент начинает:

- предсказывать будущие состояния
- соединять разные воспоминания
- искать новые состояния
- оценивать длинные планы

> Это уже очень близко к **гиппокампальной когнитивной карте и воображению**.

---

## 14. Что появится после HIE-002

Агент сможет строить план из несвязанных воспоминаний:

```
memory:
    berry bush
    cave
    wolf

imagination:

    go to bush
        ↓
    cave
        ↓
    safety
```

> Хотя такой траектории не было в опыте.
