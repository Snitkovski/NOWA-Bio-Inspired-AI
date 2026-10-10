# Главная страница документации по нейромодуляторам

English version: [NEUROMODULATORS_HOME.en.md](NEUROMODULATORS_HOME.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**Февраль 2026 — Финальный релиз**

---

## Старт здесь

### В спешке? (5 мин)
→ [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md)

### Разработчик? (30 мин)
→ [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md)

### Архитектор? (60+ мин)
→ [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

### Нужен отчёт?
→ [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.ru.md)

---

## Все документы

### Основная документация (обязательная)

| Документ | Объём | Назначение | Прочитано? |
|----------|-------|-----------|-----------|
| [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md) | 5 стр | **НАЧНИТЕ ОТСЮДА** | ☐ |
| [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) | 10 стр | API и примеры | ☐ |
| [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md) | 12 стр | Полная спецификация | ☐ |
| [NEUROMODULATORS_SUMMARY_REPORT.md](NEUROMODULATORS_SUMMARY_REPORT.ru.md) | 8 стр | Что было сделано | ☐ |

### Справочная документация (по мере необходимости)

| Документ | Объём | Назначение |
|----------|-------|-----------|
| [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.ru.md) | 18 стр | Полный отчёт |
| [NEUROMODULATORS_DOCUMENTATION_GUIDE.md](NEUROMODULATORS_DOCUMENTATION_GUIDE.ru.md) | 10 стр | Как читать документацию |
| [NEUROMODULATORS_CHECKLIST.md](NEUROMODULATORS_CHECKLIST.ru.md) | 8 стр | Чек-лист завершения |
| [PROJECT_STATUS_FINAL.ru.md](PROJECT_STATUS_FINAL.ru.md) | 12 стр | Финальный статус |

### Обновлённые документы

| Документ | Изменения |
|----------|-----------|
| [README.md](README.md) | Добавлены ссылки на нейромодуляторы |
| [CHANGELOG.md](CHANGELOG.ru.md) | Запись о февральском релизе |
| [INDEX.md](INDEX.ru.md) | Раздел о нейромодуляторах |

---

## По ролям

### Я новичок в проекте
1. Прочитать: [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md) (5 мин)
2. Запустить: `python src/gui.py` (5 мин)
3. Прочитать: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) (15 мин)
4. Посмотреть: примеры кода в документе (10 мин)
**Итого:** ~35 минут

### Я разработчик
1. Прочитать: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) (15 мин)
2. Посмотреть: `src/neuromodulators.py` (10 мин)
3. Прочитать: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md) (30 мин)
4. Запустить: тесты `pytest tests/test_neuromodulators.py` (5 мин)
**Итого:** ~60 минут

### Я архитектор или лидер команды
1. Прочитать: [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.ru.md) (45 мин)
2. Прочитать: [PROJECT_STATUS_FINAL.ru.md](PROJECT_STATUS_FINAL.ru.md) (20 мин)
3. Посмотреть: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md) для глубокого понимания (30 мин)
4. Обсудить: выводы с командой
**Итого:** ~95 минут + обсуждение

### Я специалист по контролю качества или тестировщик
1. Прочитать: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) раздел "Testing" (10 мин)
2. Запустить: тесты `pytest tests/test_neuromodulators.py -v` (5 мин)
3. Запустить: все тесты `pytest tests/` (2 мин)
4. Прочитать: [NEUROMODULATORS_CHECKLIST.md](NEUROMODULATORS_CHECKLIST.ru.md) (15 мин)
**Итого:** ~32 минуты

---

## По темам

### Что такое нейромодуляторы?
→ Раздел "Overview" в [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md)

### Как они работают?
→ Раздел "Architecture" в [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

### Как их использовать?
→ Раздел "Usage Examples" в [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md)

### Как их тестировать?
→ Раздел "Testing" в [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

### Как их расширять?
→ Раздел "Расширение" в [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

### Что если ошибка?
→ Раздел "Troubleshooting" в [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md)

---

## Получить работающую систему

### Быстрая проверка (2 минуты)

```bash
# Проверить, что всё установлено
python -c "from src.neuromodulators import NeuromodulatorState; print('OK')"

# Запустить основной тест
pytest tests/test_neuromodulators.py::test_dopamine_increases_on_reward -v
```

### Полная проверка (5 минут)

```bash
# Запустить все тесты нейромодуляторов
pytest tests/test_neuromodulators.py -v

# Запустить весь проект
pytest tests/ -v --tb=short
```

### Интерактивная проверка (10 минут)

```bash
# Запустить GUI
python src/gui.py

# Выполнить несколько шагов → посмотреть на значения нейромодуляторов
# Выполнить sleep (Ctrl+Z или через интерфейс) → посмотреть эффекты
```

---

## Вопросы и ответы

**Вопрос: С чего начать?**  
Ответ: [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md)

**Вопрос: Где примеры кода?**  
Ответ: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) раздел "Examples"

**Вопрос: Как это всё работает внутри?**  
Ответ: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

**Вопрос: Есть ошибка, что делать?**  
Ответ: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) раздел "Troubleshooting"

**Вопрос: Хочу расширить систему**  
Ответ: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md) раздел "Расширение"

**Вопрос: Нужна вся информация**  
Ответ: [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.ru.md)

---

## Статус проекта

| Компонент | Статус |
|-----------|--------|
| Код | 100% завершён |
| Тесты | 172/172 проходят |
| Документация | Полная (1300+ строк) |
| Интеграция | Полная |
| Готовность к эксплуатации | Да |

---

## Быстрая статистика

- **4 нейромодулятора:** Dopamine, Norepinephrine, Serotonin, Cortisol
- **1 новый файл:** `src/neuromodulators.py` (81 строка)
- **5 модифицировано:** agent.py, sleep.py, storage.py, gui.py, и др.
- **4 новых теста:** test_dopamine, test_norepinephrine, test_serotonin, test_cortisol
- **172 всего тестов:** 172/172 проходят
- **6 новых документов:** Полная документация
- **0 ломающих изменений:** Обратная совместимость 100%

---

## Обучение

Хотите стать экспертом? Читайте в этом порядке:

1. **Уровень 1 (Пользователь):** [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md) - 15 мин
2. **Уровень 2 (Разработчик):** [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md) - 30 мин
3. **Уровень 3 (Специалист):** [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.ru.md) - 45 мин
4. **Уровень 4 (Эксперт):** [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.ru.md) - 60 мин

**Итого:** ~150 минут и вы эксперт!

---

## Полезные ссылки

### В этом проекте

- [Исходный код: src/neuromodulators.py](../src/neuromodulators.py)
- [Интеграция: src/agent.py (поиск "neuromodulators")](../src/agent.py)
- [Эффекты: src/sleep.py (_apply_neuromodulators_during_sleep)](../src/sleep.py)
- [Тесты: tests/test_neuromodulators.py](../tests/test_neuromodulators.py)

### Документация

- [Главный README](README.md)
- [Полный INDEX](INDEX.ru.md)
- [CHANGELOG](CHANGELOG.ru.md)

---

## Готово к использованию

**Система нейромодуляторов полностью реализована, протестирована и задокументирована.**

Начните с [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.ru.md) или выберите документ по вашей роли выше.

---

**Последнее обновление:** 5 февраля 2026  
**Версия:** 1.0  
**Статус:** готово к промышленной эксплуатации
