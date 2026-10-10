"""Tests for Direction B diagnostic tools (patch v1.2 open questions)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import trend_diagnostic  # noqa: E402
import world_volatility_diagnostic  # noqa: E402


def test_moving_average_and_slope_detect_learning():
    rising = [float(i) / 20 for i in range(30)]
    smoothed = trend_diagnostic.moving_average(rising, window=10)
    assert smoothed
    assert trend_diagnostic.trend_slope(smoothed) > 0.002


def test_flat_noise_is_no_clear_trend():
    flat = [0.3, 0.7, 0.1, 0.9, 0.2, 0.8, 0.4, 0.6] * 5
    smoothed = trend_diagnostic.moving_average(flat, window=10)
    assert abs(trend_diagnostic.trend_slope(smoothed)) <= 0.05


def test_analyze_reports_verdicts(tmp_path, capsys):
    from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

    quarters = [
        {
            "quarter_index": i,
            "fitness": {c: min(1.0, i / 40) for c in STAGE_1A_CRITERIA},
        }
        for i in range(1, 31)
    ]
    report = trend_diagnostic.analyze(quarters, window=10)
    out = capsys.readouterr().out
    assert "Trend diagnostic" in out
    assert report["stockout_avoidance"]["verdict"] == "LEARNING TREND"
    assert report["stockout_avoidance"]["verdict_dual"] == "LEARNING TREND"


def test_dual_verdict_catches_weak_slope():
    """v1.3 open Q: slope 0.001 missed by strict 0.002 but caught by dual."""
    verdicts = trend_diagnostic.classify_trend(0.001, first_last_delta=0.0)
    assert verdicts["strict"] == "NO CLEAR TREND"
    assert verdicts["dual"] == "LEARNING TREND"


def test_dual_verdict_uses_first_last_delta():
    verdicts = trend_diagnostic.classify_trend(0.0, first_last_delta=0.08)
    assert verdicts["strict"] == "NO CLEAR TREND"
    assert verdicts["dual"] == "LEARNING TREND"


def test_trend_cli_reads_results_json(tmp_path):
    from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

    path = tmp_path / "run.json"
    path.write_text(
        json.dumps(
            [
                {
                    "quarter_index": i,
                    "fitness": {c: 0.5 for c in STAGE_1A_CRITERIA},
                }
                for i in range(1, 25)
            ]
        ),
        encoding="utf-8",
    )
    assert trend_diagnostic.main([str(path), "--window", "5"]) == 0


def test_world_volatility_diagnostic_runs():
    report = world_volatility_diagnostic.analyze_world_volatility(
        n_quarters=5, base_seed=1
    )
    assert report["n_quarters"] == 5
    assert "total_stockout_units" in report
    assert report["total_stockout_units"]["stdev"] >= 0.0


def test_results_correlation_mode(tmp_path, capsys):
    from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

    quarters = []
    for i in range(1, 11):
        fitness = {c: 0.9 for c in STAGE_1A_CRITERIA}
        if i <= 3:
            fitness["stockout_avoidance"] = 0.0
        quarters.append(
            {
                "quarter_index": i,
                "fitness": fitness,
                "world_summary": {
                    "n_orders_placed": 10 if i > 3 else 2,
                    "n_orders_delivered": 8,
                    "n_suppliers_defaulted": 0 if i > 3 else 2,
                    "total_stockout_units": 10.0 if i > 3 else 500.0,
                    "total_holding_cost": 1.0,
                    "spent_ratio": 0.5 if i > 3 else 0.95,
                },
            }
        )
    path = tmp_path / "run.json"
    path.write_text(json.dumps(quarters), encoding="utf-8")
    assert world_volatility_diagnostic.main([str(path), "--zero-threshold", "0.1"]) == 0
    out = capsys.readouterr().out
    assert "Zero quarters" in out
    assert "Good quarters" in out


def test_sleep_hooks_probe():
    sleep = world_volatility_diagnostic.analyze_sleep_hooks()
    assert "has_sleep_cycle" in sleep
