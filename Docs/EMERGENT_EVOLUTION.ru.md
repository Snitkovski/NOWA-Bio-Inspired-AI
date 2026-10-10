# Руководство по реализации эмерджентной эволюции (пакет F)

English version: [EMERGENT_EVOLUTION.en.md](EMERGENT_EVOLUTION.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последняя проверка: 27 марта 2026 г.

---

## Область

Пакет F вводит децентрализованную эмерджентную эволюцию поверх существующих пакетов A–E. Глобального оркестратора эволюции нет: каждый агент обновляет локальные системы витальности и размножения, а среда лишь опосредует ресурсы, проверки смертности и события рождения.

Реализованные модули:
1. `src/reproduction.py`
2. `src/mortality.py`
3. `src/ecology.py`
4. `src/population_observer.py`

---

## Основные компоненты

### `ReproductiveSystem` (`src/reproduction.py`)

1. Поддерживает автономный `reproductive_drive` с возрастным порогом и периодом восстановления.
2. Использует сигналы локального состояния:
   - энергия
   - valence
   - cortisol
   - прожитые шаги
   - доля ресурса
3. Предоставляет:
   - `update(...)`
   - `is_ready()`
   - `register_reproduction(...)`
   - `snapshot()`, `to_dict()`, `from_dict()`
4. Включает чистую функцию совместимости:
   - `compute_compatibility(snapshot_a, snapshot_b)`

### `MortalitySystem` (`src/mortality.py`)

1. Отслеживает возрастную сенильность и необратимое состояние смерти.
2. Приоритеты смерти:
   - истощение
   - депривация сна
   - старость
   - сенильность
3. Предоставляет:
   - `update(...) -> bool`
   - `is_dead()`
   - `get_age_fraction(...)`
   - `snapshot()`, `to_dict()`, `from_dict()`

### `EcologyLayer` (`src/ecology.py`)

1. Поддерживает конечный общий пул ресурса.
2. Вычисляет ресурсное давление на агента через:
   - `compute_resource_share(agent_count)`
3. Обновляет пул на каждом такте через:
   - `consume(agent_count)`

### `PopulationObserver` (`src/population_observer.py`)

1. Пассивный наблюдатель (только чтение, без управляющих решений).
2. Производит историю `PopulationSnapshot` с:
   - размером и разнообразием популяции
   - агрегатами витальности, драйва и возраста
   - счётчиками рождений и смертей
   - текущим уровнем и долей ресурса
   - необязательной агрегацией средней приспособленности
3. Поддерживает:
   - `observe()`
   - `save(path)`
   - `load(path, environment)`

---

## Точки интеграции

### Геном (пакет A)

`src/genome.py`:
1. Добавлен ген `lt_max_lifespan_factor` (группа `LT`).
2. В `GenomeVector.to_agent_params()` добавлен `mortality.max_lifespan_factor`.

### AgentFactory (пакет C)

`src/agent_factory.py`:
1. `AgentConfig` теперь включает `base_lifespan_steps`.
2. `spawn(...)` теперь присоединяет:
   - `agent.reproductive_system = ReproductiveSystem(...)`
   - `agent.mortality_system = MortalitySystem(...)`
3. Продолжительность жизни вычисляется из:
   - `base_lifespan_steps * genome.genes["lt_max_lifespan_factor"]`

### SwarmEnvironment (пакет E)

`src/swarm.py`:
1. `SwarmConfig` расширен полями экологии и размножения.
2. `SwarmState` расширен статистикой ресурса, рождений и смертей.
3. `SwarmEnvironment` теперь включает:
   - `ecology`
   - необязательную `factory`
   - `births_this_step`, `deaths_this_step`, `total_births`, `total_deaths`
4. Новые внутренние методы жизненного цикла:
   - `_update_agent_vitality(...)`
   - `_check_mortality(...)`
   - `_check_reproduction_pairs(...)`
   - `_reproduce(...)`

---

## Покрытие тестами

Основной набор пакета F:
1. `tests/test_emergent_evolution_v2.py`

Точечные проверки:
1. динамика размножения и совместимость
2. причины смертности и сенильность
3. ресурсное давление экологии
4. интеграция с роем (обновления рождения, смерти и ресурса)
5. пассивное поведение наблюдателя и сохранение

Последние прогоны (без Demo):

```text
python -m pytest tests/test_emergent_evolution_v2.py -q
20 passed in 0.08s

python -m pytest tests -q
723 passed, 3 skipped
```
