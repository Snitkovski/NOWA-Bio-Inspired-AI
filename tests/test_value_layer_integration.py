
import pytest
from learning_guard import learning_allowed

@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct tests of stable writers. Sleep opens the same guard."""
    with learning_allowed():
        yield

from agent import Agent
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from neuromodulators import NeuromodulatorState
from selector import ActionSelector
from sleep import SleepManager
from stability_monitoring import StabilityMonitoringLayer
from value_layer import ValueLayer


def _build_agent():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    return Agent(hip, cortex, selector, sleep_mgr, intent_mem)


def test_agent_positive_surprise_updates_value_and_dopamine():
    agent = _build_agent()
    initial_da = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))

    agent.step(
        context_events=["ctx:positive"],
        reward=0.8,
        novelty=0.1,
        conflict=0.0,
        intensity=1.0,
    )

    value_snapshot = agent.value_layer.snapshot()
    da_after = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))

    assert value_snapshot["last_td_error"] > 0.0
    assert value_snapshot["last_dopamine_delta"] > 0.0
    assert da_after > initial_da


def test_agent_negative_surprise_decreases_value_and_dopamine():
    agent = _build_agent()

    agent.step(
        context_events=["ctx:bootstrap"],
        reward=0.4,
        novelty=0.0,
        conflict=0.0,
        intensity=1.0,
    )
    da_before = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))

    agent.step(
        context_events=["ctx:negative"],
        reward=-0.8,
        novelty=0.0,
        conflict=0.2,
        intensity=1.0,
    )

    value_snapshot = agent.value_layer.snapshot()
    da_after = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))

    assert value_snapshot["last_td_error"] < 0.0
    assert value_snapshot["last_dopamine_delta"] < 0.0
    assert da_after < da_before


def test_dopamine_isolation_no_feedback_cycle_into_td_reward():
    agent = _build_agent()

    # First update with zero reward should keep TD near zero.
    agent.step(
        context_events=["ctx:steady"],
        reward=0.0,
        novelty=0.0,
        conflict=0.0,
        intensity=1.0,
    )
    td_first = float(agent.value_layer.snapshot().get("last_td_error", 0.0))

    # Artificially shift dopamine and run same zero-reward transition again.
    agent.neuromodulators.dopamine = 1.0
    agent.step(
        context_events=["ctx:steady"],
        reward=0.0,
        novelty=0.0,
        conflict=0.0,
        intensity=1.0,
    )
    td_second = float(agent.value_layer.snapshot().get("last_td_error", 0.0))

    assert abs(td_first) < 1e-9
    assert abs(td_second) < 1e-9


def test_stability_stress_10000_updates_no_runaway():
    layer = ValueLayer(max_states=256)
    nm = NeuromodulatorState()
    monitor = StabilityMonitoringLayer(window_size=500, baseline_background=0.0)

    snapshot = {}
    for step in range(10_000):
        current = {
            "context_signature": f"s:{step % 32}",
            "context_size": 1,
            "action": "",
            "consequence": "",
            "intensity": 1.0,
            "novelty": 0.0,
            "conflict": 0.0,
        }
        nxt = {
            "context_signature": f"s:{(step + 1) % 32}",
            "context_size": 1,
            "action": "",
            "consequence": "",
            "intensity": 1.0,
            "novelty": 0.0,
            "conflict": 0.0,
        }
        reward = 0.05 if (step % 2 == 0) else -0.05
        update = layer.update(current, reward=reward, next_state_snapshot=nxt, timestamp=float(step + 1))

        nm.apply_dopamine_delta(layer.compute_dopamine_delta(update["td_error"]))
        nm.decay_over_time(1.0)

        snapshot = monitor.update(
            emotional_state_snapshot={"valence": 0.0, "arousal": 0.0, "threat": 0.0, "curiosity": 0.0},
            affective_background_snapshot={
                "background_anxiety": 0.0,
                "background_tension": 0.0,
                "background_satisfaction": 0.0,
                "background_interest": 0.0,
            },
            neuromodulators_snapshot=nm.snapshot(),
            expectations_snapshot={"expectations": [], "dominant_forecast": "", "global_outlook": "stabilizing"},
            regulation_snapshot={"regulation_active": False, "regulation_mode": "none"},
            semantic_emotions_snapshot=[],
            trigger_event=False,
            timestamp=float(step + 1),
        )

    assert all(-1.0 <= value <= 1.0 for value in layer.values.values())
    assert snapshot.get("drift_flags", {}).get("neuromodulator_drift") is False
    assert float(snapshot.get("stability_index", 0.0)) > 0.6


def test_agent_state_reports_value_drift_ratio_and_warning():
    agent = _build_agent()
    agent.step(
        context_events=["ctx:drift"],
        reward=0.2,
        novelty=0.0,
        conflict=0.0,
        intensity=1.0,
    )

    agent.value_layer.online_update_count = 1
    agent.value_layer.sleep_update_count = 10
    agent.value_layer.update_count = 11

    state = agent.get_state()
    assert abs(float(state.get("value_drift_ratio", 0.0)) - (10.0 / 2.0)) < 1e-9
    assert state.get("value_drift_warning") is True
    assert abs(float(agent.snapshot().get("value_drift_ratio", 0.0)) - (10.0 / 2.0)) < 1e-9


def test_td_sign_couples_to_exploration_bias_with_20_percent_cap():
    def _stub_acc(**_kwargs):
        return {
            "control_mode": "balanced",
            "threshold_delta": 0.0,
            "control_gain_multiplier": 1.0,
            "wm_boost_flag": False,
            "exploration_override": False,
            "request_additional_evaluation": False,
            "metrics": {"error_likelihood": 0.0},
        }

    pos = _build_agent()
    neg = _build_agent()
    pos.conflict_arbitration.arbitrate = _stub_acc
    neg.conflict_arbitration.arbitrate = _stub_acc
    pos.emotional_regulation.modulation_factors["exploration_bias"] = 0.5
    neg.emotional_regulation.modulation_factors["exploration_bias"] = 0.5

    pos.step(context_events=["ctx:pos"], reward=0.9, novelty=0.0, conflict=0.0, intensity=1.0)
    neg.step(context_events=["ctx:neg"], reward=-0.9, novelty=0.0, conflict=0.0, intensity=1.0)

    pos.emotional_regulation.modulation_factors["exploration_bias"] = 0.5
    neg.emotional_regulation.modulation_factors["exploration_bias"] = 0.5
    pos.step(context_events=["ctx:pos:2"], reward=0.0, novelty=0.0, conflict=0.0, intensity=1.0)
    neg.step(context_events=["ctx:neg:2"], reward=0.0, novelty=0.0, conflict=0.0, intensity=1.0)

    pos_bias = float(getattr(pos.basal_ganglia, "last_exploration_bias", 0.0))
    neg_bias = float(getattr(neg.basal_ganglia, "last_exploration_bias", 0.0))

    assert pos_bias < 0.5
    assert neg_bias > 0.5
    assert abs(pos_bias - 0.5) <= 0.1 + 1e-9
    assert abs(neg_bias - 0.5) <= 0.1 + 1e-9


def test_inhibit_mode_with_td_modulation_keeps_exploration_above_safety_floor():
    def _stub_acc_inhibit(**_kwargs):
        return {
            "control_mode": "inhibit",
            "threshold_delta": 0.1,
            "control_gain_multiplier": 1.2,
            "wm_boost_flag": True,
            "exploration_override": False,
            "request_additional_evaluation": True,
            "metrics": {"error_likelihood": 0.9},
        }

    agent = _build_agent()
    agent.conflict_arbitration.arbitrate = _stub_acc_inhibit
    agent.emotional_regulation.modulation_factors["exploration_bias"] = 0.0

    # Step 1 sets positive TD snapshot for the next-cycle pre-TD estimate.
    agent.step(context_events=["ctx:prime"], reward=0.9, novelty=0.0, conflict=0.0, intensity=1.0)
    # Step 2 applies inhibit-mode + positive TD coupling; guardrail should prevent collapse to 0.
    agent.step(context_events=["ctx:inhibit"], reward=0.0, novelty=0.0, conflict=0.0, intensity=1.0)

    bias = float(getattr(agent.basal_ganglia, "last_exploration_bias", 0.0))
    assert 0.05 <= bias <= 0.20
