from __future__ import annotations

import os
import tempfile

from agent_knowledge import KnownAgent
from colony_agent import ChinchillaAgent
from colony_population_observer import (
    MAX_HISTORY_LENGTH,
    ColonyPopulationObserver,
)
from simulation_runner import SimulationRunner


def _set_known(
    observer: ChinchillaAgent,
    target: ChinchillaAgent,
    *,
    affinity: float,
    familiarity: float = 0.7,
    relation: str = "acquaintance",
) -> None:
    observer.knowledge[target.agent_id] = KnownAgent(
        agent_id=target.agent_id,
        name=target.name,
        sex=target.sex,
        last_seen_position=target.position,
        last_seen_time=observer.sim_time,
        familiarity=familiarity,
        affinity=affinity,
        relationship_type=relation,
    )


def test_tc01_observe_on_empty_runner() -> None:
    runner = SimulationRunner()
    observer = ColonyPopulationObserver(runner)

    snapshot = observer.observe_force()

    assert snapshot is not None
    assert snapshot.agent_count == 0
    assert snapshot.mean_stress == 0.0
    assert snapshot.action_distribution == {}
    assert snapshot.food_pellets >= 0.0


def test_tc02_observe_every_n_ticks_filters() -> None:
    runner = SimulationRunner()
    observer = ColonyPopulationObserver(runner, observe_every_n_ticks=3)

    results = [observer.observe_tick() for _ in range(9)]
    non_none = [item for item in results if item is not None]

    assert len(non_none) == 3
    assert len(observer.history) == 3


def test_tc03_demographic_counters() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F", is_mature=True))
    runner.add_agent(ChinchillaAgent(sex="F", is_mature=False))
    runner.add_agent(ChinchillaAgent(sex="M", is_mature=True))

    observer = ColonyPopulationObserver(runner)
    snapshot = observer.observe_force()

    assert snapshot.agent_count == 3
    assert snapshot.female_count == 2
    assert snapshot.male_count == 1
    assert snapshot.juvenile_count == 1
    assert snapshot.adult_count == 2


def test_tc04_mean_stress_reads_from_affective_space() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F")
    agent.affective_space.axes["stress"] = 0.6
    runner.add_agent(agent)

    observer = ColonyPopulationObserver(runner)
    snapshot = observer.observe_force()

    assert abs(snapshot.mean_stress - 0.6) < 1e-6


def test_tc05_social_cohesion_grows_for_bonded_pairs() -> None:
    runner = SimulationRunner()
    female = ChinchillaAgent(sex="F")
    male = ChinchillaAgent(sex="M")
    _set_known(female, male, affinity=0.8, familiarity=0.9, relation="bonded")
    runner.add_agent(female)
    runner.add_agent(male)

    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    cohesion = observer.get_social_cohesion()
    assert cohesion > 0.3


def test_tc06_extinction_risk_with_one_agent() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))

    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    risk = observer.get_extinction_risk()
    assert risk >= 0.4


def test_tc07_extinction_risk_with_healthy_population() -> None:
    runner = SimulationRunner()
    for index in range(4):
        sex = "F" if index % 2 == 0 else "M"
        agent = ChinchillaAgent(sex=sex, is_mature=True)
        agent.affective_space.axes["stress"] = 0.1
        runner.add_agent(agent)
    runner.resources.food_pellets = 0.8

    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    risk = observer.get_extinction_risk()
    assert risk < 0.3


def test_tc08_births_since_last_uses_total_births_delta() -> None:
    runner = SimulationRunner()
    runner.total_births = 0
    runner.total_deaths = 0
    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    runner.total_births = 2
    snapshot = observer.observe_force()

    assert snapshot.births_since_last == 2
    assert snapshot.total_births == 2


def test_tc09_get_trend_returns_values_in_order() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F")
    runner.add_agent(agent)
    observer = ColonyPopulationObserver(runner)

    stress_levels = [0.1, 0.3, 0.5, 0.2, 0.4]
    for stress in stress_levels:
        agent.affective_space.axes["stress"] = stress
        observer.observe_force()

    trend = observer.get_trend("mean_stress", last_n=5)
    assert len(trend) == 5
    for expected, actual in zip(stress_levels, trend):
        assert abs(expected - actual) < 1e-6


def test_tc10_get_trend_for_unknown_field_returns_empty() -> None:
    runner = SimulationRunner()
    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    trend = observer.get_trend("nonexistent_field_xyz")
    assert trend == []


def test_tc11_save_load_round_trip() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    observer = ColonyPopulationObserver(runner)
    observer.observe_force()
    observer.observe_force()

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        observer.save(path)

        observer2 = ColonyPopulationObserver(runner)
        observer2.load(path)

        assert len(observer2.history) == 2
        assert abs(observer2.history[0].mean_stress - observer.history[0].mean_stress) < 1e-6
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_tc12_action_distribution_counts_correctly() -> None:
    runner = SimulationRunner()
    actions = ["eat", "eat", "sleep", "explore"]
    for idx, action in enumerate(actions):
        agent = ChinchillaAgent(sex="F" if idx % 2 == 0 else "M")
        agent.current_action = action
        runner.add_agent(agent)

    observer = ColonyPopulationObserver(runner)
    snapshot = observer.observe_force()

    assert snapshot.action_distribution["eat"] == 2
    assert snapshot.action_distribution["sleep"] == 1
    assert snapshot.action_distribution["explore"] == 1


def test_tc13_summary_text_has_expected_parts() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    runner.add_agent(ChinchillaAgent(sex="M"))
    observer = ColonyPopulationObserver(runner)
    observer.observe_force()

    text = observer.summary_text()
    assert "2" in text
    assert "stress" in text.lower()
    assert len(text) > 10


def test_tc14_get_population_peak() -> None:
    runner = SimulationRunner()
    observer = ColonyPopulationObserver(runner)

    for count in [1, 3, 2, 4, 2]:
        runner.agents = [ChinchillaAgent(sex="F") for _ in range(count)]
        observer.observe_force()

    peak = observer.get_population_peak()
    assert peak is not None
    assert peak.agent_count == 4


def test_tc15_history_is_limited_by_max_history_length() -> None:
    runner = SimulationRunner()
    observer = ColonyPopulationObserver(runner)

    for _ in range(MAX_HISTORY_LENGTH + 50):
        observer.observe_force()

    assert len(observer.history) == MAX_HISTORY_LENGTH


def test_tc16_agent_without_nowa_does_not_break_observer() -> None:
    class MinimalAgent:
        agent_id = "test"
        sex = "F"
        age = 0.0
        current_action = "idle"
        position = "floor"
        is_sleeping = False
        is_mature = True
        is_pregnant = False

    runner = SimulationRunner()
    runner.agents = [MinimalAgent()]

    observer = ColonyPopulationObserver(runner)
    snapshot = observer.observe_force()

    assert snapshot is not None
    assert snapshot.agent_count == 1
    assert snapshot.mean_stress == 0.0
