from __future__ import annotations

from pathlib import Path

from colony_agent import ChinchillaAgent
from colony_storage import ColonyStorage
from simulation_runner import SimulationRunner


def _find_agent(agents: list[ChinchillaAgent], agent_id: str) -> ChinchillaAgent:
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent
    raise AssertionError(f"Agent not found: {agent_id}")


def test_storage_roundtrip_preserves_runner_and_links(tmp_path: Path) -> None:
    runner = SimulationRunner()
    a0 = ChinchillaAgent(sex="F", position="floor")
    a1 = ChinchillaAgent(sex="M", position="floor")
    runner.add_agent(a0)
    runner.add_agent(a1)
    runner.run_for(15.0, dt=1.0)
    a0._try_acquire_resource("wheel")
    runner._refill_enabled = False

    storage = ColonyStorage(save_dir=tmp_path)
    saved_path = storage.save_colony(runner, "roundtrip.json")
    loaded = storage.load_colony(saved_path)

    assert len(loaded.agents) == 2
    assert loaded.sim_time == runner.sim_time
    assert loaded._refill_enabled is False
    assert loaded.resources.wheel_lock == runner.resources.wheel_lock

    loaded_ids = {agent.agent_id for agent in loaded.agents}
    expected_ids = {a0.agent_id, a1.agent_id}
    assert loaded_ids == expected_ids

    for agent in loaded.agents:
        assert agent.resources is loaded.resources
        assert agent.colony is loaded.agents
        assert hasattr(agent, "hippocampus")
        assert not hasattr(agent, "affect")


def test_storage_preserves_pending_offspring(tmp_path: Path) -> None:
    runner = SimulationRunner()
    mother = ChinchillaAgent(sex="F", is_mature=True, position="house")
    father = ChinchillaAgent(sex="M", is_mature=True, position="house")
    runner.add_agent(mother)
    runner.add_agent(father)

    offspring = ChinchillaAgent(
        sex="F",
        age=0.0,
        generation=1,
        parents=(mother.agent_id, father.agent_id),
        is_mature=False,
    )
    mother.pending_offspring_list.append(offspring)

    storage = ColonyStorage(save_dir=tmp_path)
    saved_path = storage.save_colony(runner, "pending.json")
    loaded = storage.load_colony(saved_path)

    loaded_mother = _find_agent(loaded.agents, mother.agent_id)
    assert len(loaded_mother.pending_offspring_list) == 1
    loaded_child = loaded_mother.pending_offspring_list[0]
    assert loaded_child.parents[0] == loaded_mother.agent_id
    assert loaded_child.resources is loaded.resources
    assert loaded_child.colony is loaded.agents


def test_storage_list_and_delete(tmp_path: Path) -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))

    storage = ColonyStorage(save_dir=tmp_path)
    storage.save_colony(runner, "first.json")
    storage.save_colony(runner, "second.json")

    names = {item["name"] for item in storage.get_save_files()}
    assert {"first.json", "second.json"}.issubset(names)

    deleted = storage.delete_save("first.json")
    assert deleted is True
    names_after = {item["name"] for item in storage.get_save_files()}
    assert "first.json" not in names_after


def test_storage_preserves_extended_death_log_fields(tmp_path: Path) -> None:
    runner = SimulationRunner()
    runner._death_log = [
        {
            "agent_id": "a-1",
            "sim_time": 12.5,
            "cause_of_death": "exhaustion",
            "recorded_at_utc": "2026-04-07T12:00:00+00:00",
            "energy": 0.01,
        }
    ]
    storage = ColonyStorage(save_dir=tmp_path)
    saved_path = storage.save_colony(runner, "deathlog.json")

    loaded = storage.load_colony(saved_path)
    assert loaded._death_log
    entry = loaded._death_log[0]
    assert entry["agent_id"] == "a-1"
    assert entry["sim_time"] == 12.5
    assert entry["cause_of_death"] == "exhaustion"
    assert entry["recorded_at_utc"] == "2026-04-07T12:00:00+00:00"
    assert entry["energy"] == 0.01
