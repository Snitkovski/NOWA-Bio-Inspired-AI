"""Tests for per-quarter graduation diagnostics and monopoly detection."""

from nowa_sandbox.quarter_diagnostics import (
    SINGLE_SUPPLIER_SCORE,
    diagnose_quarter,
    format_diagnosis_text,
    is_single_supplier_monopoly,
)


def _record(
    *,
    stage="1b",
    diversif=0.1333,
    consist=0.97,
    risk=0.61,
    all_passed=False,
    nr=None,
):
    fitness = {
        "cost_efficiency": 0.85,
        "stockout_avoidance": 0.95,
        "budget_discipline": 1.0,
        "supplier_diversification": diversif,
        "decision_consistency": consist,
        "reaction_to_risk_events": risk,
    }
    graduation = {
        "stage": stage,
        "all_passed": all_passed,
    }
    for key, value in fitness.items():
        threshold = {
            "cost_efficiency": 0.60,
            "stockout_avoidance": 0.85,
            "budget_discipline": 0.95,
            "reaction_to_risk_events": 0.50,
            "supplier_diversification": 0.40,
            "decision_consistency": 0.60,
        }[key]
        gating = key in (
            ("supplier_diversification", "decision_consistency")
            if stage == "1b"
            else (
                "cost_efficiency",
                "stockout_avoidance",
                "budget_discipline",
                "reaction_to_risk_events",
            )
        )
        graduation[key] = {
            "value": value,
            "threshold": threshold,
            "passed": value >= threshold,
            "gating": gating,
        }
    return {
        "quarter_index": 38,
        "fitness": fitness,
        "graduation": graduation,
        "non_regression": nr,
        "world_summary": {
            "action_counts": {
                "place_order_reliable_supplier": 40,
                "diversify_supplier": 1,
                "wait_and_monitor": 49,
            }
        },
    }


class TestMonopoly:

    def test_single_supplier_score_constant(self):
        assert abs(SINGLE_SUPPLIER_SCORE - 0.133333) < 1e-5
        assert is_single_supplier_monopoly(0.133)
        assert is_single_supplier_monopoly(0.1333)
        assert not is_single_supplier_monopoly(0.438)


class TestDiagnoseQuarter:

    def test_monopoly_gate_fail(self):
        d = diagnose_quarter(_record(diversif=0.133, all_passed=False))
        assert d.monopoly
        assert "supplier_diversification" in d.gate_failures
        assert d.verdict_key == "diag.verdict.monopoly"
        assert not d.qualifies

    def test_nr_blocks_streak(self):
        d = diagnose_quarter(
            _record(
                diversif=0.438,
                risk=0.45,
                all_passed=True,
                nr={
                    "cost_efficiency": True,
                    "stockout_avoidance": True,
                    "budget_discipline": True,
                    "reaction_to_risk_events": False,
                },
            )
        )
        assert d.all_passed
        assert not d.qualifies
        assert d.nr_failures == ["reaction_to_risk_events"]
        assert d.verdict_key == "diag.verdict.nr_blocks"

    def test_stage_1a_ignores_loaded_nr_floors(self):
        """A baseline file in the GUI must not mark Stage 1a as NR-failed."""
        d = diagnose_quarter(
            _record(stage="1a", diversif=0.70, all_passed=False, nr=None),
            nr_floors={"stockout_avoidance": 0.90, "cost_efficiency": 0.45},
        )
        assert d.nr_failures == []
        assert d.stage == "1a"

    def test_format_includes_actions(self):
        d = diagnose_quarter(_record())
        text = format_diagnosis_text(d)
        assert "diversify_supplier" in text
        assert "diag.monopoly_flag" in text
        assert d.verdict_key == "diag.verdict.monopoly"
