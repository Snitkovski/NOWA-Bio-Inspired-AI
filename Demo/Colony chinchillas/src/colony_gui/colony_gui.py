"""Main GUI orchestration logic for colony simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_knowledge import PublicState
from colony_renderer import RenderSnapshot
from colony_population_observer import ColonyPopulationObserver
from colony_storage import ColonyStorage
from death_registry import DeathRegistry
from birth_registry import BirthRegistry
from shared_resources import SharedResources

from .agent_panel import AgentPanel
from .agent_inspector import (
    AgentInspectorOverlay,
    build_inspector_data_from_agent,
    build_inspector_data_from_memorial,
)
from .cage_view import get_zone_render_pos
from .lineage_overlay import LineageOverlay
from .swarm_analytics_overlay import SwarmAnalyticsOverlay
from .config import (
    ACTION_ANIMATIONS,
    ACTION_SFX,
    DEFAULT_SPEED,
    FPS,
    SIM_SPEED_LEVELS,
    UPDATE_INTERVAL_MS,
    WINDOW_SIZE,
    resolve_assets_dir,
    resolve_manifest_path,
)
from .detail_popup import build_agent_detail
from .interaction_overlay import InteractionEntry, extract_interactions
from .resource_bar import ResourceBar
from .utils import build_generation_index_map, canonical_display_name, format_sim_time

DEFAULT_OBSERVER_EVERY_N_TICKS = 5
HIGH_POP_OBSERVER_EVERY_N_TICKS = 20
VERY_HIGH_POP_OBSERVER_EVERY_N_TICKS = 40
HIGH_POPULATION_THRESHOLD = 50
VERY_HIGH_POPULATION_THRESHOLD = 100
INTERACTION_LOG_MAX_AGENTS = 48


def _copy_public_state(item: PublicState) -> PublicState:
    return PublicState(
        agent_id=str(item.agent_id),
        name=str(item.name),
        position=str(item.position),
        affect_tone=str(item.affect_tone),
        current_action=str(item.current_action),
        is_receptive=bool(item.is_receptive),
        sex=str(item.sex),
        age_category=str(item.age_category),
        scent_signature=str(item.scent_signature),
    )


def _copy_resources(resources: SharedResources) -> SharedResources:
    return SharedResources(
        food_pellets=float(resources.food_pellets),
        hay=float(resources.hay),
        water=float(resources.water),
        wheel_lock=resources.wheel_lock,
        dustbath_lock=resources.dustbath_lock,
        house_occupants=list(resources.house_occupants),
        shelf_occupants={key: list(value) for key, value in resources.shelf_occupants.items()},
        last_refill_time=float(resources.last_refill_time),
    )


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


class ColonyGUI:
    """Read-only GUI helper around SimulationRunner snapshots."""

    WIDTH = WINDOW_SIZE[0]
    HEIGHT = WINDOW_SIZE[1]
    FPS = FPS
    UPDATE_INTERVAL_MS = UPDATE_INTERVAL_MS

    def __init__(self, runner: Any) -> None:
        self.runner = runner
        if getattr(self.runner, "death_registry", None) is None:
            self.runner.death_registry = DeathRegistry()
        self.paused = False
        self.speed = DEFAULT_SPEED
        self.selected_agent_id: str | None = None
        self._snapshot: RenderSnapshot | None = None
        self._last_update_ms = 0
        self._interaction_log: list[InteractionEntry] = []
        self._generation_index_map: dict[str, int] = {}
        self.observer = ColonyPopulationObserver(
            runner,
            observe_every_n_ticks=DEFAULT_OBSERVER_EVERY_N_TICKS,
        )
        self._interaction_log_max_agents = INTERACTION_LOG_MAX_AGENTS

        self.sprites_dir = resolve_assets_dir("sprites")
        self.sfx_dir = resolve_assets_dir("sfx")
        self.sprite_manifest_path = resolve_manifest_path("sprites")
        self.sfx_manifest_path = resolve_manifest_path("sfx")
        self.sprite_manifest = _load_manifest(self.sprite_manifest_path)
        self.sfx_manifest = _load_manifest(self.sfx_manifest_path)
        self.inspector = AgentInspectorOverlay()
        # Enable non-adjacent parent links in the interactive GUI overlay per
        # user preference; tests that construct LineageOverlay directly will
        # keep the default conservative behaviour.
        self.lineage = LineageOverlay(self.runner.death_registry, allow_nonadjacent_parents=True)
        self.swarm_analytics = SwarmAnalyticsOverlay()
        self._right_panel_scroll: int = 0

    def run(self) -> None:
        """
        Minimal non-blocking tick suitable for integration loops.

        Rendering is intentionally left to dedicated UI glue; this class focuses
        on snapshot/read-model logic defined by specification.
        """
        self._update_snapshot()

    def _sim_tick(self, real_dt: float) -> None:
        """Advance simulation when not paused."""
        if self.paused:
            return
        self.runner.tick(float(real_dt) * float(self.speed))
        self._adapt_observer_sampling()
        self.observer.observe_tick()

    def _adapt_observer_sampling(self) -> None:
        """Reduce observer overhead on large populations."""
        agents = list(getattr(self.runner, "agents", []) or [])
        count = len(agents)
        target_every = DEFAULT_OBSERVER_EVERY_N_TICKS
        if count >= VERY_HIGH_POPULATION_THRESHOLD:
            target_every = VERY_HIGH_POP_OBSERVER_EVERY_N_TICKS
        elif count >= HIGH_POPULATION_THRESHOLD:
            target_every = HIGH_POP_OBSERVER_EVERY_N_TICKS
        if int(getattr(self.observer, "observe_every_n_ticks", target_every)) != target_every:
            self.observer.observe_every_n_ticks = target_every

    def _update_snapshot(self) -> None:
        """Refresh cached snapshot from runner in read-only mode."""
        base_snapshot = self.runner.snapshot()
        copied_agents = [_copy_public_state(item) for item in list(base_snapshot.agents)]
        copied_resources = _copy_resources(base_snapshot.resources)
        self._snapshot = RenderSnapshot(
            agents=copied_agents,
            resources=copied_resources,
            sim_time=float(base_snapshot.sim_time),
        )

        agents = list(getattr(self.runner, "agents", []) or [])
        self._generation_index_map = build_generation_index_map(agents)
        if len(agents) <= self._interaction_log_max_agents:
            self._interaction_log = extract_interactions(agents, now=float(self.runner.sim_time))
        else:
            self._interaction_log = []

    def speed_up(self) -> float:
        current = SIM_SPEED_LEVELS.index(self.speed) if self.speed in SIM_SPEED_LEVELS else 2
        current = min(len(SIM_SPEED_LEVELS) - 1, current + 1)
        self.speed = SIM_SPEED_LEVELS[current]
        return self.speed

    def speed_down(self) -> float:
        current = SIM_SPEED_LEVELS.index(self.speed) if self.speed in SIM_SPEED_LEVELS else 2
        current = max(0, current - 1)
        self.speed = SIM_SPEED_LEVELS[current]
        return self.speed

    def pause_resume(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def get_agent_display_name(self, agent_id: str) -> str:
        agent = next(
            (item for item in list(getattr(self.runner, "agents", [])) if str(item.agent_id) == str(agent_id)),
            None,
        )
        if agent is None:
            return str(agent_id)
        # Use authoritative birth registry for human-friendly names when available.
        try:
            registry = getattr(self.runner, "birth_registry", None)
            if registry is not None:
                name = registry.get_human_name(str(agent_id))
                if name:
                    return name
        except Exception:
            pass
        return str(agent_id)

    def get_render_state(self) -> dict[str, Any]:
        """Build computed read-model for renderers and tests."""
        if self._snapshot is None:
            self._update_snapshot()
        assert self._snapshot is not None

        runner_agents = {str(agent.agent_id): agent for agent in list(getattr(self.runner, "agents", []))}
        zone_counts: dict[str, int] = {}
        render_agents: list[dict[str, Any]] = []

        for public in self._snapshot.agents:
            zone = str(public.position)
            zone_index = zone_counts.get(zone, 0)
            zone_counts[zone] = zone_index + 1
            pos_x, pos_y = get_zone_render_pos(zone, agent_index=zone_index, agent_id=public.agent_id)

            source_agent = runner_agents.get(public.agent_id)
            # All human-readable names must come exclusively from the birth
            # registry. If no registry or no name is recorded, fall back to
            # the agent id (not to a synthesized canonical name).
            try:
                registry = getattr(self.runner, "birth_registry", None)
                display_name = registry.get_human_name(str(public.agent_id)) if registry is not None else ""
            except Exception:
                display_name = ""
            if not display_name:
                display_name = str(public.agent_id)

            action = str(public.current_action or "idle")
            animation_id = ACTION_ANIMATIONS.get(action, ACTION_ANIMATIONS["idle"])
            sfx_id = ACTION_SFX.get(action, ACTION_SFX.get("idle"))
            stress = 0.0
            energy = 1.0
            if source_agent is not None:
                try:
                    stress = float(getattr(source_agent, "stress", 0.0))
                except Exception:
                    stress = 0.0
                try:
                    energy = float(getattr(source_agent, "energy", 1.0))
                except Exception:
                    energy = 1.0
            render_agents.append(
                {
                    "agent_id": public.agent_id,
                    "name": display_name,
                    "sex": public.sex,
                    "age_category": public.age_category,
                    "position": public.position,
                    "render_pos": (pos_x, pos_y),
                    "action": action,
                    "animation_id": animation_id,
                    "sfx_id": sfx_id,
                    "has_animation": animation_id in self.sprite_manifest,
                    "has_sfx": (sfx_id is None) or (sfx_id in self.sfx_manifest),
                    "affect_tone": public.affect_tone,
                    "stress": max(0.0, min(1.0, stress)),
                    "energy": max(0.0, min(1.0, energy)),
                }
            )

        resources = self._snapshot.resources
        return {
            "window_size": WINDOW_SIZE,
            "sim_time": self._snapshot.sim_time,
            "sim_time_text": format_sim_time(self._snapshot.sim_time),
            "resources": {
                "food_pellets": ResourceBar.clamp_level(resources.food_pellets),
                "hay": ResourceBar.clamp_level(resources.hay),
                "water": ResourceBar.clamp_level(resources.water),
            },
            "agents": render_agents,
            "interactions": list(self._interaction_log),
            "sprite_manifest_path": str(self.sprite_manifest_path),
            "sfx_manifest_path": str(self.sfx_manifest_path),
            "population_stats": self._build_population_stats(),
        }

    def _build_population_stats(self) -> dict[str, Any]:
        """Build robust population observer payload for renderers."""
        defaults: dict[str, Any] = {
            "extinction_risk": 0.0,
            "social_cohesion": 0.0,
            "agent_count": 0,
            "female_count": 0,
            "male_count": 0,
            "juvenile_count": 0,
            "pregnant_count": 0,
            "sleeping_count": 0,
            "births_since_last": 0,
            "deaths_since_last": 0,
            "total_births": 0,
            "total_deaths": 0,
            "mean_stress": 0.0,
            "mean_valence": 0.0,
            "mean_energy": 0.0,
            "mean_affinity": 0.0,
            "bonded_pairs": 0,
            "total_known_pairs": 0,
            "mean_genome_diversity": 0.0,
            "stress_trend": [],
            "energy_trend": [],
            "population_trend": [],
            "summary": "",
            "has_data": False,
        }
        try:
            observer = getattr(self, "observer", None)
            if observer is None:
                return defaults

            latest = observer.get_latest()
            if latest is None:
                return defaults

            return {
                "extinction_risk": float(observer.get_extinction_risk()),
                "social_cohesion": float(observer.get_social_cohesion()),
                "agent_count": int(latest.agent_count),
                "female_count": int(latest.female_count),
                "male_count": int(latest.male_count),
                "juvenile_count": int(latest.juvenile_count),
                "pregnant_count": int(latest.pregnant_count),
                "sleeping_count": int(latest.sleeping_count),
                "births_since_last": int(latest.births_since_last),
                "deaths_since_last": int(latest.deaths_since_last),
                "total_births": int(latest.total_births),
                "total_deaths": int(latest.total_deaths),
                "mean_stress": float(latest.mean_stress),
                "mean_valence": float(latest.mean_valence),
                "mean_energy": float(latest.mean_energy),
                "mean_affinity": float(latest.mean_affinity),
                "bonded_pairs": int(latest.bonded_pairs),
                "total_known_pairs": int(latest.total_known_pairs),
                "mean_genome_diversity": float(latest.mean_genome_diversity),
                "stress_trend": list(observer.get_trend("mean_stress", last_n=20)),
                "energy_trend": list(observer.get_trend("mean_energy", last_n=20)),
                "population_trend": list(observer.get_trend("agent_count", last_n=20)),
                "summary": str(observer.summary_text()),
                "has_data": True,
            }
        except Exception:
            return defaults

    def build_agent_card(self, agent_id: str) -> dict[str, Any]:
        if self._snapshot is None:
            self._update_snapshot()
        assert self._snapshot is not None
        return AgentPanel(self._snapshot).build_card(agent_id, self.runner)

    def build_agent_detail(self, agent_id: str) -> dict[str, Any]:
        agents = list(getattr(self.runner, "agents", []) or [])
        match = next((agent for agent in agents if str(agent.agent_id) == str(agent_id)), None)
        if match is None:
            raise KeyError(f"Agent not found: {agent_id}")
        return build_agent_detail(match, agents, name_registry=getattr(self.runner, "birth_registry", None))

    def open_inspector(self, agent_id: str) -> None:
        target_id = str(agent_id)
        agents = list(getattr(self.runner, "agents", []) or [])
        living_agent = next((agent for agent in agents if str(getattr(agent, "agent_id", "")) == target_id), None)
        if living_agent is not None:
            try:
                registry = getattr(self.runner, "birth_registry", None)
                display_name = registry.get_human_name(target_id) if registry is not None else ""
            except Exception:
                display_name = ""
            display_name = display_name or target_id
            payload = build_inspector_data_from_agent(
                living_agent,
                display_name,
                name_registry=getattr(self.runner, "birth_registry", None),
                death_registry=getattr(self.runner, "death_registry", None),
                generation_index_map=getattr(self, "_generation_index_map", {}),
            )
            self.lineage.close()
            self.swarm_analytics.close()
            self.inspector.open(payload)
            return

        registry = getattr(self.runner, "death_registry", None)
        if registry is None:
            return
        memorial = registry.get_memorial(target_id)
        if memorial is None:
            return
        try:
            registry = getattr(self.runner, "birth_registry", None)
            display_name = registry.get_human_name(target_id) if registry is not None else ""
        except Exception:
            display_name = ""
        display_name = display_name or target_id
        payload = build_inspector_data_from_memorial(
            memorial,
            display_name,
            name_registry=getattr(self.runner, "birth_registry", None),
            death_registry=getattr(self.runner, "death_registry", None),
        )
        self.lineage.close()
        self.swarm_analytics.close()
        self.inspector.open(payload)

    def close_all_overlays(self) -> None:
        self.inspector.close()
        self.lineage.close()
        self.swarm_analytics.close()

    def save(self, path: str | Path) -> str:
        target = Path(path)
        storage = ColonyStorage(save_dir=target.parent)
        result = storage.save_colony(self.runner, target.name)
        registry = getattr(self.runner, "death_registry", None)
        if registry is not None:
            registry.save(target.parent / "death_registry.json")
        birth_registry = getattr(self.runner, "birth_registry", None)
        if birth_registry is not None:
            try:
                birth_registry.save(target.parent / "birth_registry.json")
            except Exception:
                pass
        return result

    def load(self, path: str | Path) -> None:
        source = Path(path)
        storage = ColonyStorage(save_dir=source.parent)
        self.runner = storage.load_colony(source)
        if getattr(self.runner, "death_registry", None) is None:
            self.runner.death_registry = DeathRegistry(save_dir=source.parent)
        registry_path = source.parent / "death_registry.json"
        if registry_path.exists():
            self.runner.death_registry.load(registry_path)
        # Ensure birth registry exists and try loading it from disk.
        if getattr(self.runner, "birth_registry", None) is None:
            try:
                self.runner.birth_registry = BirthRegistry(save_dir=source.parent)
            except Exception:
                self.runner.birth_registry = None
        birth_path = source.parent / "birth_registry.json"
        if getattr(self.runner, "birth_registry", None) is not None and birth_path.exists():
            try:
                self.runner.birth_registry.load(birth_path)
            except Exception:
                pass
        self._snapshot = None
        self.observer = ColonyPopulationObserver(
            self.runner,
            observe_every_n_ticks=5,
        )
        self.inspector.close()
        self.swarm_analytics.close()
        self.swarm_analytics.mark_dirty()
        self.lineage = LineageOverlay(self.runner.death_registry, allow_nonadjacent_parents=True)
        self.lineage.mark_dirty()
        self._right_panel_scroll = 0
