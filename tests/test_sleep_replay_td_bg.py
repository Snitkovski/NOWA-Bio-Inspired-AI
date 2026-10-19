import pytest

from learning_guard import learning_allowed


@pytest.fixture(autouse=True)
def _seed_stable_weights_under_sleep_guard():
    """Seed stable weights the way sleep does. Invariant W is test_issue13."""
    with learning_allowed():
        yield


from agent import Agent
from experience import Event, EventType
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("act",)):
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


def _step(agent: Agent, context: str, reward: float, consequence_name: str = ""):
    consequence = None
    if consequence_name:
        consequence = Event(consequence_name, EventType.CONSEQUENCE)
    agent.step(
        context_events=[context],
        consequence=consequence,
        intensity=1.0,
        reward=reward,
        novelty=0.0,
        conflict=0.0,
    )


def _channel_l1(channel) -> float:
    return abs(float(channel.go_weight)) + abs(float(channel.nogo_weight)) + abs(float(channel.habit_strength))


def test_replay_positive_strengthens_habit_and_value():
    """Q rises from replay. Go rises from capture, not from a second replay write."""
    agent = _build_agent(actions=("approach",))
    channel = agent.bg_action_channels["approach"]
    channel.go_weight = 0.25
    channel.nogo_weight = 0.45
    channel.habit_strength = 0.05

    for _ in range(8):
        _step(agent, context="ctx_pos", reward=0.8, consequence_name="feedback:1")

    exp = agent.hippocampus.experiences[-1]
    before_value = agent.value_layer.get_value(exp.value_state_snapshot)
    before_go = channel.go_weight

    stats = agent.sleep(cycles=1)

    after_value = agent.value_layer.get_value(exp.value_state_snapshot)
    after_go = agent.bg_action_channels["approach"].go_weight

    assert stats["total_replays"] > 0
    assert after_value > before_value
    # The once-per-sleep capture moves Go. Replay's own channel delta is 0.
    assert after_go > before_go
    assert stats["sleep_update_count"] > 0
    assert stats["total_value_delta_sleep"] == pytest.approx(stats["total_value_delta"])
    assert stats["total_bg_delta_sleep"] == pytest.approx(0.0)
    assert stats["total_weight_delta"] == pytest.approx(0.0)
    assert _channel_l1(agent.bg_action_channels["approach"]) <= agent.sleep_manager.weight_norm_cap + 1e-9


def test_replay_negative_weakens_habit_without_negative_runaway():
    """A punished episode lowers Go via the compensated step, not via replay."""
    agent = _build_agent(actions=("avoid",))
    channel = agent.bg_action_channels["avoid"]
    channel.go_weight = 0.85
    channel.nogo_weight = 0.15
    channel.habit_strength = 0.40
    agent.sleep_manager.weight_norm_cap = 10.0

    for _ in range(8):
        _step(agent, context="ctx_neg", reward=-0.9, consequence_name="feedback:-1")

    before_go = channel.go_weight
    before_nogo = channel.nogo_weight

    agent.sleep(cycles=1)

    updated = agent.bg_action_channels["avoid"]
    assert updated.go_weight < before_go
    assert updated.nogo_weight > before_nogo
    assert 0.0 <= updated.go_weight <= 1.0
    assert 0.0 <= updated.nogo_weight <= 1.0
    assert 0.0 <= updated.habit_strength <= 1.0


def test_runaway_protection_caps_and_normalization():
    agent = _build_agent(actions=("persist",))
    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 50
    sleep.max_replay_per_episode = 50
    sleep.delta_weight_max_per_sleep = 0.03
    sleep.weight_total_cap = 0.08
    sleep.delta_value_max_per_sleep = 0.03
    sleep.value_total_cap = 0.08
    sleep.weight_norm_cap = 0.25
    sleep.decay_rate_sleep = 0.0

    channel = agent.bg_action_channels["persist"]
    channel.go_weight = 0.95
    channel.nogo_weight = 0.95
    channel.habit_strength = 0.95

    _step(agent, context="ctx_hi", reward=1.0, consequence_name="feedback:1")
    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 1.0
    exp.replay_salience = 1.0
    exp.replay_importance = 1.0

    stats = agent.sleep(cycles=1)
    updated = agent.bg_action_channels["persist"]

    assert stats["total_weight_delta"] <= sleep.weight_total_cap + 1e-9
    assert stats["total_value_delta"] <= sleep.value_total_cap + 1e-9
    assert stats["sleep_update_count"] <= stats["total_replay_selected"]
    assert stats["normalization_applied_cycles"] >= 1
    assert _channel_l1(updated) <= sleep.weight_norm_cap + 1e-9


def test_instability_blocks_replay_and_reinforcement():
    """A high per-state estimate variance blocks that state's replay.

    Spreading unrelated table entries used to trip the same flag. That spread
    is no longer the gate; the estimate variance on the replayed state is.
    """
    agent = _build_agent(actions=("stable",))
    sleep = agent.sleep_manager
    sleep.decay_rate_sleep = 0.0
    sleep.weight_norm_cap = 10.0
    sleep.td_threshold = 0.05
    sleep.salience_threshold = 0.0
    sleep.ach_min_for_consolidation = 0.0

    for _ in range(4):
        _step(agent, context="ctx_block", reward=0.7, consequence_name="feedback:1")
    for exp in agent.hippocampus.experiences:
        exp.reinforcement_count = 3
        state_key = str(getattr(exp, "value_state_key", "") or "")
        if state_key:
            agent.value_layer.expectation_memory[state_key] = {"expected_reward_var": 1.0}
    # Outcome-cache consolidation is a separate path. This check is about replay.
    agent.bg_sleep_memories.clear()

    before = agent.bg_action_channels["stable"].go_weight
    stats = agent.sleep(cycles=1)
    after = agent.bg_action_channels["stable"].go_weight

    assert stats["rejected_due_to_variance_gate"] >= 1
    assert stats["total_replays"] == 0
    # The variance gate still blocks TD replay. The once-per-episode
    # Go/NoGo step is not that replay, so known outcomes still move Go.
    assert after > before


def test_affective_isolation_zero_td_not_prioritized():
    agent = _build_agent(actions=("neutral",))
    sleep = agent.sleep_manager
    sleep.decay_rate_sleep = 0.0
    sleep.weight_norm_cap = 10.0

    _step(agent, context="ctx_affect", reward=0.0, consequence_name="feedback:0")
    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 0.0
    exp.replay_salience = 0.0
    exp.replay_importance = 0.0

    agent.affect_state.valence = 1.0
    agent.affect_state.arousal = 2.0
    agent.affect_state.threat = 1.0
    agent.affect_state.curiosity = 1.0

    before = agent.bg_action_channels["neutral"].go_weight
    stats = agent.sleep(cycles=1)
    after = agent.bg_action_channels["neutral"].go_weight

    assert stats["total_replay_selected"] == 0
    assert stats["total_replays"] == 0
    assert after == pytest.approx(before)


def test_replay_budget_limit_enforced():
    agent = _build_agent(actions=("budget",))
    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 5
    sleep.max_replay_per_episode = 10
    sleep.instability_variance_threshold = 1.0
    sleep.decay_rate_sleep = 0.0

    for idx in range(20):
        _step(agent, context=f"ctx_budget_{idx}", reward=0.6, consequence_name="feedback:1")

    stats = agent.sleep(cycles=1)
    assert stats["total_replay_blocked"] == 0
    assert stats["total_replays"] <= 5
    assert stats["total_replay_selected"] <= 5


def test_sleep_dopamine_scaling_applies_weak_da_delta():
    agent = _build_agent(actions=("da",))
    sleep = agent.sleep_manager
    sleep.decay_rate_sleep = 0.0
    sleep.weight_norm_cap = 10.0
    sleep.replay_budget_per_sleep = 1
    sleep.max_replay_per_episode = 1

    _step(agent, context="ctx_da", reward=0.9, consequence_name="feedback:1")
    da_before = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))
    stats = agent.sleep(cycles=1)
    da_after = float(agent.neuromodulators.snapshot().get("dopamine", 0.0))

    assert stats["sleep_update_count"] >= 1
    assert da_after > da_before


def test_stability_modulates_sleep_alpha_strength():
    class _Monitor:
        def __init__(self, value: float):
            self._value = float(value)

        def snapshot(self):
            return {"stability_index": self._value}

    high = _build_agent(actions=("stable_alpha",))
    low = _build_agent(actions=("stable_alpha",))
    for agent in (high, low):
        agent.sleep_manager.replay_budget_per_sleep = 1
        agent.sleep_manager.max_replay_per_episode = 1
        agent.sleep_manager.decay_rate_sleep = 0.0
        agent.sleep_manager.weight_norm_cap = 10.0
        _step(agent, context="ctx_alpha", reward=0.2, consequence_name="feedback:1")

    high.stability_monitor = _Monitor(1.0)
    low.stability_monitor = _Monitor(0.1)

    high_stats = high.sleep(cycles=1)
    low_stats = low.sleep(cycles=1)

    assert high_stats["total_value_delta_sleep"] > low_stats["total_value_delta_sleep"]


def test_replay_temperature_decay_reduces_selection_horizon():
    agent = _build_agent(actions=("temp",))
    sleep = agent.sleep_manager
    sleep.replay_priority_weights = (1.0, 0.0, 0.0)
    sleep.replay_priority_min = 0.85
    sleep.replay_temperature_decay = 0.95
    sleep.replay_budget_per_sleep = 10
    sleep.max_replay_per_episode = 10

    _step(agent, context="ctx_temp", reward=1.0, consequence_name="feedback:1")
    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 1.0
    exp.replay_salience = 0.0
    exp.replay_importance = 0.0

    sample = sleep._select_replay_sample([exp])
    assert len(sample) == 3


def test_sleep_value_delta_follows_recomputed_td_not_stale_sign():
    agent = _build_agent(actions=("sync",))
    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 1
    sleep.max_replay_per_episode = 1
    sleep.decay_rate_sleep = 0.0
    sleep.weight_norm_cap = 10.0
    sleep.td_threshold = 0.05
    sleep.salience_threshold = 0.0
    sleep.ach_min_for_consolidation = 0.0

    _step(agent, context="ctx_sync", reward=0.0, consequence_name="feedback:0")
    exp = agent.hippocampus.experiences[-1]
    exp.reinforcement_count = 3
    # Stale snapshot is positive. The table is already above the target, so
    # the recomputed TD is negative and replay must move V down.
    exp.td_error_snapshot = 1.0
    exp.td_mean_snapshot = 1.0
    exp.replay_salience = 1.0
    exp.replay_importance = 1.0
    exp.reward = 0.0
    exp.td_committed_reward = 0.0
    exp.value_terminal = True
    agent.value_layer._set_value(str(exp.value_state_key), 0.45)
    before_value = agent.value_layer.get_value(exp.value_state_snapshot)

    stats = agent.sleep(cycles=1)
    after_value = agent.value_layer.get_value(exp.value_state_snapshot)

    assert stats["total_replays"] == 1
    assert after_value < before_value
    assert stats["total_value_delta_sleep"] > 0.0
    assert stats["total_value_delta_sleep"] <= sleep.per_update_cap + 1e-9
