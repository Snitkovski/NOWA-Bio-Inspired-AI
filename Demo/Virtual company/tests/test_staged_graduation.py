"""Tests for the v1.1 two-stage curriculum (spec section 26.4, 26.5, 26.8)."""

import pytest

from nowa_sandbox.procurement_fitness import (
    GRADUATION_THRESHOLDS,
    NON_REGRESSION_FLOOR,
    PROCUREMENT_CRITERIA,
    STAGE_1A_CRITERIA,
    STAGE_1B_CRITERIA,
    ProcurementFitnessEvaluator,
    ProcurementFitnessVector,
)


def _vector(**overrides):
    """A fitness vector that passes everything unless told otherwise."""
    values = {c: 1.0 for c in PROCUREMENT_CRITERIA}
    values.update(overrides)
    return ProcurementFitnessVector(**values, n_days=90, n_orders=30)


# A monopolist: perfect at the trade, terrible at spreading its business.
MONOPOLY_VECTOR = _vector(
    cost_efficiency=0.85,
    stockout_avoidance=0.95,
    budget_discipline=1.0,
    reaction_to_risk_events=0.90,
    supplier_diversification=0.1333,
    decision_consistency=1.0,
)


class TestCriteriaPartition:

    def test_the_two_stages_partition_all_six_criteria(self):
        assert set(STAGE_1A_CRITERIA) | set(STAGE_1B_CRITERIA) == set(
            PROCUREMENT_CRITERIA
        )
        assert not set(STAGE_1A_CRITERIA) & set(STAGE_1B_CRITERIA)

    def test_stage_1b_holds_exactly_the_identity_dependent_criteria(self):
        assert set(STAGE_1B_CRITERIA) == {
            "decision_consistency",
            "supplier_diversification",
        }

    def test_gating_criteria_exposed_per_stage(self):
        assert ProcurementFitnessEvaluator(stage="1a").gating_criteria == (
            STAGE_1A_CRITERIA
        )
        assert ProcurementFitnessEvaluator(stage="1b").gating_criteria == (
            STAGE_1B_CRITERIA
        )

    def test_default_stage_is_1a(self):
        assert ProcurementFitnessEvaluator().stage == "1a"

    def test_unknown_stage_is_rejected(self):
        with pytest.raises(ValueError, match="unknown stage"):
            ProcurementFitnessEvaluator(stage="1c")


class TestStagedGraduation:

    def test_stage_1a_ignores_diversification(self):
        """A monopolist still graduates 1a: identity metrics are not gating."""
        report = ProcurementFitnessEvaluator(stage="1a").graduation_report(
            MONOPOLY_VECTOR
        )
        assert report["supplier_diversification"]["gating"] is False
        assert report["supplier_diversification"]["passed"] is False
        assert report["all_passed"] is True

    def test_stage_1b_requires_diversification(self):
        """The same data must not graduate 1b, where the metric is the point."""
        report = ProcurementFitnessEvaluator(stage="1b").graduation_report(
            MONOPOLY_VECTOR
        )
        assert report["supplier_diversification"]["gating"] is True
        assert report["all_passed"] is False

    def test_stage_1b_ignores_a_failing_1a_criterion_for_gating(self):
        """1b gates on relationships only; 1a rot is caught by the guard instead."""
        vector = _vector(cost_efficiency=0.0)
        report = ProcurementFitnessEvaluator(stage="1b").graduation_report(vector)
        assert report["cost_efficiency"]["passed"] is False
        assert report["cost_efficiency"]["gating"] is False
        assert report["all_passed"] is True

    def test_all_six_criteria_are_always_reported(self):
        """Full diagnostic transparency regardless of which stage is gating."""
        for stage in ("1a", "1b"):
            report = ProcurementFitnessEvaluator(stage=stage).graduation_report(
                MONOPOLY_VECTOR
            )
            for criterion in PROCUREMENT_CRITERIA:
                assert criterion in report
                assert report[criterion]["threshold"] == GRADUATION_THRESHOLDS[
                    criterion
                ]
            assert report["stage"] == stage

    def test_gating_flags_match_the_active_stage(self):
        report = ProcurementFitnessEvaluator(stage="1a").graduation_report(
            MONOPOLY_VECTOR
        )
        gating = {c for c in PROCUREMENT_CRITERIA if report[c]["gating"]}
        assert gating == set(STAGE_1A_CRITERIA)

    def test_a_failing_gating_criterion_blocks_stage_1a(self):
        vector = _vector(stockout_avoidance=0.0)
        report = ProcurementFitnessEvaluator(stage="1a").graduation_report(vector)
        assert report["all_passed"] is False

    def test_thresholds_still_apply_per_stage(self):
        lenient = ProcurementFitnessEvaluator(
            thresholds={"supplier_diversification": 0.1}, stage="1b"
        )
        report = lenient.graduation_report(MONOPOLY_VECTOR)
        assert report["all_passed"] is True

    def test_report_keeps_run_size_fields(self):
        report = ProcurementFitnessEvaluator(stage="1b").graduation_report(
            MONOPOLY_VECTOR
        )
        assert report["n_days"] == 90
        assert report["n_orders"] == 30


class TestNonRegressionGuard:

    BASELINE = {
        "cost_efficiency": 0.8,
        "stockout_avoidance": 0.9,
        "budget_discipline": 1.0,
        "reaction_to_risk_events": 0.8,
    }

    def test_regression_detected_when_cost_efficiency_drops(self, fitness_evaluator):
        degraded = _vector(
            cost_efficiency=0.5,  # below the 0.9 * 0.8 = 0.72 floor
            stockout_avoidance=0.9,
            budget_discipline=1.0,
            reaction_to_risk_events=0.8,
        )
        result = fitness_evaluator.check_non_regression(degraded, self.BASELINE)
        assert result["cost_efficiency"] is False
        assert result["stockout_avoidance"] is True

    def test_guard_covers_exactly_the_stage_1a_criteria(self, fitness_evaluator):
        result = fitness_evaluator.check_non_regression(_vector(), self.BASELINE)
        assert set(result) == set(STAGE_1A_CRITERIA)

    def test_value_exactly_on_the_floor_passes(self, fitness_evaluator):
        floor = self.BASELINE["cost_efficiency"] * NON_REGRESSION_FLOOR
        result = fitness_evaluator.check_non_regression(
            _vector(cost_efficiency=floor), self.BASELINE
        )
        assert result["cost_efficiency"] is True

    def test_small_dip_within_tolerance_passes(self, fitness_evaluator):
        """A 5% dip is noise; the floor only trips on real degradation."""
        result = fitness_evaluator.check_non_regression(
            _vector(cost_efficiency=0.76), self.BASELINE
        )
        assert result["cost_efficiency"] is True

    def test_improving_beyond_baseline_passes(self, fitness_evaluator):
        result = fitness_evaluator.check_non_regression(
            _vector(cost_efficiency=1.0), self.BASELINE
        )
        assert all(result.values())

    def test_missing_baseline_entry_does_not_block(self, fitness_evaluator):
        """Absent baseline data means no floor, not an automatic failure."""
        result = fitness_evaluator.check_non_regression(
            _vector(cost_efficiency=0.0), {"stockout_avoidance": 0.9}
        )
        assert result["cost_efficiency"] is True

    def test_empty_baseline_passes_everything(self, fitness_evaluator):
        assert all(
            ProcurementFitnessEvaluator().check_non_regression(
                _vector(**{c: 0.0 for c in STAGE_1A_CRITERIA}), {}
            ).values()
        )

    def test_garbage_baseline_values_are_ignored(self, fitness_evaluator):
        result = fitness_evaluator.check_non_regression(
            _vector(cost_efficiency=0.1),
            {"cost_efficiency": "not-a-number"},
        )
        assert result["cost_efficiency"] is True

    def test_none_baseline_is_tolerated(self, fitness_evaluator):
        assert all(fitness_evaluator.check_non_regression(_vector(), None).values())


class TestBackwardCompatibility:
    """v1.0 behaviour that must survive the staging change."""

    def test_positional_thresholds_argument_still_works(self):
        evaluator = ProcurementFitnessEvaluator({"cost_efficiency": 0.1})
        assert evaluator.thresholds["cost_efficiency"] == 0.1
        assert evaluator.stage == "1a"

    def test_evaluate_still_returns_all_six_criteria(self, small_world):
        small_world.tick()
        vector = ProcurementFitnessEvaluator(stage="1b").evaluate(small_world, [])
        assert set(vector.as_dict()) == set(PROCUREMENT_CRITERIA)
