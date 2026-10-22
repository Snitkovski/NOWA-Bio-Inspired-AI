# QA PR #44 — демо Tamagochi на двухуровневой пластичности

Ветка: `team/demo-tamagochi-two-tier`. Раунд 2 смотрит `7442837`. Раунд 1 смотрел `bcf4f16`.
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/44
База: `origin/main` @ `8971960`.
Спеки: `Docs/specs/issue-13-two-tier-plasticity.ru.md`, `Docs/architecture/two-tier-plasticity.ru.md`, `Docs/specs/issue-13-demo-tamagochi.ru.md`.

## Раунд 2 — вердикт

**PASS**

Коммит `7442837` закрывает три дефекта раунда 1. Регрессионные тесты в `Demo/Tamagochi Chinchilla/tests/test_two_tier_host.py` падают, если любой из них вернётся. `git diff --stat origin/main...HEAD -- src` пуст. Продуктовый код в этом проходе не менялся.

### Три исправления

1. Захват привычки. `SleepManager` создаётся с `intent_memory` клетки (`main.py:532`), `_rewire_two_tier_host` ставит тот же объект (`:1056`). Пробник: `sleep_manager.intent_memory is agent.intent_memory`. След `note_selection(["idle"], "eating_and_grooming")` с силой 0 после `_run_sleep_consolidation` на месте, сила `0.0907` (порог `0.08`). `test_sleep_capture_applies_intent_outcome` проверяет идентичность и `max(strength) > 0`.

2. Одна запись канала. `apply_sleep_learning` и `consolidate_habits` убраны (ноль вызовов). После `deep_sleep` клетка только сбрасывает оценки владельца (`:3344-3350`). Пробник, канал `eating_and_grooming` из закоммиченного сохранения: до сна `(go 0.523348, nogo 0.454799, habit 0.046013)`; после `deep_sleep` и после `_run_sleep_consolidation` тот же объект и те же веса `(0.599256, 0.418173, 0.227433)`. Захват по-прежнему двигает веса. `test_deep_sleep_is_the_only_channel_writer` проверяет id объекта и три веса на этой границе.

3. Дневного `record_trace` нет. Старт цепочки вызывает `note_selection` (`:1823-1826`) и не ловит `Exception`. Новые следы остаются с силой 0. `fail_if_waking_learning_error_was_caught` (`test_two_tier_host.py:17-40`) считает `WakingLearningError`, даже если вызывающий код его глотает. `test_chain_start_does_not_write_stable_intent` стартует цепочку через `sim_step(0.1)`.

Новых дневных стабильных записей нет. Поиск по `main.py`: нет `record_trace`, нет `strengthen_trace`, нет `update_weights`, нет вызова `value_layer.update(mode="online")`. `apply_learning_hooks` остаётся только внутри `_flush_owner_feedback`.

### Консолидация на месте

Оценка 5 встаёт в очередь через `_apply_training_feedback` и днём не меняет логиты и `stable_fingerprint`. `_run_sleep_consolidation` очередь очищает. `strategy_logits` сдвигаются (пример: логит `eating_and_grooming` равен `0.08`). Веса softmax остаются равномерными, потому что все логиты сдвигаются вместе. Привычка канала по-прежнему двигается внутри `deep_sleep` (0.046013 → 0.227433).

### Оба затухания за одну ночь

`deep_sleep(cycles=2)` дважды вызывает `degrade_unused(0.8)`, затем клетка вызывает `degrade_unused(0.85)` (`:3296`) уже после захвата. После всей ночи: новый след исхода `0.0907`, след, посеянный на `0.2`, тоже `0.0907`, след, посеянный на `0.6`, равен `0.2722`. Все выше `0.08`. В эту ночь они не удаляются.

### Pytest

Python 3.12.3, pytest 9.1.1, корень репозитория.

| Команда | Результат | Время |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **27 passed**, 15 предупреждений, код 0 | 2.77 с |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **27 passed**, 15 предупреждений, код 0 | 2.64 с |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **893 passed, 5 skipped**, 2 предупреждения, код 0 | 194.57 с |

В выводе Tamagochi `WakingLearningError` нет. 15 предупреждений — прежний `PytestReturnNotNoneWarning`.

### Замечание

Один награждённый исход заканчивается на `0.0907`. Следующий `_run_sleep_consolidation`, когда эпизод уже консолидирован, этот след удаляет: первый `degrade_unused(0.8)` опускает его ниже `0.08`. След, посеянный на `0.6`, в этой полосе не оказывается. Тест хоста проверяет только силу `> 0` после одной ночи.

---

## Раунд 1 — вердикт

**FAIL** на `bcf4f16`. Ниже — запись того прохода. Объём тогда: одно чтение diff, граф вызовов guard сна, один пробник дня и сна, и команды pytest в этом разделе. Полного `Demo/` нет, длинной симуляции нет, перебора сидов нет. Продуктовый код не менялся.

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
- `Docs/specs/issue-13-demo-tamagochi.ru.md`

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
