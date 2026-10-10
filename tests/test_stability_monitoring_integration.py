from agent import Agent
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import SleepManager


def test_agent_updates_stability_monitor_on_step():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent_mem = IntentMemory()
    sleep_mgr = SleepManager(hip, cortex, intent_mem)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

    for _ in range(5):
        agent.step(
            context_events=["user:test"],
            reward=0.1,
            novelty=0.2,
            conflict=0.0,
            intensity=1.0,
        )

    assert hasattr(agent, "stability_monitor")

    snapshot = agent.stability_monitor.snapshot()
    assert "stability_index" in snapshot
    assert "drift_flags" in snapshot
    assert "recommendation" in snapshot
    assert int(snapshot.get("metrics", {}).get("sample_count", 0)) >= 5

    state = agent.get_state()
    assert "stability_monitor" in state
    assert "stability_index" in state["stability_monitor"]

