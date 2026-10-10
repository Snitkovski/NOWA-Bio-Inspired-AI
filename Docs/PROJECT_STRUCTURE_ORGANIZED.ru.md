# Структура проекта NOWA-Cognitive (организованная)

English version: [PROJECT_STRUCTURE_ORGANIZED.en.md](PROJECT_STRUCTURE_ORGANIZED.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**Дата**: 31 января 2026  
**Статус**: реорганизована

---

## Новая структура проекта

```
NOWA-Cognitive/
├── src/                          # Исходный код
│   ├── action_intent.py
│   ├── action_realizer.py
│   ├── agent.py
│   ├── affect.py                    # Новое: аффективная система
│   ├── cortex.py
│   ├── dataset.py
│   ├── experience.py
│   ├── gui.py
│   ├── hippocampus.py
│   ├── intent_memory.py
│   ├── loader.py
│   ├── player.py
│   ├── sample.py
│   ├── selector.py
│   ├── sleep_manager.py
│   ├── sleep.py
│   ├── storage.py
│   ├── train_from_dataset.py
│   ├── trainer.py
│   ├── usage_example.py
│   └── dataset/
│       └── dialog_experience.json
│
├── tests/                        # Все тесты
│   ├── __init__.py
│   ├── test_adaptive_mouth.py
│   ├── test_affective_regulators.py  # Новое: регуляторы аффекта
│   ├── test_affect_integration.py     # Новое: интеграция аффекта
│   ├── test_agent.py
│   ├── test_dataset_loading.py
│   ├── test_dialog_loading.py
│   ├── test_experience_immutability.py
│   ├── test_fix.py
│   ├── test_gui_affective.py          # Перемещён: из корня
│   ├── test_gui_refactoring.py
│   ├── test_habits_loading.py         # Перемещён: из корня
│   ├── test_hippocampus.py
│   ├── test_intent_memory.py
│   ├── test_intent_memory_integration.py
│   ├── test_save_load_affect.py       # Перемещён: из корня (новый)
│   ├── test_selector.py
│   ├── test_sleep_consolidation.py
│   ├── test_trainer.py
│   ├── test_trainer_deprecated.py
│   └── __pycache__/
│
├── Docs/                         # Вся документация
│   ├── README.md                    # Главная документация
│   ├── ADAPTIVE_MOUTH_QUICK_REFERENCE.md
│   ├── ADAPTIVE_MOUTH_REFACTORING_COMPLETE.md
│   ├── ADAPTIVE_MOUTH_SUMMARY.py
│   ├── CHANGELOG.md
│   ├── CHANGES_SUMMARY.md           # Перемещён: из корня
│   ├── COMPLETE_PROJECT_REPORT.ru.md   # Перемещён: из корня
│   ├── DATASET_LOADING_FIX.md
│   ├── DELIVERY_SUMMARY.md
│   ├── EXECUTIVE_SUMMARY.md         # Перемещён: из корня
│   ├── FILES_CHANGES_COMPLETE_LIST.md # Перемещён: из корня
│   ├── FINAL_PROJECT_SUMMARY.md     # Перемещён: из корня
│   ├── FINAL_REPORT.md              # Перемещён: из корня
│   ├── FINAL_SUMMARY_RU.md          # Перемещён: из корня
│   ├── GUI_AFFECTIVE_VISUALIZATION_REPORT.md # Перемещён: из корня
│   ├── GUI_COMPLETE.md
│   ├── GUI_HABITS_IMPLEMENTATION.md # Перемещён: из корня
│   ├── GUI_QUICK_REFERENCE.md
│   ├── GUI_REFACTORING.md
│   ├── GUI_REFACTORING_SUMMARY.md
│   ├── GUIDE_AUTO_TRAINING.md
│   ├── IMPLEMENTATION_REPORT.md     # Перемещён: из корня
│   ├── INDEX.md                     # Перемещён: из корня
│   ├── INTENT_MEMORY.md
│   ├── INTENT_MEMORY_IMPLEMENTATION.md
│   ├── LEARNING.md
│   ├── PROJECT_COMPLETION_CONFIRMATION.md # Перемещён: из корня
│   ├── PROJECT_STATISTICS.md        # Перемещён: из корня
│   ├── PROJECT_STRUCTURE.md         # Перемещён: из корня
│   ├── QUICK_START_RU.md            # Перемещён: из корня
│   ├── README_AFFECTIVE_SYSTEM.md   # Перемещён: из корня
│   ├── README_AUTO_TRAINING.md
│   ├── README_REFACTORED.md
│   ├── REALIZATIONS_EXPANSION.md
│   ├── REFACTORING_COMPLETE.md
│   ├── REFACTORING_STATUS.md
│   ├── SAVE_LOAD_AFFECT_STATE.md    # Перемещён: из корня (новый)
│   ├── START_HERE.md                # Перемещён: из корня
│   ├── SUMMARY.md
│   ├── nowa_affective_refactor_plan.md
│   ├── nowa_refactoring_plan_intent_memory.md
│   ├── nowa_refactoring_plan_v_2.md
│   └── refactoring_plan_adaptive_mouth.md
│
├── Demo/                         # Примеры и демонстрации
│   ├── demo_intent_memory.py
│   ├── demo_realizations.py
│   └── examples_training.py
│
├── datasets/                     # Данные для тренировки
│   ├── habits.json
│   ├── realizations_advanced.json
│   ├── realizations_basic.json
│   ├── realizations_extended.json
│   └── test.json
│
├── saves/                        # Сохранённые состояния агента
│
├── .venv/                        # Виртуальное окружение Python
│
├── .pytest_cache/                # Кэш pytest
│
├── __pycache__/                  # Кэш Python
│
├── LICENSE                       # Лицензия проекта
├── .gitignore                    # Git ignore
└── README.md                     # (ссылка на Docs/README.md)
```

---

## Статистика реорганизации

### До реорганизации
```
Корень проекта:
  ├─ 18 файлов .md (документация)
  ├─ 3 файла .py (тесты)
  └─ Прочие файлы
```

### После реорганизации
```
Все 18 документов перемещены в Docs/
Все 3 дополнительных теста перемещены в tests/
Корень проекта очищен
```

### Новые числа
- **Docs/**: 43 файла (было 25, добавлено 18)
- **tests/**: 22 файла (было 19, добавлено 3)
- **src/**: 24 файла (без изменений)
- **Корень**: только файлы конфигурации и данные

---

## Что переместилось

### В Docs/ (18 файлов)
```
CHANGES_SUMMARY.md
COMPLETE_PROJECT_REPORT.ru.md
EXECUTIVE_SUMMARY.md
FILES_CHANGES_COMPLETE_LIST.md
FINAL_PROJECT_SUMMARY.md
FINAL_REPORT.md
FINAL_SUMMARY_RU.md
GUI_AFFECTIVE_VISUALIZATION_REPORT.md
GUI_HABITS_IMPLEMENTATION.md
IMPLEMENTATION_REPORT.md
INDEX.md
PROJECT_COMPLETION_CONFIRMATION.md
PROJECT_STATISTICS.md
PROJECT_STRUCTURE.md
QUICK_START_RU.md
README_AFFECTIVE_SYSTEM.md
SAVE_LOAD_AFFECT_STATE.md
START_HERE.md
```

### В tests/ (3 файла)
```
test_save_load_affect.py
test_habits_loading.py
test_gui_affective.py
```

---

## Назначение каждой папки

### src/
**Назначение**: исходный код проекта  
**Содержит**: модули Python ядра системы
- Ядро агента (agent.py, cortex.py, hippocampus.py)
- Аффективная система (affect.py)
- Интерфейс (gui.py)
- Тренировка и обучение (trainer.py, train_from_dataset.py)
- Хранилище (storage.py)

### tests/
**Назначение**: все тесты проекта  
**Содержит**: модульные и интеграционные тесты (22 файла)
- Тесты ядра (test_agent.py, test_cortex.py)
- Тесты аффективной системы (test_affective_regulators.py, test_affect_integration.py)
- Тесты интерфейса (test_gui_affective.py, test_gui_refactoring.py)
- Тесты памяти (test_hippocampus.py, test_intent_memory.py)
- Тесты сохранения и загрузки (test_save_load_affect.py)
- И многое другое

### Docs/
**Назначение**: полная документация проекта  
**Содержит**: 43 файла markdown
- Основная документация (README.md)
- Отчёты о внедрении (IMPLEMENTATION_REPORT.md, DELIVERY_SUMMARY.md)
- Руководства (QUICK_START_RU.md, GUIDE_AUTO_TRAINING.md)
- Планы рефакторинга и подробные отчёты
- Итоговые документы о завершении проекта

### Demo/
**Назначение**: примеры и демонстрации  
**Содержит**: сценарии Python для демонстрации функциональности
- demo_intent_memory.py — демонстрация памяти намерений
- demo_realizations.py — демонстрация реализаций
- examples_training.py — примеры обучения

### datasets/
**Назначение**: данные для тренировки  
**Содержит**: файлы JSON с данными
- habits.json — привычки агента
- realizations_*.json — реализации разного уровня
- test.json — тестовые данные

### saves/
**Назначение**: сохранённые состояния  
**Содержит**: файлы сохранённых состояний агента

---

## Преимущества новой структуры

- **Чистота**: корень проекта содержит только критически важные файлы
- **Логичность**: каждый тип файлов в своём месте
- **Масштабируемость**: легко добавлять новые документы и тесты
- **Профессиональная форма**: соответствует стандартам организации проектов
- **Навигация**: легче ориентироваться в структуре проекта

---

## Рекомендации

1. **При добавлении новых документов**: размещайте в `Docs/`
2. **При добавлении новых тестов**: размещайте в `tests/`
3. **При добавлении новых примеров**: размещайте в `Demo/`
4. **При добавлении новых данных**: размещайте в `datasets/`
5. **При сохранении состояния**: используется `saves/` (автоматически)

---

## Навигация

- **Начало работы**: [START_HERE.md](START_HERE.ru.md)
- **Быстрый старт**: [QUICK_START_RU.md](QUICK_START_RU.ru.md)
- **Главная документация**: [README.md](README.md)
- **Индекс документов**: [INDEX.md](INDEX.ru.md)

---

**Дата обновления**: 31 января 2026  
**Версия структуры**: 2.0  
**Статус**: организовано и готово
