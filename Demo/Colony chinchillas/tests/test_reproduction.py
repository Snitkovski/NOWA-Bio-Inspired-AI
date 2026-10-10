from __future__ import annotations

from agent_knowledge import KnownAgent
from colony_agent import ChinchillaAgent
from config_colony import OFFER_COOLDOWNS
from social_offers import SocialOffer
from simulation_runner import SimulationRunner


def _set_known(
    observer: ChinchillaAgent,
    target: ChinchillaAgent,
    *,
    affinity: float,
    relation: str = "acquaintance",
    familiarity: float = 0.7,
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


def test_tc07_full_reproduction_cycle_from_mating_to_spawn() -> None:
    runner = SimulationRunner()
    agent_f = ChinchillaAgent(sex="F", is_mature=True, position="floor")
    agent_m = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    runner.add_agent(agent_f)
    runner.add_agent(agent_m)

    _set_known(agent_f, agent_m, affinity=0.7)
    _set_known(agent_m, agent_f, affinity=0.6)
    assert agent_f.heat_cycle is not None
    agent_f.heat_cycle.phase = "estrus"
    agent_f.heat_cycle.value = 0.8
    agent_f.affective_space.axes["stress"] = 0.1
    agent_m.affective_space.axes["stress"] = 0.1
    agent_f.energy = 0.9
    agent_m.energy = 0.9

    mating_response = agent_m.send_social_offer("mount_display", agent_f)
    assert mating_response is not None
    assert mating_response.accepted is True

    runner.run_for(120.0, dt=1.0)

    assert agent_f.is_pregnant is True
    assert agent_f.gestation_timer > 0.0

    agent_f.gestation_timer = 1.0
    runner.run_for(3.0, dt=1.0)

    assert len(runner.agents) >= 3
    offspring = [a for a in runner.agents if a.generation == 1][0]
    assert agent_f.agent_id in offspring.knowledge
    assert offspring.knowledge[agent_f.agent_id].affinity >= 0.85


def test_tc07b_birth_preserves_father_id_when_father_object_missing() -> None:
    mother = ChinchillaAgent(sex="F", is_mature=True)
    mother.colony = [mother]
    mother.is_pregnant = True
    mother._current_mate_id = "missing-father-id"

    mother._give_birth()

    assert mother.pending_offspring_list
    for offspring in mother.pending_offspring_list:
        assert offspring.parents[0] == mother.agent_id
        assert offspring.parents[1] == "missing-father-id"


def test_tc09_juvenile_cannot_start_adult_offer_but_can_socialize() -> None:
    juvenile = ChinchillaAgent(sex="F", age=100.0, is_mature=False, position="floor")
    adult = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    juvenile.colony = [juvenile, adult]
    adult.colony = [juvenile, adult]
    _set_known(juvenile, adult, affinity=0.6)
    _set_known(adult, juvenile, affinity=0.4)

    blocked = juvenile.send_social_offer("mount_display", adult)
    allowed = juvenile.send_social_offer("allogroom", adult)

    assert blocked is not None and blocked.accepted is False
    assert allowed is not None and allowed.accepted is True
    assert juvenile.heat_cycle is None


def test_tc10_inbreeding_parent_offspring_blocked() -> None:
    mother = ChinchillaAgent(sex="F", is_mature=True)
    son = ChinchillaAgent(sex="M", is_mature=True, parents=(mother.agent_id, None))
    mother.colony = [mother, son]
    son.colony = [mother, son]
    _set_known(mother, son, affinity=0.8, relation="kin")
    _set_known(son, mother, affinity=0.8, relation="kin")
    assert mother.heat_cycle is not None
    mother.heat_cycle.phase = "estrus"
    mother.heat_cycle.value = 0.85

    offer = SocialOffer("mount_display", son.agent_id, son.get_public_state(), 0.9)
    response = mother.receive_social_offer(offer)

    assert response is not None
    assert response.accepted is False
    assert response.reason == "kin"
    assert mother.is_pregnant is False


def test_tc12_low_food_blocks_reproduction_and_population_growth() -> None:
    runner = SimulationRunner()
    runner._refill_enabled = False
    runner.resources.food_pellets = 0.1
    runner.resources.hay = 0.1

    female = ChinchillaAgent(sex="F", is_mature=True, position="floor")
    male = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    runner.add_agent(female)
    runner.add_agent(male)
    _set_known(female, male, affinity=0.7)
    _set_known(male, female, affinity=0.7)
    assert female.heat_cycle is not None
    female.heat_cycle.phase = "estrus"
    female.heat_cycle.value = 0.9

    response = male.send_social_offer("mount_display", female)
    runner.run_for(30.0, dt=1.0)

    assert response is not None
    assert response.accepted is False
    assert female.is_pregnant is False
    assert len(runner.agents) == 2


def test_tc13_relaxed_affinity_threshold_allows_mating_in_estrus() -> None:
    female = ChinchillaAgent(sex="F", is_mature=True, position="floor")
    male = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    female.colony = [female, male]
    male.colony = [female, male]
    _set_known(female, male, affinity=0.31)
    _set_known(male, female, affinity=0.36)

    assert female.heat_cycle is not None
    female.heat_cycle.phase = "estrus"
    female.heat_cycle.value = 0.55
    female.affective_space.axes["stress"] = 0.1
    male.affective_space.axes["stress"] = 0.1
    female.energy = 0.9
    male.energy = 0.9

    response = male.send_social_offer("mount_display", female)

    assert response is not None
    assert response.accepted is True
    assert female.is_pregnant is True


def test_tc14_mount_display_prefers_estrus_partner_even_from_nearby_contact() -> None:
    male = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    female = ChinchillaAgent(sex="F", is_mature=True, position="house")
    male.colony = [male, female]
    female.colony = [male, female]
    _set_known(male, female, affinity=0.24)
    _set_known(female, male, affinity=0.24)

    assert female.heat_cycle is not None
    female.heat_cycle.phase = "estrus"
    female.heat_cycle.value = 0.82
    male.energy = 0.9
    male.affective_space.axes["stress"] = 0.05
    male.reproductive_system.reproductive_drive = 0.7

    male._perceive()
    offer_type, target = male._choose_social_offer()

    assert offer_type == "mount_display"
    assert target is female


def test_tc15_mount_display_cooldown_is_shorter_for_more_attempts() -> None:
    assert OFFER_COOLDOWNS["mount_display"] == 45.0


def test_tc16_low_familiar_contact_repeats_sniff_greet_before_mating() -> None:
    male = ChinchillaAgent(sex="M", is_mature=True, position="floor")
    female = ChinchillaAgent(sex="F", is_mature=True, position="floor")
    male.colony = [male, female]
    female.colony = [male, female]

    _set_known(male, female, affinity=0.07, familiarity=0.2)
    _set_known(female, male, affinity=0.18, familiarity=0.35)

    male._perceive()
    offer_type, target = male._choose_social_offer()

    assert offer_type == "sniff_greet"
    assert target is female
