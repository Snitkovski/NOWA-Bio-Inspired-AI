# Указатель документации NOWA

English version: [INDEX.en.md](INDEX.en.md)

Научное изложение каждого языка вынесено в отдельный файл. Настоящий указатель содержит только русский текст. Нормативные спецификации сохраняют контрактные идентификаторы на языке исходной редакции; у спецификаций экспериментальных установок двуязычное предисловие указывает предмет и отсылает к научному описанию.

### 1. Научное изложение

1. [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md) — актуальное описание комплекса.
2. [arxiv_NOWA_ru.md](arxiv_NOWA_ru.md) — препринт, русский текст.
3. [arxiv_NOWA_en.md](arxiv_NOWA_en.md) — препринт, английский текст.
4. [../README.md](../README.md) — предмет, состав репозитория, воспроизведение.
5. [START_HERE_NEW.ru.md](START_HERE_NEW.ru.md) — порядок чтения.

Научные описания установок:

1. [Колония](../Demo/Colony%20chinchillas/Docs/COLONY_SPEC.ru.md), [реализованное состояние](../Demo/Colony%20chinchillas/Docs/IMPLEMENTATION_DESCRIPTION.ru.md).
2. [Этологический агент](../Demo/Tamagochi%20Chinchilla/Docs/SCIENTIFIC_DESCRIPTION.ru.md).
3. [Виртуальная организация](../Demo/Virtual%20company/Docs/SCIENTIFIC_DESCRIPTION.ru.md).
4. [Лексическая валидация](../Demo/Warriner%20Validation/Docs/SCIENTIFIC_DESCRIPTION.ru.md).

### 2. Программный интерфейс и проверка ядра

1. [API.md](API.ru.md) — интерфейс ядра.
2. [TESTING.ru.md](TESTING.ru.md) — протоколы регрессионной проверки.
3. [ARCHITECTURE_UPDATED.md](ARCHITECTURE_UPDATED.ru.md) — инвентарь фаз по состоянию марта 2026 г. Актуальная архитектура изложена в научном описании.

### 3. Нормативные спецификации ядра

Контракты фаз — аффективное пространство, нейромодуляторы, базальные ганглии, слой ценности, EDPC, сон и консолидацию, арбитраж, воображение, геном, эпигеном, фабрику агентов, приспособленность, роевую среду и эмерджентную эволюцию — перечислены поимённо в [разделе 5](#5-полный-перечень). Их следует читать как контракт модуля, после научного описания.

Платформенное тело и канон \(A(t)\): [spec_affective_space_platform_body.md](spec_affective_space_platform_body.ru.md).

### 4. Лабораторные журналы

Лабораторные журналы сохраняют историю разработки. Сводки числа тестов в них относятся к дате соответствующей записи. Именной список — в [разделе 5](#5-полный-перечень).

---

## 5. Полный перечень

Каждый документ каталогов Docs/ и Demo/*/Docs/ на русском языке перечислен ниже. Английская пара открывается из шапки соответствующего файла.

### Ядро

- [Документация проекта NOWA-Cognitive](00_INDEX.ru.md)
- [Документация проекта NOWA-Cognitive](00_INDEX_NEW.ru.md)
- [Адаптивный «рот» — краткая справка](ADAPTIVE_MOUTH_QUICK_REFERENCE.ru.md)
- [РЕФАКТОРИНГ "РТА" - ИТОГОВЫЙ ОТЧЕТ](ADAPTIVE_MOUTH_REFACTORING_COMPLETE.ru.md)
- [Аффективное ядро и фаза 4](affective_core_phase4_spec.ru.md)
- [Руководство по реализации AgentFactory (пакет C)](AGENT_FACTORY.ru.md)
- [Аудит автономной физиологии агента](agent_physiology_audit.ru.md)
- [Справочник API — NOWA Cognitive (Phase 5 EDPC + арбитраж решения + обдуманное планирование v2 + HIE-003/HIE-002 + присвоение кредита + Phase 6.2.1 + SAC + автономная среда исполнения + слой внешнего взаимодействия + CER + ACC + Packages A/B/C/D/E/F)](API.ru.md)
- [🏗️ Архитектура NOWA Cognitive](ARCHITECTURE.ru.md)
- [Архитектура системы](ARCHITECTURE_UPDATED.ru.md)
- [NOWA: нейронные сети с обучением по награде и эволюционным ростом архитектуры](arxiv_NOWA_ru.md)
- [Спецификация агента автономного организма](Autonomous_Organism_Agent_Spec_v1.ru.md)
- [NOWA — Изменения и новая функциональность](CHANGELOG.ru.md)
- [Журнал изменений — интеграция Prediction Layer (Plan C)](CHANGELOG_PREDICTION_LAYER.ru.md)
- [КРАТКАЯ СПРАВКА: Изменения в проекте NOWA](CHANGES_SUMMARY.ru.md)
- [Когнитивная архитектура — программа исследований](cognitive_architecture_roadmap.ru.md)
- [Когнитивная система NOWA — аффективные регуляторы и визуализация в графическом интерфейсе](COMPLETE_PROJECT_REPORT.ru.md)
- [Тонкие места и антипаттерны текущей архитектуры](core_fix_and_improvements_v1.ru.md)
- [Ошибка загрузки датасета — исправлена](DATASET_LOADING_FIX.ru.md)
- [Рефакторинг графического интерфейса — сводка поставки](DELIVERY_SUMMARY.ru.md)
- [Руководство разработчика](DEVELOPER_GUIDE.ru.md)
- [Руководство по разработке NOWA Cognitive](DEVELOPMENT.ru.md)
- [Финальный итог — документация по нейромодуляторам](DOCUMENTATION_COMPLETE_FINAL.ru.md)
- [Сводка и организация документации](DOCUMENTATION_SUMMARY.ru.md)
- [Руководство по реализации эмерджентной эволюции (пакет F)](EMERGENT_EVOLUTION.ru.md)
- [Руководство по реализации EpigenomeSnapshot (пакет B)](EPIGENOME_SNAPSHOT.ru.md)
- [Краткое резюме](EXECUTIVE_SUMMARY.ru.md)
- [Ответы на вопросы: интерфейс, цепочки, любопытство и дефекты](FAQ_CHAINS_CURIOSITY.ru.md)
- [📋 Полный Список Изменений и Созданных Файлов](FILES_CHANGES_COMPLETE_LIST.ru.md)
- [Готовый результат: реализация системы бодрствования](FINAL_DELIVERY_WAKEFULNESS.ru.md)
- [ПРОЕКТ ЗАВЕРШЁН! ФИНАЛЬНОЕ РЕЗЮМЕ](FINAL_PROJECT_SUMMARY.ru.md)
- [Финальный отчёт: рефакторинг аффективных регуляторов NOWA](FINAL_REPORT.ru.md)
- [ФИНАЛЬНЫЙ ОТЧЕТ: Реализация Нейромодуляторов Phase 2](FINAL_REPORT_NEUROMODULATORS_PHASE2.ru.md)
- [ФИНАЛЬНЫЙ ОТЧЕТ: Реализация Нейромодуляторов Phase 2](FINAL_REPORT_NEUROMODULATORS_PHASE2v2.ru.md)
- [🎯 Итоговый Результат: Реализация Аффективных Регуляторов и Системы Wakefulness с GUI Визуализацией](FINAL_SUMMARY_RU.ru.md)
- [Руководство по реализации FitnessEvaluator (пакет D)](FITNESS_EVALUATOR.ru.md)
- [Краткое резюме: исправления и инструкции](FIXES_SUMMARY.ru.md)
- [ПОЛНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ПРОЕКТА](FULL_PROJECT_TEST_REPORT.ru.md)
- [Руководство по реализации GenomeVector (пакет A)](GENOME_VECTOR.ru.md)
- [Визуализация аффекта в GUI — отчёт о завершении](GUI_AFFECTIVE_VISUALIZATION_REPORT.ru.md)
- [Рефакторинг графического интерфейса NOWA — завершён](GUI_COMPLETE.ru.md)
- [Привычки в GUI — полная интеграция](GUI_HABITS_IMPLEMENTATION.ru.md)
- [Краткий справочник графического интерфейса — когнитивная архитектура NOWA](GUI_QUICK_REFERENCE.ru.md)
- [Рефакторинг графического интерфейса когнитивной архитектуры NOWA](GUI_REFACTORING.ru.md)
- [Рефакторинг интерфейса NOWA — полная сводка](GUI_REFACTORING_SUMMARY.ru.md)
- [Руководство: автоматическая тренировка селектора](GUIDE_AUTO_TRAINING.ru.md)
- [Заметки о реализации Hippocampus 2.0](HIPPOCAMPUS_2_0_IMPLEMENTATION.ru.md)
- [NOWA — Рефакторинг аффективных регуляторов: ЗАВЕРШЕНО ✅](IMPLEMENTATION_REPORT.ru.md)
- [Отчет о внедрении бодрствования, сна и модуляции префронтальной коры](IMPLEMENTATION_REPORT_WAKEFULNESS.ru.md)
- [Индекс: система нейромодуляторов, фаза 2](INDEX_NEUROMODULATORS.ru.md)
- [Индекс: система нейромодуляторов, фаза 2](INDEX_NEUROMODULATORSv2.ru.md)
- [Руководство по установке и настройке](INSTALLATION.ru.md)
- [NOWA IntentMemory — Реализация слоя памяти намерений](INTENT_MEMORY.ru.md)
- [NOWA IntentMemory — Итоговый отчёт о реализации](INTENT_MEMORY_IMPLEMENTATION.ru.md)
- [NOWA — нейросимволический агент с памятью](LEARNING.ru.md)
- [Слой взаимодействия нейромодуляторов](NEUROMODULATOR_INTERACTION_LAYER.ru.md)
- [Полный список всех документов по нейромодуляторам](NEUROMODULATORS_ALL_DOCS_LIST.ru.md)
- [Полный каталог документации по нейромодуляторам](NEUROMODULATORS_CATALOG.ru.md)
- [Чек-лист — Реализация нейромодуляторов (Февраль 2026)](NEUROMODULATORS_CHECKLIST.ru.md)
- [Реализация завершена — Нейромодуляторы (февраль 2026)](NEUROMODULATORS_COMPLETION_REPORT.ru.md)
- [Руководство по документации — нейромодуляторы (февраль 2026)](NEUROMODULATORS_DOCUMENTATION_GUIDE.ru.md)
- [📋 Полный Отчёт о Реализации Нейромодуляторов](NEUROMODULATORS_FULL_REPORT.ru.md)
- [Главная страница документации по нейромодуляторам](NEUROMODULATORS_HOME.ru.md)
- [🧬 Нейромодуляторы — Реализация и Интеграция](NEUROMODULATORS_IMPLEMENTATION.ru.md)
- [Ссылки на всю документацию](NEUROMODULATORS_LINKS.ru.md)
- [Сводка: реализация нейромодуляторов, фаза 2](NEUROMODULATORS_PHASE2_SUMMARY.ru.md)
- [Сводка: реализация нейромодуляторов, фаза 2](NEUROMODULATORS_PHASE2v2_SUMMARY.ru.md)
- [Нейромодуляторы — Краткая справка](NEUROMODULATORS_QUICK_REFERENCE.ru.md)
- [Суммарный отчёт об изменениях — Нейромодуляторы (Февраль 2026)](NEUROMODULATORS_SUMMARY_REPORT.ru.md)
- [NOWA — План рефакторинга (аффективные регуляторы без проекции)](nowa_affective_refactor_plan.ru.md)
- [NOWA — План внедрения нейромедиаторов](NOWA_Neuromodulators_Plan.ru.md)
- [NOWA — План A: Темпоральная глубина (время как архитектурный фактор)](nowa_plan_a_temporal_depth.ru.md)
- [NOWA — План B](nowa_plan_b_temporal_chains_proto_strategy.ru.md)
- [NOWA — План рефакторинга IntentMemory (память намерений)](nowa_refactoring_plan_intent_memory.ru.md)
- [NOWA — План рефакторинга (финальная версия)](nowa_refactoring_plan_v_2.ru.md)
- [Расширение фазы 2: бодрствование, циркадный процесс C и модуляция префронтальной коры](Phase2_Wakefulness_PFC_Extension.ru.md)
- [Фаза 2 — нейромодуляторы (нейромодуляция, версия 2)](phase_2_neuromodulators_v_2.ru.md)
- [Фаза 3.5 — Аффективная устойчивость](phase_3_5_affective_persistence.ru.md)
- [Фаза 3.75 — Аффективное фоновое поле с модуляцией времени жизни](phase_3_75_affective_background_with_lifetime.ru.md)
- [Phase 3: базальные ганглии / гейтинг действий (BG-AG)](Phase_3_Basal_Ganglia_Action_Gating_refactoring.ru.md)
- [Фаза 3: базальные ганглии / пропускание действий (BG-AG)](phase_3_basal_ganglia_action_gating_specification.ru.md)
- [Фаза 3: система гейтирования действий базальных ганглиев](PHASE_3_GUIDE.ru.md)
- [Phase 4.1 — семантические эмоции](phase_4_1_semantic_emotions_spec.ru.md)
- [Phase 4.2 — эмоциональная память и нарративы](phase_4_2_emotional_memory_narratives.ru.md)
- [Фаза 4.3 — Эмоциональные ожидания](Phase_4_3_Emotional_Expectations_Spec.ru.md)
- [Phase 4.4 — Регуляция на основе эмоциональных ожиданий](Phase_4_4_Regulation_RU_Spec.ru.md)
- [Phase 4.5 — мониторинг устойчивости и контроль дрейфа](Phase_4_5_Stability_Monitoring_RU_Spec.ru.md)
- [Фаза 4 (предварительная): спецификация аффективного пространства](Phase_4_Affective_Space_Spec.ru.md)
- [Фаза 5.0.1 — Слой ценности и ошибка TD (инженерная версия)](Phase_5_0_1_Value_Layer_RU_Spec.ru.md)
- [Phase 5.0 — слой ценности и ошибка TD](Phase_5_0_Value_Layer_RU_Spec.ru.md)
- [Фаза 5.A.1 — Интеграция базальных ганглиев в цикл сна](Phase_5_A_1_BG_Sleep_Replay_RU_Spec.ru.md)
- [Задачи — фаза 5.A.2](Phase_5A2_Online_Sleep_Plasticity_Harmonization.ru.md)
- [Phase 6.1 — спецификация слоя ацетилхолина (ACh)](Phase_6_1_ACh_RU_Spec.ru.md)
- [Фаза 6.2.1 — фильтрованная консолидация (полная спецификация)](Phase_6_2_1_Filtered_Consolidation_FULL_RU_Spec.ru.md)
- [Фаза 6.2 --- Фильтрованная консолидация](Phase_6_2_Filtered_Consolidation_RU_Spec.ru.md)
- [Интеграция плана B завершена — краткое изложение](PLAN_B_DELIVERY.ru.md)
- [Проект NOWA-Cognitive: отчёт о реализации плана B](PLAN_B_FINAL_REPORT.ru.md)
- [Реализация плана B: временные цепи, протостратегия и присвоение кредита](PLAN_B_IMPLEMENTATION.ru.md)
- [План B: реализация темпоральных цепей — краткое начало](PLAN_B_QUICK_START.ru.md)
- [Слой предсказания — контур предсказания (формальная спецификация)](plan_c_prediction_layer_formal_spec.ru.md)
- [Финальное подтверждение завершения проекта](PROJECT_COMPLETION_CONFIRMATION.ru.md)
- [Обновление хода проекта — план B завершён](PROJECT_PROGRESS.ru.md)
- [Итоговая статистика проекта](PROJECT_STATISTICS.ru.md)
- [📊 Финальное Состояние Проекта — Актуализация на 3 марта 2026](PROJECT_STATUS_FINAL.ru.md)
- [Структура проекта NOWA с аффективными регуляторами](PROJECT_STRUCTURE.ru.md)
- [Структура проекта NOWA-Cognitive (организованная)](PROJECT_STRUCTURE_ORGANIZED.ru.md)
- [Краткое руководство](QUICK_START.ru.md)
- [Быстрая справка — нейромодуляторы (февраль 2026)](QUICK_START_NEUROMODULATORS.ru.md)
- [Быстрая Справка: Запуск и Использование (v2.1)](QUICK_START_RU.ru.md)
- [Когнитивная система NOWA — аффективные регуляторы v1.0](README_AFFECTIVE_SYSTEM.ru.md)
- [NOWA — агент нейронной памяти с автоматической тренировкой](README_AUTO_TRAINING.ru.md)
- [NOWA-Cognitive: переработанная архитектура](README_REFACTORED.ru.md)
- [Расширение датасетов реализаций](REALIZATIONS_EXPANSION.ru.md)
- [Рефакторинг NOWA — сводка завершения](REFACTORING_COMPLETE.ru.md)
- [NOWA — План рефакторинга «рта» (адаптивная реализация действий)](refactoring_plan_adaptive_mouth.ru.md)
- [Фаза 3: базальные ганглии — отчёт о рефакторинге](REFACTORING_REPORT.ru.md)
- [Рефакторинг завершён: адаптивный «рот» — итоговое состояние](REFACTORING_STATUS.ru.md)
- [Отчёт о Реорганизации Проекта](REORGANIZATION_COMPLETE.ru.md)
- [Обновление: сохранение и загрузка состояния агента](SAVE_LOAD_AFFECT_STATE.ru.md)
- [Когнитивная архитектура NOWA: научное описание программного комплекса](SCIENTIFIC_DESCRIPTION.ru.md)
- [SPEC-011 — Арбитраж решений, глобальная неопределённость и обобщение состояния](spec_011_decision_arbitration.ru.md)
- [SPEC-011A — Стабилизация присвоения кредита](spec_011a_credit_assignment.ru.md)
- [Спецификация пакета A — GenomeVector](SPEC_A_GenomeVector.ru.md)
- [Спецификация: ACC-модуляция конфликта с защитой от динамической нестабильности](spec_acc_conflict_modulation.ru.md)
- [Спецификация: AffectiveSpace как канон платформы + MCP-тело без MotorAdapter](spec_affective_space_platform_body.ru.md)
- [Спецификация пакета B — EpigenomeSnapshot](SPEC_B_EpigenomeSnapshot.ru.md)
- [Обязательная спецификация интеграции базальных ганглиев (реализовано)](spec_basal_ganglia_integration.ru.md)
- [Спецификация пакета C — AgentFactory](SPEC_C_AgentFactory.ru.md)
- [Циркадный процесс C](spec_circadian_process_c.ru.md)
- [Слой конфликта и арбитража (подобный ACC)](spec_conflict_arbitration_layer.ru.md)
- [Непрерывная эмоциональная регуляция (CER)](spec_continuous_emotional_regulation.ru.md)
- [Спецификация пакета D — FitnessEvaluator](SPEC_D_FitnessEvaluator.ru.md)
- [Делиберативное планирование v2](spec_deliberative_planning_v2.ru.md)
- [Фаза 4 — дофаминергический слой обучения по временной разности](spec_dopaminergic_td_learning.ru.md)
- [Спецификация пакета E v2.1 — SwarmEnvironment](SPEC_E_SwarmEnvironment_v2.1.ru.md)
- [Фаза 5.x — строгая спецификация синхронизации EDPC и SAC](spec_edpc_sac_synchronization.ru.md)
- [Спецификация — External Interaction Layer (реализовано)](spec_external_interaction_layer.ru.md)
- [Спецификация пакета F v2 — Emergent Evolution](SPEC_F_EmergentEvolution_v2.ru.md)
- [Спецификация HIE-002](spec_hie_002.ru.md)
- [Спецификация HIE-003](spec_hie_003.ru.md)
- [Спецификация движка гиппокампального воображения, версия 1](spec_hippocampal_imagine_engine_v1.ru.md)
- [Спецификация гиппокампа 2.0](spec_hippocampus_2.0.ru.md)
- [Слой взаимодействия нейромодуляторов](spec_neuromodulator_interaction_layer.ru.md)
- [Поосевое аффективное затухание](spec_per_axis_affective_decay.ru.md)
- [Phase 5 — Experience-Driven Predictive Consolidation (EDPC)](spec_phase5_edpc.ru.md)
- [Консолидация семантических действий (SAC)](spec_semantic_action_consolidation.ru.md)
- [Замена семантическим сходством](spec_semantic_similarity_replacement.ru.md)
- [Спецификация: активация внутренней симуляции и исправление таксономии драйвов](spec_simulation_drive_taxonomy.ru.md)
- [Медленный тонический дофамин](spec_slow_tonic_dopamine.ru.md)
- [Спецификация разделения фаз SWS и REM, версия 1.0](spec_sws_rem_phase_separation.ru.md)
- [Начните отсюда](START_HERE.ru.md)
- [Порядок чтения](START_HERE_NEW.ru.md)
- [Итоговый отчёт — автоматическая тренировка селектора](SUMMARY.ru.md)
- [Руководство по реализации SwarmEnvironment (пакет E)](SWARM_ENVIRONMENT.ru.md)
- [Интерфейс NOWA — визуализация временных уровней](TEMPORAL_DISPLAY_VISUAL_GUIDE.ru.md)
- [Визуализация временных уровней в интерфейсе — реализация завершена](TEMPORAL_GUI_COMPLETE.ru.md)
- [Визуализация временных уровней в графическом интерфейсе — сводка реализации](TEMPORAL_GUI_IMPLEMENTATION.ru.md)
- [Визуализация времени в GUI NOWA — проект завершён](TEMPORAL_GUI_PROJECT_COMPLETE.ru.md)
- [Визуализация временных уровней в интерфейсе](TEMPORAL_GUI_VISUALIZATION.ru.md)
- [Руководство по проверке — NOWA Cognitive (Hippocampus 2.0 + Phase 5 EDPC + Spec 011/011a + HIE-003/HIE-002 + Phase 6.2.1 + SAC + Autonomous Runtime + External Interaction Layer + CER + ACC + Dopaminergic TD + Packages A/B/C/D/E/F)](TESTING.ru.md)
- [Инструкция: тестирование любопытства в NOWA](TESTING_CURIOSITY.ru.md)
- [Руководство по тестированию](TESTING_GUIDE.ru.md)

### Колония

- [Колония шиншилл: научное описание экспериментальной установки](../Demo/Colony%20chinchillas/Docs/COLONY_SPEC.ru.md)
- [Колония шиншилл: реализованное состояние](../Demo/Colony%20chinchillas/Docs/IMPLEMENTATION_DESCRIPTION.ru.md)
- [Спецификация: Agent Inspector + Death Registry + Lineage Tree](../Demo/Colony%20chinchillas/Docs/SPEC_AgentInspector_DeathRegistry_LineageTree.ru.md)
- [Спецификация: DeathRegistry + AgentInspector + LineageOverlay](../Demo/Colony%20chinchillas/Docs/SPEC_AgentInspector_DeathRegistry_LineageTree_v1.1.ru.md)
- [Спецификация: ChinchillaAgent со стеком NOWA (текущая реализация)](../Demo/Colony%20chinchillas/Docs/SPEC_ChinchillaAgent_NOWA.ru.md)
- [Спецификация: графический интерфейс колонии (текущая реализация)](../Demo/Colony%20chinchillas/Docs/SPEC_ColonyGUI.ru.md)
- [Спецификация ColonyPopulationObserver](../Demo/Colony%20chinchillas/Docs/SPEC_ColonyPopulationObserver.ru.md)
- [Спецификация: мост роя колонии (текущая реализация)](../Demo/Colony%20chinchillas/Docs/SPEC_ColonySwarmBridge.ru.md)
- [Спецификация: Расширенная вкладка «Геном» в AgentInspectorOverlay](../Demo/Colony%20chinchillas/Docs/SPEC_GenomePortrait_InspectorTab.ru.md)
- [Спецификация: интеграция ColonyPopulationObserver в ColonyGUI](../Demo/Colony%20chinchillas/Docs/SPEC_GUI_PopulationStats.ru.md)
- [Спецификация: Расширенная вкладка NOWA в AgentInspectorOverlay](../Demo/Colony%20chinchillas/Docs/SPEC_NowaTab_Extended.ru.md)
- [Спецификация: SwarmAnalyticsOverlay](../Demo/Colony%20chinchillas/Docs/SPEC_SwarmAnalyticsOverlay.ru.md)

### Этологический агент

- [Chinchilla Agent — Техническая спецификация](../Demo/Tamagochi%20Chinchilla/Docs/chinchilla_agent_spec.ru.md)
- [Агент «шиншилла» — спецификация реализации](../Demo/Tamagochi%20Chinchilla/Docs/IMPLEMENTATION_SPEC.ru.md)
- [NOWA-Powered Chinchilla — Спецификация интеграции](../Demo/Tamagochi%20Chinchilla/Docs/NOWA_INTEGRATION_SPEC.ru.md)
- [Фаза 2: обучение и консолидация памяти — реализация завершена](../Demo/Tamagochi%20Chinchilla/Docs/PHASE2_MEMORY_SYSTEM.ru.md)
- [Фаза 3: система планирования — автономные аффективные циклы — реализация завершена](../Demo/Tamagochi%20Chinchilla/Docs/PHASE3_SCHEDULING_SYSTEM.ru.md)
- [Этологический агент: состав и статус документов](../Demo/Tamagochi%20Chinchilla/Docs/PROJECT_COMPLETE_SUMMARY.ru.md)
- [Этологический агент: научное описание установки](../Demo/Tamagochi%20Chinchilla/Docs/SCIENTIFIC_DESCRIPTION.ru.md)

### Виртуальная организация

- [Дополнение: канон AffectiveSpace и тело без MotorAdapter](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_AffectiveSpace_Body_Addendum.ru.md)
- [NOWA Body Layer — As-Built Фаза 1 и контракт MCP-интеграции](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_Phase1_AsBuilt_MCP_API.ru.md)
- [NOWA Body Layer — Патч v1.1](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_Phase1_Patch_v1.1.ru.md)
- [NOWA Body Layer — Патч v1.2](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_Phase1_Patch_v1.2.ru.md)
- [NOWA Body Layer — Фаза 1 Спецификация](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_Phase1_Spec.ru.md)
- [NOWA Body Layer — Конфигуратор роли (RoleConfig)](../Demo/Virtual%20company/Docs/NOWA_Body_Layer_RoleConfig_Spec.ru.md)
- [NOWA Procurement Sandbox — Техническая спецификация](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec.ru.md)
- [NOWA Procurement Sandbox — Патч v1.1.1](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.ru.md)
- [NOWA Procurement Sandbox — Патч v1.1](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec_v1.1_patch.ru.md)
- [NOWA Procurement Sandbox — Патч v1.2](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec_v1.2_patch.ru.md)
- [NOWA Procurement Sandbox — Патч v1.3](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec_v1.3_patch.ru.md)
- [NOWA Procurement Sandbox — Рефакторинг v2.0](../Demo/Virtual%20company/Docs/NOWA_Procurement_Sandbox_Spec_v2.0_refactor.ru.md)
- [NOWA Role Configurator — полный канон чувств и эмоций](../Demo/Virtual%20company/Docs/NOWA_Role_Configurator_Affective_Mapping_Spec.ru.md)
- [NOWA Role Configurator — Хост сотрудников (роли → экземпляр → start/stop)](../Demo/Virtual%20company/Docs/NOWA_Role_Configurator_Agent_Host_Spec.ru.md)
- [NOWA Role Configurator — GUI Спецификация](../Demo/Virtual%20company/Docs/NOWA_Role_Configurator_GUI_Spec.ru.md)
- [NOWA Virtual Employees — Архитектурная спецификация](../Demo/Virtual%20company/Docs/NOWA_Virtual_Employees_Architecture_Spec.ru.md)
- [Виртуальная организация: научное описание установки](../Demo/Virtual%20company/Docs/SCIENTIFIC_DESCRIPTION.ru.md)
- [Песочница закупок NOWA v1.1: двухстадийный учебный план](../Demo/Virtual%20company/Docs/v1.1_two_stage_curriculum.ru.md)

### Лексическая валидация

- [NOWA × Warriner Validation Demo — Техническая спецификация](../Demo/Warriner%20Validation/Docs/NOWA_Warriner_Validation_Spec.ru.md)
- [NOWA × Warriner Validation Demo — Техническая спецификация](../Demo/Warriner%20Validation/Docs/NOWA_Warriner_Validation_Spec_2.1.ru.md)
- [Лексическая валидация: научное описание установки](../Demo/Warriner%20Validation/Docs/SCIENTIFIC_DESCRIPTION.ru.md)
