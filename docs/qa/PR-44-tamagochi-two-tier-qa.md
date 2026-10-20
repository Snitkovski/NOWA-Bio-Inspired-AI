# QA PR #44 — Tamagochi demo on two-tier plasticity

Branch: `team/demo-tamagochi-two-tier` @ `bcf4f16` (code under review; this note is a later commit).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/44
Base: `origin/main` @ `8971960`.
Specs: `docs/specs/issue-13-two-tier-plasticity.md`, `docs/architecture/two-tier-plasticity.en.md`, `docs/specs/issue-13-demo-tamagochi.md`.
Scope: one read of the diff, call-graph of the sleep guards, one daytime/sleep probe, and the pytest commands below. No full `Demo/` suite, no long sim, no seed loop. Product code was not edited.

## Verdict

**FAIL**

`src/` is unchanged. Game `dt` reaches the core once per `sim_step`. `expected_wake_interval_s` is `10080` and matches the cage pressure constants. The new host test passes, and both Tamagochi pytest modes exit 0.

Three defects remain. Intent habits never receive the sleep outcome write. One deep sleep then applies a second Go/NoGo/habit update on the same channels. `IntentMemory.record_trace` is still called when a chain starts while awake; strict mode raises `WakingLearningError`, and the caller swallows it, so the suite stays green.

## Pytest

Python 3.12.3, pytest 9.1.1. Commands run from the repo root.

| Command | Result | Time |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 warnings, exit 0 | 2.40 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 warnings, exit 0 | 2.47 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **893 passed, 5 skipped**, 2 warnings, exit 0 | 190.55 s |
| `NOWA_STRICT_LEARNING=0 python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **6 failed, 887 passed, 5 skipped**, 2 warnings, exit 1 | 190.34 s |

No `WakingLearningError` in the Tamagochi pytest output. The exception is raised and caught inside `sim_step` (defect 3); these two commands do not start a chain, because the committed save is mid-action (see the probe).

The 15 warnings are `PytestReturnNotNoneWarning` on older tests that `return True`. They are outside this diff.

### The six core failures are the forced-env artifact

`git diff --stat origin/main...HEAD -- src tests` is empty. The core suite at `bcf4f16` is the suite on `origin/main`.

`tests/conftest.py:10` does `os.environ.setdefault("NOWA_STRICT_LEARNING", "1")`. A process that already has `NOWA_STRICT_LEARNING=0` keeps `0`. The guard then skips the write and logs, and `pytest.raises(WakingLearningError)` fails. Each failure message is `Failed: DID NOT RAISE WakingLearningError`.

| Test | Assertion |
| --- | --- |
| `tests/test_issue13_two_tier.py::test_stable_fingerprint_is_unchanged_across_waking_calls` | `:93` |
| `tests/test_issue13_two_tier.py::test_direct_replay_does_not_open_the_learning_guard` | `:476` |
| `tests/test_issue13_two_tier.py::test_waking_guard_blocks_direct_stable_writes` | `:650` |
| `tests/test_qa_pr37_labile_layer.py::test_strict_guard_raises_and_production_skips_once` | `:357` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_named_guards_raise_in_strict_mode_and_skip_once_in_production` | `:422` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn` | `:536` |

With the variable unset, the same tree is **893 passed, 5 skipped**. These six are not a regression from this PR.

## Checklist

### 1. `src/` against `main` — pass

Diff of `bcf4f16` against `origin/main` is only:

- `Demo/Tamagochi Chinchilla/src/main.py`
- `Demo/Tamagochi Chinchilla/tests/test_two_tier_host.py`
- `docs/specs/issue-13-demo-tamagochi.md`

### 2. Daytime stable writes — fail

Removed from the waking path, confirmed in the diff and by search of `main.py`: `value_layer.update(mode="online")` (comment only, `:1454`), `strengthen_trace`, `update_weights`, and a direct `apply_learning_hooks` on the rating click.

`apply_learning_hooks` remains only in `_flush_owner_feedback` (`:2085`). Callers are the light-sleep branch (`:1710`) and `_run_sleep_consolidation` (`:3372`). `_apply_training_feedback` (`:1978`) appends to `_pending_owner_feedback` and does not call it.

`learning_allowed()` blocks:

| Block | Reached from |
| --- | --- |
| `:1707-1711` flush, then `sleep_cycle()` | `sim_step` only when `is_light_sleep` (`:1700`) |
| `:3296-3298` habit modulation and `degrade_unused` | `_run_sleep_consolidation` |
| `:3371-3382` flush, `apply_sleep_learning`, `consolidate_habits` | `_run_sleep_consolidation` |

`_run_sleep_consolidation` is called from production code only at `:1699`, inside `is_deep_sleep`. The test calls it directly. These three wrappers are not on the waking path.

`initializing()` wraps channel restore (`:3536-3552`) and the fallback `ActionChannel` (`:2466-2469`). `nowa.register_action_channel` (`:2463`) enters `initializing()` in the core (`src/agent.py:2830-2832`).

Defect 3: `record_trace` at `:1823` is still a waking call.

### 3. `dt` once, wake interval `10080` — pass

`sim_step` calls `nowa.advance_time(_host_dt(dt))` once (`main.py:1114-1115`). There is no second `advance_time`, no `Agent.step`, and no `commit_executed_transition`. `Agent.advance_time` uses `_advance_host_clock(..., wall_fallback=False)` (`src/agent.py:4627-4629`). Non-finite or negative `dt` becomes `0` in `_host_dt` (`main.py:292-299`).

`tamagochi_expected_wake_interval_s` (`:276-289`) returns `_SLEEP_ONSET_PRESSURE / _WAKE_PRESSURE_RATE` = `0.7 / (1/(4*3600))` = `10080`. The cage installs that rate on `WakefulnessState` (`:430-432`). Bedtime pressure is boosted when wake pressure exceeds `0.7` (`:2581-2582`). The constructor starts at `0.1` (`:431`), so the first climb is `(0.7-0.1)*14400` = `8640` s. `SchedulingSystem()` keeps the default `cycle_period` of `1200` (`scheduling_system.py:77`, constructed at `main.py:394`). Recovery is `1/(2*3600)` (`:433`); `960` s of `sleep_house` (`config.py:224`) drops pressure by at most `960/7200` ≈ `0.133`. No other `PlasticityConfig` field is set. `src/` is untouched, so core coefficients are not retuned.

`test_two_tier_host.py` asserts the interval, `+4` on `_host_clock_s`, `_dt_warning_sent is False`, an unchanged fingerprint after four `sim_step(1)` and one waking outcome, and a changed fingerprint after `_run_sleep_consolidation`. That test passed inside the 24.

### 4. Shared `nowa` with `sleep_manager=None` — fail

`_bind_two_tier_host` builds `Agent(..., sleep_manager=None)` (`:979-987`), so `Agent.__init__` does not attach its private value layer to the cage manager (`src/agent.py:160-174`). `_rewire_two_tier_host` (`:991-1053`) then points `nowa` at the cage `value_layer`, `bg_channels`, and `sleep_manager`, and sets `labile`, `plasticity`, and `_host_agent` on that manager.

Probe after `ChinchillaAgent(...)` (loads the committed `Demo/Tamagochi Chinchilla/saves/nowa_state.json`): `nowa.bg_action_channels`, `agent.bg_channels`, and `sleep_manager.bg_action_channels` are one dict; the three value layers are one object; `nowa.sleep_manager` is the cage manager. `deep_sleep` therefore runs `_consolidate_two_tier_once` on the cage channels. Q replay is that `deep_sleep`, not a second `Agent.sleep`. `Agent.sleep` is not called.

`SleepManager` is constructed without `intent_memory` (`:529-534`). Rewire does not set it. `nowa.intent_memory` is the cage object, and `sleep_manager.intent_memory` stays `None`. Core habit EMA reads the manager (`src/sleep.py:2921-2928`) and does not run. Defect 1.

After that capture, the cage calls `apply_sleep_learning` and `consolidate_habits` on the same channels and replaces the dict entries (`:3371-3384`). Defect 2.

### 5. Tests — pass, with defect 3 hidden by `except`

Both Tamagochi modes and the default core run passed. The six `NOWA_STRICT_LEARNING=0` failures are the conftest artifact above. The suite does not fail on defect 3 because `record_trace` is inside `except Exception` (`:1828`).

### 6. Fingerprint day vs sleep — pass as written

`test_waking_ticks_hold_stable_tier_until_sleep` passed. It does not read intent-trace strength and does not compare channel weights after `deep_sleep` with weights after the cage BG block. Those two gaps are defects 1 and 2.

### 7. Spec vs code — fail on the two sleep writers

Matching: host is not an `Agent` subclass; `sleep_manager=None` then rewire; one `advance_time` per tick; interval `10080` and the `8640` / `1200` / `0.133` figures; waking chain outcome goes through `_record_known_outcome`; owner ratings are queued; channel restore and `register_action_channel` use `initializing()`; `deep_sleep(cycles=2)` and one `sleep_cycle` are the schedule; `src/` is unchanged.

Not matching: spec §3 says `note_selection` leaves strength 0 until sleep. Sleep does not run `apply_outcome` on the cage memory, then `degrade_unused(0.85)` deletes the strength-0 trace (defect 1). Spec acceptance 5 says the suite must not raise `WakingLearningError`. `record_trace` raises it on a waking chain start (defect 3). The spec's "cage's own sleep writers" matches the second BG write being present; it does not say that write is a second Go/NoGo/habit step after core capture (defect 2).

## Defects

### 1. High — sleep never applies the intent outcome

`Demo/Tamagochi Chinchilla/src/main.py:529-534` and `:1044-1053`. Capture uses `src/sleep.py:2921`.

`SleepManager.intent_memory` is `None` for the life of the cage. `_apply_episode_channel_and_habit` therefore skips `IntentMemory.apply_outcome`. The daytime path now calls `note_selection` (`main.py:1580-1584`), which stores strength 0. `_run_sleep_consolidation` then runs `degrade_unused(0.85)` (`:3298`). Strength 0 is below `min_strength_for_trace` (0.1), so the trace is deleted. `stable_fingerprint` ignores strength `<= 0` (`src/learning_guard.py:124-126`), so the host test still passes.

Reproduce, from the repo root, with `NOWA_STRICT_LEARNING=1` and `src` plus `Demo/Tamagochi Chinchilla/src` on `sys.path`:

1. `agent = ChinchillaAgent(demo_dir="Demo/Tamagochi Chinchilla", use_pygame=False, use_gui=False)`.
2. Store one hippocampal episode for `eating_and_grooming` with reward `1.0`, call `_commit_waking_chain_outcome` with that episode, and `note_selection(["idle"], "eating_and_grooming")`.
3. Observe `sleep_manager.intent_memory is None` and the new trace strength `0.0`.
4. Call `_run_sleep_consolidation`.

Observed: after `deep_sleep` the trace strength is still `0.0`; after the cage degrade the key `eating_and_grooming:ec2f993a` is gone.

### 2. Medium — one deep sleep writes Go/NoGo/habit twice

`Demo/Tamagochi Chinchilla/src/main.py:3199` then `:3371-3384`.

`deep_sleep(cycles=2)` already runs the once-per-sleep channel capture and two decay cycles on the shared `bg_channels`. The following block clones those channels through `BasalGangliaLearning.apply_sleep_learning` and `consolidate_habits`, then replaces the dict values (`:3383-3384`). Core replay does not update Go/NoGo (`src/sleep.py:1427-1433`). This second formula does.

Same probe as defect 1, channel `eating_and_grooming`, weights `(go, nogo, habit)` from the committed `nowa_state.json`:

| Point | go | nogo | habit |
| --- | --- | --- | --- |
| Before sleep | 0.523348 | 0.454799 | 0.046013 |
| After `deep_sleep` returns | 0.599256 | 0.418173 | 0.227433 |
| After `_run_sleep_consolidation` returns | 0.667727 | 0.376987 | 0.251192 |

The channel object id changes on the second step. `last_outcome` was set by waking `record_outcome` (`:1484-1485`), which is what `apply_sleep_learning` reads.

### 3. Medium — waking `record_trace` raises, and the caller hides it

`Demo/Tamagochi Chinchilla/src/main.py:1821-1829`. Guard: `src/intent_memory.py:161`.

`_try_start_chain` calls `intent_memory.record_trace` with no `learning_allowed()` or `initializing()`. In strict mode that raises `WakingLearningError: IntentMemory.record_trace writes the stable tier while awake.` The `except Exception` at `:1828` discards it. The trace is not written (`traces` stayed 0). Pytest stays green.

Reproduce: construct the agent as above (the committed save has `action_remaining_s` ≈ 330.6 on `sleep_house`, so a short `sim_step` loop does not start a chain). Set `running = True`, `action_remaining_s = 0`, `chain_cooldown_s = 0`, `current_chain = None`, `current_action = None`, `wakefulness = 0.1`. One `sim_step(0.1)` started `mild_fear` and raised that error once. The step still completed.

## Remarks

The host test's four `sim_step(1)` calls run against the committed save (`tick_count` 74772, `sleep_house` still in progress). `advance_time` still runs, so the clock and fingerprint assertions are real. They do not reach `record_trace` or the sleep branches. `sim_step` returns at `:1679` while `action_remaining_s > 0`, so the pressure band is sampled when the sleep action ends, which is the schedule spec §6 already describes.

`nowa`'s own slow-affect queue stays empty because the cage does not call `Agent.step`. Spec §6. Light sleep calls `sleep_cycle` and does not call `_consolidate_two_tier_once`. That matches spec §2: capture is on `deep_sleep`.

`tests/test_complete_flow.py` and `tests/test_debug_load.py` execute at import and delete `saves/*.pkl`. Two overlapping `pytest tests` processes can make collection raise `FileNotFoundError`. A single run collected them. `tests/` is unchanged in this PR.

---

# QA PR #44 — демо Tamagochi на двухуровневой пластичности

Ветка: `team/demo-tamagochi-two-tier` @ `bcf4f16` (код под проверкой; эта заметка — следующий коммит).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/44
База: `origin/main` @ `8971960`.
Спеки: `docs/specs/issue-13-two-tier-plasticity.md`, `docs/architecture/two-tier-plasticity.en.md`, `docs/specs/issue-13-demo-tamagochi.md`.
Объём: одно чтение diff, граф вызовов guard сна, один пробник дня и сна, и команды pytest ниже. Полного `Demo/` нет, длинной симуляции нет, перебора сидов нет. Продуктовый код не менялся.

## Вердикт

**FAIL**

`src/` не изменён. Игровой `dt` доходит до ядра один раз за `sim_step`. `expected_wake_interval_s` равен `10080` и совпадает с константами давления клетки. Новый тест хоста проходит, оба режима pytest Tamagochi завершаются с кодом 0.

Остаются три дефекта. Привычки намерения не получают запись исхода во сне. Один глубокий сон затем второй раз обновляет Go/NoGo/привычку тех же каналов. `IntentMemory.record_trace` по-прежнему вызывается при старте цепочки днём; в строгом режиме это `WakingLearningError`, вызывающий код его глотает, и набор тестов остаётся зелёным.

## Pytest

Python 3.12.3, pytest 9.1.1. Команды из корня репозитория.

| Команда | Результат | Время |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 предупреждений, код 0 | 2.40 с |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 предупреждений, код 0 | 2.47 с |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **893 passed, 5 skipped**, 2 предупреждения, код 0 | 190.55 с |
| `NOWA_STRICT_LEARNING=0 python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **6 failed, 887 passed, 5 skipped**, 2 предупреждения, код 1 | 190.34 с |

В выводе pytest Tamagochi `WakingLearningError` нет. Исключение поднимается и ловится внутри `sim_step` (дефект 3); эти две команды цепочку не начинают, потому что закоммиченное сохранение застаёт действие на середине (см. пробник).

15 предупреждений — `PytestReturnNotNoneWarning` у старых тестов с `return True`. Их нет в этом diff.

### Шесть падений ядра — артефакт принудительного env

`git diff --stat origin/main...HEAD -- src tests` пуст. Набор ядра на `bcf4f16` — это набор на `origin/main`.

`tests/conftest.py:10` делает `os.environ.setdefault("NOWA_STRICT_LEARNING", "1")`. Процесс, в котором уже стоит `NOWA_STRICT_LEARNING=0`, сохраняет `0`. Guard пропускает запись и пишет в лог, `pytest.raises(WakingLearningError)` падает. Текст каждого падения: `Failed: DID NOT RAISE WakingLearningError`.

| Тест | Проверка |
| --- | --- |
| `tests/test_issue13_two_tier.py::test_stable_fingerprint_is_unchanged_across_waking_calls` | `:93` |
| `tests/test_issue13_two_tier.py::test_direct_replay_does_not_open_the_learning_guard` | `:476` |
| `tests/test_issue13_two_tier.py::test_waking_guard_blocks_direct_stable_writes` | `:650` |
| `tests/test_qa_pr37_labile_layer.py::test_strict_guard_raises_and_production_skips_once` | `:357` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_named_guards_raise_in_strict_mode_and_skip_once_in_production` | `:422` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn` | `:536` |

Без переменной то же дерево даёт **893 passed, 5 skipped**. Эти шесть — не регрессия этого PR.

## Проверка

### 1. `src/` против `main` — да

Diff `bcf4f16` против `origin/main` только:

- `Demo/Tamagochi Chinchilla/src/main.py`
- `Demo/Tamagochi Chinchilla/tests/test_two_tier_host.py`
- `docs/specs/issue-13-demo-tamagochi.md`

### 2. Дневные записи стабильного слоя — нет

С дневного пути убраны, это видно в diff и поиском по `main.py`: `value_layer.update(mode="online")` (только комментарий, `:1454`), `strengthen_trace`, `update_weights` и прямой `apply_learning_hooks` на клике оценки.

`apply_learning_hooks` остаётся только в `_flush_owner_feedback` (`:2085`). Вызовы — ветка лёгкого сна (`:1710`) и `_run_sleep_consolidation` (`:3372`). `_apply_training_feedback` (`:1978`) кладёт оценку в `_pending_owner_feedback` и сам хук не вызывает.

Блоки `learning_allowed()`:

| Блок | Откуда |
| --- | --- |
| `:1707-1711` очередь оценок, затем `sleep_cycle()` | `sim_step` только при `is_light_sleep` (`:1700`) |
| `:3296-3298` модуляция привычек и `degrade_unused` | `_run_sleep_consolidation` |
| `:3371-3382` очередь, `apply_sleep_learning`, `consolidate_habits` | `_run_sleep_consolidation` |

`_run_sleep_consolidation` из продакшн-кода вызывается только на `:1699`, внутри `is_deep_sleep`. Тест вызывает его напрямую. Эти три обёртки не стоят на дневном пути.

`initializing()` оборачивает восстановление каналов (`:3536-3552`) и запасной `ActionChannel` (`:2466-2469`). `nowa.register_action_channel` (`:2463`) сам входит в `initializing()` в ядре (`src/agent.py:2830-2832`).

Дефект 3: `record_trace` на `:1823` остаётся дневным вызовом.

### 3. `dt` один раз, интервал `10080` — да

`sim_step` один раз вызывает `nowa.advance_time(_host_dt(dt))` (`main.py:1114-1115`). Второго `advance_time`, `Agent.step` и `commit_executed_transition` нет. `Agent.advance_time` идёт в `_advance_host_clock(..., wall_fallback=False)` (`src/agent.py:4627-4629`). Нечисловой или отрицательный `dt` становится `0` в `_host_dt` (`main.py:292-299`).

`tamagochi_expected_wake_interval_s` (`:276-289`) возвращает `_SLEEP_ONSET_PRESSURE / _WAKE_PRESSURE_RATE` = `0.7 / (1/(4*3600))` = `10080`. Клетка ставит эту скорость в `WakefulnessState` (`:430-432`). Давление рутины сна растёт, когда давление бодрствования выше `0.7` (`:2581-2582`). Конструктор стартует с `0.1` (`:431`), первый подъём — `(0.7-0.1)*14400` = `8640` с. `SchedulingSystem()` оставляет дефолтный `cycle_period` `1200` (`scheduling_system.py:77`, создание на `main.py:394`). Восстановление — `1/(2*3600)` (`:433`); `960` с `sleep_house` (`config.py:224`) снижают давление не больше чем на `960/7200` ≈ `0.133`. Другие поля `PlasticityConfig` не задаются. `src/` не тронут, коэффициенты ядра не перенастроены.

`test_two_tier_host.py` проверяет интервал, `+4` к `_host_clock_s`, `_dt_warning_sent is False`, неизменный отпечаток после четырёх `sim_step(1)` и одного дневного исхода, и изменившийся отпечаток после `_run_sleep_consolidation`. Этот тест вошёл в 24 прошедших.

### 4. Общий `nowa` с `sleep_manager=None` — нет

`_bind_two_tier_host` создаёт `Agent(..., sleep_manager=None)` (`:979-987`), поэтому `Agent.__init__` не вешает свою таблицу ценности на менеджер клетки (`src/agent.py:160-174`). `_rewire_two_tier_host` (`:991-1053`) направляет `nowa` на `value_layer`, `bg_channels` и `sleep_manager` клетки и ставит на этот менеджер `labile`, `plasticity` и `_host_agent`.

Пробник после `ChinchillaAgent(...)` (грузит закоммиченный `Demo/Tamagochi Chinchilla/saves/nowa_state.json`): `nowa.bg_action_channels`, `agent.bg_channels` и `sleep_manager.bg_action_channels` — один словарь; три таблицы ценности — один объект; `nowa.sleep_manager` — менеджер клетки. `deep_sleep` поэтому выполняет `_consolidate_two_tier_once` на каналах клетки. Replay Q — этот `deep_sleep`, не второй `Agent.sleep`. `Agent.sleep` не вызывается.

`SleepManager` создаётся без `intent_memory` (`:529-534`). Rewire его не ставит. `nowa.intent_memory` — объект клетки, `sleep_manager.intent_memory` остаётся `None`. EMA привычки в ядре читает менеджер (`src/sleep.py:2921-2928`) и не выполняется. Дефект 1.

После этого захвата клетка вызывает `apply_sleep_learning` и `consolidate_habits` на тех же каналах и подменяет записи словаря (`:3371-3384`). Дефект 2.

### 5. Тесты — да, дефект 3 спрятан `except`

Оба режима Tamagochi и ядро в дефолтном режиме прошли. Шесть падений при `NOWA_STRICT_LEARNING=0` — артефакт conftest выше. Набор не падает на дефекте 3, потому что `record_trace` стоит внутри `except Exception` (`:1828`).

### 6. Отпечаток днём и после сна — да в том виде, как написан тест

`test_waking_ticks_hold_stable_tier_until_sleep` прошёл. Он не читает силу следа намерения и не сравнивает веса канала после `deep_sleep` с весами после блока BG клетки. Эти два пробела — дефекты 1 и 2.

### 7. Спека и код — нет по двум писателям сна

Совпадает: хост не подкласс `Agent`; `sleep_manager=None`, затем rewire; один `advance_time` за тик; интервал `10080` и цифры `8640` / `1200` / `0.133`; дневной исход цепочки идёт через `_record_known_outcome`; оценки владельца в очереди; восстановление канала и `register_action_channel` под `initializing()`; расписание — `deep_sleep(cycles=2)` и один `sleep_cycle`; `src/` не изменён.

Не совпадает: §3 спеки говорит, что `note_selection` оставляет силу 0 до сна. Сон не вызывает `apply_outcome` на памяти клетки, затем `degrade_unused(0.85)` удаляет след с силой 0 (дефект 1). Приёмка 5 говорит, что набор не должен поднимать `WakingLearningError`. `record_trace` поднимает его на дневном старте цепочки (дефект 3). Формулировка спеки «собственные писатели сна клетки» совпадает с тем, что вторая запись BG есть; она не говорит, что это второй шаг Go/NoGo/привычки после захвата ядра (дефект 2).

## Дефекты

### 1. Высокий — сон не применяет исход к привычке намерения

`Demo/Tamagochi Chinchilla/src/main.py:529-534` и `:1044-1053`. Захват: `src/sleep.py:2921`.

`SleepManager.intent_memory` равен `None` всё время жизни клетки. `_apply_episode_channel_and_habit` поэтому пропускает `IntentMemory.apply_outcome`. Дневной путь теперь вызывает `note_selection` (`main.py:1580-1584`), он кладёт силу 0. `_run_sleep_consolidation` затем вызывает `degrade_unused(0.85)` (`:3298`). Сила 0 ниже `min_strength_for_trace` (0.1), след удаляется. `stable_fingerprint` игнорирует силу `<= 0` (`src/learning_guard.py:124-126`), поэтому тест хоста проходит.

Воспроизведение из корня репозитория, `NOWA_STRICT_LEARNING=1`, в `sys.path` есть `src` и `Demo/Tamagochi Chinchilla/src`:

1. `agent = ChinchillaAgent(demo_dir="Demo/Tamagochi Chinchilla", use_pygame=False, use_gui=False)`.
2. Положить в гиппокамп один эпизод `eating_and_grooming` с наградой `1.0`, вызвать `_commit_waking_chain_outcome` с этим эпизодом и `note_selection(["idle"], "eating_and_grooming")`.
3. Увидеть `sleep_manager.intent_memory is None` и силу нового следа `0.0`.
4. Вызвать `_run_sleep_consolidation`.

Наблюдение: после `deep_sleep` сила следа всё ещё `0.0`; после деградации клетки ключа `eating_and_grooming:ec2f993a` нет.

### 2. Средний — один глубокий сон пишет Go/NoGo/привычку дважды

`Demo/Tamagochi Chinchilla/src/main.py:3199`, затем `:3371-3384`.

`deep_sleep(cycles=2)` уже делает захват каналов один раз за сон и два цикла затухания на общем `bg_channels`. Следующий блок клонирует эти каналы через `BasalGangliaLearning.apply_sleep_learning` и `consolidate_habits`, затем подменяет значения словаря (`:3383-3384`). Replay ядра Go/NoGo не обновляет (`src/sleep.py:1427-1433`). Эта вторая формула обновляет.

Тот же пробник, что в дефекте 1, канал `eating_and_grooming`, веса `(go, nogo, habit)` из закоммиченного `nowa_state.json`:

| Точка | go | nogo | habit |
| --- | --- | --- | --- |
| До сна | 0.523348 | 0.454799 | 0.046013 |
| После возврата из `deep_sleep` | 0.599256 | 0.418173 | 0.227433 |
| После возврата из `_run_sleep_consolidation` | 0.667727 | 0.376987 | 0.251192 |

Идентификатор объекта канала меняется на втором шаге. `last_outcome` ставит дневной `record_outcome` (`:1484-1485`), его и читает `apply_sleep_learning`.

### 3. Средний — дневной `record_trace` поднимает исключение, вызывающий код его прячет

`Demo/Tamagochi Chinchilla/src/main.py:1821-1829`. Guard: `src/intent_memory.py:161`.

`_try_start_chain` вызывает `intent_memory.record_trace` без `learning_allowed()` и без `initializing()`. В строгом режиме это `WakingLearningError: IntentMemory.record_trace writes the stable tier while awake.` `except Exception` на `:1828` его отбрасывает. След не пишется (`traces` остался 0). Pytest остаётся зелёным.

Воспроизведение: создать агента как выше (в закоммиченном сохранении `action_remaining_s` ≈ 330.6 на `sleep_house`, поэтому короткий цикл `sim_step` цепочку не начинает). Поставить `running = True`, `action_remaining_s = 0`, `chain_cooldown_s = 0`, `current_chain = None`, `current_action = None`, `wakefulness = 0.1`. Один `sim_step(0.1)` начал `mild_fear` и один раз поднял эту ошибку. Шаг при этом завершился.

## Замечания

Четыре `sim_step(1)` теста хоста идут по закоммиченному сохранению (`tick_count` 74772, `sleep_house` ещё идёт). `advance_time` всё равно вызывается, проверки часов и отпечатка настоящие. До `record_trace` и веток сна они не доходят. `sim_step` возвращается на `:1679`, пока `action_remaining_s > 0`, поэтому полоса давления смотрится в момент окончания действия сна. Это расписание, которое §6 спеки уже описывает.

Очередь медленного аффекта самого `nowa` пуста, потому что клетка не вызывает `Agent.step`. Спека §6. Лёгкий сон вызывает `sleep_cycle` и не вызывает `_consolidate_two_tier_once`. Это совпадает с §2 спеки: захват на `deep_sleep`.

`tests/test_complete_flow.py` и `tests/test_debug_load.py` выполняются при импорте и удаляют `saves/*.pkl`. Два одновременных `pytest tests` могут дать `FileNotFoundError` на сборе. Одиночный прогон их собрал. `tests/` в этом PR не менялся.
