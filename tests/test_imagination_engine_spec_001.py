import agent as agent_module
import hippocampal_imagine_engine as hie_module
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
    target_context = str(next_context or context)
    next_snapshot = agent._build_value_state_snapshot(
        context_events=[target_context],
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
    agent.hippocampus.experiences.append(exp)
    return exp


def _patch_exact_similarity(monkeypatch) -> None:
    def _similarity(state_a, state_b, encoder=None):
        sig_a = str((state_a or {}).get("context_signature", ""))
        sig_b = str((state_b or {}).get("context_signature", ""))
        return 1.0 if sig_a == sig_b else 0.0

    monkeypatch.setattr(agent_module, "state_similarity", _similarity)
    monkeypatch.setattr(hie_module, "state_similarity", _similarity)


def test_imagination_produces_trajectories(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("go_left", "climb_tree"))
    agent.imagination_similarity_threshold = 0.6
    agent.imagination_novelty_bonus = 0.0
    _append_memory(
        agent,
        context="ctx_food",
        action="go_left",
        reward=0.0,
        ts=1.0,
        next_context="ctx_branch",
    )
    _append_memory(
        agent,
        context="ctx_branch",
        action="climb_tree",
        reward=1.0,
        ts=2.0,
        next_context="ctx_eat",
    )
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_food"],
        action="go_left",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    values = agent._generate_imagined_rollouts(
        start_state=start_state,
        action_id="go_left",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
    )

    assert values
    assert max(values) > 0.0


def test_imagination_similarity_filtering(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat",))
    agent.imagination_similarity_threshold = 0.8
    agent.imagination_novelty_bonus = 0.0
    agent.imagination_goal_bias = 0.0
    agent.imagination_state_novelty_weight = 0.0
    _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0, next_context="ctx_food")
    _append_memory(agent, context="ctx_noise", action="eat", reward=2.0, ts=2.0, next_context="ctx_noise")
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_food"],
        action="eat",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    values = agent._generate_imagined_rollouts(
        start_state=start_state,
        action_id="eat",
        experiences=list(agent.hippocampus.experiences),
        depth=3,
    )

    assert values
    assert max(values) <= 0.0


def test_imagination_rollout_count_is_bounded(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat",))
    agent.imagination_samples = 99
    agent.imagination_depth = 1
    _append_memory(agent, context="ctx_food", action="eat", reward=0.0, ts=1.0, next_context="ctx_food")
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_food"],
        action="eat",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    values = agent._generate_imagined_rollouts(
        start_state=start_state,
        action_id="eat",
        experiences=list(agent.hippocampus.experiences),
        depth=1,
    )

    assert len(values) <= 8


def test_imagination_depth_is_bounded(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("walk",))
    agent.imagination_depth = 99
    agent.imagination_samples = 1
    for idx in range(8):
        _append_memory(
            agent,
            context=f"ctx_{idx}",
            action="walk",
            reward=0.0,
            ts=float(idx),
            next_context=f"ctx_{idx + 1}",
        )
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_0"],
        action="walk",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    _ = agent._generate_imagined_rollouts(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=20,
    )

    assert int(agent._last_imagination_stats.get("max_depth_reached", 0)) <= 5


def test_planning_integration_boosts_reward_delayed_action(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat", "rest", "climb"))
    agent.imagination_enabled = True
    agent.imagination_novelty_bonus = 0.0
    agent.planning_similarity_threshold = 0.6
    agent.planning_gain = 0.3
    agent.planning_min_confidence = 0.0
    _append_memory(
        agent,
        context="ctx_food",
        action="eat",
        reward=0.0,
        ts=1.0,
        next_context="ctx_food",
    )
    _append_memory(
        agent,
        context="ctx_food",
        action="rest",
        reward=0.0,
        ts=2.0,
        next_context="ctx_branch",
    )
    _append_memory(
        agent,
        context="ctx_branch",
        action="climb",
        reward=1.0,
        ts=3.0,
        next_context="ctx_goal",
    )

    planned, meta = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5, "climb": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.8},
    )

    assert meta["planning_bias_applied"] is True
    assert meta["imagined_rollouts_used"] > 0
    assert planned["rest"] > 0.5


def test_planning_without_imagination_matches_legacy_path(monkeypatch):
    _patch_exact_similarity(monkeypatch)
    agent = _build_agent(actions=("eat", "rest", "climb"))
    agent.imagination_enable_action_sequences = False
    agent.imagination_enabled = False
    agent.planning_similarity_threshold = 0.6
    agent.planning_gain = 0.3
    agent.planning_min_confidence = 0.0
    _append_memory(
        agent,
        context="ctx_food",
        action="eat",
        reward=0.0,
        ts=1.0,
        next_context="ctx_food",
    )
    _append_memory(
        agent,
        context="ctx_food",
        action="rest",
        reward=0.0,
        ts=2.0,
        next_context="ctx_branch",
    )
    _append_memory(
        agent,
        context="ctx_branch",
        action="climb",
        reward=1.0,
        ts=3.0,
        next_context="ctx_goal",
    )

    def _boom(*_args, **_kwargs):
        raise AssertionError("imagination should not be called when disabled")

    agent._generate_structured_imagination = _boom
    planned_disabled, meta_disabled = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5, "climb": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.8},
    )

    assert meta_disabled["imagination_enabled"] is False

    def _imagine_stub(start_state, action_id, experiences, depth):
        if str(action_id) == "rest":
            values = [2.0]
        else:
            values = [0.0]
        return {
            "trajectories": [],
            "values": values,
            "nodes_visited": 1,
            "novelty_hits": 0,
        }

    agent.imagination_enabled = True
    agent.imagination_enable_action_sequences = False
    agent._generate_structured_imagination = _imagine_stub
    planned_enabled, _ = agent._apply_deliberative_planning(
        pressure_vector={"eat": 0.5, "rest": 0.5, "climb": 0.5},
        context_events=["ctx_food"],
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
        decision_state={"global_uncertainty": 0.8},
    )

    assert planned_enabled["rest"] > planned_disabled["rest"]
