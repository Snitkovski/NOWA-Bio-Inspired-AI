from __future__ import annotations

from agent_knowledge import KnownAgent
from colony_agent import ChinchillaAgent
from simulation_runner import SimulationRunner


def _link_pair(a: ChinchillaAgent, b: ChinchillaAgent, affinity_ab: float, affinity_ba: float) -> None:
    a.knowledge[b.agent_id] = KnownAgent(
        agent_id=b.agent_id,
        name=b.name,
        sex=b.sex,
        last_seen_position=b.position,
        last_seen_time=a.sim_time,
        familiarity=0.5,
        affinity=affinity_ab,
        relationship_type="acquaintance",
    )
    b.knowledge[a.agent_id] = KnownAgent(
        agent_id=a.agent_id,
        name=a.name,
        sex=a.sex,
        last_seen_position=a.position,
        last_seen_time=b.sim_time,
        familiarity=0.5,
        affinity=affinity_ba,
        relationship_type="acquaintance",
    )


def test_tc03_allogroom_increases_affinity_and_can_create_bond() -> None:
    runner = SimulationRunner()
    a0 = ChinchillaAgent(sex="F", position="floor")
    a1 = ChinchillaAgent(sex="M", position="floor")
    _link_pair(a0, a1, affinity_ab=0.35, affinity_ba=0.35)
    a0.social_drive = 0.95
    a1.social_drive = 0.95

    runner.add_agent(a0)
    runner.add_agent(a1)
    runner.run_for(300.0, dt=1.0)

    known = a0.knowledge[a1.agent_id]
    groom_events = [ep for ep in known.interaction_history if ep.interaction_type == "allogroom"]
    assert len(groom_events) >= 1
    assert known.affinity > 0.3
    if known.affinity > 0.6:
        assert known.relationship_type == "bonded"


def test_tc11_offer_timeout_produces_frustration_and_timeout_episode() -> None:
    a = ChinchillaAgent(sex="F", position="floor")
    b = ChinchillaAgent(sex="M", position="floor")
    a.colony = [a, b]
    b.colony = [a, b]
    _link_pair(a, b, affinity_ab=0.5, affinity_ba=0.5)

    b.current_action = "busy"
    b._exclusive_action_timer = 100.0

    response = a.send_social_offer("allogroom", b)
    assert response is None

    for _ in range(11):
        a.sim_step(1.0)

    assert "offer_timeout" in a.frustration_events
    history = a.knowledge[b.agent_id].interaction_history
    assert any(ep.outcome == "timeout" for ep in history)
