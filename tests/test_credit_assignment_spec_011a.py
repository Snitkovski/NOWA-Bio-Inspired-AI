import math
from types import SimpleNamespace

from decision_arbitrator import DecisionArbitrator
from experience import Event, EventType, Experience, Path
from sleep import SleepManager
from value_layer import ValueLayer


def _make_experience(index: int, layer: ValueLayer) -> Experience:
    path = Path().add_event(Event(f"ctx{index}", event_type=EventType.CONTEXT))
    path = path.add_event(Event("action:move", event_type=EventType.ACTION))
    exp = Experience(path=path, consequence=None, intensity=1.0, reward=1.0)
    snapshot = {
        "context_signature": f"ctx{index}",
        "context_size": 1,
        "action": "move",
        "consequence": "",
        "intensity": 1.0,
        "novelty": 0.0,
        "conflict": 0.0,
    }
    exp.value_state_snapshot = dict(snapshot)
    exp.value_state_key = layer.encoder.encode(snapshot)
    exp.value_next_state_snapshot = dict(snapshot)
    exp.td_error_snapshot = 1.0
    exp._sleep_consolidation_score = 1.0
    exp._sleep_variance_gate = 1.0
    exp.timestamp = float(index)
    return exp


def test_credit_window_limits_updates():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.value_layer = ValueLayer()
    sleep.global_sleep_update_budget = 10.0
    sleep.delta_value_max_per_sleep = 1.0
    sleep.per_update_cap = 1.0
    sleep.max_l2_update_per_cycle = 10.0
    sleep.credit_window = 6

    experiences = [_make_experience(i, sleep.value_layer) for i in range(10)]
    stats = sleep._apply_replay_td_bg(experiences)
    assert stats["sleep_update_count"] <= 6
    assert len(sleep.value_layer.values) <= 6


def test_trace_decay_values():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.eligibility_lambda = 0.85
    assert math.isclose(sleep._eligibility_trace_for_depth(0), 1.0, abs_tol=1e-6)
    assert math.isclose(sleep._eligibility_trace_for_depth(1), 0.85, abs_tol=1e-2)
    assert math.isclose(sleep._eligibility_trace_for_depth(2), 0.72, abs_tol=1e-2)
    assert math.isclose(sleep._eligibility_trace_for_depth(3), 0.61, abs_tol=1e-2)


def test_replay_causality_filter_rejects():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    exp = _make_experience(0, ValueLayer())
    exp.reward = 0.2
    exp.state_distance = 0.8
    exp.action_stability = 0.4
    score = sleep._compute_causality_score(exp)
    assert score < float(getattr(sleep, "causality_threshold", 0.15))


def test_shock_override_allows_replay():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    exp = _make_experience(0, ValueLayer())
    exp.prediction_shock_score = 0.8
    exp.expectation_stability_score = 0.1
    assert sleep._replay_stability_gate(exp) is True


def test_td_clipping_sleep_replay():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.value_layer = ValueLayer()
    sleep.global_sleep_update_budget = 10.0
    sleep.delta_value_max_per_sleep = 1.0
    sleep.per_update_cap = 1.0
    sleep.max_l2_update_per_cycle = 10.0
    exp = _make_experience(0, sleep.value_layer)
    exp.td_error_snapshot = 3.5
    sleep._apply_replay_td_bg([exp])
    assert math.isclose(sleep.value_layer.last_td_error, 1.0, abs_tol=1e-6)


def test_causal_depth_tracks_distance_to_reward_anchor():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.value_layer = ValueLayer()
    sleep.global_sleep_update_budget = 10.0
    sleep.delta_value_max_per_sleep = 1.0
    sleep.per_update_cap = 1.0
    sleep.max_l2_update_per_cycle = 10.0
    sleep.credit_window = 2

    experiences = [_make_experience(i, sleep.value_layer) for i in range(5)]
    for exp in experiences:
        # Below the reward-anchor threshold, so the anchor stays on index 3.
        # The reward itself is the live TD; a stored snapshot is not the update.
        exp.reward = 0.05
        exp.td_error_snapshot = 0.8
        exp.value_terminal = True
    experiences[3].reward = 1.0

    depths = sleep._assign_reward_anchored_causal_depth(experiences, credit_window=2)
    assert depths[id(experiences[3])] == 0
    assert depths[id(experiences[2])] == 1
    assert depths[id(experiences[4])] == 1
    assert depths[id(experiences[1])] == 2

    stats = sleep._apply_replay_td_bg(experiences)
    assert stats["sleep_update_count"] == 3


def test_causal_depth_uses_largest_td_when_no_reward_anchor():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.value_layer = ValueLayer()

    experiences = [_make_experience(i, sleep.value_layer) for i in range(5)]
    td_values = [0.1, 0.3, 0.9, 0.2, 0.1]
    for exp, td in zip(experiences, td_values):
        exp.reward = 0.0
        exp.td_error_snapshot = float(td)

    depths = sleep._assign_reward_anchored_causal_depth(experiences, credit_window=4)
    assert depths[id(experiences[2])] == 0
    assert depths[id(experiences[1])] == 1
    assert depths[id(experiences[3])] == 1


def test_causal_depth_falls_back_to_middle_when_no_signal():
    dummy = SimpleNamespace()
    sleep = SleepManager(dummy, dummy)
    sleep.value_layer = ValueLayer()
    sleep.td_anchor_threshold = 10.0
    sleep.reward_anchor_threshold = 10.0

    experiences = [_make_experience(i, sleep.value_layer) for i in range(5)]
    for exp in experiences:
        exp.reward = 0.0
        exp.td_error_snapshot = 0.0
        exp.prediction_shock_flag = False

    depths = sleep._assign_reward_anchored_causal_depth(experiences, credit_window=4)
    assert depths[id(experiences[2])] == 0
    assert depths[id(experiences[1])] == 1
    assert depths[id(experiences[3])] == 1


def test_policy_reliability_collapse_forces_deliberation():
    arbitrator = DecisionArbitrator()
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata={"A": {"td_variance": 0.5}},
        error_likelihood=0.6,
        surprise=0.36,
        stress_level=0.0,
        action_stability_mean=0.3,
        causality_mean=0.2,
    )
    assert output["policy_reliability"] < 0.35
    assert output["decision_mode"] == "DELIBERATIVE"
