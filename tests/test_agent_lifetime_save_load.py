import time
import pytest

from agent import Agent
from hippocampus import NOWAHippocampus
from sleep import CortexMemory, SleepManager
from selector import ActionSelector
from intent_memory import IntentMemory
from storage import AgentStorage


def test_agent_lifetime_persistence(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    # Set deterministic lifetime fields
    agent.created_ts = time.time() - 123.0
    agent._simulated_sleep_seconds = 456.0

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        sleep_manager=sleep_mgr,
        agent=agent,
        filename="agent_lifetime.pkl",
    )

    # Fresh agent
    hip2 = NOWAHippocampus()
    cortex2 = CortexMemory()
    intent_mem2 = IntentMemory()
    sleep_mgr2 = SleepManager(hip2, cortex2, intent_mem2)
    selector2 = ActionSelector(actions=["a", "b"])
    agent2 = Agent(hip2, cortex2, selector2, sleep_mgr2, intent_mem2)

    storage.load_agent(
        hip2,
        cortex2,
        selector2,
        path,
        sleep_manager=sleep_mgr2,
        agent=agent2,
    )

    assert abs(agent2.created_ts - agent.created_ts) < 0.001
    assert abs(agent2._simulated_sleep_seconds - agent._simulated_sleep_seconds) < 0.001


def test_wakefulness_and_autonomous_runtime_persistence(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    # Set deterministic wakefulness state.
    agent.wakefulness.wakefulness = 0.73
    agent.wakefulness.accumulated_waking_time = 7200.0
    agent.wakefulness.total_sleep_time = 1800.0
    agent.wakefulness.circadian_time_hours = 13.25
    agent.wakefulness.circadian_period_hours = 24.2
    agent.wakefulness.circadian_amplitude = 0.27
    agent.wakefulness.circadian_phase = 0.45

    # Prepare deterministic autonomous snapshot.
    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable in current environment")

    runtime.drive_system.set_drive("curiosity", 0.77)
    runtime.drive_system.set_drive("social_drive", 0.31)
    runtime.energy_system.energy = 0.41
    runtime.energy_system.fatigue = 0.66
    runtime.energy_system.suppress_internal_cycles = True
    runtime.failure_log = [{"timestamp": 1.0, "failure_mode": "test", "details": {"k": "v"}}]
    runtime.tick_history = [{"restored": False}, {"restored": False}, {"restored": False}]
    runtime.speech_governor.last_speech_time = 123.4

    autonomous_before = agent.get_autonomous_state()

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        sleep_manager=sleep_mgr,
        agent=agent,
        filename="agent_autonomous_wakefulness.pkl",
    )

    # Fresh agent to restore into.
    hip2 = NOWAHippocampus()
    cortex2 = CortexMemory()
    intent_mem2 = IntentMemory()
    sleep_mgr2 = SleepManager(hip2, cortex2, intent_mem2)
    selector2 = ActionSelector(actions=["a", "b"])
    agent2 = Agent(hip2, cortex2, selector2, sleep_mgr2, intent_mem2)

    storage.load_agent(
        hip2,
        cortex2,
        selector2,
        path,
        sleep_manager=sleep_mgr2,
        agent=agent2,
    )

    # Wakefulness round-trip.
    assert abs(agent2.wakefulness.wakefulness - 0.73) < 1e-9
    assert abs(agent2.wakefulness.accumulated_waking_time - 7200.0) < 1e-9
    assert abs(agent2.wakefulness.total_sleep_time - 1800.0) < 1e-9
    assert abs(agent2.wakefulness.circadian_time_hours - 13.25) < 1e-9
    assert abs(agent2.wakefulness.circadian_period_hours - 24.2) < 1e-9
    assert abs(agent2.wakefulness.circadian_amplitude - 0.27) < 1e-9
    assert abs(agent2.wakefulness.circadian_phase - 0.45) < 1e-9

    # Autonomous runtime round-trip.
    autonomous_after = agent2.get_autonomous_state()
    assert autonomous_after
    assert abs(float(autonomous_after["drives"]["curiosity"]) - float(autonomous_before["drives"]["curiosity"])) < 1e-9
    assert abs(float(autonomous_after["drives"]["social_drive"]) - float(autonomous_before["drives"]["social_drive"])) < 1e-9
    assert abs(float(autonomous_after["energy"]["energy"]) - float(autonomous_before["energy"]["energy"])) < 1e-9
    assert abs(float(autonomous_after["energy"]["fatigue"]) - float(autonomous_before["energy"]["fatigue"])) < 1e-9
    assert bool(autonomous_after["energy"]["suppress_internal_cycles"]) is True
    assert int(autonomous_after.get("tick_count", 0)) == int(autonomous_before.get("tick_count", 0))
    assert len(list(autonomous_after.get("failures", []) or [])) == len(list(autonomous_before.get("failures", []) or []))
    assert abs(float(autonomous_after.get("speech", {}).get("last_speech_time", 0.0)) - 123.4) < 1e-9


def test_agent_step_updates_wakefulness_once_per_step():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    calls = {"count": 0}
    original_update = agent.wakefulness.update_waking

    def _counting_update(*args, **kwargs):
        calls["count"] += 1
        return original_update(*args, **kwargs)

    agent.wakefulness.update_waking = _counting_update
    agent.step(["ctx:single_call"])

    assert calls["count"] == 1


def test_autonomous_tick_advances_wakefulness():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable in current environment")

    before = float(agent.wakefulness.wakefulness)
    tick = agent.autonomous_tick(dt=10.0)

    assert isinstance(tick, dict)
    assert float(agent.wakefulness.wakefulness) > before


def test_autonomous_runtime_wires_selector_into_internal_loop():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable in current environment")

    assert runtime.internal_loop.cognitive_core is selector
    assert runtime.internal_loop.decision_engine is selector
    assert hasattr(runtime.internal_loop.decision_engine, "evaluate")


def test_sleep_reduces_autonomous_energy_fatigue():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable in current environment")

    runtime.energy_system.energy = 0.12
    runtime.energy_system.fatigue = 0.91
    runtime.energy_system.suppress_internal_cycles = True
    agent.wakefulness.wakefulness = 0.80

    agent.sleep(cycles=2, sleep_duration_seconds=3600.0)

    assert runtime.energy_system.energy > 0.12
    assert runtime.energy_system.fatigue < 0.91
    assert runtime.energy_system.suppress_internal_cycles is False
    assert agent.wakefulness.wakefulness < 0.80


def test_restored_autonomous_runtime_keeps_physiology_tick_contract(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable in current environment")

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        sleep_manager=sleep_mgr,
        agent=agent,
        filename="agent_autonomous_contract.pkl",
    )

    hip2 = NOWAHippocampus()
    cortex2 = CortexMemory()
    intent_mem2 = IntentMemory()
    sleep_mgr2 = SleepManager(hip2, cortex2, intent_mem2)
    selector2 = ActionSelector(actions=["a", "b"])
    agent2 = Agent(hip2, cortex2, selector2, sleep_mgr2, intent_mem2)

    storage.load_agent(
        hip2,
        cortex2,
        selector2,
        path,
        sleep_manager=sleep_mgr2,
        agent=agent2,
    )

    tick = agent2.autonomous_tick(dt=1.0)
    assert isinstance(tick, dict)
    assert "physiology_mode" in tick
    assert "cognitive_load" in tick
    assert "load_components" in tick
