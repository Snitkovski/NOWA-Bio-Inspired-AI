import agent as agent_module
import hippocampal_imagine_engine as hie_module
from agent import Agent
from experience import Event, EventType, Experience, Path
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("walk", "jump", "link")):
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
    next_context: str,
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
        context_events=[str(next_context)],
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


def _patch_similarity(monkeypatch, stitched_pairs=None):
    stitched = set(stitched_pairs or set())

    def _similarity(state_a, state_b, encoder=None):
        sig_a = str((state_a or {}).get("context_signature", ""))
        sig_b = str((state_b or {}).get("context_signature", ""))
        if sig_a == sig_b:
            return 1.0
        if (sig_a, sig_b) in stitched:
            return 1.0
        return 0.0

    monkeypatch.setattr(agent_module, "state_similarity", _similarity)
    monkeypatch.setattr(hie_module, "state_similarity", _similarity)


def _ctx_signature(state) -> str:
    return str((state or {}).get("context_signature", ""))


def test_hie002_trajectory_recombination(monkeypatch):
    _patch_similarity(monkeypatch, stitched_pairs={("ctx_B", "ctx_C"), ("ctx_C", "ctx_B")})
    agent = _build_agent(actions=("walk", "jump"))
    _append_memory(
        agent,
        context="ctx_A",
        action="walk",
        reward=0.0,
        ts=1.0,
        next_context="ctx_B",
    )
    _append_memory(
        agent,
        context="ctx_C",
        action="jump",
        reward=1.0,
        ts=2.0,
        next_context="ctx_D",
    )

    engine = agent.imagination_engine
    engine.samples = 4
    engine.depth = 4
    engine.branching = 4
    engine.goal_bias = 0.0
    engine.state_novelty_weight = 0.0
    engine.confidence_decay = 1.0
    engine.reward_decay = 1.0
    engine.__post_init__()

    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_A"],
        action="walk",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    result = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )

    trajectories = list(result.get("trajectories", []) or [])
    assert trajectories
    recombined = False
    for trajectory in trajectories:
        path = [_ctx_signature(state) for state in list(getattr(trajectory, "states", []) or [])]
        if "ctx_B" in path and "ctx_D" in path and path.index("ctx_B") < path.index("ctx_D"):
            recombined = True
            break
    assert recombined is True


def test_hie002_novelty_bonus_increases_value(monkeypatch):
    _patch_similarity(monkeypatch)
    agent = _build_agent(actions=("walk", "link"))
    _append_memory(
        agent,
        context="ctx_A",
        action="walk",
        reward=0.0,
        ts=1.0,
        next_context="ctx_B",
    )
    _append_memory(
        agent,
        context="ctx_B",
        action="link",
        reward=0.0,
        ts=2.0,
        next_context="ctx_C",
    )
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_A"],
        action="walk",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    engine = agent.imagination_engine
    engine.samples = 4
    engine.depth = 4
    engine.branching = 1
    engine.goal_bias = 0.0
    engine.confidence_decay = 1.0
    engine.reward_decay = 1.0

    engine.state_novelty_weight = 0.0
    engine.__post_init__()
    base = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )

    engine.state_novelty_weight = 1.0
    engine.__post_init__()
    with_bonus = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )

    assert with_bonus.get("novelty_hits", 0) > 0
    assert max(with_bonus["values"]) > max(base["values"])


def test_hie002_confidence_decay_on_longer_trajectories(monkeypatch):
    _patch_similarity(monkeypatch)
    agent = _build_agent(actions=("walk", "link"))
    _append_memory(agent, context="ctx_A", action="walk", reward=0.0, ts=1.0, next_context="ctx_B")
    _append_memory(agent, context="ctx_B", action="link", reward=0.0, ts=2.0, next_context="ctx_C")
    _append_memory(agent, context="ctx_C", action="link", reward=0.0, ts=3.0, next_context="ctx_D")
    _append_memory(agent, context="ctx_D", action="link", reward=0.0, ts=4.0, next_context="ctx_E")
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_A"],
        action="walk",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    engine = agent.imagination_engine
    engine.samples = 1
    engine.branching = 1
    engine.goal_bias = 0.0
    engine.state_novelty_weight = 0.0
    engine.reward_decay = 1.0
    engine.confidence_decay = 0.8
    engine.__post_init__()

    shallow = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=1,
        gamma=0.95,
        value_layer=agent.value_layer,
    )
    deep = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )

    shallow_conf = float(shallow["trajectories"][0].confidence)
    deep_conf = float(deep["trajectories"][0].confidence)
    assert deep_conf < shallow_conf


def test_hie002_goal_bias_prefers_high_value_terminal_state(monkeypatch):
    _patch_similarity(monkeypatch)
    agent = _build_agent(actions=("high", "low", "link"))
    _append_memory(agent, context="ctx_A", action="high", reward=0.0, ts=1.0, next_context="ctx_B")
    _append_memory(agent, context="ctx_B", action="link", reward=0.0, ts=2.0, next_context="ctx_goal_high")
    _append_memory(agent, context="ctx_A", action="low", reward=0.0, ts=3.0, next_context="ctx_C")
    _append_memory(agent, context="ctx_C", action="link", reward=0.0, ts=4.0, next_context="ctx_goal_low")

    def _value_stub(state):
        sig = _ctx_signature(state)
        if sig == "ctx_goal_high":
            return 5.0
        if sig == "ctx_goal_low":
            return 0.0
        return 0.0

    agent.value_layer.get_value = _value_stub
    start_state = agent._build_value_state_snapshot(
        context_events=["ctx_A"],
        action="",
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )

    engine = agent.imagination_engine
    engine.samples = 2
    engine.depth = 4
    engine.branching = 2
    engine.goal_bias = 1.0
    engine.state_novelty_weight = 0.0
    engine.confidence_decay = 1.0
    engine.reward_decay = 1.0
    engine.__post_init__()

    high = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="high",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )
    low = engine.generate_structured_imagination(
        start_state=start_state,
        action_id="low",
        experiences=list(agent.hippocampus.experiences),
        depth=4,
        gamma=0.95,
        value_layer=agent.value_layer,
    )
    assert max(high["values"]) > max(low["values"])


def test_hie002_complexity_guard_clamps_samples_and_depth(monkeypatch):
    _patch_similarity(monkeypatch)
    agent = _build_agent(actions=("walk",))
    agent.imagination_samples = 20
    agent.imagination_depth = 10
    agent.imagination_max_nodes = 500
    agent.imagination_max_graph_nodes = 500
    agent.imagination_max_graph_edges = 500

    for idx in range(20):
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
    result = agent._generate_structured_imagination(
        start_state=start_state,
        action_id="walk",
        experiences=list(agent.hippocampus.experiences),
        depth=10,
    )
    trajectories = list(result.get("trajectories", []) or [])
    max_depth = max((int(getattr(traj, "depth", 0)) for traj in trajectories), default=0)

    assert len(result.get("values", [])) <= 8
    assert max_depth <= 5
    assert int(result.get("nodes_visited", 0)) <= 96
