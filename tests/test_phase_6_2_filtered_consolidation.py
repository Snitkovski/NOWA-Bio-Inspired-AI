import os

import pytest

from agent import Agent
from experience import Event, EventType
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("act",)):
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


def _step(agent: Agent, context: str, reward: float, novelty: float = 0.0):
    agent.step(
        context_events=[context],
        consequence=Event(f"feedback:{reward:+.2f}", EventType.CONSEQUENCE),
        intensity=1.0,
        reward=reward,
        novelty=novelty,
        conflict=0.0,
    )


def test_noise_episode_is_rejected_by_filtered_consolidation():
    agent = _build_agent(actions=("noise",))
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.2
    sleep.salience_threshold = 0.2
    sleep.min_reinforcement_for_consolidation = 1

    _step(agent, context="ctx_noise", reward=0.01, novelty=0.0)

    stats = agent.sleep(cycles=1)
    assert stats["total_episodes_examined"] >= 1
    assert stats["total_episodes_consolidated"] == 0
    assert stats["rejected_due_to_td_threshold"] >= 1
    assert stats["mean_consolidation_score"] == 0.0


def test_repeated_significant_episode_is_consolidated():
    agent = _build_agent(actions=("stable",))
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.08
    sleep.salience_threshold = 0.2
    sleep.min_reinforcement_for_consolidation = 2
    sleep.ach_min_for_consolidation = 0.0

    for _ in range(8):
        _step(agent, context="ctx_stable", reward=0.9, novelty=1.0)
    for exp in agent.hippocampus.experiences:
        exp.reinforcement_count = max(3, int(getattr(exp, "reinforcement_count", 1)))

    stats = agent.sleep(cycles=1)
    assert stats["total_episodes_examined"] >= 1
    assert stats["total_episodes_consolidated"] >= 1
    assert stats["mean_consolidation_score"] > 0.0
    assert stats["consolidation_ratio"] > 0.0


def test_high_value_variance_blocks_sleep_consolidation():
    agent = _build_agent(actions=("variance",))
    sleep = agent.sleep_manager
    sleep.instability_variance_threshold = 0.1

    for _ in range(4):
        _step(agent, context="ctx_var", reward=0.8, novelty=1.0)

    agent.value_layer._set_value("v0", -1.0)
    agent.value_layer._set_value("v1", 1.0)
    agent.value_layer._set_value("v2", -1.0)
    agent.value_layer._set_value("v3", 1.0)

    stats = agent.sleep(cycles=1)
    assert stats["total_replay_blocked"] == 1
    assert stats["total_replays"] == 0
    assert stats["rejected_due_to_variance_gate"] >= 1


def test_budget_overflow_stops_sleep_updates():
    agent = _build_agent(actions=("budget",))
    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 20
    sleep.max_replay_per_episode = 20
    sleep.per_update_cap = 0.02
    sleep.global_sleep_update_budget = 0.03
    sleep.max_l2_update_per_cycle = 1.0

    for _ in range(6):
        _step(agent, context="ctx_budget", reward=1.0, novelty=1.0)

    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 1.0
    exp.replay_salience = 1.0
    exp.replay_importance = 1.0

    stats = agent.sleep(cycles=1)
    assert stats["total_value_delta_sleep"] <= sleep.global_sleep_update_budget + 1e-9
    assert stats["replay_blocked"] is True


def test_high_ach_with_low_td_is_rejected():
    agent = _build_agent(actions=("ach",))
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.2
    sleep.salience_threshold = 0.0
    sleep.ach_min_for_consolidation = 0.0

    _step(agent, context="ctx_ach_low_td", reward=0.01, novelty=1.0)
    exp = agent.hippocampus.experiences[-1]
    exp.acetylcholine_snapshot = 1.0
    exp.td_error_snapshot = 0.01
    exp.td_mean_snapshot = 0.01

    stats = agent.sleep(cycles=1)
    assert stats["total_episodes_consolidated"] == 0
    assert stats["rejected_due_to_td_threshold"] >= 1


def test_td_history_updates_mean_and_variance():
    agent = _build_agent(actions=("td_hist",))
    _step(agent, context="ctx_td_hist", reward=0.6, novelty=0.0)
    exp = agent.hippocampus.experiences[-1]

    agent.apply_feedback_to_last_experience(2, context_events=["ctx_td_hist"], action_id="td_hist")
    agent.apply_feedback_to_last_experience(-2, context_events=["ctx_td_hist"], action_id="td_hist")
    agent.apply_feedback_to_last_experience(1, context_events=["ctx_td_hist"], action_id="td_hist")

    history = list(getattr(exp, "td_history_snapshot", []))
    assert len(history) >= 4
    mean_v = sum(float(value) for value in history) / float(len(history))
    variance_v = sum((float(value) - mean_v) ** 2 for value in history) / float(len(history))
    assert float(exp.td_mean_snapshot) == pytest.approx(mean_v)
    assert float(exp.td_variance_snapshot) == pytest.approx(variance_v)
    assert float(exp.td_variance_snapshot) > 0.0


def test_sleep_replay_does_not_mutate_td_history_statistics():
    agent = _build_agent(actions=("td_sleep",))
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.0
    sleep.salience_threshold = 0.0
    sleep.ach_min_for_consolidation = 0.0

    _step(agent, context="ctx_td_sleep", reward=0.7, novelty=0.0)
    exp = agent.hippocampus.experiences[-1]
    exp.reinforcement_count = 3
    exp.td_history_snapshot = [0.2, 0.6, 0.4]
    exp.td_error_snapshot = 0.4
    exp.td_mean_snapshot = 0.4
    exp.td_variance_snapshot = ((0.2 - 0.4) ** 2 + (0.6 - 0.4) ** 2 + (0.4 - 0.4) ** 2) / 3.0
    before_history = list(exp.td_history_snapshot)
    before_mean = float(exp.td_mean_snapshot)
    before_variance = float(exp.td_variance_snapshot)

    stats = agent.sleep(cycles=1)
    assert stats["total_replays"] >= 1
    assert list(exp.td_history_snapshot) == before_history
    assert float(exp.td_mean_snapshot) == pytest.approx(before_mean)
    assert float(exp.td_variance_snapshot) == pytest.approx(before_variance)


def test_td_variance_cap_rejects_high_variance_episode():
    agent = _build_agent(actions=("td_var",))
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.0
    sleep.salience_threshold = 0.0
    sleep.ach_min_for_consolidation = 0.0
    sleep.td_variance_cap = 0.01

    _step(agent, context="ctx_td_var", reward=0.8, novelty=0.0)
    exp = agent.hippocampus.experiences[-1]
    exp.reinforcement_count = 3
    exp.td_history_snapshot = [1.0, -1.0, 1.0, -1.0]
    exp.td_error_snapshot = 1.0
    exp.td_mean_snapshot = 0.0
    exp.td_variance_snapshot = 1.0

    stats = agent.sleep(cycles=1)
    assert stats["rejected_due_to_td_variance"] >= 1
    assert stats["total_episodes_consolidated"] == 0


def test_sleep_cycle_freezes_value_variance_snapshot():
    agent = _build_agent(actions=("freeze",))
    sleep = agent.sleep_manager
    for _ in range(4):
        _step(agent, context="ctx_freeze", reward=0.9, novelty=1.0)
    for exp in agent.hippocampus.experiences:
        exp.reinforcement_count = max(3, int(getattr(exp, "reinforcement_count", 1)))

    calls = {"count": 0}

    def _fake_variance():
        calls["count"] += 1
        # If called repeatedly in one cycle this would destabilize replay.
        return 0.0 if calls["count"] == 1 else 10.0

    sleep._compute_value_variance = _fake_variance
    stats = agent.sleep(cycles=1)
    assert calls["count"] == 1
    assert stats["total_replays"] >= 1
    assert float(stats.get("value_variance_ratio", 0.0)) == pytest.approx(0.0)


@pytest.mark.skipif(
    os.getenv("RUN_LONG_HORIZON_FILTERED_CONSOLIDATION", "0") != "1",
    reason="Long stress-test disabled by default (set RUN_LONG_HORIZON_FILTERED_CONSOLIDATION=1).",
)
def test_stress_5000_cycles_no_variance_growth():
    agent = _build_agent(actions=("stress",))
    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 1
    sleep.max_replay_per_episode = 1
    sleep.per_update_cap = 0.01
    sleep.global_sleep_update_budget = 0.01
    sleep.max_l2_update_per_cycle = 0.01

    for _ in range(5):
        _step(agent, context="ctx_stress", reward=0.7, novelty=1.0)

    max_ratio = 0.0
    for _ in range(5000):
        stats = agent.sleep(cycles=1)
        max_ratio = max(max_ratio, float(stats.get("variance_ratio", 0.0)))

    assert max_ratio < 1.0
