# QA PR #42 — демо колонии на двухуровневой пластичности

Ветка: `team/demo-colony-two-tier` @ `8d67917` (код под проверкой; эта заметка — следующий коммит).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/42
Спеки: `Docs/specs/issue-13-two-tier-plasticity.ru.md`, `Docs/architecture/two-tier-plasticity.ru.md`, `Docs/specs/issue-13-demo-colony.ru.md`.
Объём: одно чтение diff и две команды pytest. Полных `Demo/` и `tests/` нет, длинной симуляции нет, перебора сидов нет. Продуктовый код не менялся.

## Вердикт

**PASS**

Ни один пункт проверки не провален. Интервал 403.2 с — шкала времени хоста. Он меняет затухание лабильного слоя относительно fallback 3600 с. Коэффициенты ядра не перенастраиваются.

## Pytest

| Команда | Результат | Время |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 pytest "Demo/Colony chinchillas" -q` | **201 passed, 1 xpassed**, код 0 | 18.46 с |
| `NOWA_STRICT_LEARNING=1 pytest "Demo/Colony chinchillas/tests/test_two_tier_host.py" -q` | **1 passed**, код 0 | 0.29 с |

`WakingLearningError` в обоих прогонах не было. xpass — прежний `test_tc01_two_agents_survive_300s` (`Demo/Colony chinchillas/tests/test_resources.py:30`, `strict=False`, issue #39). Полный `pytest Demo` автора заново не гонялся.

## Проверка

### 1. Игровой `dt` ровно один раз за тик — да

`sim_step` (`Demo/Colony chinchillas/src/colony_agent.py:472-524`) берёт один `_host_dt(dt)` (`:119-127`).

- Тик с решением: `step(..., dt=host_dt)` на `:492-501`, затем `advanced_by_step = True`. `commit_executed_transition` на `:514-524` без `dt`.
- Продолжение сна или `replaced_policy_action`: `step` нет. `advance_time(host_dt)` один раз на `:512-513`, затем тот же commit без `dt`.

Два хода часов взаимно исключены. Ядро двигает часы в `commit_executed_transition` только при переданном `dt` (`src/agent.py:1024-1025`). `step` двигает их в `_advance_host_clock(dt, wall_fallback=dt is None)` (`src/agent.py:381`). Переданный `dt`, включая явный `0` для нечислового или отрицательного входа, ставит `wall_fallback=False` (`src/agent.py:4601-4610`). Ветка настенных часов (`src/agent.py:4612-4624`) не берётся.

`test_two_tier_host.py:34-35`: после четырёх `sim_step(1)` `_dt_warning_sent is False` и `_host_clock_s == 4`. Тест прошёл.

### 2. Стабильные записи только под `initializing()` и только при загрузке или рождении — да

| Запись | Область | Когда |
| --- | --- | --- |
| Посев привычек | `colony_agent.py:945-948` оборачивает `_write_habit_bootstrap` (`:950-976`) | Только из `__init__` (`:302`) |
| Геном конструктора | `colony_agent.py:311-314` | Создание, если геном передан |
| Геном новорождённого | `colony_agent.py:1964-1969` внутри `_inherit_nowa_from` | Рождение: `_create_offspring` (`:1794`) |
| JSON колонии | `colony_storage.py:270-271` оборачивает `_restore_saved_agent` | Загрузка в `_deserialize_agent` |

Дневной тик эти функции не вызывает. Код колонии не присваивает `go_weight`, `nogo_weight`, `habit_strength`. В JSON нет таблиц Q/V и привычек (в `colony_storage.py` таких полей нет). Каналы по-прежнему через `register_action_channel` ядра, который сам входит в `initializing()`. Консолидация сна — по-прежнему `Agent.sleep` из `_apply_sleep_recovery` (`colony_agent.py:938`).

### 3. Интервал бодрствования 403.2 с — да (шкала хоста, не подстройка ядра)

**Откуда.** `colony_expected_wake_interval_s` (`colony_agent.py:103-116`), передаётся только как `PlasticityConfig.expected_wake_interval_s` (`:188-190`). Другие поля пластичности не задаются.

**Счёт.** Засыпание при `SLEEP_WAKEFULNESS_THRESHOLD` 0.7 (`:73`). Пробуждение при `0.7 * SLEEP_HYSTERESIS` = 0.49 (`:74`). Промежуток `0.7 * (1 - 0.7) = 0.21`. Каждая секунда симуляции добавляет `WAKEFULNESS_ACCUMULATION_FACTOR` 30 (`:80`) физиологических секунд. Скорость давления — `WakefulnessState.ACCUMULATION_RATE = 1/(16*3600)` (`src/wakefulness.py:39`). `0.21 * 16 * 3600 / 30 = 403.2`. `return 3600.0` на `colony_agent.py:115` срабатывает только при неположительной скорости; при этих константах её нет.

**Смена поведения.** Да, и только у шкалы лабильного слоя. Без интервала `resolved_tau_s()` ядра равен 3600 (`src/labile_layer.py:75-92`). С этим значением хоста и дефолтным `tau_labile_ratio` 1.0 τ_L равен 403.2 с, дневные метки затухают быстрее за одно бодрствование колонии. Пороги сна колонии, сжатие ×30, η, clamp, κ и веса replay не менялись.

**Оправдание.** Приложение спеки ядра, пункт 1 доработки демо: хост задаёт среднюю длительность бодрствования между снами (`Docs/specs/issue-13-two-tier-plasticity.md:222`). Архитектура: хост передаёт `expected_wake_interval_s` в своих секундах (`Docs/architecture/two-tier-plasticity.en.md:76-77`). Спека колонии фиксирует 403.2 с и запрещает 3600 (`Docs/specs/issue-13-demo-colony.md:31-39`, приёмка 2 на `:71`). Коэффициенты ядра вне объёма (`:66`).

**Не подстройка ядра.** `git diff main...HEAD` не трогает `src/`. Конфиг не перекрывает `tau_labile_s`, `eta_labile_q`, `capture_kappa`, `replay_priority_weights`.

Заметка, не провал: 403.2 с — устойчивый сжатый подъём от 0.49 до 0.7, не замер симуляции. На тиках с решением `Agent.step` по-прежнему вызывает `wakefulness.update_waking()` без длительности (`src/agent.py:384`), и этот путь берёт настенные часы (`src/wakefulness.py:128-131`). Вызов старше этого PR и не входит в `_advance_host_clock`. Обновление колонии ×30 его перекрывает.

### 4. Изменений `src/` нет — да

Diff против `main` только:

- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.en.md`
- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.ru.md`
- `Demo/Colony chinchillas/src/colony_agent.py`
- `Demo/Colony chinchillas/src/colony_storage.py`
- `Demo/Colony chinchillas/tests/test_two_tier_host.py`
- `Docs/specs/issue-13-demo-colony.ru.md`

### 5. Двуязычные спека и тело PR, `Refs #13` — да

`Docs/specs/issue-13-demo-colony.ru.md`: сначала английский (`PART I`, `:8`), затем русский (`ЧАСТЬ II`, `:78`). Заголовок PR: `Refs #13: Colony demo on two-tier plasticity`. Тело: `## English`, затем `## Русский`; оба начинаются с `Refs #13`. В спеке агента по одной ссылке (`SPEC_ChinchillaAgent_NOWA.en.md:7`, `SPEC_ChinchillaAgent_NOWA.ru.md:7`).

## Замечания

Дефектов нет. Единственные остаточные наблюдения — в §3.
