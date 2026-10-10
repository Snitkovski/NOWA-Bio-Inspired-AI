"""Passive population observer for emergent evolution simulations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Dict, List

from fitness import CRITERIA_ORDER


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if casted != casted or casted in (float("inf"), float("-inf")):
        return float(fallback)
    return casted


@dataclass(frozen=True)
class PopulationSnapshot:
    step: int
    agent_count: int
    mean_genome_diversity: float
    mean_vitality: float
    mean_reproductive_drive: float
    births_this_step: int
    deaths_this_step: int
    total_births: int
    total_deaths: int
    resource_level: float
    resource_share: float
    mean_age_fraction: float
    oldest_agent_id: str
    most_offspring_agent_id: str
    mean_fitness: Dict[str, float]


class PopulationObserver:
    """
    Passive observer that collects population metrics without mutating the environment.
    """

    def __init__(self, environment: Any):
        self.environment = environment
        self.history: List[PopulationSnapshot] = []

    def _mean_fitness(self, agents: List[Any]) -> Dict[str, float]:
        evaluator = getattr(self.environment, "fitness_evaluator", None)
        if evaluator is None or not agents:
            return {}

        sums = {criterion: 0.0 for criterion in CRITERIA_ORDER}
        count = 0
        for agent in agents:
            try:
                vector = evaluator.evaluate(agent)
            except Exception:
                continue
            count += 1
            for criterion in CRITERIA_ORDER:
                sums[criterion] += _safe_float(getattr(vector, criterion, 0.0), 0.0)

        if count == 0:
            return {}
        return {criterion: sums[criterion] / float(count) for criterion in CRITERIA_ORDER}

    def observe(self) -> PopulationSnapshot:
        """Collect one snapshot and append it to observer history."""
        agents = list(getattr(self.environment, "get_all_agents", lambda: [])() or [])
        agent_count = len(agents)

        ecology = getattr(self.environment, "ecology", None)
        if ecology is None:
            resource_level = 0.0
            resource_share = 1.0 if agent_count == 0 else 0.0
        else:
            resource_level = _safe_float(getattr(ecology, "current_resources", 0.0), 0.0)
            compute_share = getattr(ecology, "compute_resource_share", None)
            if callable(compute_share):
                try:
                    resource_share = _safe_float(compute_share(agent_count), 0.0)
                except Exception:
                    resource_share = 0.0
            else:
                resource_share = 0.0

        vitality_values: List[float] = []
        drive_values: List[float] = []
        age_fractions: List[float] = []
        oldest_agent_id = ""
        oldest_age = -1.0
        most_offspring_agent_id = ""
        most_offspring = -1

        for agent in agents:
            agent_id = str(getattr(agent, "agent_id", "") or "")

            mortality = getattr(agent, "mortality_system", None)
            if mortality is not None:
                vitality_values.append(_safe_float(getattr(mortality, "vitality", 0.0), 0.0))
                try:
                    age_fraction = _safe_float(
                        mortality.get_age_fraction(getattr(agent, "lived_steps", 0)),
                        0.0,
                    )
                except Exception:
                    age_fraction = 0.0
            else:
                age_fraction = 0.0
            age_fractions.append(age_fraction)
            if age_fraction > oldest_age:
                oldest_age = age_fraction
                oldest_agent_id = agent_id

            reproductive = getattr(agent, "reproductive_system", None)
            if reproductive is not None:
                drive_values.append(_safe_float(getattr(reproductive, "reproductive_drive", 0.0), 0.0))
                offspring = int(getattr(reproductive, "total_offspring", 0))
                if offspring > most_offspring:
                    most_offspring = offspring
                    most_offspring_agent_id = agent_id

        mean_vitality = sum(vitality_values) / float(len(vitality_values)) if vitality_values else 0.0
        mean_drive = sum(drive_values) / float(len(drive_values)) if drive_values else 0.0
        mean_age_fraction = sum(age_fractions) / float(len(age_fractions)) if age_fractions else 0.0

        snapshot = PopulationSnapshot(
            step=int(getattr(self.environment, "global_step", 0)),
            agent_count=agent_count,
            mean_genome_diversity=_safe_float(
                getattr(self.environment, "get_diversity", lambda: 0.0)(),
                0.0,
            ),
            mean_vitality=mean_vitality,
            mean_reproductive_drive=mean_drive,
            births_this_step=int(getattr(self.environment, "births_this_step", 0)),
            deaths_this_step=int(getattr(self.environment, "deaths_this_step", 0)),
            total_births=int(getattr(self.environment, "total_births", 0)),
            total_deaths=int(getattr(self.environment, "total_deaths", 0)),
            resource_level=resource_level,
            resource_share=resource_share,
            mean_age_fraction=mean_age_fraction,
            oldest_agent_id=oldest_agent_id,
            most_offspring_agent_id=most_offspring_agent_id,
            mean_fitness=self._mean_fitness(agents),
        )
        self.history.append(snapshot)
        return snapshot

    def save(self, path: str) -> None:
        """Persist snapshot history as JSON."""
        payload = [asdict(item) for item in self.history]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str, environment: Any) -> "PopulationObserver":
        """Load snapshot history from JSON."""
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observer = cls(environment=environment)
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    observer.history.append(PopulationSnapshot(**item))
        return observer


__all__ = [
    "PopulationSnapshot",
    "PopulationObserver",
]
