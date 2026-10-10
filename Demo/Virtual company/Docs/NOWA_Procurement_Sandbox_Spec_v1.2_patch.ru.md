# NOWA Procurement Sandbox — Патч v1.2

English version: [NOWA_Procurement_Sandbox_Spec_v1.2_patch.en.md](NOWA_Procurement_Sandbox_Spec_v1.2_patch.en.md)

## Аннотация

Патч v1.2 принимается после того, как логика серии v1.1.1 на семени 1 подтвердилась: допускающая серия стадии 1b за пятьдесят кварталов не превысила единицы, и `result.graduated` остался ложным. Тот же материал показал, что `stockout_avoidance` на стадии 1a (семя 1, кварталы 1–30) не образует монотонного тренда. Квартал 1 даёт 0,000, квартал 30 — 0,398; соседние шаги расходятся как 0,419 → 0,995 и 0,995 → 0,204. Прогоны семян 11 и 14 не дали ни одного выпущенного квартала из тридцати. Документ объясняет разброс тем, что каждый квартал стадии 1a порождает новый профиль спроса, шоков и точек перезаказа, и сложность задачи меняется сильнее, чем различимый прирост компетентности за тридцать итераций.

Базовая линия v1.1 усредняла последние успешные кварталы. Для избежания дефицита на семени 1 это кварталы 6, 9, 19, 23 и 26 со значениями от 0,897 до 1,000 и средним 0,9493, то есть верхний хвост распределения. Пол 0,854 затем помечал как регрессию колебания, которые на стадии 1b остаются в том же широком диапазоне и не являются следствием персистентности поставщиков. Патч заменяет расчёт медианой по всем кварталам (`median_all`), требует не менее пятнадцати кварталов и публикует межквартильный размах. Пол равен минимуму из произведения медианы на 0,9 и разности медианы и размаха: при нулевом размахе, как у наблюдавшейся бюджетной дисциплины, сохраняется множитель 0,9, а при большом размахе пол опускается к обычному размаху стадии 1a. Метод `mean_best` остаётся для сравнения в отчёте и отказывается записываться как охраняющая базовая линия. Критерий с размахом выше 0,3 помечается как высоко волатильный.

Функции проверки нерегрессии и подсчёта серии не меняются; меняется число, которое им передают. Вопросы о тренде на масштабе ста и более кварталов, о работе `sleep_cycle` между соседними кварталами и о калибровке `demand_shock_probability` и `late_delivery_probability_base`, обе равные 0,05, отложены. Для первого из них спецификация предлагает отдельный скрипт скользящего среднего с окном 10 и наклона линейной регрессии по сглаженному ряду, с порогами наклона ±0,002 для вердиктов обучения, отсутствия тренда и снижения. Скрипт не входит в пакет `nowa_sandbox`.

---

**Базовые документы:**
NOWA_Procurement_Sandbox_Spec.md (v1.0)
NOWA_Procurement_Sandbox_Spec_v1.1_patch.ru.md (Stage 1a/1b curriculum)
NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.md (non-regression streak fix)

**Статус:** Ready for implementation — диагностика и фикс baseline
methodology, обнаруженный после успешной проверки патча v1.1.1

---

## Эмпирическое обоснование

Патч v1.1.1 сработал правильно: `qualifying_streak` для Stage 1b (seed1,
50 кварталов) не превысил 1, `result.graduated = False`. Это подтверждает,
что streak-логика реализована корректно (раздел проверки v1.1.1 закрыт).

Но данные вскрыли проблему на уровень выше: **сам `stockout_avoidance`
не показывает тенденции обучения на протяжении 30 кварталов Stage 1a**.

Полная последовательность (seed1, кварталы 1–30):

```
Q 1: 0.000   Q 7: 0.197   Q13: 0.376   Q19: 0.897   Q25: 0.090
Q 2: 0.745   Q 8: 0.419   Q14: 0.000   Q20: 0.741   Q26: 0.919
Q 3: 0.000   Q 9: 0.995   Q15: 0.000   Q21: 0.000   Q27: 0.448
Q 4: 0.178   Q10: 0.204   Q16: 0.000   Q22: 0.716   Q28: 0.000
Q 5: 0.456   Q11: 0.481   Q17: 0.096   Q23: 1.000   Q29: 0.000
Q 6: 0.936   Q12: 0.835   Q18: 0.000   Q24: 0.216   Q30: 0.398
```

Нет монотонного или даже слабо возрастающего тренда: квартал 1 (0.000)
и квартал 30 (0.398) сопоставимы по качеству; лучшие результаты (0.995,
1.000) появляются в кварталах 9 и 23 без видимой связи с накопленным
опытом. Дисперсия между соседними кварталами огромна (Q8→Q9:
0.419→0.995; Q9→Q10: 0.995→0.204).

Это подтверждено и на двух дополнительных прогонах (seed11, seed14):
**0 из 30 кварталов graduated** в обоих — то есть даже разовое попадание
в "удачное окно" (как было у seed1) не гарантировано при других seed.

### Механизм, объясняющий волатильность

Constraint V1 (раздел 8) требует нового `ProcurementWorld` каждый квартал —
это осознанное архитектурное решение (не даёт агенту привязываться к
конкретным поставщикам в Stage 1a). Побочный эффект: каждый квартал —
это не только новые поставщики, но и новый случайный **профиль спроса**
(`demand_volatility`, момент `demand_shock`, комбинация товаров с низким
`reorder_point`). Сложность самого квартала как задачи варьируется сильнее,
чем растёт компетентность агента за 30 итераций — поэтому наблюдаемая
производительность выглядит как шум, наложенный на неразличимый тренд,
а не как кривая обучения.

### Как это ломает non-regression baseline (v1.1.1)

`compute_stage_1a_baseline()` берёт **5 лучших прошедших** кварталов
(для seed1: Q6, Q9, Q19, Q23, Q26, значения `stockout_avoidance` в
диапазоне 0.897–1.000) — это верхний хвост распределения, не типичное
поведение. `stage_1a_baseline["stockout_avoidance"] = 0.9493` — почти
максимум из всей серии.

Non-regression floor = 0.9493 × 0.9 = 0.854. В Stage 1b (кварталы 31–50)
`stockout_avoidance` продолжает колебаться в том же широком диапазоне,
что и в Stage 1a (0.292–1.000) — **та же самая изначальная волатильность
задачи**, не деградация от персистентности поставщиков. Но guard
интерпретирует любое падение ниже 0.854 как "регрессию", хотя агент,
возможно, никогда не работал стабильно выше этого уровня.

**Вывод:** нельзя доверять non-regression guard, пока baseline построен
по нерепрезентативной выборке (cherry-picked лучшие кварталы), а не по
типичной производительности агента.

---

## Два независимых направления фикса

Эти направления не взаимоисключающие — вероятно, нужны оба, но в
указанном порядке приоритета.

### Направление A (приоритет 1): честный baseline

Изменить `compute_stage_1a_baseline()` так, чтобы он отражал **типичную**,
а не **пиковую** производительность. Не переопределяет саму физику мира —
только то, как строится ожидание для non-regression guard.

### Направление B (приоритет 2, требует отдельного анализа): стабильность самого Stage 1a

Если после направления A всё ещё видно, что агент не показывает тренда
обучения даже в среднем/медианном виде — проблема глубже baseline, речь
о том, усваивает ли агент вообще что-то устойчивое между кварталами
(вопрос к работе `sleep_manager.sleep_cycle()` и seed-инициализации,
не к метрикам). Это выходит за рамки данного патча — фиксируется как
открытый вопрос (раздел "Открытые вопросы" ниже), не как немедленная
задача.

---

## Затронутые файлы (Направление A)

| Файл | Тип изменения |
|---|---|
| `stage_baseline.py::compute_stage_1a_baseline` | Заменить "среднее по 5 лучшим" на статистику, устойчивую к выбросам, по **всем** кварталам, не только прошедшим |
| `stage_baseline.py::load_baseline` | Обновить сообщение об ошибке (раздел v1.1.1 NR4) под новую методологию |
| `stage1a_report.py` | Обновить вывод отчёта — показывать не только "лучшие 5", но и полное распределение по всем 30 кварталам |
| `tests/` | Тесты на новую методологию baseline, включая regression-тест на данных из этого прогона |

---

## Изменение 1: `compute_stage_1a_baseline` — median-of-all вместо mean-of-best

### Текущее поведение (v1.1)

```python
def compute_stage_1a_baseline(quarters, last_n=BASELINE_QUARTERS):
    good = successful_quarters(quarters)   # только all_passed=True
    from_successful = bool(good)
    selected = (good or quarters)[-max(1, int(last_n)):]  # последние N успешных
    # ... затем среднее по selected
```

Это даёт baseline = "среднее из лучших N попыток", системно оптимистичный
показатель.

### Требуемое поведение

Использовать **медиану по всем кварталам** (не только успешным), с явным
указанием на волатильность (межквартильный размах) в отчёте — чтобы
человек, читающий baseline, видел не только число, но и его надёжность.

```python
import statistics

MIN_QUARTERS_FOR_BASELINE = 15
"""Below this, a median is too noisy to trust as a floor reference."""


def compute_stage_1a_baseline(
    quarters: List[dict],
    method: str = "median_all",
) -> dict:
    """
    method="median_all" (new default): median across ALL quarters run,
    successful or not. Represents typical performance, not peak performance.
    Robust to the kind of quarter-to-quarter volatility observed in the
    real Stage 1a runs (values from 0.000 to 1.000 with no visible trend).

    method="mean_best" (old v1.1 behaviour, kept for comparison/diagnostics
    only — NOT recommended as the value fed to a non-regression guard):
    mean of the last N quarters that passed all_passed. Retained under this
    name so stage1a_report.py can still show it side by side for context.
    """
    if len(quarters) < MIN_QUARTERS_FOR_BASELINE:
        raise ValueError(
            f"Only {len(quarters)} quarters available; need at least "
            f"{MIN_QUARTERS_FOR_BASELINE} for a median baseline stable "
            f"enough to gate Stage 1b. Run more Stage 1a quarters."
        )

    criteria = STAGE_1A_CRITERIA  # cost_efficiency, stockout_avoidance,
                                    # budget_discipline, reaction_to_risk_events
    baseline = {}
    spread = {}
    for criterion in criteria:
        values = [safe_float(q["fitness"].get(criterion, 0.0), 0.0) for q in quarters]
        baseline[criterion] = statistics.median(values)
        # Interquartile range as an honest volatility signal alongside
        # the point estimate — a criterion with IQR > 0.3 is not "regressed"
        # so much as "inherently noisy", and Stage 1b tooling should say so.
        sorted_values = sorted(values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[(3 * len(sorted_values)) // 4]
        spread[criterion] = q3 - q1

    passed_count = sum(1 for q in quarters if q.get("graduation", {}).get("all_passed"))

    return {
        "stage_1a_baseline": baseline,
        "stage_1a_spread_iqr": spread,
        "method": "median_all",
        "n_quarters_used": len(quarters),
        "n_quarters_passed": passed_count,
        "computed_from_quarters": [q["quarter_index"] for q in quarters],
    }
```

### Non-regression floor должен учитывать volatility, не только точку

Раздел 26.5 (v1.1) определял `NON_REGRESSION_FLOOR = 0.9` как фиксированный
множитель. Это имело смысл при оптимистичном "mean of best" baseline —
но с честным median-baseline фиксированный множитель 0.9 всё ещё может
быть слишком строгим для критериев с большим IQR (`stockout_avoidance`
в этих данных имеет размах от 0 до 1 — почти весь диапазон).

```python
def non_regression_floor(
    median_value: float,
    iqr: float,
    base_multiplier: float = 0.9,
) -> float:
    """
    For low-volatility criteria (small IQR, e.g. budget_discipline which
    sat at 1.0 in every quarter observed), the floor stays close to
    median * 0.9, matching v1.1 behaviour.

    For high-volatility criteria (large IQR, e.g. stockout_avoidance with
    IQR observed around 0.5-0.6), the floor relaxes toward
    median - iqr, acknowledging that swings of this size are the agent's
    normal operating range, not a sign that persistent suppliers made
    things worse.
    """
    strict_floor = median_value * base_multiplier
    volatility_floor = median_value - iqr
    return max(0.0, min(strict_floor, volatility_floor))
```

**Обоснование этой формулы, не произвольный выбор:** для
`budget_discipline` (наблюдаемый IQR ≈ 0, все значения 1.0)
`volatility_floor ≈ median`, строже чем `strict_floor` — эта формула
берёт `min()`, так что для стабильных критериев ничего не меняется
относительно v1.1. Для `stockout_avoidance` (наблюдаемый IQR ≈ 0.5–0.6)
`volatility_floor` заметно ниже `strict_floor`, что и требуется — не
наказывать агента за колебания, которые были нормой ещё в Stage 1a.

---

## Изменение 2: `stage1a_report.py` — показывать распределение, не только точку

Текущий вывод (v1.1) показывает только `stage_1a_baseline` как готовые
числа. Добавить явную визуализацию волатильности в текстовом отчёте:

```python
def print_baseline_summary(payload: dict) -> None:
    print(f"\n=== Stage 1a baseline (method={payload['method']}) ===")
    print(f"Quarters used: {payload['n_quarters_used']} "
          f"(passed: {payload['n_quarters_passed']})")
    print()
    for criterion in STAGE_1A_CRITERIA:
        median = payload["stage_1a_baseline"][criterion]
        iqr = payload["stage_1a_spread_iqr"][criterion]
        volatility_flag = " ⚠️ HIGH VOLATILITY" if iqr > 0.3 else ""
        print(f"  {criterion:24s} median={median:.4f}  IQR={iqr:.4f}{volatility_flag}")

    high_vol = [c for c in STAGE_1A_CRITERIA if payload["stage_1a_spread_iqr"][c] > 0.3]
    if high_vol:
        print(f"\n⚠️  {len(high_vol)} criteria show high quarter-to-quarter "
              f"volatility: {', '.join(high_vol)}.")
        print(f"    This is normal Stage 1a variance, not regression — the "
              f"non-regression floor accounts for it (see spec v1.2).")
```

---

## Тест-кейсы

### `tests/test_baseline_methodology.py` (новый файл)

```python
"""Regression-anchored on the actual seed1 run: stockout_avoidance
ranged 0.000-1.000 across 30 quarters with no visible learning trend."""

import pytest
import statistics
from nowa_sandbox.stage_baseline import (
    compute_stage_1a_baseline, non_regression_floor,
    MIN_QUARTERS_FOR_BASELINE,
)


SEED1_STOCKOUT_AVOIDANCE = [
    0.000, 0.745, 0.000, 0.178, 0.456, 0.936, 0.197, 0.419, 0.995, 0.204,
    0.481, 0.835, 0.376, 0.000, 0.000, 0.000, 0.096, 0.000, 0.897, 0.741,
    0.000, 0.716, 1.000, 0.216, 0.090, 0.919, 0.448, 0.000, 0.000, 0.398,
]


def _fake_quarters(stockout_values, passed_indices=None):
    passed_indices = passed_indices or set()
    return [
        {
            "quarter_index": i + 1,
            "fitness": {
                "cost_efficiency": 0.6, "stockout_avoidance": v,
                "budget_discipline": 1.0, "reaction_to_risk_events": 0.6,
            },
            "graduation": {"all_passed": (i + 1) in passed_indices},
        }
        for i, v in enumerate(stockout_values)
    ]


class TestMedianVsMeanOfBest:

    def test_median_baseline_far_below_mean_of_best(self):
        """The exact discrepancy that caused the false regression signal:
        cherry-picked best-5 mean was 0.9493, but median across all 30
        quarters is much lower."""
        quarters = _fake_quarters(
            SEED1_STOCKOUT_AVOIDANCE,
            passed_indices={6, 9, 19, 23, 26},
        )
        payload = compute_stage_1a_baseline(quarters)
        median_value = payload["stage_1a_baseline"]["stockout_avoidance"]
        old_mean_of_best = statistics.mean(
            [SEED1_STOCKOUT_AVOIDANCE[i - 1] for i in (6, 9, 19, 23, 26)]
        )
        assert median_value < old_mean_of_best - 0.3, (
            f"median={median_value:.4f} should be well below the old "
            f"cherry-picked mean={old_mean_of_best:.4f}"
        )

    def test_raises_below_minimum_quarters(self):
        quarters = _fake_quarters(SEED1_STOCKOUT_AVOIDANCE[:10])
        with pytest.raises(ValueError, match="at least"):
            compute_stage_1a_baseline(quarters)

    def test_high_iqr_flagged_in_spread(self):
        quarters = _fake_quarters(SEED1_STOCKOUT_AVOIDANCE)
        payload = compute_stage_1a_baseline(quarters)
        assert payload["stage_1a_spread_iqr"]["stockout_avoidance"] > 0.3


class TestNonRegressionFloorAccountsForVolatility:

    def test_stable_criterion_floor_matches_v1_1(self):
        """budget_discipline sat at 1.0 in every observed quarter — for a
        near-zero IQR criterion, the new floor should match the old
        median * 0.9 behaviour almost exactly."""
        floor = non_regression_floor(median_value=1.0, iqr=0.0)
        assert abs(floor - 0.9) < 1e-6

    def test_volatile_criterion_floor_relaxes(self):
        """stockout_avoidance with a large IQR should get a floor well
        below median * 0.9 — the volatility itself is normal, not a
        regression signal."""
        median_value = statistics.median(SEED1_STOCKOUT_AVOIDANCE)
        iqr = 0.6  # observed magnitude order
        floor = non_regression_floor(median_value, iqr)
        strict_floor = median_value * 0.9
        assert floor < strict_floor

    def test_floor_never_negative(self):
        floor = non_regression_floor(median_value=0.1, iqr=0.5)
        assert floor >= 0.0


class TestStage1bReinterpretedWithNewFloor:

    def test_stage1b_run_fewer_false_regressions_under_new_floor(self):
        """Re-run the non_regression check for the real Stage 1b quarters
        (31-50) using the volatility-aware floor and confirm fewer
        quarters are flagged as regressed on stockout_avoidance than
        under the old fixed 0.9 multiplier — the point of this patch."""
        stage1b_stockout = [
            0.810, 0.292, 0.761, 0.870, 0.784, 0.840, 0.854, 0.912, 0.860,
            0.803, 0.696, 0.909, 0.994, 0.908, 0.931, 0.827, 0.938, 0.942,
            0.900, 0.925,
        ]
        median_value = statistics.median(SEED1_STOCKOUT_AVOIDANCE)
        iqr = 0.6
        new_floor = non_regression_floor(median_value, iqr)
        old_floor = 0.9493 * 0.9  # v1.1 mean-of-best baseline * 0.9

        old_regressions = sum(1 for v in stage1b_stockout if v < old_floor)
        new_regressions = sum(1 for v in stage1b_stockout if v < new_floor)

        assert new_regressions < old_regressions
```

---

## Ограничения

| # | Ограничение |
|---|---|
| **B1** | `method="mean_best"` сохраняется в коде (не удаляется) только для диагностического сравнения в `stage1a_report.py` — **никогда** не используется как значение, идущее в `check_non_regression` |
| **B2** | `MIN_QUARTERS_FOR_BASELINE = 15` — с меньшим числом кварталов медиана статистически ненадёжна; `compute_stage_1a_baseline` обязан отказать, не тихо посчитать по малой выборке |
| **B3** | `non_regression_floor()` — чистая функция от `(median, iqr)`, не имеет побочных эффектов, не зависит от порядка кварталов |
| **B4** | Изменение затрагивает только методологию **вычисления** baseline; `check_non_regression()` (v1.1) и streak-логика (v1.1.1) не меняются — они уже корректно используют переданный им floor, просто раньше floor был построен неверно |

---

## Открытые вопросы (Направление B — не решается этим патчем)

1. **Показывает ли агент вообще тренд обучения, если усреднять грубее?**
   30 отдельных кварталов — мало данных для статистики; возможно, тренд
   есть, но виден только на масштабе 100+ кварталов. Рекомендация: перед
   дальнейшей калибровкой прогнать 100 кварталов Stage 1a на одном seed
   и посчитать скользящее среднее (окно 10 кварталов) — если тренд
   отсутствует и там, вопрос уже не про размер выборки.

2. **Работает ли `sleep_manager.sleep_cycle()` так, как задумано?**
   Хаотичность между соседними кварталами (Q8→Q9: 0.419→0.995) не
   исключает, что консолидация происходит, но не удерживает полезные
   паттерны между кварталами из-за конфликта с тем, что *остальные*
   условия мира (спрос, шоки) меняются сильнее, чем то, что агент
   способен обобщить. Это требует профилирования hippocampus/cortex
   между конкретными кварталами (например, Q8 vs Q9), не входит в
   объём данного патча.

3. **Правильно ли откалиброван `demand_shock_probability=0.05` и
   `late_delivery_probability_base=0.05`?** Возможно, дисперсия сложности
   кварталов сама по себе слишком велика для того, чтобы за 30 попыток
   можно было увидеть устойчивое обучение — это вопрос к параметрам
   `ProcurementWorldConfig`, не к коду fitness/baseline.

Эти три вопроса — кандидаты на патч v1.3, после того как будет собрано
больше диагностических данных (пункт 1 выше — самый дешёвый способ начать).

---

*Патч v1.2. Обоснован эмпирически данными трёх Stage 1a прогонов
(seed1, seed11, seed14) и одного Stage 1b прогона под патчем v1.1.1.
Меняет методологию расчёта baseline, не саму логику graduation/streak.*

---

## Изменения CLI

### `stage1a_report.py`

```python
parser.add_argument(
    "--baseline-method",
    choices=["median_all", "mean_best"],
    default="median_all",
    help="median_all (recommended): robust to quarter-to-quarter volatility, "
         "used for --write-baseline. mean_best: legacy v1.1 behaviour, shown "
         "for comparison only, refuses to be written as a guard baseline "
         "(see B1).",
)
```

Если `--baseline-method mean_best` передан вместе с `--write-baseline` —
явный отказ, не тихая деградация:

```python
if args.write_baseline and args.baseline_method == "mean_best":
    print(
        "Refusing to write a baseline computed with method=mean_best. "
        "This method reflects peak performance from cherry-picked quarters, "
        "not typical behaviour, and produces a non-regression floor that "
        "flags normal Stage 1a variance as regression (see patch v1.2). "
        "Use --baseline-method median_all, or omit --write-baseline to "
        "view mean_best for comparison only."
    )
    return 1
```

### `run_sandbox.py`

Нет изменений сигнатуры — `--baseline-from` продолжает принимать путь к
файлу, произведённому `stage1a_report.py --write-baseline`; выбор метода
инкапсулирован там, `load_baseline()` просто читает готовое значение.

---

## Критерии готовности патча v1.2

- [ ] `compute_stage_1a_baseline` по умолчанию использует `median_all`,
      бросает `ValueError` при `len(quarters) < 15`
- [ ] `non_regression_floor()` реализована как чистая функция, покрыта
      тестами на стабильный (`budget_discipline`) и волатильный
      (`stockout_avoidance`) случаи
- [ ] Повторный пересчёт non-regression для реальных данных Stage 1b
      (кварталы 31–50, seed1) под новым floor даёt строго меньше
      ложных регрессий, чем под floor из v1.1 — тест
      `test_stage1b_run_fewer_false_regressions_under_new_floor` зелёный
- [ ] `stage1a_report.py` печатает IQR и флаг `HIGH VOLATILITY` для
      каждого критерия с IQR > 0.3
- [ ] Попытка `--write-baseline --baseline-method mean_best` завершается
      явным отказом с кодом возврата 1
- [ ] Существующие тесты `test_stage_baseline_strictness.py` (патч
      v1.1.1) остаются зелёными без изменений — строгость на "нет
      graduated кварталов вообще" не связана с выбором метода
      усреднения и должна работать одинаково для обоих

---

## Диагностический инструмент для Направления B (следующий шаг после этого патча)

Открытый вопрос 1 ("показывает ли агент тренд обучения на большем
масштабе") — самый дешёвый способ продвинуться, не требует изменений
кода fitness/baseline, только новый анализирующий скрипт поверх уже
существующего `run_sandbox.py`.

### `tools/trend_diagnostic.py` (новый файл, не часть основного пакета)

```python
"""Moving-average trend diagnostic for Stage 1a runs.

Not part of nowa_sandbox itself — a standalone analysis script that reads
an existing results JSON (or triggers a longer run) and reports whether
per-criterion performance shows any learning trend when smoothed, or
remains pure noise even at 100+ quarters.
"""

import argparse
import json
import statistics
from pathlib import Path
from typing import List


def moving_average(values: List[float], window: int = 10) -> List[float]:
    if len(values) < window:
        return []
    return [
        statistics.mean(values[i : i + window])
        for i in range(len(values) - window + 1)
    ]


def trend_slope(smoothed: List[float]) -> float:
    """Simple linear regression slope over the smoothed series.
    Near-zero slope with the raw series noisy = no learning signal.
    Clearly positive slope = agent is improving despite per-quarter noise.
    """
    n = len(smoothed)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(smoothed)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(smoothed))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


def analyze(quarters: List[dict], window: int = 10) -> None:
    from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

    print(f"=== Trend diagnostic ({len(quarters)} quarters, window={window}) ===\n")
    for criterion in STAGE_1A_CRITERIA:
        raw = [q["fitness"][criterion] for q in quarters]
        smoothed = moving_average(raw, window)
        if not smoothed:
            print(f"{criterion}: not enough quarters for window={window}")
            continue
        slope = trend_slope(smoothed)
        raw_std = statistics.pstdev(raw)
        smoothed_std = statistics.pstdev(smoothed) if len(smoothed) > 1 else 0.0
        verdict = (
            "LEARNING TREND" if slope > 0.002 else
            "NO CLEAR TREND" if abs(slope) <= 0.002 else
            "DECLINING TREND"
        )
        print(
            f"{criterion:24s} raw_std={raw_std:.3f}  "
            f"smoothed_std={smoothed_std:.3f}  slope={slope:+.5f}  [{verdict}]"
        )


def main():
    parser = argparse.ArgumentParser(description="Diagnose Stage 1a learning trend.")
    parser.add_argument("results_json", help="Path to a Stage 1a results file.")
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args()

    quarters = json.loads(Path(args.results_json).read_text())
    analyze(quarters, window=args.window)


if __name__ == "__main__":
    main()
```

### Использование

```bash
# Сначала собрать больше данных, чем 30 кварталов — рекомендация
# открытого вопроса 1 (100+ кварталов на одном seed):
python -m nowa_sandbox.run_sandbox \
  --stage 1a --quarters 100 --seed 1 \
  --stop-on-graduation false \
  --output results/stage1a_seed1_extended.json

# Затем диагностика тренда:
python tools/trend_diagnostic.py results/stage1a_seed1_extended.json --window 10
```

**Интерпретация результата:**
- Если `stockout_avoidance` показывает `LEARNING TREND` при 100+ кварталах
  (просто был не виден на масштабе 30) — Направление B закрывается само
  собой, увеличением `--quarters` в стандартном прогоне, без изменений кода
- Если `NO CLEAR TREND` сохраняется и при 100 кварталах — это сигнал
  переходить к вопросам 2 и 3 (sleep consolidation, параметры мира) как
  реальным техническим задачам, не к дальнейшему увеличению выборки

**Важно:** этот скрипт — диагностика, не часть продуктового пайплайна.
Не встраивать в `run_sandbox.py`/`stage1a_report.py` в этом патче — если
Направление B подтвердится как реальная проблема, тогда решение (не сам
диагностический инструмент) войдёт в патч v1.3.

---

*Патч v1.2 завершён. Разделы: диагноз, изменение методологии baseline
(median_all + volatility-aware floor), CLI, definition of done,
диагностический инструмент для следующего шага (Направление B).*
