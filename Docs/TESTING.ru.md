# Руководство по проверке — NOWA Cognitive (Hippocampus 2.0 + Phase 5 EDPC + Spec 011/011a + HIE-003/HIE-002 + Phase 6.2.1 + SAC + Autonomous Runtime + External Interaction Layer + CER + ACC + Dopaminergic TD + Packages A/B/C/D/E/F)

English version: [TESTING.en.md](TESTING.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


Последняя сверка: 27 марта 2026 г.

---

## Текущее состояние

Набор по умолчанию для кодовой базы (без Demo):
```text
723 passed, 3 skipped
```

Использованная команда:
```bash
pytest -q tests
```

Целевой прогон GenomeVector:
```text
17 passed in 0.04s
```

Использованная команда:
```bash
pytest -q tests/test_genome_vector.py
```

Целевой прогон EpigenomeSnapshot:
```text
16 passed in 0.04s
```

Использованная команда:
```bash
pytest -q tests/test_epigenome_snapshot.py
```

Целевой прогон AgentFactory:
```text
19 passed in 0.26s
```

Использованная команда:
```bash
pytest -q tests/test_agent_factory.py
```

Целевой прогон FitnessEvaluator:
```text
21 passed in 0.22s
```

Использованная команда:
```bash
pytest -q tests/test_fitness.py tests/test_fitness_agent_integration.py
```

Целевой прогон SwarmEnvironment:
```text
20 passed, 1 warning in 0.30s
```

Использованная команда:
```bash
pytest -q tests/test_swarm_environment.py
```

Целевой прогон эмерджентной эволюции (пакет F):
```text
20 passed in 0.08s
```

Использованная команда:
```bash
pytest -q tests/test_emergent_evolution_v2.py
```

Целевой прогон бодрствования и циркадного ритма:
```text
44 passed in 1.01s
```

Использованная команда:
```bash
pytest -q tests/test_wakefulness.py tests/test_agent_lifetime_save_load.py
```

Целевой прогон взаимодействия нейромодуляторов:
```text
44 passed in 0.22s
```

Использованная команда:
```bash
pytest -q tests/test_acc_conflict_modulation.py tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
```

Целевой прогон арбитража решений, планирования и назначения кредита:
```text
68 passed in 0.40s
```

Использованная команда:
```bash
pytest -q tests/test_decision_arbitration_spec_011.py tests/test_credit_assignment_spec_011a.py tests/test_deliberative_planning_spec_011.py tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py tests/test_sleep_replay_td_bg.py tests/test_value_layer.py
```

Целевой прогон гиппокампального воображения:
```text
15 passed in 0.20s
```

Использованная команда:
```bash
pytest -q tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py
```

Целевой прогон синхронизации EDPC и SAC:
```text
21 passed
```

Использованная команда:
```bash
pytest -q tests/test_edpc_sac_synchronization.py tests/test_phase_5_edpc.py tests/test_value_layer.py tests/test_value_layer_storage.py
```

Целевой прогон SAC:
```text
16 passed in 0.44s
```

Использованная команда:
```bash
pytest -q tests/test_semantic_action_consolidation.py tests/test_sleep_replay_storage.py
```

Целевой прогон CER/BG:
```text
19 passed in 0.22s
```

Использованная команда:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py tests/test_basal_ganglia_integration_spec.py
```

Целевой прогон ACC:
```text
15 passed in 0.16s
```

Использованная команда:
```bash
pytest -q tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

Целевой прогон CER/BG/ACC:
```text
34 passed in 0.71s
```

Использованная команда:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py tests/test_basal_ganglia_integration_spec.py tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

Целевой прогон внешнего взаимодействия:
```text
15 passed in 0.27s
```

Использованная команда:
```bash
pytest -q tests/test_external_interaction_layer.py
```

Длительный стресс-тест (фильтрованная консолидация фазы 6.2, по включению):
```text
1 passed, 9 deselected in 5.34s
```

Целевой прогон Hippocampus 2.0:
```text
13 passed in 0.11s
```

Использованная команда:
```bash
pytest -q tests/test_hippocampus_2_0.py
```

Совмещённый прогон регрессии гиппокампа и спецификации:
```text
24 passed in 0.28s
```

Использованная команда:
```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

Использованная команда (PowerShell):
```powershell
$env:RUN_LONG_HORIZON_FILTERED_CONSOLIDATION='1'
pytest -q tests/test_phase_6_2_filtered_consolidation.py -k stress_5000 -rs
Remove-Item Env:RUN_LONG_HORIZON_FILTERED_CONSOLIDATION
```

---

## Основные команды

Запуск всех тестов по умолчанию:
```bash
pytest -q tests
```

Запуск тестов GenomeVector:
```bash
pytest -q tests/test_genome_vector.py
```

Запуск тестов EpigenomeSnapshot:
```bash
pytest -q tests/test_epigenome_snapshot.py
```

Запуск тестов AgentFactory:
```bash
pytest -q tests/test_agent_factory.py
```

Запуск тестов FitnessEvaluator:
```bash
pytest -q tests/test_fitness.py tests/test_fitness_agent_integration.py
```

Запуск тестов SwarmEnvironment:
```bash
pytest -q tests/test_swarm_environment.py
```

Запуск тестов эмерджентной эволюции (пакет F):
```bash
pytest -q tests/test_emergent_evolution_v2.py
```

Запуск только тестов фазы 6.1:
```bash
pytest -q tests/test_phase_6_1_ach.py
```

Запуск связки взаимодействия нейромодуляторов:
```bash
pytest -q tests/test_acc_conflict_modulation.py tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
```

Запуск только тестов фазы 6.2:
```bash
pytest -q tests/test_phase_6_2_filtered_consolidation.py
```

Запуск тестов SAC:
```bash
pytest -q tests/test_semantic_action_consolidation.py tests/test_sleep_replay_storage.py
```

Запуск только тестов фазы 5 EDPC:
```bash
pytest -q tests/test_phase_5_edpc.py
```

Запуск регрессионной связки Spec 011/011a:
```bash
pytest -q tests/test_decision_arbitration_spec_011.py tests/test_credit_assignment_spec_011a.py tests/test_deliberative_planning_spec_011.py tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py
```

Запуск регрессионных тестов воспроизведения:
```bash
pytest -q tests/test_sleep_replay_td_bg.py tests/test_phase_6_2_filtered_consolidation.py
```

Запуск целевых тестов дофаминергического TD и слоя ценности:
```bash
pytest -q tests/test_dopaminergic_td_layer.py tests/test_value_layer_integration.py tests/test_value_layer_storage.py
```

Запуск тестов автономного организма и сохранения:
```bash
pytest -q tests/test_autonomous_organism.py tests/test_agent_lifetime_save_load.py
```

Запуск тестов слоя внешнего взаимодействия:
```bash
pytest -q tests/test_external_interaction_layer.py
```

Запуск тестов регрессии гиппокампа и спецификации:
```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

Запуск тестов спецификации интеграции BG:
```bash
pytest -q tests/test_basal_ganglia_integration_spec.py
```

Запуск целевых тестов CER:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py
```

Запуск целевых тестов ACC:
```bash
pytest -q tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

Запуск регрессионной связки селектора, BG и графического интерфейса:
```bash
pytest -q tests/test_basal_ganglia.py tests/test_basal_ganglia_integration_spec.py tests/test_gui_refactoring.py
```

Запуск с кратким трассировочным выводом:
```bash
pytest -q --tb=short
```

---

## Покрытие фазы 5.x: TD и EDPC

Файлы:
- `tests/test_dopaminergic_td_layer.py`
- `tests/test_value_layer_integration.py`
- `tests/test_value_layer_storage.py`
- `tests/test_phase_5_edpc.py`

Покрытые сценарии:
1. Знаковая фазическая TD-динамика (`delta_sign`, burst/dip) при положительном, отрицательном и нулевом сюрпризе.
2. Диагностика сырого и обрезанного TD (`delta`, `delta_modulated`, `delta_clipped`) при насыщении.
3. Эффекты стресса CER: сниженная эффективная альфа и усиленный отрицательный фазический спад.
4. Контракт обработки награды: `reward_raw` сохраняется, необязательный `reward_scale` задаёт эффективную награду TD.
5. Телеметрия насыщения обрезки: `td_was_clipped`, `online_td_clip_count`, `online_td_clip_frequency`, слежение EMA.
6. Адаптивная подстройка онлайн-обрезки TD к целевой частоте обрезки.
7. Знак связи с исследованием и поведение потолка в 20 %.
8. Разморозка исследования от нулевой базовой линии через `exploration_unfreeze_floor`.
9. Ограничитель на уровне агента в режиме inhibit не даёт исследованию схлопнуться (пол `0.05..0.20`).
10. Медленный дрейф тонического дофамина относительно фазических всплесков (`tonic_slow_rate`, `mean_phasic`, `tonic_level`).
11. Долговременный тонический тренд следует текущему фазическому направлению при смене знака.
12. Сохранение и загрузка полей TD, адаптивной обрезки и тонической динамики (`td_tonic_slow_rate`, `td_phasic_mean`, `td_tonic_target_base`).
13. Устойчивый поток: уверенность и стабильность растут, эффективная альфа затухает.
14. Шумный поток: ожидаемое среднее сходится при большей дисперсии и меньшей уверенности, чем у устойчивого потока.
15. Структурный сдвиг: рассогласование при высокой уверенности вызывает шок предсказания и временный рост пластичности.
16. Формула приоритета воспроизведения EDPC использует величину TD, признак шока и стабильность ожидания.
17. Выдача метрик времени выполнения: распределения уверенности и стабильности, частота шока, траектория альфы, разнообразие воспроизведения.

---

## Покрытие Spec 011 / 011a

Файлы:
- `tests/test_decision_arbitration_spec_011.py`
- `tests/test_deliberative_planning_spec_011.py`
- `tests/test_imagination_engine_spec_001.py`
- `tests/test_hie_002.py`
- `tests/test_hie_003.py`
- `tests/test_credit_assignment_spec_011a.py`
- `tests/test_sleep_replay_td_bg.py`

Покрытые сценарии:
1. Переключение режима решения (`HABITUAL`/`DELIBERATIVE`) с гистерезисом неопределённости.
2. EMA неопределённости и температура политики, задаваемая неопределённостью.
3. Связь надёжности политики со стабильностью действия и причинностью воспроизведения.
4. Смещение давления делиберативного планирования до выбора BG.
5. Адаптация глубины развёртки по неопределённости.
6. Кандидаты эпизодического планирования, отфильтрованные по сходству.
7. Оценка развёртки как максимум дисконтированной отдачи траектории.
8. Исследовательская надбавка ценности информации (`gain * (1 - confidence)`).
9. Предохранители делиберативного планирования (`support >= 0.05`, `confidence >= planning_min_confidence`).
10. Предохранители сложности делиберативного планирования (`actions <= 32`, `samples <= 8`, `depth <= 6`).
11. Пропуск при отключённом планировании и пустой памяти.
12. Путь совместимости HIE-001 сохранён через `Agent._generate_imagined_rollouts(...)`.
13. Структурированное воображение HIE-002 встроено (`generate_structured_imagination`) с временной сшивкой.
14. Древовидное воображение многих действий HIE-003 встроено (`generate_action_tree_imagination`) с агрегацией ценности корневого действия.
15. Предохранители сложности HIE-003: `action_branching<=4`, `max_tree_nodes<=128`, `depth<=5`.
16. Предохранители сложности запасного пути HIE-002: `samples<=8`, `depth<=5`, `branching<=4`, `nodes<=96`, `edges<=192`.
17. Инвариант уверенности HIE: уверенность траектории ограничена отрезком `[0, 1]`.
18. Проверена смесь состава развёртки (интерполяция `memory/imagined` через `imagination_value_blend`).
19. При отключённом HIE планирование остаётся на прежнем пути только по памяти.
20. Назначение причинной глубины с якорем на награде (явная награда / шок TD / запасная середина).
21. Использование окна кредита и диагностика следа годности в статистике воспроизведения.

---

## Покрытие фазы 6.1

Файл: `tests/test_phase_6_1_ach.py`

Покрытые сценарии:
1. Всплеск новизны повышает ACh, онлайн-альфу и приоритет воспроизведения.
2. Устойчивое повторение снижает ACh.
3. Фильтр новизны сглаживает шумные всплески ACh.
4. Безопасность насыщения: ограничение ACh и мягкий потолок онлайн-альфы.
5. ACh спадает к базовой линии без новизны.
6. ACh не меняет ошибку TD непосредственно.
7. Нет систематического смещения альфы, когда ACh равен базовой линии.
8. Альфа сна не масштабируется ACh.
9. Прирост ACh при воспроизведении ослабляется, когда дисперсия ценности высока.
10. Сила кодирования и статистика сна выставляют метрики ACh.
11. Проверки устойчивости на длинном горизонте (2000 и 5000 шагов, по включению).

---

## Покрытие фазы 6.2 / 6.2.1 и SAC

Файл: `tests/test_phase_6_2_filtered_consolidation.py`
Дополнительные файлы:
- `tests/test_semantic_action_consolidation.py`
- `tests/test_sleep_replay_storage.py`

Покрытые сценарии:
1. Шумовой эпизод отвергается.
2. Повторенный значимый эпизод консолидируется.
3. Высокая дисперсия ценности блокирует воспроизведение во сне.
4. Переполнение бюджета сна останавливает обновления.
5. Высокий ACh при низком TD отвергается.
6. История TD верно обновляет среднее и дисперсию в бодрствовании и при обратной связи.
7. `td_variance_cap` отвергает эпизоды с высокой дисперсией.
8. `value_variance` замораживается на цикл сна ради детерминированного поведения.
9. Воспроизведение во сне не меняет статистику истории TD (вариант A).
10. Стресс-тест на 5000 циклов: дисперсия не растёт (по включению).
11. Подтверждённое действие SAC обновляет семантические среднее, дисперсию и риск.
12. Аномальные шоковые эпизоды SAC игнорируются.
13. SAC блокирует обновления при малом числе воспроизведений и низкой стабильности.
14. SAC удерживает защиту от подтверждения смещения (`epsilon_divergence`).
15. SAC удерживает жёсткое ограничение `sac_alpha_slow <= 0.01`.
16. SAC применяет пол дисперсии (`sac_sigma_floor`), чтобы не допустить кристаллизации.
17. Параметры SAC и `selector_action_metadata` сохраняются при save/load.
18. Фаза SWS, как ожидается, сужает сигму и не снижает стабильность.
19. Фаза REM, как ожидается, расширяет сигму и не повышает стабильность.
20. Фаза TRANSITIONAL оставляет стабильность неизменной.
21. SAC удерживает инварианты порогов фаз (`theta_arousal_low < theta_arousal_high`, `theta_shock_low < theta_shock_high`).
22. SAC удерживает жёсткие ограничения `sac_alpha_base <= 0.01` и `sac_lambda_sws > sac_lambda_rem`.
23. Глобальная фаза SAC отражает строки, которые действительно можно обновить (после фильтра), а не сырые потенциальные строки.
24. Структурное предупреждение поддерживает сброс спокойного цикла; пол стабильности REM не даёт коллапса; потолок шага семантической уверенности ограничивает рост за цикл.

---

## Покрытие автономного времени выполнения (спецификация v1 и аудит физиологии)

Файлы:
- `tests/test_autonomous_organism.py`
- `tests/test_agent_lifetime_save_load.py`

Покрытые сценарии:
1. Рост любопытства в простое и ограниченность на длинном горизонте.
2. Подавление энергией внутренних циклов при низкой энергии.
3. Охлаждение речи и разрядка речевого драйва.
4. Конкуренция драйвов с взвешенными порогами.
5. Эмоциональная перегрузка повышает драйв разрядки.
6. Потолок доли импульса припоминания (`<= 40%`).
7. Физиологический режим простоя снижает усталость при низкой когнитивной нагрузке.
8. Ограничение и запись аномалии `dt`.
9. Сбои внутреннего применения аффекта записываются в журнал.
10. Круговой save/load сохраняет автономное состояние и состояние бодрствования.

Замечания о следах графического интерфейса:
1. Следы автономной речи выдаются с метками `[AUTO] ...`.
2. Следы внутренней мысли выдаются как `[AUTO] think: ...`, когда запускается внутренний цикл.
3. Повторные строки мысли подавляются в коротких окнах (защита от спама).

---

## Покрытие слоя внешнего взаимодействия

Файл:
- `tests/test_external_interaction_layer.py`

Покрытые сценарии:
1. Приём и интерпретация наблюдения с обработкой неопределённости.
2. Исполнение действия через адаптер среды и приведение обратной связи.
3. Конвейер очереди и разрешения отложенной обратной связи.
4. Устойчивость обновления драйвов: спад, насыщение, конкуренция.
5. Устойчивость обновления стратегии: логиты, спад, softmax, температура.
6. Связь драйва со стратегией при нейтральной награде.
7. Перекалибровка гипотезы с явным `P(E|not H)`.
8. Модуляция давления селектора выученным `strategy_weight`.
9. Интеграция на уровне агента: execute/resolve/poll и параллельная симуляция.

---
## Покрытие регрессии конвейера BG

Файлы:
- `tests/test_basal_ganglia.py`
- `tests/test_basal_ganglia_integration_spec.py`

Покрытые сценарии:
1. Высокий дофамин усиливает путь Go.
2. Высокий кортизол подавляет действие через усиление NoGo.
3. Сила привычки может преобладать при слабом кортикальном давлении.
4. Нулевое давление в аверсивных условиях может дать `NO_ACTION`.
5. Путь предложения внутренней симуляции совпадает с реальным конвейером решения BG и таламуса.

---

## Покрытие CER

Файлы:
- `tests/test_emotional_regulation.py`
- `tests/test_emotional_regulation_integration.py`

Покрытые сценарии:
1. Динамика устойчивой положительной награды.
2. Хронический неуспех и включение режима восстановления.
3. Предохранитель насыщения при длительном высоком возбуждении.
4. Осторожность, задаваемая энтропией (рост `decision_threshold_shift`).
5. Успех разрешения снижает неопределённость.
6. Устойчивость колебаний и потолки скачка на шаг.
7. Нелинейный насыщающийся ответ валентности.
8. Хроническая отрицательная валентность стрессового вида повышает `habit_gain_scale`.
9. Нейромодуляторное указание CER остаётся ограниченным (по модулю не более `0.006`).

---

## Покрытие ACC

Файлы:
- `tests/test_conflict_arbitration_layer.py`
- `tests/test_conflict_arbitration_integration.py`
- `tests/test_conflict_arbitration_storage.py`

Покрытые сценарии:
1. Низкий конфликт даёт режим `habitual` и снижение порога.
2. Высокий конфликт и высокая новизна дают режим `deliberative` с усилением рабочей памяти.
3. Повторные неуспехи дают режим `inhibit` с запросом дополнительной оценки.
4. Высокое возбуждение при низком конфликте не вынуждает режим `deliberative`.
5. Гистерезис и рефрактерность не дают быстрого колебания режима.
6. Исчерпание стоимости контроля вынуждает снижение из режимов высокого контроля.
7. Метрика конфликта остаётся отделённой от валентности и возбуждения CER.
8. `control_demand` включает латентность решения.
9. Повышение скорости обучения агента зависит от `error_likelihood`, а не от одного лишь режима контроля.
10. Путь `inhibit` действует через модуляцию порога, а не через прямое подавление вектора давления.
11. Совместный сдвиг порога CER и ACC ограничен, чтобы не допустить чрезмерного подавления.
12. Круговое сохранение состояния ACC через `AgentStorage`.

---

## Длинный горизонт и тесты по включению

Тесты, пропускаемые по умолчанию:
1. `RUN_LONG_HORIZON_ACH=1` включает 2 длинных теста ACh (`tests/test_phase_6_1_ach.py`).
2. `RUN_LONG_HORIZON_FILTERED_CONSOLIDATION=1` включает стресс-тест на 5000 циклов (`tests/test_phase_6_2_filtered_consolidation.py`).

---

## Замечания

1. Проверки длинного горизонта намеренно выключены в прогонах по умолчанию ради скорости непрерывной интеграции.
2. Для проверки выпуска следует выполнить набор по умолчанию и обе группы по включению.
3. Сообщаемые числа прохождений следует держать согласованными с выводом `pytest -q -rs` после слияния каждой крупной фазы.
