from src.agent import Agent
from src.temporal import TemporalLevels
from src.affect import AffectiveState


class DummyHippocampus:
    def activate(self, ctx):
        return []
    def store(self, path, consequence=None, intensity=1.0):
        pass
    def get_statistics(self):
        return {}

class DummyCortex:
    def activate(self, ctx):
        return []
    def get_statistics(self):
        return {}

class DummySelector:
    def choose(self, hip, ctx, intent_pressure=None, affect_modifier=1.0):
        return "do_nothing"

class DummySleepCore:
    def sleep_cycle(self):
        pass
    def consolidate_to_cortex(self, cortex):
        pass

class DummySleepManager:
    def __init__(self, hippocampus, cortex):
        # keep interface compatible with new SleepManager
        self.hippocampus = hippocampus
        self.cortex = cortex
        self.temporal = None
        self.affect_state = None
        self.consolidation_cycles = 0
    def deep_sleep(self, cycles=1):
        # simulate consolidation by calling temporal if present
        for _ in range(cycles):
            if self.temporal:
                self.temporal.consolidate()
            self.consolidation_cycles += 1
        return {"status":"ok","cycles":cycles}


def test_agent_logs_temporal_and_updates_affect():
    hip = DummyHippocampus()
    ctx = DummyCortex()
    sel = DummySelector()
    sleep_mgr = DummySleepManager(hip, ctx)
    agent = Agent(hip, ctx, sel, sleep_manager=sleep_mgr)

    # initial step logs T0/T1
    action = agent.step(["context_a"], reward=0.5)
    levels = agent.temporal.get_levels()
    assert "T0" in levels and "T1_mean" in levels
    # affect_state aggregates updated
    assert isinstance(agent.affect_state.affect_trend, dict)

    # call sleep to consolidate
    result = agent.sleep(cycles=2)
    assert result.get("status") == "ok"
    # after consolidation baseline should be present
    assert agent.affect_state.affect_baseline is not None
    assert agent.temporal.t2 is not None
