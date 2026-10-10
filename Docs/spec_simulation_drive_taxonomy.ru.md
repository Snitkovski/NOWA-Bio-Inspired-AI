# Спецификация: активация внутренней симуляции и исправление таксономии драйвов

English version: [spec_simulation_drive_taxonomy.en.md](spec_simulation_drive_taxonomy.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Область

Документ описывает:

- Подключение существующего `selector` и `ActionSelector.choose()` к `InternalSimulationLoop` без введения новых модулей.
- Удаление `self_reflection` и `emotional_discharge` из `DRIVE_NAMES` с корректной переразметкой их функциональной роли.

Цель — оживить внутреннюю симуляцию и устранить концептуальную путаницу между биологическими драйвами и регуляторными механизмами.

---

## ЧАСТЬ 1 — активация InternalSimulationLoop

### 1.1 Постановка проблемы

В текущей реализации:

```
InternalSimulationLoop.cognitive_core = None
InternalSimulationLoop.decision_engine = None
```

Следствие:

- всегда используется fallback
- гипотезы не генерируются
- предиктивная оценка отсутствует
- система остаётся реактивной

Архитектура симуляции формально присутствует, но функционально отключена.

### 1.2 Цель проектирования

Активировать внутренние циклы без:

- создания новых модулей
- переписывания `selector`
- изменения внешнего API `DecisionEngine`

Использовать:

- `selector` как `cognitive_core`
- `selector.evaluate()` как `decision_engine` (только полезность)
- `ActionSelector.choose()` только как proposer внутри гипотетического цикла

### 1.3 Спецификация соединения

#### 1.3.1 Внедрение зависимостей

В инициализации агента:

```python
internal_loop.cognitive_core = selector
internal_loop.decision_engine = selector  # использует .evaluate(hypothetical_state)
```

> **Запрещено** оставлять их `None`.

### 1.4 Контракт исполнения InternalSimulationLoop

#### 1.4.1 Требование: симуляция должна работать на копии состояния

**Запрещено:**
```python
decision_engine(current_state)
```

**Разрешено только:**
```python
decision_engine.evaluate(hypothetical_state)
```

### 1.5 Алгоритм генерации гипотез

Внутренний цикл обязан:

1. Создать N гипотетических состояний *(минимум N=1, максимум ограничен существующим recall limit)*
2. Для каждого состояния:
   - применить предполагаемое действие
   - оценить изменение drives
   - рассчитать utility

#### 1.5.1 Псевдокод

```python
for i in range(simulation_budget):

    hypothetical_state = deepcopy(current_state)

    proposed_action = cognitive_core.propose(hypothetical_state)

    hypothetical_state = simulate_action(hypothetical_state, proposed_action)

    score = decision_engine.evaluate(hypothetical_state)

    collect(score, proposed_action)
```

#### 1.5.2 Единая полезность

Расчёт utility должен быть единым для:
- `selector.evaluate()`
- `InternalSimulationLoop`

Реализовано через общий модуль:
```text
src/simulation_utility.py
```

### 1.6 Контракт выхода

`InternalSimulationLoop` обязан вернуть:

```json
{
    "best_action": "action",
    "confidence": 0.0,
    "evaluated_variants": 0
}
```

> Если ни одна гипотеза не сгенерирована — только тогда допускается fallback.

### 1.7 Инварианты

- Нельзя мутировать `current_state`
- Нельзя вызывать `decision_engine` без гипотетического состояния
- Нельзя запускать внутренний цикл без `simulation_budget > 0`
- Нельзя использовать `selector` напрямую на живом состоянии

---

## ЧАСТЬ 2 — исправление таксономии драйвов

### 2.1 Постановка проблемы

В текущем `DRIVE_NAMES` присутствуют:

- `self_reflection`
- `emotional_discharge`

Это:

- не физиологические потребности
- не первичные регуляторы
- не гомеостатические дефициты

Это механизмы более высокого уровня.

### 2.2 Принцип проектирования

> **Drive** = состояние дефицита, возникающее из биологических или социальных примитивов.

- Drive не есть когнитивная операция
- Drive не есть режим работы
- Drive не есть защитная реакция

### 2.3 Изменения спецификации

#### 2.3.1 Удалить из DRIVE_NAMES

```yaml
remove:
    - self_reflection
    - emotional_discharge
```

### 2.4 Замещающая архитектура

#### 2.4.1 Саморефлексия переводится в режим

Вместо драйва `drive.self_reflection` ввести:

```python
agent_mode = {
    IDLE,
    ACTIVE,
    REFLECTION
}
```

Условия входа в `REFLECTION`:

- низкая внешняя стимуляция
- высокий накопленный `prediction_error`
- повышенный `uncertainty`

#### 2.4.2 Эмоциональная разрядка переводится в механизм регуляции

Вместо драйва `drive.emotional_discharge` ввести функцию:

```python
regulate_affect()
```

Триггер:

```python
if affect_overload > threshold:
    trigger_discharge()
```

> Это не мотивация. Это защитная реакция.

### 2.5 Требуемый рефакторинг

#### 2.5.1 SpeechGovernor

Если `discharge` ранее снижал `social_drive`, теперь он должен:

- снижать `affect`
- снижать `overload`
- **не** создавать новый drive

### 2.6 Инварианты

- Регуляция не может генерировать новый drive
- Drive не может быть когнитивной операцией
- Mode не участвует в конкуренции драйвов
- регуляция аффекта не участвует в ранжировании решений

---

## Ожидаемые эффекты на уровне системы

После внедрения:

- `InternalSimulationLoop` перестаёт быть декларативным
- Появляется предиктивная оценка действий
- Система становится частично проактивной
- Устраняется мета-драйвовая рекурсия
- Конкуренция драйвов становится чистой

---

## Контрольный список миграции

- [x] `cognitive_core` подключён
- [x] `decision_engine` подключён
- [x] fallback используется только при отсутствии гипотез
- [x] `DRIVE_NAMES` очищен
- [x] `self_reflection` переведён в mode
- [x] `emotional_discharge` переведён в regulation
- [x] регуляция не участвует в drive ranking
- [x] модульные тесты обновлены
