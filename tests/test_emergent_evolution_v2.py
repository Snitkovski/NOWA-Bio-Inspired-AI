import random
from types import SimpleNamespace

import pytest

from ecology import EcologyLayer
from epigenome import EpigenomeSnapshot
from fitness import FitnessEvaluator
from genome import GenomeVector
from mortality import MortalitySystem
from population_observer import PopulationObserver, PopulationSnapshot
from reproduction import (
    MIN_COMPATIBILITY_THRESHOLD,
    MIN_REPRODUCTIVE_AGE,
    ReproductiveSystem,
    compute_compatibility,
)
from swarm import Position3D, SpaceBounds, SwarmConfig, SwarmEnvironment


class DummyAgent:
    def __init__(
        self,
        agent_id: str,
        *,
        genome: GenomeVector | None = None,
        energy: float = 0.8,
        valence: float = 0.5,
        cortisol: float = 0.1,
        wakefulness: float = 0.2,
        lived_steps: int = 200,
    ) -> None:
        self.agent_id = agent_id
        self.genome = genome if genome is not None else GenomeVector.default()
        self.epigenome = EpigenomeSnapshot.empty()
        self.affective_space = SimpleNamespace(
            axes={
                "valence": valence,
                "arousal": 0.2,
                "stress": 0.2,
                "curiosity": 0.2,
            }
        )
        self.neuromodulators = SimpleNamespace(cortisol=cortisol)
        self.wakefulness = SimpleNamespace(wakefulness=wakefulness)
        self.autonomous_runtime = SimpleNamespace(energy_system=SimpleNamespace(energy=energy))
        self.cortisol_history = [cortisol]
        self.lived_steps = lived_steps
        self.reproductive_system = ReproductiveSystem()
        self.mortality_system = MortalitySystem()
        self.expected_lifetime_steps = 10000

    def step(self, *args, **kwargs) -> str:
        self.lived_steps += 1
        return "act"

    def sleep(self, *args, **kwargs) -> dict:
        return {"cycles": 1}

    def observe_external_input(self, *args, **kwargs) -> None:
        return None


class DummyFactory:
    def __init__(self) -> None:
        self._counter = 0

    def extract_genome(self, agent):
        return getattr(agent, "genome", GenomeVector.default())

    def extract_epigenome(self, agent):
        payload = getattr(agent, "epigenome", EpigenomeSnapshot.empty())
        if isinstance(payload, EpigenomeSnapshot):
            return payload
        return EpigenomeSnapshot.empty()

    def spawn(self, genome, epigenome=None, epigenome_noise=0.1, rng=None, agent_id=""):
        del epigenome_noise
        del rng
        self._counter += 1
        child_id = agent_id or f"child_{self._counter}"
        child = DummyAgent(child_id, genome=genome, lived_steps=0)
        child.epigenome = epigenome if isinstance(epigenome, EpigenomeSnapshot) else EpigenomeSnapshot.empty()
        return child


def _build_env(factory=None, **config_kwargs) -> SwarmEnvironment:
    return SwarmEnvironment(
        config=SwarmConfig(
            bounds=SpaceBounds(x_max=100.0, y_max=100.0),
            **config_kwargs,
        ),
        fitness_evaluator=FitnessEvaluator(),
        rng=random.Random(42),
        factory=factory,
    )


def test_tc_01_reproductive_drive_grows_with_favorable_conditions():
    rs = ReproductiveSystem(drive_threshold=0.7, drive_decay=0.01, drive_recovery_rate=0.05)
    for _ in range(100):
        rs.update(energy=0.9, valence=0.8, cortisol=0.05, lived_steps=200, resource_share=0.9)
    assert rs.reproductive_drive > 0.5


def test_tc_02_reproductive_drive_stays_low_under_stress():
    rs = ReproductiveSystem()
    for _ in range(100):
        rs.update(energy=0.1, valence=-0.8, cortisol=0.9, lived_steps=200, resource_share=0.1)
    assert rs.reproductive_drive < 0.1


def test_tc_03_reproductive_drive_locked_before_maturity():
    rs = ReproductiveSystem()
    for step in range(MIN_REPRODUCTIVE_AGE - 1):
        rs.update(energy=1.0, valence=1.0, cortisol=0.0, lived_steps=step, resource_share=1.0)
    assert rs.reproductive_drive == 0.0
    assert rs.is_ready() is False


def test_tc_04_is_ready_depends_on_threshold():
    rs = ReproductiveSystem(drive_threshold=0.5)
    rs.reproductive_drive = 0.6
    assert rs.is_ready() is True
    rs.reproductive_drive = 0.4
    assert rs.is_ready() is False


def test_tc_05_register_reproduction_starts_cooldown():
    rs = ReproductiveSystem(cooldown_duration=50)
    rs.reproductive_drive = 0.9
    rs.register_reproduction(current_step=500)

    assert rs.total_offspring == 1
    assert rs.last_reproduction_step == 500
    assert rs.cooldown_steps == 50
    assert rs.reproductive_drive == 0.0

    rs.update(energy=1.0, valence=1.0, cortisol=0.0, lived_steps=501, resource_share=1.0)
    assert rs.reproductive_drive == 0.0


def test_tc_06_compute_compatibility_high_for_well_matched_agents():
    snapshot_a = {
        "genome_distance": 0.3,
        "valence": 0.5,
        "cortisol": 0.1,
        "reproductive_drive": 0.8,
    }
    snapshot_b = {
        "genome_distance": 0.3,
        "valence": 0.5,
        "cortisol": 0.1,
        "reproductive_drive": 0.8,
    }
    compat = compute_compatibility(snapshot_a, snapshot_b)
    assert compat >= 0.7


def test_tc_07_compute_compatibility_low_for_mismatched_agents():
    snapshot_a = {
        "genome_distance": 0.0,
        "valence": -0.8,
        "cortisol": 0.9,
        "reproductive_drive": 0.1,
    }
    snapshot_b = {
        "genome_distance": 0.0,
        "valence": 0.8,
        "cortisol": 0.9,
        "reproductive_drive": 0.1,
    }
    compat = compute_compatibility(snapshot_a, snapshot_b)
    assert compat < MIN_COMPATIBILITY_THRESHOLD


def test_tc_08_mortality_death_by_exhaustion():
    ms = MortalitySystem(critical_energy_threshold=0.05)
    died = ms.update(energy=0.03, wakefulness=0.3, lived_steps=100, cortisol_mean=0.1)
    assert died is True
    assert ms.is_dead() is True
    assert ms.cause_of_death == "exhaustion"
    assert ms.death_step == 100


def test_tc_09_mortality_death_by_sleep_deprivation():
    ms = MortalitySystem(critical_wakefulness_threshold=0.95)
    died = ms.update(energy=0.8, wakefulness=0.97, lived_steps=200, cortisol_mean=0.2)
    assert died is True
    assert ms.cause_of_death == "sleep_deprivation"


def test_tc_10_mortality_death_by_old_age():
    ms = MortalitySystem(max_lifespan_steps=1000)
    died = ms.update(energy=0.8, wakefulness=0.3, lived_steps=1000, cortisol_mean=0.1)
    assert died is True
    assert ms.cause_of_death == "old_age"


def test_tc_11_senescence_reduces_vitality():
    ms = MortalitySystem(max_lifespan_steps=1000, senescence_start_fraction=0.7)
    for step in range(700):
        ms.update(energy=0.8, wakefulness=0.3, lived_steps=step, cortisol_mean=0.1)
    vitality_at_start = ms.vitality
    assert vitality_at_start > 0.95

    for step in range(700, 900):
        ms.update(energy=0.8, wakefulness=0.3, lived_steps=step, cortisol_mean=0.1)
    assert ms.vitality < vitality_at_start


def test_tc_12_ecology_resource_share_is_population_sensitive():
    ecology = EcologyLayer(total_resources=1000.0, current_resources=500.0, resource_per_agent_base=10.0)
    share_10 = ecology.compute_resource_share(agent_count=10)
    share_100 = ecology.compute_resource_share(agent_count=100)
    assert 0.0 <= share_10 <= 1.0
    assert 0.0 <= share_100 <= 1.0
    assert share_10 > share_100
    assert ecology.compute_resource_share(agent_count=0) == 1.0


def test_tc_13_ecology_consume_reduces_resources():
    ecology = EcologyLayer(
        total_resources=1000.0,
        current_resources=1000.0,
        resource_per_agent_base=10.0,
        resource_regen_rate=1.0,
    )
    share = ecology.consume(agent_count=5)
    assert abs(ecology.current_resources - 951.0) < 1e-6
    assert 0.0 <= share <= 1.0


def test_tc_14_ecology_consume_clamps_at_zero():
    ecology = EcologyLayer(
        total_resources=100.0,
        current_resources=5.0,
        resource_per_agent_base=10.0,
        resource_regen_rate=0.0,
    )
    ecology.consume(agent_count=100)
    assert ecology.current_resources == 0.0


def test_tc_15_reproduce_creates_child_and_updates_counters():
    factory = DummyFactory()
    env = _build_env(factory=factory, mutation_rate=0.05)
    parent_a = DummyAgent("pa", lived_steps=500)
    parent_b = DummyAgent("pb", lived_steps=500)
    parent_a.reproductive_system.reproductive_drive = 0.9
    parent_b.reproductive_system.reproductive_drive = 0.9

    env.add_agent(parent_a, position=Position3D(10.0, 10.0, 0.0))
    env.add_agent(parent_b, position=Position3D(12.0, 10.0, 0.0))
    result = env._reproduce(parent_a, parent_b)

    assert result is not None
    assert env.births_this_step == 1
    assert parent_a.reproductive_system.total_offspring == 1
    assert parent_b.reproductive_system.total_offspring == 1
    child_pos = env.get_position(result.agent_id)
    assert child_pos is not None
    assert child_pos.distance_to(Position3D(11.0, 10.0, 0.0)) < 10.0


def test_tc_16_crowded_ecology_slows_drive_growth():
    ecology_crowded = EcologyLayer(total_resources=100.0, current_resources=100.0, resource_per_agent_base=10.0)
    ecology_sparse = EcologyLayer(total_resources=100.0, current_resources=100.0, resource_per_agent_base=10.0)
    share_crowded = ecology_crowded.compute_resource_share(agent_count=50)
    share_sparse = ecology_sparse.compute_resource_share(agent_count=2)

    rs_crowded = ReproductiveSystem()
    rs_sparse = ReproductiveSystem()
    for step in range(MIN_REPRODUCTIVE_AGE + 30):
        rs_crowded.update(energy=0.8, valence=0.5, cortisol=0.1, lived_steps=step, resource_share=share_crowded)
        rs_sparse.update(energy=0.8, valence=0.5, cortisol=0.1, lived_steps=step, resource_share=share_sparse)
    assert rs_sparse.reproductive_drive > rs_crowded.reproductive_drive


def test_tc_17_population_observer_is_passive(tmp_path):
    env = _build_env()
    for i in range(5):
        env.add_agent(DummyAgent(f"a{i}"), position=Position3D(float(i + 1), 0.0, 0.0))

    observer = PopulationObserver(env)
    snapshot = observer.observe()

    assert len(env.get_all_agents()) == 5
    assert env.global_step == 0
    assert isinstance(snapshot, PopulationSnapshot)
    assert snapshot.agent_count == 5
    assert snapshot.step == 0

    out_path = tmp_path / "observer.json"
    observer.save(str(out_path))
    loaded = PopulationObserver.load(str(out_path), env)
    assert len(loaded.history) == 1
    assert loaded.history[0].agent_count == 5


def test_tc_18_reproductive_and_mortality_roundtrip():
    rs = ReproductiveSystem(
        reproductive_drive=0.65,
        cooldown_steps=30,
        total_offspring=3,
        last_reproduction_step=450,
    )
    rs_restored = ReproductiveSystem.from_dict(rs.to_dict())
    assert abs(rs_restored.reproductive_drive - 0.65) < 1e-9
    assert rs_restored.cooldown_steps == 30
    assert rs_restored.total_offspring == 3

    ms = MortalitySystem(
        vitality=0.82,
        max_lifespan_steps=8000,
        cause_of_death="",
        death_step=-1,
    )
    ms_restored = MortalitySystem.from_dict(ms.to_dict())
    assert abs(ms_restored.vitality - 0.82) < 1e-9
    assert ms_restored.max_lifespan_steps == 8000


def test_swarm_tick_updates_resources_and_mortality():
    env = _build_env(total_resources=20.0, resource_per_agent_base=10.0, resource_regen_rate=0.0)
    dying = DummyAgent("dying", energy=0.01)
    env.add_agent(dying, position=Position3D(5.0, 5.0, 0.0))

    state = env.tick()

    assert state.resource_level <= 20.0
    assert state.deaths_this_step == 1
    assert env.get_agent("dying") is None


def test_swarm_tick_reproduction_pairing_is_decentralized():
    factory = DummyFactory()
    env = _build_env(factory=factory, base_perception_radius=50.0)
    parent_a = DummyAgent("pa", lived_steps=500, valence=0.7, cortisol=0.1)
    parent_b = DummyAgent("pb", lived_steps=500, valence=0.7, cortisol=0.1)
    parent_a.reproductive_system.reproductive_drive = 0.95
    parent_b.reproductive_system.reproductive_drive = 0.95

    env.add_agent(parent_a, position=Position3D(10.0, 10.0, 0.0))
    env.add_agent(parent_b, position=Position3D(12.0, 10.0, 0.0))
    before = len(env.get_all_agents())

    env.tick()

    assert len(env.get_all_agents()) == before + 1
    assert env.total_births == 1
    assert parent_a.reproductive_system.cooldown_steps > 0
    assert parent_b.reproductive_system.cooldown_steps > 0
