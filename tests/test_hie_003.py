import agent as agent_module
import hippocampal_imagine_engine as hie_module
from agent import Agent
from experience import Event, EventType, Experience, Path
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("eat", "rest", "climb")):
    hip = NOWAHippocampus(max_experiences=4000)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(hip, cortex, selector, sleep, intent)
    for action in actions:
        agent.register_action_channel(action, go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)
    sleep._rng.seed(0)
    return agent


def _append_memory(
    agent: Agent,
    *,
    context: str,
    action: str,
    reward: float,
    ts: float,
    next_context: str = "",
) -> Experience:
    path = Path().add_event(Event(context, event_type=EventType.CONTEXT))
    path = path.add_event(Event(f"action:{action}", event_type=EventType.ACTION))
    exp = Experience(path=path, consequence=None, intensity=1.0, reward=reward)
    state_snapshot = agent._build_value_state_snapshot(
        context_events=[context],
        action=action,
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    next_snapshot = agent._build_value_state_snapshot(
        context_events=[str(next_context or context)],
        action="",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    exp.value_state_snapshot = dict(state_snapshot)
    exp.value_next_state_snapshot = dict(next_snapshot)
    exp.value_state_key = agent.value_layer.encoder.encode(state_snapshot)
    exp.replay_action_id = str(action)
    exp.timestamp = float(ts)
    exp.expectation_confidence_score = 1.0
    agent.hippocampus.experiences.append(exp)
    return exp


def _patch_exact_similarity(monkeypatch):
    def _similarity(state_a, state_b, encoder=None):
        sig_a = str((state_a or {}).get("context_signature", ""))
        sig_b = str((state_b or {}).get("context_signature", ""))
        return 1.0 if sig_a == sig_b else 0.0

    monkeypatch.setattr(agent_module, "state_similarity", _similarity)
    monkeypatch.setattr(hie_module, "state_similarity", _similarity)


def _patch_uniform_similarity(monkeypatch):
    def _similarity(_state_a, _state_b, encoder=None):
        return 1.0

    monkeypatch.setattr(agent_module, "state_similarity", _similarity)
    monkeypatch.setattr(hie_module, "state_similarity", _similarity)


def test_hie003_action_tree_returns_action_values(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("a1", "a2", "a3"))
    agent.imagination_enable_action_sequences = True
    agent.imagination_action_branching = 3
    agent.imagination_action_temperature = 0.05
    _append_memory(
        agent,
        context="ctx_start",
        action="a1",
        reward=0.0,
        ts=1.0,
        next_context="ctx_mid",
    )
    _append_memory(
        agent,
        context="ctx_mid",
        action="a2",
        reward=1.0,
        ts=2.0,
        next_context="ctx_goal",
    )
    _append_memory(
        agent,
        context="ctx_start",
        action="a3",
        reward=0.0,
        ts=3.0,
        next_context="ctx_dead",
    )
    _append_memory(
        agent,
        context="ctx_dead",
        action="a2",
        reward=-0.5,
        ts=4.0,
        next_context="ctx_dead",
    )
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_start"],
        action="",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    result = agent._generate_action_tree_imagination(
        start_state=start_state,
        candidate_actions=["a1", "a2", "a3"],
        experiences=list(agent.hippocampus.experiences),
        depth=4,
    )

    trajectories = list(result.get("trajectories", []) or [])
    action_values = dict(result.get("action_values", {}) or {})
    assert trajectories
    assert "a1" in action_values
    assert "a3" in action_values
    assert action_values["a1"] > action_values["a3"]
    assert int(result.get("nodes_visited", 0)) <= 128
    assert int(result.get("edges_visited", 0)) >= 0

    trajectory = trajectories[0]
    assert isinstance(str(trajectory.root_action), str)
    assert isinstance(float(trajectory.cumulative_reward), float)
    assert isinstance(float(trajectory.terminal_state_value), float)


def test_hie003_planning_uses_value_blend_for_imagined_value(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0, next_context="ctx_food")
    _append_memory(agent, context="ctx_food", action="rest", reward=0.0, ts=2.0, next_context="ctx_food")
    agent.imagination_enable_action_sequences = True
    agent.imagination_enabled = True
    agent.planning_min_confidence = 0.0
    agent.planning_gain = 0.3
    agent.value_layer.get_value = lambda _state: 0.0
    agent._estimate_action_reward_from_memory = lambda *_args, **_kwargs: (0.0, 1.0)
    agent._estimate_rollout_value = lambda start_action, *_args, **_kwargs: (10.0 if str(start_action) == "eat" else 0.0)

    tree_calls = {"count": 0}

    def _tree_stub(start_state, candidate_actions, experiences, depth):
        tree_calls["count"] += 1
        return {
            "trajectories": [],
            "values": [0.0, 10.0],
            "action_values": {"eat": 0.0, "rest": 10.0},
            "nodes_visited": 7,
            "edges_visited": 9,
            "novelty_hits": 1,
        }

    agent._generate_action_tree_imagination = _tree_stub

    agent.imagination_value_blend = 0.0
    planned_memory, _meta_memory = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )
    agent.imagination_value_blend = 1.0
    planned_imagined, meta_imagined = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={},
    )

    assert planned_memory["eat"] > planned_memory["rest"]
    assert planned_imagined["rest"] > planned_imagined["eat"]
    assert tree_calls["count"] == 2
    assert int(meta_imagined.get("imagination_tree_nodes", 0)) == 7
    assert int(meta_imagined.get("imagination_tree_edges", 0)) == 9
    assert int(meta_imagined.get("imagination_action_count", 0)) == 2


def test_hie003_tree_complexity_limits_are_enforced(monkeypatch):
    _patch_uniform_similarity(monkeypatch)
    agent = _build_agent(actions=("walk", "jump", "rest", "look", "hide"))
    agent.imagination_enable_action_sequences = True
    agent.imagination_action_branching = 99
    agent.imagination_max_tree_nodes = 999
    agent.imagination_depth = 99
    for idx in range(300):
        _append_memory(
            agent,
            context=f"ctx_{idx % 7}",
            action=("walk", "jump", "rest", "look")[idx % 4],
            reward=0.1,
            ts=float(idx),
            next_context=f"ctx_{(idx + 1) % 7}",
        )

    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_0"],
        action="",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    result = agent._generate_action_tree_imagination(
        start_state=start_state,
        candidate_actions=["walk", "jump", "rest", "look", "hide"],
        experiences=list(agent.hippocampus.experiences),
        depth=99,
    )
    trajectories = list(result.get("trajectories", []) or [])
    max_depth = max((int(getattr(trajectory, "depth", 0)) for trajectory in trajectories), default=0)

    assert int(result.get("nodes_visited", 0)) <= 128
    assert int(result.get("edges_visited", 0)) >= 0
    assert max_depth <= 5


def test_hie003_step_telemetry_includes_tree_fields(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat", "rest"))
    _append_memory(agent, context="ctx_food", action="eat", reward=0.2, ts=1.0, next_context="ctx_food")
    _append_memory(agent, context="ctx_food", action="rest", reward=0.2, ts=2.0, next_context="ctx_food")
    agent.imagination_enable_action_sequences = True

    def _force_deliberative(**_kwargs):
        return {
            "decision_mode": "DELIBERATIVE",
            "global_uncertainty": 0.6,
            "global_uncertainty_raw": 0.6,
            "uncertainty_ema": 0.6,
            "policy_temperature": 0.35,
            "policy_reliability": 0.9,
        }

    agent.decision_arbitrator.arbitrate = _force_deliberative
    agent._generate_action_tree_imagination = lambda **_kwargs: {
        "trajectories": [],
        "values": [1.0],
        "action_values": {"eat": 1.0},
        "nodes_visited": 3,
        "edges_visited": 4,
        "novelty_hits": 0,
    }

    _ = agent.step(
        context_events=["ctx_food"],
        consequence=None,
        intensity=1.0,
        reward=0.1,
        novelty=0.0,
        conflict=0.0,
    )
    snap = dict(getattr(agent, "_last_decision_arbitration_output", {}) or {})
    assert "planning_imagination_tree_nodes" in snap
    assert "planning_imagination_tree_edges" in snap
    assert "planning_imagination_action_count" in snap
    assert "planning_imagination_branching" in snap

