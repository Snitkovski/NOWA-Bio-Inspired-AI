"""Tamagochi host contract for two-tier plasticity (issue #13)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


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
