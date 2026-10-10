"""NOWA colony orchestration for Warriner validation stimuli."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ._common import (
    clamp,
    ensure_core_src_on_path,
    mean,
    normalize_warriner_records,
    normalize_word,
    population_sd,
)
from .hippocampus_seeder import HippocampusSeeder


ARCHETYPES = ("explorer", "passive", "resource_pragmatist", "anxious_loner")


@dataclass
class AgentResponse:
    agent_id: str
    archetype: str
    valence_before: float
    valence_after: float
    valence_shift: float
    arousal_shift: float
    da_delta: float
    ne_delta: float
    cortisol_delta: float
    serotonin_delta: float
    n_activated_memories: int
    stimulus_word: str
    raw_axes_before: dict
    raw_axes_after: dict


@dataclass
class ColonyResponse:
    word: str
    n_agents: int
    mean_valence_shift: float
    std_valence_shift: float
    mean_arousal_shift: float
    mean_da_delta: float
    mean_ne_delta: float
    mean_cortisol_delta: float
    mean_n_activated_memories: float
    per_archetype: Dict[str, float]
    agent_responses: List[AgentResponse]
    processing_time_s: float


class _SimpleAffectiveSpace:
    def __init__(self):
        self.axes = {
            "valence": 0.0,
            "arousal": 0.0,
            "dominance": 0.0,
            "stress": 0.0,
            "trust": 0.0,
            "curiosity": 0.0,
            "stability": 0.0,
            "attachment": 0.0,
        }
        self.last_axes = dict(self.axes)

    def step(self, inputs: Optional[Mapping[str, float]] = None, **_: Any) -> Dict[str, float]:
        self.last_axes = dict(self.axes)
        for axis, value in dict(inputs or {}).items():
            if axis in self.axes:
                self.axes[axis] = clamp(self.axes[axis] * 0.90 + float(value), -1.0, 1.0)
        if not inputs:
            for axis in self.axes:
                self.axes[axis] = clamp(self.axes[axis] * 0.90, -1.0, 1.0)
        return dict(self.axes)

    def snapshot(self) -> dict:
        return {"axes": dict(self.axes)}


class _SimpleNeuromodulators:
    dopamine = 0.1
    norepinephrine = 0.1
    serotonin = 0.1
    cortisol = 0.05

    def snapshot(self) -> dict:
        return {
            "dopamine": self.dopamine,
            "norepinephrine": self.norepinephrine,
            "serotonin": self.serotonin,
            "cortisol": self.cortisol,
        }


class _SimpleHippocampus:
    def __init__(self):
        self.experiences: List[Any] = []

    def store(self, path: Any, consequence: Any = None, intensity: float = 1.0, reward: float = 0.0, **_: Any) -> Any:
        exp = type("SimpleExperience", (), {})()
        exp.path = path
        exp.consequence = consequence
        exp.intensity = intensity
        exp.reward = reward
        exp.reinforcement_count = 1
        exp.activation_energy = 1.0
        self.experiences.append(exp)
        return exp

    def reinforce(self, path: Any, consequence: Any = None, intensity: float = 1.0) -> Any:
        del consequence, intensity
        target = set(_path_tokens(path))
        for exp in self.experiences:
            if set(_path_tokens(exp.path)) == target:
                exp.reinforcement_count += 1
                return exp
        return self.store(path)

    def activate(self, context_events: Sequence[str]) -> List[Any]:
        query = set(str(token) for token in context_events or [])
        if not query:
            return []
        return [
            exp
            for exp in self.experiences
            if query.intersection(set(_path_tokens(getattr(exp, "path", []))))
        ]


class _SimpleAgent:
    def __init__(self, agent_id: str, rng: random.Random):
        self.agent_id = agent_id
        self.hippocampus = _SimpleHippocampus()
        self.affective_space = _SimpleAffectiveSpace()
        self.neuromodulators = _SimpleNeuromodulators()
        self.genome = {
            "nm_acc_k_cort": rng.uniform(0.3, 1.2),
            "dr_curiosity_baseline": rng.uniform(0.05, 0.40),
        }
        self.affect_state = type(
            "SimpleAffectState",
            (),
            {"valence": 0.0, "arousal": 0.0, "threat": 0.0, "curiosity": 0.1},
        )()

    def step(self, context_events: Sequence[str], affective_inputs: Optional[dict] = None, **_: Any) -> str:
        del context_events
        self.affective_space.step(inputs=affective_inputs or {})
        valence = self.affective_space.axes.get("valence", 0.0)
        self.neuromodulators.dopamine = clamp(0.1 + max(0.0, valence) * 0.05, 0.0, 1.0)
        self.neuromodulators.cortisol = clamp(0.05 + max(0.0, -valence) * 0.05, 0.0, 1.0)
        self.neuromodulators.norepinephrine = clamp(
            0.1 + abs(self.affective_space.axes.get("arousal", 0.0)) * 0.04,
            0.0,
            1.0,
        )
        return "observe"


def _path_tokens(path: Any) -> List[str]:
    if hasattr(path, "signature"):
        try:
            return [str(token) for token in path.signature()]
        except Exception:
            return []
    if isinstance(path, (list, tuple, set)):
        return [str(token) for token in path]
    return [str(path)]


class NOWAColony:
    """Create agents, seed hippocampi, and aggregate stimulus responses."""

    def __init__(
        self,
        n_agents: int = 100,
        ticks_per_stimulus: int = 20,
        signal_ticks: int = 3,
        affective_gain: float = 1.8,
        memory_top_k: int = 3,
        memory_min_activation: float = 0.3,
        seed: int = 42,
    ):
        self.n_agents = max(1, int(n_agents))
        self.ticks_per_stimulus = max(1, int(ticks_per_stimulus))
        self.signal_ticks = max(1, min(int(signal_ticks), self.ticks_per_stimulus))
        self.affective_gain = max(0.1, float(affective_gain))
        self.memory_top_k = max(1, int(memory_top_k))
        self.memory_min_activation = clamp(float(memory_min_activation), 0.0, 1.0)
        self.seed = int(seed)
        self.rng = random.Random(seed)
        self.agents: List[Any] = []
        self.agent_archetypes: Dict[str, str] = {}
        self.seed_corpus: List[dict] = []
        self.backend_name = "uninitialized"
        self._baseline_states: Dict[str, dict] = {}
        self._seed_counts: Dict[str, int] = {}

    def initialize(
        self,
        warriner_df: Any,
        n_seed: int = 500,
        agent_factory: Any = None,
    ) -> None:
        """Spawn agents, assign archetypes, seed hippocampi, and capture baselines."""
        self.agents = []
        for index in range(self.n_agents):
            agent = self._spawn_agent(agent_factory, index)
            if not str(getattr(agent, "agent_id", "") or ""):
                try:
                    setattr(agent, "agent_id", f"agent_{index:04d}")
                except Exception:
                    pass
            self.agents.append(agent)
        self.agent_archetypes = self._assign_archetypes(self.agents)

        seed_rows = normalize_warriner_records(warriner_df)
        seeder = HippocampusSeeder(
            seed_rows,
            n_seed=min(max(0, int(n_seed)), len(seed_rows)),
            seed_strategy="stratified",
            rng=self.rng,
        )
        self.seed_corpus = seeder.build_seed_corpus()
        self._seed_counts = seeder.seed_colony(self.agents)
        self._baseline_states = {
            self._agent_id(agent, index): self._capture_baseline(agent)
            for index, agent in enumerate(self.agents)
        }

    def run_stimulus(self, context_events: List[str]) -> ColonyResponse:
        """Run a stimulus through the colony and aggregate per-agent responses."""
        start = time.perf_counter()
        word = self._stimulus_word(context_events)
        responses: List[AgentResponse] = []

        for index, agent in enumerate(self.agents):
            agent_id = self._agent_id(agent, index)
            self._reset_agent_affective_state(agent)
            axes_before = self._axes_snapshot(agent)
            nm_before = self._neuromodulator_snapshot(agent)

            active = self._activate_memories(agent, context_events)
            memory_v, memory_a, memory_d, memory_intensity = self._memory_signal(
                active,
                top_k=self.memory_top_k,
                min_activation=self.memory_min_activation,
            )
            affective_inputs = self._memory_affective_inputs(
                memory_v,
                memory_a,
                memory_d,
                gain=self.affective_gain,
            )
            novelty = 1.0 if not active else 0.0
            conflict = max(0.0, -memory_v) * 0.25

            for _ in range(self.signal_ticks):
                self._run_agent_step(
                    agent,
                    context_events=context_events,
                    memory_reward=memory_v,
                    affective_inputs=affective_inputs,
                    intensity=max(0.1, memory_intensity),
                    novelty=novelty,
                    conflict=conflict,
                )
            for _ in range(max(0, self.ticks_per_stimulus - self.signal_ticks)):
                self._tick_agent_decay(agent)

            axes_after = self._axes_snapshot(agent)
            nm_after = self._neuromodulator_snapshot(agent)
            valence_before = self._axis_valence(axes_before)
            valence_after = self._axis_valence(axes_after)
            arousal_before = float(axes_before.get("arousal", 0.0))
            arousal_after = float(axes_after.get("arousal", 0.0))

            responses.append(
                AgentResponse(
                    agent_id=agent_id,
                    archetype=self.agent_archetypes.get(agent_id, "unknown"),
                    valence_before=valence_before,
                    valence_after=valence_after,
                    valence_shift=valence_after - valence_before,
                    arousal_shift=arousal_after - arousal_before,
                    da_delta=self._nm_delta(nm_before, nm_after, "dopamine"),
                    ne_delta=self._nm_delta(nm_before, nm_after, "norepinephrine"),
                    cortisol_delta=self._nm_delta(nm_before, nm_after, "cortisol"),
                    serotonin_delta=self._nm_delta(nm_before, nm_after, "serotonin"),
                    n_activated_memories=len(active),
                    stimulus_word=word,
                    raw_axes_before=axes_before,
                    raw_axes_after=axes_after,
                )
            )

        valence_shifts = [item.valence_shift for item in responses]
        archetype_means = {}
        for archetype in ARCHETYPES:
            values = [item.valence_shift for item in responses if item.archetype == archetype]
            if values:
                archetype_means[archetype] = mean(values)

        return ColonyResponse(
            word=word,
            n_agents=len(responses),
            mean_valence_shift=mean(valence_shifts),
            std_valence_shift=population_sd(valence_shifts),
            mean_arousal_shift=mean(item.arousal_shift for item in responses),
            mean_da_delta=mean(item.da_delta for item in responses),
            mean_ne_delta=mean(item.ne_delta for item in responses),
            mean_cortisol_delta=mean(item.cortisol_delta for item in responses),
            mean_n_activated_memories=mean(item.n_activated_memories for item in responses),
            per_archetype=archetype_means,
            agent_responses=responses,
            processing_time_s=time.perf_counter() - start,
        )

    def _spawn_agent(self, agent_factory: Any, index: int) -> Any:
        agent_id = f"agent_{index:04d}"
        if agent_factory is not None:
            if callable(agent_factory):
                try:
                    return agent_factory(agent_id=agent_id, rng=self.rng, index=index)
                except TypeError:
                    try:
                        return agent_factory(agent_id)
                    except TypeError:
                        return agent_factory()
            if hasattr(agent_factory, "spawn_random"):
                return agent_factory.spawn_random(rng=self.rng, agent_id=agent_id)

        ensure_core_src_on_path()
        try:
            from agent_factory import AgentConfig, AgentFactory
        except Exception:
            self.backend_name = "simple_fallback"
            return _SimpleAgent(agent_id, self.rng)

        factory = AgentFactory(
            AgentConfig(
                actions=["approach", "avoid", "inspect", "rest"],
                hippocampus_capacity=4096,
                cortex_capacity=1024,
            )
        )
        self.backend_name = "core_agent_factory"
        return factory.spawn_random(rng=self.rng, agent_id=agent_id)

    def _assign_archetypes(self, agents: Sequence[Any]) -> Dict[str, str]:
        traits = []
        for index, agent in enumerate(agents):
            traits.append((self._agent_id(agent, index), self._trait(agent, "nm_acc_k_cort"), self._trait(agent, "dr_curiosity_baseline")))
        cort_median = self._median([item[1] for item in traits])
        curiosity_median = self._median([item[2] for item in traits])
        out = {}
        for agent_id, cort, curiosity in traits:
            high_cort = cort >= cort_median
            high_curiosity = curiosity >= curiosity_median
            if not high_cort and high_curiosity:
                archetype = "explorer"
            elif not high_cort and not high_curiosity:
                archetype = "passive"
            elif high_cort and high_curiosity:
                archetype = "resource_pragmatist"
            else:
                archetype = "anxious_loner"
            out[agent_id] = archetype
        return out

    @staticmethod
    def _median(values: Sequence[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(float(value) for value in values)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2.0

    @staticmethod
    def _trait(agent: Any, key: str) -> float:
        genome = getattr(agent, "genome", None)
        if isinstance(genome, Mapping):
            genes = genome.get("genes", genome)
            if key in genes:
                return float(genes[key])
        genes = getattr(genome, "genes", None)
        if isinstance(genes, Mapping) and key in genes:
            return float(genes[key])
        if key == "nm_acc_k_cort":
            nm = getattr(agent, "neuromodulators", None)
            return float(getattr(nm, "ACC_K_CORT", 0.7))
        return 0.18

    def _capture_baseline(self, agent: Any) -> dict:
        affect_state = getattr(agent, "affect_state", None)
        return {
            "axes": self._axes_snapshot(agent),
            "affect_state": {
                "valence": float(getattr(affect_state, "valence", 0.0)),
                "arousal": float(getattr(affect_state, "arousal", 0.0)),
                "threat": float(getattr(affect_state, "threat", 0.0)),
                "curiosity": float(getattr(affect_state, "curiosity", 0.0)),
            },
        }

    def _reset_agent_affective_state(self, agent: Any) -> None:
        agent_id = str(getattr(agent, "agent_id", "") or "")
        baseline = self._baseline_states.get(agent_id)
        if baseline is None:
            return
        space = getattr(agent, "affective_space", None)
        if space is not None and hasattr(space, "axes"):
            try:
                space.axes = dict(baseline.get("axes", {}))
                if hasattr(space, "last_axes"):
                    space.last_axes = dict(space.axes)
            except Exception:
                pass
        affect_state = getattr(agent, "affect_state", None)
        for key, value in dict(baseline.get("affect_state", {})).items():
            if hasattr(affect_state, key):
                try:
                    setattr(affect_state, key, float(value))
                except Exception:
                    pass

    @staticmethod
    def _activate_memories(agent: Any, context_events: Sequence[str]) -> List[Any]:
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None or not hasattr(hippocampus, "activate"):
            return []
        try:
            return list(hippocampus.activate(list(context_events or [])) or [])
        except Exception:
            return []

    @staticmethod
    def _memory_signal(
        active: Sequence[Any],
        top_k: int = 3,
        min_activation: float = 0.3,
    ) -> Tuple[float, float, float, float]:
        """Compute weighted VAD from the strongest activated episodes."""
        if not active:
            return 0.0, 0.5, 0.5, 0.0

        threshold = clamp(float(min_activation), 0.0, 1.0)
        filtered = [
            exp
            for exp in active
            if float(getattr(exp, "activation_energy", 1.0)) >= threshold
        ]
        if not filtered:
            filtered = sorted(
                active,
                key=lambda exp: float(getattr(exp, "activation_energy", 0.0)),
                reverse=True,
            )[:1]

        limit = max(1, int(top_k))
        strongest = sorted(
            filtered,
            key=lambda exp: (
                float(getattr(exp, "activation_energy", 1.0))
                * max(1.0, float(getattr(exp, "reinforcement_count", 1)))
            ),
            reverse=True,
        )[:limit]

        weighted_v = 0.0
        weighted_a = 0.0
        weighted_d = 0.0
        total = 0.0
        for exp in strongest:
            v = float(getattr(exp, "warriner_valence_norm", getattr(exp, "reward", 0.0)))
            a = float(getattr(exp, "warriner_arousal_norm", 0.5))
            d = float(getattr(exp, "warriner_dominance_norm", 0.5))
            weight = max(0.01, float(getattr(exp, "activation_energy", 1.0)))
            weight *= max(1.0, float(getattr(exp, "reinforcement_count", 1)))
            weighted_v += v * weight
            weighted_a += a * weight
            weighted_d += d * weight
            total += weight
        if total <= 0.0:
            return 0.0, 0.5, 0.5, 0.0
        v = clamp(weighted_v / total, -1.0, 1.0)
        a = clamp(weighted_a / total, 0.0, 1.0)
        d = clamp(weighted_d / total, 0.0, 1.0)
        return v, a, d, max(abs(v), abs((a * 2.0) - 1.0), 0.1)

    @staticmethod
    def _memory_affective_inputs(v: float, a: float, d: float, gain: float = 1.8) -> Dict[str, float]:
        """Map VAD memory signal into AffectiveSpace axes."""
        if abs(v) < 1e-12 and abs(a - 0.5) < 1e-12 and abs(d - 0.5) < 1e-12:
            return {}
        arousal_axis = (a * 2.0) - 1.0
        dominance_axis = (d * 2.0) - 1.0
        gain_value = max(0.1, float(gain))
        return {
            "valence": clamp(v * gain_value, -1.0, 1.0),
            "arousal": clamp(arousal_axis * gain_value * 0.70, -1.0, 1.0),
            "dominance": clamp(dominance_axis * gain_value * 0.50, -1.0, 1.0),
            "stress": clamp(max(0.0, -v) * gain_value * 0.60, -1.0, 1.0),
            "trust": clamp(max(0.0, v) * gain_value * 0.35, -1.0, 1.0),
            "curiosity": clamp(0.08 + (abs(arousal_axis) * 0.10 * gain_value), -1.0, 1.0),
            "stability": clamp(-max(0.0, -v) * gain_value * 0.20, -1.0, 1.0),
            "attachment": clamp(max(0.0, v) * gain_value * 0.15, -1.0, 1.0),
        }

    @staticmethod
    def _run_agent_step(
        agent: Any,
        context_events: Sequence[str],
        memory_reward: float,
        affective_inputs: Mapping[str, float],
        intensity: float,
        novelty: float,
        conflict: float,
    ) -> None:
        if not hasattr(agent, "step"):
            return
        try:
            agent.step(
                list(context_events or []),
                reward=float(memory_reward),
                intensity=float(intensity),
                novelty=float(novelty),
                conflict=float(conflict),
                affective_inputs=dict(affective_inputs or {}),
            )
        except TypeError:
            try:
                agent.step(list(context_events or []), affective_inputs=dict(affective_inputs or {}))
            except TypeError:
                agent.step(list(context_events or []))

    @staticmethod
    def _tick_agent_decay(agent: Any) -> None:
        space = getattr(agent, "affective_space", None)
        if space is None or not hasattr(space, "step"):
            return
        try:
            space.step(inputs={}, time_elapsed=1.0)
        except TypeError:
            space.step({})
        projector = getattr(agent, "_project_legacy_affect_from_affective_space", None)
        if callable(projector):
            try:
                projector(blend=1.0)
            except Exception:
                pass

    @staticmethod
    def _axes_snapshot(agent: Any) -> dict:
        space = getattr(agent, "affective_space", None)
        if space is None:
            return {}
        if hasattr(space, "snapshot"):
            try:
                snap = space.snapshot()
                axes = snap.get("axes", snap) if isinstance(snap, Mapping) else {}
                return {str(key): float(value) for key, value in dict(axes or {}).items()}
            except Exception:
                pass
        return {str(key): float(value) for key, value in dict(getattr(space, "axes", {}) or {}).items()}

    @staticmethod
    def _neuromodulator_snapshot(agent: Any) -> dict:
        nm = getattr(agent, "neuromodulators", None)
        if nm is None:
            return {}
        if hasattr(nm, "snapshot"):
            try:
                return dict(nm.snapshot() or {})
            except Exception:
                pass
        return {
            "dopamine": getattr(nm, "dopamine", 0.0),
            "norepinephrine": getattr(nm, "norepinephrine", 0.0),
            "serotonin": getattr(nm, "serotonin", 0.0),
            "cortisol": getattr(nm, "cortisol", 0.0),
        }

    @staticmethod
    def _axis_valence(axes: Mapping[str, float]) -> float:
        if "valence" in axes:
            return float(axes.get("valence", 0.0))
        return float(axes.get("pleasure", 0.0)) - float(axes.get("pain", 0.0))

    @staticmethod
    def _nm_delta(before: Mapping[str, Any], after: Mapping[str, Any], key: str) -> float:
        return float(after.get(key, 0.0)) - float(before.get(key, 0.0))

    @staticmethod
    def _stimulus_word(context_events: Sequence[str]) -> str:
        for event in context_events or []:
            token = str(event)
            if token.startswith("word:"):
                return normalize_word(token.split(":", 1)[1])
        return normalize_word(next(iter(context_events or [""]), ""))

    @staticmethod
    def _agent_id(agent: Any, index: int) -> str:
        return str(getattr(agent, "agent_id", "") or f"agent_{index:04d}")


__all__ = ["AgentResponse", "ColonyResponse", "NOWAColony", "ARCHETYPES"]
