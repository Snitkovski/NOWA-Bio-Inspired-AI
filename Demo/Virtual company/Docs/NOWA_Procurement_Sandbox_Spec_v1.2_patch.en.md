# NOWA Procurement Sandbox — Patch v1.2

Russian version: [NOWA_Procurement_Sandbox_Spec_v1.2_patch.ru.md](NOWA_Procurement_Sandbox_Spec_v1.2_patch.ru.md)

## Abstract

Patch v1.2 is taken up after the v1.1.1 streak logic was confirmed on seed 1: the Stage 1b qualifying streak over fifty quarters did not exceed one, and `result.graduated` remained false. The same material showed that `stockout_avoidance` on Stage 1a (seed 1, quarters 1–30) forms no monotonic trend. Quarter 1 yields 0.000 and quarter 30 yields 0.398; neighbouring steps diverge as 0.419 → 0.995 and 0.995 → 0.204. Runs of seeds 11 and 14 produced no graduated quarter out of thirty. The document accounts for the dispersion by the fact that every Stage 1a quarter generates a new profile of demand, shocks, and reorder points, so task difficulty changes by more than any competence gain distinguishable over thirty iterations.

The v1.1 baseline averaged the last successful quarters. For stockout avoidance on seed 1 those are quarters 6, 9, 19, 23, and 26, with values from 0.897 to 1.000 and a mean of 0.9493, that is, the upper tail of the distribution. The floor of 0.854 then marked as regression swings that on Stage 1b remain in the same wide range and are not a consequence of supplier persistence. The patch replaces the calculation with the median over all quarters (`median_all`), requires at least fifteen quarters, and publishes the interquartile range. The floor is the minimum of the median multiplied by 0.9 and the median minus the range: at zero range, as with the budget discipline that was observed, the factor 0.9 is retained, and at a large range the floor drops toward the ordinary Stage 1a spread. The method `mean_best` remains available for comparison in the report and refuses to be written as a guarding baseline. A criterion with a range above 0.3 is marked highly volatile.

The non-regression check and the streak count do not change; the number passed to them does. Questions about a trend at a scale of one hundred quarters or more, about the behaviour of `sleep_cycle` between neighbouring quarters, and about the calibration of `demand_shock_probability` and `late_delivery_probability_base`, both equal to 0.05, are deferred. For the first of these the specification proposes a separate script of a moving average with window 10 and of the linear-regression slope of the smoothed series, with slope thresholds of ±0.002 for verdicts of learning, no clear trend, and decline. The script is not part of the `nowa_sandbox` package.

---

**Base documents:**
NOWA_Procurement_Sandbox_Spec.md (v1.0)
NOWA_Procurement_Sandbox_Spec_v1.1_patch.en.md (Stage 1a/1b curriculum)
NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.md (non-regression streak fix)

**Status:** Ready for implementation — diagnosis of, and a fix to, the baseline methodology, found after the v1.1.1 patch had been checked successfully

---

## Empirical grounds

Patch v1.1.1 behaved correctly: `qualifying_streak` for Stage 1b (seed 1, 50 quarters) did not exceed 1, and `result.graduated = False`. That confirms that the streak logic is implemented correctly (the v1.1.1 verification section is closed).

The data, however, exposed a problem one level higher: **`stockout_avoidance` itself shows no learning trend across the 30 quarters of Stage 1a**.

The full sequence (seed 1, quarters 1–30):

```
Q 1: 0.000   Q 7: 0.197   Q13: 0.376   Q19: 0.897   Q25: 0.090
Q 2: 0.745   Q 8: 0.419   Q14: 0.000   Q20: 0.741   Q26: 0.919
Q 3: 0.000   Q 9: 0.995   Q15: 0.000   Q21: 0.000   Q27: 0.448
Q 4: 0.178   Q10: 0.204   Q16: 0.000   Q22: 0.716   Q28: 0.000
Q 5: 0.456   Q11: 0.481   Q17: 0.096   Q23: 1.000   Q29: 0.000
Q 6: 0.936   Q12: 0.835   Q18: 0.000   Q24: 0.216   Q30: 0.398
```

There is no monotonic trend, and not even a weakly increasing one: quarter 1 (0.000) and quarter 30 (0.398) are comparable in quality; the best results (0.995, 1.000) appear in quarters 9 and 23 with no visible link to accumulated experience. The dispersion between neighbouring quarters is large (Q8→Q9: 0.419→0.995; Q9→Q10: 0.995→0.204).

This is confirmed on two further runs (seed 11, seed 14): **0 of 30 quarters graduated** in both. Even a single hit of a “fortunate window”, as happened for seed 1, is not guaranteed under another seed.

### The mechanism that accounts for the volatility

Constraint V1 (section 8) requires a new `ProcurementWorld` every quarter. That is a deliberate architectural decision: it stops the agent from binding to particular suppliers in Stage 1a. The side effect is that every quarter brings not only new suppliers but also a new random **demand profile** (`demand_volatility`, the moment of `demand_shock`, and the combination of goods with a low `reorder_point`). The difficulty of the quarter as a task varies by more than the agent’s competence grows over 30 iterations. Observed performance therefore looks like noise laid over an indistinguishable trend, rather than like a learning curve.

### How this breaks the non-regression baseline (v1.1.1)

`compute_stage_1a_baseline()` takes the **5 best quarters that passed** (for seed 1: Q6, Q9, Q19, Q23, Q26, with `stockout_avoidance` in the range 0.897–1.000). That is the upper tail of the distribution, not typical behaviour. `stage_1a_baseline["stockout_avoidance"] = 0.9493` is nearly the maximum of the whole series.

The non-regression floor is 0.9493 × 0.9 = 0.854. In Stage 1b (quarters 31–50) `stockout_avoidance` continues to swing through the same wide range as in Stage 1a (0.292–1.000). That is **the same original volatility of the task**, not a degradation caused by supplier persistence. The guard nevertheless treats any drop below 0.854 as “regression”, although the agent may never have worked stably above that level.

**Conclusion:** the non-regression guard cannot be trusted while the baseline is built from a non-representative sample (the best quarters, picked out of the series) rather than from the agent’s typical performance.

---

## Two independent directions of the fix

These directions do not exclude each other. Both are probably required, in the priority order given.

### Direction A (priority 1): an honest baseline

Change `compute_stage_1a_baseline()` so that it reflects **typical** performance, not **peak** performance. This does not redefine the physics of the world. It changes only how the expectation for the non-regression guard is built.

### Direction B (priority 2, and it requires a separate analysis): stability of Stage 1a itself

If, after Direction A, the agent still shows no learning trend even in the mean or the median, the problem lies deeper than the baseline. The question is whether the agent acquires anything stable from one quarter to the next (a question about `sleep_manager.sleep_cycle()` and about seed initialisation, not about the metrics). That is outside this patch. It is recorded as an open question (the section “Open questions” below), not as an immediate task.

---

## Files affected (Direction A)

| File | Kind of change |
|---|---|
| `stage_baseline.py::compute_stage_1a_baseline` | Replace “the mean of the 5 best” with a statistic that is robust to outliers, taken over **all** quarters, not only those that passed |
| `stage_baseline.py::load_baseline` | Update the error message (section v1.1.1 NR4) to the new methodology |
| `stage1a_report.py` | Update the report so that it shows not only the “best 5” but the full distribution over all 30 quarters |
| `tests/` | Tests of the new baseline methodology, including a regression test on the data from this run |

---

## Change 1: `compute_stage_1a_baseline` — median-of-all in place of mean-of-best

### Current behaviour (v1.1)

```python
def compute_stage_1a_baseline(quarters, last_n=BASELINE_QUARTERS):
    good = successful_quarters(quarters)   # только all_passed=True
    from_successful = bool(good)
    selected = (good or quarters)[-max(1, int(last_n)):]  # последние N успешных
    # ... затем среднее по selected
```

This yields a baseline equal to “the mean of the best N attempts”, a systematically optimistic figure.

### Required behaviour

Use the **median over all quarters** (not only the successful ones), and state the volatility (the interquartile range) explicitly in the report, so that a person reading the baseline sees not only the number but also its reliability.

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

### The non-regression floor must take volatility into account, not only the point

Section 26.5 (v1.1) defined `NON_REGRESSION_FLOOR = 0.9` as a fixed multiplier. That made sense for an optimistic “mean of best” baseline. With an honest median baseline, a fixed multiplier of 0.9 can still be too strict for criteria with a large IQR (`stockout_avoidance` in these data ranges from 0 to 1, almost the whole scale).

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

**Grounds for this formula.** For `budget_discipline` (observed IQR ≈ 0, every value 1.0) `volatility_floor ≈ median`, which is stricter than `strict_floor`. The formula takes `min()`, so for stable criteria nothing changes relative to v1.1. For `stockout_avoidance` (observed IQR ≈ 0.5–0.6) `volatility_floor` lies noticeably below `strict_floor`, which is what is required: the agent is not penalised for swings that were already normal in Stage 1a.

---

## Change 2: `stage1a_report.py` — show the distribution, not only the point

The current output (v1.1) shows `stage_1a_baseline` only as finished numbers. Add an explicit picture of volatility to the text report:

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

## Test cases

### `tests/test_baseline_methodology.py` (new file)

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

## Constraints

| # | Constraint |
|---|---|
| **B1** | `method="mean_best"` is retained in the code (it is not deleted) only for diagnostic comparison in `stage1a_report.py`. It is **never** used as the value passed to `check_non_regression` |
| **B2** | `MIN_QUARTERS_FOR_BASELINE = 15`. With fewer quarters the median is statistically unreliable; `compute_stage_1a_baseline` must refuse, and must not quietly compute on a small sample |
| **B3** | `non_regression_floor()` is a pure function of `(median, iqr)`. It has no side effects and does not depend on the order of quarters |
| **B4** | The change affects only the methodology by which the baseline is **computed**. `check_non_regression()` (v1.1) and the streak logic (v1.1.1) do not change. They already use the floor that is passed to them; previously that floor had simply been built incorrectly |

---

## Open questions (Direction B — not settled by this patch)

1. **Does the agent show a learning trend at all, if the average is taken more coarsely?**
   Thirty separate quarters are little data for a statistic. A trend may exist and be visible only at a scale of 100 quarters or more. Recommendation: before any further calibration, run 100 quarters of Stage 1a on one seed and compute a moving average (a window of 10 quarters). If the trend is absent there as well, the question is no longer the sample size.

2. **Does `sleep_manager.sleep_cycle()` work as intended?**
   The chaos between neighbouring quarters (Q8→Q9: 0.419→0.995) does not rule out consolidation. It may fail to retain useful patterns from one quarter to the next because the *other* conditions of the world (demand, shocks) change by more than the agent can generalise. That requires profiling of hippocampus and cortex between particular quarters (for example Q8 against Q9) and is not in the scope of this patch.

3. **Are `demand_shock_probability=0.05` and `late_delivery_probability_base=0.05` calibrated correctly?**
   The dispersion of quarter difficulty may itself be too large for stable learning to be visible in 30 attempts. That is a question about the parameters of `ProcurementWorldConfig`, not about the fitness or baseline code.

These three questions are candidates for a patch v1.3, after more diagnostic data have been collected (item 1 above is the cheapest way to begin).

---

*Patch v1.2. It is grounded empirically in three Stage 1a runs (seed 1, seed 11, seed 14) and one Stage 1b run under patch v1.1.1. It changes the methodology of the baseline calculation, not the graduation or streak logic itself.*

---

## CLI changes

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

If `--baseline-method mean_best` is passed together with `--write-baseline`, the command refuses explicitly. It does not degrade quietly:

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

There is no change of signature. `--baseline-from` continues to accept a path to a file produced by `stage1a_report.py --write-baseline`. The choice of method is encapsulated there; `load_baseline()` simply reads the finished value.

---

## Definition of done for patch v1.2

- [ ] `compute_stage_1a_baseline` uses `median_all` by default and raises `ValueError` when `len(quarters) < 15`
- [ ] `non_regression_floor()` is implemented as a pure function and is covered by tests for a stable case (`budget_discipline`) and a volatile case (`stockout_avoidance`)
- [ ] Recomputing non-regression for the real Stage 1b data (quarters 31–50, seed 1) under the new floor yields strictly fewer false regressions than under the floor from v1.1. The test `test_stage1b_run_fewer_false_regressions_under_new_floor` is green
- [ ] `stage1a_report.py` prints the IQR and the flag `HIGH VOLATILITY` for every criterion with IQR > 0.3
- [ ] The attempt `--write-baseline --baseline-method mean_best` ends in an explicit refusal with return code 1
- [ ] The existing tests `test_stage_baseline_strictness.py` (patch v1.1.1) stay green without modification. Strictness on “there are no graduated quarters at all” is not tied to the choice of averaging method and must work the same way for both

---

## Diagnostic tool for Direction B (the next step after this patch)

Open question 1 (“does the agent show a learning trend at a larger scale”) is the cheapest way to move forward. It does not require changes to the fitness or baseline code, only a new analysis script on top of the existing `run_sandbox.py`.

### `tools/trend_diagnostic.py` (a new file, not part of the main package)

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

### Use

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

**Interpretation of the result:**

- If `stockout_avoidance` shows `LEARNING TREND` at 100 quarters or more (it was simply invisible at the scale of 30), Direction B closes by itself, by increasing `--quarters` in the standard run, with no change to the code.
- If `NO CLEAR TREND` persists at 100 quarters as well, that is the signal to move to questions 2 and 3 (sleep consolidation, world parameters) as real technical tasks, and not to enlarge the sample further.

**Important:** this script is a diagnostic. It is not part of the product pipeline. Do not build it into `run_sandbox.py` or `stage1a_report.py` in this patch. If Direction B is confirmed as a real problem, the decision (not the diagnostic tool itself) will enter patch v1.3.

---

*Patch v1.2 is complete. Sections: diagnosis, the change of baseline methodology (median_all and a volatility-aware floor), the CLI, the definition of done, and a diagnostic tool for the next step (Direction B).*
