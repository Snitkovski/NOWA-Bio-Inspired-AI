from __future__ import annotations

import json
import os
import random

import pytest

from colony_agent import ChinchillaAgent
from colony_gui import (
    AgentInspectorOverlay,
    ColonyGUI,
    GENERATION_ROW_H,
    LineageOverlay,
    build_inspector_data_from_agent,
    build_inspector_data_from_memorial,
)
from death_registry import DeathRegistry, LineageNode
from simulation_runner import SimulationRunner


@pytest.fixture(autouse=True)
def _russian_ui():
    from colony_gui.i18n import reset_language, set_language

    set_language("ru")
    yield
    reset_language()


def test_tc_death_registry_01_register_birth_and_death() -> None:
    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="F", generation=0)
    registry.register_birth(agent, sim_time=10.0)

    assert registry.get_birth_time(agent.agent_id) == 10.0
    assert not registry.is_deceased(agent.agent_id)

    memorial = registry.register_death(agent, sim_time=500.0, generation_index_map={})
    assert registry.is_deceased(agent.agent_id)
    assert memorial.death_sim_time == 500.0
    assert memorial.birth_sim_time == 10.0


def test_tc_death_registry_02_stores_full_genome() -> None:
    from genome import GenomeVector

    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="M")
    agent.genome = GenomeVector.default()
    registry.register_birth(agent, 0.0)
    memorial = registry.register_death(agent, 100.0, {})

    expected_keys = set(GenomeVector.default().genes.keys())
    assert set(memorial.genome_genes.keys()) == expected_keys
    for key in expected_keys:
        assert abs(memorial.genome_genes[key] - agent.genome.genes[key]) < 1e-9


def test_tc_death_registry_03_affective_snapshot() -> None:
    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="F")
    agent.affective_space.axes["stress"] = 0.75
    agent.affective_space.axes["valence"] = -0.30
    agent.affective_space.axes["curiosity"] = 0.60
    registry.register_birth(agent, 0.0)
    memorial = registry.register_death(agent, 50.0, {})

    assert abs(memorial.final_stress - 0.75) < 1e-6
    assert abs(memorial.final_valence - (-0.30)) < 1e-6
    assert abs(memorial.final_curiosity - 0.60) < 1e-6


def test_tc_death_registry_04_social_footprint() -> None:
    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="M")
    other = ChinchillaAgent(sex="F")

    agent._ensure_known(other.agent_id, other.get_public_state())
    known = agent.knowledge[other.agent_id]
    known.affinity = 0.8
    known.relationship_type = "bonded"
    known.positive_count = 10
    known.negative_count = 2

    registry.register_birth(agent, 0.0)
    memorial = registry.register_death(agent, 100.0, {})

    assert memorial.known_agents_count == 1
    assert memorial.bonded_count == 1
    assert memorial.positive_interactions == 10
    assert memorial.negative_interactions == 2


def test_tc_death_registry_05_save_load_roundtrip(tmp_path) -> None:
    from genome import GenomeVector

    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="F")
    agent.genome = GenomeVector.random(random.Random(42))
    registry.register_birth(agent, 0.0)
    registry.register_death(agent, 200.0, {})

    path = tmp_path / "registry.json"
    registry.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == "1.1"
    assert len(data["memorials"]) == 1
    assert len(data["memorials"][0]["genome_genes"]) == len(agent.genome.genes)

    registry2 = DeathRegistry()
    registry2.load(path)
    loaded = registry2.get_memorial(agent.agent_id)
    assert loaded is not None
    for key in agent.genome.genes:
        assert abs(loaded.genome_genes[key] - agent.genome.genes[key]) < 1e-9


def test_tc_death_registry_06_load_adds_without_overwrite(tmp_path) -> None:
    registry = DeathRegistry()
    a1 = ChinchillaAgent(sex="F")
    registry.register_birth(a1, 0.0)
    registry.register_death(a1, 100.0, {})

    path = tmp_path / "registry.json"
    registry.save(path)

    a2 = ChinchillaAgent(sex="M")
    registry.register_birth(a2, 50.0)
    registry.register_death(a2, 200.0, {})
    registry.load(path)

    assert len(registry._memorials) == 2


def test_tc_death_registry_07_lineage_nodes_include_living_and_dead() -> None:
    registry = DeathRegistry()
    dead = ChinchillaAgent(sex="F", generation=0)
    registry.register_birth(dead, 0.0)
    registry.register_death(dead, 100.0, {})
    living = ChinchillaAgent(sex="M", generation=0)

    nodes = registry.get_lineage_nodes([living], generation_index_map={})
    ids = {node.agent_id for node in nodes}
    assert dead.agent_id in ids
    assert living.agent_id in ids
    dead_node = next(node for node in nodes if node.agent_id == dead.agent_id)
    assert dead_node.is_alive is False


def test_tc_death_registry_08_register_death_on_minimal_agent() -> None:
    class Minimal:
        agent_id = "x"
        sex = "F"
        generation = 0
        parents = (None, None)
        name = "Test"
        age = 50.0
        lived_steps = 100
        own_offspring = []
        knowledge = {}

    registry = DeathRegistry()
    registry.register_birth(Minimal(), 0.0)
    memorial = registry.register_death(Minimal(), 50.0, {})
    assert memorial.agent_id == "x"
    assert memorial.final_stress == 0.0
    assert memorial.genome_genes == {}


def test_tc_death_registry_09_max_memorials_limit(monkeypatch) -> None:
    import death_registry as registry_module

    monkeypatch.setattr(registry_module, "MAX_MEMORIALS_IN_MEMORY", 12)
    registry = DeathRegistry()
    for idx in range(20):
        agent = ChinchillaAgent(sex="F" if idx % 2 == 0 else "M")
        registry.register_birth(agent, float(idx))
        registry.register_death(agent, float(idx) + 0.5, {})
    assert len(registry._memorials) == 12


def test_tc_death_registry_10_build_inspector_data_from_agent() -> None:
    from genome import GenomeVector

    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F", generation=1)
    agent.genome = GenomeVector.default()
    runner.add_agent(agent)
    data = build_inspector_data_from_agent(agent, "G1A1")

    assert data.agent_id == agent.agent_id
    assert data.is_deceased is False
    assert "stress" in data.affective_axes
    assert "dopamine" in data.neuromodulators
    assert "wakefulness" in data.wakefulness
    assert "curiosity" in data.autonomous_drives
    assert "hippocampus_size" in data.memory
    assert isinstance(data.genome_genes, dict)


def test_tc_death_registry_10b_build_inspector_data_contains_memory_details() -> None:
    from experience import Event, EventType, Path

    agent = ChinchillaAgent(sex="F", generation=1)
    path = Path().add_event(Event("context:food", EventType.CONTEXT)).add_event(Event("action:eat", EventType.ACTION))
    consequence = Event("feedback:+0.20", EventType.CONSEQUENCE)
    agent.hippocampus.store(path, consequence=consequence, intensity=0.7, reward=0.3, encoding_strength=0.9)
    agent.cortex.store_pattern(("context:food", "action:eat", "consequence:feedback:+0.20"), source_experiences=3)

    data = build_inspector_data_from_agent(agent, "G1A1SF")

    assert data.memory["hippocampus_size"] >= 1
    assert data.memory["cortex_patterns"] >= 1
    assert data.hippocampus_episodes
    assert data.cortex_patterns_detail
    episode = data.hippocampus_episodes[-1]
    assert episode["action"] == "eat"
    assert "context:food" in episode["context_tokens"]
    pattern = data.cortex_patterns_detail[-1]
    assert pattern["action"] == "eat"
    assert "context:food" in pattern["context_tokens"]


def test_tc_death_registry_10c_memory_details_are_human_readable() -> None:
    from experience import Event, EventType, Path

    agent = ChinchillaAgent(sex="F", generation=0)
    path = (
        Path()
        .add_event(Event("zone:waterer", EventType.CONTEXT))
        .add_event(Event("food_low", EventType.CONTEXT))
        .add_event(Event("action:drink", EventType.ACTION))
    )
    consequence = Event("feedback:+0.20", EventType.CONSEQUENCE)
    agent.hippocampus.store(path, consequence=consequence, intensity=0.6, reward=0.2)
    agent.cortex.store_pattern(
        ("zone:waterer", "food_low", "action:drink", "consequence:feedback:+0.20"),
        source_experiences=2,
    )

    data = build_inspector_data_from_agent(agent, "G0A1SF")
    inspector = AgentInspectorOverlay()
    inspector.open(data)

    inspector._open_memory_detail("hippocampus_size")
    hippocampus_text = " ".join(inspector._memory_detail_lines)
    assert "зона: поилка" in hippocampus_text
    assert "мало еды" in hippocampus_text
    assert "пьёт" in hippocampus_text
    assert "обратная связь +0.20" in hippocampus_text

    inspector._open_memory_detail("cortex_patterns")
    cortex_text = " ".join(inspector._memory_detail_lines)
    assert "действие: пьёт" in cortex_text
    assert "зона: поилка" in cortex_text


def test_tc_death_registry_10d_genome_lineage_rows_follow_generations_for_live_agent() -> None:
    from genome import GenomeVector

    g0_mother = ChinchillaAgent(sex="F", generation=0)
    g0_father = ChinchillaAgent(sex="M", generation=0)
    g1_mother = ChinchillaAgent(sex="F", generation=1, parents=(g0_mother.agent_id, g0_father.agent_id))
    g1_father = ChinchillaAgent(sex="M", generation=1, parents=(g0_mother.agent_id, g0_father.agent_id))
    child = ChinchillaAgent(sex="M", generation=2, parents=(g1_mother.agent_id, g1_father.agent_id))

    colony = [g0_mother, g0_father, g1_mother, g1_father, child]
    for member in colony:
        member.colony = colony

    child.genome = GenomeVector(
        genes=dict(GenomeVector.default().genes),
        generation=2,
        lineage_id="g0a1sfxg0a2smxg0a1sfxg0a2sm",
    )

    data = build_inspector_data_from_agent(child, child.name)
    assert data.genome_lineage_rows
    assert data.genome_lineage_rows[0].startswith("G1")
    assert any(row.startswith("G0") for row in data.genome_lineage_rows[1:])


def test_tc_death_registry_10e_genome_lineage_truncated_tail_is_hidden() -> None:
    from genome import GenomeVector

    agent = ChinchillaAgent(sex="F", generation=0)
    raw_lineage = ("x".join(["g0a1sf"] * 9)) + "xg"
    assert len(raw_lineage) >= 64
    agent.genome = GenomeVector(
        genes=dict(GenomeVector.default().genes),
        generation=0,
        lineage_id=raw_lineage,
    )

    data = build_inspector_data_from_agent(agent, agent.name)
    assert data.genome_lineage_rows
    assert all(row != "G" for row in data.genome_lineage_rows)
    assert all(len(row) >= 3 for row in data.genome_lineage_rows)


def test_tc_death_registry_11_build_inspector_data_from_memorial() -> None:
    from genome import GenomeVector

    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="M")
    agent.genome = GenomeVector.default()
    registry.register_birth(agent, 0.0)
    memorial = registry.register_death(agent, 100.0, {})

    data = build_inspector_data_from_memorial(memorial, "G0A1")
    assert data.is_deceased is True
    assert data.cause_of_death == memorial.cause_of_death
    assert data.genome_genes == memorial.genome_genes


def test_tc_death_registry_12_inspector_open_close() -> None:
    inspector = AgentInspectorOverlay()
    assert inspector.visible is False
    assert inspector.agent_id == ""

    agent = ChinchillaAgent(sex="F")
    data = build_inspector_data_from_agent(agent, "G0A1")
    inspector.open(data)
    assert inspector.visible is True
    assert inspector.agent_id == agent.agent_id
    inspector.close()
    assert inspector.visible is False


def test_tc_death_registry_13_inspector_esc_closes() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")

    pygame.init()
    inspector = AgentInspectorOverlay()
    agent = ChinchillaAgent(sex="M")
    inspector.open(build_inspector_data_from_agent(agent, "G0A2"))
    esc_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""})
    consumed = inspector.handle_event(esc_event)
    assert consumed is True
    assert inspector.visible is False
    pygame.quit()


def test_tc_death_registry_13b_inspector_memory_link_opens_detail_window() -> None:
    from experience import Event, EventType, Path

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")

    pygame.init()
    screen = pygame.display.set_mode((1024, 768))
    font = pygame.font.Font(None, 28)
    font_small = pygame.font.Font(None, 22)
    font_mono = pygame.font.Font(None, 20)

    agent = ChinchillaAgent(sex="F")
    path = Path().add_event(Event("context:food", EventType.CONTEXT)).add_event(Event("action:eat", EventType.ACTION))
    agent.hippocampus.store(path, consequence=Event("feedback:+0.10", EventType.CONSEQUENCE), intensity=0.5, reward=0.1)
    inspector = AgentInspectorOverlay()
    inspector.open(build_inspector_data_from_agent(agent, "G0A1SF"))
    inspector.draw(screen, font, font_small, font_mono)

    link_rect = inspector._memory_link_screen_rects.get("hippocampus_size")
    if link_rect is None:
        # Default-font metrics can push the link below the first viewport.
        local = inspector._memory_link_local_rects.get("hippocampus_size")
        assert local is not None
        inspector._scroll = max(0, int(local.y) - 8)
        inspector.draw(screen, font, font_small, font_mono)
        link_rect = inspector._memory_link_screen_rects.get("hippocampus_size")
    assert link_rect is not None

    click_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": link_rect.center},
    )
    consumed = inspector.handle_event(click_event)
    assert consumed is True
    assert inspector._memory_detail_visible is True
    assert inspector._memory_detail_kind == "hippocampus_size"

    esc_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""})
    consumed = inspector.handle_event(esc_event)
    assert consumed is True
    assert inspector._memory_detail_visible is False
    assert inspector.visible is True

    consumed = inspector.handle_event(esc_event)
    assert consumed is True
    assert inspector.visible is False
    pygame.quit()


def test_tc_death_registry_14_lineage_rebuild_positions() -> None:
    runner = SimulationRunner()
    for idx in range(4):
        runner.add_agent(ChinchillaAgent(sex="F" if idx % 2 == 0 else "M", generation=0))
    lineage = LineageOverlay(runner.death_registry)
    lineage.rebuild(runner.agents, {})

    assert len(lineage._nodes) == 4
    positions = {(node.tree_x, node.tree_y) for node in lineage._nodes}
    assert len(positions) == 4
    for node in lineage._nodes:
        assert node.tree_y == 0.0
        assert node.tree_x >= 0.0


def test_tc_death_registry_15_lineage_two_generations() -> None:
    runner = SimulationRunner()
    parent = ChinchillaAgent(sex="F", generation=0)
    child = ChinchillaAgent(sex="M", generation=1)
    child.parents = (parent.agent_id, None)
    runner.add_agent(parent)
    runner.add_agent(child)

    lineage = LineageOverlay(runner.death_registry)
    lineage.rebuild(runner.agents, {})

    by_generation: dict[int, list[Any]] = {}
    for node in lineage._nodes:
        by_generation.setdefault(node.generation, []).append(node)
    assert 0 in by_generation
    assert 1 in by_generation
    y0 = by_generation[0][0].tree_y
    y1 = by_generation[1][0].tree_y
    assert abs(y1 - y0 - GENERATION_ROW_H) < 1e-6


def test_tc_death_registry_15b_lineage_parent_links_skip_non_adjacent_generation() -> None:
    lineage = LineageOverlay(DeathRegistry())
    parent_g0 = LineageNode(
        agent_id="g0_parent",
        display_name="G0A1SF",
        sex="F",
        generation=0,
        parents=(None, None),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=10.0,
        total_offspring=0,
        generation_index=1,
    )
    parent_g1 = LineageNode(
        agent_id="g1_parent",
        display_name="G1A1SM",
        sex="M",
        generation=1,
        parents=(None, None),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=6.0,
        total_offspring=0,
        generation_index=1,
    )
    child_g2 = LineageNode(
        agent_id="g2_child",
        display_name="G2A1SF",
        sex="F",
        generation=2,
        parents=(parent_g1.agent_id, parent_g0.agent_id),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=1.0,
        total_offspring=0,
        generation_index=1,
    )
    lineage._nodes = [parent_g0, parent_g1, child_g2]
    nodes_by_id = {node.agent_id: node for node in lineage._nodes}
    assert lineage._valid_parent_ids(child_g2, nodes_by_id) == [parent_g1.agent_id]
    assert lineage._collect_parent_edges(nodes_by_id) == []


def test_tc_death_registry_15c_lineage_two_parents_create_two_edges() -> None:
    lineage = LineageOverlay(DeathRegistry())
    mother = LineageNode(
        agent_id="mother",
        display_name="G1A1SF",
        sex="F",
        generation=1,
        parents=(None, None),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=6.0,
        total_offspring=0,
        generation_index=1,
    )
    father = LineageNode(
        agent_id="father",
        display_name="G1A2SM",
        sex="M",
        generation=1,
        parents=(None, None),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=6.0,
        total_offspring=0,
        generation_index=2,
    )
    child = LineageNode(
        agent_id="child",
        display_name="G2A1SF",
        sex="F",
        generation=2,
        parents=(mother.agent_id, father.agent_id),
        own_offspring=[],
        is_alive=True,
        cause_of_death="",
        age=1.0,
        total_offspring=0,
        generation_index=1,
    )
    lineage._nodes = [mother, father, child]
    nodes_by_id = {node.agent_id: node for node in lineage._nodes}
    assert lineage._valid_parent_ids(child, nodes_by_id) == [mother.agent_id, father.agent_id]
    assert lineage._collect_parent_edges(nodes_by_id) == [
        (mother.agent_id, child.agent_id),
        (father.agent_id, child.agent_id),
    ]


def test_tc_death_registry_16_colony_gui_open_inspector_for_live_and_dead() -> None:
    runner = SimulationRunner()
    living = ChinchillaAgent(sex="F")
    runner.add_agent(living)
    dead = ChinchillaAgent(sex="M")
    runner.add_agent(dead)
    runner._handle_agent_death(dead.agent_id)

    gui = ColonyGUI(runner)
    gui._update_snapshot()

    gui.open_inspector(living.agent_id)
    assert gui.inspector.visible is True
    assert gui.inspector._data is not None
    assert gui.inspector._data.is_deceased is False

    gui.inspector.close()
    gui.open_inspector(dead.agent_id)
    assert gui.inspector.visible is True
    assert gui.inspector._data is not None
    assert gui.inspector._data.is_deceased is True
