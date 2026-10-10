from __future__ import annotations

import json

from colony_agent import ChinchillaAgent
from colony_swarm_bridge import (
    MIN_AGENT_DISTANCE_COLONY,
    ZONE_JITTER_RANGE,
    ColonySwarmBridge,
)
from simulation_runner import SimulationRunner


def _find_signal(signals: list[object], source_id: str):
    for signal in signals:
        if getattr(signal, "source_agent_id", "") == source_id:
            return signal
    return None


def test_bridge_add_agent_assigns_3d_position() -> None:
    bridge = ColonySwarmBridge()
    agent = ChinchillaAgent(sex="F", position="floor")
    bridge.add_agent(agent)

    pos = bridge._swarm.get_position(agent.agent_id)
    assert pos is not None
    assert abs(pos.x - 50.0) <= ZONE_JITTER_RANGE
    assert abs(pos.z - 0.0) < 1e-6


def test_bridge_sync_positions_updates_after_zone_change() -> None:
    bridge = ColonySwarmBridge()
    agent = ChinchillaAgent(sex="M", position="floor")
    bridge.add_agent(agent)

    agent.position = "house"
    bridge.sync_positions()

    pos = bridge._swarm.get_position(agent.agent_id)
    assert pos is not None
    assert abs(pos.x - 20.0) <= ZONE_JITTER_RANGE
    assert abs(pos.y - 20.0) <= ZONE_JITTER_RANGE


def test_bridge_same_zone_agents_have_separated_positions() -> None:
    bridge = ColonySwarmBridge()
    agents = [ChinchillaAgent(sex="F", position="floor") for _ in range(3)]
    for agent in agents:
        bridge.add_agent(agent)
    bridge.sync_positions()

    positions = [bridge._swarm.get_position(agent.agent_id) for agent in agents]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            left = positions[i]
            right = positions[j]
            assert left is not None and right is not None
            assert left.distance_to(right) >= MIN_AGENT_DISTANCE_COLONY


def test_bridge_update_signals_delivers_payload() -> None:
    bridge = ColonySwarmBridge()
    stressed = ChinchillaAgent(sex="F", position="floor")
    calm = ChinchillaAgent(sex="M", position="floor")
    stressed.affective_space.axes["stress"] = 0.9
    calm.affective_space.axes["stress"] = 0.1
    bridge.add_agent(stressed)
    bridge.add_agent(calm)
    bridge.sync_positions()

    captured: list[dict] = []

    def _capture(*, source: str, payload: dict, uncertainty: float) -> None:
        captured.append(
            {
                "source": source,
                "payload": payload,
                "uncertainty": uncertainty,
            }
        )

    calm.observe_external_input = _capture  # type: ignore[method-assign]

    signals_sent = bridge.update_signals()
    assert signals_sent > 0
    assert captured
    assert any(item["payload"].get("stress", 0.0) != 0.0 for item in captured)


def test_bridge_check_mortality_removes_dead_agent() -> None:
    bridge = ColonySwarmBridge()
    agent = ChinchillaAgent(sex="M", position="floor")
    bridge.add_agent(agent)

    agent.mortality_system.death_step = 0
    dead_ids = bridge.check_mortality()

    assert agent.agent_id in dead_ids
    assert bridge._swarm.get_agent(agent.agent_id) is None


def test_bridge_check_reproduction_returns_empty_without_factory() -> None:
    bridge = ColonySwarmBridge()
    female = ChinchillaAgent(sex="F", position="floor", is_mature=True)
    male = ChinchillaAgent(sex="M", position="floor", is_mature=True)

    female.reproductive_system.reproductive_drive = 0.9
    male.reproductive_system.reproductive_drive = 0.9
    female.affective_space.axes["valence"] = 0.4
    male.affective_space.axes["valence"] = 0.4
    female.neuromodulators.cortisol = 0.1
    male.neuromodulators.cortisol = 0.1

    bridge.add_agent(female)
    bridge.add_agent(male)
    bridge.sync_positions()

    newborns = bridge.check_reproduction()
    assert newborns == []
    assert female.is_pregnant is False


def test_bridge_check_reproduction_starts_pregnancy_with_factory() -> None:
    bridge = ColonySwarmBridge(factory=object())
    female = ChinchillaAgent(sex="F", position="floor", is_mature=True)
    male = ChinchillaAgent(sex="M", position="floor", is_mature=True)

    female.reproductive_system.reproductive_drive = 0.9
    male.reproductive_system.reproductive_drive = 0.9
    female.affective_space.axes["valence"] = 0.4
    male.affective_space.axes["valence"] = 0.4
    female.neuromodulators.cortisol = 0.1
    male.neuromodulators.cortisol = 0.1

    bridge.add_agent(female)
    bridge.add_agent(male)
    bridge.sync_positions()

    bridge.check_reproduction()
    assert female.is_pregnant is True


def test_bridge_3d_distance_uses_vertical_axis() -> None:
    bridge = ColonySwarmBridge()
    a1 = ChinchillaAgent(sex="F", position="floor")
    a2 = ChinchillaAgent(sex="M", position="shelf_upper")
    bridge.add_agent(a1)
    bridge.add_agent(a2)
    bridge.sync_positions()

    pos1 = bridge._swarm.get_position(a1.agent_id)
    pos2 = bridge._swarm.get_position(a2.agent_id)
    assert pos1 is not None and pos2 is not None
    assert pos1.distance_to(pos2) > 40.0


def test_bridge_signal_strength_decays_with_distance() -> None:
    bridge = ColonySwarmBridge()
    bridge._swarm.config.base_perception_radius = 200.0
    emitter = ChinchillaAgent(sex="F", position="floor")
    near = ChinchillaAgent(sex="M", position="floor")
    far = ChinchillaAgent(sex="F", position="shelf_upper")
    emitter.affective_space.axes["stress"] = 0.95

    bridge.add_agent(emitter)
    bridge.add_agent(near)
    bridge.add_agent(far)
    bridge.sync_positions()

    signals_near = bridge._swarm.collect_signals_for_agent(near.agent_id)
    signals_far = bridge._swarm.collect_signals_for_agent(far.agent_id)
    near_signal = _find_signal(signals_near, emitter.agent_id)
    far_signal = _find_signal(signals_far, emitter.agent_id)
    assert near_signal is not None and far_signal is not None
    assert near_signal.signal_strength > far_signal.signal_strength


def test_bridge_update_ecology_returns_share_in_range() -> None:
    bridge = ColonySwarmBridge()
    for idx in range(5):
        bridge.add_agent(ChinchillaAgent(sex="F" if idx % 2 == 0 else "M"))
    share = bridge.update_ecology(5)
    assert 0.0 <= share <= 1.0


def test_runner_tick_integrates_swarm_and_logs_death() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="M")
    runner.add_agent(agent)

    agent.mortality_system.death_step = 0
    runner.tick(0.1)

    assert agent.agent_id not in {item.agent_id for item in runner.agents}
    assert runner.swarm._swarm.get_agent(agent.agent_id) is None
    assert len(runner._death_log) == 1


def test_runner_writes_death_journal_with_cause(tmp_path) -> None:
    journal_path = tmp_path / "deaths.jsonl"
    runner = SimulationRunner(death_journal_path=journal_path)
    agent = ChinchillaAgent(sex="M")
    runner.add_agent(agent)
    agent.mortality_system.cause_of_death = "exhaustion"
    agent.mortality_system.death_step = 10

    runner.tick(0.1)

    assert journal_path.exists()
    lines = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["agent_id"] == agent.agent_id
    assert payload["cause_of_death"] == "exhaustion"
    assert payload["sim_time"] > 0.0


def test_runner_spawned_offspring_added_to_swarm() -> None:
    runner = SimulationRunner()
    mother = ChinchillaAgent(sex="F", is_mature=True)
    runner.add_agent(mother)
    child = ChinchillaAgent(sex="M", is_mature=False, generation=1)
    mother.pending_offspring_list.append(child)

    runner.tick(0.1)
    assert child.agent_id in {agent.agent_id for agent in runner.agents}
    assert runner.swarm._swarm.get_agent(child.agent_id) is not None
