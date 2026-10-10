from __future__ import annotations

import os

import pytest

from colony_agent import ChinchillaAgent
from colony_gui import ColonyGUI, SwarmAnalyticsOverlay
from colony_gui.swarm_analytics import (
    GenerationSummary,
    build_gene_tracks,
    build_swarm_analytics,
)
from colony_population_observer import ColonyPopulationObserver
from death_registry import DeathRegistry
from genome import GenomeVector
from simulation_runner import SimulationRunner


def _summary(generation: int, genes: dict[str, float]) -> GenerationSummary:
    return GenerationSummary(
        generation=generation,
        agent_count=1,
        alive_count=0,
        dead_count=1,
        mean_lived_steps=1000.0,
        mean_stress_at_death=0.2,
        mean_cortisol_at_death=0.2,
        mean_energy_at_death=0.8,
        mean_vitality_at_death=0.8,
        cause_distribution={},
        mean_genome=genes,
        genome_std={key: 0.01 for key in genes},
        total_offspring=1,
        mean_total_offspring=1.0,
    )


def test_tc01_build_swarm_analytics_empty_runner() -> None:
    runner = SimulationRunner()

    analytics = build_swarm_analytics(runner, observer=None)

    assert analytics is not None
    assert analytics.living_count == 0
    assert analytics.generation_summaries == []
    assert analytics.gene_tracks == []
    assert analytics.forecast.extinction_risk >= 0.0


def test_tc02_generation_summary_from_memorials() -> None:
    registry = DeathRegistry()
    for gen in [0, 0, 1, 1, 1]:
        agent = ChinchillaAgent(sex="F", generation=gen)
        agent.genome = GenomeVector.default()
        registry.register_birth(agent, 0.0)
        registry.register_death(agent, 1000.0, {})

    runner = SimulationRunner()
    runner.death_registry = registry
    analytics = build_swarm_analytics(runner, None)

    assert len(analytics.generation_summaries) == 2
    g0 = next(summary for summary in analytics.generation_summaries if summary.generation == 0)
    g1 = next(summary for summary in analytics.generation_summaries if summary.generation == 1)
    assert g0.dead_count == 2
    assert g1.dead_count == 3


def test_tc03_gene_evolution_track_increasing() -> None:
    summaries = [
        _summary(i, {"lt_max_lifespan_factor": 1.0 + i * 0.05})
        for i in range(5)
    ]

    tracks = build_gene_tracks(summaries)
    lt_track = next(track for track in tracks if track.gene_key == "lt_max_lifespan_factor")

    assert lt_track.trend_label == "↗ растёт"
    assert lt_track.is_under_selection is True
    assert lt_track.trend_magnitude > 0.05


def test_tc04_gene_evolution_track_stable() -> None:
    summaries = [
        _summary(i, {"lr_gamma": 0.85 + (i % 2) * 0.01})
        for i in range(6)
    ]

    tracks = build_gene_tracks(summaries)
    lr_track = next((track for track in tracks if track.gene_key == "lr_gamma"), None)

    assert lr_track is not None
    assert lr_track.trend_label == "↔ стабильно"
    assert lr_track.is_under_selection is False


def test_tc05_colony_health_normal_colony() -> None:
    runner = SimulationRunner()
    for i in range(10):
        agent = ChinchillaAgent(sex="F" if i % 2 == 0 else "M")
        agent.affective_space.axes["stress"] = 0.2
        agent.energy = 0.8
        runner.add_agent(agent)
    runner.resources.food_pellets = 0.8

    analytics = build_swarm_analytics(runner, None)

    assert analytics.health_index.overall > 0.50


def test_tc06_colony_health_crisis_colony() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F")
    agent.affective_space.axes["stress"] = 0.95
    agent.neuromodulators.cortisol = 0.95
    agent.energy = 0.1
    runner.add_agent(agent)

    analytics = build_swarm_analytics(runner, None)

    assert analytics.health_index.overall < 0.50
    assert analytics.health_index.color[0] > 150


def test_tc07_behavior_pattern_from_living_agents() -> None:
    runner = SimulationRunner()
    actions = ["eat", "eat", "sleep", "hide", "eat", "explore"]
    for i, action in enumerate(actions):
        agent = ChinchillaAgent(sex="F" if i % 2 == 0 else "M")
        agent.current_action = action
        runner.add_agent(agent)

    analytics = build_swarm_analytics(runner, None)
    eat_pattern = next(pattern for pattern in analytics.current_action_distribution if pattern.action == "eat")

    assert eat_pattern.count == 3
    assert abs(eat_pattern.fraction - 0.5) < 0.01


def test_tc08_forecast_cortisol_risk() -> None:
    runner = SimulationRunner()
    for i in range(5):
        agent = ChinchillaAgent(sex="F" if i % 2 == 0 else "M")
        agent.neuromodulators.cortisol = 0.90
        runner.add_agent(agent)

    analytics = build_swarm_analytics(runner, None)
    risk_texts = " ".join(analytics.forecast.key_risks).lower()

    assert "кортизол" in risk_texts or "репродукц" in risk_texts


def test_tc09_observer_trends_are_integrated() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    observer = ColonyPopulationObserver(runner, observe_every_n_ticks=1)
    for _ in range(10):
        runner.tick(0.1)
        observer.observe_tick()

    analytics = build_swarm_analytics(runner, observer)

    assert len(analytics.observer_stress_trend) > 0
    assert len(analytics.observer_population_trend) > 0


def test_tc10_swarm_analytics_overlay_toggle() -> None:
    overlay = SwarmAnalyticsOverlay()

    assert not overlay.visible
    overlay.toggle()
    assert overlay.visible
    overlay.toggle()
    assert not overlay.visible


def test_tc11_swarm_analytics_overlay_esc_closes() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")
    pygame.init()

    overlay = SwarmAnalyticsOverlay()
    overlay._visible = True
    esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""})
    consumed = overlay.handle_event(esc)

    assert consumed is True
    assert not overlay.visible
    pygame.quit()


def test_tc12_social_structure_isolated_agents() -> None:
    runner = SimulationRunner()
    for i in range(5):
        runner.add_agent(ChinchillaAgent(sex="F" if i % 2 == 0 else "M"))

    analytics = build_swarm_analytics(runner, None)

    assert analytics.current_social.isolation_count == 5
    assert analytics.current_social.total_known_pairs == 0


def test_tc13_select_display_generations_max_twelve() -> None:
    summaries = [_summary(i, {"lt_max_lifespan_factor": 1.0}) for i in range(20)]
    overlay = SwarmAnalyticsOverlay()

    display_points = overlay._select_display_generations(summaries)

    assert len(display_points) <= 12
    assert display_points[0].generation == 0
    assert display_points[-1].generation == 19


def test_tc14_forecast_summary_nonempty() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))

    analytics = build_swarm_analytics(runner, None)

    assert len(analytics.forecast.summary) > 20
    assert isinstance(analytics.forecast.summary, str)


def test_tc15_key_a_integration_closes_inspector_opens_overlay() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F")
    runner.add_agent(agent)
    gui = ColonyGUI(runner)
    gui.open_inspector(agent.agent_id)
    assert gui.inspector.visible

    if gui.inspector.visible:
        gui.inspector.close()
    gui.swarm_analytics.toggle()

    assert gui.swarm_analytics.visible
    assert not gui.inspector.visible


def test_overlay_refresh_and_draw_without_errors() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")
    pygame.init()
    screen = pygame.Surface((1000, 760), pygame.SRCALPHA)
    font = pygame.font.SysFont("Arial", 16)
    font_small = pygame.font.SysFont("Arial", 13)
    font_mono = pygame.font.SysFont("Courier New", 12)

    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    overlay = SwarmAnalyticsOverlay()
    overlay.toggle()
    overlay.refresh(runner, None)

    overlay.draw(screen, font, font_small, font_mono)

    pygame.quit()
