import random

from agent import Agent
from agent_factory import AgentConfig, AgentFactory
from epigenome import EpigenomeSnapshot
from genome import GENE_REGISTRY, GenomeVector
from mortality import MortalitySystem
from reproduction import ReproductiveSystem


def _make_factory(actions=None) -> AgentFactory:
    return AgentFactory(
        AgentConfig(
            actions=list(actions or ["eat", "sleep", "play"]),
            hippocampus_capacity=256,
            cortex_capacity=128,
        )
    )


def _make_custom_genome(**overrides) -> GenomeVector:
    genes = {key: descriptor.default for key, descriptor in GENE_REGISTRY.items()}
    genes.update(overrides)
    return GenomeVector(genes=genes)


def _simple_epigenome(context_signature: str = "ctx", action: str = "eat") -> EpigenomeSnapshot:
    return EpigenomeSnapshot.extract(
        cortex_patterns=[
            {
                "context_signature": context_signature,
                "action": action,
                "strength": 0.9,
                "reinforcement_count": 5,
            }
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )


def test_tc_01_spawn_default_genome_creates_working_agent():
    factory = _make_factory()
    genome = GenomeVector.default()

    agent = factory.spawn(genome)

    assert hasattr(agent, "genome")
    assert hasattr(agent, "epigenome")
    assert hasattr(agent, "agent_id")
    assert agent.genome.genes == genome.genes
    assert agent.epigenome.is_empty() is True
    action = agent.step(context_events=["morning"], reward=0.0, novelty=0.0)
    assert isinstance(action, str)


def test_tc_02_genome_parameters_are_applied():
    factory = _make_factory(actions=["eat", "sleep"])
    genome = _make_custom_genome(af_decay_valence=0.85, lr_gamma=0.90)

    agent = factory.spawn(genome)

    assert abs(agent.affective_space.axis_decay.get("valence", 0.0) - 0.85) < 1e-9
    assert abs(agent.value_layer.gamma_default - 0.90) < 1e-9


def test_tc_03_spawn_random_uses_random_genome():
    factory = _make_factory()
    agent_a = factory.spawn_random(rng=random.Random(42))
    agent_b = factory.spawn_random(rng=random.Random(99))

    assert agent_a.genome.genes != agent_b.genome.genes
    assert isinstance(agent_a.step(["ctx"], reward=0.0, novelty=0.0), str)
    assert isinstance(agent_b.step(["ctx"], reward=0.0, novelty=0.0), str)


def test_tc_04_spawn_default_matches_registry_defaults():
    factory = _make_factory(actions=["eat", "sleep"])

    agent = factory.spawn_default()

    for key, descriptor in GENE_REGISTRY.items():
        assert abs(agent.genome.genes[key] - descriptor.default) < 1e-12


def test_tc_05_epigenome_injection_populates_cortex():
    factory = _make_factory()
    epigenome = _simple_epigenome(context_signature="morning", action="eat")

    agent = factory.spawn(GenomeVector.default(), epigenome=epigenome, epigenome_noise=0.0)

    signatures = [tuple(getattr(pattern, "signature", ())) for pattern in list(agent.cortex.patterns)]
    assert any("morning" in signature for signature in signatures)
    assert agent.epigenome is not None
    assert not agent.epigenome.is_empty()


def test_tc_06_spawn_child_no_mutation_stays_between_parents():
    factory = _make_factory(actions=["eat", "sleep"])
    parent_a = factory.spawn_random(rng=random.Random(1))
    parent_b = factory.spawn_random(rng=random.Random(2))

    child = factory.spawn_child(
        parent_a,
        parent_b,
        mutation_rate=0.0,
        crossover_alpha=0.5,
        crossover_mode="arithmetic",
        blend_epigenomes=False,
        rng=random.Random(42),
    )

    assert child.genome.generation == max(parent_a.genome.generation, parent_b.genome.generation) + 1
    for key in GENE_REGISTRY:
        value_a = parent_a.genome.genes[key]
        value_b = parent_b.genome.genes[key]
        value_child = child.genome.genes[key]
        lower, upper = min(value_a, value_b), max(value_a, value_b)
        assert lower - 1e-12 <= value_child <= upper + 1e-12


def test_tc_07_spawn_child_mutation_changes_genes():
    factory = _make_factory(actions=["eat", "sleep"])
    parent_a = factory.spawn_default()
    parent_b = factory.spawn_default()

    child = factory.spawn_child(
        parent_a,
        parent_b,
        mutation_rate=1.0,
        sigma_scale=2.0,
        blend_epigenomes=False,
        rng=random.Random(7),
    )

    assert any(
        abs(child.genome.genes[key] - parent_a.genome.genes[key]) > 1e-9
        for key in GENE_REGISTRY
    )


def test_tc_08_extract_genome_returns_valid_vector():
    factory = _make_factory(actions=["eat", "sleep"])
    original_genome = GenomeVector.random(random.Random(5))
    agent = factory.spawn(original_genome)

    extracted = factory.extract_genome(agent)

    assert isinstance(extracted, GenomeVector)
    assert extracted.validate() == []
    assert abs(extracted.genes["lr_gamma"] - original_genome.genes["lr_gamma"]) < 1e-9
    assert abs(extracted.genes["af_decay_valence"] - original_genome.genes["af_decay_valence"]) < 1e-9


def test_tc_09_extract_epigenome_after_steps_returns_valid_snapshot():
    factory = _make_factory()
    agent = factory.spawn_default()
    for _ in range(10):
        agent.step(["morning", "hungry"], reward=0.8, novelty=0.3)
    agent.sleep(cycles=1)

    epigenome = factory.extract_epigenome(
        agent,
        min_reinforcement=0,
        min_stability=0.0,
        min_confirmation=0.0,
    )

    assert isinstance(epigenome, EpigenomeSnapshot)
    assert epigenome.validate() == []
    assert epigenome.source_generation >= 0


def test_tc_10_spawn_child_blends_parent_epigenomes():
    factory = _make_factory(actions=["eat", "sleep"])
    parent_a = factory.spawn_default()
    parent_b = factory.spawn_default()
    parent_a.epigenome = _simple_epigenome(context_signature="ctx_a", action="eat")
    parent_b.epigenome = _simple_epigenome(context_signature="ctx_b", action="sleep")

    child = factory.spawn_child(
        parent_a,
        parent_b,
        blend_epigenomes=True,
        epigenome_noise=0.0,
        rng=random.Random(0),
    )

    assert child.epigenome is not None
    assert not child.epigenome.is_empty()
    assert isinstance(child.step(["ctx_a"], reward=0.0, novelty=0.0), str)


def test_tc_11_factory_has_no_cross_spawn_shared_state():
    factory = _make_factory(actions=["eat", "sleep"])
    agent_1 = factory.spawn(GenomeVector.default(), agent_id="agent_1")
    agent_2 = factory.spawn(GenomeVector.default(), agent_id="agent_2")

    assert agent_1.agent_id == "agent_1"
    assert agent_2.agent_id == "agent_2"
    assert agent_1 is not agent_2
    assert agent_1.hippocampus is not agent_2.hippocampus


def test_tc_12_agent_id_is_persisted():
    factory = _make_factory(actions=["eat"])
    agent = factory.spawn(GenomeVector.default(), agent_id="test_agent_42")

    assert agent.agent_id == "test_agent_42"
    assert agent.lineage_id == "test_agent_42"


def test_tc_13_spawn_with_invalid_epigenome_does_not_crash():
    factory = _make_factory(actions=["eat", "sleep"])
    agent = factory.spawn(
        GenomeVector.default(),
        epigenome=object(),
        epigenome_noise=0.5,
    )

    assert agent is not None
    assert isinstance(agent.epigenome, EpigenomeSnapshot)


def test_tc_14_spawn_child_without_parent_genome_uses_defaults():
    factory = _make_factory(actions=["eat", "sleep"])
    parent_a = factory.spawn_default()
    parent_b = factory.spawn_default()
    del parent_a.genome
    del parent_b.genome

    child = factory.spawn_child(parent_a, parent_b, rng=random.Random(0))

    assert isinstance(child, Agent)
    assert isinstance(child.genome, GenomeVector)
    assert child.genome.validate() == []


def test_tc_15_all_actions_are_registered_in_bg_channels():
    actions = ["eat", "sleep", "play", "explore"]
    factory = _make_factory(actions=actions)
    agent = factory.spawn_default()

    for action in actions:
        assert action in agent.bg_action_channels


def test_tc_16_spawn_child_is_deterministic_for_fixed_rng():
    factory = _make_factory(actions=["eat", "sleep"])
    parent_a = factory.spawn(GenomeVector.random(random.Random(1)))
    parent_b = factory.spawn(GenomeVector.random(random.Random(2)))

    child_1 = factory.spawn_child(
        parent_a,
        parent_b,
        mutation_rate=0.3,
        blend_epigenomes=False,
        rng=random.Random(42),
    )
    child_2 = factory.spawn_child(
        parent_a,
        parent_b,
        mutation_rate=0.3,
        blend_epigenomes=False,
        rng=random.Random(42),
    )

    assert child_1.genome.genes == child_2.genome.genes


def test_tc_17_neuromodulator_matrix_roundtrip_is_consistent():
    factory = _make_factory(actions=["eat", "sleep"])
    genome = _make_custom_genome(
        nm_da_ne_weight=-0.35,
        nm_ne_da_weight=0.31,
        nm_da_ach_weight=-0.44,
        nm_ach_da_weight=-0.22,
    )
    agent = factory.spawn(genome)

    # Force reconstruction path instead of returning stored agent.genome.
    del agent.genome
    reconstructed = factory.extract_genome(agent)

    assert abs(reconstructed.genes["nm_da_ne_weight"] - genome.genes["nm_da_ne_weight"]) < 1e-9
    assert abs(reconstructed.genes["nm_ne_da_weight"] - genome.genes["nm_ne_da_weight"]) < 1e-9
    assert abs(reconstructed.genes["nm_da_ach_weight"] - genome.genes["nm_da_ach_weight"]) < 1e-9
    assert abs(reconstructed.genes["nm_ach_da_weight"] - genome.genes["nm_ach_da_weight"]) < 1e-9


def test_spawn_attaches_reproduction_and_mortality_systems():
    factory = _make_factory(actions=["eat", "sleep"])
    agent = factory.spawn(GenomeVector.default())

    assert isinstance(agent.reproductive_system, ReproductiveSystem)
    assert isinstance(agent.mortality_system, MortalitySystem)
    assert agent.mortality_system.max_lifespan_steps == factory.config.base_lifespan_steps


def test_spawn_uses_lifespan_factor_from_genome():
    factory = AgentFactory(
        AgentConfig(
            actions=["eat", "sleep"],
            base_lifespan_steps=4000,
        )
    )
    genome = _make_custom_genome(lt_max_lifespan_factor=1.5)
    agent = factory.spawn(genome)

    assert agent.mortality_system.max_lifespan_steps == 6000
    assert agent.expected_lifetime_steps == 6000
