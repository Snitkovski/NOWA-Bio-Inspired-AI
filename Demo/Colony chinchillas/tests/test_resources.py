from __future__ import annotations

from colony_agent import ChinchillaAgent
from simulation_runner import SimulationRunner


def test_tc01_two_agents_basic_survival_loop() -> None:
    runner = SimulationRunner()
    agent_0 = ChinchillaAgent(sex="F")
    agent_1 = ChinchillaAgent(sex="M")
    runner.add_agent(agent_0)
    runner.add_agent(agent_1)

    runner.run_for(300.0, dt=1.0)

    assert agent_0.sim_time > 290.0
    assert agent_1.sim_time > 290.0
    assert len(agent_0.hippocampus.experiences) > 0
    assert (runner.resources.food_pellets < 1.0) or (runner.resources.hay < 1.0)


def test_tc04_wheel_is_exclusive_resource() -> None:
    runner = SimulationRunner()
    agent_0 = ChinchillaAgent(sex="F")
    agent_1 = ChinchillaAgent(sex="M")
    runner.add_agent(agent_0)
    runner.add_agent(agent_1)

    acquired_0 = agent_0._try_acquire_resource("wheel")
    acquired_1 = agent_1._try_acquire_resource("wheel")

    assert runner.resources.wheel_lock in {agent_0.agent_id, agent_1.agent_id}
    assert acquired_0 != acquired_1
    blocked = agent_0 if not acquired_0 else agent_1
    assert len(blocked.frustration_events) >= 1
