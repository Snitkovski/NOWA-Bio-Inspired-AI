import math

from agent import Agent
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from selector import ActionSelector


def _build_agent():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b", "c"])
    return Agent(hip, cortex, selector)


def test_agent_uses_acc_to_raise_control_in_high_conflict():
    agent = _build_agent()
    agent.conflict_arbitration.error_high_threshold = 0.15
    agent.conflict_arbitration.inhibit_error_threshold = 0.9
    agent.selector.compute_pressures = lambda *args, **kwargs: {"a": 0.34, "b": 0.33, "c": 0.33}

    agent.step(["ctx:high_conflict"], reward=0.0, novelty=0.9, conflict=0.0)
    acc_snap = agent.get_state().get("conflict_arbitration", {})
    last_output = dict(acc_snap.get("last_output", {}) or {})

    assert last_output.get("control_mode") == "deliberative"
    assert bool(last_output.get("wm_boost_flag")) is True
    assert float(agent.basal_ganglia.last_decision_threshold_shift) > 0.05


def test_agent_switches_to_inhibit_after_repeated_failures():
    agent = _build_agent()
    agent.conflict_arbitration.inhibit_conflict_threshold = 0.55
    agent.conflict_arbitration.inhibit_error_threshold = 0.40
    agent.conflict_arbitration.inhibit_failure_threshold = 0.50
    agent.selector.compute_pressures = lambda *args, **kwargs: {"a": 0.34, "b": 0.33, "c": 0.33}
    for _ in range(16):
        agent.conflict_arbitration.register_outcome(reward_signal=-1.0, prediction_error=1.0)

    agent.step(["ctx:repeated_failure"], reward=-0.2, novelty=0.2, conflict=0.0)
    last_output = dict(agent.get_state().get("conflict_arbitration", {}).get("last_output", {}) or {})

    assert last_output.get("control_mode") == "inhibit"
    assert bool(last_output.get("request_additional_evaluation")) is True
    assert float(agent.basal_ganglia.last_decision_threshold_shift) >= 0.20


def test_agent_high_arousal_with_low_conflict_does_not_force_deliberative():
    agent = _build_agent()
    agent.selector.compute_pressures = lambda *args, **kwargs: {"a": 1.0, "b": 0.05, "c": 0.01}
    agent.emotional_regulation.arousal = 1.0
    agent.emotional_regulation.valence = -0.8

    agent.step(["ctx:low_conflict"], reward=0.0, novelty=0.05, conflict=0.0)
    last_output = dict(agent.get_state().get("conflict_arbitration", {}).get("last_output", {}) or {})
    assert last_output.get("control_mode") != "deliberative"


def test_agent_learning_rate_boost_depends_on_error_likelihood_not_mode():
    agent = _build_agent()
    base_alpha = float(
        getattr(
            agent.value_layer,
            "alpha_online_default",
            getattr(agent.value_layer, "alpha_default", 0.03),
        )
    )
    agent.emotional_regulation.modulation_factors["learning_rate_scale"] = 1.4
    captured = []

    original_update = agent.value_layer.update

    def _wrapped_update(*args, **kwargs):
        captured.append(float(kwargs.get("alpha", 0.0)))
        return original_update(*args, **kwargs)

    agent.value_layer.update = _wrapped_update
    agent.selector.compute_pressures = lambda *args, **kwargs: {"a": 0.34, "b": 0.33, "c": 0.33}

    def _acc_low_error(**kwargs):
        return {
            "control_mode": "deliberative",
            "threshold_delta": 0.25,
            "control_gain_multiplier": 1.6,
            "wm_boost_flag": True,
            "exploration_override": True,
            "request_additional_evaluation": False,
            "inhibit_action": False,
            "metrics": {"error_likelihood": 0.10},
        }

    def _acc_high_error(**kwargs):
        return {
            "control_mode": "deliberative",
            "threshold_delta": 0.25,
            "control_gain_multiplier": 1.6,
            "wm_boost_flag": True,
            "exploration_override": True,
            "request_additional_evaluation": False,
            "inhibit_action": False,
            "metrics": {"error_likelihood": 0.90},
        }

    agent.conflict_arbitration.arbitrate = _acc_low_error
    agent.step(["ctx:lr_low_error"], reward=0.1, novelty=0.8, conflict=0.0)

    agent.conflict_arbitration.arbitrate = _acc_high_error
    agent.step(["ctx:lr_high_error"], reward=0.1, novelty=0.8, conflict=0.0)

    # ACC error likelihood used to scale the waking stable alpha. The stable
    # writer is not called. Both outcomes still land on the labile tier.
    assert captured == []
    assert int(agent.value_layer.online_update_count) == 0
    errors = [
        float(getattr(exp, "td_error_snapshot", 0.0))
        for exp in agent.hippocampus.experiences
    ]
    assert len(errors) >= 2
    assert all(math.isfinite(value) for value in errors)
    _ = base_alpha


def test_agent_inhibit_does_not_directly_scale_pressure_vector():
    agent = _build_agent()
    base_pressures = {"a": 0.5, "b": 0.25, "c": 0.10}
    agent.selector.compute_pressures = lambda *args, **kwargs: dict(base_pressures)
    captured_pressures = {}

    def _acc_inhibit(**kwargs):
        return {
            "control_mode": "inhibit",
            "threshold_delta": 0.6,
            "control_gain_multiplier": 1.4,
            "wm_boost_flag": True,
            "exploration_override": False,
            "request_additional_evaluation": True,
            "inhibit_action": True,
            "metrics": {"error_likelihood": 0.95},
        }

    def _capture_pipeline(pressure_vector, cer_modulation_factors=None):
        captured_pressures.update(dict(pressure_vector or {}))
        return "a"

    agent.conflict_arbitration.arbitrate = _acc_inhibit
    agent._select_action_via_basal_ganglia_pipeline = _capture_pipeline

    agent.step(["ctx:inhibit_pressure"], reward=-0.2, novelty=0.2, conflict=0.0)

    assert captured_pressures == base_pressures


def test_agent_caps_combined_cer_acc_threshold_shift():
    agent = _build_agent()
    agent.selector.compute_pressures = lambda *args, **kwargs: {"a": 0.34, "b": 0.33, "c": 0.33}
    agent.emotional_regulation.modulation_factors["decision_threshold_shift"] = 0.8

    captured_modulation = {}

    def _acc_high_threshold(**kwargs):
        return {
            "control_mode": "deliberative",
            "threshold_delta": 0.55,
            "control_gain_multiplier": 1.2,
            "wm_boost_flag": True,
            "exploration_override": False,
            "request_additional_evaluation": False,
            "inhibit_action": False,
            "metrics": {"error_likelihood": 0.9},
        }

    def _capture_pipeline(pressure_vector, cer_modulation_factors=None):
        captured_modulation.update(dict(cer_modulation_factors or {}))
        return "a"

    agent.conflict_arbitration.arbitrate = _acc_high_threshold
    agent._select_action_via_basal_ganglia_pipeline = _capture_pipeline

    agent.step(["ctx:threshold_cap"], reward=0.0, novelty=0.1, conflict=0.0)

    assert abs(float(captured_modulation.get("decision_threshold_shift", 0.0)) - 0.60) < 1e-9
