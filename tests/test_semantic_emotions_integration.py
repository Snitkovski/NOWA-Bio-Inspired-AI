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


def test_agent_updates_semantic_emotions():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

    _make_deterministic(agent)

    agent.step(["ctx"], affective_inputs={"pleasure": 0.5, "arousal": 0.5})

    assert hasattr(agent, "semantic_emotions")
    active = agent.semantic_emotions.snapshot()
    assert any(item.get("emotion") == "joy" for item in active)

    state = agent.get_state()
    assert "semantic_emotions" in state
