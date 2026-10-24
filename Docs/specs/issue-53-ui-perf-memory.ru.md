# Issue #53 — скорость UI колонии и память эпизодов: спецификация реализации

Closes #53. База: `main` @ `c3bbd62` (merge-base после PR #48). QA: [issue-53-ui-perf-memory.ru.md](../qa/issue-53-ui-perf-memory.ru.md). English: [issue-53-ui-perf-memory.en.md](issue-53-ui-perf-memory.en.md).

Сабтики из issue #39 (`SimulationRunner.MAX_TICK_DT = 0.25`) сохранены. Ёмкость гиппокампа (1024 на агента), recall, decay, eviction, консолидация во сне и двухъярусная пластичность не менялись. Каждая шиншилла — отдельный `Agent`. Стоимость неудовлетворённой потребности та же.

---

## 1. Проблема

После PR #48 headless на мощной машине даёт примерно **8×** реальной скорости при ускорении 10×. В демо **Colony chinchillas** с pygame UI и девятью агентами наблюдалось только **2–3×**, а длинные сессии удерживали около **1 ГБ** RAM.

Шейдеры отрисовки не менялись. На этой ветке подтверждены причины:

1. **Связка в одном потоке.** Цикл GUI одновременно крутил симуляцию и полную отрисовку; тяжёлый тик с полным гиппокампом блокировал кадр, карточки справа и полоса статистики перерисовывались каждый раз.
2. **История тиков организма.** `AutonomousOrganismAgent` дописывал полный словарь тика в `tick_history` на каждом шаге. Девять агентов × тысячи тиков × ~5 КБ на словарь раздували RSS.
3. **Накладные расходы эпизода.** `Experience`, пути, события и следы были обычными объектами; повторяющиеся строки признаков и событий не разделялись.

Приёмка issue #53 также требует пару спецификаций и QA-отчёт с замерами до/после.

---

## 2. Цели и не-цели

### Цели

| Область | Задача |
| --- | --- |
| UI на 10× | Развязать **частоту отрисовки** и **catch-up симуляции**; ограничить интерактивный FPS; кешировать статичные и редко меняющиеся поверхности. |
| Память | Уменьшить объём на эпизод и тик **без** снижения ёмкости гиппокампа и числа эпизодов. |
| Эквивалентность | Та же биология и траектории, что на `main`, на 1× и 10× (семантика сабтиков сохранена). |
| Сохранения | Pickle `AgentStorage`, записанные на `main`, должны открываться на этой ветке. |
| Замеры | `bench_speed.py` сообщает headless и GUI achieved speed и RSS на одной колонии. |

### Не-цели

- Вынос симуляции во второй поток или процесс (ломает детерминизм catch-up в GUI-потоке).
- Перенастройка алгоритмов гиппокампа, порогов или пластичности.
- Смена формата JSON колонии (по-прежнему число эпизодов, не граф объектов).

---

## 3. GUI: потолок кадров и кеш панелей

**Файлы:** `Demo/Colony chinchillas/src/colony_gui/app.py`, `colony_gui/colony_gui.py` (read-model без изменений).

### 3.1 Фиксированный cadence отрисовки

- `RENDER_FPS_CAP = 30` — интерактивное окно рисует не чаще ~30 fps.
- `SIM_FRAME_DT_CAP_S = 1.0` — настенное время для catch-up не обрезается до 50 ms, чтобы 10× мог использовать длинные шаги при достаточном CPU.
- Сабшаги симуляции по-прежнему задаются `SIM_MAX_STEP_S = 0.25`, `SIM_MAX_CATCHUP_STEPS` и `SIM_ACCUMULATOR_MAX_STEPS` (как в issue #39).
- Между кадрами цикл **продолжает** catch-up `_sim_tick`; медленная сессия 10× упирается в симуляцию, а не в отрисовку.

**Исключения (рисуют каждую итерацию):** захват кадров (`frame_dt_s`, `on_frame`, `max_frames`) и тесты с этими хуками.

При большой популяции `target_fps` повышается через `HIGH_POP_RENDER_FPS` / `VERY_HIGH_POP_RENDER_FPS`; при ≥90 агентах потолок остаётся 30.

### 3.2 Кеши

| Поверхность | Поведение |
| --- | --- |
| Фон клетки | Уже кешировался (`static_scene`); без изменений. |
| Карточки агентов справа | `_right_panel_cache_token(...)` — пересборка blit только при смене входов (метрики, действие, язык, скролл, выбор и т.д.). |
| Полоса статистики под клеткой | `_stats_panel_cache_token(...)` — то же для изобилия, полос и полей observer. |
| Текст подписей | Существующие `panel_text_surface_cache` / `name_surface_cache`. |

Пропущенные кадры всё равно двигают сглаживание спрайтов по накопленному `visual_elapsed_s`.

### 3.3 Профилирование

`run_pygame_demo(..., frame_profile=profile)` заполняет доли wall-time: `sim_s`, `snapshot_s`, `background_s`, `agents_s`, `labels_s`, `stats_s`, `panel_s`, `flip_s`, плюс `paints` и `sim_advanced_s`. Используют `bench_speed.py` и `test_capped_pygame_loop_advances_simulation`.

---

## 4. Память: слоты, интернирование, tick_history

### 4.1 Слотовый граф эпизода

**Файлы:** `src/experience.py`, `src/affective_space.py`, `src/hippocampus.py`.

| Тип | Механизм |
| --- | --- |
| `Experience` | `__slots__` |
| `Event` | `__slots__` + свои `__getstate__` / `__setstate__` |
| `Path` | `__slots__` + состояние pickle |
| `SignatureTrace` | `@dataclass(slots=True)` |
| `EmotionalTrace` | `@dataclass(slots=True)` |
| `NOWAHippocampus` | слоты + `__setstate__` для полей кеша, добавленных на ветке |

Имена событий и токены признаков длиной ≤ 80 **интернируются** (`sys.intern`) через `_intern_short_token` / `_intern_token_collection`, чтобы общие токены (например `ctx:nest`) были одним объектом `str`.

`IntentTrace` и `AffectiveTrace` вне scope issue (здесь без слотов). Поля сидера Warriner на `Experience` остаются валидными именами слотов.

### 4.2 Удержание `tick_history`

**Файл:** `src/autonomous_organism.py`

- `TICK_HISTORY_RETAIN = 1` — после тика старые записи отбрасываются, остаётся только последний словарь.
- `get_autonomous_state()["tick_count"]` по-прежнему отдаёт полное число тиков через `_completed_ticks` и `_autonomous_tick_count_offset` после restore (`src/agent.py`).
- Читатели: режим физиологии в `src/gui.py` берёт только `tick_history[-1]`; save/load и диагностика старые тики не обходят.

**Известное расщепление (было на `main`):** `runtime.snapshot()["tick_count"]` в Tk после restore — `len(tick_history)`, без offset.

---

## 5. Совместимость pickle с `main`

В раунде 1 ветка не открывала blob `AgentStorage` с `main` (`AttributeError: 'Path' object has no attribute '__dict__'` после `__slots__`).

**Исправление (коммит `4945e24`):** `__setstate__` у `Event`, `Path`, `Experience`, `EmotionalTrace`, `SignatureTrace` и `NOWAHippocampus` принимает legacy payload `__dict__` из pickle до слотов и слотовый layout. Новые поля кеша гиппокампа по умолчанию пустые, если их не было.

**Регрессия:**

- Фикстура: `tests/fixtures/agent_from_main_c3bbd62.pkl` (агент с `main` @ `c3bbd62`).
- Тесты: `tests/test_main_pickle_compat.py` (загрузка фикстуры, round-trip на ветке, поведение после load на замороженных часах).

Pickle с ветки в QA-прогонах открывается и на `main`. JSON колонии не затронут.

---

## 6. Гарантия эквивалентности биологии

Оптимизации **только реализации** (layout памяти, индексация, общие множители decay). Формулы Jaccard, decay, порядка eviction и импульсов recall зафиксированы тестами.

**Блокировка траектории (9 агентов, сид 7, `PYTHONHASHSEED=0`, `time.time` = `1_700_000_000`, 60 с sim):**

SHA-256 конечного состояния на `main` и на ветке (`dt=0.25` и `dt=2.5`):

`c8f1d7e6770e7d715cd4aff8a71054b2bef3b16dd702050372be862de4ef8b90`

Максимальная абсолютная дельта 0 по действиям, позициям, признакам эпизодов, наградам и активации. Ёмкость гиппокампа 1024 на агента. `MAX_TICK_DT` и число сабтиков те же (60 с при 0.25 с и при 2.5 с → одинаковое число `_tick_once`).

`git diff c3bbd62...dbc351b` не меняет recall/decay/eviction/сон гиппокампа и лабильный слой.

---

## 7. Инструмент бенчмарка

**Файл:** `Demo/Colony chinchillas/tools/bench_speed.py`

- Прогревает колонию на 10×, пока каждый гиппокамп не заполнен (1024 эпизода) или не истечёт `--warmup-wall` (по умолчанию 60 с).
- **Headless:** та же математика catch-up, что в GUI (`_sim_tick`, адаптация нагрузки), без pygame.
- **GUI:** `run_pygame_demo` с SDL dummy (`SDL_VIDEODRIVER=dummy`).
- Печатает achieved = sim / wall (как HUD «факт x»).
- `--agents N` (по умолчанию 4; в QA — `--agents 9`). `--headless-only` пропускает секцию GUI.

Команда:

```bash
python3 "Demo/Colony chinchillas/tools/bench_speed.py" --agents 9
```

---

## 8. Замеры QA (независимая ВМ)

Источник: [issue-53-ui-perf-memory.ru.md](../qa/issue-53-ui-perf-memory.ru.md) (Python 3.12.3, pygame 2.6.1; **не** машина с ~8× headless из issue #39).

Сравнение `main` @ `c3bbd62` и ветки @ `dbc351b` после прогрева до 1024/1024:

| Метрика | `main` | Ветка |
| --- | --- | --- |
| Пик RSS | 299.6 MiB (306792 KiB) | 223.2 MiB (228512 KiB) |
| Headless 10× achieved | 2.64× | 2.86× |
| Headless 1× achieved | 0.98× | 0.98× |
| GUI 10× achieved | (нет в скрипте `main`) | 1.90× (7 отрисовок; **sim 98.5%** wall-time цикла) |
| GUI 1× achieved | — | 0.97× |

Пик RSS на ветке **ниже на 78280 KiB (−25.5%)**. GUI 10× на этой ВМ упирается в симуляцию; потолок кадров активен (QA: 23.8 fps за 2.78 с при cap 30).

Раунд 2 (`4945e24`) повторно подтвердил хеш траектории и загрузку pickle с `main`. Полный pytest: **1932 passed**, 1 failed (см. §9).

---

## 9. Тесты

| Модуль | Роль |
| --- | --- |
| `Demo/Colony chinchillas/tests/test_issue53_trajectory_and_gui.py` | Траектории с одним сидом; эквивалентность 10×0.25 с и 1×2.5 с (`abs=1e-4` только для float); capped pygame двигает `sim_time`. |
| `tests/test_memory_speed_equivalence.py` | Decay, eviction, суммы recall, импульсы vs референс; pickle слотовых типов. |
| `tests/test_main_pickle_compat.py` | Загрузка `agent_from_main_c3bbd62.pkl`; round-trip на ветке; `step` / `sleep` / `activate` после load. |
| `tests/test_autonomous_organism.py` | `tick_history` длины 1 с верным `tick_count` через save/load. |

**Флак (был раньше, не регрессия ветки):** `Demo/Colony chinchillas/tests/test_fix_colony_no_rest.py::test_founders_do_not_die_of_exhaustion_at_10x` — основатели без `rng_seed`; уровень сена в миске недетерминирован. QA раунд 2: одно падение полного набора (hay 0.4846 < 0.5), следующий одиночный прогон прошёл; новым дефектом не заведено.

---

## 10. Затронутые файлы (кратко)

| Путь | Изменение |
| --- | --- |
| `Demo/Colony chinchillas/src/colony_gui/app.py` | Потолок кадров, кеш панелей/статистики, `frame_profile`, развязка sim/paint |
| `Demo/Colony chinchillas/tools/bench_speed.py` | Замер headless + GUI, RSS |
| `src/experience.py`, `src/affective_space.py`, `src/hippocampus.py` | Слоты, интернирование, pickle `__setstate__` |
| `src/autonomous_organism.py`, `src/agent.py` | `TICK_HISTORY_RETAIN`, offset счётчика тиков |
| `tests/*`, `tests/fixtures/agent_from_main_c3bbd62.pkl` | Эквивалентность, pickle, история организма |

---

## 11. Связанные документы

- Issue: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/issues/53
- PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/55
- QA-отчёт: [issue-53-ui-perf-memory.ru.md](../qa/issue-53-ui-perf-memory.ru.md)
- Сабтики хоста: [issue-39-dt-robustness.ru.md](issue-39-dt-robustness.ru.md)
