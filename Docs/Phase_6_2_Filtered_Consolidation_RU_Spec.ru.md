# Фаза 6.2 --- Фильтрованная консолидация

English version: [Phase_6_2_Filtered_Consolidation_RU_Spec.en.md](Phase_6_2_Filtered_Consolidation_RU_Spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Назначение

Механизм селективной консолидации эпизодической памяти в долговременные
представления.

## Архитектурные границы

-   Не изменяет reward
-   Не изменяет TD error
-   Не влияет на online alpha
-   Работает только в sleep

## Критерии допуска

Эпизод допускается если: - \|TD_mean\| ≥ td_threshold - salience ≥
salience_threshold - reinforcement_count ≥ min_reinforcement -
value_variance_ratio \< variance_gate_threshold - ACh_effective ≥
ach_min_for_consolidation

## Ограничения

-   sleep_alpha ≤ sleep_alpha_cap
-   max_l2_update_per_cycle
-   global_sleep_update_budget
-   consolidation_cap
-   variance gate обязателен
-   ACh не влияет на sleep_alpha

## Антипаттерны

-   Консолидация каждого эпизода
-   Удаление variance gate
-   Увеличение sleep_alpha через ACh
-   Игнорирование budget

## Тест-кейсы

1.  Шумовой эпизод → не консолидируется
2.  Повторяемый значимый эпизод → консолидируется
3.  Высокая variance → нет консолидации
4.  Высокий ACh при низком TD → нет консолидации
5.  Превышение бюджета → остановка sleep
