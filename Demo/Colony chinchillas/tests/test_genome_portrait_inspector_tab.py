from __future__ import annotations

import os

import pytest

from colony_agent import ChinchillaAgent
from colony_gui import AgentInspectorOverlay, InspectorData, build_inspector_data_from_agent, build_inspector_data_from_memorial
from colony_gui.genome_portrait import (
    LineageTrendPoint,
    analyze_trend,
    build_lineage_trend,
    build_portrait,
    describe_lineage_trend,
    wrap_text,
)
from death_registry import DeathRegistry
from genome import GenomeVector


def _default_genes() -> dict[str, float]:
    return dict(GenomeVector.default().genes)


def test_build_portrait_from_default_genome() -> None:
    portrait = build_portrait(_default_genes(), {})

    assert portrait is not None
    assert len(portrait.trait_scores) == 5
    for category in ["temperament", "social", "endurance", "cognition", "lifespan"]:
        assert category in portrait.trait_scores
        assert portrait.trait_scores[category].category == category
        assert 0.0 <= portrait.trait_scores[category].score <= 1.0
    assert len(portrait.summary) > 10


def test_high_lifespan_gene_becomes_strength() -> None:
    genes = _default_genes()
    genes["lt_max_lifespan_factor"] = 1.45

    portrait = build_portrait(genes, {})

    assert portrait.trait_scores["lifespan"].score > 0.7
    assert any("долгожит" in item.lower() for item in portrait.strengths)


def test_high_stress_decay_becomes_temperament_weakness() -> None:
    genes = _default_genes()
    genes["af_decay_stress"] = 0.87

    portrait = build_portrait(genes, {})

    assert portrait.trait_scores["temperament"].score < 0.4
    assert any("стресс" in item.lower() for item in portrait.weaknesses)


def test_major_mutation_effect_is_described() -> None:
    genes = _default_genes()
    parent_genes = _default_genes()
    parent_genes["wk_recovery_factor"] = 0.85
    genes["wk_recovery_factor"] = 0.58

    portrait = build_portrait(
        genes,
        {
            "parent_midpoint_genes": parent_genes,
            "top_shifted_genes": [{"key": "wk_recovery_factor", "delta": -0.27}],
        },
    )

    mutation = next((item for item in portrait.mutations if item.gene_key == "wk_recovery_factor"), None)
    assert mutation is not None
    assert mutation.magnitude == "major"
    assert mutation.valence == "negative"
    assert mutation.direction == "down"
    assert "восстанавл" in mutation.consequence_short.lower()


def test_build_portrait_never_fails_on_empty_genome() -> None:
    portrait = build_portrait({}, {})

    assert portrait is not None
    assert portrait.summary != ""
    assert portrait.mutations == []


def test_build_lineage_trend_returns_none_without_registry_ancestors() -> None:
    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="F", generation=0)
    agent.parents = (None, None)

    assert build_lineage_trend(agent, registry, {}) is None


def test_build_lineage_trend_includes_registered_parent_and_current_agent() -> None:
    registry = DeathRegistry()
    mother = ChinchillaAgent(sex="F", generation=0, genome=GenomeVector.default(), name="G0A1SF")
    registry.register_birth(mother, 0.0)
    registry.register_death(mother, 1000.0, {})

    child = ChinchillaAgent(
        sex="M",
        generation=1,
        parents=(mother.agent_id, None),
        genome=GenomeVector.default(),
        name="G1A1SM",
    )

    result = build_lineage_trend(child, registry, {})

    assert result is not None
    assert len(result) >= 2
    assert result[0].agent_id == mother.agent_id
    assert result[-1].agent_id == child.agent_id


def test_analyze_trend_detects_direction_by_first_and_last_thirds() -> None:
    points_down = [
        LineageTrendPoint("a1", "G0A1", 0, {"af_decay_stress": 0.85}, 0.94, 1.0, 18000),
        LineageTrendPoint("a2", "G1A1", 1, {"af_decay_stress": 0.80}, 0.88, 0.95, 18200),
        LineageTrendPoint("a3", "G2A1", 2, {"af_decay_stress": 0.73}, 0.81, 0.82, 18400),
    ]
    points_up = [
        LineageTrendPoint("b1", "G0A2", 0, {"lt_max_lifespan_factor": 1.00}, 0.92, 1.0, 18000),
        LineageTrendPoint("b2", "G1A2", 1, {"lt_max_lifespan_factor": 1.10}, 0.87, 0.92, 18500),
        LineageTrendPoint("b3", "G2A2", 2, {"lt_max_lifespan_factor": 1.23}, 0.81, 0.85, 19000),
    ]

    assert "↘" in analyze_trend(points_down, "af_decay_stress")
    assert "↗" in analyze_trend(points_up, "lt_max_lifespan_factor")


def test_describe_lineage_trend_is_human_readable() -> None:
    points = [
        LineageTrendPoint("b1", "G0A2", 0, {"lt_max_lifespan_factor": 1.00}, 0.92, 1.0, 18000),
        LineageTrendPoint("b2", "G1A2", 1, {"lt_max_lifespan_factor": 1.10}, 0.87, 0.92, 18500),
        LineageTrendPoint("b3", "G2A2", 2, {"lt_max_lifespan_factor": 1.23}, 0.81, 0.85, 19000),
    ]

    description = describe_lineage_trend(points, "lt_max_lifespan_factor")

    assert "раст" in description.lower()
    assert "жизни" in description.lower()


def test_wrap_text_limits_to_eight_lines_and_marks_truncation() -> None:
    lines = wrap_text(" ".join(f"word{i}" for i in range(40)), max_chars=10)

    assert len(lines) <= 8
    assert lines[-1].endswith("...")


def test_genome_tab_portrait_draws_without_errors() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")

    pygame.init()
    screen = pygame.Surface((500, 700), pygame.SRCALPHA)
    font = pygame.font.SysFont("Arial", 16)
    font_small = pygame.font.SysFont("Arial", 12)
    font_mono = pygame.font.SysFont("Courier New", 12)

    genes = _default_genes()
    genes["lt_max_lifespan_factor"] = 1.3
    genes["af_decay_stress"] = 0.62
    portrait = build_portrait(genes, {})
    data = InspectorData(
        agent_id="test",
        display_name="G2A5SM",
        is_deceased=False,
        sex="M",
        generation=2,
        parents=(None, None),
        age=5000.0,
        lived_steps=5000,
        cause_of_death="",
        genome_portrait=portrait,
        genome_genes=genes,
    )
    overlay = AgentInspectorOverlay()
    overlay.open(data)
    overlay._active_tab = 3

    overlay.draw(screen, font, font_small, font_mono)


def test_lineage_trend_draws_death_metrics_only_for_deceased_agents() -> None:
    class FontStub:
        def render(self, text: str, _antialias: bool, _color: object) -> str:
            return text

    class SurfaceStub:
        def __init__(self) -> None:
            self.texts: list[str] = []

        def blit(self, rendered: str, _pos: tuple[int, int]) -> None:
            self.texts.append(rendered)

    trend = [
        LineageTrendPoint(
            "a1",
            "G0A1",
            0,
            {"lt_max_lifespan_factor": 1.0, "af_decay_stress": 0.85},
            0.70,
            0.90,
            1000,
        ),
        LineageTrendPoint(
            "a2",
            "G1A1",
            1,
            {"lt_max_lifespan_factor": 1.2, "af_decay_stress": 0.75},
            0.80,
            1.00,
            1200,
        ),
    ]

    live_overlay = AgentInspectorOverlay()
    live_overlay._data = InspectorData(
        agent_id="live",
        display_name="G1A1SM",
        is_deceased=False,
        sex="M",
        generation=1,
        parents=(None, None),
        age=1.0,
        lived_steps=1,
        cause_of_death="",
    )
    live_surface = SurfaceStub()
    live_overlay._draw_lineage_trend(live_surface, FontStub(), FontStub(), 0, trend)
    live_text = " ".join(live_surface.texts)

    dead_overlay = AgentInspectorOverlay()
    dead_overlay._data = InspectorData(
        agent_id="dead",
        display_name="G1A1SM",
        is_deceased=True,
        sex="M",
        generation=1,
        parents=(None, None),
        age=1.0,
        lived_steps=1,
        cause_of_death="old_age",
    )
    dead_surface = SurfaceStub()
    dead_overlay._draw_lineage_trend(dead_surface, FontStub(), FontStub(), 0, trend)
    dead_text = " ".join(dead_surface.texts)

    assert "lt_max_lifespan_factor" not in live_text
    assert "Долгожитие" in live_text
    assert "при смерти" not in live_text
    assert "Стресс при смерти" in dead_text
    assert "Кортизол при смерти" in dead_text


def test_genome_table_is_collapsed_by_default_and_resets_on_tab_change() -> None:
    data = InspectorData(
        agent_id="test",
        display_name="G0A1SF",
        is_deceased=False,
        sex="F",
        generation=0,
        parents=(None, None),
        age=0.0,
        lived_steps=0,
        cause_of_death="",
        genome_genes=_default_genes(),
        genome_portrait=build_portrait(_default_genes(), {}),
    )
    overlay = AgentInspectorOverlay()
    overlay.open(data)
    overlay._active_tab = 3

    assert overlay._genome_table_expanded is False
    overlay._genome_table_expanded = True
    assert overlay._genome_table_expanded is True
    overlay._active_tab = 0
    overlay._active_tab = 3
    assert overlay._genome_table_expanded is False


def test_inspector_builders_attach_portrait_and_lineage_trend() -> None:
    registry = DeathRegistry()
    mother = ChinchillaAgent(sex="F", generation=0, genome=GenomeVector.default(), name="G0A1SF")
    registry.register_birth(mother, 0.0)
    memorial = registry.register_death(mother, 100.0, {})
    child = ChinchillaAgent(
        sex="M",
        generation=1,
        parents=(mother.agent_id, None),
        genome=GenomeVector.default(),
        name="G1A1SM",
    )

    live_data = build_inspector_data_from_agent(child, child.name, death_registry=registry, generation_index_map={})
    memorial_data = build_inspector_data_from_memorial(memorial, memorial.name, death_registry=registry)

    assert live_data.genome_portrait is not None
    assert live_data.genome_portrait.lineage_trend is not None
    assert memorial_data.genome_portrait is not None
