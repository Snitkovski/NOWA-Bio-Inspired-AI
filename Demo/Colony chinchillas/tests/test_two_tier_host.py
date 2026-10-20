"""Colony host contract for two-tier plasticity (issue #13)."""

from __future__ import annotations

from colony_agent import ChinchillaAgent, colony_expected_wake_interval_s
from learning_guard import stable_fingerprint
from shared_resources import SharedResources


def test_waking_ticks_hold_stable_tier_until_sleep(monkeypatch) -> None:
    monkeypatch.setenv("NOWA_STRICT_LEARNING", "1")
    agent = ChinchillaAgent(
        sex="F",
        name="Luna",
        rng_seed=1,
        physiology_as_policy=True,
    )
    agent.colony = [agent]
    agent.resources = SharedResources()
    agent.hunger = 0.2
    agent.thirst = 0.2
    agent.wakefulness.wakefulness = 0.1

    interval = colony_expected_wake_interval_s()
    assert agent.plasticity.expected_wake_interval_s == interval
    assert interval > 0.0

    before = stable_fingerprint(agent)
    dt = 1.0
    ticks = 4
    for _ in range(ticks):
        agent.sim_step(dt)

    assert agent._dt_warning_sent is False
    assert agent._host_clock_s == dt * ticks
    assert stable_fingerprint(agent) == before

    agent.sleep(cycles=1, sleep_duration_seconds=0.0)
    assert stable_fingerprint(agent) != before
