"""Regression-anchored on the actual seed1 run: stockout_avoidance
ranged 0.000-1.000 across 30 quarters with no visible learning trend."""

import statistics

import pytest

from nowa_sandbox.procurement_fitness import (
    NON_REGRESSION_FLOOR,
    ProcurementFitnessEvaluator,
    ProcurementFitnessVector,
)
from nowa_sandbox.stage_baseline import (
    MIN_QUARTERS_FOR_BASELINE,
    compute_stage_1a_baseline,
    non_regression_floor,
    save_baseline,
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
                "cost_efficiency": 0.6,
                "stockout_avoidance": v,
                "budget_discipline": 1.0,
                "reaction_to_risk_events": 0.6,
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
        assert payload["method"] == "median_all"
        assert payload["n_quarters_used"] == 30

    def test_raises_below_minimum_quarters(self):
        quarters = _fake_quarters(SEED1_STOCKOUT_AVOIDANCE[:10])
        with pytest.raises(ValueError, match="at least"):
            compute_stage_1a_baseline(quarters)

    def test_high_iqr_flagged_in_spread(self):
        quarters = _fake_quarters(SEED1_STOCKOUT_AVOIDANCE)
        payload = compute_stage_1a_baseline(quarters)
        assert payload["stage_1a_spread_iqr"]["stockout_avoidance"] > 0.3

    def test_mean_best_still_available_for_diagnostics(self):
        quarters = _fake_quarters(
            SEED1_STOCKOUT_AVOIDANCE,
            passed_indices={6, 9, 19, 23, 26},
        )
        payload = compute_stage_1a_baseline(quarters, method="mean_best", last_n=5)
        assert payload["method"] == "mean_best"
        assert payload["stage_1a_baseline"]["stockout_avoidance"] == pytest.approx(
            statistics.mean(
                [SEED1_STOCKOUT_AVOIDANCE[i - 1] for i in (6, 9, 19, 23, 26)]
            ),
            abs=1e-3,
        )

    def test_refuses_to_save_mean_best_as_guard_baseline(self, tmp_path):
        quarters = _fake_quarters(SEED1_STOCKOUT_AVOIDANCE[:5], passed_indices={1})
        payload = compute_stage_1a_baseline(quarters, method="mean_best")
        with pytest.raises(ValueError, match="mean_best"):
            save_baseline(str(tmp_path / "bad.json"), payload)


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

    def test_min_quarters_constant(self):
        assert MIN_QUARTERS_FOR_BASELINE == 15


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

    def test_guard_uses_iqr_when_provided(self):
        """Wiring: check_non_regression must honour the volatility floor."""
        evaluator = ProcurementFitnessEvaluator(stage="1b")
        baseline = {
            "cost_efficiency": 0.6,
            "stockout_avoidance": statistics.median(SEED1_STOCKOUT_AVOIDANCE),
            "budget_discipline": 1.0,
            "reaction_to_risk_events": 0.6,
        }
        spread = {
            "cost_efficiency": 0.0,
            "stockout_avoidance": 0.6,
            "budget_discipline": 0.0,
            "reaction_to_risk_events": 0.0,
        }
        # 0.40 is below median*0.9 for the seed1 median (~0.207*0.9) wait —
        # seed1 median of stockout is around 0.3; 0.40 should pass the
        # volatility floor but would fail a cherry-picked 0.949*0.9 floor.
        vector = ProcurementFitnessVector(
            cost_efficiency=0.6,
            stockout_avoidance=0.40,
            budget_discipline=1.0,
            supplier_diversification=0.5,
            decision_consistency=0.5,
            reaction_to_risk_events=0.6,
            n_days=90,
            n_orders=10,
        )
        with_iqr = evaluator.check_non_regression(
            vector, baseline, stage_1a_spread_iqr=spread
        )
        without = evaluator.check_non_regression(vector, baseline)
        # Volatility-aware floor for stockout is ~0 (median - 0.6), so 0.40 passes.
        assert with_iqr["stockout_avoidance"] is True
        # Without IQR, floor = median * 0.9. For seed1 median ~0.3 that is
        # ~0.27 — 0.40 still passes. Use a high baseline to show the difference.
        high_baseline = dict(baseline)
        high_baseline["stockout_avoidance"] = 0.9493
        with_iqr_high = evaluator.check_non_regression(
            vector, high_baseline, stage_1a_spread_iqr=spread
        )
        without_high = evaluator.check_non_regression(vector, high_baseline)
        assert with_iqr_high["stockout_avoidance"] is True
        assert without_high["stockout_avoidance"] is False
        assert without["budget_discipline"] is True
        assert abs(NON_REGRESSION_FLOOR - 0.9) < 1e-9
