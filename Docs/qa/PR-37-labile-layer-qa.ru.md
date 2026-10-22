# QA PR #37 — лабильный слой бодрствования (PR A по #13)

Ветка: `team/core-labile-layer` (база `c2f8b1a`).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/37
Спека: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/issues/13#issuecomment-6261798711
Объём прохода: лабильный слой, guard обучения, время хоста (`dt` / `advance_time`). Capture во сне, κ, приоритеты replay, ровно-один-раз и EMA привычек во сне — это PR B, их отсутствие не провал этого PR. Код ядра не менялся.

## Вердикт

**PASS with notes**

Дневной контракт держится на вызовах, которыми пользуется хост: `step`, `commit_executed_transition`, feedback и поставленный в очередь внешний feedback не меняют отпечаток стабильного слоя; выбор сдвигается через лабильный слой в пределах clamp; затухание, нарезка `dt`, замена оценки, save/load и уже существующие писатели сна (replay Q и кэш исходов BG) ведут себя так, как задано для PR A. Замечания ниже — дыры guard, которые автор уже перечислил, медленная аффективная статистика, оставленная на PR B, и один ассерт, который стал тождественно истинным.

## Pytest

| Набор | Результат | Время |
| --- | --- | --- |
| `pytest tests -q` | **869 passed, 5 skipped** | 217 с |
| `pytest Demo -q` | **999 passed, 6 skipped** | 108 с |

Пять skip ядра и шесть skip демо — прежние. 869 = заявленные автором 860 плюс 9 проверок в `tests/test_qa_pr37_labile_layer.py`. Headless-демо не запускался. Перебора seed шире, чем seed внутри этих проверок (1–8, по одному сценарию), нет.

## Чеклист

1. **Отпечаток.** Двенадцать дневных циклов (commit с наградой, override, оценка и затем смена оценки, внешний feedback в очереди) не меняют `stable_fingerprint`. Стабильные счётчики визитов пустые, стабильный Go остаётся 0.5, `online_update_count` равен 0, сила привычки равна 0. `|L_Q| ≤ 0.2`, `|L_channel| ≤ 0.1`.
2. **Выбор без сна.** Seed 1, 40 вознаграждённых commit действия `red`, без сна: P(`red`) растёт. Один вклад с `td_error=100` / `reward=100` зажат в `|ΔQ| ≤ 0.05` и `|Δchannel| ≤ 0.1`, накопленные смещения остаются в 0.2 / 0.1.
3. **Затухание и время.** Через `5·τ_L` остаток `|L_Q| < 1%` от только что записанного. `advance_time(8)` и четыре `advance_time(2)` совпадают до `1e-12` по Q, смещениям канала и меткам времени. `τ_L` следует за `expected_wake_interval_s`. Если интервал не задан, `resolved_tau_s()` равен 3600, и при создании пишется одно предупреждение о fallback.
4. **Feedback.** Три одинаковые оценки совпадают с одним применением (одна строка в журнале сна BG). Повтор той же оценки возвращает `updated=True` и не двигает метки. Оценка `+2`, затем 50 с, затем `-2` совпадает с одним `-2`, применённым в этот более поздний момент (Q и каналы, `1e-12`). Неизвестный `episode_id` даёт `updated=False` и не двигает ни метки, ни отпечаток.
5. **Save/load.** Сохранение возвращает лабильный слой, часы хоста и `PlasticityConfig`. После загрузки ещё 30 с `advance_time` затухают синхронно с исходным агентом. Pickle, из которого убраны `labile_layer`, `plasticity_config` и `host_clock_s`, грузится с пустым слоем и часами 0 и затирает лабильное состояние, которое уже было у цели.
6. **Сон.** Двенадцать терминальных наград `+1` на `go`, затем `sleep(cycles=3)`: стабильная Q `0 → 0.225`, стабильный Go `0.5 → 0.967`. Сила привычки не растёт (PR B). Пустой дневной след силы 0 снимается существующим `degrade_unused`.
7. **Guard.** При `NOWA_STRICT_LEARNING=1` вызов `ValueLayer.update` бросает `WakingLearningError`, отпечаток не меняется. Без переменной или при `0` тот же вызов возвращает `skipped=True`, отпечаток не меняется, предупреждение одно на два вызова. `step(reward=NaN)` лабильную метку не пишет. `step(reward=±inf)` сохраняет `±1` и метку пишет.

Явный `dt` в `step` / `commit` не читает `time.time()` для часов хоста (это уже проверяет `tests/test_issue13_two_tier.py`).

## Дефекты

### Medium — прежний ассерт больше не проверяет сон

`tests/test_qa_issue32_reward_learning.py`, `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep`. Строка не редактировалась:

```python
assert _q(agent, ["ctx"], "go") > 0.0 or q_before <= 0.0
```

`q_before` — стабильная Q после дневного feedback и до `deep_sleep`. Днём стабильная Q теперь 0, поэтому `q_before <= 0` истинно, и проверка после сна проходит, даже если сон оставил Q нулевой или записал отрицательную. Комментарий по-прежнему говорит, что сон не должен уничтожить знак выученного значения. Другие тесты по-прежнему требуют роста стабильной Q (`test_td_transition`, блок преемника в этом файле и QA-проверка сна: 0.225). Это дыра покрытия, а не сломанный писатель.

Воспроизведение: 25 дневных `step` + feedback на `["ctx"]`, прочитать стабильную Q (0), вызвать `sleep_manager.deep_sleep(cycles=1)`. На знаке Q ассерт упасть не может.

### Medium — стабильные писатели вне guard (подтверждено, одно добавление)

Совпадает с вопросами автора, проверено прямым вызовом. На пути `step` / `commit` / feedback этого нет. Закрывать в отдельном ужесточении; этот PR их не закрывает.

| Точка | Что делает дневной вызов | Серьёзность |
| --- | --- | --- |
| `ValueLayer._set_value` | Пишет `values` без проверки. Отпечаток меняется. Им пользуются replay и загрузка. | Medium |
| `channel.go_weight = ...` (и nogo / habit) | Прямая запись. Так пишут `SleepManager._relax_channel_weight`, `_normalize_bg_weights` и `_copy_bg_weights`. Безопасно только потому, что `sleep_cycle` уже держит guard. | Medium |
| `BasalGangliaLearning.apply_sleep_learning` | Сам входит в `learning_allowed()`. Дневной вызов обучает возвращённый клон (`go` 0.5 → 0.54 на одной положительной памяти при DA 0.8). Живой канал остаётся 0.5, пока вызывающий не скопирует клон. Сон тамагочи так и копирует — ради этого guard и открывается внутри. Дневной вызывающий, который копирует результат, тоже запишет стабильный Go. | Medium |
| `BasalGangliaLearning.consolidate_habits` | В списке автора не было. Пишет `habit_strength` на клоне без guard (`selection_count=5` → сила ≈ 0.068). Установка этого клона меняет отпечаток. | Medium |
| `Agent.register_action_channel` | Пишет Go / NoGo / привычку без области `initializing()`. `register_action_channel("new", go_weight=0.8, habit_strength=0.3)` меняет отпечаток. Решение 4 разрешает посев хоста внутри `initializing()`; этот метод в область не входит, чтобы текущая настройка не сломалась. | Low |

### Medium — медленная аффективная статистика всё ещё меняется днём (PR B)

Решение 3 относит её к стабильному слою и только ко сну. Разбиение PR оставляет её на PR B, и `stable_fingerprint` прямо исключает её из хеша. При `step` она меняется, так что инвариант W для пункта 7 категории A ещё не выполнен, и хеш этого не поймает.

После 6 дневных шагов (`reward ±1`, novelty 0.8, conflict 0.6) отпечаток не изменился, а сдвинулось следующее:

- `affective_background`: тревога / напряжение / удовлетворённость / интерес с 0 до примерно 0.30–0.38
- `semantic_emotions.active_emotions`: появились fear и love
- `emotional_memory`: черты, эпизоды, паттерны, фрагменты нарратива
- `emotional_expectations`: `dominant_forecast` с пустого на `love`, outlook с `stabilizing` на `volatile`
- `conflict_arbitration`: `recent_failure_rate` 0 → 0.5, история ошибок заполнена, `control_cost` > 0
- `emotional_regulation`: `learning_rate_scale` 1.0 → 1.36, сдвинулись arousal и valence

`learning_rate_scale` больше не умножает дневной стабильный alpha: этого писателя нет. Лабильный шаг его не читает.

### Low — NaN / ±inf в feedback

`step` / `commit` считают NaN неизвестным исходом (лабильной метки нет), а ±inf — это ±1. `apply_feedback_to_last_experience` идёт через `int(...)`. NaN и ±inf дают исключение, обработчик ставит оценку 0, эпизод коммитится с наградой 0 (`updated=True`). Оценка 99 зажимается в `+1` — это и есть целочисленная шкала. Спека 4.1.4 ставит правило NaN/inf рядом с feedback. Демо передают целочисленную оценку; это щель парсера, а не сломанная идемпотентность для `-2..2`.

### Low — ветка `mode="online"` всё ещё реализована

`ValueLayer.update` по-прежнему содержит online-ветку, за guard. Агент днём её не вызывает. Автор оставил её, чтобы тесты профилей ожидания не потеряли реализацию. Пункт полной спеки «убрать `mode=online`» не сделан. Для PR A это принято, как написано в описании PR.

### Low — поля `outcome_revision` нет

У эпизода есть `labile_contribution`, `encoded_at`, `td_outcome_committed`. Атрибута `outcome_revision` нет. Ровно-один-раз и ревизии после консолидации — PR B. No-op той же оценки для `-2..2` в этом счётчике не нуждается.

### Low — опциональный тест ACh всё ещё ждёт дневной alpha

`test_long_horizon_ach_stability_metrics_normal_mode` пропускается, пока не задан `RUN_LONG_HORIZON_ACH=1`. Он по-прежнему требует `fraction_alpha_above_default > 0.05`. Дневные шаги больше не выставляют `last_alpha_effective`. В обычные 869 он не входит.

## Аудит тестов

Правило: **equivalent** — то же утверждение в двухуровневой модели, тот же порог. **justified-by-spec** — старое утверждение про дневную запись в стабильный слой снято, потому что PR A это запрещает, а замена соответствует спеке (или это явно PR B). **weakened-coverage** — числовой порог снижен, и новый ассерт проходит на более слабом эффекте. **hides-regression** — ассерт проходит, когда названного им поведения нет.

| Тест | Изменение | Вердикт |
| --- | --- | --- |
| `test_td_transition.py` | Одна лабильная запись на оценку; днём стабильная Q равна 0. `Q > 0.8` стало эффективной Q в `(0.15, 0.2]` плюс стабильная `Q > 0.2` после `sleep(cycles=3)`. Преемник `Q > 0.4` стал эффективным `> 0.01` против холодного агента, стабильная Q остаётся 0. | weakened-coverage |
| `test_reward_bandit.py` | `sleep(cycles=3)` каждые 20 проб. `_MIN_ACCURACY` по-прежнему 0.60. | equivalent |
| `test_qa_issue32_reward_learning.py` (бандит, идемпотентный backup, ревизия, канал) | Бандит спит каждые 20 проб; порог 0.60 сохранён. Дневные проверки Q/Go, которые умещаются в clamp, читают эффективные значения. Стабильный Go остаётся 0.5; сила привычки после дневной награды равна 0 (было `> 0`). Тридцать наград: эффективная `> 0.05` (было стабильная `> 0.5`), затем стабильная `> 0.2` после сна. Цикл ревизии вырос с 8 до 70 шагов; пороги 0.15 и 0.05 сохранены на эффективной Q. | weakened-coverage |
| `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` (тот же файл, строка не менялась) | `Q_after > 0 or q_before <= 0` истинно всегда, когда дневная стабильная Q равна 0. | hides-regression |
| `test_intent_memory_integration.py` | Дневные награды оставляют силу 0. `confidence > 0.5` даёт `apply_outcome` внутри `learning_allowed()`, а не `Agent.sleep`. | justified-by-spec |
| `test_qa_pr35_sleep_learning.py` | Дисперсию ожидания пишет `ValueLayer.update` под guard после дневной последовательности. Пороги гейта не менялись. | equivalent |
| `test_qa_pr36_colony_core.py` | Тест кредита читает эффективный Go (`> 0.5`) и проверяет, что стабильный Go остаётся 0.5. EMA ключа привычки идёт под guard; порог силы `> 0.9` сохранён. | equivalent |
| `test_conflict_arbitration_integration.py` | ACC больше не масштабирует дневной alpha (`base*1.4`, high > low). Замена: `update` не вызван, снимки TD конечны. Отсутствующий снимок читается как 0.0 и всё равно проходит `isfinite`. | weakened-coverage |
| `test_emotional_regulation_integration.py` | Масштаб CER `base*1.7` снят. Замена: писатель не вызван и `td_error_snapshot != 0`. | weakened-coverage |
| `test_phase_6_1_ach.py` | Дневная проверка `last_alpha_effective > alpha_online_default` снята. Рост ACh и приоритет replay при высоком ACh остаются. Общий для модуля guard не прячет вернувшийся вызов `update`: тест по-прежнему требует `online_update_count == 0`. | justified-by-spec |
| `test_value_layer_integration.py` | Только autouse `learning_allowed()`. Пороги не менялись. | equivalent |
| `test_external_interaction_layer.py` | Прямой `apply_learning_hooks` внутри guard; неравенства весов те же. Путь агента применяет хуки в `sleep()` и затем проверяет то же неравенство. | equivalent |
| `test_k03_habit_signature.py`, `test_intent_memory.py`, `test_basal_ganglia.py`, `test_value_layer.py`, `test_value_layer_storage.py`, `test_phase_5_edpc.py`, `test_dopaminergic_td_layer.py`, `test_edpc_sac_synchronization.py`, `test_affect_integration.py`, `test_habits_loading.py` | Прямые вызовы стабильных писателей идут внутри `learning_allowed()` (autouse модуля и/или локальный `with`). Числовые ассерты не менялись. | equivalent |

Снижение 0.8 → 0.2 и 0.5 → 0.05 не прячет мёртвый писатель: стабильная Q всё ещё должна перейти 0.2 за один нынешний бюджет сна, а один лабильный шаг `η_L ≈ 0.003` не переходит 0.05. Они перестают требовать, чтобы Q подошла к награде. Проверка преемника на 0.01 — самая слабая из этих.

Общий для модуля `learning_allowed()` значит, что эти файлы не заметят дневной вызов того писателя, который они тестируют, кроме мест, где они ещё проверяют `online_update_count == 0` или замороженный отпечаток. Инвариант W закрывают `test_issue13_two_tier.py` и `test_qa_pr37_labile_layer.py`, а не эти модульные файлы.

## Демо (не чинились)

Для следующих PR по каждому демо. `pytest Demo` зелёный, потому что fallback ещё работает, а Demo не ставит `NOWA_STRICT_LEARNING`.

### Colony chinchillas

`ChinchillaAgent.sim_step(dt)` передаёт `dt` в физиологию и **не** передаёт его в `Agent.step(..., decision_only=True)` и `commit_executed_transition(reward=...)`. Каждый шаг решения попадает в fallback настенных часов (первый шаг берёт синтетическую 1 с, если прошлой метки нет). Награда становится лабильной меткой и строкой `bg_sleep_memories`. Стабильные Q, Go и сила привычки не двигаются, пока колония сама не вызовет `sleep()`.

Тесты, которые идут по этому пути (им понадобится `dt=` в вызовах ядра, а явный сон — только если сценарий держался на дневных стабильных весах):

- `Demo/Colony chinchillas/tests/test_nowa_agent.py` (`sim_step`, включая тест, что вызван базовый `step`)
- `test_knowledge.py`, `test_reproduction.py`, `test_resources.py`, `test_social.py`, `test_storage.py` (`run_for` / `sim_step`)
- `tests/test_k01_colony_ablation.py`, `tests/test_k01_need_consumption.py`, `tests/test_k02_decide_act_learn.py`, `tests/test_qa_pr36_colony_core.py`

Тесты колонии, которые только создают агента (родословная, портрет генома, большая часть GUI-юнитов), по этому пути не ходят.

### Tamagotchi Chinchilla

Это не `Agent.step`. По завершении цепи `Demo/Tamagochi Chinchilla/src/main.py` вызывает `value_layer.update(..., mode="online")`. В продовом guard запись пропускается с одним предупреждением; при `NOWA_STRICT_LEARNING=1` будет исключение. Тесты демо переменную не ставят, остаются зелёными и Q не проверяют.

Сон в этом файле зовёт `BasalGangliaLearning.apply_sleep_learning` (guard открывается сам, обучение происходит) и `consolidate_habits` (прямая запись `habit_strength`, без guard).

Тесты, которые гоняют `sim_step` / демо-`step` и при адаптации демо упрутся в решение по strict-режиму:

- `Demo/Tamagochi Chinchilla/tests/test_nowa_integration.py`
- `Demo/Tamagochi Chinchilla/tests/test_integration.py`
- `Demo/Tamagochi Chinchilla/tests/test_core.py`, `test_comprehensive.py` (создают агента и тикают; стабильную Q не проверяют)
- `tests/test_chinchilla_integration.py`

Fallback `dt` у `Agent.step` к этому демо не относится.

### Virtual company

`TrainingLoop._agent_step` вызывает `agent.step(context, decision_only=True)` без `dt`, поэтому каждый день попадает в fallback настенных часов. Комментарий цикла и так не хочет дневного обновления value внутри `step`; с PR A это совпадает. Feedback, который потом зовёт `apply_feedback_to_last_experience`, пишет лабильный слой, а не стабильную Q.

Тесты на настоящем агенте ядра, без `dt`:

- `Demo/Virtual company/tests/test_agent_pipeline.py` (прогоны квартала, `decision_only` и тест, что шаг без decision_only сохраняет эпизод)
- `Demo/Virtual company/tests/test_agent_independence.py` (`agent.step(context)`)
- `test_sandbox_integration.py`, `test_run_sandbox.py`, `test_sandbox_checkpoint.py` (живые сессии `create_procurement_agent`)

`test_training_loop.py` подставляет фальшивый `step`. `test_agent_pipeline.py` проверяет, что на пути decision-only `value_layer.update` не вызывается; это согласовано с PR A и от дневного стабильного обучения не зависит.

### Warriner Validation

`nowa_colony._run_agent_step` вызывает `agent.step(..., reward=memory_reward)` без `dt` (fallback настенных часов и дневная лабильная метка). `Demo/Warriner Validation/tests/test_nowa_colony.py` и `test_hippocampus_seeder.py` используют `FakeAgent`. Ни один текущий тест Warriner не гоняет настоящий агент ядра. В следующем PR демо нужно прокинуть `dt` именно в этом runtime-пути.

## Вопросы владельцу

1. Медленная аффективная статистика и статистика ожиданий (решение 3): подтвердите, что до PR B она остаётся записываемой и вне отпечатка. Что именно сдвинулось — в списке выше.
2. Подтвердите, что незащищённые примитивы (`_set_value`, прямая запись Go/NoGo/habit, `consolidate_habits`) и самооткрывающийся `apply_sleep_learning` в этом PR остаются как есть.
3. `register_action_channel` не входит в `initializing()`. Оставляем так, чтобы текущая настройка работала?
4. `g_DA` зафиксирован в 1.0 внутри `_record_known_outcome`. Отдельного поля фазического gain нет. Подтвердите.
5. Лабильный счётчик визитов не затухает; стабильный днём не растёт. Подтвердите.
6. EMA привычек в этом сне нет. След силы 0, созданный днём, может исчезнуть в `degrade_unused`. До PR B так и оставляем?
7. Должен ли `apply_feedback_to_last_experience(NaN | ±inf)` следовать правилу step/commit (неизвестно / ±1), или контракт — только целочисленная шкала оценок?
8. Тождественный ассерт `q_before <= 0`: поправить следующим коммитом на этой ветке или оставить до переписи тестов в PR B?
9. Обход документации остаётся PR C. Docstring затронутых путей агента и сна обновлены; `Docs/` нет.
