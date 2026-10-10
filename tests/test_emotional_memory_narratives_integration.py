from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager


def _make_deterministic(agent):
    for axis in agent.affective_space.noise_sigma:
        agent.affective_space.noise_sigma[axis] = 0.0
    for axis in agent.affective_space.decay:
        agent.affective_space.decay[axis] = 0.0
    for axis in agent.affective_space.inertia:
        agent.affective_space.inertia[axis] = 0.0


def test_agent_updates_emotional_memory():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

    _make_deterministic(agent)
    agent.step(["ctx"], affective_inputs={"pleasure": 0.6, "arousal": 0.5})

    assert hasattr(agent, "emotional_memory")
    snapshot = agent.emotional_memory.snapshot()
    assert "patterns" in snapshot

    state = agent.get_state()
    assert "emotional_memory" in state
