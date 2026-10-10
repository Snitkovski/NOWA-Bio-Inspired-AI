"""load_baseline must be as strict as stage1a_report.py's --write-baseline.

Refuse rather than silently build a Stage 1b guard from non-graduated quarters
(patch v1.1.1 change 2). Median methodology (v1.2) does not relax that rule.
"""

import json

import pytest

from nowa_sandbox.stage_baseline import (
    MIN_QUARTERS_FOR_BASELINE,
    compute_stage_1a_baseline,
    load_baseline,
)


def test_refuses_baseline_from_all_failed_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": i,
            "fitness": {
                "cost_efficiency": 0.3,
                "stockout_avoidance": 0.1,
                "budget_discipline": 1.0,
                "reaction_to_risk_events": 0.2,
            },
            "graduation": {"all_passed": False},
        }
        for i in range(1, 6)
    ]
    path = tmp_path / "all_failed.json"
    path.write_text(json.dumps(quarters), encoding="utf-8")

    with pytest.raises(ValueError, match="no graduated Stage 1a quarters"):
        load_baseline(str(path))


def test_accepts_baseline_from_graduated_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": i,
            "fitness": {
                "cost_efficiency": 0.8,
                "stockout_avoidance": 0.9,
                "budget_discipline": 1.0,
                "reaction_to_risk_events": 0.7,
            },
            "graduation": {"all_passed": True},
        }
        for i in range(1, MIN_QUARTERS_FOR_BASELINE + 1)
    ]
    path = tmp_path / "graduated.json"
    path.write_text(json.dumps(quarters), encoding="utf-8")

    baseline = load_baseline(str(path))
    assert baseline["cost_efficiency"] == 0.8


def test_curated_baseline_file_unaffected(tmp_path):
    """Mapping-based path (already produced by --write-baseline) keeps working."""
    payload = {
        "stage_1a_baseline": {
            "cost_efficiency": 0.7523,
            "stockout_avoidance": 0.9493,
            "budget_discipline": 1.0,
            "reaction_to_risk_events": 0.7894,
        },
        "stage_1a_spread_iqr": {
            "cost_efficiency": 0.1,
            "stockout_avoidance": 0.6,
            "budget_discipline": 0.0,
            "reaction_to_risk_events": 0.2,
        },
        "method": "median_all",
        "computed_from_quarters": list(range(1, 31)),
        "from_successful_quarters": True,
    }
    path = tmp_path / "curated.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    baseline = load_baseline(str(path))
    assert baseline["stockout_avoidance"] == 0.9493


def test_compute_baseline_still_permits_failed_runs_for_diagnostics(tmp_path):
    """NR5: mean_best stays permissive; only load_baseline is strict."""
    quarters = [
        {
            "quarter_index": 1,
            "fitness": {
                "cost_efficiency": 0.3,
                "stockout_avoidance": 0.1,
                "budget_discipline": 1.0,
                "reaction_to_risk_events": 0.2,
            },
            "graduation": {"all_passed": False},
        }
    ]
    payload = compute_stage_1a_baseline(quarters, method="mean_best")
    assert payload["from_successful_quarters"] is False
    assert payload["stage_1a_baseline"]["cost_efficiency"] == pytest.approx(0.3)
