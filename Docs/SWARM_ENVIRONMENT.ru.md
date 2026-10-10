# Руководство по реализации SwarmEnvironment (пакет E)

English version: [SWARM_ENVIRONMENT.en.md](SWARM_ENVIRONMENT.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последняя проверка: 27 марта 2026 г.

---

## Область

`src/swarm.py` реализует пакет E (`SwarmEnvironment v2.2`) как физическое непрерывное трёхмерное пространство для автономных агентов.

Модуль предоставляет:
1. пространственное размещение и управление популяцией без столкновений
2. локальную социальную сигнализацию с затуханием по расстоянию
3. автономные переходы сна и бодрствования с пробуждением по сигналу стресса
4. детерминированное исполнение на каждом такте и диагностику уровня роя
5. ресурсное давление экологии и децентрализованные точки размножения и смертности

---

## Реализованные объекты

### Пространственная модель

1. `Position3D`
2. `SpaceBounds`

Возможности:
1. евклидово расстояние в трёх измерениях
2. двумерный режим при `z_min == z_max`
3. проверка границ и ограничение координат
4. порождение случайного положения

### Модель социальной сигнализации

1. `SocialSignal`
2. формула затухания:
   `signal_strength = base_strength / (1 + distance^2 * signal_decay_factor)`
3. затухание источника во сне:
   `SLEEPING_SIGNAL_FACTOR = 0.3`
4. фильтр минимальной силы сигнала:
   `SIGNAL_MIN_STRENGTH = 0.01`

### Структуры состояния времени выполнения

1. `AgentSlot`
2. `SwarmState`
3. `SwarmConfig`

### Ядро среды

Открытый интерфейс `SwarmEnvironment`:
1. жизненный цикл популяции:
   - `add_agent`, `remove_agent`, `move_agent`, `replace_population`
2. восприятие и сигнализация:
   - `get_agents_in_radius`, `collect_signals_for_agent`, `apply_social_signal`
3. цикл исполнения:
   - `tick`, `run_generation`
4. диагностика:
   - `get_swarm_state`, `get_diversity`, `evaluate_all`
   - `get_sleeping_agents`, `get_active_agents`
   - `get_nearest_agents`, `get_spatial_density`

### Интеграция эмерджентной эволюции (пакет F)

1. экология и ресурсное давление:
   - `self.ecology` (`EcologyLayer`)
2. необязательная фабрика потомства:
   - `self.factory`
3. статистика жизненного цикла:
   - `births_this_step`, `deaths_this_step`, `total_births`, `total_deaths`
4. внутренние методы жизненного цикла:
   - `_update_agent_vitality(...)`
   - `_check_mortality(...)`
   - `_check_reproduction_pairs(...)`
   - `_reproduce(...)`
5. `SwarmState` теперь включает:
   - `resource_level`
   - `resource_share`
   - `births_this_step`
   - `deaths_this_step`
   - `total_births`
   - `total_deaths`

---

## Контракт сна и бодрствования

Реализованная семантика из `Docs/SPEC_E_SwarmEnvironment_v2.1.md`:
1. спящие агенты остаются пространственно присутствующими и воспринимаемыми
2. спящие агенты по-прежнему принимают социальные сигналы
3. спящие агенты излучают ослабленные сигналы (`0.3x`)
4. пробуждение может быть принуждено накопленным сигналом стресса
5. если стресс не разбудил агента, гистерезисное пробуждение использует:
   `wakefulness < sleep_threshold * SLEEP_HYSTERESIS_FACTOR`

Помощник сигнала пробуждения:
1. `_check_wake_signal(...)` вычисляет:
   `sum(signal.stress * signal.signal_strength)`
2. порог конфигурируем (`SwarmConfig.wake_signal_threshold`, по умолчанию `0.6`)

---

## События контекста по умолчанию

Если `SwarmConfig.context_events_fn` не задана, среда использует построитель контекста по умолчанию, так что `agent.step(...)` по-прежнему получает физиологический контекст.

События по умолчанию включают:
1. состояние активности:
   - `agent_active` или `agent_sleeping`
2. корзина бодрствования:
   - `wakefulness_high`
   - `wakefulness_mid`
   - `wakefulness_low`
3. контекст социального состояния (когда входящие сигналы существуют):
   - `social_signal_present`
   - `social_sleeping_neighbor`
   - `social_stress_high` (когда накопленный стресс превышает порог пробуждения)

---

## Интеграция с геномом

`src/genome.py` содержит ген, специфичный для роя:
1. `dr_perception_radius_factor` (диапазон `0.5..2.0`, по умолчанию `1.0`)

`GenomeVector.to_agent_params()` теперь экспортирует:
1. `autonomous.perception_radius_factor`

`SwarmEnvironment.add_agent(...)` использует этот ген для масштабирования:
1. `perception_radius = base_perception_radius * dr_perception_radius_factor`

---

## Покрытие тестами

Основной набор:
1. `tests/test_swarm_environment.py`
2. `tests/test_emergent_evolution_v2.py` (интеграционные сценарии, затрагивающие жизненный цикл роя)

Покрытие включает:
1. TC-01..TC-18 из `Docs/SPEC_E_SwarmEnvironment_v2.1.md`
2. запасной контекст по умолчанию (события `wakefulness_high/low`, когда пользовательская функция контекста отсутствует)
3. изоляцию отказа (один отказавший агент не останавливает глобальный такт)
4. проверки жизненного цикла эмерджентной эволюции (потребление ресурса, удаление по смертности, децентрализованное размножение)

Последний локальный прогон:

```text
python -m pytest tests/test_swarm_environment.py -q
20 passed, 1 warning

python -m pytest tests/test_emergent_evolution_v2.py -q
20 passed in 0.08s
```

Регрессия по проекту (без Demo):

```text
python -m pytest tests -q
723 passed, 3 skipped
```
