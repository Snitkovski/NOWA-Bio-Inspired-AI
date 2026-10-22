# QA: PR #33 — обучение ядра на награде (C01–C06, C09)

> **Superseded for core learning contract by issue #13 two-tier plasticity** (PR #37 labile layer, PR #40 sleep consolidation). Waking stable writes described here are no longer current; see `Docs/specs/issue-13-two-tier-plasticity.ru.md` and `Docs/architecture/two-tier-plasticity.ru.md`.
>
> **Заменено двухуровневой моделью #13** для контракта обучения ядра (PR #37, PR #40). Дневные записи в стабильный слой из этого отчёта устарели.

Ветка: `team/issue-32-reward-learning`
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/33
Продуктовый код не менялся. Артефакты QA: этот отчёт и `tests/test_qa_issue32_reward_learning.py`.

Вне scope и не запускались как критерии приёмки: #9 (C07 sleep replay), #10 (C08 BG sleep decay), #12 (C10 фиксированные точки нейромодуляторов), колония #19–#21. Сон и аффект проверены только как регрессия соседнего контура (границы привычек и конечность Q).

## Вердикт

FAIL

Контекстный бандит закрывает зонт #32: замороженная политика выше случайного выбора на дополнительных seed, маппингах, `PYTHONHASHSEED` и при шуме награды. Issues #3, #4, #7 и #11 на проверенных сценариях держатся. Issues #5, #6 и #8 закрыты не полностью: ревизия старой оценки затирает общий Q, повтор того же feedback копит Go/NoGo и привычку, `step(reward=...)` не двигает привычку и канал, нефинитная награда обрывает `step()`, а после save/load счётчик эпизодов начинается заново и `ep-1` указывает на другой эпизод.

## Покрытие

- сценарии: 11 пройдено / 7 провалено / 4 не запускалось
- продуктовый `pytest tests` до добавления QA-файла: 764 passed, 5 skipped, 17.73 s (совпадает с заявкой senior-dev; CI PR зелёный на коммите `3cad48d`)
- `pytest tests/test_qa_issue32_reward_learning.py`: 11 passed, 7 failed, 35.58 s

Пройдено:

1. Замороженный бандит, seed 2, 3, 5, 8, 13, 21, 42 × 4 маппинга вне набора PR (в том числе одинаковый лучший ответ в обоих контекстах и действия `left/stay/right`). Порог как в PR: accuracy ≥ 0.60, каждый контекст ≥ 0.50. Оценка `decision_only`, без доучивания в окне измерения.
2. Замороженный бандит при `PYTHONHASHSEED` 2, 3, 4, 11, 99 × 2 маппинга (в PR были только 0, 1, 7).
3. Шум: uniform ±0.35 к ±1 (порог 0.60/0.50); gauss σ=0.5 и 10% переворотов знака (порог «выше случайного»: 0.45 / 0.35).
4. Два прогона с одним `rng_seed` и `random.seed(11)`: 40 шагов совпали посимвольно.
5. Одна и та же трасса при `PYTHONHASHSEED` 0, 1, 7, 12345 (`random.seed` и `rng_seed` зафиксированы).
6. Feedback по id: 0 несовпадений на 120 шагах при capacity 1, 2 и 40. Вытесненный id возвращает `updated=False` и не меняет награду выжившего эпизода.
7. Пустая память, feedback до первого `step`, неизвестная награда (`reward=None` не делает TD), нулевая награда (ровно один TD), строка `"not-a-number"` не считается известным исходом.
8. Повтор того же rating не добавляет второй TD-апдейт. Один терминальный шаг с наградой 0 не создаёт ценность из пустого bootstrap.
9. Единственное действие выбирается и учится. Все посещённые каналы с `go_weight=0`, `nogo_weight=1` и кортизолом 1 дают `NO_ACTION`. Стресс увеличивает NoGo своего канала и оставляет действие с положительным surplus доступным.
10. Непробованное действие получает больший бонус и за 40 выборок попадает в softmax.
11. 25 шагов при `valence=1` и один цикл `deep_sleep`: сила привычек и веса каналов остаются в `[0, 1]`, Q конечен и сохраняет положительный знак.

Провалено: см. дефекты 1–5 (семь тестов, пять дефектов: NaN и inf — одна причина, сброс счётчика и save/load — одна причина).

Не запускалось: #9, #10, #12, колония #19–#21.

## Сверка DoD

| Issue | Итог | На чём стоит вывод |
| --- | --- | --- |
| #3 C01 знак и шкала давления | выполнено | `ActionSelector._signed_recall_means`: среднее знаковой награды, энергия = intensity×activation, итог через `tanh`. Продуктовый тест 20×`reward=-1` против 2×`reward=+1` не ослаблен. Бандит учится. |
| #4 C02 солёный `hash()` | выполнено | В `src/agent.py` нет вызова `hash()`. Холодный старт: sha256 и `self._rng`. Трасса не зависит от `PYTHONHASHSEED`. |
| #5 C03 адресация feedback | частично | Внутри процесса id из `last_episode_id` стабилен, в том числе при capacity 1. После обнуления `_episode_seq` (так делает свежий процесс после load, потому что счётчик не пишется в `AgentStorage`) новый шаг снова получает `ep-1`, и `get_experience("ep-1")` возвращает новый эпизод. |
| #6 C04 один TD и V(s') | частично | Пока rating не меняется, на переход один online-update, повтор того же rating TD не дублирует. Терминальный bootstrap 0. Ревизия старого эпизода перезаписывает общую ячейку Q с исходного prior и стирает последующие апдейты того же `(s, a)`. |
| #7 C05 NO_ACTION и непробованные | выполнено | `step()` больше не подменяет `NO_ACTION`. Gated score 0 не входит в softmax. Бонус по визитам больше у `n=0`, непробованное действие остаётся в выборе. |
| #8 C06 привычки | частично | `IntentMemory.apply_outcome`: EMA к 1 или 0, сила в `[0, 1]`, affect только масштабирует скорость и режется в `[0.25, 1.5]`. Сон эту границу не ломает. `step(reward=1.0)` Q обновляет, привычку и Go/NoGo — нет. Повтор того же feedback двигает их снова. |
| #11 C09 NoGo | выполнено | NoGo = `nogo_weight * (0.05 + 0.12 * stress_drive)`, без общего множителя `\|pressure\|`. Стресс не обнуляет канал с положительным surplus. Полный NoGo по уже посещённым действиям даёт `NO_ACTION`. |
| #32 бандит | выполнено | Замороженная политика выше порога на матрице seed / маппингов / hash seed / шума, которая шире набора PR. |

## Правки старых тестов

Обоснованы и не подменяют проверку более слабым условием:

- `tests/test_selector.py`, `tests/test_affect_integration.py`, `tests/test_affective_persistence.py`, `tests/test_agent.py` ставят `reward=1.0`, потому что давление теперь берётся из знака исхода, а не из интенсивности. Утверждения о выборе прежние.
- `tests/test_basal_ganglia.py::test_threat_effect_inhibition` больше не требует, чтобы высокий NoGo стал популярнее высокого Go. Это и был дефект #11. Новый ассерт: при угрозе high-Go остаётся впереди high-NoGo и выбор не схлопывается в один `NO_ACTION`. Отдельная QA-проверка подтвердила, что NoGo канала растёт вместе с aversive/cortisol.
- `tests/test_intent_memory_integration.py` закрепляет одну награду и наказывает остальные. Доминирует награждённое действие, а не факт повтора. Порог confidence > 0.5 сохранён. Стохастические «≥ 60% выборов» заменены сравнением давления: у ограниченной EMA нет прежнего счётчика-частоты, и новое условие по-прежнему падает, если награждённое действие не на вершине.

Замечание, не дефект этой правки: `test_no_learning_during_waking` по-прежнему проверяет только отсутствие `selector.weights`. На явный `reward` бодрствующий TD уже есть, тест этого не видит.

## Дефекты

### [MAJOR] Ревизия старого rating затирает последующие апдейты того же Q

- **Шаги**: 8 терминальных шагов в одном контексте с одним действием, каждый с feedback `+2`. Запомнить Q. Повторить feedback первого эпизода с rating `-2`.
- **Ожидалось**: правка одного перехода сдвигает Q примерно на один backup. Остальные семь награждённых переходов остаются в ячейке.
- **Факт**: Q падает с `0.2163` до `-0.0277`. `-0.0277` — это один шаг от исходного prior `0`, как будто остальных апдейтов не было. `_apply_feedback_value_update` при смене награды подставляет `td_prior_value` первого коммита и `_set_value` перезаписывает общую табличную ячейку.
- **Где**: `src/agent.py` `_apply_feedback_value_update`; `src/value_layer.py` `update(prior_value=...)`
- **Severity**: major
- **Тест**: `tests/test_qa_issue32_reward_learning.py::test_qa_revising_an_older_rating_must_not_clobber_later_updates`

### [MAJOR] Повтор того же feedback снова двигает Go/NoGo, привычку и sleep-память

- **Шаги**: один `step`, дважды `apply_feedback_to_last_experience(2)` на тот же `episode_id`.
- **Ожидалось**: второй вызов с тем же исходом ничего не меняет. TD так и делает (`online_update_count` остаётся 1).
- **Факт**: до проверки «та же награда» вызываются `_apply_outcome_to_habits`, `_apply_outcome_to_channel` и `record_action_outcome`. Измерено на действии `stop`: habit `0.20 → 0.36`, go `0.58 → 0.66`, nogo `0.46 → 0.42`, записей в `bg_sleep_memories` `1 → 2`. TD при этом не дублируется.
- **Где**: `src/agent.py` `apply_feedback_to_last_experience` (обновление привычки и канала стоит выше раннего выхода по `same_reward`)
- **Severity**: major
- **Тест**: `tests/test_qa_issue32_reward_learning.py::test_qa_repeated_feedback_is_idempotent`

### [MAJOR] Известная награда в step() учит Q и не учит привычку и канал

- **Шаги**: `step(["bin"], reward=1.0, terminal=True)` без `apply_feedback_to_last_experience`.
- **Ожидалось**: известный исход двигает Q, EMA привычки и Go/NoGo этого канала. Чужой канал не меняется.
- **Факт**: TD-апдейт есть, Q выбранного действия `go` стал `0.03`. `go_weight` остался `0.5`. Trace создан через `note_selection` со `strength=0`. `_apply_outcome_to_habits` и `_apply_outcome_to_channel` вызываются только из feedback.
- **Где**: `src/agent.py` `step` (ветка `outcome_known`) и `apply_feedback_to_last_experience`
- **Severity**: major
- **Тест**: `tests/test_qa_issue32_reward_learning.py::test_qa_step_reward_teaches_habits_and_channel`

### [MAJOR] NaN и inf в step(reward=...) обрывают шаг

- **Шаги**: `step(["bin"], reward=float("nan"), terminal=True)` и то же с `+inf` / `-inf`.
- **Ожидалось**: шаг завершается, награда эпизода и Q конечны и лежат в рабочем диапазоне.
- **Факт**: `ValueError: cannot convert float NaN to integer` и `OverflowError: cannot convert float infinity to integer` в `_discretize_drive`. Исключение выходит из `step()`. К этому моменту действие уже выбрано и визит записан, эпизод не сохранён. Feedback-путь безопаснее: нечисловой rating сбрасывается в 0.
- **Где**: `src/hippocampus.py` `_discretize_drive` (строка с `int(round(...))`); `src/agent.py` `step` не отфильтровывает нефинитный `reward` перед `hippocampus.store`
- **Severity**: major
- **Тесты**: `test_qa_nan_reward_does_not_abort_the_step`, `test_qa_inf_reward_does_not_abort_the_step`

### [MAJOR] После save/load id эпизода выдаётся заново и перестаёт указывать на прежний эпизод

- **Шаги**: 4 шага с feedback `+2` (`ep-1`…`ep-4`), `AgentStorage.save_agent` / `load_agent` в новый агент. До следующего шага `get_experience("ep-1")` находит эпизод с наградой `1.0`, Q совпадает. Затем `step(["after-load"])`.
- **Ожидалось**: новый эпизод получает новый id. `get_experience("ep-1")` по-прежнему возвращает первый эпизод с наградой `1.0`.
- **Факт**: `_episode_seq`, `_episodes_by_id` и `last_episode_id` в сохранение не входят. После load счётчик равен 0, следующий эпизод снова `ep-1`. В списке два объекта с id `ep-1`. `get_experience("ep-1")` возвращает новый (награда 0, после feedback `-1`). Тот же эффект без файла: обнулить `_episode_seq` и индекс на живом агенте, сделать шаг — `get_experience(first_id)` уже не тот объект. Сами эпизоды load не стирает: `_ensure_signature_store` восстанавливает подписи, Q value layer читается обратно.
- **Где**: `src/hippocampus.py` `_assign_episode_id`, `_sync_episode_index`; `src/storage.py` `save_agent` / `load_agent`
- **Severity**: major
- **Тесты**: `test_qa_episode_id_survives_a_sequence_reset_like_reload`, `test_qa_save_load_keeps_episode_identity`

### [MINOR] rng_seed не управляет выбором в таламусе

- **Шаги**: два агента с `rng_seed=5`, без повторного `random.seed`. Перед вторым прогоном сдвинуть глобальный `random` на 5 вызовов.
- **Ожидалось**: при зафиксированном seed агента трасса действий одна и та же.
- **Факт**: трассы разошлись уже на первом действии (`red...` и `green...`). Холодный prior берётся из `self._rng`, а `ThalamicGate.select` вызывает `random.choices` модуля `random`. Совпадение есть только если засеять и `rng_seed`, и глобальный `random`.
- **Где**: `src/basal_ganglia.py` `ThalamicGate.select`; `src/agent.py` `_stable_bootstrap_prior`
- **Severity**: minor

### [TRIVIAL] Докстринги описывают старые формулы

- **Шаги**: прочитать докстринг `BasalGangliaGate.process`, модульный докстринг `src/agent.py` и докстринг `Agent.step`.
- **Ожидалось**: текст совпадает с NoGo канала и с бодрствующим TD.
- **Факт**: в `process` по-прежнему написано `NoGo = |pressure| * (gamma * cortisol + delta * aversive)`. В `agent.py` по-прежнему «Learning happens ONLY during sleep» и «NO learning happens here».
- **Где**: `src/basal_ganglia.py` `process`; `src/agent.py`
- **Severity**: trivial

## Вопросы / блокеры

Блокеров прогона нет: стенд поднялся, `pytest` и issues читаются.

Спорное, что не стало отдельным дефектом:

- Бонус визитов режется `cer_bonus_cap_abs=0.05`. На проверенной матрице бандит всё равно выходит из случайного выбора, поэтому потолок не помечен как дефект.
- Продуктовый бандит продолжает вызывать feedback внутри окна оценки. Замороженная оценка QA этот порог тоже проходит, так что послабление измерения в PR дефект не скрыло.
- `record_trace` / `strengthen_trace` по-прежнему могут довести strength до 64. `Agent.step` на бодрствовании идёт через `note_selection` и `apply_outcome`. Прямой вызов остался у `src/gui.py`. К DoD ядра не приписывался.

## Рекомендации

1. Ревизию rating делать поправкой к текущему Q (разность целей), а не записью одного backup от `td_prior_value` первого коммита.
2. При повторном feedback с тем же rating выходить до обновления привычки, канала и `bg_sleep_memories`.
3. В ветке `outcome_known` у `step()` вызывать те же `_apply_outcome_to_habits` и `_apply_outcome_to_channel`, что и feedback.
4. До `hippocampus.store` зажимать награду в конечный диапазон. В `_discretize_drive` не вызывать `int(round(...))` на NaN/inf.
5. Писать в save/load `_episode_seq` (и не выдавать id, который уже есть в списке). Туда же `last_episode_id` и `_action_visit_counts`, иначе после загрузки бонус «непробованного» включается заново.
6. Отдать softmax seed агента, а не глобальный `random`.
7. Не считать PR зелёным по `pytest tests`, пока в дереве лежит `tests/test_qa_issue32_reward_learning.py`: семь тестов красные и фиксируют дефекты выше. Продуктовый набор без этого файла — 764 passed, 5 skipped.

## Готовность к релизу

нет

Бандит и контуры #3, #4, #7, #11 к демонстрации обучения готовы. Вливать как закрытие #5, #6 и #8 рано: ревизия оценки и повтор feedback портят уже выученное, а id эпизода после сохранения перестаёт быть идентичностью.
