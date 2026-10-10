from conflict_arbitration import ConflictArbitrationLayer


def _high_conflict_inputs():
    return {
        "go_signals": [0.34, 0.33, 0.33],
        "top2_gap": 0.01,
        "policy_entropy": 0.98,
        "decision_latency": 0.85,
        "threshold_current": 0.0,
        "novelty_score": 0.90,
        "pattern_completion_confidence": 0.15,
        "prediction_error": 1.0,
        "working_memory_load": 0.88,
        "task_complexity": 0.86,
    }


def _low_conflict_inputs():
    return {
        "go_signals": [0.90, 0.08, 0.02],
        "top2_gap": 0.82,
        "policy_entropy": 0.08,
        "decision_latency": 0.15,
        "threshold_current": 0.0,
        "novelty_score": 0.08,
        "pattern_completion_confidence": 0.92,
        "prediction_error": 0.04,
        "working_memory_load": 0.10,
        "task_complexity": 0.18,
    }


def test_acc_tc1_low_conflict_habitual():
    layer = ConflictArbitrationLayer()
    out = layer.arbitrate(**_low_conflict_inputs())

    assert out["control_mode"] == "habitual"
    assert out["threshold_delta"] < 0.0
    assert out["wm_boost_flag"] is False


def test_acc_tc2_high_conflict_high_novelty_deliberative_with_exploration():
    layer = ConflictArbitrationLayer()
    out = layer.arbitrate(**_high_conflict_inputs())

    assert out["control_mode"] == "deliberative"
    assert out["wm_boost_flag"] is True
    assert out["exploration_override"] is True
    assert out["threshold_delta"] > 0.0


def test_acc_tc3_repeated_failure_switches_to_inhibit():
    layer = ConflictArbitrationLayer()
    for _ in range(20):
        layer.register_outcome(reward_signal=-1.0, prediction_error=1.0)

    out = layer.arbitrate(**_high_conflict_inputs())
    assert out["control_mode"] == "inhibit"
    assert out["request_additional_evaluation"] is True
    assert out["threshold_delta"] >= 0.20


def test_acc_tc4_stress_without_conflict_does_not_force_deliberative():
    layer = ConflictArbitrationLayer()
    base = _low_conflict_inputs()
    stressed_out = layer.arbitrate(
        **base,
        arousal=1.0,
        stress_level=1.0,
        valence=-0.9,
    )

    assert stressed_out["control_mode"] != "deliberative"


def test_acc_tc5_oscillation_refractory_blocks_immediate_reentry():
    layer = ConflictArbitrationLayer(refractory_steps_after_deliberative=2)

    out_1 = layer.arbitrate(**_high_conflict_inputs())
    out_2 = layer.arbitrate(**_low_conflict_inputs())
    out_3 = layer.arbitrate(**_high_conflict_inputs())
    out_4 = layer.arbitrate(**_high_conflict_inputs())

    assert out_1["control_mode"] == "deliberative"
    assert out_2["control_mode"] in ("balanced", "habitual")
    assert out_3["control_mode"] != "deliberative"
    assert out_4["control_mode"] == "deliberative"


def test_acc_tc6_resource_exhaustion_forces_downshift_to_balanced():
    layer = ConflictArbitrationLayer(
        control_cost_limit=0.15,
        control_cost_gain=0.12,
        control_cost_decay=0.0,
    )

    modes = [layer.arbitrate(**_high_conflict_inputs())["control_mode"] for _ in range(5)]
    snap = layer.snapshot()

    assert modes[0] == "deliberative"
    assert "balanced" in modes[1:]
    assert int(snap.get("forced_downshift_count", 0)) > 0


def test_acc_conflict_metric_is_independent_from_valence():
    inputs = _high_conflict_inputs()
    layer_pos = ConflictArbitrationLayer()
    layer_neg = ConflictArbitrationLayer()

    out_pos = layer_pos.arbitrate(**inputs, valence=1.0, arousal=0.0, stress_level=0.0)
    out_neg = layer_neg.arbitrate(**inputs, valence=-1.0, arousal=1.0, stress_level=1.0)

    c_pos = float(out_pos["metrics"]["conflict_score"])
    c_neg = float(out_neg["metrics"]["conflict_score"])
    assert abs(c_pos - c_neg) < 1e-9


def test_acc_control_demand_increases_with_latency():
    layer = ConflictArbitrationLayer()
    base = dict(_high_conflict_inputs())
    base.pop("decision_latency", None)

    low_latency = layer.arbitrate(**base, decision_latency=0.10)
    high_latency = layer.arbitrate(**base, decision_latency=0.95)

    assert float(high_latency["metrics"]["control_demand"]) > float(low_latency["metrics"]["control_demand"])
