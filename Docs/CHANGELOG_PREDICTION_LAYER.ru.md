# Журнал изменений — интеграция Prediction Layer (Plan C)

English version: [CHANGELOG_PREDICTION_LAYER.en.md](CHANGELOG_PREDICTION_LAYER.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Дата: 2026-02-06

Краткое описание:

- Переименован архитектурный компонент `Plan C` → `Prediction Layer`.
- Реализован `src/prediction_layer.py` — минимальная v1 реализация предсказательного слоя.
- Интеграция `PredictionLayer` в `Agent` и `Selector` через `prediction_pressure`.
- Улучшена логика управления любопытством и затуханием в GUI: `novelty` стал градуированным (Jaccard), и `decay_over_time()` вызывается при обработке входа.
- Добавлен полный набор спецификационных тестов TC-C-01..TC-C-A3 и интеграционные тесты.

Изменённые/добавленные файлы:

- `src/prediction_layer.py` — новый модуль PredictionLayer
- `src/agent.py` — поддержка опционального `prediction_layer`
- `src/selector.py` — приём `prediction_pressure` в `choose()` (только как рекомендация)
- `src/affect.py` — смягчённый рост `curiosity` и сохранён `decay_over_time()`
- `src/gui.py` — градуированная новизна (Jaccard), явный вызов затухания перед шагом агента
- `tests/test_prediction_layer.py` — базовые модульные тесты для PredictionLayer
- `tests/test_prediction_layer_spec_compliance.py` — 15 спецификационных тестов (TC-C-01..TC-C-A3)
- `tests/test_affect_curiosity.py` и `tests/test_affect_curiosity_integration.py` — тесты curiosity

Тестирование:

- Полный прогон тестов: `pytest` → `193 passed`.
- Спецификационные тесты Prediction Layer: `pytest tests/test_prediction_layer_spec_compliance.py` → `15 passed`.

Руководство по верификации (быстрые команды):

```bash
# Запустить все тесты
pytest -q

# Спецификации Prediction Layer
pytest tests/test_prediction_layer_spec_compliance.py -q

# Тесты curiosity
pytest tests/test_affect_curiosity.py tests/test_affect_curiosity_integration.py -q
```

Замечания по совместимости и дальнейшие шаги:

- `PredictionLayer.predict()` — чистая функция, не совершает побочных эффектов и не запускает обучение.
- Обучение/консолидация остаётся в `SleepManager`/`temporal_chains`.
- Для v2: рекомендовано использовать `ChainMemory` как источник обучающей информации, добавить статистику исходов и вероятностную прямую модель.

Если нужно — подготовлю PR с этим журналом изменений и кратким описанием в теле PR для ревью.
