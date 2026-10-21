"""Founders must be able to sleep at UI 1x and 10x.

UI speed multiplies the simulation step (``ColonyGUI._sim_tick``). A slow
frame also widens the base step up to 0.25 s, so 10x is a 2.5 s decision.
Process S has to keep integrating in sim seconds, and a nap chosen before
sleep onset must not discharge it. Energy recovery has to use that same
step length, or a long step spends the body down to exhaustion while the
bowls are still full.
"""

from __future__ import annotations

import random

from colony_agent import SLEEP_WAKEFULNESS_THRESHOLD, ChinchillaAgent
from genome import GenomeVector
from simulation_runner import SimulationRunner

# Nominal UI step at speed 1. ``app._sim_tick`` then multiplies by speed.
# When a frame costs more than the 12 ms budget, the base step grows to
# ``SIM_MAX_STEP_S`` (0.25) before that multiply. 10x in a live UI is 2.5 s.
UI_DT_1X = 1.0 / 12.0
UI_DT_10X = 0.25 * 10.0


def _founders(seed: int, count: int = 4) -> tuple[SimulationRunner, list[ChinchillaAgent]]:
    state = random.getstate()
    random.seed(seed)
    try:
        runner = SimulationRunner()
        genome_rng = random.Random(seed)
        agents: list[ChinchillaAgent] = []
        for index in range(count):
            agent = ChinchillaAgent(
                sex="F" if index % 2 == 0 else "M",
                generation=0,
                genome=GenomeVector.random(genome_rng),
            )
            runner.add_agent(agent)
            agents.append(agent)
        return runner, agents
    finally:
        random.setstate(state)


def test_exploratory_sleep_does_not_discharge_process_s() -> None:
    agent = ChinchillaAgent(sex="F", rng_seed=3)
    agent.colony = [agent]
    agent.wakefulness.wakefulness = 0.2
    agent.is_sleeping = False
    agent.current_action = "sleep"

    agent._apply_sleep_recovery(UI_DT_10X)

    assert agent.is_sleeping is False
    assert agent.current_action == "rest"
    assert agent.wakefulness.wakefulness == 0.2
    assert agent.wakefulness.total_sleep_time == 0.0


def test_onset_starts_a_bout_at_both_timesteps() -> None:
    for dt in (UI_DT_1X, UI_DT_10X):
        agent = ChinchillaAgent(sex="M", rng_seed=4)
        agent.colony = [agent]
        agent.wakefulness.wakefulness = SLEEP_WAKEFULNESS_THRESHOLD + 0.05
        agent.is_sleeping = False
        agent.current_action = "explore"

        agent._apply_sleep_recovery(dt)

        assert agent.is_sleeping is True
        assert agent.wakefulness.wakefulness > 0.6
        assert agent.wakefulness.total_sleep_time > 0.0


def test_founders_accumulate_sleep_pressure_at_1x() -> None:
    runner, agents = _founders(seed=1)
    runner.run_for(90.0, dt=UI_DT_1X)

    assert runner.resources.food_pellets > 0.5
    assert runner.resources.water > 0.5
    for agent in agents:
        assert agent.mortality_system.cause_of_death != "exhaustion"
        assert agent.energy > 0.5
    # 90 sim seconds * 30 physiological seconds * 1/16h ≈ 0.047.
    # Aborted naps on current main hold this near 0.
    assert max(agent.wakefulness.wakefulness for agent in agents) > 0.03


def test_founders_do_not_die_of_exhaustion_at_10x() -> None:
    # Onset is ~0.7 / (30 / 16h) ≈ 1344 sim seconds. 1600 s is past that
    # night's start. Seed 2 died of exhaustion at age 890 s before the fix.
    runner, agents = _founders(seed=2)
    runner.run_for(1600.0, dt=UI_DT_10X)

    assert runner.resources.food_pellets > 0.4
    assert runner.resources.water > 0.4
    assert runner.total_deaths == 0
    for agent in agents:
        assert agent.mortality_system.cause_of_death != "exhaustion"
        assert agent.energy > 0.2
    assert max(agent.wakefulness.total_sleep_time for agent in agents) > 0.0
    assert any(agent.is_sleeping for agent in agents)
