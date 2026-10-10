# Спецификация HIE-003

English version: [spec_hie_003.en.md](spec_hie_003.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Дерево гиппокампального воображения с несколькими действиями

### Цель

Расширить `HippocampalImagineEngine` так, чтобы система могла генерировать траектории с **последовательностями действий**, а не только оценивать фиксированное начальное действие.

Это приближает систему к:

- прямому прогону гиппокампа
- заместительному пробному действию (VTE)

и формирует примитивную модель мира.

---

## 1. Новая функциональность

**Было:**

```
start_state → actionX → trajectory
```

**Стало:**

```
start_state
   ↓
action1
   ↓
state1
   ↓
action2
   ↓
state2
   ↓
action3
```

---

## 2. Новые параметры агента

Добавить в `Agent.__init__`:

```python
# HIE-003: multi-action imagination tree
self.imagination_enable_action_sequences: bool  = True
self.imagination_action_branching: int           = 3
self.imagination_max_tree_nodes: int             = 128
self.imagination_action_temperature: float       = 0.7
self.imagination_value_backup: float             = 0.8
```

| Параметр                               | Смысл                                    |
|----------------------------------------|------------------------------------------|
| `imagination_enable_action_sequences`  | включает новый режим                     |
| `imagination_action_branching`         | сколько действий пробовать из состояния  |
| `imagination_max_tree_nodes`           | лимит дерева                             |
| `imagination_action_temperature`       | стохастичность выбора действий           |
| `imagination_value_backup`             | насколько ценность распространяется вверх |

---

## 3. Расширение ImaginedTrajectory

Добавить поля:

```python
root_action:            str
terminal_state_value:   float
cumulative_reward:      float
```

**Итоговая структура:**

```python
ImaginedTrajectory:
    states
    actions
    rewards
    root_action
    cumulative_reward
    terminal_state_value
    value_estimate
    novelty_score
    confidence
    depth
```

---

## 4. Новый метод движка

Добавить в `HippocampalImagineEngine`:

```python
def generate_action_tree_imagination(
    *,
    start_state:        Mapping[str, Any],
    candidate_actions:  Sequence[str],
    experiences:        Sequence[Any],
    depth:              int,
    gamma:              float,
    value_layer:        Optional[ValueLayer],
) -> Dict[str, Any]:
```

---

## 5. Алгоритм генерации дерева

### Шаг 1 — Выбор начальных действий

```python
root_actions = top_k_actions(candidate_actions, imagination_action_branching)

for root_action in root_actions:
    expand_action(root_action)
```

### Шаг 2 — Построение дерева

**Узел дерева:**

```python
TreeNode:
    state
    action
    reward
    parent
    children
    depth
```

**Алгоритм:**

```python
queue = [root_nodes]

while queue and nodes < max_tree_nodes:

    node = pop(queue)

    if node.depth >= depth_limit:
        continue

    candidate_experiences = select_similar_experiences(node.state)

    for exp in top_k(candidate_experiences):

        next_state = exp.next_state
        action     = exp.action
        reward     = exp.reward

        child = create_node()

        add_edge(node, child)
        queue.push(child)
```

---

## 6. Генерация траекторий

После построения дерева:

```python
leaf_nodes = nodes with no children

for leaf in leaf_nodes:
    trajectory = trace_path_to_root(leaf)
```

---

## 7. Оценка ценности траектории

```
reward_total     = Σ (gamma^t * reward_t)

terminal_value   = value_layer.get_value(terminal_state)

novelty          = novelty_weight * novelty_score

value_estimate   =
    reward_total
  + goal_bias * terminal_value
  + novelty
```

Затем:

```
trajectory_value = value_estimate * confidence
```

---

## 8. Возврат ценности к корневому действию

Агрегация ценности по `root_action`:

```
action_values[root_action] =
    quantile(values_of_trajectories_for_action, 0.7)
```

---

## 9. Возвращаемая структура

```python
{
    "trajectories":  List[ImaginedTrajectory],
    "values":        List[float],
    "action_values": Dict[action_id, float],
    "nodes_visited": int,
    "edges_visited": int,
    "novelty_hits":  int
}
```

---

## 10. Изменение планирования Agent

В `_apply_deliberative_planning`:

```python
if imagination_enable_action_sequences:

    imagination_result =
        imagination_engine.generate_action_tree_imagination(...)

    imagined_value =
        imagination_result["action_values"].get(action_id, 0.0)

else:
    # fallback to HIE-002
```

---

## 11. Смешивание ценности (исправление HIE-002)

**Было:**

```python
rollout_value = max(memory_rollout_value, imagined_value)
```

**Станет:**

```python
blend = self.imagination_value_blend

rollout_value =
    (1 - blend) * memory_rollout_value +
    blend * imagined_value
```

---

## 12. Новая телеметрия

Добавить поля:

- `planning_imagination_tree_nodes`
- `planning_imagination_tree_edges`
- `planning_imagination_action_count`
- `planning_imagination_branching`

---

## 13. Ограничение сложности

Жёсткие лимиты (иначе планирование станет экспоненциальным):

```
max_tree_nodes ≤ 128
branching      ≤ 4
depth          ≤ 5
```

---

## 14. Ожидаемый результат

После HIE-003 система сможет воображать контрфактические последовательности:

```
action1 → action2 → action3
action1 → action4 → action2
action2 → action3 → action1
```

> Это уже **планирование на основе модели**.

---

## 15. Архитектура после HIE-003

```
episodic memory
        ↓
hippocampal imagination tree
        ↓
trajectory evaluation
        ↓
action value aggregation
        ↓
basal ganglia selection
```

---

## 16. Что это даст системе

После HIE-003 агент сможет:

- планировать многошаговые действия
- избегать отложенного наказания
- обнаруживать длинные цепочки вознаграждения
- моделировать стратегии

> То есть: **примитивная модель мира**.
