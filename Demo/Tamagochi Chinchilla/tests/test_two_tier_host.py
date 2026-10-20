"""Tamagochi host contract for two-tier plasticity (issue #13)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

DEMO_SRC = Path(__file__).resolve().parent.parent / "src"
REPO_SRC = Path(__file__).resolve().parents[3] / "src"
for _path in (REPO_SRC, DEMO_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


@pytest.fixture(autouse=True)
def fail_if_waking_learning_error_was_caught(monkeypatch):
    """Strict mode. A swallowed ``WakingLearningError`` fails the test.

    The guard raises inside ``learning_guard``. Callers that catch
    ``Exception`` hide it and the test would otherwise stay green.
    """
    monkeypatch.setenv("NOWA_STRICT_LEARNING", "1")
    import learning_guard

    raised: list[str] = []
    original = learning_guard.WakingLearningError

    class _CountingWakingLearningError(original):
        def __init__(self, *args):
            raised.append(" ".join(str(item) for item in args))
            super().__init__(*args)

    monkeypatch.setattr(learning_guard, "WakingLearningError", _CountingWakingLearningError)
    yield
    if raised:
        pytest.fail(
            "WakingLearningError was raised and caught: " + " | ".join(raised)
        )


def _cage():
    from main import ChinchillaAgent

    demo_dir = Path(__file__).resolve().parent.parent
    agent = ChinchillaAgent(
        demo_dir=str(demo_dir),
        use_pygame=False,
        use_gui=False,
    )
    agent._last_nowa_save = float(agent.total_sim_time)
    agent._memory_save_timer = 0.0
    return agent


def _store_chain(agent, chain_name: str, reward: float):
    from experience import Event, EventType, Path as ExperiencePath

    return agent.hippocampus.store(
        path=ExperiencePath(
            events=[Event(name=chain_name, event_type=EventType.ACTION)]
        ),
        reward=reward,
        intensity=1.0,
    )


def test_waking_ticks_hold_stable_tier_until_sleep(monkeypatch) -> None:
    monkeypatch.setenv("NOWA_STRICT_LEARNING", "1")
    from main import ChinchillaAgent, tamagochi_expected_wake_interval_s
    from experience import Event, EventType, Path as ExperiencePath
    from learning_guard import stable_fingerprint

    demo_dir = Path(__file__).resolve().parent.parent
    agent = ChinchillaAgent(
        demo_dir=str(demo_dir),
        use_pygame=False,
        use_gui=False,
    )
    agent.running = True
    agent.wakefulness.wakefulness = 0.1
    agent.chain_executor.current_chain = None
    agent.current_action = None
    # Loaded session time is already past the autosave mark. Keep the test
    # from rewriting Demo saves.
    agent._last_nowa_save = float(agent.total_sim_time)
    agent._memory_save_timer = 0.0

    host = agent.nowa
    interval = tamagochi_expected_wake_interval_s()
    assert host is not None
    assert host.plasticity.expected_wake_interval_s == interval
    assert interval == 10080.0

    before = stable_fingerprint(host)
    clock0 = float(host._host_clock_s)
    dt = 1.0
    ticks = 4
    for _ in range(ticks):
        agent.sim_step(dt)

    assert host._dt_warning_sent is False
    assert host._host_clock_s == clock0 + (dt * ticks)
    assert stable_fingerprint(host) == before

    episode = agent.hippocampus.store(
        path=ExperiencePath(
            events=[Event(name="eating_and_grooming", event_type=EventType.ACTION)]
        ),
        reward=1.0,
        intensity=1.0,
    )
    agent._commit_waking_chain_outcome(
        "eating_and_grooming",
        1.0,
        {"chain": "eating_and_grooming"},
        {"chain": "after"},
        episode=episode,
    )
    assert stable_fingerprint(host) == before
    assert agent.labile.max_abs_channel(float(host._host_clock_s)) > 0.0

    agent._run_sleep_consolidation()
    assert stable_fingerprint(host) != before


def test_sleep_capture_applies_intent_outcome() -> None:
    """SleepManager must see the cage intent memory so capture calls apply_outcome."""
    agent = _cage()
    assert agent.sleep_manager.intent_memory is agent.intent_memory

    chain = "eating_and_grooming"
    episode = _store_chain(agent, chain, 1.0)
    episode.context_events = ["idle"]
    agent._commit_waking_chain_outcome(chain, 1.0, {"chain": chain}, {"chain": "after"}, episode)
    agent.intent_memory.note_selection(["idle"], chain)
    created = [
        trace
        for trace in agent.intent_memory.traces.values()
        if trace.intent_type == chain and float(trace.strength) == 0.0
    ]
    assert created

    agent._run_sleep_consolidation()
    survived = [
        float(trace.strength)
        for trace in agent.intent_memory.traces.values()
        if trace.intent_type == chain
    ]
    assert survived
    assert max(survived) > 0.0


def test_deep_sleep_is_the_only_channel_writer() -> None:
    """One night must not run a second Go/NoGo/habit step or replace the channel."""
    agent = _cage()
    chain = "eating_and_grooming"
    episode = _store_chain(agent, chain, 1.0)
    agent._commit_waking_chain_outcome(chain, 1.0, {"chain": chain}, {"chain": "after"}, episode)
    agent.bg_channels[chain].record_outcome(1.0)

    seen: dict[str, object] = {}
    original = agent.sleep_manager.deep_sleep

    def _wrapped(*args, **kwargs):
        result = original(*args, **kwargs)
        channel = agent.bg_channels[chain]
        seen["id"] = id(channel)
        seen["go"] = float(channel.go_weight)
        seen["nogo"] = float(channel.nogo_weight)
        seen["habit"] = float(channel.habit_strength)
        return result

    agent.sleep_manager.deep_sleep = _wrapped
    agent._run_sleep_consolidation()
    channel = agent.bg_channels[chain]
    assert id(channel) == seen["id"]
    assert float(channel.go_weight) == seen["go"]
    assert float(channel.nogo_weight) == seen["nogo"]
    assert float(channel.habit_strength) == seen["habit"]


def test_chain_start_does_not_write_stable_intent() -> None:
    """Starting a chain while awake must not call IntentMemory.record_trace."""
    agent = _cage()
    agent.running = True
    agent.action_remaining_s = 0.0
    agent.chain_cooldown_s = 0.0
    agent.current_action = None
    agent.wakefulness.wakefulness = 0.1
    agent.chain_executor.current_chain = None
    agent._intent_context = ["idle"]

    before = set(agent.intent_memory.traces)
    agent.sim_step(0.1)
    assert agent.last_chain_name
    for key, trace in agent.intent_memory.traces.items():
        if key not in before:
            assert float(trace.strength) == 0.0
