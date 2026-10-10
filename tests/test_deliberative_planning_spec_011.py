import pytest

import agent as agent_module
from agent import Agent
from experience import Event, EventType, Experience, Path
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("eat", "rest")):
    hip = NOWAHippocampus(max_experiences=2000)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(hip, cortex, selector, sleep, intent)
    for action in actions:
        agent.register_action_channel(action, go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)
    sleep._rng.seed(0)
    return agent


def _append_memory(agent: Agent, context: str, action: str, reward: float, ts: float) -> Experience:
    path = Path().add_event(Event(context, event_type=EventType.CONTEXT))
    path = path.add_event(Event(f"action:{action}", event_type=EventType.ACTION))
    exp = Experience(path=path, consequence=None, intensity=1.0, reward=reward)
    snapshot = agent._build_value_state_snapshot(
        context_events=[context],
        action=action,
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    exp.value_state_snapshot = dict(snapshot)
    exp.value_state_key = agent.value_layer.encoder.encode(snapshot)
    exp.replay_action_id = str(action)
    exp.timestamp = float(ts)
    agent.hippocampus.experiences.append(exp)
    return exp


def test_deliberative_planning_biases_toward_rewarded_action():
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.2, ts=1.0)
    rest_start = _append_memory(agent, context="ctx_food", action="rest", reward=0.0, ts=2.0)
    rest_tail = _append_memory(agent, context="ctx_food", action="rest", reward=0.8, ts=3.0)
    rest_start.next_experience = rest_tail

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )
    assert meta["planning_bias_applied"] is True
    assert planned["rest"] > planned["eat"]


def test_step_does_not_call_selector_pre_modulation():
    agent = _build_agent(actions=("eat", "rest"))

    def _boom(*_args, **_kwargs):
        raise AssertionError("selector pre-modulation should not run in BG pipeline")

    agent.selector.apply_decision_modulation = _boom
    agent.decision_arbitrator.base_threshold = -1.0
    agent.decision_arbitrator.min_threshold = -1.0
    agent.decision_arbitrator.hysteresis_margin = 0.0

    action = agent.step(
        context_events=["ctx_food"],
        consequence=None,
        intensity=1.0,
        reward=0.2,
        novelty=0.0,
        conflict=0.0,
    )
    assert action in {"eat", "rest"}


def test_step_reports_deliberative_planning_v2_telemetry():
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=1.0, ts=1.0)
    _append_memory(agent, context="ctx_food", action="eat", reward=0.8, ts=2.0)
    _append_memory(agent, context="ctx_food", action="rest", reward=-0.5, ts=3.0)

    def _force_deliberative(**_kwargs):
        return {
            "decision_mode": "DELIBERATIVE",
            "global_uncertainty": 0.7,
            "global_uncertainty_raw": 0.7,
            "uncertainty_ema": 0.7,
            "policy_temperature": 0.35,
            "policy_reliability": 0.9,
        }

    agent.decision_arbitrator.arbitrate = _force_deliberative

    _ = agent.step(
        context_events=["ctx_food"],
        consequence=None,
        intensity=1.0,
        reward=0.1,
        novelty=0.0,
        conflict=0.0,
    )
    snap = dict(getattr(agent, "_last_decision_arbitration_output", {}) or {})
    assert snap.get("planning_rollout_depth", 0) >= 1
    assert 1 <= snap.get("planning_rollout_samples", 0) <= 8
    assert snap.get("planning_rollout_used", 0) >= 0
    assert snap.get("planning_exploration_bonus_mean", 0.0) >= 0.0
    assert snap.get("planning_temperature_factor", 0.0) == 1.0


def test_deliberative_planning_uses_action_index_subsets():
    agent = _build_agent(actions=("eat", "rest", "play"))
    for i in range(6):
        _append_memory(agent, context="ctx_food", action="eat", reward=0.2, ts=float(i))
    for i in range(3):
        _append_memory(agent, context="ctx_food", action="rest", reward=0.1, ts=float(10 + i))
    for i in range(2):
        _append_memory(agent, context="ctx_food", action="play", reward=-0.1, ts=float(20 + i))

    seen_lengths = {}

    def _spy(action_id, action_snapshot, action_experiences):
        seen_lengths[str(action_id)] = len(list(action_experiences or []))
        if action_id == "eat":
            return 1.0, 1.0
        return 0.0, 0.0

    agent._estimate_action_reward_from_memory = _spy
    _ = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5, "play": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )
    assert seen_lengths.get("eat") == 6
    assert seen_lengths.get("rest") == 3
    assert seen_lengths.get("play") == 2


def test_estimate_rollout_value_uses_max_trajectory():
    agent = _build_agent(actions=("eat",))

    def _make_exp(reward: float) -> Experience:
        path = Path().add_event(Event("ctx_food", event_type=EventType.CONTEXT))
        path = path.add_event(Event("action:eat", event_type=EventType.ACTION))
        exp = Experience(path=path, consequence=None, intensity=1.0, reward=reward)
        exp.replay_action_id = "eat"
        return exp

    exp_a = _make_exp(0.1)
    exp_b = _make_exp(0.0)
    exp_b_tail = _make_exp(1.0)
    exp_b.next_experience = exp_b_tail
    exp_c = _make_exp(0.3)
    experiences = [exp_a, exp_b, exp_c]
    value = agent._estimate_rollout_value(
        start_action="eat",
        experiences=experiences,
        depth=2,
        gamma=0.9,
    )
    assert value == pytest.approx(0.9, abs=1e-9)


def test_deliberative_planning_scales_rollout_depth_with_uncertainty():
    agent = _build_agent(actions=("eat",))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.1, ts=1.0)
    agent.planning_rollout_depth = 2
    agent.planning_uncertainty_depth_gain = 3.0
    seen_depths = []

    def _reward_stub(action_id, action_snapshot, action_experiences):
        return 0.0, 1.0

    def _rollout_spy(start_action, experiences, depth, gamma):
        seen_depths.append(int(depth))
        return 0.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = _rollout_spy

    _ = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.0},
    )
    low_depth = seen_depths[-1]

    _ = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 1.0},
    )
    high_depth = seen_depths[-1]
    assert low_depth == 2
    assert high_depth == 5


def test_deliberative_planning_adds_voi_bonus_to_low_confidence_actions():
    agent = _build_agent(actions=("eat", "rest"))
    eat_exp = _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0)
    rest_exp = _append_memory(agent, context="ctx_food", action="rest", reward=0.0, ts=2.0)
    eat_exp.expectation_confidence_score = 0.9
    rest_exp.expectation_confidence_score = 0.1
    agent.planning_exploration_gain = 0.5
    agent.planning_min_confidence = 0.0
    agent.planning_gain = 0.4

    def _reward_stub(action_id, action_snapshot, action_experiences):
        return 0.0, 1.0

    def _rollout_stub(start_action, experiences, depth, gamma):
        return 0.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = _rollout_stub
    agent.value_layer.get_value = lambda _state: 0.0

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )
    assert meta["planning_bias_applied"] is True
    assert planned["rest"] > planned["eat"]


def test_deliberative_planning_reports_exploration_bonus_formula():
    agent = _build_agent(actions=("eat",))
    exp = _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0)
    exp.expectation_confidence_score = 0.1
    agent.planning_exploration_gain = 0.15
    agent.planning_min_confidence = 0.0

    def _reward_stub(action_id, action_snapshot, action_experiences):
        return 0.0, 1.0

    def _rollout_stub(start_action, experiences, depth, gamma):
        return 0.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = _rollout_stub
    agent.value_layer.get_value = lambda _state: 0.0

    _planned, meta = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )
    assert meta["planning_bias_applied"] is True
    assert meta["exploration_bonus_mean"] == pytest.approx(0.135, abs=1e-9)


def test_deliberative_planning_disabled_keeps_pressure_unchanged():
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.8, ts=1.0)
    _append_memory(agent, context="ctx_food", action="rest", reward=0.1, ts=2.0)
    agent.deliberative_planning_enabled = False
    base = {"eat": 0.4, "rest": 0.4}

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector=base,
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.9},
    )

    assert planned == base
    assert meta["planning_bias_applied"] is False


def test_deliberative_planning_skips_when_memory_absent():
    agent = _build_agent(actions=("eat", "rest"))
    base = {"eat": 0.4, "rest": 0.4}

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector=base,
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.9},
    )

    assert planned == base
    assert meta["planning_bias_applied"] is False


def test_deliberative_planning_skips_actions_below_support_or_confidence_threshold():
    agent = _build_agent(actions=("eat", "rest"))
    eat_exp = _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0)
    rest_exp = _append_memory(agent, context="ctx_food", action="rest", reward=0.0, ts=2.0)
    eat_exp.expectation_confidence_score = 0.9
    rest_exp.expectation_confidence_score = 0.1
    agent.planning_min_confidence = 0.2

    def _reward_stub(action_id, action_snapshot, action_experiences):
        if action_id == "eat":
            return 0.0, 0.04
        return 0.0, 1.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = lambda *args, **kwargs: 0.0
    agent.value_layer.get_value = lambda _state: 0.0

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )

    assert planned == {"eat": 0.5, "rest": 0.5}
    assert meta["planning_bias_applied"] is False
    assert meta["supported_actions"] == 0


def test_deliberative_planning_enforces_v2_complexity_limits():
    actions = tuple(f"a{i:02d}" for i in range(40))
    agent = _build_agent(actions=actions)
    for idx, action in enumerate(actions):
        exp = _append_memory(agent, context="ctx_food", action=action, reward=0.0, ts=float(idx))
        exp.expectation_confidence_score = 0.9

    agent.planning_rollout_samples = 20
    agent.planning_rollout_depth = 10
    agent.planning_uncertainty_depth_gain = 10.0
    agent.planning_min_confidence = 0.0
    seen_depths = []
    rollout_calls = {"count": 0}

    def _reward_stub(action_id, action_snapshot, action_experiences):
        return 0.0, 1.0

    def _rollout_spy(start_action, experiences, depth, gamma):
        rollout_calls["count"] += 1
        seen_depths.append(int(depth))
        return 0.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = _rollout_spy
    agent.value_layer.get_value = lambda _state: 0.0

    _planned, meta = agent._apply_deliberative_planning(
        pressure_vector={action: 0.5 for action in actions},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 1.0},
    )

    assert rollout_calls["count"] <= 32
    assert max(seen_depths) <= 6
    assert meta["rollout_depth"] <= 6
    assert meta["rollout_samples"] == 8


def test_deliberative_planning_rollout_uses_similarity_filtered_experiences():
    agent = _build_agent(actions=("eat",))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.2, ts=1.0)
    _append_memory(agent, context="ctx_sleep", action="eat", reward=0.9, ts=2.0)
    seen = {}

    def _reward_stub(action_id, action_snapshot, action_experiences):
        return 0.0, 1.0

    def _rollout_spy(start_action, experiences, depth, gamma):
        seen["count"] = len(list(experiences or []))
        return 0.0

    original_similarity = agent_module.state_similarity

    def _similarity(state_a, state_b, encoder=None):
        sig_a = str((state_a or {}).get("context_signature", ""))
        sig_b = str((state_b or {}).get("context_signature", ""))
        return 1.0 if sig_a == sig_b else 0.0

    agent._estimate_action_reward_from_memory = _reward_stub
    agent._estimate_rollout_value = _rollout_spy
    agent_module.state_similarity = _similarity
    try:
        _ = agent._apply_deliberative_planning(
            pressure_vector={"eat": 0.5},
            context_events=["ctx_food"],
            intensity=1.0,
            novelty=0.0,
            conflict=0.0,
            decision_state={},
        )
    finally:
        agent_module.state_similarity = original_similarity

    assert seen.get("count") == 1


def test_step_passes_global_uncertainty_to_planning_state():
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.8, ts=1.0)
    agent.decision_arbitrator.base_threshold = -1.0
    agent.decision_arbitrator.min_threshold = -1.0
    agent.decision_arbitrator.hysteresis_margin = 0.0
    captured = {}

    def _planning_spy(pressure_vector, context_events, intensity, novelty, conflict, decision_state=None):
        captured["global_uncertainty"] = float((decision_state or {}).get("global_uncertainty", -1.0))
        return pressure_vector, {"planning_bias_applied": False, "supported_actions": 0, "support_mean": 0.0}

    agent._apply_deliberative_planning = _planning_spy
    _ = agent.step(
        context_events=["ctx_food"],
        consequence=None,
        intensity=1.0,
        reward=0.1,
        novelty=0.0,
        conflict=0.0,
    )
    assert captured.get("global_uncertainty", -1.0) >= 0.0
