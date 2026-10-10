# Слой взаимодействия нейромодуляторов

English version: [NEUROMODULATOR_INTERACTION_LAYER.en.md](NEUROMODULATOR_INTERACTION_LAYER.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последнее обновление: 22 марта 2026 г.

Исходная реализация:
- `src/neuromodulators.py`

Связанная спецификация:
- `Docs/spec_neuromodulator_interaction_layer.md`

---

## Краткое изложение

В проекте теперь есть связанный слой взаимодействия четырёх нейромодуляторов:
- дофамин (`DA`)
- серотонин (`5HT`)
- норадреналин (`NE`)
- ацетилхолин (`ACh`)

Этот слой реализован как `NeuromodulatorField` и встроен в `NeuromodulatorState.update_from_signals(...)`.

---

## Динамика

Вектор состояния:

```text
M = [DA, 5HT, NE, ACh]
```

Матрица взаимодействия (`W`, взятая из спецификации):

```text
       DA    5HT   NE    ACh
DA   [  0   -0.2   0.1  -0.3 ]
5HT  [  0.1   0   -0.1   0   ]
NE   [  0.2  -0.1   0    0.2 ]
ACh  [ -0.3   0    0.2   0   ]
```

Реализованное обновление (центрированное на базовой линии ради устойчивости):

```text
dM/dt = base_signal + W * (M - baseline) - decay * (M - baseline)
```

Где:
- `base_signal` приходит из вознаграждения, новизны и конфликта, а также из логики новизны и повторения ACh.
- `baseline` — базовая линия каждого модулятора (`DA`, `5HT`, `NE` и `ach_baseline`).

---

## Интеграция в `NeuromodulatorState`

Добавленное или обновлённое поведение:
- `interaction_field: Optional[NeuromodulatorField]`
- помощники синхронизации:
  - `_sync_field_from_state()`
  - `_sync_state_from_field()`
  - `_apply_interaction_dynamics(...)`
- `update_from_signals(...)` теперь:
  1. строит `base_signal`,
  2. применяет обновления cortisol,
  3. вычисляет дельту ACh,
  4. исполняет связанную динамику взаимодействия,
  5. ограничивает значения и обновляет метку времени.

Сохранение:
- `to_dict()` включает `interaction_field`
- `from_dict()` восстанавливает `interaction_field` (с обратной совместимостью, если поле отсутствует)

---

## Испытания

Новые выделенные тесты:
- `tests/test_neuromodulator_interaction_layer.py`
  - устойчивость базовой линии без сигналов
  - высокий серотонин гасит дофамин
  - высокий дофамин подавляет ацетилхолин
  - связь на следующем шаге в `NeuromodulatorState`
  - сохранение поля взаимодействия

Команды проверки:

```bash
pytest -q tests/test_neuromodulator_interaction_layer.py
pytest -q tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
pytest -q tests
```

Последние наблюдавшиеся результаты:
- `tests/test_neuromodulator_interaction_layer.py`: `5 passed`
- совокупный набор нейромодуляторов: `29 passed`
- полный набор ядра (без Demo): `589 passed, 3 skipped`
