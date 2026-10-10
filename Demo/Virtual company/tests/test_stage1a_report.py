"""Tests for the Stage 1a sweep report (spec sections 27.2, 27.3, 26.7)."""

import json

import pytest

from nowa_sandbox import stage1a_report
from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA


def _quarter(index, all_passed, value=0.8):
    return {
        "quarter_index": index,
        "fitness": {c: value for c in STAGE_1A_CRITERIA},
        "graduation": {"all_passed": all_passed},
    }


def _run_file(tmp_path, name, graduated_at=None, n_quarters=30, value=0.8):
    """Write a synthetic run result where graduation starts at a given quarter."""
    quarters = [
        _quarter(
            i,
            all_passed=graduated_at is not None and i >= graduated_at,
            value=value,
        )
        for i in range(1, n_quarters + 1)
    ]
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(quarters), encoding="utf-8")
    return str(path)


class TestSummarizeRun:

    def test_reports_first_graduation_quarter(self, tmp_path):
        row = stage1a_report.summarize_run(_run_file(tmp_path, "seed1", graduated_at=12))
        assert row["graduated"] is True
        assert row["first_graduation_quarter"] == 12
        assert row["n_graduated_quarters"] == 19
        assert row["n_quarters"] == 30

    def test_reports_a_run_that_never_graduated(self, tmp_path):
        row = stage1a_report.summarize_run(_run_file(tmp_path, "seed2", graduated_at=None))
        assert row["graduated"] is False
        assert row["first_graduation_quarter"] is None
        assert row["baseline_from_successful"] is False

    def test_baseline_covers_stage_1a_criteria(self, tmp_path):
        row = stage1a_report.summarize_run(_run_file(tmp_path, "seed3", graduated_at=1))
        assert set(row["baseline"]) == set(STAGE_1A_CRITERIA)
        assert row["baseline"]["cost_efficiency"] == pytest.approx(0.8)


class TestReadiness:

    def _rows(self, tmp_path, quarters):
        return [
            stage1a_report.summarize_run(
                _run_file(tmp_path, f"seed{i}", graduated_at=q)
            )
            for i, q in enumerate(quarters, start=1)
        ]

    def test_three_of_five_graduating_with_tight_spread_is_ready(self, tmp_path):
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [10, 11, 12, None, None])
        )
        assert readiness["n_graduated"] == 3
        assert readiness["enough_graduated"] is True
        assert readiness["spread_within_tolerance"] is True
        assert readiness["ready_for_stage_1b"] is True

    def test_two_of_five_graduating_is_not_ready(self, tmp_path):
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [10, 11, None, None, None])
        )
        assert readiness["enough_graduated"] is False
        assert readiness["ready_for_stage_1b"] is False

    def test_wide_spread_blocks_readiness(self, tmp_path):
        """Graduating at quarter 2 in one run and 28 in another is not stable."""
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [2, 15, 28, None, None])
        )
        assert readiness["enough_graduated"] is True
        assert readiness["spread_within_tolerance"] is False
        assert readiness["ready_for_stage_1b"] is False

    def test_early_graduation_cluster_is_ready(self, tmp_path):
        """v1.3: ±50% of a tiny mean must not reject healthy early q* clusters.

        Real sweep: q* = [1, 2, 2, 6] failed the pure relative rule with
        spread_ratio 1.182 even though four of five seeds graduated fast.
        """
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [1, 2, 2, 6, None])
        )
        assert readiness["n_graduated"] == 4
        assert readiness["enough_graduated"] is True
        assert readiness["spread_half_width"] == stage1a_report.MIN_ABSOLUTE_HALF_WIDTH
        assert readiness["spread_within_tolerance"] is True
        assert readiness["ready_for_stage_1b"] is True
        assert readiness["spread_ratio"] <= 1.0

    def test_spread_ratio_is_zero_for_identical_runs(self, tmp_path):
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [10, 10, 10, 10, 10])
        )
        assert readiness["spread_ratio"] == 0.0

    def test_no_graduated_runs_is_not_ready(self, tmp_path):
        readiness = stage1a_report.check_readiness(
            self._rows(tmp_path, [None] * 5)
        )
        assert readiness["ready_for_stage_1b"] is False
        assert readiness["graduation_quarters"] == []


class TestBaselineSelection:

    def test_picks_the_median_graduated_run(self, tmp_path):
        rows = [
            stage1a_report.summarize_run(
                _run_file(tmp_path, "low", graduated_at=1, value=0.6)
            ),
            stage1a_report.summarize_run(
                _run_file(tmp_path, "mid", graduated_at=1, value=0.8)
            ),
            stage1a_report.summarize_run(
                _run_file(tmp_path, "high", graduated_at=1, value=0.95)
            ),
        ]
        chosen = stage1a_report.pick_baseline_run(rows)
        assert chosen["name"] == "mid"

    def test_ignores_runs_that_never_graduated(self, tmp_path):
        rows = [
            stage1a_report.summarize_run(
                _run_file(tmp_path, "failed", graduated_at=None, value=0.99)
            ),
            stage1a_report.summarize_run(
                _run_file(tmp_path, "passed", graduated_at=1, value=0.7)
            ),
        ]
        assert stage1a_report.pick_baseline_run(rows)["name"] == "passed"

    def test_returns_none_when_nothing_graduated(self, tmp_path):
        rows = [
            stage1a_report.summarize_run(_run_file(tmp_path, "a", graduated_at=None))
        ]
        assert stage1a_report.pick_baseline_run(rows) is None


class TestCli:

    def test_prints_table_and_verdict(self, tmp_path, capsys):
        paths = [
            _run_file(tmp_path, f"seed{i}", graduated_at=q)
            for i, q in enumerate([10, 11, 12, None, None], start=1)
        ]
        assert stage1a_report.main(paths) == 0
        out = capsys.readouterr().out
        assert "READY for Stage 1b" in out
        assert "cost_eff" in out
        assert "Graduation quarters: [10, 11, 12]" in out
        assert "Stage 1a baseline (method=median_all)" in out
        assert "IQR=" in out

    def test_writes_baseline_file(self, tmp_path):
        paths = [
            _run_file(tmp_path, f"seed{i}", graduated_at=5, value=0.75)
            for i in range(1, 4)
        ]
        out_path = tmp_path / "baseline.json"
        assert stage1a_report.main(paths + ["--write-baseline", str(out_path)]) == 0

        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(0.75)
        assert payload["from_successful_quarters"] is True
        assert payload["method"] == "median_all"
        assert "stage_1a_spread_iqr" in payload
        assert "source" in payload

    def test_refuses_to_write_a_baseline_without_graduation(self, tmp_path, capsys):
        paths = [_run_file(tmp_path, "seed1", graduated_at=None)]
        out_path = tmp_path / "baseline.json"
        assert stage1a_report.main(paths + ["--write-baseline", str(out_path)]) == 1
        assert not out_path.exists()
        assert "refusing to write" in capsys.readouterr().out.lower()

    def test_refuses_write_baseline_with_mean_best(self, tmp_path, capsys):
        paths = [_run_file(tmp_path, "seed1", graduated_at=5, value=0.8)]
        out_path = tmp_path / "baseline.json"
        code = stage1a_report.main(
            paths
            + [
                "--write-baseline",
                str(out_path),
                "--baseline-method",
                "mean_best",
            ]
        )
        assert code == 1
        assert not out_path.exists()
        assert "mean_best" in capsys.readouterr().out

    def test_high_volatility_flag_in_summary(self, tmp_path, capsys):
        """Varying stockout across 30 quarters should flag HIGH VOLATILITY."""
        from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

        values = [
            0.0, 0.7, 0.0, 0.2, 0.5, 0.9, 0.2, 0.4, 1.0, 0.2,
            0.5, 0.8, 0.4, 0.0, 0.0, 0.0, 0.1, 0.0, 0.9, 0.7,
            0.0, 0.7, 1.0, 0.2, 0.1, 0.9, 0.4, 0.0, 0.0, 0.4,
        ]
        quarters = []
        for i, v in enumerate(values, start=1):
            fitness = {c: 0.8 for c in STAGE_1A_CRITERIA}
            fitness["stockout_avoidance"] = v
            quarters.append(
                {
                    "quarter_index": i,
                    "fitness": fitness,
                    "graduation": {"all_passed": i in (6, 9, 19)},
                }
            )
        path = tmp_path / "volatile.json"
        path.write_text(json.dumps(quarters), encoding="utf-8")
        assert stage1a_report.main([str(path)]) == 0
        out = capsys.readouterr().out
        assert "HIGH VOLATILITY" in out

