# Руководство по реализации EpigenomeSnapshot (пакет B)

English version: [EPIGENOME_SNAPSHOT.en.md](EPIGENOME_SNAPSHOT.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последняя проверка: 24 марта 2026 г.

---

## Область

`src/epigenome.py` реализует перенос унаследованной консолидированной памяти для агентов NOWA. Модуль автономен и использует только стандартную библиотеку Python.

Основные цели:
1. неизменяемый контейнер снимка (классы данных с `frozen=True` и коллекции-кортежи)
2. безопасное извлечение из сырых словарных нагрузок (без импорта модулей времени выполнения NOWA)
3. внедрение на месте в целевые словари с ограниченным шумом
4. детерминированное поведение при фиксированном генераторе случайных чисел
5. устойчивая сериализация и диагностика проверки для хранения и процедур линии происхождения

---

## Реализованные объекты

### `InheritedPattern`

Поля:
- `context_signature: str`
- `action: str`
- `strength: float` в `[0.0, 1.0]`
- `reinforcement_count: int`

### `InheritedAction`

Поля:
- `action_id: str`
- `predicted_effect: Dict[str, float]`
- `semantic_confidence: float` в `[0.0, 1.0]`
- `stability_score: float` в `[0.0, 1.0]`
- `success_rate: float` в `[0.0, 1.0]`

### `InheritedValue`

Поля:
- `state_key: str`
- `value: float` в `[-1.0, 1.0]`
- `confidence: float` в `[0.0, 1.0]`
- `confirmation_count: float`

### `EpigenomeSnapshot`

Основные методы:
- создание: `extract(...)`, `from_dict(...)`, `empty()`
- перенос: `inject(...)`
- кроссовер: `blend(...)`
- диагностика: `is_empty()`, `size()`, `validate()`, `summary()`
- сериализация: `to_dict()`

---

## Поведение интерфейса

### `extract(...)`

Вход:
- `cortex_patterns: List[dict]`
- `action_metadata: Dict[str, dict]`
- `value_profiles: Dict[str, dict]`

Поведение отбора:
1. паттерны: верхние N по `reinforcement_count` (по убыванию), с порогом `min_reinforcement`
2. действия: верхние N по `stability_score` (по убыванию), требуется `consolidated=True`, порог `min_stability`
3. ценности: верхние N по `confirmation_count` (по убыванию), с порогом `min_confirmation`

Поведение безопасности:
1. некорректные записи пропускаются
2. числовые поля ограничиваются объявленными диапазонами
3. `max_patterns`, `max_actions` и `max_values` ограничиваются диапазоном `[1, 256]`
4. `source_generation` нормализуется к `>= 0`
5. `extraction_timestamp` задаётся через `time.time()`

### `inject(...)`

Поведение:
1. изменяет на месте `target_cortex_patterns`, `target_action_metadata` и `target_value_profiles`
2. возвращает статистику переноса:
   - `patterns_injected`, `patterns_skipped`
   - `actions_injected`, `actions_skipped`
   - `values_injected`, `values_skipped`
   - `noise_level`

Политика конфликтов:
1. действия и ценности: существующие ключи не перезаписываются
2. паттерны: существующая запись контекста заменяется только если унаследованная `strength` выше

Поведение шума:
1. `noise_level` ограничивается диапазоном `[0.0, 1.0]`
2. шум силы паттерна: гауссово `N(0, noise_level * 0.1)`, затем ограничение до `[0, 1]`
3. шум ценности: гауссово `N(0, noise_level * 0.2)`, затем ограничение до `[-1, 1]`
4. ослабление уверенности: мультипликативный множитель с ограниченной равномерной составляющей, затем ограничение до `[0, 1]`

### `blend(...)`

Поведение:
1. паттерны сливаются по `context_signature`; дубликаты сохраняют большую `strength`
2. действия сливаются по `action_id`; дубликаты сохраняют больший `stability_score`
3. ценности с одним `state_key` смешиваются:
   - `value = alpha * self + (1 - alpha) * other`
   - `confidence = min(self.confidence, other.confidence)`
4. выход ограничен `MAX_PATTERNS`, `MAX_ACTIONS` и `MAX_VALUES`
5. `alpha` ограничивается диапазоном `[0.0, 1.0]`
6. линия происхождения составляется как `f"{self.source_lineage_id}+{other.source_lineage_id}"[:64]`

### Сериализация и диагностика

1. `to_dict()` выдаёт отсортированные коллекции:
   - паттерны по силе, по убыванию
   - действия по устойчивости, по убыванию
   - ценности по подтверждению, по убыванию
2. `from_dict()` безопасно восстанавливает снимок:
   - некорректные строки пропускаются с предупреждениями
   - `source_generation < 0` нормализуется к `0`
3. `validate()` проверяет:
   - границы и конечность числовых значений
   - дубликаты ключей паттернов, действий и ценностей
   - отрицательные счётчики там, где они недопустимы
4. `summary()` возвращает компактные агрегатные метрики и счётчики

---

## Покрытие тестами

Основной набор:
- `tests/test_epigenome_snapshot.py`

Покрытие включает:
- TC-01..TC-16 из `Docs/SPEC_B_EpigenomeSnapshot.md`

Последний локальный прогон:

```text
python -m pytest tests/test_epigenome_snapshot.py -q
16 passed in 0.04s
```

Регрессия по проекту (без Demo):

```text
python -m pytest tests -q
643 passed, 3 skipped
```
