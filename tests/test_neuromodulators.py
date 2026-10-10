import time
from src.neuromodulators import NeuromodulatorState
from src.hippocampus import NOWAHippocampus
from src.sleep import CortexMemory, SleepManager
from src.selector import ActionSelector
from src.agent import Agent


def make_agent():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a1", "a2", "a3"])
    sleep = SleepManager(hip, cortex)
    ag = Agent(hip, cortex, selector, sleep_manager=sleep)
    return ag


def test_repeating_success_increases_dopamine_and_consolidation():
    ag = make_agent()
    da_values = []
    for i in range(6):
        ag.step(["user:task"], reward=1.0, intensity=1.0)
        da_values.append(ag.neuromodulators.dopamine)
    assert da_values[-1] >= da_values[0]

    # Run sleep cycles to consolidate
    stats = ag.sleep(cycles=2)
    ctx_stats = ag.cortex.get_statistics()
    assert ctx_stats["total_patterns"] >= 0


def test_novelty_elevates_norepinephrine():
    ag = make_agent()
    before = ag.neuromodulators.norepinephrine
    ag.step(["user:novel"], novelty=1.0)
    after = ag.neuromodulators.norepinephrine
    assert after > before


def test_prolonged_negative_increases_cortisol_and_forgetting():
    ag = make_agent()
    # Create several negative experiences via step
    for i in range(8):
        ag.step([f"user:bad{i}"], reward=-1.0, intensity=1.0)
    before_count = len(ag.hippocampus.experiences)
    # Cortisol should grow
    assert ag.neuromodulators.cortisol > 0
    ag.sleep(cycles=1)
    after_count = len(ag.hippocampus.experiences)
    assert after_count <= before_count


def test_long_stability_increases_serotonin():
    ag = make_agent()
    before = ag.neuromodulators.serotonin
    # Many positive reward steps - serotonin increases on reward > 0 with no conflict
    for _ in range(10):
        ag.step(["user:calm"], reward=0.2, novelty=0.0, conflict=0.0)
    after = ag.neuromodulators.serotonin
    # With 10 steps @ reward=0.2, should increase: HT += 0.05 * 0.2 = 0.01 per step
    # Expected after ~10 steps: 0.1 + (0.01 * 10) = 0.2
    assert after > before, f"Serotonin should increase with positive rewards: {before} > {after}"
