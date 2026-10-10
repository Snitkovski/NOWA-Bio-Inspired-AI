## Аннотация

English version: [NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.en.md](NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.en.md)

Патч v1.1.1 закрывает разрыв, измеренный на прогоне стадии 1b длиной двадцать кварталов при базовой линии семени 1: `cost_efficiency` = 0,7523, `stockout_avoidance` = 0,9493, `budget_discipline` = 1,0, `reaction_to_risk_events` = 0,7894. Избежание дефицита регрессирует во всех двадцати кварталах. Пол равен 0,9493 × 0,9 = 0,854. К концу серии значения падают до интервала 0,000–0,023 в кварталах 41, 42, 44 и 47. При этом `all_passed` истинен в восьми кварталах из двадцати — 31, 32, 34, 36, 41, 42, 45 и 48 — и в каждом из них избежание дефицита лежит ниже пола. При `stop_on_graduation=True` обучение остановилось бы на квартале 31, хотя суммарный дефицит в соседних кварталах достигает 4621–6002 единиц. Наибольшая непрерывная последовательность `all_passed` равна двум кварталам. Отчёты выпуска и нерегрессии в реализации v1.1 вычисляются верно и друг на друга не влияют.

Для стадии 1b квартал входит в серию выпуска только при одновременном прохождении запирающих критериев и при отсутствии значения «ложь» в словаре `non_regression`. Выпуск наступает после `GRADUATION_MIN_STREAK` = 3 таких кварталов подряд. Поле `graduated_at_quarter` указывает на первый квартал серии, то есть на начало удержанной компетентности. Серия вычисляется как чистая функция уже пройденных `result.quarters`, поэтому возобновление с контрольной точки её не обнуляет. Стадия 1a не меняется: при отсутствии базовой линии `non_regression` равен `None`, и достаточен один `all_passed`. Сами `graduation_report` и `_non_regression_for` патч не переписывает.

Второе изменение выравнивает строгость загрузки базовой линии со строгостью команды записи отчёта. Если `load_baseline` получает сырой список результатов и среди кварталов нет выпущенных, функция отказывается строить пол и возбуждает ошибку. `compute_stage_1a_baseline` для диагностической таблицы остаётся допускающей запасной расчёт по всем кварталам; строгость добавляется только на границе, где число попадает в охрану нерегрессии. Уже записанный курированный файл с ключом `stage_1a_baseline` читается по-прежнему. Повтор того же прогона после патча должен оставить `result.graduated` ложным на всех двадцати показанных кварталах.

---

# NOWA Procurement Sandbox — Патч v1.1.1

**Базовые документы:**
NOWA_Procurement_Sandbox_Spec.md (v1.0)
NOWA_Procurement_Sandbox_Spec_v1.1_patch.ru.md (учебный план стадий 1a/1b)

**Статус:** Готово к реализации — критический фикс поверх уже
реализованного и работающего кода v1.1

---

## Эмпирическое обоснование (не гипотеза — зафиксированный факт)

Прогон Stage 1b (20 кварталов, `stage_1a_baseline` из seed1:
`cost_efficiency=0.7523, stockout_avoidance=0.9493, budget_discipline=1.0,
reaction_to_risk_events=0.7894`) показал:

**`stockout_avoidance` регрессирует в 20 из 20 кварталов Stage 1b подряд,
без единого исключения.** Пол = 0.9493 × 0.9 = 0.854. К концу прогона
значения падают до 0.000–0.023 (кварталы 41, 42, 44, 47) — агент
фактически прекратил управление стоком.

**При этом `all_passed: true` срабатывает в 8 из 20 кварталов** (31, 32,
34, 36, 41, 42, 45, 48) — **в каждом из этих восьми** `stockout_avoidance`
одновременно регрессирован ниже пола.

С дефолтным `stop_on_graduation=True` обучение остановилось бы на
**квартале 31** с формальным `"GRADUATED"`, хотя `total_stockout_units`
в соседних кварталах достигает 4621–6002 единиц. Проверка streak (≥3
подряд, раздел 26.7) частично защищает — максимальная последовательность
`all_passed=true` в этом прогоне равна 2 (Q31–32, Q41–42) — но не решает
проблему полностью, если streak не связан явно с non-regression.

Вывод: `graduation_report()` и `check_non_regression()` в реализации v1.1
оба вычисляются корректно и независимо, но **не влияют друг на друга**.
`result.graduated` в `run_quarters`/`run_stage1b_persistent` смотрит
только на `graduation.get("all_passed")`.

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `training_loop.py` | Условие `result.graduated` для stage="1b" должно требовать non-regression на streak, не только `all_passed` на одном квартале |
| `stage_baseline.py::load_baseline` | Привести к строгости `stage1a_report.py::pick_baseline_run` — отказывать на baseline из непрошедших кварталов без явного переопределения |
| `tests/` | Регрессионный тест на точном сценарии этого прогона (см. раздел "Тест-кейсы") |

---

## Изменение 1: `training_loop.py` — выпуск требует устойчивой нерегрессии

### Текущее поведение (v1.1)

```python
# В run_quarters(), после каждого квартала:
if graduation.get("all_passed") and not result.graduated:
    result.graduated = True
    result.graduated_at_quarter = q_idx
    if stop_on_graduation:
        break
```

Это условие не учитывает `non_regression`, вычисленный в том же цикле
через `self._non_regression_for(fitness)` и сохранённый в
`QuarterResult.non_regression` — но не используемый для решения о
graduation.

### Требуемое поведение

Для `stage == "1a"` поведение не меняется — там `non_regression` всегда
`None` (нет baseline, нечего проверять), логика `all_passed` остаётся
единственным условием.

Для `stage == "1b"` graduation должен требовать:
1. `graduation.get("all_passed")` — как раньше
2. **И** `non_regression` не содержит `False` ни по одному критерию
   (или `non_regression is None`, если `stage_1a_baseline` не передан —
   это уже покрыто существующим предупреждением `--stage 1b requires
   --baseline-from`)
3. **И** это выполняется **на протяжении `min_streak` подряд идущих
   кварталов** (раздел 26.7: `min_streak=3` по умолчанию), а не на одном

```python
GRADUATION_MIN_STREAK = 3
"""Section 26.7: Stage 1b graduation must hold for this many consecutive
quarters, not trigger on the first lucky pass."""


def _quarter_qualifies(quarter: "QuarterResult") -> bool:
    """A quarter counts toward the graduation streak only if it passed
    AND did not buy that pass by regressing Stage 1a competence.

    For Stage 1a runs, non_regression is always None (no baseline to
    check against), so the check is a no-op and only all_passed matters —
    this keeps existing Stage 1a behaviour unchanged.
    """
    if not quarter.graduation.get("all_passed"):
        return False
    if quarter.non_regression is None:
        return True
    return not any(
        ok is False for ok in quarter.non_regression.values()
    )


# В run_quarters(), заменить блок graduation detection:
qualifying_streak = 0
for offset in range(...):
    # ... existing per-quarter computation, including non_regression ...

    quarter_result = QuarterResult(..., non_regression=self._non_regression_for(fitness))
    result.quarters.append(quarter_result)

    if _quarter_qualifies(quarter_result):
        qualifying_streak += 1
    else:
        qualifying_streak = 0

    if qualifying_streak >= GRADUATION_MIN_STREAK and not result.graduated:
        result.graduated = True
        # Graduated at the FIRST quarter of the qualifying streak, not the
        # last — this is when sustained competence actually began, and
        # matches how a resumed run should report it.
        result.graduated_at_quarter = quarter_result.quarter_index - GRADUATION_MIN_STREAK + 1
        if stop_on_graduation:
            break
```

### Важное уточнение: `qualifying_streak` должен переживать resume

Если обучение прерывается чекпоинтом посреди накопления streak, streak
не должен обнуляться при `--resume-from`. Нужно вычислять
`qualifying_streak` **из истории `result.quarters`**, а не хранить как
отдельное поле трейнера — тогда resume автоматически корректен:

```python
def _current_qualifying_streak(quarters: List["QuarterResult"]) -> int:
    """Recompute the streak from history instead of tracking it as
    mutable trainer state, so a checkpoint resume gets the right answer
    for free — the streak is a pure function of the quarters already run.
    """
    streak = 0
    for quarter in reversed(quarters):
        if _quarter_qualifies(quarter):
            streak += 1
        else:
            break
    return streak
```

Использовать `_current_qualifying_streak(result.quarters)` в начале
каждого вызова `run_quarters`/`run_stage1b_persistent`, вместо
инкрементального счётчика.

### Не менять

- `_non_regression_for()` — вычисляется корректно, не трогать
- `graduation_report()` в `procurement_fitness.py` — `all_passed` там
  остаётся честным "прошёл ли этот конкретный квартал", это не место
  для streak-логики (streak — свойство последовательности кварталов,
  не одного квартала)
- Логика Stage 1a — изменение затрагивает только путь `stage == "1b"`

---

## Изменение 2: `stage_baseline.py::load_baseline` — симметричная строгость

### Текущая асимметрия

`stage1a_report.py::pick_baseline_run` **отказывается** писать baseline,
если нет ни одного graduated-прогона:

```python
if chosen is None:
    print("\nNo graduated run: refusing to write a baseline.")
    return 1
```

Но `stage_baseline.py::load_baseline`, когда получает сырой список
результатов (не файл baseline, а `results/stage1a_seedN.json` напрямую
через `--baseline-from`), молча вызывает `compute_stage_1a_baseline`,
который **сам** переходит к запасному варианту «все кварталы» вместо только успешных, без
отказа:

```python
def compute_stage_1a_baseline(quarters, last_n=BASELINE_QUARTERS):
    good = successful_quarters(quarters)
    from_successful = bool(good)
    selected = (good or quarters)[-max(1, int(last_n)):]  # <- тихий fallback
```

Оператор может случайно передать в `--baseline-from` прогон, где агент
Stage 1a вообще не graduated, и получить baseline, посчитанный по
проваленным кварталам — non-regression guard в Stage 1b тогда защищает
не "типичную компетентность", а "среднюю производительность
непрошедшего курс агента", что бессмысленно.

### Требуемое поведение

`load_baseline`, когда строит baseline из сырого списка результатов
(`isinstance(data, list)` — путь без явного `stage_1a_baseline` ключа),
должен требовать `from_successful_quarters=True`, иначе бросать явную
ошибку, а не тихо деградировать:

```python
def load_baseline(path: str) -> Dict[str, float]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if isinstance(data, list):
        payload = compute_stage_1a_baseline(data)
        if not payload["from_successful_quarters"]:
            raise ValueError(
                f"{path} contains no graduated Stage 1a quarters. "
                f"Refusing to build a non-regression baseline from failed "
                f"quarters — this would guard Stage 1b against nothing. "
                f"Run more Stage 1a quarters, or use "
                f"stage1a_report.py --write-baseline on a run that "
                f"actually graduated."
            )
        return dict(payload["stage_1a_baseline"])

    # ... existing mapping-based path unchanged ...
```

### Не менять

- `compute_stage_1a_baseline()` сам по себе — его сигнатура и fallback
  поведение остаются как есть, потому что `stage1a_report.py::summarize_run`
  легитимно использует его для диагностической таблицы (раздел 27.2),
  где показ "baseline даже из неудачного прогона" — осмысленная
  диагностика, не финальное решение. Строгость нужна только на границе
  `load_baseline`, где результат идёт прямо в `check_non_regression`.

---

## Тест-кейсы

### `tests/test_graduation_non_regression.py` (новый файл)

```python
"""Regression test built directly from the v1.1 run that exposed the gap:
Stage 1b graduated on quarter 31 while stockout_avoidance was regressed
in every one of the 20 Stage 1b quarters observed."""

import pytest
from nowa_sandbox.training_loop import (
    QuarterResult, SandboxTrainingResult,
    GRADUATION_MIN_STREAK, _quarter_qualifies, _current_qualifying_streak,
)


def _fake_quarter(index, all_passed, non_regression=None):
    from nowa_sandbox.procurement_fitness import ProcurementFitnessVector
    vector = ProcurementFitnessVector(
        cost_efficiency=0.5, stockout_avoidance=0.5, budget_discipline=1.0,
        supplier_diversification=0.5, decision_consistency=0.5,
        reaction_to_risk_events=0.5, n_days=90, n_orders=90,
    )
    return QuarterResult(
        quarter_index=index,
        fitness=vector,
        graduation={"all_passed": all_passed, "stage": "1b"},
        world_summary={},
        processing_time_s=0.0,
        non_regression=non_regression,
    )


class TestQuarterQualifies:

    def test_fails_all_passed_disqualifies(self):
        q = _fake_quarter(1, all_passed=False, non_regression={"stockout_avoidance": True})
        assert _quarter_qualifies(q) is False

    def test_regressed_criterion_disqualifies_even_if_all_passed(self):
        """The exact bug: all_passed=True but stockout_avoidance regressed."""
        q = _fake_quarter(
            31, all_passed=True,
            non_regression={
                "cost_efficiency": False, "stockout_avoidance": False,
                "budget_discipline": True, "reaction_to_risk_events": True,
            },
        )
        assert _quarter_qualifies(q) is False

    def test_all_passed_with_clean_non_regression_qualifies(self):
        q = _fake_quarter(
            1, all_passed=True,
            non_regression={
                "cost_efficiency": True, "stockout_avoidance": True,
                "budget_discipline": True, "reaction_to_risk_events": True,
            },
        )
        assert _quarter_qualifies(q) is True

    def test_stage_1a_none_non_regression_qualifies_on_all_passed_alone(self):
        """Stage 1a has no baseline to check; non_regression is None by
        design and must not block graduation there."""
        q = _fake_quarter(1, all_passed=True, non_regression=None)
        assert _quarter_qualifies(q) is True


class TestQualifyingStreak:

    def test_streak_resets_on_disqualifying_quarter(self):
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": True}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
            _fake_quarter(3, True, {"stockout_avoidance": False}),  # regressed
        ]
        assert _current_qualifying_streak(quarters) == 0

    def test_streak_counts_trailing_run_only(self):
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": False}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
            _fake_quarter(3, True, {"stockout_avoidance": True}),
        ]
        assert _current_qualifying_streak(quarters) == 2

    def test_reproduces_actual_run_never_reaches_min_streak(self):
        """Sequence taken from the real Stage 1b run (quarters 31-50):
        all_passed pattern is T T F T F F T T F T T T F F T F F T F F,
        with stockout_avoidance regressed in all 20. Max observed streak
        under the old (broken) rule was 2 quarters (Q31-32, Q41-42) —
        under the fix, since every quarter has stockout_avoidance
        regressed, the qualifying streak must never exceed 0.
        """
        all_passed_pattern = [
            True, True, False, True, False, False, True, True, False,
            True, True, True, False, False, True, False, False, True,
            False, False,
        ]
        quarters = [
            _fake_quarter(
                31 + i, all_passed,
                {"cost_efficiency": True, "stockout_avoidance": False,
                 "budget_discipline": True, "reaction_to_risk_events": True},
            )
            for i, all_passed in enumerate(all_passed_pattern)
        ]
        assert _current_qualifying_streak(quarters) == 0


class TestGraduationRequiresStreak:

    def test_single_qualifying_quarter_does_not_graduate(self, mini_world_config):
        """One good quarter is not enough — GRADUATION_MIN_STREAK requires
        several in a row, per section 26.7."""
        # Built via a trainer double whose fitness_evaluator always returns
        # a passing, non-regressed vector for exactly one quarter and then
        # a regressed one — asserts result.graduated stays False after
        # quarter 1 and result.graduated_at_quarter is None.
        ...

    def test_sustained_streak_graduates_at_streak_start(self):
        """When GRADUATION_MIN_STREAK consecutive quarters all qualify,
        graduated_at_quarter should be the FIRST quarter of that streak,
        not the last — this is when sustained competence began."""
        ...


class TestResumePreservesStreak:

    def test_streak_recomputed_from_history_not_reset_on_resume(self):
        """A checkpoint saved mid-streak, then resumed, must not lose
        credit for quarters already run — streak is a pure function of
        result.quarters, never trainer-local mutable state."""
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": True}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
        ]
        result = SandboxTrainingResult(quarters=quarters)
        assert _current_qualifying_streak(result.quarters) == 2
        # A subsequent qualifying quarter must bring the streak to 3 and
        # trigger graduation, exactly as if the run had never stopped.
```

### `tests/test_stage_baseline_strictness.py` (новый файл)

```python
"""load_baseline must be as strict as stage1a_report.py's
--write-baseline: refuse rather than silently build a guard from
non-graduated quarters."""

import json
import pytest
from nowa_sandbox.stage_baseline import load_baseline


def test_refuses_baseline_from_all_failed_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": i,
            "fitness": {
                "cost_efficiency": 0.3, "stockout_avoidance": 0.1,
                "budget_discipline": 1.0, "reaction_to_risk_events": 0.2,
            },
            "graduation": {"all_passed": False},
        }
        for i in range(1, 6)
    ]
    path = tmp_path / "all_failed.json"
    path.write_text(json.dumps(quarters))

    with pytest.raises(ValueError, match="no graduated Stage 1a quarters"):
        load_baseline(str(path))


def test_accepts_baseline_from_graduated_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": 1,
            "fitness": {
                "cost_efficiency": 0.8, "stockout_avoidance": 0.9,
                "budget_discipline": 1.0, "reaction_to_risk_events": 0.7,
            },
            "graduation": {"all_passed": True},
        }
    ]
    path = tmp_path / "graduated.json"
    path.write_text(json.dumps(quarters))

    baseline = load_baseline(str(path))
    assert baseline["cost_efficiency"] == 0.8


def test_curated_baseline_file_unaffected(tmp_path):
    """The mapping-based path (a file already produced by
    stage1a_report.py --write-baseline) must keep working unchanged."""
    payload = {
        "stage_1a_baseline": {
            "cost_efficiency": 0.7523, "stockout_avoidance": 0.9493,
            "budget_discipline": 1.0, "reaction_to_risk_events": 0.7894,
        },
        "computed_from_quarters": [6, 9, 19, 23, 26],
        "from_successful_quarters": True,
    }
    path = tmp_path / "curated.json"
    path.write_text(json.dumps(payload))

    baseline = load_baseline(str(path))
    assert baseline["stockout_avoidance"] == 0.9493
```

---

## Ограничения (не подлежат обходу)

| # | Ограничение |
|---|---|
| **NR1** | Stage 1a graduation логика **не изменяется** этим патчем — `non_regression is None` там всегда, и `_quarter_qualifies` для Stage 1a эквивалентен старому `graduation.get("all_passed")` |
| **NR2** | `qualifying_streak` вычисляется из `result.quarters` (чистая функция), не хранится как изменяемое состояние трейнера — иначе возобновление после контрольной точки ломает подсчёт |
| **NR3** | `graduated_at_quarter` указывает на **первый** квартал streak'а, не последний — это момент начала устойчивой компетентности |
| **NR4** | `load_baseline` строгость применяется **только** к пути "сырой список результатов"; curated baseline-файлы (уже прошедшие через `stage1a_report.py --write-baseline`) не затрагиваются |
| **NR5** | `compute_stage_1a_baseline()` как функция остаётся permissive (для диагностики раздела 27.2) — строгость добавляется только на границе `load_baseline` |

---

## Проверка после реализации

Перезапустить точно тот же Stage 1b сценарий (тот же `stage_1a_baseline`,
тот же seed) и убедиться:

- [ ] `result.graduated` остаётся `False` на протяжении всех 20 показанных
      кварталов (streak ни разу не достигает 3 при `stockout_avoidance`,
      регрессированном во всех кварталах)
- [ ] Лог явно показывает `qualifying_streak` после каждого квартала —
      полезно для отладки, не только для итогового решения
- [ ] `test_reproduces_actual_run_never_reaches_min_streak` зелёный
- [ ] Попытка `--baseline-from results/stage1a_seed_never_graduated.json`
      (гипотетический прогон, где Stage 1a не прошёл ни одного квартала)
      завершается явной ошибкой, не тихим построением бесполезного baseline

---

*Патч v1.1.1. Обоснован эмпирически данными реального прогона.
Готов к передаче агенту-разработчику.*
