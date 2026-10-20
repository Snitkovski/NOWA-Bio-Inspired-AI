# QA PR #42 — colony demo on two-tier plasticity

Branch: `team/demo-colony-two-tier` @ `8d67917` (code under review; this note is a later commit).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/42
Specs: `docs/specs/issue-13-two-tier-plasticity.md`, `docs/architecture/two-tier-plasticity.en.md`, `docs/specs/issue-13-demo-colony.md`.
Scope: one read of the diff, then two pytest commands. No full `Demo/` or `tests/` suite, no long sim, no seed loop. Product code was not edited.

## Verdict

**PASS**

No checklist item fails. The 403.2 s wake interval is a host time-scale setting. It changes labile decay relative to the unset 3600 s fallback. It does not retune core coefficients.

## Pytest

| Command | Result | Time |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 pytest "Demo/Colony chinchillas" -q` | **201 passed, 1 xpassed**, exit 0 | 18.46 s |
| `NOWA_STRICT_LEARNING=1 pytest "Demo/Colony chinchillas/tests/test_two_tier_host.py" -q` | **1 passed**, exit 0 | 0.29 s |

No `WakingLearningError` in either run. The xpass is the existing `test_tc01_two_agents_survive_300s` (`Demo/Colony chinchillas/tests/test_resources.py:30`, `strict=False`, issue #39). The author's full `pytest Demo` counts were not re-run.

## Checklist

### 1. Game `dt` once per tick — pass

`sim_step` (`Demo/Colony chinchillas/src/colony_agent.py:472-524`) takes one `_host_dt(dt)` (`:119-127`).

- Decision tick: `step(..., dt=host_dt)` at `:492-501`, then `advanced_by_step = True`. `commit_executed_transition` at `:514-524` is called with no `dt`.
- Continued sleep or `replaced_policy_action`: `step` is not called. `advance_time(host_dt)` runs once at `:512-513`, then the same commit omits `dt`.

Those two clocks are exclusive. Core `commit_executed_transition` advances only when `dt is not None` (`src/agent.py:1024-1025`). Core `step` advances in `_advance_host_clock(dt, wall_fallback=dt is None)` (`src/agent.py:381`). A passed `dt`, including the explicit `0` that `_host_dt` uses for non-finite or negative input, sets `wall_fallback=False` (`src/agent.py:4601-4610`). The wall-clock branch (`src/agent.py:4612-4624`) is not taken.

`test_two_tier_host.py:34-35` checks `_dt_warning_sent is False` and `_host_clock_s == 4` after four `sim_step(1)` calls. That passed.

### 2. Stable writes only under `initializing()`, and only at load or birth — pass

| Write | Scope | When |
| --- | --- | --- |
| Habit seed | `colony_agent.py:945-948` wraps `_write_habit_bootstrap` (`:950-976`) | Only from `__init__` (`:302`) |
| Genome on the constructor | `colony_agent.py:311-314` | Construction, when a genome is passed |
| Genome on a newborn | `colony_agent.py:1964-1969` inside `_inherit_nowa_from` | Birth: `_create_offspring` (`:1794`) |
| Colony JSON restore | `colony_storage.py:270-271` wraps `_restore_saved_agent` | Load in `_deserialize_agent` |

No waking tick calls those helpers. Colony code does not assign `go_weight`, `nogo_weight`, or `habit_strength`. The JSON payload has no Q/V or habit tables (`colony_storage.py` has no such fields). Channels stay on core `register_action_channel`, which enters `initializing()` itself. Sleep consolidation is still `Agent.sleep` from `_apply_sleep_recovery` (`colony_agent.py:938`).

### 3. Wake interval 403.2 s — pass (host scale, not core tuning)

**Where.** `colony_expected_wake_interval_s` (`colony_agent.py:103-116`), passed only as `PlasticityConfig.expected_wake_interval_s` (`:188-190`). No other plasticity field is set.

**Arithmetic.** Sleep onset `SLEEP_WAKEFULNESS_THRESHOLD` 0.7 (`:73`). Resume at `0.7 * SLEEP_HYSTERESIS` = 0.49 (`:74`). Span `0.7 * (1 - 0.7) = 0.21`. Each simulation second adds `WAKEFULNESS_ACCUMULATION_FACTOR` 30 (`:80`) physiological seconds. Pressure rate is `WakefulnessState.ACCUMULATION_RATE = 1/(16*3600)` (`src/wakefulness.py:39`). `0.21 * 16 * 3600 / 30 = 403.2`. The `return 3600.0` at `colony_agent.py:115` runs only if that rate is non-positive, which these constants are not.

**Behaviour change.** Yes, for the labile time scale only. With the interval unset, core `resolved_tau_s()` is 3600 (`src/labile_layer.py:75-92`). With this host value and the default `tau_labile_ratio` of 1.0, τ_L is 403.2 s, so waking tags decay faster across a colony wake bout. Colony sleep thresholds, the ×30 compression, η, clamps, κ, and replay weights are unchanged.

**Justified.** Core spec appendix, demo follow-up 1: the host sets the mean wake between sleeps (`docs/specs/issue-13-two-tier-plasticity.md:222`). Architecture: the host supplies `expected_wake_interval_s` in its own seconds (`docs/architecture/two-tier-plasticity.en.md:76-77`). The colony spec states 403.2 s and forbids using 3600 (`docs/specs/issue-13-demo-colony.md:31-39`, acceptance 2 at `:71`). It also leaves core coefficients out of scope (`:66`).

**Not core tuning.** `git diff main...HEAD` does not touch `src/`. The config does not override `tau_labile_s`, `eta_labile_q`, `capture_kappa`, or `replay_priority_weights`.

Note, not a failure: the 403.2 s figure is the steady compressed climb from 0.49 to 0.7. It is not a measured sim. On decision ticks, core `Agent.step` still calls `wakefulness.update_waking()` with no elapsed (`src/agent.py:384`), and that path uses the wall clock (`src/wakefulness.py:128-131`). That call predates this PR and is outside `_advance_host_clock`. The ×30 colony update dominates it.

### 4. No `src/` changes — pass

Diff against `main` is only:

- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.en.md`
- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.ru.md`
- `Demo/Colony chinchillas/src/colony_agent.py`
- `Demo/Colony chinchillas/src/colony_storage.py`
- `Demo/Colony chinchillas/tests/test_two_tier_host.py`
- `docs/specs/issue-13-demo-colony.md`

### 5. Bilingual spec and PR body, `Refs #13` — pass

`docs/specs/issue-13-demo-colony.md` is English (`PART I`, `:8`) then Russian (`ЧАСТЬ II`, `:78`). The PR title is `Refs #13: Colony demo on two-tier plasticity`. The body is `## English` then `## Русский`, and both open with `Refs #13`. The agent spec has one pointer each (`SPEC_ChinchillaAgent_NOWA.en.md:7`, `SPEC_ChinchillaAgent_NOWA.ru.md:7`).

## Findings

No defects. The notes in §3 are the only residual observations.

---

# QA PR #42 — демо колонии на двухуровневой пластичности

Ветка: `team/demo-colony-two-tier` @ `8d67917` (код под проверкой; эта заметка — следующий коммит).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/42
Спеки: `docs/specs/issue-13-two-tier-plasticity.md`, `docs/architecture/two-tier-plasticity.en.md`, `docs/specs/issue-13-demo-colony.md`.
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

**Оправдание.** Приложение спеки ядра, пункт 1 доработки демо: хост задаёт среднюю длительность бодрствования между снами (`docs/specs/issue-13-two-tier-plasticity.md:222`). Архитектура: хост передаёт `expected_wake_interval_s` в своих секундах (`docs/architecture/two-tier-plasticity.en.md:76-77`). Спека колонии фиксирует 403.2 с и запрещает 3600 (`docs/specs/issue-13-demo-colony.md:31-39`, приёмка 2 на `:71`). Коэффициенты ядра вне объёма (`:66`).

**Не подстройка ядра.** `git diff main...HEAD` не трогает `src/`. Конфиг не перекрывает `tau_labile_s`, `eta_labile_q`, `capture_kappa`, `replay_priority_weights`.

Заметка, не провал: 403.2 с — устойчивый сжатый подъём от 0.49 до 0.7, не замер симуляции. На тиках с решением `Agent.step` по-прежнему вызывает `wakefulness.update_waking()` без длительности (`src/agent.py:384`), и этот путь берёт настенные часы (`src/wakefulness.py:128-131`). Вызов старше этого PR и не входит в `_advance_host_clock`. Обновление колонии ×30 его перекрывает.

### 4. Изменений `src/` нет — да

Diff против `main` только:

- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.en.md`
- `Demo/Colony chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.ru.md`
- `Demo/Colony chinchillas/src/colony_agent.py`
- `Demo/Colony chinchillas/src/colony_storage.py`
- `Demo/Colony chinchillas/tests/test_two_tier_host.py`
- `docs/specs/issue-13-demo-colony.md`

### 5. Двуязычные спека и тело PR, `Refs #13` — да

`docs/specs/issue-13-demo-colony.md`: сначала английский (`PART I`, `:8`), затем русский (`ЧАСТЬ II`, `:78`). Заголовок PR: `Refs #13: Colony demo on two-tier plasticity`. Тело: `## English`, затем `## Русский`; оба начинаются с `Refs #13`. В спеке агента по одной ссылке (`SPEC_ChinchillaAgent_NOWA.en.md:7`, `SPEC_ChinchillaAgent_NOWA.ru.md:7`).

## Замечания

Дефектов нет. Единственные остаточные наблюдения — в §3.
