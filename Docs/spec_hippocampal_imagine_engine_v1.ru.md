# Спецификация движка гиппокампального воображения, версия 1

English version: [spec_hippocampal_imagine_engine_v1.en.md](spec_hippocampal_imagine_engine_v1.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**SPEC VERSION:** HIE-001
**TARGET:** конвейер `Agent.deliberative_planning`
**STATUS:** готово к реализации

**Зависимости:**
- Граф опыта
- `state_similarity()`
- `ValueLayer`
- `action_index`

---

## 1. Мотивация

Текущее планирование использует траектории памяти. Животные (гиппокамп) выполняют **replay + recombination + imagination** — то есть симулируют траектории, которых никогда не было.

**Пример:**

```
ctx_food + action=go_left
ctx_food + action=climb_tree
```

Гиппокамп может вообразить:

```
ctx_food → climb_tree → eat
```

даже если это никогда не случалось.

Поэтому:

```
rollout source =
    memory trajectories
  + imagined trajectories
```

---

## 2. Обзор устройства

Добавляется модуль `HippocampalImagineEngine`, генерирующий `imagined_rollouts` из похожих состояний, графа опыта и переходов действий.

**Конвейер:**

```
decision
   ↓
deliberative planning
   ↓
HIE (generate imagined trajectories)
   ↓
rollout evaluation
   ↓
pressure modulation
```

---

## 3. Конфигурация агента

Добавляются параметры:

```python
self.imagination_enabled: bool              = True

self.imagination_samples: int               = 8
self.imagination_depth: int                 = 4
self.imagination_branching: int             = 3
self.imagination_similarity_threshold: float = 0.6

self.imagination_reward_decay: float        = 0.9
self.imagination_novelty_bonus: float       = 0.05

self.imagination_max_nodes: int             = 64
```

**Жёсткие пределы:**

```
imagination_samples   ≤ 8
imagination_depth     ≤ 5
imagination_branching ≤ 4
```

---

## 4. Основной интерфейс

Добавляется метод:

```python
def _generate_imagined_rollouts(
    self,
    start_state: Mapping[str, Any],
    action_id: str,
    experiences: list,
    depth: int,
) -> list[float]:
```

**Возвращает:** список значений воображаемых траекторий, где каждое значение — дисконтированное накопленное вознаграждение.

---

## 5. Алгоритм воображения

**Псевдокод:**

```
for sample in imagination_samples:

    node = random similar experience

    for step in depth:

        candidate_experiences =
            experiences with similar state

        choose random transition

        accumulate reward

        move to next state
```

**Формальный псевдокод:**

```python
values = []

for s in range(samples):

    current = random_similar_experience()

    total    = 0
    discount = 1

    for d in range(depth):

        next_candidates =
            find experiences with similar state

        if empty:
            break

        next_exp = random_choice(next_candidates)
        reward   = next_exp.reward

        total    += discount * reward
        discount *= gamma * imagination_reward_decay
        current   = next_exp

    values.append(total)
```

---

## 6. Поиск по сходству

Используется существующая функция `state_similarity(a, b)`.

**Фильтр:** `similarity >= imagination_similarity_threshold`.
**Лимит:** `max candidates = imagination_branching`.
**Выбор:** первые K по сходству.

---

## 7. Интеграция с планированием

Модифицируется `_apply_deliberative_planning()`.

**Было:**

```python
rollout_value = estimate_rollout_value(...)
```

**Станет:**

```python
memory_value    = estimate_rollout_value(...)
imagined_values = generate_imagined_rollouts(...)

imagined_value  = quantile(imagined_values, 0.7)

rollout_value   = max(memory_value, imagined_value)
```

---

## 8. Премия за новизну

Поощрение исследования воображаемых траекторий. Если воображаемая траектория использует состояние, **никогда не наблюдавшееся с данным действием**:

```
value += imagination_novelty_bonus
```

---

## 9. Предохранители

Ограничения для предотвращения взрыва:

```
total_nodes ≤ imagination_max_nodes
```

Также завершение, если:

```
discount < 0.02
```

---

## 10. Бюджет сложности

**Верхняя граница:** `O(actions × samples × depth)`.

**Пределы:**

```
actions ≤ 32
samples ≤ 8
depth   ≤ 5
```

**Худший случай:** `32 × 8 × 5 = 1280` посещений узлов — допустимо.

---

## 11. Телеметрия

Добавляются поля в метаданные планирования:

- `imagination_enabled`
- `imagination_samples`
- `imagination_depth`
- `imagined_rollouts_used`
- `imagined_value_mean`
- `imagined_value_max`
- `imagination_novelty_hits`

---

## 12. Поведенческие следствия

Агент получает способность к следующему.

**1. Обнаружение сокращений:**

```
A → B → C
A → D → C

agent may imagine: A → D → B → C
```

**2. Распространение вознаграждения** — долго отложенное вознаграждение становится видимым.

**3. Планирование при разреженном вознаграждении** — даже при неполной памяти.

---

## 13. Тестовые случаи

**Файл:** `tests/test_imagination_engine_spec_001.py`

### Тест 1 — воображение порождает траектории

**Память:** `A → B (0)`, `B → C (1)`. Агент воображает `A → B → C`.
**Утверждение:** `imagined_value > 0`.

### Тест 2 — фильтрация по сходству

Опыты с `similarity < threshold` должны игнорироваться.

### Тест 3 — ограниченное число развёрток

**Обеспечить:** `imagined_rollouts ≤ imagination_samples`.

### Тест 4 — ограниченная глубина

**Обеспечить:** `depth ≤ imagination_depth`.

### Тест 5 — интеграция с планированием

При `imagination_enabled = True`: `planned_pressure > baseline` для действий с отложенным вознаграждением.

### Тест 6 — отключённый режим

При `imagination_enabled = False`: планировщик ведёт себя идентично предыдущей версии.

---

## 14. Ожидаемое когнитивное поведение

Система эквивалентна:

| Компонент архитектуры | Биологический аналог       |
|-----------------------|----------------------------|
| Граф опыта            | эпизодическая память       |
| Поиск по сходству     | перекрытие клеток места    |
| Выборка развёрток     | гиппокампальное воспроизведение |
| Q-значение планирования | префронтальная оценка    |

Наблюдается у грызунов и у людей, в задачах навигации.

---

## 15. Минимальная реализация (около 120 строк)

| Компонент                        | Объём      |
|----------------------------------|------------|
| `_generate_imagined_rollouts`    | ~70 строк  |
| Интеграция в планирование        | ~20 строк  |
| Конфигурация и телеметрия        | ~30 строк  |
| **Итого**                        | **~120 строк** |

---

## 16. Что это открывает далее

После HIE агент может поддерживать:

| Возможность               | Механизм                                        |
|---------------------------|-------------------------------------------------|
| Когнитивная карта         | гиппокампальный граф                            |
| Целенаправленный поиск    | A\*, Dyna-Q, successor representation           |
| Контрфактуальное рассуждение | *«что, если бы я сделал X»*                  |

---

## 17. Приоритет реализации

Рекомендуемый порядок:

```
1  add config
2  implement generator
3  integrate into planning
4  add telemetry
5  add tests
```
