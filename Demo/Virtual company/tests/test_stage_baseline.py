"""Tests for Stage 1a baseline extraction (spec sections 26.5, 27.3, v1.2)."""

import json

import pytest

from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA
from nowa_sandbox.stage_baseline import (
    MIN_QUARTERS_FOR_BASELINE,
    compute_stage_1a_baseline,
    load_baseline,
    load_baseline_bundle,
    save_baseline,
    successful_quarters,
)


def _quarter(index, all_passed=True, **fitness):
    values = {c: 0.8 for c in STAGE_1A_CRITERIA}
    values.update(fitness)
    return {
        "quarter_index": index,
        "fitness": values,
        "graduation": {"all_passed": all_passed},
    }


def _many(n=MIN_QUARTERS_FOR_BASELINE, all_passed=True, **fitness):
    return [_quarter(i, all_passed=all_passed, **fitness) for i in range(1, n + 1)]


class TestSuccessfulQuarters:

    def test_selects_only_graduated_quarters(self):
        quarters = [_quarter(1, False), _quarter(2, True), _quarter(3, False)]
        assert [q["quarter_index"] for q in successful_quarters(quarters)] == [2]

    def test_empty_input_is_empty_output(self):
        assert successful_quarters([]) == []
        assert successful_quarters(None) == []

    def test_missing_graduation_block_counts_as_failure(self):
        assert successful_quarters([{"quarter_index": 1, "fitness": {}}]) == []


class TestComputeBaselineMedianAll:

    def test_median_across_all_quarters(self):
        quarters = [
            _quarter(i, True, cost_efficiency=float(i) / 10) for i in range(1, 16)
        ]
        # values 0.1 .. 1.5 — wait, i/10 for i=1..15 is 0.1..1.5, median of
        # 15 values is the 8th = 0.8
        payload = compute_stage_1a_baseline(quarters)
        assert payload["method"] == "median_all"
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(0.8)
        assert payload["n_quarters_used"] == 15
        assert payload["computed_from_quarters"] == list(range(1, 16))

    def test_failed_quarters_are_included_in_median(self):
        quarters = _many(15, all_passed=True, cost_efficiency=1.0)
        quarters[0] = _quarter(1, False, cost_efficiency=0.0)
        payload = compute_stage_1a_baseline(quarters)
        # 14 ones and one zero -> median still 1.0
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(1.0)
        assert payload["n_quarters_passed"] == 14

    def test_covers_exactly_the_stage_1a_criteria(self):
        payload = compute_stage_1a_baseline(_many())
        assert set(payload["stage_1a_baseline"]) == set(STAGE_1A_CRITERIA)
        assert set(payload["stage_1a_spread_iqr"]) == set(STAGE_1A_CRITERIA)

    def test_zero_quarters_is_an_error(self):
        with pytest.raises(ValueError, match="zero quarters"):
            compute_stage_1a_baseline([])

    def test_below_minimum_raises(self):
        with pytest.raises(ValueError, match="at least"):
            compute_stage_1a_baseline(_many(MIN_QUARTERS_FOR_BASELINE - 1))

    def test_missing_criterion_scores_zero_rather_than_crashing(self):
        quarters = [
            {"quarter_index": i, "fitness": {}, "graduation": {"all_passed": True}}
            for i in range(1, MIN_QUARTERS_FOR_BASELINE + 1)
        ]
        payload = compute_stage_1a_baseline(quarters)
        assert payload["stage_1a_baseline"]["cost_efficiency"] == 0.0

    def test_accepts_quarter_result_objects(self):
        """Works on live QuarterResult objects, not just parsed JSON."""
        from nowa_sandbox.procurement_fitness import ProcurementFitnessVector

        class _Q:
            def __init__(self, index):
                self.quarter_index = index
                self.fitness = ProcurementFitnessVector(
                    cost_efficiency=0.7, stockout_avoidance=0.9, budget_discipline=1.0,
                    supplier_diversification=0.5, decision_consistency=0.5,
                    reaction_to_risk_events=0.6, n_days=90, n_orders=10,
                )
                self.graduation = {"all_passed": True}

        payload = compute_stage_1a_baseline([_Q(i) for i in range(1, 16)])
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(0.7)


class TestComputeBaselineMeanBest:

    def test_averages_the_last_five_successful_quarters(self):
        quarters = [_quarter(i, True, cost_efficiency=float(i) / 10) for i in range(1, 11)]
        payload = compute_stage_1a_baseline(quarters, method="mean_best", last_n=5)
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(0.8)
        assert payload["computed_from_quarters"] == [6, 7, 8, 9, 10]
        assert payload["from_successful_quarters"] is True
        assert payload["method"] == "mean_best"

    def test_failed_quarters_are_excluded(self):
        quarters = [
            _quarter(1, True, cost_efficiency=1.0),
            _quarter(2, False, cost_efficiency=0.0),
            _quarter(3, True, cost_efficiency=1.0),
        ]
        payload = compute_stage_1a_baseline(quarters, method="mean_best", last_n=5)
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(1.0)
        assert payload["computed_from_quarters"] == [1, 3]

    def test_falls_back_to_trailing_quarters_when_none_graduated(self):
        """A baseline is still derivable from an exploratory run, but flagged."""
        quarters = [_quarter(i, False, cost_efficiency=0.5) for i in range(1, 4)]
        payload = compute_stage_1a_baseline(quarters, method="mean_best", last_n=2)
        assert payload["from_successful_quarters"] is False
        assert payload["computed_from_quarters"] == [2, 3]

    def test_fewer_quarters_than_requested_uses_what_exists(self):
        payload = compute_stage_1a_baseline(
            [_quarter(1, True)], method="mean_best", last_n=5
        )
        assert payload["computed_from_quarters"] == [1]

    def test_last_n_of_zero_still_yields_one_quarter(self):
        payload = compute_stage_1a_baseline(
            [_quarter(1), _quarter(2)], method="mean_best", last_n=0
        )
        assert payload["computed_from_quarters"] == [2]


class TestSaveAndLoad:

    def test_round_trip_through_a_baseline_file(self, tmp_path):
        path = tmp_path / "nested" / "baseline.json"
        payload = compute_stage_1a_baseline(_many(15, cost_efficiency=0.9))
        save_baseline(str(path), payload, source="results/stage1a_seed3.json")

        written = json.loads(path.read_text(encoding="utf-8"))
        assert written["source"] == "results/stage1a_seed3.json"
        assert written["method"] == "median_all"
        assert "stage_1a_spread_iqr" in written

        loaded = load_baseline(str(path))
        assert loaded["cost_efficiency"] == pytest.approx(0.9)
        assert set(loaded) == set(STAGE_1A_CRITERIA)

        bundle = load_baseline_bundle(str(path))
        assert bundle["stage_1a_spread_iqr"]["cost_efficiency"] == pytest.approx(0.0)

    def test_loads_directly_from_a_run_result_list(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(
            json.dumps(_many(15, True, cost_efficiency=0.75)), encoding="utf-8"
        )
        assert load_baseline(str(path))["cost_efficiency"] == pytest.approx(0.75)

    def test_loads_a_bare_criterion_mapping(self, tmp_path):
        path = tmp_path / "bare.json"
        path.write_text(json.dumps({"cost_efficiency": 0.5}), encoding="utf-8")
        assert load_baseline(str(path)) == {"cost_efficiency": 0.5}

    def test_unrecognized_payload_is_rejected(self, tmp_path):
        path = tmp_path / "junk.json"
        path.write_text(json.dumps({"unrelated": 1}), encoding="utf-8")
        with pytest.raises(ValueError, match="no Stage 1a baseline"):
            load_baseline(str(path))

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_baseline(str(tmp_path / "absent.json"))

    def test_malformed_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_baseline(str(path))

    def test_refuses_saving_mean_best(self, tmp_path):
        payload = compute_stage_1a_baseline(_many(5), method="mean_best")
        with pytest.raises(ValueError, match="mean_best"):
            save_baseline(str(tmp_path / "x.json"), payload)
