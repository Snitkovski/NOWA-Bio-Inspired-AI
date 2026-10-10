# Phase 4.5 — мониторинг устойчивости и контроль дрейфа

English version: [Phase_4_5_Stability_Monitoring_RU_Spec.en.md](Phase_4_5_Stability_Monitoring_RU_Spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## 1. Назначение фазы

Phase 4.5 вводит мета-уровень мониторинга устойчивости эмоционально-нейромодуляторной системы.

Фаза НЕ:
- изменяет эмоции
- изменяет background
- изменяет нейромодуляторы
- участвует в action selection
- влияет на learning

Фаза ТОЛЬКО:
- измеряет
- анализирует долгосрочные метрики
- выставляет диагностические флаги устойчивости

Это слой только для чтения.

---

## 2. Архитектурные границы

### 2.1 Доступ к данным

Разрешено:
- чтение emotional_state
- чтение affective_background
- чтение neuromodulators
- чтение expectations (global_outlook)
- чтение логов активации Phase 4.4

Запрещено:
- любая запись в указанные структуры
- вызов регуляторов
- изменение памяти T1/T2/T3
- изменение BG, TD-learning и других связанных механизмов

---

## 3. Временное окно анализа

Используется скользящее окно W:

W = 500–2000 тиков (конфигурируемо)

Все вычисления производятся по агрегированным значениям в пределах окна.

---

## 4. Метрики устойчивости

### 4.1 Regulation Activation Rate

regulation_activation_rate = activations_4_4 / window_length

Порог: > 0.15 → regulation_overuse_flag = True

---

### 4.2 Background Drift

mean_background = mean(background_anxiety over W)

Если mean_background > baseline_background + 0.20 → background_drift_flag = True

---

### 4.3 Neuromodulator Drift

Для каждого модулятора:

mean_mod = mean(level over W)

Если |mean_mod − baseline_mod| > 0.25 → neuromodulator_drift_flag = True

---

### 4.4 Dominant Emotion Lock

Если одна и та же эмоция:

- доминирует более 70% времени в окне
- без соответствующего роста интенсивности
- без новых триггеров

→ dominant_emotion_lock_flag = True

---

### 4.5 Outlook Bias

escalating_ratio = fraction(global_outlook == "escalating")

Если escalating_ratio > 0.7 → outlook_bias_flag = True

---

## 5. Stability Index

stability_index = 1.0 − weighted_sum(flags)

Пример весов:
- regulation_overuse: 0.25
- background_drift: 0.25
- neuromodulator_drift: 0.25
- dominant_emotion_lock: 0.15
- outlook_bias: 0.10

Индекс ограничивается диапазоном [0.0, 1.0]

---

## 6. Возвращаемая структура

```python
{
  "stability_index": float,
  "drift_flags": {
      "regulation_overuse": bool,
      "background_drift": bool,
      "neuromodulator_drift": bool,
      "dominant_emotion_lock": bool,
      "outlook_bias": bool
  },
  "recommendation": "none" |
                    "inspect_expectations" |
                    "inspect_memory" |
                    "inspect_regulation" |
                    "inspect_background" |
                    "inspect_neuromodulators"
}
```

recommendation формируется логически:
- regulation_overuse → inspect_regulation
- neuromodulator_drift → inspect_neuromodulators
- background_drift → inspect_background
- outlook_bias → inspect_expectations
- dominant_emotion_lock → inspect_memory
- иначе → none

---

## 7. Ограничения безопасности

1. Phase 4.5 НЕ может изменять состояние системы.
2. Phase 4.5 НЕ может инициировать регуляцию.
3. Phase 4.5 НЕ участвует в вычислении reward.
4. Phase 4.5 НЕ влияет на TD-learning.
5. Phase 4.5 НЕ передаёт сигналы напрямую в Phase 4.4.

Связь с Phase 5 допускается только через чтение stability_index.

---

## 8. Инварианты

- Доступ только для чтения
- Отсутствие побочных эффектов записи
- Использование сглаженных метрик
- Наличие гистерезиса (минимум 2 окна подряд для фиксации drift)

---

## 9. Будущие расширения

- Интеграция циркадных ритмов (после Phase 5)
- Разделение краткосрочной и долгосрочной устойчивости
- Адаптивные пороги на основе истории системы

---

## 10. Примечания реализации (фактическое состояние)

- baseline_background НЕ фиксируется по первому тику.
- baseline_background калибруется по warm-up выборке (медиана первых N тиков, по умолчанию N = window_size).
- До завершения warm-up background_drift не активируется.
- Состояние калибровки и истории сохраняются в save/load (через emotional_stability).

---

Статус: Implemented v1.1
