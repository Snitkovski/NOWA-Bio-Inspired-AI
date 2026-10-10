# Спецификация — External Interaction Layer (реализовано)

English version: [spec_external_interaction_layer.en.md](spec_external_interaction_layer.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## 1. Архитектурное положение

Слой расположен между средой и когнитивным контуром агента:

```
[ Environment ]
       ↑ ↓
[ External Interaction Layer ]
       ↑ ↓
[ Agent / Selector / BG pipeline ]
       ↑ ↓
[ Drives + Internal Simulation ]
```

Ключевой принцип:
- `ActionSelector` остается proposer (предлагает действие),
- `EnvironmentInterface` исполняет,
- `ExternalInteractionLayer` интерпретирует feedback и применяет learning hooks.

---

## 2. Модели данных

### 2.1 Observation

```python
@dataclass
class Observation:
    timestamp: float
    source: str
    payload: Dict[str, Any]
    uncertainty: float  # clamp [0, 1]
```

Поддержка:
- шумных наблюдений;
- кэширования истории (`history_limit`);
- вероятностной интерпретации (`confidence = 1 - uncertainty`).

### 2.2 ExternalAction

```python
@dataclass
class ExternalAction:
    action_type: str
    parameters: Dict[str, Any]
    expected_outcome: Optional[Hypothesis]
```

### 2.3 Feedback

```python
@dataclass
class Feedback:
    reward: float               # clamp [-1, 1]
    signal: Dict[str, Any]
    success_probability: float  # clamp [0, 1]
    latency: float              # >= 0
```

### 2.4 Hypothesis

```python
@dataclass
class Hypothesis:
    name: str
    prior: float
    likelihood: float
    likelihood_not_h: float
    posterior: float
    metadata: Dict[str, Any]
```

---

## 3. Learning hooks (текущая реализация)

### 3.1 Drive update: decay + saturation + competition

Обновление выполняется в `ExternalInteractionLayer.apply_learning_hooks(...)`.

Шаг 1: базовое обновление по reward с затуханием:

```
decayed = (1 - drive_decay) * current
edge_distance = |2*current - 1|
saturation_gate = max(0.05, 1 - drive_saturation * edge_distance)
delta = alpha * reward_signal * saturation_gate
raw = clamp(decayed + delta, 0, 1)
```

Шаг 2: competition между drives:

```
distribution = softmax(raw_drive_updates)
competitive = (1 - drive_competition) * raw
            + drive_competition * distribution * total_energy
```

Эффект:
- нет бесконечного линейного разгона;
- снижается риск sticky-режима на границах;
- несколько drives конкурируют за ограниченную "энергию".

### 3.2 Strategy update: logits + weight decay + softmax

Используется логитное пространство и нормализация:

```
td_residual = reward_signal - predicted_reward
drive_term = drive_policy_gain * strategy_drive_signal
new_logit = (1 - strategy_weight_decay) * current_logit
          + learning_rate * (td_residual + drive_term)
strategy_weights = softmax(strategy_logits, temperature)
```

Поддержка:
- `strategy_temperature` (контроль sharpness policy),
- `strategy_weight_decay`,
- стабильная нормализация (`sum(weights)=1`).

### 3.3 Coupling drives → policy (устранена недосвязка)

`strategy_drive_signal` вычисляется как взвешенная проекция drive levels:

```
signal_s = clamp( Σ_d w(s,d) * (2*level_d - 1) / Σ_d |w(s,d)| , -1, 1 )
```

Источники coupling:
1. Явный `strategy_drive_coupling` (передается из Agent).
2. Если не передан, строится fallback-эвристика.

Интеграция в Agent:
- coupling извлекается из `selector.action_metadata[action]["predicted_effect"]["drives"]`,
- знак инвертируется по `-delta`, чтобы ожидаемое снижение drive усиливало стратегию.

### 3.4 Hypothesis update: расширенный Bayesian

Поддерживается явный `P(E|¬H)` и опциональный `P(E)`:

```
P(H|E) = P(E|H) * P(H) / P(E)
```

Если `P(E|¬H)` не задан:
- используется значение из metadata/состояния hypothesis,
- либо выводится через base-rate, если передан `P(E)`.

---

## 4. Асинхронный слой

`AsyncInteractionScheduler` реализует:
- `poll_observation_non_blocking()` — неблокирующий опрос среды;
- `schedule_parallel_simulations(...)` — параллельные внутренние simulation requests;
- `queue_feedback(...)` / `resolve_feedback(...)` — delayed feedback.

Гарантия:
- delayed signals применяются только при `due_step <= current_step`.

---

## 5. Интеграция в Agent

Добавлены публичные методы:
- `observe_external_input(...)`
- `get_external_observation_history(...)`
- `create_external_action(...)`
- `poll_external_observation_non_blocking()`
- `poll_external_observation_once()`
- `execute_external_action(...)`
- `resolve_external_feedback(...)`
- `get_external_interaction_state()`
- `run_parallel_internal_simulations(...)`

Внутренний learning bridge:
- `Agent._apply_external_feedback_learning(...)` передает drives/strategies/coupling в `apply_learning_hooks(...)`;
- после update новые `strategy_weights` пробрасываются в `selector.action_metadata[*]["strategy_weight"]`.

---

## 6. Интеграция в Selector policy

В `ActionSelector.compute_pressures(...)` добавлена policy-модуляция:
- берется `strategy_weight` из `action_metadata`,
- центрируется относительно равномерного baseline,
- добавляется в pressure-вектор.

Итог:
- learning в ExternalInteractionLayer влияет на реальный выбор действия,
- цепочка замкнута: `feedback -> drives/strategies -> selector pressure -> action`.

---

## 7. GUI (интерактивное управление, RU)

В `src/gui.py` добавлен блок `Слой внешнего взаимодействия`:

- поля наблюдения:
  - `источник`
  - `неопр.`
  - `данные JSON`
- кнопки:
  - `Добавить наблюдение`
  - `Опрос среды`
- поля действия:
  - `действие`
  - `приор`
  - `задержка`
  - `прогноз`
  - `параметры JSON`
- кнопки:
  - `Выполнить действие`
  - `Обработать отложенные`
  - `Обновить статус`
- статусные строки:
  - `набл | ожидание | шаг | стратегии`
  - последняя обратная связь.

---

## 8. Тестовое покрытие

Покрытие находится в `tests/test_external_interaction_layer.py` и включает:
- delayed feedback pipeline;
- strategy normalization (softmax);
- explicit `P(E|¬H)` path for hypothesis;
- drive→strategy coupling при нейтральной награде;
- влияние `strategy_weight` на selector pressures;
- agent-level integration (external action execution, delayed resolution, polling, parallel simulation).

Команда:

```bash
python -m pytest -q tests/test_external_interaction_layer.py
```

---

## 9. Инварианты реализации

1. `reward` clamp в `[-1, 1]`, вероятности clamp в `[0, 1]`.
2. Drive интенсивности ограничены `[0, 1]`.
3. Strategy веса всегда нормализованы (softmax).
4. Delayed feedback не применяется раньше срока.
5. Coupling drives→strategies не bypass-ит selector/BG pipeline, а модулирует policy через pressures.
