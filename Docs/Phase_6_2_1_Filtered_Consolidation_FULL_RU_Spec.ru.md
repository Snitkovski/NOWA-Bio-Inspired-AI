# Фаза 6.2.1 — фильтрованная консолидация (полная спецификация)

English version: [Phase_6_2_1_Filtered_Consolidation_FULL_RU_Spec.en.md](Phase_6_2_1_Filtered_Consolidation_FULL_RU_Spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## 1. Назначение

Строгий механизм селективной консолидации эпизодической памяти в долговременные представления.

Цели:
- исключение шумовой консолидации
- перенос устойчивых паттернов
- сохранение стабильности Value Layer
- предотвращение самоусиливающихся контуров

## 2. Архитектурные ограничения

НЕ допускается:
- изменение reward
- изменение TD error
- модификация online alpha
- влияние на политику решения
- модуляция sleep_alpha через ACh

Работает только в режиме сна.

## 3. Критерии допуска

Эпизод допускается, если:
- |TD_mean| ≥ td_threshold
- TD_variance ≤ td_variance_cap
- salience ≥ salience_threshold
- reinforcement_count ≥ min_reinforcement
- value_variance_ratio < variance_gate_threshold
- ACh_effective ≥ ach_min_for_consolidation
- stability_flag == TRUE

## 4. Оценка консолидации

```text
ACh_effective = max(0, ACh_snapshot - ach_baseline)

consolidation_score =
    w_td * |TD_mean| +
    w_salience * salience +
    w_importance * importance +
    w_ach * ACh_effective +
    w_encoding * encoding_strength
```

Ограничение:

```text
consolidation_score ≤ consolidation_cap
```

## 5. Обновление во сне

```text
delta_value =
    sleep_alpha *
    consolidation_score *
    sign(TD_mean)
```

Ограничения:
- sleep_alpha ≤ sleep_alpha_cap
- |delta_value| ≤ per_update_cap
- L2(delta_value_total) ≤ max_l2_update_per_cycle
- Σ|delta_value| ≤ global_sleep_update_budget

## 6. Вентиль дисперсии

```text
variance_gate = max(0, 1 - value_variance_ratio)
delta_value *= variance_gate
```

Если value_variance_ratio ≥ 1.0, сон запрещён.

## 7. Диагностика

Журналируются:
- total_episodes_examined
- total_episodes_consolidated
- причины rejected_due_to_*
- mean_consolidation_score
- sleep_update_l2_total
- variance_ratio
- consolidation_ratio

## 8. Антишаблоны

- Консолидация всех эпизодов
- Удаление вентиля дисперсии
- Игнорирование бюджета сна
- Прямая модификация TD

## 9. Тест-кейсы

1. Шум не консолидируется
2. Высокий TD вместе со стабильностью ведёт к консолидации
3. Высокая дисперсия блокирует сон
4. Переполнение бюджета останавливает сон
5. Стресс-тест 5000 циклов не показывает роста дисперсии
