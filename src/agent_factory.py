"""Factory helpers for evolutionary creation of NOWA agents."""

from __future__ import annotations

import random
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from affect import AffectiveState
from agent import Agent
from cortex import CortexMemory
from epigenome import EpigenomeSnapshot
from genome import GENE_REGISTRY, GenomeVector
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from mortality import BASE_LIFESPAN_STEPS, MortalitySystem
from reproduction import ReproductiveSystem
from selector import ActionSelector
from sleep import CorticalPattern, SleepManager
from wakefulness import WakefulnessState


def _safe_float(value: Any, fallback: float) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if casted != casted or casted in (float("inf"), float("-inf")):
        return float(fallback)
    return casted


def _clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, float(value)))


# Neuromodulator interaction matrix convention in NeuromodulatorField.update():
# interaction[target] += W[target][source] * centered[source]
# i.e. row = target modulator, column = source modulator.
_NM_GENE_MATRIX_INDEX = {
    "nm_da_ne_weight": (2, 0),   # DA -> NE
    "nm_ne_da_weight": (0, 2),   # NE -> DA
    "nm_da_ach_weight": (3, 0),  # DA -> ACh
    "nm_ach_da_weight": (0, 3),  # ACh -> DA
}
_NM_OVERRIDE_GENE_KEY = {
    "da_ne": "nm_da_ne_weight",
    "ne_da": "nm_ne_da_weight",
    "da_ach": "nm_da_ach_weight",
    "ach_da": "nm_ach_da_weight",
}


@dataclass
class AgentConfig:
    """Environment configuration independent from genome values."""

    actions: List[str]
    hippocampus_capacity: int = 512
    cortex_capacity: int = 256
    sleep_cycles_default: int = 3
    intent_memory_enabled: bool = True
    environment_id: str = ""
    base_lifespan_steps: int = BASE_LIFESPAN_STEPS


class AgentFactory:
    """Factory for creating NOWA agents from genome/epigenome data."""

    def __init__(self, config: AgentConfig):
        self.config = config

    def spawn(
        self,
        genome: GenomeVector,
        epigenome: Optional[EpigenomeSnapshot] = None,
        epigenome_noise: float = 0.1,
        rng: Optional[random.Random] = None,
        agent_id: str = "",
    ) -> Agent:
        """Create one ready-to-run agent instance."""
        generator = rng if rng is not None else random.Random()
        noise = _clamp(_safe_float(epigenome_noise, 0.1), 0.0, 1.0)
        safe_genome = genome if isinstance(genome, GenomeVector) else GenomeVector.default()
        params = safe_genome.to_agent_params()

        hippocampus = self._build_hippocampus(params)
        cortex = self._build_cortex(params)
        selector = self._build_selector(params)
        intent_memory = IntentMemory() if bool(self.config.intent_memory_enabled) else None
        sleep_manager = self._build_sleep_manager(params, hippocampus, cortex, intent_memory)
        affect_state = AffectiveState()
        agent = Agent(
            hippocampus,
            cortex,
            selector,
            sleep_manager=sleep_manager,
            intent_memory=intent_memory,
            affect_state=affect_state,
        )
        agent.wakefulness = self._build_wakefulness(params)
        self._apply_genome_to_agent(agent, params)
        for action in list(self.config.actions or []):
            action_name = str(action)
            if action_name and action_name not in agent.bg_action_channels:
                agent.register_action_channel(action_name)

        safe_epigenome = epigenome if isinstance(epigenome, EpigenomeSnapshot) else EpigenomeSnapshot.empty()
        agent.genome = safe_genome
        agent.epigenome = safe_epigenome if epigenome is not None else EpigenomeSnapshot.empty()
        agent.agent_id = str(agent_id)
        agent.lineage_id = str(agent_id)
        agent.factory_config = self.config
        agent.reproductive_system = ReproductiveSystem(
            drive_threshold=0.7,
            cooldown_duration=50,
        )
        mortality_params = (params or {}).get("mortality", {}) or {}
        lifespan_factor = _clamp(
            _safe_float(
                mortality_params.get(
                    "max_lifespan_factor",
                    safe_genome.genes.get("lt_max_lifespan_factor", 1.0),
                ),
                1.0,
            ),
            0.5,
            2.0,
        )
        base_lifespan = max(1, int(getattr(self.config, "base_lifespan_steps", BASE_LIFESPAN_STEPS)))
        max_lifespan_steps = max(1, int(base_lifespan * lifespan_factor))
        agent.mortality_system = MortalitySystem(max_lifespan_steps=max_lifespan_steps)
        agent.expected_lifetime_steps = max_lifespan_steps

        if epigenome is not None:
            self._inject_epigenome(agent, safe_epigenome, noise, generator)
        return agent

    def spawn_random(
        self,
        rng: Optional[random.Random] = None,
        agent_id: str = "",
    ) -> Agent:
        """Create a random genome first-generation agent."""
        generator = rng if rng is not None else random.Random()
        return self.spawn(
            genome=GenomeVector.random(generator),
            epigenome=None,
            epigenome_noise=0.1,
            rng=generator,
            agent_id=agent_id,
        )

    def spawn_default(
        self,
        agent_id: str = "",
    ) -> Agent:
        """Create an agent with default genome and empty epigenome."""
        return self.spawn(
            genome=GenomeVector.default(),
            epigenome=None,
            epigenome_noise=0.1,
            rng=None,
            agent_id=agent_id,
        )

    def spawn_child(
        self,
        parent_a: Agent,
        parent_b: Agent,
        mutation_rate: float = 0.05,
        sigma_scale: float = 1.0,
        crossover_alpha: float = 0.5,
        crossover_mode: str = "arithmetic",
        epigenome_noise: float = 0.1,
        blend_epigenomes: bool = True,
        rng: Optional[random.Random] = None,
        agent_id: str = "",
    ) -> Agent:
        """Create one child from two parent agents."""
        generator = rng if rng is not None else random.Random()
        mutation = _clamp(_safe_float(mutation_rate, 0.05), 0.0, 1.0)
        sigma = _clamp(_safe_float(sigma_scale, 1.0), 0.1, 5.0)
        alpha = _clamp(_safe_float(crossover_alpha, 0.5), 0.0, 1.0)
        mode = str(crossover_mode or "arithmetic").strip().lower()
        if mode not in {"arithmetic", "uniform", "sbx"}:
            mode = "arithmetic"

        genome_a = self.extract_genome(parent_a)
        genome_b = self.extract_genome(parent_b)
        try:
            child_genome, _ = genome_a.crossover(genome_b, alpha=alpha, mode=mode, rng=generator)
        except Exception:
            child_genome, _ = genome_a.crossover(genome_b, alpha=alpha, mode="arithmetic", rng=generator)
        child_genome = child_genome.mutate(rate=mutation, sigma_scale=sigma, rng=generator)

        child_epigenome = None
        if blend_epigenomes:
            epigenome_a = getattr(parent_a, "epigenome", EpigenomeSnapshot.empty())
            epigenome_b = getattr(parent_b, "epigenome", EpigenomeSnapshot.empty())
            if not isinstance(epigenome_a, EpigenomeSnapshot):
                epigenome_a = EpigenomeSnapshot.empty()
            if not isinstance(epigenome_b, EpigenomeSnapshot):
                epigenome_b = EpigenomeSnapshot.empty()
            try:
                child_epigenome = epigenome_a.blend(epigenome_b, alpha=alpha, rng=generator)
            except Exception:
                child_epigenome = EpigenomeSnapshot.empty()

        return self.spawn(
            genome=child_genome,
            epigenome=child_epigenome,
            epigenome_noise=epigenome_noise,
            rng=generator,
            agent_id=agent_id,
        )

    def extract_genome(self, agent: Agent) -> GenomeVector:
        """Extract stored genome or reconstruct it from agent state."""
        existing = getattr(agent, "genome", None)
        if isinstance(existing, GenomeVector):
            return existing
        if isinstance(existing, Mapping):
            return GenomeVector.from_dict({"genes": dict(existing)})
        return self._reconstruct_genome(agent)

    def extract_epigenome(
        self,
        agent: Agent,
        max_patterns: int = 32,
        max_actions: int = 16,
        max_values: int = 24,
        min_reinforcement: int = 2,
        min_stability: float = 0.5,
        min_confirmation: float = 1.0,
    ) -> EpigenomeSnapshot:
        """Extract epigenome snapshot from live agent public module state."""
        try:
            genome = self.extract_genome(agent)
            source_generation = int(getattr(genome, "generation", 0))
            source_lineage_id = str(getattr(genome, "lineage_id", ""))
            cortex_patterns = self._extract_cortex_patterns(getattr(agent, "cortex", None))
            action_metadata = self._extract_action_metadata(getattr(agent, "selector", None))
            value_profiles = self._extract_value_profiles(getattr(agent, "value_layer", None))
            return EpigenomeSnapshot.extract(
                cortex_patterns=cortex_patterns,
                action_metadata=action_metadata,
                value_profiles=value_profiles,
                source_generation=max(0, source_generation),
                source_lineage_id=source_lineage_id,
                max_patterns=max_patterns,
                max_actions=max_actions,
                max_values=max_values,
                min_reinforcement=min_reinforcement,
                min_stability=min_stability,
                min_confirmation=min_confirmation,
            )
        except Exception as exc:
            warnings.warn(
                f"Failed to extract epigenome snapshot: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return EpigenomeSnapshot.empty()

    def _build_hippocampus(self, params: dict) -> NOWAHippocampus:
        threshold = _safe_float(
            ((params or {}).get("hippocampus", {}) or {}).get(
                "similarity_threshold",
                GENE_REGISTRY["lr_similarity_threshold"].default,
            ),
            GENE_REGISTRY["lr_similarity_threshold"].default,
        )
        return NOWAHippocampus(
            max_experiences=max(1, int(self.config.hippocampus_capacity)),
            activation_similarity_threshold=_clamp(threshold, 0.0, 1.0),
        )

    def _build_cortex(self, params: dict) -> CortexMemory:
        del params
        cortex = CortexMemory()
        try:
            setattr(cortex, "capacity", max(1, int(self.config.cortex_capacity)))
        except Exception:
            pass
        return cortex

    def _build_selector(self, params: dict) -> ActionSelector:
        del params
        actions = [str(action) for action in list(self.config.actions or [])]
        return ActionSelector(actions=actions)

    def _build_sleep_manager(
        self,
        params: dict,
        hippocampus: NOWAHippocampus,
        cortex: CortexMemory,
        intent_memory: Optional[IntentMemory],
    ) -> SleepManager:
        manager = SleepManager(hippocampus, cortex, intent_memory=intent_memory)
        threshold = _safe_float(
            ((params or {}).get("sleep", {}) or {}).get(
                "consolidation_threshold",
                GENE_REGISTRY["lr_consolidation_threshold"].default,
            ),
            GENE_REGISTRY["lr_consolidation_threshold"].default,
        )
        manager.stability_index_threshold = _clamp(threshold, 0.0, 1.0)
        return manager

    def _build_wakefulness(self, params: dict) -> WakefulnessState:
        wakefulness_params = (params or {}).get("wakefulness", {}) or {}
        amplitude = _safe_float(
            wakefulness_params.get(
                "circadian_amplitude",
                GENE_REGISTRY["wk_circadian_amplitude"].default,
            ),
            GENE_REGISTRY["wk_circadian_amplitude"].default,
        )
        phase = _safe_float(
            wakefulness_params.get(
                "circadian_phase",
                GENE_REGISTRY["wk_circadian_phase"].default,
            ),
            GENE_REGISTRY["wk_circadian_phase"].default,
        )
        accumulation_factor = _safe_float(
            wakefulness_params.get(
                "accumulation_rate_factor",
                GENE_REGISTRY["wk_accumulation_factor"].default,
            ),
            GENE_REGISTRY["wk_accumulation_factor"].default,
        )
        recovery_factor = _safe_float(
            wakefulness_params.get(
                "recovery_rate_factor",
                GENE_REGISTRY["wk_recovery_factor"].default,
            ),
            GENE_REGISTRY["wk_recovery_factor"].default,
        )
        wakefulness = WakefulnessState(
            circadian_amplitude=max(0.0, amplitude),
            circadian_phase=phase,
        )
        wakefulness.accumulation_rate = max(
            0.0,
            float(WakefulnessState.ACCUMULATION_RATE) * max(0.0, accumulation_factor),
        )
        wakefulness.recovery_rate = max(
            0.0,
            float(WakefulnessState.RECOVERY_RATE) * max(0.0, recovery_factor),
        )
        return wakefulness

    def _apply_genome_to_agent(self, agent: Agent, params: dict) -> None:
        """Apply genome-defined runtime overrides after base initialization."""

        def _warn_and_continue(label: str, fn) -> None:
            try:
                fn()
            except Exception as exc:
                warnings.warn(
                    f"Skipped applying genome parameter '{label}': {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )

        affective_params = (params or {}).get("affective_space", {}) or {}
        _warn_and_continue(
            "affective_space.axis_decay",
            lambda: agent.affective_space.axis_decay.update(
                {
                    str(axis): _safe_float(value, 0.9)
                    for axis, value in dict(affective_params.get("axis_decay", {}) or {}).items()
                }
            ),
        )
        _warn_and_continue(
            "affective_space.lambda_reg",
            lambda: setattr(
                agent.affective_space,
                "lambda_reg",
                _safe_float(
                    affective_params.get("lambda_reg", GENE_REGISTRY["af_lambda_reg"].default),
                    GENE_REGISTRY["af_lambda_reg"].default,
                ),
            ),
        )
        _warn_and_continue(
            "affective_space.baseline_adapt_rate",
            lambda: setattr(
                agent.affective_space,
                "baseline_adapt_rate",
                _safe_float(
                    affective_params.get(
                        "baseline_adapt_rate",
                        GENE_REGISTRY["af_baseline_adapt_rate"].default,
                    ),
                    GENE_REGISTRY["af_baseline_adapt_rate"].default,
                ),
            ),
        )

        neuromod_params = (params or {}).get("neuromodulators", {}) or {}
        overrides = dict(neuromod_params.get("interaction_overrides", {}) or {})
        _warn_and_continue(
            "neuromodulators.interaction_overrides",
            lambda: self._apply_neuromodulator_overrides(agent, overrides),
        )
        _warn_and_continue(
            "neuromodulators.acc_k_ne",
            lambda: setattr(
                agent.neuromodulators,
                "ACC_K_NE",
                _safe_float(
                    neuromod_params.get("acc_k_ne", GENE_REGISTRY["nm_acc_k_ne"].default),
                    GENE_REGISTRY["nm_acc_k_ne"].default,
                ),
            ),
        )
        _warn_and_continue(
            "neuromodulators.acc_k_cort",
            lambda: setattr(
                agent.neuromodulators,
                "ACC_K_CORT",
                _safe_float(
                    neuromod_params.get("acc_k_cort", GENE_REGISTRY["nm_acc_k_cort"].default),
                    GENE_REGISTRY["nm_acc_k_cort"].default,
                ),
            ),
        )
        _warn_and_continue(
            "neuromodulators.acc_k_ht",
            lambda: setattr(
                agent.neuromodulators,
                "ACC_K_HT_INHIBITION",
                _safe_float(
                    neuromod_params.get("acc_k_ht", GENE_REGISTRY["nm_acc_k_ht"].default),
                    GENE_REGISTRY["nm_acc_k_ht"].default,
                ),
            ),
        )
        _warn_and_continue(
            "neuromodulators.decay_half_life",
            lambda: setattr(
                agent.neuromodulators,
                "DECAY_HALF_LIFE",
                _safe_float(
                    neuromod_params.get(
                        "decay_half_life",
                        GENE_REGISTRY["nm_decay_half_life"].default,
                    ),
                    GENE_REGISTRY["nm_decay_half_life"].default,
                ),
            ),
        )

        value_params = (params or {}).get("value_layer", {}) or {}
        _warn_and_continue(
            "value_layer.gamma_default",
            lambda: setattr(
                agent.value_layer,
                "gamma_default",
                _safe_float(
                    value_params.get("gamma_default", GENE_REGISTRY["lr_gamma"].default),
                    GENE_REGISTRY["lr_gamma"].default,
                ),
            ),
        )
        _warn_and_continue(
            "value_layer.alpha_online_default",
            lambda: setattr(
                agent.value_layer,
                "alpha_online_default",
                _safe_float(
                    value_params.get("alpha_online_default", GENE_REGISTRY["lr_alpha_online"].default),
                    GENE_REGISTRY["lr_alpha_online"].default,
                ),
            ),
        )
        _warn_and_continue(
            "value_layer.alpha_default",
            lambda: setattr(agent.value_layer, "alpha_default", float(agent.value_layer.alpha_online_default)),
        )
        _warn_and_continue(
            "value_layer.td_layer.tonic_slow_rate",
            lambda: setattr(
                agent.value_layer.td_layer,
                "tonic_slow_rate",
                _safe_float(
                    value_params.get("tonic_slow_rate", GENE_REGISTRY["lr_tonic_slow_rate"].default),
                    GENE_REGISTRY["lr_tonic_slow_rate"].default,
                ),
            ),
        )

        imagination_params = (params or {}).get("imagination", {}) or {}
        _warn_and_continue(
            "imagination.goal_bias",
            lambda: setattr(
                agent.imagination_engine,
                "goal_bias",
                _safe_float(
                    imagination_params.get("goal_bias", GENE_REGISTRY["im_goal_bias"].default),
                    GENE_REGISTRY["im_goal_bias"].default,
                ),
            ),
        )
        _warn_and_continue(
            "imagination.confidence_decay",
            lambda: setattr(
                agent.imagination_engine,
                "confidence_decay",
                _safe_float(
                    imagination_params.get("confidence_decay", GENE_REGISTRY["im_confidence_decay"].default),
                    GENE_REGISTRY["im_confidence_decay"].default,
                ),
            ),
        )
        _warn_and_continue(
            "imagination.state_novelty_weight",
            lambda: setattr(
                agent.imagination_engine,
                "state_novelty_weight",
                _safe_float(
                    imagination_params.get("state_novelty_weight", GENE_REGISTRY["im_novelty_weight"].default),
                    GENE_REGISTRY["im_novelty_weight"].default,
                ),
            ),
        )
        _warn_and_continue(
            "imagination.value_blend",
            lambda: setattr(
                agent,
                "imagination_value_blend",
                _safe_float(
                    imagination_params.get("value_blend", GENE_REGISTRY["im_value_blend"].default),
                    GENE_REGISTRY["im_value_blend"].default,
                ),
            ),
        )

        autonomous_params = (params or {}).get("autonomous", {}) or {}
        _warn_and_continue(
            "autonomous.init_runtime",
            lambda: self._apply_autonomous_params(agent, autonomous_params),
        )

    def _inject_epigenome(
        self,
        agent: Agent,
        epigenome: EpigenomeSnapshot,
        noise_level: float,
        rng: Optional[random.Random],
    ) -> dict:
        """Inject inherited memory while keeping agent stable on failures."""
        empty_stats = {
            "patterns_injected": 0,
            "patterns_skipped": 0,
            "actions_injected": 0,
            "actions_skipped": 0,
            "values_injected": 0,
            "values_skipped": 0,
            "noise_level": _clamp(_safe_float(noise_level, 0.1), 0.0, 1.0),
        }
        if not isinstance(epigenome, EpigenomeSnapshot):
            return empty_stats

        generator = rng if rng is not None else random.Random()
        try:
            cortex_patterns = self._extract_cortex_patterns(getattr(agent, "cortex", None))
            action_metadata = self._extract_action_metadata(getattr(agent, "selector", None))
            value_profiles = self._extract_value_profiles(getattr(agent, "value_layer", None))
            stats = epigenome.inject(
                target_cortex_patterns=cortex_patterns,
                target_action_metadata=action_metadata,
                target_value_profiles=value_profiles,
                noise_level=_clamp(_safe_float(noise_level, 0.1), 0.0, 1.0),
                rng=generator,
            )
            self._apply_cortex_patterns(getattr(agent, "cortex", None), cortex_patterns)
            self._apply_action_metadata(getattr(agent, "selector", None), action_metadata)
            self._apply_value_profiles(getattr(agent, "value_layer", None), value_profiles)
            if isinstance(stats, Mapping):
                merged_stats = dict(empty_stats)
                merged_stats.update(dict(stats))
                return merged_stats
            return empty_stats
        except Exception as exc:
            warnings.warn(
                f"Epigenome injection failed, keeping agent state unchanged: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return empty_stats

    def _reconstruct_genome(self, agent: Agent) -> GenomeVector:
        """Rebuild a valid genome from current live module parameters."""
        genes = {key: descriptor.default for key, descriptor in GENE_REGISTRY.items()}

        def _set_gene(gene_key: str, value: Any) -> None:
            descriptor = GENE_REGISTRY[gene_key]
            genes[gene_key] = _clamp(
                _safe_float(value, descriptor.default),
                descriptor.min_val,
                descriptor.max_val,
            )

        try:
            matrix = None
            neuromodulators = getattr(agent, "neuromodulators", None)
            if neuromodulators is not None:
                field = getattr(neuromodulators, "interaction_field", None)
                if field is None and hasattr(neuromodulators, "_sync_field_from_state"):
                    neuromodulators._sync_field_from_state()
                    field = getattr(neuromodulators, "interaction_field", None)
                if field is not None:
                    matrix = [list(row) for row in list(getattr(field, "INTERACTION_MATRIX", ()) or ())]
            if matrix and len(matrix) >= 4 and all(len(row) >= 4 for row in matrix):
                for gene_key, (row_idx, col_idx) in _NM_GENE_MATRIX_INDEX.items():
                    _set_gene(gene_key, matrix[row_idx][col_idx])
            if neuromodulators is not None:
                _set_gene("nm_acc_k_ne", getattr(neuromodulators, "ACC_K_NE", genes["nm_acc_k_ne"]))
                _set_gene("nm_acc_k_cort", getattr(neuromodulators, "ACC_K_CORT", genes["nm_acc_k_cort"]))
                _set_gene(
                    "nm_acc_k_ht",
                    getattr(neuromodulators, "ACC_K_HT_INHIBITION", genes["nm_acc_k_ht"]),
                )
                _set_gene(
                    "nm_decay_half_life",
                    getattr(neuromodulators, "DECAY_HALF_LIFE", genes["nm_decay_half_life"]),
                )
        except Exception:
            pass

        try:
            affective_space = getattr(agent, "affective_space", None)
            if affective_space is not None:
                axis_decay = dict(getattr(affective_space, "axis_decay", {}) or {})
                _set_gene("af_decay_valence", axis_decay.get("valence", genes["af_decay_valence"]))
                _set_gene("af_decay_arousal", axis_decay.get("arousal", genes["af_decay_arousal"]))
                _set_gene("af_decay_dominance", axis_decay.get("dominance", genes["af_decay_dominance"]))
                _set_gene("af_decay_stress", axis_decay.get("stress", genes["af_decay_stress"]))
                _set_gene("af_decay_curiosity", axis_decay.get("curiosity", genes["af_decay_curiosity"]))
                _set_gene("af_decay_trust", axis_decay.get("trust", genes["af_decay_trust"]))
                _set_gene(
                    "af_decay_attachment",
                    axis_decay.get("attachment", genes["af_decay_attachment"]),
                )
                _set_gene("af_lambda_reg", getattr(affective_space, "lambda_reg", genes["af_lambda_reg"]))
                _set_gene(
                    "af_baseline_adapt_rate",
                    getattr(affective_space, "baseline_adapt_rate", genes["af_baseline_adapt_rate"]),
                )
        except Exception:
            pass

        try:
            wakefulness = getattr(agent, "wakefulness", None)
            if wakefulness is not None:
                _set_gene(
                    "wk_circadian_amplitude",
                    getattr(wakefulness, "circadian_amplitude", genes["wk_circadian_amplitude"]),
                )
                _set_gene(
                    "wk_circadian_phase",
                    getattr(wakefulness, "circadian_phase", genes["wk_circadian_phase"]),
                )
                base_acc = max(1e-9, float(WakefulnessState.ACCUMULATION_RATE))
                base_rec = max(1e-9, float(WakefulnessState.RECOVERY_RATE))
                _set_gene(
                    "wk_accumulation_factor",
                    _safe_float(getattr(wakefulness, "accumulation_rate", base_acc), base_acc) / base_acc,
                )
                _set_gene(
                    "wk_recovery_factor",
                    _safe_float(getattr(wakefulness, "recovery_rate", base_rec), base_rec) / base_rec,
                )
        except Exception:
            pass

        try:
            runtime = getattr(agent, "autonomous_runtime", None)
            if runtime is not None:
                drives = dict(getattr(runtime.drive_system, "drives", {}) or {})
                _set_gene("dr_curiosity_baseline", drives.get("curiosity", genes["dr_curiosity_baseline"]))
                _set_gene("dr_social_drive_baseline", drives.get("social_drive", genes["dr_social_drive_baseline"]))
                _set_gene("dr_exploration_baseline", drives.get("exploration", genes["dr_exploration_baseline"]))
                thresholds = dict(getattr(runtime.hard_limits, "drive_thresholds", {}) or {})
                _set_gene("dr_curiosity_threshold", thresholds.get("curiosity", genes["dr_curiosity_threshold"]))
                _set_gene("dr_social_threshold", thresholds.get("social_drive", genes["dr_social_threshold"]))
                _set_gene(
                    "dr_energy_recovery_rate",
                    getattr(runtime.energy_system, "recovery_rate", genes["dr_energy_recovery_rate"]),
                )
                _set_gene(
                    "dr_cognitive_cost",
                    getattr(runtime.energy_system, "cognitive_cost", genes["dr_cognitive_cost"]),
                )
        except Exception:
            pass

        try:
            value_layer = getattr(agent, "value_layer", None)
            if value_layer is not None:
                _set_gene("lr_gamma", getattr(value_layer, "gamma_default", genes["lr_gamma"]))
                _set_gene(
                    "lr_alpha_online",
                    getattr(value_layer, "alpha_online_default", genes["lr_alpha_online"]),
                )
                td_layer = getattr(value_layer, "td_layer", None)
                if td_layer is not None:
                    _set_gene(
                        "lr_tonic_slow_rate",
                        getattr(td_layer, "tonic_slow_rate", genes["lr_tonic_slow_rate"]),
                    )
        except Exception:
            pass

        try:
            hippocampus = getattr(agent, "hippocampus", None)
            if hippocampus is not None:
                _set_gene(
                    "lr_similarity_threshold",
                    getattr(hippocampus, "activation_similarity_threshold", genes["lr_similarity_threshold"]),
                )
        except Exception:
            pass

        try:
            sleep_manager = getattr(agent, "sleep_manager", None)
            if sleep_manager is not None:
                _set_gene(
                    "lr_consolidation_threshold",
                    getattr(sleep_manager, "stability_index_threshold", genes["lr_consolidation_threshold"]),
                )
        except Exception:
            pass

        try:
            imagination_engine = getattr(agent, "imagination_engine", None)
            if imagination_engine is not None:
                _set_gene("im_goal_bias", getattr(imagination_engine, "goal_bias", genes["im_goal_bias"]))
                _set_gene(
                    "im_confidence_decay",
                    getattr(imagination_engine, "confidence_decay", genes["im_confidence_decay"]),
                )
                _set_gene(
                    "im_novelty_weight",
                    getattr(imagination_engine, "state_novelty_weight", genes["im_novelty_weight"]),
                )
            _set_gene("im_value_blend", getattr(agent, "imagination_value_blend", genes["im_value_blend"]))
        except Exception:
            pass

        existing = getattr(agent, "genome", None)
        generation = int(getattr(existing, "generation", 0)) if isinstance(existing, GenomeVector) else 0
        lineage_id = ""
        if isinstance(existing, GenomeVector):
            lineage_id = str(getattr(existing, "lineage_id", ""))
        if not lineage_id:
            lineage_id = str(getattr(agent, "lineage_id", ""))

        return GenomeVector(
            genes=genes,
            generation=max(0, generation),
            lineage_id=lineage_id,
        )

    def _apply_neuromodulator_overrides(self, agent: Agent, overrides: Mapping[str, Any]) -> None:
        neuromodulators = getattr(agent, "neuromodulators", None)
        if neuromodulators is None:
            return
        if hasattr(neuromodulators, "_sync_field_from_state"):
            neuromodulators._sync_field_from_state()
        field = getattr(neuromodulators, "interaction_field", None)
        if field is None:
            return

        matrix = [list(row) for row in list(getattr(field, "INTERACTION_MATRIX", ()) or ())]
        if len(matrix) < 4 or any(len(row) < 4 for row in matrix):
            return

        for override_key, gene_key in _NM_OVERRIDE_GENE_KEY.items():
            if override_key not in overrides:
                continue
            row_idx, col_idx = _NM_GENE_MATRIX_INDEX[gene_key]
            matrix[row_idx][col_idx] = _safe_float(overrides.get(override_key), matrix[row_idx][col_idx])
        field.INTERACTION_MATRIX = tuple(tuple(float(cell) for cell in row) for row in matrix)

    def _apply_autonomous_params(self, agent: Agent, autonomous_params: Mapping[str, Any]) -> None:
        thresholds = {
            str(key): _safe_float(value, 0.5)
            for key, value in dict(autonomous_params.get("drive_thresholds", {}) or {}).items()
        }
        runtime = agent.init_autonomous_runtime(drive_thresholds=thresholds or None)
        if runtime is None:
            return

        drive_baselines = dict(autonomous_params.get("drive_baselines", {}) or {})
        for name, value in drive_baselines.items():
            if hasattr(runtime, "drive_system") and hasattr(runtime.drive_system, "set_drive"):
                runtime.drive_system.set_drive(str(name), _safe_float(value, 0.0))

        if hasattr(runtime, "hard_limits"):
            current = dict(getattr(runtime.hard_limits, "drive_thresholds", {}) or {})
            current.update({str(k): _safe_float(v, 0.5) for k, v in thresholds.items()})
            runtime.hard_limits.drive_thresholds = current

        if hasattr(runtime, "energy_system"):
            if "energy_recovery_rate" in autonomous_params:
                runtime.energy_system.recovery_rate = max(
                    0.0,
                    _safe_float(
                        autonomous_params.get("energy_recovery_rate"),
                        runtime.energy_system.recovery_rate,
                    ),
                )
            if "cognitive_cost" in autonomous_params:
                runtime.energy_system.cognitive_cost = max(
                    0.0,
                    _safe_float(
                        autonomous_params.get("cognitive_cost"),
                        runtime.energy_system.cognitive_cost,
                    ),
                )

    def _extract_cortex_patterns(self, cortex: Any) -> List[dict]:
        rows: List[dict] = []
        raw_patterns = []
        if cortex is not None:
            raw_patterns = list(getattr(cortex, "patterns", []) or [])
        for pattern in raw_patterns:
            if isinstance(pattern, Mapping):
                context_signature = str(pattern.get("context_signature", "")).strip()
                if not context_signature:
                    continue
                rows.append(
                    {
                        "context_signature": context_signature,
                        "action": str(pattern.get("action", "")).strip(),
                        "strength": _safe_float(pattern.get("strength"), 0.0),
                        "reinforcement_count": max(
                            0,
                            int(_safe_float(pattern.get("reinforcement_count"), 0.0)),
                        ),
                    }
                )
                continue

            signature = tuple(getattr(pattern, "signature", ()) or ())
            signature_tokens = [str(token) for token in signature]
            context_tokens = [token for token in signature_tokens if not token.startswith("action:")]
            action_tokens = [token for token in signature_tokens if token.startswith("action:")]
            context_signature = "|".join(context_tokens).strip()
            if not context_signature and signature_tokens:
                context_signature = signature_tokens[0]
            if not context_signature:
                continue
            action = action_tokens[-1][7:] if action_tokens else ""
            reinforcement = max(
                int(_safe_float(getattr(pattern, "source_experiences", 0), 0.0)),
                int(_safe_float(getattr(pattern, "activation_count", 0), 0.0)),
            )
            rows.append(
                {
                    "context_signature": context_signature,
                    "action": action,
                    "strength": _safe_float(getattr(pattern, "strength", 0.0), 0.0),
                    "reinforcement_count": max(0, reinforcement),
                }
            )
        return rows

    def _apply_cortex_patterns(self, cortex: Any, cortex_patterns: List[dict]) -> None:
        if cortex is None:
            return
        materialized = []
        for row in list(cortex_patterns or []):
            if not isinstance(row, Mapping):
                continue
            context_signature = str(row.get("context_signature", "")).strip()
            if not context_signature:
                continue
            action = str(row.get("action", "")).strip()
            signature = (
                (context_signature, f"action:{action}")
                if action
                else (context_signature,)
            )
            reinforcement = max(1, int(_safe_float(row.get("reinforcement_count"), 1.0)))
            pattern = CorticalPattern(signature=signature, source_experiences=reinforcement)
            pattern.strength = _safe_float(row.get("strength"), pattern.strength)
            pattern.activation_count = max(0, int(_safe_float(row.get("reinforcement_count"), 0.0)))
            materialized.append(pattern)
        setattr(cortex, "patterns", materialized)

    def _extract_action_metadata(self, selector: Any) -> Dict[str, dict]:
        rows: Dict[str, dict] = {}
        metadata = {}
        if selector is not None and isinstance(getattr(selector, "action_metadata", None), Mapping):
            metadata = dict(getattr(selector, "action_metadata", {}) or {})
        for action_name, payload in metadata.items():
            if not isinstance(payload, Mapping):
                continue
            predicted_effect = self._flatten_predicted_effect(payload.get("predicted_effect", {}))
            success_alpha = _safe_float(payload.get("success_alpha"), 1.0)
            success_beta = _safe_float(payload.get("success_beta"), 1.0)
            success_rate = _safe_float(payload.get("success_rate"), success_alpha / max(1e-6, success_alpha + success_beta))
            rows[str(action_name)] = {
                "predicted_effect": predicted_effect,
                "semantic_confidence": _clamp(
                    _safe_float(payload.get("semantic_confidence", payload.get("confidence", 0.0)), 0.0),
                    0.0,
                    1.0,
                ),
                "stability_score": _clamp(
                    _safe_float(payload.get("stability_score", payload.get("stability", 0.0)), 0.0),
                    0.0,
                    1.0,
                ),
                "success_rate": _clamp(success_rate, 0.0, 1.0),
                "consolidated": bool(payload.get("consolidated", payload.get("consolidation_flag", False))),
            }
        return rows

    def _apply_action_metadata(self, selector: Any, action_metadata: Mapping[str, dict]) -> None:
        if selector is None:
            return
        if hasattr(selector, "set_action_metadata"):
            for action_name, payload in dict(action_metadata or {}).items():
                selector.set_action_metadata(str(action_name), dict(payload or {}))
            return
        if not isinstance(getattr(selector, "action_metadata", None), Mapping):
            setattr(selector, "action_metadata", {})
        for action_name, payload in dict(action_metadata or {}).items():
            selector.action_metadata[str(action_name)] = dict(payload or {})

    def _extract_value_profiles(self, value_layer: Any) -> Dict[str, dict]:
        rows: Dict[str, dict] = {}
        expectation_memory = {}
        if value_layer is not None and isinstance(getattr(value_layer, "expectation_memory", None), Mapping):
            expectation_memory = dict(getattr(value_layer, "expectation_memory", {}) or {})
        for state_key, payload in expectation_memory.items():
            if not isinstance(payload, Mapping):
                continue
            value = _safe_float(
                payload.get("predicted_value", payload.get("expected_reward_mean", payload.get("value", 0.0))),
                0.0,
            )
            confidence = _safe_float(payload.get("confidence_score", payload.get("confidence", 0.0)), 0.0)
            rows[str(state_key)] = {
                "value": _clamp(value, -1.0, 1.0),
                "confidence": _clamp(confidence, 0.0, 1.0),
                "confirmation_count": max(0.0, _safe_float(payload.get("confirmation_count"), 0.0)),
            }
        return rows

    def _apply_value_profiles(self, value_layer: Any, value_profiles: Mapping[str, dict]) -> None:
        if value_layer is None:
            return
        if not isinstance(getattr(value_layer, "expectation_memory", None), Mapping):
            setattr(value_layer, "expectation_memory", {})
        if not isinstance(getattr(value_layer, "values", None), Mapping):
            setattr(value_layer, "values", {})

        for state_key, payload in dict(value_profiles or {}).items():
            if not isinstance(payload, Mapping):
                continue
            value = _clamp(_safe_float(payload.get("value"), 0.0), -1.0, 1.0)
            confidence = _clamp(_safe_float(payload.get("confidence"), 0.0), 0.0, 1.0)
            confirmation_count = max(0.0, _safe_float(payload.get("confirmation_count"), 0.0))
            current = value_layer.expectation_memory.get(str(state_key), {})
            if not isinstance(current, Mapping):
                current = {}
            merged = dict(current)
            merged.update(
                {
                    "value": value,
                    "expected_reward_mean": value,
                    "predicted_value": value,
                    "confidence": confidence,
                    "confidence_score": confidence,
                    "confirmation_count": confirmation_count,
                    "stability_score": _clamp(
                        _safe_float(merged.get("stability_score"), confidence),
                        0.0,
                        1.0,
                    ),
                }
            )
            value_layer.expectation_memory[str(state_key)] = merged
            value_layer.values[str(state_key)] = value

    def _flatten_predicted_effect(self, payload: Any) -> Dict[str, float]:
        flattened: Dict[str, float] = {}
        if not isinstance(payload, Mapping):
            return flattened
        raw = dict(payload or {})
        axes = raw.get("axes", {})
        drives = raw.get("drives", {})
        if isinstance(axes, Mapping):
            for axis, value in axes.items():
                flattened[f"axis:{axis}"] = _safe_float(value, 0.0)
        if isinstance(drives, Mapping):
            for drive, value in drives.items():
                flattened[f"drive:{drive}"] = _safe_float(value, 0.0)
        for key, value in raw.items():
            if key in {"axes", "drives"}:
                continue
            try:
                flattened[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        return flattened


__all__ = ["AgentConfig", "AgentFactory"]
