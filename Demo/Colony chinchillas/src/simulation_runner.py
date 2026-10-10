"""Simulation loop for colony agents."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from colony_agent import ChinchillaAgent
from colony_renderer import RenderSnapshot, build_snapshot
from colony_swarm_bridge import ColonySwarmBridge
from config_colony import REFILL_DAY_S
from death_registry import DeathRegistry
from birth_registry import BirthRegistry
from colony_gui.utils import canonical_display_name
from shared_resources import SharedResources


class SimulationRunner:
    """Runs colony simulation without centralized behavior decisions."""

    SIM_DT = 0.1

    def __init__(
        self,
        factory: Optional[Any] = None,
        death_journal_path: str | Path | None = None,
    ) -> None:
        self.agents: list[ChinchillaAgent] = []
        self.resources = SharedResources()
        self.sim_time = 0.0
        self._refill_enabled = True
        self.swarm = ColonySwarmBridge(factory=factory)
        self.births_this_step = 0
        self.deaths_this_step = 0
        self.total_births = 0
        self.total_deaths = 0
        self._death_log: list[dict[str, Any]] = []
        self._death_journal_path = self._resolve_death_journal_path(death_journal_path)
        self.death_registry = DeathRegistry(save_dir=self._resolve_save_dir())
        # Separate birth registry: authoritative source of human-readable
        # names captured at birth. Attach to death_registry for downstream
        # consumers that receive only the death registry object.
        self.birth_registry = BirthRegistry(save_dir=self._resolve_save_dir())
        try:
            # optional convenience: allow death_registry to reference birth registry
            setattr(self.death_registry, "birth_registry", self.birth_registry)
        except Exception:
            pass

    def add_agent(self, agent: ChinchillaAgent) -> None:
        agent.colony = self.agents
        agent.resources = self.resources
        self.agents.append(agent)
        self.swarm.add_agent(agent)
        # Compute a canonical display name for the newborn and register the
        # birth in both registries. The canonical name follows GUI format
        # (e.g., G0A1SM) and is computed using the generation index map.
        canonical_name = None
        try:
            gen_index_map = self._build_generation_index_map()
            canonical_name = canonical_display_name(agent, index_map=gen_index_map)
        except Exception:
            canonical_name = None

        # Register birth both in the death registry (for timing) and in the
        # dedicated birth registry for authoritative human-readable names.
        try:
            self.death_registry.register_birth(agent, self.sim_time)
        except Exception:
            pass
        try:
            self.birth_registry.register_birth(agent, self.sim_time, canonical_name=canonical_name)
        except Exception:
            pass

    def tick(self, dt: float) -> None:
        self.sim_time += dt
        self.births_this_step = 0
        self.deaths_this_step = 0

        self.swarm.sync_positions()
        self.swarm.update_signals()

        shuffled = list(self.agents)
        random.shuffle(shuffled)
        for agent in shuffled:
            agent.sim_step(dt)

        self.swarm.sync_positions()
        dead_ids = self.swarm.check_mortality()
        for agent_id in dead_ids:
            self._handle_agent_death(agent_id)

        self.swarm.check_reproduction()
        self._spawn_pending_offspring()
        self.swarm.update_ecology(len(self.agents))
        if self._refill_enabled:
            self._maybe_refill_resources()

    def run_for(self, duration_s: float, dt: float | None = None) -> None:
        step = self.SIM_DT if dt is None else dt
        remaining = duration_s
        while remaining > 0.0:
            self.tick(min(step, remaining))
            remaining -= step

    def _spawn_pending_offspring(self) -> None:
        new_agents: list[ChinchillaAgent] = []
        for agent in self.agents:
            while agent.pending_offspring_list:
                offspring = agent.pending_offspring_list.pop(0)
                offspring.colony = self.agents
                offspring.resources = self.resources
                new_agents.append(offspring)
        for offspring in new_agents:
            # Use add_agent to ensure consistent registration hooks.
            try:
                self.add_agent(offspring)
            except Exception:
                # Best-effort: fall back to manual insertion if add_agent fails.
                self.agents.append(offspring)
                try:
                    self.swarm.add_agent(offspring)
                except Exception:
                    pass
        if new_agents:
            born_now = len(new_agents)
            self.births_this_step += born_now
            self.total_births += born_now

    def _handle_agent_death(self, agent_id: str) -> None:
        dead_agent = next((agent for agent in self.agents if agent.agent_id == agent_id), None)
        if dead_agent is not None:
            generation_index_map = self._build_generation_index_map()
            self.death_registry.register_death(dead_agent, self.sim_time, generation_index_map)
        self.agents[:] = [agent for agent in self.agents if agent.agent_id != agent_id]
        entry = self._build_death_entry(agent_id=agent_id, agent=dead_agent)
        self._death_log.append(entry)
        self._append_death_entry(entry)
        self.deaths_this_step += 1
        self.total_deaths += 1

    def _maybe_refill_resources(self) -> None:
        if self.sim_time - self.resources.last_refill_time < REFILL_DAY_S:
            return
        self.resources.food_pellets = 1.0
        self.resources.hay = 1.0
        self.resources.water = 1.0
        self.resources.last_refill_time = self.sim_time

    def snapshot(self) -> RenderSnapshot:
        return build_snapshot(
            [agent.get_public_state() for agent in self.agents],
            self.resources,
            self.sim_time,
        )

    def _resolve_death_journal_path(self, custom_path: str | Path | None) -> Path:
        if custom_path is not None:
            return Path(custom_path)
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "logs" / "deaths.jsonl"

    def _resolve_save_dir(self) -> Path | None:
        if self._death_journal_path:
            return Path(self._death_journal_path).parent
        return None

    def _build_generation_index_map(self) -> dict[str, int]:
        by_generation: dict[int, list[str]] = {}
        for agent in self.agents:
            agent_id = str(getattr(agent, "agent_id", ""))
            if not agent_id:
                continue
            generation = int(getattr(agent, "generation", 0) or 0)
            by_generation.setdefault(generation, []).append(agent_id)
        out: dict[str, int] = {}
        for generation, agent_ids in by_generation.items():
            for idx, value in enumerate(sorted(set(agent_ids)), start=1):
                out[value] = idx
        return out

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _build_death_entry(self, *, agent_id: str, agent: ChinchillaAgent | None) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "agent_id": str(agent_id),
            "sim_time": float(self.sim_time),
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if agent is None:
            entry["cause_of_death"] = "unknown"
            return entry

        mortality = getattr(agent, "mortality_system", None)
        wakefulness = getattr(getattr(agent, "wakefulness", None), "wakefulness", 0.0)
        neuromodulators = getattr(agent, "neuromodulators", None)

        entry.update(
            {
                "name": str(getattr(agent, "name", "")),
                "sex": str(getattr(agent, "sex", "")),
                "generation": int(getattr(agent, "generation", 0) or 0),
                "age": self._safe_float(getattr(agent, "age", 0.0), 0.0),
                "lived_steps": int(getattr(agent, "lived_steps", 0) or 0),
                "position": str(getattr(agent, "position", "unknown")),
                "last_action": str(getattr(agent, "current_action", "unknown")),
                "cause_of_death": str(getattr(mortality, "cause_of_death", "") or "unknown"),
                "death_step": int(getattr(mortality, "death_step", -1) or -1),
                "vitality": self._safe_float(getattr(mortality, "vitality", 0.0), 0.0),
                "energy": self._safe_float(getattr(agent, "energy", 0.0), 0.0),
                "wakefulness": self._safe_float(wakefulness, 0.0),
                "stress": self._safe_float(getattr(agent, "stress", 0.0), 0.0),
                "arousal": self._safe_float(getattr(agent, "arousal", 0.0), 0.0),
                "valence": self._safe_float(getattr(agent, "valence", 0.0), 0.0),
                "cortisol": self._safe_float(getattr(neuromodulators, "cortisol", 0.0), 0.0),
            }
        )
        return entry

    def _append_death_entry(self, entry: dict[str, Any]) -> None:
        try:
            path = self._death_journal_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            # Logging must not break simulation loop.
            return
