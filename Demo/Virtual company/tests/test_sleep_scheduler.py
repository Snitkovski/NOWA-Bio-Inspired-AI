"""Tests for SleepScheduler (patch v1.1 §1)."""

from datetime import datetime

from nowa_body.sleep_scheduler import SleepScheduler

from body_support import make_test_agent, make_test_agent_with_pressure


class TestSleepScheduler:
    def test_circadian_window_triggers(self):
        scheduler = SleepScheduler(circadian_window=(2, 5), min_ticks_between_sleep=0)
        agent = make_test_agent()  # no wakefulness_state, pressure=None
        now = datetime(2026, 1, 1, 3, 0)  # 3am, inside window
        should, reason = scheduler.should_sleep(agent, now)
        assert should is True
        assert reason == "circadian"

    def test_fatigue_triggers_outside_window(self):
        scheduler = SleepScheduler(fatigue_threshold=0.8, min_ticks_between_sleep=0)
        agent = make_test_agent_with_pressure(0.9)
        now = datetime(2026, 1, 1, 14, 0)  # 2pm, outside circadian window
        should, reason = scheduler.should_sleep(agent, now)
        assert should is True
        assert reason == "fatigue"

    def test_neither_signal_no_sleep(self):
        scheduler = SleepScheduler(fatigue_threshold=0.8, min_ticks_between_sleep=0)
        agent = make_test_agent_with_pressure(0.3)
        now = datetime(2026, 1, 1, 14, 0)
        should, reason = scheduler.should_sleep(agent, now)
        assert should is False

    def test_min_ticks_prevents_thrashing(self):
        """Even a fully fatigued agent must not sleep every tick."""
        scheduler = SleepScheduler(fatigue_threshold=0.1, min_ticks_between_sleep=100)
        agent = make_test_agent_with_pressure(0.99)
        now = datetime(2026, 1, 1, 14, 0)
        results = [scheduler.should_sleep(agent, now)[0] for _ in range(50)]
        assert not any(results)  # min_ticks not yet reached

    def test_mark_slept_resets_counter(self):
        scheduler = SleepScheduler(min_ticks_between_sleep=5)
        agent = make_test_agent()
        for _ in range(5):
            scheduler.should_sleep(agent, datetime(2026, 1, 1, 14, 0))
        scheduler.mark_slept()
        should, _ = scheduler.should_sleep(agent, datetime(2026, 1, 1, 2, 0))
        assert should is False  # counter reset, min_ticks not reached again yet

    def test_reads_get_sleep_pressure_from_core_wakefulness_api(self):
        scheduler = SleepScheduler(fatigue_threshold=0.5, min_ticks_between_sleep=0)
        agent = make_test_agent()
        agent.wakefulness = type(
            "WS", (), {"get_sleep_pressure": lambda self: 0.91}
        )()
        should, reason = scheduler.should_sleep(agent, datetime(2026, 1, 1, 14, 0))
        assert should is True
        assert reason == "fatigue"

    def test_circadian_window_wraps_midnight(self):
        scheduler = SleepScheduler(circadian_window=(22, 4), min_ticks_between_sleep=0)
        agent = make_test_agent()
        should, reason = scheduler.should_sleep(agent, datetime(2026, 1, 1, 23, 0))
        assert should is True
        assert reason == "circadian"
        scheduler2 = SleepScheduler(circadian_window=(22, 4), min_ticks_between_sleep=0)
        should, _ = scheduler2.should_sleep(agent, datetime(2026, 1, 1, 12, 0))
        assert should is False
