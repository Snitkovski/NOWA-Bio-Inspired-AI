"""Passive population observer for the chinchilla colony simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import warnings

OBSERVER_VERSION = "1.0"
MAX_HISTORY_LENGTH = 10000
EXTINCTION_RISK_WEIGHTS = {
    "low_population": 0.4,
    "single_sex": 0.3,
    "high_stress": 0.2,
    "food_critical": 0.2,
    "no_reproduction": 0.3,
}
EXTINCTION_RISK_MAX_WEIGHT = sum(EXTINCTION_RISK_WEIGHTS.values())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return float(default)
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return float(default)
    return parsed


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        return 0.0
    return sum(data) / float(len(data))


def _safe_str(value: Any, default: str = "") -> str:
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _read_neuromodulator(agent: Any, nm_name: str) -> float:
    """Read neuromodulator value via ``agent.neuromodulators.{nm_name}``."""
    try:
        neuromodulators = getattr(agent, "neuromodulators", None)
        value = _safe_float(getattr(neuromodulators, nm_name, 0.0), 0.0)
        return _clamp(value, 0.0, 1.0)
    except Exception:
        return 0.0


def _read_affective_axis(agent: Any, axis: str) -> float:
    """Read affective axis via ``agent.affective_space.axes.get(axis, 0.0)``."""
    try:
        affective_space = getattr(agent, "affective_space", None)
        axes = getattr(affective_space, "axes", None)
        if hasattr(axes, "get"):
            value = _safe_float(axes.get(axis, 0.0), 0.0)
        else:
            value = _safe_float(getattr(agent, axis, 0.0), 0.0)
    except Exception:
        value = 0.0
    if axis == "valence":
        return _clamp(value, -1.0, 1.0)
    return _clamp(value, 0.0, 1.0)


def _collect_knowledge_stats(
    agents: List[Any],
) -> Tuple[float, float, int, int, int, int, int]:
    """
    Return:
        (mean_affinity, mean_familiarity, total_pairs, bonded, rival, kin, mate)
    """
    affinity_values: list[float] = []
    familiarity_values: list[float] = []
    total_pairs = 0
    bonded = 0
    rival = 0
    kin = 0
    mate = 0

    for agent in agents:
        try:
            knowledge = getattr(agent, "knowledge", None)
            if isinstance(knowledge, dict):
                known_entries = list(knowledge.values())
            elif isinstance(knowledge, list):
                known_entries = list(knowledge)
            else:
                known_entries = []
        except Exception:
            known_entries = []

        for known in known_entries:
            try:
                if isinstance(known, dict):
                    affinity = _safe_float(known.get("affinity", 0.0), 0.0)
                    familiarity = _safe_float(known.get("familiarity", 0.0), 0.0)
                    relation = _safe_str(known.get("relationship_type", ""), "").lower()
                else:
                    affinity = _safe_float(getattr(known, "affinity", 0.0), 0.0)
                    familiarity = _safe_float(getattr(known, "familiarity", 0.0), 0.0)
                    relation = _safe_str(getattr(known, "relationship_type", ""), "").lower()
                affinity_values.append(_clamp(affinity, -1.0, 1.0))
                familiarity_values.append(_clamp(familiarity, 0.0, 1.0))
                total_pairs += 1
                if relation == "bonded":
                    bonded += 1
                elif relation == "rival":
                    rival += 1
                elif relation == "kin":
                    kin += 1
                elif relation == "mate":
                    mate += 1
            except Exception:
                continue

    return (
        _mean(affinity_values),
        _mean(familiarity_values),
        total_pairs,
        bonded,
        rival,
        kin,
        mate,
    )


def _build_action_distribution(agents: List[Any]) -> Dict[str, int]:
    """Count ``{action: count}`` for all agents."""
    distribution: dict[str, int] = {}
    for agent in agents:
        try:
            action = _safe_str(getattr(agent, "current_action", "idle"), "idle")
        except Exception:
            action = "idle"
        distribution[action] = distribution.get(action, 0) + 1
    return distribution


def _build_position_distribution(agents: List[Any]) -> Dict[str, int]:
    """Count ``{zone: count}`` for all agents."""
    distribution: dict[str, int] = {}
    for agent in agents:
        try:
            zone = _safe_str(getattr(agent, "position", "floor"), "floor")
        except Exception:
            zone = "floor"
        distribution[zone] = distribution.get(zone, 0) + 1
    return distribution


def _read_age_fraction(agent: Any) -> float:
    mortality = getattr(agent, "mortality_system", None)
    getter = getattr(mortality, "get_age_fraction", None)
    lived_steps = _safe_int(getattr(agent, "lived_steps", 0), 0)
    biological_age_s = _safe_float(getattr(agent, "age", 0.0), 0.0)
    if callable(getter):
        try:
            return _clamp(_safe_float(getter(lived_steps, biological_age_s=biological_age_s), 0.0), 0.0, 1.0)
        except TypeError:
            try:
                return _clamp(_safe_float(getter(lived_steps), 0.0), 0.0, 1.0)
            except Exception:
                pass
        except Exception:
            pass
    max_steps = _safe_int(getattr(mortality, "max_lifespan_steps", 0), 0)
    if max_steps <= 0:
        return 0.0
    return _clamp(float(lived_steps) / float(max_steps), 0.0, 1.0)


@dataclass(frozen=True)
class ColonySnapshot:
    # Time
    sim_time: float = field(default=0.0)
    tick_number: int = field(default=0)

    # Demographics
    agent_count: int = field(default=0)
    female_count: int = field(default=0)
    male_count: int = field(default=0)
    juvenile_count: int = field(default=0)
    adult_count: int = field(default=0)
    elder_count: int = field(default=0)
    pregnant_count: int = field(default=0)
    sleeping_count: int = field(default=0)

    # Births / deaths
    births_since_last: int = field(default=0)
    deaths_since_last: int = field(default=0)
    total_births: int = field(default=0)
    total_deaths: int = field(default=0)

    # Affective means
    mean_stress: float = field(default=0.0)
    mean_valence: float = field(default=0.0)
    mean_arousal: float = field(default=0.0)
    mean_energy: float = field(default=0.0)
    mean_social_drive: float = field(default=0.0)

    # Neuromodulator means
    mean_dopamine: float = field(default=0.0)
    mean_serotonin: float = field(default=0.0)
    mean_cortisol: float = field(default=0.0)
    mean_wakefulness: float = field(default=0.0)

    # Social structure
    mean_affinity: float = field(default=0.0)
    mean_familiarity: float = field(default=0.0)
    total_known_pairs: int = field(default=0)
    bonded_pairs: int = field(default=0)
    rival_pairs: int = field(default=0)
    kin_pairs: int = field(default=0)
    mate_pairs: int = field(default=0)

    # Reproduction
    mean_reproductive_drive: float = field(default=0.0)
    mean_heat_cycle_value: float = field(default=0.0)
    mean_vitality: float = field(default=0.0)
    mean_age: float = field(default=0.0)

    # NOWA cognition
    mean_lived_steps: float = field(default=0.0)
    mean_hippocampus_size: float = field(default=0.0)
    mean_td_error: float = field(default=0.0)
    mean_genome_diversity: float = field(default=0.0)

    # Resources
    food_pellets: float = field(default=0.0)
    hay: float = field(default=0.0)
    water: float = field(default=0.0)
    wheel_occupied: bool = field(default=False)
    dustbath_occupied: bool = field(default=False)
    house_occupant_count: int = field(default=0)

    # Activity
    action_distribution: Dict[str, int] = field(default_factory=dict)
    position_distribution: Dict[str, int] = field(default_factory=dict)

    # Record holders
    oldest_agent_id: str = field(default="")
    most_offspring_agent_id: str = field(default="")
    most_social_agent_id: str = field(default="")
    most_stressed_agent_id: str = field(default="")


class ColonyPopulationObserver:
    """Passive observer of colony population dynamics."""

    def __init__(self, runner: Any, observe_every_n_ticks: int = 1) -> None:
        self.runner = runner
        self.observe_every_n_ticks = max(1, _safe_int(observe_every_n_ticks, 1))
        self.history: List[ColonySnapshot] = []
        self._tick_counter: int = 0
        self._total_births_last: int = 0
        self._total_deaths_last: int = 0
        self._prev_agent_ids: Set[str] = set()
        self._snapshot_fields = {item.name for item in fields(ColonySnapshot)}

    def _iter_agents(self) -> list[Any]:
        try:
            agents = getattr(self.runner, "agents", None)
            if isinstance(agents, list):
                return list(agents)
            if agents is None:
                return []
            return list(agents)
        except Exception:
            return []

    def _compute_sleeping_count(self, agents: list[Any], active_agent_ids: set[str]) -> int:
        swarm = getattr(self.runner, "swarm", None)
        getter = getattr(swarm, "get_sleeping_agents", None)
        if callable(getter):
            try:
                sleeping_raw = getter()
                if isinstance(sleeping_raw, (list, tuple, set)):
                    sleeping_ids = {_safe_str(item, "") for item in sleeping_raw}
                else:
                    sleeping_ids = set()
                sleeping_ids.discard("")
                if active_agent_ids:
                    return len(active_agent_ids.intersection(sleeping_ids))
                return len(sleeping_ids)
            except Exception:
                pass

        count = 0
        for agent in agents:
            try:
                if bool(getattr(agent, "is_sleeping", False)):
                    count += 1
            except Exception:
                continue
        return count

    def _read_diversity(self) -> float:
        swarm = getattr(self.runner, "swarm", None)
        getter = getattr(swarm, "get_diversity", None)
        if callable(getter):
            try:
                value = getter()
                if callable(value):
                    value = value()
                return _clamp(_safe_float(value, 0.0), 0.0, 1.0)
            except Exception:
                return 0.0
        return 0.0

    def _safe_reproduction_ready(self, agent: Any) -> bool:
        try:
            if not bool(getattr(agent, "is_mature", False)):
                return False
            if bool(getattr(agent, "is_sleeping", False)):
                return False

            sex = _safe_str(getattr(agent, "sex", ""), "").upper()
            if sex == "F" and bool(getattr(agent, "is_pregnant", False)):
                return False

            reproductive = getattr(agent, "reproductive_system", None)
            is_ready_fn = getattr(reproductive, "is_ready", None)
            if callable(is_ready_fn):
                try:
                    if not bool(is_ready_fn()):
                        return False
                except Exception:
                    return False
            else:
                drive = _safe_float(getattr(reproductive, "reproductive_drive", 0.0), 0.0)
                threshold = _safe_float(getattr(reproductive, "drive_threshold", 0.55), 0.55)
                if drive < threshold:
                    return False

            if sex == "F":
                heat_cycle = getattr(agent, "heat_cycle", None)
                if heat_cycle is not None:
                    phase = _safe_str(getattr(heat_cycle, "phase", ""), "").lower()
                    value = _safe_float(getattr(heat_cycle, "value", 0.0), 0.0)
                    if phase not in {"estrus", "proestrus"} and value < 0.55:
                        return False
            return True
        except Exception:
            return False

    def _has_reproduction_potential(self, agents: list[Any]) -> bool:
        for agent in agents:
            try:
                if bool(getattr(agent, "is_pregnant", False)):
                    return True
            except Exception:
                continue

        ready_females = 0
        ready_males = 0
        for agent in agents:
            if not self._safe_reproduction_ready(agent):
                continue
            sex = _safe_str(getattr(agent, "sex", ""), "").upper()
            if sex == "F":
                ready_females += 1
            elif sex == "M":
                ready_males += 1

        return ready_females > 0 and ready_males > 0

    def _collect_snapshot(self, *, tick_number: int) -> ColonySnapshot:
        agents = self._iter_agents()
        agent_count = len(agents)
        active_agent_ids: set[str] = set()
        for agent in agents:
            agent_id = _safe_str(getattr(agent, "agent_id", ""), "")
            if agent_id:
                active_agent_ids.add(agent_id)

        sim_time = _safe_float(getattr(self.runner, "sim_time", 0.0), 0.0)

        female_count = 0
        male_count = 0
        juvenile_count = 0
        adult_count = 0
        elder_count = 0
        pregnant_count = 0

        stress_values: list[float] = []
        valence_values: list[float] = []
        arousal_values: list[float] = []
        energy_values: list[float] = []
        social_drive_values: list[float] = []
        dopamine_values: list[float] = []
        serotonin_values: list[float] = []
        cortisol_values: list[float] = []
        wakefulness_values: list[float] = []

        reproductive_drive_values: list[float] = []
        heat_cycle_values: list[float] = []
        vitality_values: list[float] = []
        age_values: list[float] = []

        lived_steps_values: list[float] = []
        hippocampus_sizes: list[float] = []
        td_errors: list[float] = []

        oldest_agent_id = ""
        oldest_age = -1.0
        most_offspring_agent_id = ""
        most_offspring = -1
        most_social_agent_id = ""
        most_social_size = -1
        most_stressed_agent_id = ""
        most_stressed = -1.0

        for agent in agents:
            sex = _safe_str(getattr(agent, "sex", ""), "").upper()
            if sex == "F":
                female_count += 1
            elif sex == "M":
                male_count += 1

            is_mature = bool(getattr(agent, "is_mature", False))
            age_fraction = _read_age_fraction(agent)
            if not is_mature:
                juvenile_count += 1
            elif age_fraction >= 0.75:
                elder_count += 1
            else:
                adult_count += 1

            if bool(getattr(agent, "is_pregnant", False)):
                pregnant_count += 1

            stress = _read_affective_axis(agent, "stress")
            stress_values.append(stress)
            valence_values.append(_read_affective_axis(agent, "valence"))
            arousal_values.append(_read_affective_axis(agent, "arousal"))

            energy_values.append(_clamp(_safe_float(getattr(agent, "energy", 0.0), 0.0), 0.0, 1.0))
            social_drive_values.append(_clamp(_safe_float(getattr(agent, "social_drive", 0.0), 0.0), 0.0, 1.0))
            dopamine_values.append(_read_neuromodulator(agent, "dopamine"))
            serotonin_values.append(_read_neuromodulator(agent, "serotonin"))
            cortisol_values.append(_read_neuromodulator(agent, "cortisol"))

            wakefulness_obj = getattr(agent, "wakefulness", None)
            wakefulness_values.append(
                _clamp(_safe_float(getattr(wakefulness_obj, "wakefulness", 0.0), 0.0), 0.0, 1.0)
            )

            reproductive = getattr(agent, "reproductive_system", None)
            reproductive_drive_values.append(
                _clamp(_safe_float(getattr(reproductive, "reproductive_drive", 0.0), 0.0), 0.0, 1.0)
            )
            if sex == "F":
                heat_cycle = getattr(agent, "heat_cycle", None)
                if heat_cycle is not None:
                    heat_cycle_values.append(_clamp(_safe_float(getattr(heat_cycle, "value", 0.0), 0.0), 0.0, 1.0))

            mortality = getattr(agent, "mortality_system", None)
            vitality_values.append(_clamp(_safe_float(getattr(mortality, "vitality", 0.0), 0.0), 0.0, 1.0))
            age = max(0.0, _safe_float(getattr(agent, "age", 0.0), 0.0))
            age_values.append(age)

            lived_steps_values.append(max(0.0, _safe_float(getattr(agent, "lived_steps", 0), 0.0)))
            experiences = getattr(getattr(agent, "hippocampus", None), "experiences", None)
            if isinstance(experiences, list):
                hippocampus_sizes.append(float(len(experiences)))
            else:
                hippocampus_sizes.append(0.0)

            td_history = getattr(agent, "td_error_history", None)
            if isinstance(td_history, list):
                for td_value in td_history:
                    td_errors.append(_safe_float(td_value, 0.0))

            agent_id = _safe_str(getattr(agent, "agent_id", ""), "")
            if age > oldest_age:
                oldest_age = age
                oldest_agent_id = agent_id

            offspring_count = _safe_int(getattr(reproductive, "total_offspring", 0), 0)
            if offspring_count > most_offspring:
                most_offspring = offspring_count
                most_offspring_agent_id = agent_id

            knowledge = getattr(agent, "knowledge", None)
            social_size = len(knowledge) if isinstance(knowledge, dict) else 0
            if social_size > most_social_size:
                most_social_size = social_size
                most_social_agent_id = agent_id

            if stress > most_stressed:
                most_stressed = stress
                most_stressed_agent_id = agent_id

        sleeping_count = self._compute_sleeping_count(agents, active_agent_ids)

        total_births_attr = getattr(self.runner, "total_births", None)
        total_deaths_attr = getattr(self.runner, "total_deaths", None)

        inferred_births = max(0, len(active_agent_ids - self._prev_agent_ids))
        inferred_deaths = max(0, len(self._prev_agent_ids - active_agent_ids))

        if total_births_attr is None:
            total_births = self._total_births_last + inferred_births
        else:
            total_births = max(0, _safe_int(total_births_attr, self._total_births_last))

        if total_deaths_attr is None:
            total_deaths = self._total_deaths_last + inferred_deaths
        else:
            total_deaths = max(0, _safe_int(total_deaths_attr, self._total_deaths_last))

        births_since_last = max(0, total_births - self._total_births_last)
        deaths_since_last = max(0, total_deaths - self._total_deaths_last)

        self._total_births_last = total_births
        self._total_deaths_last = total_deaths
        self._prev_agent_ids = set(active_agent_ids)

        (
            mean_affinity,
            mean_familiarity,
            total_known_pairs,
            bonded_pairs,
            rival_pairs,
            kin_pairs,
            mate_pairs,
        ) = _collect_knowledge_stats(agents)

        resources = getattr(self.runner, "resources", None)
        food_pellets = _clamp(_safe_float(getattr(resources, "food_pellets", 0.0), 0.0), 0.0, 1.0)
        hay = _clamp(_safe_float(getattr(resources, "hay", 0.0), 0.0), 0.0, 1.0)
        water = _clamp(_safe_float(getattr(resources, "water", 0.0), 0.0), 0.0, 1.0)
        wheel_occupied = bool(getattr(resources, "wheel_lock", None))
        dustbath_occupied = bool(getattr(resources, "dustbath_lock", None))
        house_occupants = getattr(resources, "house_occupants", None)
        house_occupant_count = len(house_occupants) if isinstance(house_occupants, list) else 0

        return ColonySnapshot(
            sim_time=sim_time,
            tick_number=max(0, _safe_int(tick_number, 0)),
            agent_count=agent_count,
            female_count=female_count,
            male_count=male_count,
            juvenile_count=juvenile_count,
            adult_count=adult_count,
            elder_count=elder_count,
            pregnant_count=pregnant_count,
            sleeping_count=max(0, sleeping_count),
            births_since_last=births_since_last,
            deaths_since_last=deaths_since_last,
            total_births=total_births,
            total_deaths=total_deaths,
            mean_stress=_mean(stress_values),
            mean_valence=_mean(valence_values),
            mean_arousal=_mean(arousal_values),
            mean_energy=_mean(energy_values),
            mean_social_drive=_mean(social_drive_values),
            mean_dopamine=_mean(dopamine_values),
            mean_serotonin=_mean(serotonin_values),
            mean_cortisol=_mean(cortisol_values),
            mean_wakefulness=_mean(wakefulness_values),
            mean_affinity=mean_affinity,
            mean_familiarity=mean_familiarity,
            total_known_pairs=total_known_pairs,
            bonded_pairs=bonded_pairs,
            rival_pairs=rival_pairs,
            kin_pairs=kin_pairs,
            mate_pairs=mate_pairs,
            mean_reproductive_drive=_mean(reproductive_drive_values),
            mean_heat_cycle_value=_mean(heat_cycle_values),
            mean_vitality=_mean(vitality_values),
            mean_age=_mean(age_values),
            mean_lived_steps=_mean(lived_steps_values),
            mean_hippocampus_size=_mean(hippocampus_sizes),
            mean_td_error=_mean(td_errors),
            mean_genome_diversity=self._read_diversity(),
            food_pellets=food_pellets,
            hay=hay,
            water=water,
            wheel_occupied=wheel_occupied,
            dustbath_occupied=dustbath_occupied,
            house_occupant_count=house_occupant_count,
            action_distribution=_build_action_distribution(agents),
            position_distribution=_build_position_distribution(agents),
            oldest_agent_id=oldest_agent_id,
            most_offspring_agent_id=most_offspring_agent_id,
            most_social_agent_id=most_social_agent_id,
            most_stressed_agent_id=most_stressed_agent_id,
        )

    def _append_snapshot(self, snapshot: ColonySnapshot) -> ColonySnapshot:
        self.history.append(snapshot)
        if len(self.history) > MAX_HISTORY_LENGTH:
            del self.history[:-MAX_HISTORY_LENGTH]
        return snapshot

    def observe(self) -> Optional[ColonySnapshot]:
        """
        Collect one snapshot.

        Returns None when the current tick is not selected by observe_every_n_ticks.
        """
        self._tick_counter += 1
        if self._tick_counter % self.observe_every_n_ticks != 0:
            return None
        try:
            return self._append_snapshot(self._collect_snapshot(tick_number=self._tick_counter))
        except Exception:
            fallback = ColonySnapshot(
                sim_time=_safe_float(getattr(self.runner, "sim_time", 0.0), 0.0),
                tick_number=self._tick_counter,
            )
            return self._append_snapshot(fallback)

    def observe_force(self) -> ColonySnapshot:
        """Collect one snapshot regardless of tick filter."""
        self._tick_counter += 1
        try:
            return self._append_snapshot(self._collect_snapshot(tick_number=self._tick_counter))
        except Exception:
            fallback = ColonySnapshot(
                sim_time=_safe_float(getattr(self.runner, "sim_time", 0.0), 0.0),
                tick_number=self._tick_counter,
            )
            return self._append_snapshot(fallback)

    def observe_tick(self) -> Optional[ColonySnapshot]:
        """Convenience wrapper for invocation from external tick loop."""
        return self.observe()

    def get_latest(self) -> Optional[ColonySnapshot]:
        """Return latest snapshot or None."""
        return self.history[-1] if self.history else None

    def get_trend(self, field: str, last_n: int = 10) -> List[float]:
        """Return numeric trend for snapshot field over the last N snapshots."""
        if field not in self._snapshot_fields:
            return []
        count = max(0, _safe_int(last_n, 10))
        if count <= 0 or not self.history:
            return []
        values: list[float] = []
        for snapshot in self.history[-count:]:
            try:
                value = getattr(snapshot, field)
            except Exception:
                continue
            if isinstance(value, (int, float, bool)):
                values.append(_safe_float(value, 0.0))
        return values

    def get_population_peak(self) -> Optional[ColonySnapshot]:
        """Return snapshot with maximal population size."""
        if not self.history:
            return None
        return max(self.history, key=lambda item: _safe_int(getattr(item, "agent_count", 0), 0))

    def get_extinction_risk(self) -> float:
        """Estimate extinction risk in [0.0, 1.0] using weighted rule factors."""
        latest = self.get_latest()
        if latest is None:
            return 0.0

        score = 0.0
        if latest.agent_count <= 2:
            score += EXTINCTION_RISK_WEIGHTS["low_population"]
        if latest.agent_count > 0 and (latest.female_count == 0 or latest.male_count == 0):
            score += EXTINCTION_RISK_WEIGHTS["single_sex"]
        if latest.mean_stress > 0.7:
            score += EXTINCTION_RISK_WEIGHTS["high_stress"]
        available_food = max(
            _clamp(_safe_float(latest.food_pellets, 0.0), 0.0, 1.0),
            _clamp(_safe_float(latest.hay, 0.0), 0.0, 1.0),
        )
        if available_food < 0.1:
            score += EXTINCTION_RISK_WEIGHTS["food_critical"]

        if latest.pregnant_count <= 0 and not self._has_reproduction_potential(self._iter_agents()):
            score += EXTINCTION_RISK_WEIGHTS["no_reproduction"]

        if EXTINCTION_RISK_MAX_WEIGHT <= 0.0:
            return 0.0
        return _clamp(score / EXTINCTION_RISK_MAX_WEIGHT, 0.0, 1.0)

    def get_social_cohesion(self) -> float:
        """Return social cohesion index in [0.0, 1.0]."""
        latest = self.get_latest()
        if latest is None:
            return 0.0
        bonded_fraction = float(latest.bonded_pairs) / float(max(1, latest.total_known_pairs))
        affinity_term = (_clamp(latest.mean_affinity, -1.0, 1.0) + 1.0) / 2.0
        return _clamp(affinity_term * bonded_fraction, 0.0, 1.0)

    def to_dict(self) -> dict:
        """Serialize observer history into JSON-compatible dict."""
        return {
            "version": OBSERVER_VERSION,
            "snapshot_count": len(self.history),
            "snapshots": [asdict(item) for item in self.history],
        }

    def save(self, path: str) -> None:
        """Save observer history to JSON file."""
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as fp:
                json.dump(self.to_dict(), fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            warnings.warn(f"Failed to save colony observer history to '{path}': {exc}", stacklevel=2)

    def load(self, path: str) -> None:
        """Load observer history from JSON and append to existing history."""
        try:
            source = Path(path)
            with source.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except Exception as exc:
            warnings.warn(f"Failed to load colony observer history from '{path}': {exc}", stacklevel=2)
            return

        raw_snapshots: Any
        if isinstance(payload, dict):
            raw_snapshots = payload.get("snapshots", [])
        elif isinstance(payload, list):
            raw_snapshots = payload
        else:
            warnings.warn(f"Unexpected colony observer payload format in '{path}'", stacklevel=2)
            return

        if not isinstance(raw_snapshots, list):
            warnings.warn(f"Invalid snapshot list in '{path}'", stacklevel=2)
            return

        appended: list[ColonySnapshot] = []
        for item in raw_snapshots:
            if not isinstance(item, dict):
                continue
            clean = {key: item[key] for key in self._snapshot_fields if key in item}
            try:
                appended.append(ColonySnapshot(**clean))
            except Exception:
                continue

        if not appended and raw_snapshots:
            warnings.warn(f"No valid snapshots found in '{path}'", stacklevel=2)
            return

        self.history.extend(appended)
        if len(self.history) > MAX_HISTORY_LENGTH:
            del self.history[:-MAX_HISTORY_LENGTH]

        latest = self.get_latest()
        if latest is not None:
            self._tick_counter = max(self._tick_counter, _safe_int(latest.tick_number, 0))
            self._total_births_last = max(0, _safe_int(latest.total_births, 0))
            self._total_deaths_last = max(0, _safe_int(latest.total_deaths, 0))

    def clear(self) -> None:
        """Clear snapshot history and reset observer counters."""
        self.history.clear()
        self._tick_counter = 0
        self._total_births_last = 0
        self._total_deaths_last = 0
        self._prev_agent_ids = set()

    def summary_text(self) -> str:
        """Return compact text summary for latest snapshot."""
        latest = self.get_latest()
        if latest is None:
            return ""
        return (
            f"Colony: {latest.agent_count} agents ({latest.female_count}F/{latest.male_count}M) | "
            f"stress: {latest.mean_stress:.2f} | affinity: {latest.mean_affinity:.2f} | "
            f"births: {latest.total_births} deaths: {latest.total_deaths}"
        )


__all__ = [
    "OBSERVER_VERSION",
    "MAX_HISTORY_LENGTH",
    "EXTINCTION_RISK_WEIGHTS",
    "EXTINCTION_RISK_MAX_WEIGHT",
    "ColonySnapshot",
    "ColonyPopulationObserver",
    "_read_neuromodulator",
    "_read_affective_axis",
    "_collect_knowledge_stats",
    "_build_action_distribution",
    "_build_position_distribution",
]
