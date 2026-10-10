# Заметки о реализации Hippocampus 2.0

English version: [HIPPOCAMPUS_2_0_IMPLEMENTATION.en.md](HIPPOCAMPUS_2_0_IMPLEMENTATION.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последнее обновление: 22 февраля 2026 г.

Настоящий документ описывает реализованное поведение эпизодической памяти в `src/hippocampus.py` и связанные тесты в `tests/test_hippocampus_2_0.py`.

---

## Область

Hippocampus 2.0 расширяет эпизодическую память:
1. Разделением паттернов (разрежение признаков).
2. Нечётким сопоставлением и подкреплением (не только точным равенством сигнатуры).
3. Завершением паттерна в духе CA3 (`reconstructed_features` из взвешенного отзыва top-k).
4. Сигналом новизны в духе CA1 (`novelty_score`, корзины класса новизны).
5. Кодированием темпорального контекста (`time_bucket`, скользящий хеш, дискретизированная корзина драйва).
6. Управлением ёмкостью и затуханием, пригодным для длительной симуляции.

---

## Открытый интерфейс

Файл: `src/hippocampus.py`

Основные методы:
1. `store(path_or_signature, consequence=None, intensity=1.0, reward=0.0, encoding_strength=None) -> Experience`
2. `reinforce(path_or_signature, consequence=None, intensity=1.0) -> Experience`
3. `activate(context_events: list[str]) -> list[Experience]`
4. `get_candidates_for_sleep(min_reinforcement=2) -> list[Experience]`
5. `get_statistics() -> dict`

Методы отзыва:
1. `recall_signature(current_signature: dict) -> dict`
2. `recall_recent(limit: int | None = None) -> list[Experience]`
3. `recall_by_drive(active_drive: str, limit: int = 6) -> list[Experience]`
4. `recall(...)` остаётся диспетчером обратной совместимости.

Схема выхода `recall_signature(...)`:

```json
{
  "reconstructed_features": [],
  "novelty_score": 0.0,
  "novelty_class": "familiar|partial_match|novel|high_novelty",
  "similarity_top_k": []
}
```

---

## Поведенческие подробности

### Сходство контекста

Контекст не основан на двоичном равенстве. Сходство сочетает:
1. Близость временных корзин.
2. Мягкое расстояние хеша.
3. Близость дискретизированных корзин драйва.
4. Частичное пересечение скользящих токенов контекста.

### Затухание

Затухание использует период полураспада как основной механизм, с мягкой регуляризацией от `decay_rate`, чтобы избежать чрезмерно быстрого схлопывания следов активации.

### Усечение ёмкости

Усечение ёмкости включает приоритет с учётом новизны:
1. Удержание активации.
2. Вклад новизны (`novelty_capacity_bias`).
3. Счётчик подкрепления.
4. Недавность.

### Реконструкция

Порог реконструкции адаптивен к текущим свидетельствам top-k (`0.5 * max_score` с границами) и не зафиксирован одной жёсткой константой.

---

## Основные настраиваемые параметры

Параметры конструктора `NOWAHippocampus(...)`:
1. `max_experiences`
2. `activation_decay_half_life`
3. `decay_rate`
4. `activation_threshold`
5. `max_features`
6. `top_k_recall`
7. `novelty_window`
8. `cycle_length`
9. `context_history_size`
10. `activation_similarity_threshold`
11. `reinforce_similarity_threshold`
12. `consolidation_min_probability`
13. `novelty_capacity_bias`

---

## Проверка

Основные тесты:
1. `tests/test_hippocampus.py` (совместимость с прежней версией и базовое поведение)
2. `tests/test_hippocampus_2_0.py` (поведение по спецификации и крайние случаи)

Точечная команда:

```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

На текущей базе:
1. `tests/test_hippocampus_2_0.py`: `13 passed`
2. Совокупные тесты hippocampus: `24 passed`
