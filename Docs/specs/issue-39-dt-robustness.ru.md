# Issue #39 — Устойчивость колонии к dt: спецификация реализации

Закрывает #39 (только хост демо). Связано: [fix-colony-no-rest.ru.md](fix-colony-no-rest.ru.md) (эпизод сна без порога), PR #36 (правило порции), PR #48.

Когнитивное **ядро** в `src/` не подстраивается. У каждой шиншиллы свой `Agent`. `PHYSIOLOGY_AS_POLICY=True` остаётся включённым.

---

## 1. Проблема

На скорости UI 10× основатели `Demo/Colony chinchillas` умирают от **истощения** (энергия ≤ 0.08) за минуты, хотя еда, сено и вода в достатке. В записях смерти низкий стресс и положительная валентность — «спокойная сытая» смерть.

На `main` после PR #36, сид 7, четыре основателя:

| шаг `dt` | policy | время сим | смерти |
| --- | --- | --- | --- |
| 1/12 (×1) | True | 142 с | нет |
| 0.25 (×1 под нагрузкой GUI) | True | 395 с | нет (мин. энергия 0.65) |
| **2.5 (×10 × 0.25)** | **True** | 2400 с | **2 (212.5 с, 1195 с)** |
| 2.5 | False | 2400 с | нет |

`ColonyGUI._sim_tick` двигает раннер на `real_dt * speed`. Под нагрузкой `SIM_MAX_STEP_S = 0.25` (`app.py`), живой кадр 10× — `0.25 × 10 = 2.5` с на границе решения до подшагов.

---

## 2. Корневая причина (хост демо)

1. **Частота решений и штраф.** `_apply_unmet_need_cost` списывает энергию за симулированную секунду (голод ≥ 0.60 → 0.02/с, жажда ≥ 0.58 → 0.025/с, дефицит сна → 0.02/с). Одно решение агента на `tick(dt)`. При `dt = 2.5` один пропуск еды/питья ~0.0625 энергии; ~8 промахов подряд смертельны. На ×1 тот же разрыв на секунду симуляции в 25–30 раз дешевле из‑за частых решений.

2. **Мёртвая зона.** Доступность еды/питья совпадала с порогом штрафа (`HUNGER_NEED_THRESHOLD` 0.60, `THIRST_NEED_THRESHOLD` 0.58). Между «действовать нельзя» и «штраф начался» животное платило без пути к облегчению.

3. **Ловушка сна.** Добровольная дремота ниже порога Process S могла вести себя как физиологический эпизод; штраф за жажду продолжался, пить во сне нельзя. Энергия падала с ~0.49 до ~0.04 за ~22.5 с симуляции.

4. **Баг метаболизма по dt.** `_metabolism_tick` сбрасывался в 0 вместо вычитания 1.0 — голод/жажда росли раз в тик, а не раз в секунду симуляции.

5. **Баг восстановления сна по dt.** `SLEEP_MIN_RECOVERY_DURATION_S` (30) был полом на каждый тик: короткие шаги восстанавливали энергию и Process S быстрее одного длинного шага за ту же секунду.

6. **Заметка по дизайну (не баг).** Еда, питьё и `rest` энергию не восстанавливают; только сон и пассивный отдых тела.

**Ядро:** не отвечает за тайминг демо. Попутно: `autonomous_organism` обрезает `dt` до 1.0, `rest_time` — за вызов, не × `dt`; в хосте — нарезка тела (см. [fix-colony-no-rest.ru.md](fix-colony-no-rest.ru.md)), без ретюна ядра.

---

## 3. Дизайн (реализованные пункты)

### A. Подшаги и фактическая скорость на HUD

**Файл:** `Demo/Colony chinchillas/src/simulation_runner.py`

- `MAX_TICK_DT = 0.25` (как шаг 1× под нагрузкой, `app.SIM_MAX_STEP_S`).
- `tick(dt)`: при `dt > MAX_TICK_DT` — `ceil(dt / 0.25)` равных подшагов; каждый вызывает `_tick_once` (один `agent.sim_step` на агента).
- Номинальный ×1 (`dt = 1/12`) уже ниже порога — без укрупнения.
- Номинальный ×10 на базе 1/12 (`10/12` с) режется так, что срез ≤ 0.25 с.

**Файлы:** `colony_gui/colony_gui.py`, `colony_gui/app.py`

- `ColonyGUI.note_sim_pace(real_dt, sim_advanced)` сравнивает прирост симуляционного времени с `real_dt * speed` за ~0.5 с стены.
- `achieved_speed_ratio < 0.85` → HUD показывает `actual x…` / `факт x…` через `format_speed_status_line`.
- Подшаги нагружают CPU; слабая машина может не держать выбранное ускорение.

### B. Штраф при невозможности действовать — **намеренно без изменений**

В #39 предлагалось не вызывать `_apply_unmet_need_cost` во сне, во время эксклюзивного действия или при пустой миске. **Этот PR этого не делает.** Неудовлетворённая потребность продолжает тратить энергию как `rate × dt`, даже когда пить/есть нельзя (включая эпизод сна по потребности). Это может быть смертельно; пробуждение по порогам штрафа (пункт D) даёт облегчение до истощения.

**Регрессия:** `test_unmet_need_still_costs_energy_while_asleep` — жажда 0.70, эпизод по потребности, энергия падает на `UNMET_THIRST_ENERGY_PER_S * dt` при шагах 0.25 с и 2.5 с.

### C. Доступность и штраф (мёртвая зона убрана)

**Файл:** `colony_agent.py`

| Константа | Значение | Роль |
| --- | --- | --- |
| `HUNGER_AVAILABILITY_THRESHOLD` | 0.50 | `_needs_eat_action`, захват ресурса |
| `THIRST_AVAILABILITY_THRESHOLD` | 0.48 | `_needs_drink_action`, захват ресурса |
| `HUNGER_NEED_THRESHOLD` | 0.60 | штраф за голод |
| `THIRST_NEED_THRESHOLD` | 0.58 | штраф за жажду |

Ниже доступности порции нет (правило PR #36). Между доступностью и штрафом еда/питьё работают; штраф ещё не начался.

### D. Ловушка сна (`_sleep_entered_by_need`, `_must_wake_to_drink_or_eat`)

**Файл:** `colony_agent.py`

- `_sleep_entered_by_need`: ставится при открытии эпизода по потребности (`wake >= SLEEP_WAKEFULNESS_THRESHOLD` 0.7). Добровольный `sleep` ниже порога → `rest`, Process S не разряжается (пересечение с [fix-colony-no-rest.ru.md](fix-colony-no-rest.ru.md)).
- `_should_continue_sleeping()`: только для эпизода по потребности выше гистерезиса (`0.7 × 0.7 = 0.49`) и без пробуждения по жажде/голоду.
- `_must_wake_to_drink_or_eat()`: жажда ≥ 0.58 или голод ≥ 0.60 **и** wake &lt; `SLEEP_CRITICAL_THRESHOLD` (0.9). Пороги штрафа, не `THIRST_CRITICAL_THRESHOLD` (0.82) / `HUNGER_CRITICAL_THRESHOLD` (0.85): при 0.025 энергии/с истощение наступает раньше.
- При `_must_wake_to_drink_or_eat()` и сне / эпизоде по потребности: `_wake_from_sleep()` **до** perceive/decide, чтобы пить/есть в том же тике.
- **Process S ≥ 0.9** ночь не прерывает: иначе пропуск восстановления и риск смерти от недосыпа в том же тике.

**Хранение:** `colony_storage.py` сохраняет `sleep_entered_by_need` и `_body_step_carry`.

### E. Метаболизм и сон, не зависящие от шага

**Метаболизм:** `_resource_metabolism_step` накапливает `dt`; `while _metabolism_tick >= 1.0 - 1e-9` вычитает 1.0 и вызывает `_apply_metabolism_second()` (допуск 1e-9 для десяти шагов по 0.1 с).

**Тело:** `_advance_autonomous_body` режет полные `COLONY_BODY_STEP_S` (1/12) из остатка `_body_step_carry` (см. fix-colony-no-rest).

**Сон:** `_sleep_recovery_duration_s(dt) = dt * SLEEP_RECOVERY_DURATION_FACTOR` (22.0). `SLEEP_MIN_RECOVERY_DURATION_S` (30) — только историческая константа, на тик не применяется.

---

## 4. Константы (сводка)

| Имя | Значение |
| --- | --- |
| `SimulationRunner.MAX_TICK_DT` | 0.25 |
| `HUNGER_AVAILABILITY_THRESHOLD` | 0.50 |
| `THIRST_AVAILABILITY_THRESHOLD` | 0.48 |
| `HUNGER_NEED_THRESHOLD` (штраф) | 0.60 |
| `THIRST_NEED_THRESHOLD` (штраф) | 0.58 |
| `UNMET_HUNGER_ENERGY_PER_S` | 0.02 |
| `UNMET_THIRST_ENERGY_PER_S` | 0.025 |
| `UNMET_SLEEP_ENERGY_PER_S` | 0.02 |
| `SLEEP_WAKEFULNESS_THRESHOLD` | 0.7 |
| `SLEEP_CRITICAL_THRESHOLD` | 0.9 |
| `SLEEP_RECOVERY_DURATION_FACTOR` | 22.0 |
| `HUNGER_ACCUMULATION_PER_S` | 0.0035 |
| `THIRST_ACCUMULATION_PER_S` | 0.0045 |
| Допуск аккумулятора метаболизма | 1e-9 |
| Порог показа отставания HUD | `achieved_ratio < 0.85` |

---

## 5. Критерии приёмки

1. При ×1 под нагрузкой (`dt = 0.25`) и ×10 (`dt = 2.5`) за один интервал симуляции одинаковое число вызовов `sim_step` на агента (проверка 5 с).
2. Голод и жажда за 10 с совпадают для мелкого (`0.1` с) и крупного (`2.5` с) шага без еды.
3. Еда/питьё снимают потребность между доступностью и штрафом; штраф масштабируется как `rate × dt` на 1/12 и 2.5.
4. Добровольный сон ниже порога не ловит; эпизод по потребности будит при жажде/голоде в полосе штрафа, кроме Process S ≥ 0.9.
5. Сид 7, четыре основателя, 600 с при `dt = 2.5`: ноль смертей от истощения.
6. Пункт B: неутолённая жажда во сне по потребности по-прежнему снимает `0.025 * dt` энергии.
7. Сохранение/загрузка сохраняет `_sleep_entered_by_need` и `_body_step_carry`.
8. `xfail` на `test_tc01_two_agents_survive_300s` для #39 снят, когда тест проходит.

---

## 6. Тесты

**Основной файл:** `Demo/Colony chinchillas/tests/test_colony_dt_invariance.py` (пункты A, C, D, E, регрессия B).

**Дополнительно:** `tests/test_fix_colony_no_rest.py` (эпизод по порогу, длинный прогон сид 2 на 10×).

### Сравнение 1× и 10× (из PR #48)

| Проверка | 1× | 10× |
| --- | --- | --- |
| Решений за 5 с, шаг 0.25 vs 2.5 | 20 (4.0 / с) | 20 (4.0 / с) |
| Решений за 5 с, номинал 1/12 vs 10/12 | 61 (12.2 / с) | 24 (4.8 / с) |
| Голод / жажда за 10 с без еды | 0.235 / 0.245 | 0.235 / 0.245 |
| Принудительный explore, 12 с, голод / жажда / энергия | 0.292 / 0.274 / 1.0 | то же, дельта 0 |
| Сид 7, 4 основателя, 600 с при `dt = 2.5` | — | 0 смертей |
| Сид 7, 4 основателя, 90 с при `1/12` и `2.5` | живы, мин. энергия &gt; 0.2 | живы, мин. энергия &gt; 0.2 |
| Сид 2, 4 основателя, 1600 с при `dt = 2.5` | — | живы, кто-то спит; гранулы 0.389, сено 1.0, вода 0.73 |

### Ослабленная граница по гранулам (`test_founders_do_not_die_of_exhaustion_at_10x`)

После метаболизма раз в секунду и более ранней доступности еды сид 2 за 1600 с на 10× сильнее опустошает гранулы, чем старый «раз в тик». Измерено `food_pellets ≈ 0.389` (сено 1.0, вода 0.73). Утверждение ослаблено с `> 0.4` до **`> 0.2`**: нет истощения при реалистичном потреблении. Сено `> 0.5`, вода `> 0.4`, у всех `energy > 0.2`, кто-то спит.

### Карта тестов

| Тест | Пункт |
| --- | --- |
| `test_a_large_tick_splits_into_quarter_second_decisions` | A |
| `test_a_decision_rate_matches_at_1x_load_and_10x` | A |
| `test_a_nominal_10x_does_not_collapse_to_one_decision` | A |
| `test_speed_line_shows_actual_rate_when_sim_lags` | A (HUD) |
| `test_c_eat_and_drink_relieve_before_the_penalty` | C |
| `test_c_penalty_still_starts_at_the_need_threshold_for_both_steps` | C |
| `test_d_voluntary_sleep_does_not_trap_at_either_speed` | D |
| `test_d_need_bout_continues_until_resume_threshold` | D |
| `test_d_penalty_band_thirst_wakes_a_need_bout_at_both_speeds` | D |
| `test_d_critical_sleep_still_outranks_thirst` | D |
| `test_unmet_need_still_costs_energy_while_asleep` | B (без изменений) |
| `test_e_hunger_and_thirst_match_across_step_sizes` | E |
| `test_e_sim_step_needs_match_at_1x_and_10x_when_not_eating` | E |
| `test_seed7_founders_do_not_die_of_exhaustion_at_10x` | интеграция |
| `test_founders_survive_the_same_interval_at_1x_and_10x` | интеграция |
| `test_sleep_flag_and_body_carry_roundtrip` | D + хранение |
| `test_founders_do_not_die_of_exhaustion_at_10x` (`test_fix_colony_no_rest.py`) | длинный прогон + гранулы |

---

## 7. Вне области / открытые вопросы

- Восстановление энергии едой или `rest`; bias к отдыху при низкой энергии (дизайн демо).
- Масштаб физиологического bias ядра относительно BG `pressure_vector` (отдельный замер).
- Ретюн ставок штрафа или пункт B #39 (отмена штрафа при невозможности действовать).
