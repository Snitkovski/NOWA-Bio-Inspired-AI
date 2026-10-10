"""Read-only analytics snapshot builder for the colony swarm overlay."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from .genome_portrait import GENE_REGISTRY
from .nowa_interpreter import (
    AffectInterpretation,
    NeuroProfile,
    build_personality_readout,
    interpret_affect,
    interpret_neuro,
)


@dataclass
class GenerationSummary:
    """Aggregate over one generation, from living agents plus memorials."""

    generation: int
    agent_count: int
    alive_count: int
    dead_count: int
    mean_lived_steps: float
    mean_stress_at_death: float
    mean_cortisol_at_death: float
    mean_energy_at_death: float
    mean_vitality_at_death: float
    cause_distribution: dict[str, int]
    mean_genome: dict[str, float]
    genome_std: dict[str, float]
    total_offspring: int
    mean_total_offspring: float


@dataclass
class GeneEvolutionTrack:
    """Evolutionary track for one gene across generations."""

    gene_key: str
    group: str
    values_by_gen: dict[int, float]
    std_by_gen: dict[int, float]
    trend_label: str
    trend_magnitude: float
    interpretation: str
    is_under_selection: bool


@dataclass
class BehaviorPattern:
    """Action or population-level behavior frequency."""

    action: str
    count: int
    fraction: float
    label_ru: str


@dataclass
class SocialStructure:
    """Current colony social structure."""

    total_known_pairs: int
    bonded_pairs: int
    rival_pairs: int
    kin_pairs: int
    mean_affinity: float
    cohesion_index: float
    isolation_count: int


@dataclass
class ColonyHealthIndex:
    """Integral colony health index in [0, 1]."""

    overall: float
    components: dict[str, float]
    verdict: str
    color: tuple[int, int, int]


@dataclass
class EvolutionaryForecast:
    """Forecast built from current and evolutionary trends."""

    extinction_risk: float
    extinction_risk_label: str
    dominant_pressure: str
    adapting_traits: list[str]
    stagnant_traits: list[str]
    key_risks: list[str]
    key_opportunities: list[str]
    summary: str


@dataclass
class SwarmAnalytics:
    """Full analytical snapshot of the colony."""

    snapshot_time: float
    total_ever_lived: int
    living_count: int
    dead_count: int
    generation_range: tuple[int, int]
    generation_summaries: list[GenerationSummary]
    gene_tracks: list[GeneEvolutionTrack]
    most_evolved_genes: list[str]
    most_stable_genes: list[str]
    current_action_distribution: list[BehaviorPattern]
    current_social: SocialStructure
    health_index: ColonyHealthIndex
    observer_stress_trend: list[float]
    observer_energy_trend: list[float]
    observer_population_trend: list[float]
    observer_cohesion_trend: list[float]
    forecast: EvolutionaryForecast
    resources: dict[str, float] = field(default_factory=dict)
    current_metrics: dict[str, float] = field(default_factory=dict)
    personality_distribution: list[BehaviorPattern] = field(default_factory=list)
    dominant_habits: list[BehaviorPattern] = field(default_factory=list)
    mean_hippocampus_size: float = 0.0
    std_hippocampus_size: float = 0.0
    mean_cortex_patterns: float = 0.0
    std_cortex_patterns: float = 0.0


TRACKED_GENE_GROUPS: dict[str, list[str]] = {
    "af": ["af_decay_stress", "af_decay_curiosity", "af_decay_attachment", "af_decay_trust", "af_lambda_reg"],
    "nm": ["nm_acc_k_cort", "nm_acc_k_ht", "nm_decay_half_life"],
    "wk": ["wk_recovery_factor", "wk_accumulation_factor"],
    "dr": ["dr_social_drive_baseline", "dr_curiosity_baseline", "dr_perception_radius_factor"],
    "lr": ["lr_alpha", "lr_gamma"],
    "lt": ["lt_max_lifespan_factor"],
}
ALL_TRACKED_GENES = [gene for genes in TRACKED_GENE_GROUPS.values() for gene in genes]

GENE_EVOLUTION_INTERPRETATIONS: dict[str, dict[str, str]] = {
    "af_decay_stress": {
        "up": "Стресс держится дольше. Колония адаптируется к хроническому стрессу, но риск подавления репродукции растёт.",
        "down": "Стресс рассеивается быстрее. Агенты восстанавливаются после стрессовых событий эффективнее.",
        "flat": "Скорость рассеивания стресса стабильна. Нет выраженного отбора по этому признаку.",
    },
    "nm_acc_k_cort": {
        "up": "Кортизол-чувствительность растёт. Популяция становится уязвимее к кортизоловому давлению.",
        "down": "Кортизол-чувствительность снижается. Колония адаптируется к высокому стрессу через сниженную реактивность.",
        "flat": "Кортизол-чувствительность стабильна.",
    },
    "lt_max_lifespan_factor": {
        "up": "Потенциальная продолжительность жизни растёт. Отбор выявил преимущество долгожителей.",
        "down": "Продолжительность жизни сокращается. Возможен отбор на быстрое размножение в ущерб долголетию.",
        "flat": "Потенциальная продолжительность жизни не меняется. Ген не находится под значимым отбором.",
    },
    "wk_recovery_factor": {
        "up": "Восстановление после сна ускоряется. Агенты с эффективным сном получают больше активного времени.",
        "down": "Восстановление после сна замедляется. Возможен отбор на сниженные требования к сну.",
        "flat": "Скорость восстановления стабильна.",
    },
    "wk_accumulation_factor": {
        "up": "Усталость накапливается быстрее. Возможно давление высокой активности.",
        "down": "Усталость накапливается медленнее. Колония эволюционирует к большей выносливости.",
        "flat": "Скорость накопления усталости стабильна.",
    },
    "dr_social_drive_baseline": {
        "up": "Социальный инстинкт усиливается. Колония становится более сплочённой.",
        "down": "Социальный инстинкт ослабевает. Растёт индивидуализм и конкуренция.",
        "flat": "Социальный инстинкт стабилен.",
    },
    "dr_curiosity_baseline": {
        "up": "Любопытство растёт. Агенты активнее исследуют среду.",
        "down": "Любопытство снижается. Консервативные стратегии получают преимущество.",
        "flat": "Базовый уровень любопытства стабилен.",
    },
    "lr_alpha": {
        "up": "Скорость обучения растёт. Быстрая адаптация выгодна, но поведение может стать нестабильным.",
        "down": "Скорость обучения снижается. Отбор идёт к более предсказуемому поведению.",
        "flat": "Скорость обучения стабильна.",
    },
    "lr_gamma": {
        "up": "Горизонт планирования растёт. Агенты учитывают долгосрочные последствия.",
        "down": "Горизонт планирования сокращается. Краткосрочные стратегии получают преимущество.",
        "flat": "Горизонт планирования стабилен.",
    },
    "af_lambda_reg": {
        "up": "Эмоциональная саморегуляция усиливается. Агенты лучше гасят аффективные всплески.",
        "down": "Эмоциональная саморегуляция слабеет. Аффект развивается свободнее.",
        "flat": "Саморегуляция стабильна.",
    },
    "nm_acc_k_ht": {
        "up": "Серотониновый тонус растёт. Базовый уровень благополучия повышается.",
        "down": "Серотониновый тонус снижается. Негативный аффект становится более частым.",
        "flat": "Серотониновый тонус стабилен.",
    },
    "dr_perception_radius_factor": {
        "up": "Поле восприятия расширяется. Агенты замечают больше событий вокруг.",
        "down": "Поле восприятия сужается. Агенты фокусируются на ближайшем окружении.",
        "flat": "Радиус восприятия стабилен.",
    },
    "_default": {
        "up": "Значение гена растёт по поколениям.",
        "down": "Значение гена снижается по поколениям.",
        "flat": "Ген стабилен - без выраженного отбора.",
    },
}

ACTION_LABELS_RU = {
    "eat": "еда",
    "drink": "вода",
    "sleep": "сон",
    "hide": "укрытие",
    "explore": "исследование",
    "rest": "отдых",
    "socialize": "социализация",
    "play": "игра",
    "groom_self": "самоуход",
    "run_wheel": "колесо",
    "idle": "ожидание",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result:
        return default
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _mean(values: Sequence[float]) -> float:
    clean = [_safe_float(value, 0.0) for value in values]
    return sum(clean) / float(len(clean)) if clean else 0.0


def _std(values: Sequence[float]) -> float:
    clean = [_safe_float(value, 0.0) for value in values]
    if len(clean) <= 1:
        return 0.0
    avg = _mean(clean)
    return sqrt(sum((value - avg) ** 2 for value in clean) / float(len(clean)))


def _read_axis(agent: Any, key: str, default: float = 0.0) -> float:
    axes = getattr(getattr(agent, "affective_space", None), "axes", {}) or {}
    if isinstance(axes, Mapping) and key in axes:
        return _safe_float(axes.get(key), default)
    return _safe_float(getattr(agent, key, default), default)


def _read_nm(agent: Any, key: str, default: float = 0.0) -> float:
    return _safe_float(getattr(getattr(agent, "neuromodulators", None), key, default), default)


def _genome_genes(agent: Any) -> dict[str, float]:
    genes = getattr(getattr(agent, "genome", None), "genes", {}) or {}
    if isinstance(genes, Mapping):
        return {str(key): _safe_float(value, 0.0) for key, value in genes.items()}
    return {}


def _memorials(death_registry: Any) -> list[Any]:
    if death_registry is None:
        return []
    try:
        return list(death_registry.get_all_memorials())
    except Exception:
        return []


def _gene_value(genes: Mapping[str, float], gene_key: str) -> float | None:
    if gene_key in genes:
        return _safe_float(genes[gene_key], 0.0)
    aliases = {
        "lr_alpha": "lr_alpha_online",
    }
    alias = aliases.get(gene_key)
    if alias and alias in genes:
        return _safe_float(genes[alias], 0.0)
    return None


def build_generation_summaries(living_agents: list[Any], death_registry: Any) -> list[GenerationSummary]:
    """Aggregate living agents and death memorials by generation."""

    try:
        living_by_gen: dict[int, list[Any]] = defaultdict(list)
        dead_by_gen: dict[int, list[Any]] = defaultdict(list)
        for agent in living_agents:
            living_by_gen[_safe_int(getattr(agent, "generation", 0), 0)].append(agent)
        for memorial in _memorials(death_registry):
            dead_by_gen[_safe_int(getattr(memorial, "generation", 0), 0)].append(memorial)

        generations = sorted(set(living_by_gen) | set(dead_by_gen))
        summaries: list[GenerationSummary] = []
        for generation in generations:
            living = living_by_gen.get(generation, [])
            dead = dead_by_gen.get(generation, [])
            stress_values = [_read_axis(agent, "stress", 0.0) for agent in living] + [
                _safe_float(getattr(memorial, "final_stress", 0.0), 0.0) for memorial in dead
            ]
            cortisol_values = [_read_nm(agent, "cortisol", 0.0) for agent in living] + [
                _safe_float(getattr(memorial, "final_cortisol", 0.0), 0.0) for memorial in dead
            ]
            energy_values = [_safe_float(getattr(agent, "energy", _read_axis(agent, "energy", 0.0)), 0.0) for agent in living] + [
                _safe_float(getattr(memorial, "final_energy", 0.0), 0.0) for memorial in dead
            ]
            vitality_values = [
                _safe_float(getattr(getattr(agent, "mortality_system", None), "vitality", 1.0), 1.0)
                for agent in living
            ] + [_safe_float(getattr(memorial, "final_vitality", 0.0), 0.0) for memorial in dead]
            lived_steps = [_safe_float(getattr(agent, "lived_steps", 0), 0.0) for agent in living] + [
                _safe_float(getattr(memorial, "lived_steps", 0), 0.0) for memorial in dead
            ]
            offspring = [_safe_int(getattr(getattr(agent, "reproductive_system", None), "total_offspring", 0), 0) for agent in living] + [
                _safe_int(getattr(memorial, "total_offspring", 0), 0) for memorial in dead
            ]
            cause_distribution = Counter(
                str(getattr(memorial, "cause_of_death", "") or "unknown") for memorial in dead
            )

            gene_values: dict[str, list[float]] = defaultdict(list)
            for agent in living:
                for key, value in _genome_genes(agent).items():
                    gene_values[key].append(value)
            for memorial in dead:
                genes = getattr(memorial, "genome_genes", {}) or {}
                if isinstance(genes, Mapping):
                    for key, value in genes.items():
                        gene_values[str(key)].append(_safe_float(value, 0.0))

            mean_genome = {key: _mean(values) for key, values in gene_values.items()}
            genome_std = {key: _std(values) for key, values in gene_values.items()}
            agent_count = len(living) + len(dead)
            summaries.append(
                GenerationSummary(
                    generation=generation,
                    agent_count=agent_count,
                    alive_count=len(living),
                    dead_count=len(dead),
                    mean_lived_steps=_mean(lived_steps),
                    mean_stress_at_death=_mean(stress_values),
                    mean_cortisol_at_death=_mean(cortisol_values),
                    mean_energy_at_death=_mean(energy_values),
                    mean_vitality_at_death=_mean(vitality_values),
                    cause_distribution=dict(cause_distribution),
                    mean_genome=mean_genome,
                    genome_std=genome_std,
                    total_offspring=sum(offspring),
                    mean_total_offspring=_mean([float(value) for value in offspring]),
                )
            )
        return summaries
    except Exception:
        return []


def compare_first_last_third(values: list[float], gene_range: float) -> tuple[str, float]:
    """Compare first and last third and return label plus normalized magnitude."""

    if not values:
        return ("↔ стабильно", 0.0)
    chunk = max(1, len(values) // 3)
    first_mean = _mean(values[:chunk])
    last_mean = _mean(values[-chunk:])
    change = (last_mean - first_mean) / max(abs(gene_range), 1e-6)
    magnitude = abs(change)
    if change > 0.05:
        return ("↗ растёт", magnitude)
    if change < -0.05:
        return ("↘ снижается", magnitude)
    return ("↔ стабильно", magnitude)


def _gene_range(gene_key: str) -> float:
    registry_item = GENE_REGISTRY.get(gene_key)
    if registry_item is None:
        return 1.0
    return max(1e-6, _safe_float(getattr(registry_item, "high", 1.0), 1.0) - _safe_float(getattr(registry_item, "low", 0.0), 0.0))


def _trend_direction(trend_label: str) -> str:
    if "раст" in trend_label:
        return "up"
    if "сни" in trend_label:
        return "down"
    return "flat"


def _gene_group(gene_key: str) -> str:
    registry_item = GENE_REGISTRY.get(gene_key)
    if registry_item is not None:
        return str(getattr(registry_item, "group", gene_key.split("_", 1)[0]))
    return gene_key.split("_", 1)[0]


def build_gene_tracks(
    generation_summaries: list[GenerationSummary],
    min_generations: int = 2,
) -> list[GeneEvolutionTrack]:
    """Build evolutionary tracks for tracked genes."""

    tracks: list[GeneEvolutionTrack] = []
    try:
        for gene_key in ALL_TRACKED_GENES:
            values_by_gen: dict[int, float] = {}
            std_by_gen: dict[int, float] = {}
            for summary in generation_summaries:
                value = _gene_value(summary.mean_genome, gene_key)
                if value is None:
                    continue
                values_by_gen[summary.generation] = value
                std_by_gen[summary.generation] = _safe_float(summary.genome_std.get(gene_key, 0.0), 0.0)
            if len(values_by_gen) < min_generations:
                continue
            ordered_values = [values_by_gen[gen] for gen in sorted(values_by_gen)]
            trend_label, trend_magnitude = compare_first_last_third(ordered_values, _gene_range(gene_key))
            direction = _trend_direction(trend_label)
            interpretations = GENE_EVOLUTION_INTERPRETATIONS.get(gene_key, GENE_EVOLUTION_INTERPRETATIONS["_default"])
            tracks.append(
                GeneEvolutionTrack(
                    gene_key=gene_key,
                    group=_gene_group(gene_key),
                    values_by_gen=values_by_gen,
                    std_by_gen=std_by_gen,
                    trend_label=trend_label,
                    trend_magnitude=trend_magnitude,
                    interpretation=interpretations.get(direction, interpretations["flat"]),
                    is_under_selection=direction != "flat" and trend_magnitude > 0.08,
                )
            )
        tracks.sort(key=lambda track: track.trend_magnitude, reverse=True)
    except Exception:
        return []
    return tracks


def build_action_distribution(living_agents: list[Any]) -> list[BehaviorPattern]:
    total = len(living_agents)
    counts = Counter(str(getattr(agent, "current_action", "idle") or "idle") for agent in living_agents)
    return [
        BehaviorPattern(action=action, count=count, fraction=count / float(max(1, total)), label_ru=ACTION_LABELS_RU.get(action, action))
        for action, count in counts.most_common()
    ]


def build_social_structure(living_agents: list[Any], observer: Any = None) -> SocialStructure:
    total_known_pairs = bonded_pairs = rival_pairs = kin_pairs = isolation_count = 0
    affinities: list[float] = []
    for agent in living_agents:
        knowledge = getattr(agent, "knowledge", {}) or {}
        if not isinstance(knowledge, Mapping) or not knowledge:
            isolation_count += 1
            continue
        total_known_pairs += len(knowledge)
        for known in knowledge.values():
            relationship = str(getattr(known, "relationship_type", "stranger"))
            if relationship == "bonded":
                bonded_pairs += 1
            elif relationship == "rival":
                rival_pairs += 1
            elif relationship == "kin":
                kin_pairs += 1
            affinities.append(_safe_float(getattr(known, "affinity", 0.0), 0.0))
    cohesion = 0.0
    if observer is not None:
        try:
            cohesion = _safe_float(observer.get_social_cohesion(), 0.0)
        except Exception:
            cohesion = 0.0
    if cohesion <= 0.0 and total_known_pairs > 0:
        bonded_fraction = bonded_pairs / float(max(1, total_known_pairs))
        affinity_term = (_clamp(_mean(affinities), -1.0, 1.0) + 1.0) / 2.0
        cohesion = _clamp(bonded_fraction * affinity_term)
    return SocialStructure(
        total_known_pairs=total_known_pairs,
        bonded_pairs=bonded_pairs,
        rival_pairs=rival_pairs,
        kin_pairs=kin_pairs,
        mean_affinity=_mean(affinities),
        cohesion_index=_clamp(cohesion),
        isolation_count=isolation_count,
    )


def _genome_diversity(living_agents: list[Any]) -> float:
    per_gene: dict[str, list[float]] = defaultdict(list)
    for agent in living_agents:
        for key, value in _genome_genes(agent).items():
            per_gene[key].append(value)
    if not per_gene:
        return 0.0
    normalized_std: list[float] = []
    for key, values in per_gene.items():
        if len(values) < 2:
            continue
        normalized_std.append(_clamp(_std(values) / _gene_range(key)))
    return _clamp(_mean(normalized_std))


def _max_lifespan_steps(living_agents: list[Any], summaries: list[GenerationSummary]) -> float:
    values = [
        _safe_float(getattr(getattr(agent, "mortality_system", None), "max_lifespan_steps", 0.0), 0.0)
        for agent in living_agents
    ]
    values = [value for value in values if value > 0]
    if values:
        return max(values)
    max_lived = max([summary.mean_lived_steps for summary in summaries] or [0.0])
    return max(1.0, max_lived)


def compute_health_index(
    living_agents: list[Any],
    observer: Any,
    swarm: Any = None,
    generation_summaries: list[GenerationSummary] | None = None,
) -> ColonyHealthIndex:
    """Compute a weighted colony health index in [0, 1]."""

    summaries = generation_summaries or []
    mean_stress = _mean([_read_axis(agent, "stress", 0.0) for agent in living_agents])
    mean_cortisol = _mean([_read_nm(agent, "cortisol", 0.0) for agent in living_agents])
    mean_energy = _mean([_safe_float(getattr(agent, "energy", _read_axis(agent, "energy", 0.0)), 0.0) for agent in living_agents])
    social = 0.0
    if observer is not None:
        try:
            social = _safe_float(observer.get_social_cohesion(), 0.0)
        except Exception:
            social = 0.0
    if social <= 0.0:
        social = build_social_structure(living_agents, None).cohesion_index
    if living_agents:
        lived_mean = _mean([_safe_float(getattr(agent, "lived_steps", 0), 0.0) for agent in living_agents])
    else:
        lived_mean = _mean([summary.mean_lived_steps for summary in summaries])
    lifespan = _clamp(lived_mean / _max_lifespan_steps(living_agents, summaries))
    diversity = _genome_diversity(living_agents)
    if diversity <= 0.0 and summaries:
        diversity = _clamp(_mean([_mean(list(summary.genome_std.values())) for summary in summaries if summary.genome_std]))

    raw_components = {
        "stress": _clamp(1.0 - mean_stress),
        "cortisol": _clamp(1.0 - mean_cortisol),
        "energy": _clamp(mean_energy),
        "social": _clamp(social),
        "lifespan": _clamp(lifespan),
        "diversity": _clamp(diversity),
    }
    weights = {
        "stress": 0.25,
        "cortisol": 0.20,
        "energy": 0.20,
        "social": 0.15,
        "lifespan": 0.10,
        "diversity": 0.10,
    }
    overall = sum(raw_components[key] * weights[key] for key in weights)
    if not living_agents:
        overall = min(overall, 0.25)
    if overall > 0.75:
        verdict, color = "Колония здорова и активно развивается", (90, 175, 110)
    elif overall > 0.55:
        verdict, color = "Колония стабильна с умеренными рисками", (185, 165, 65)
    elif overall > 0.35:
        verdict, color = "Колония под давлением, требует внимания", (210, 120, 60)
    else:
        verdict, color = "Колония в критическом состоянии", (200, 65, 55)
    return ColonyHealthIndex(_clamp(overall), raw_components, verdict, color)


def _trend_from_values(values: Sequence[float]) -> str:
    if len(values) < 2:
        return "↔ стабильно"
    label, _ = compare_first_last_third([_safe_float(value, 0.0) for value in values], 1.0)
    return label


def _observer_trend(observer: Any, field_name: str) -> list[float]:
    if observer is None:
        return []
    try:
        return list(observer.get_trend(field_name, last_n=50))
    except Exception:
        return []


def _observer_cohesion_trend(observer: Any) -> list[float]:
    if observer is None:
        return []
    history = list(getattr(observer, "history", []) or [])[-50:]
    values: list[float] = []
    for snapshot in history:
        total = _safe_int(getattr(snapshot, "total_known_pairs", 0), 0)
        bonded = _safe_int(getattr(snapshot, "bonded_pairs", 0), 0)
        affinity = _safe_float(getattr(snapshot, "mean_affinity", 0.0), 0.0)
        values.append(_clamp((bonded / float(max(1, total))) * ((_clamp(affinity, -1.0, 1.0) + 1.0) / 2.0)))
    return values


def _build_personality_distribution(living_agents: list[Any]) -> list[BehaviorPattern]:
    counts: Counter[str] = Counter()
    total = len(living_agents)
    for agent in living_agents:
        label = ""
        interp = getattr(agent, "nowa_interpretation", None)
        if interp is not None:
            label = str(getattr(getattr(interp, "personality", None), "character_label", ""))
        if not label:
            action = str(getattr(agent, "current_action", "idle") or "idle")
            if action in {"hide"}:
                label = "ТРЕВОЖНЫЙ ОДИНОЧКА"
            elif action in {"eat", "drink"}:
                label = "РЕСУРСНЫЙ ПРАГМАТИК"
            elif action in {"socialize", "play", "allogroom"}:
                label = "СОЦИАЛЬНЫЙ АГЕНТ"
            elif action in {"explore", "run_wheel"}:
                label = "ИССЛЕДОВАТЕЛЬ"
            elif action in {"sleep", "rest"}:
                label = "ПАССИВНЫЙ"
            else:
                try:
                    axes = {
                        "stress": _read_axis(agent, "stress", 0.0),
                        "arousal": _read_axis(agent, "arousal", 0.0),
                        "valence": _read_axis(agent, "valence", 0.0),
                        "attachment": _read_axis(agent, "attachment", 0.0),
                        "curiosity": _read_axis(agent, "curiosity", 0.0),
                        "trust": _read_axis(agent, "trust", 0.0),
                        "dominance": _read_axis(agent, "dominance", 0.0),
                        "energy": _safe_float(getattr(agent, "energy", 0.0), 0.0),
                        "social_drive": _safe_float(getattr(agent, "social_drive", 0.0), 0.0),
                    }
                    nm = {key: _read_nm(agent, key, 0.0) for key in ["dopamine", "serotonin", "norepinephrine", "cortisol", "acetylcholine"]}
                    label = build_personality_readout([], interpret_affect(axes), interpret_neuro(nm)).character_label
                except Exception:
                    label = "НЕОПРЕДЕЛЁННЫЙ"
        counts[label or "НЕОПРЕДЕЛЁННЫЙ"] += 1
    return [
        BehaviorPattern(action=label, count=count, fraction=count / float(max(1, total)), label_ru=label)
        for label, count in counts.most_common()
    ]


def _dominant_habits(living_agents: list[Any]) -> list[BehaviorPattern]:
    counts: Counter[str] = Counter()
    for agent in living_agents:
        cortex = getattr(agent, "cortex", None)
        patterns = list(getattr(cortex, "patterns", []) or [])
        actions_seen: set[str] = set()
        for pattern in patterns[-25:]:
            signature = getattr(pattern, "signature", pattern)
            tokens: list[str]
            if isinstance(signature, str):
                tokens = [signature]
            elif isinstance(signature, Sequence):
                tokens = [str(item) for item in signature]
            else:
                tokens = []
            for token in tokens:
                if token.startswith("action:"):
                    actions_seen.add(token.split(":", 1)[1])
        if not actions_seen:
            action = str(getattr(agent, "current_action", "") or "")
            if action:
                actions_seen.add(action)
        for action in actions_seen:
            counts[action] += 1
    total = len(living_agents)
    return [
        BehaviorPattern(action=action, count=count, fraction=count / float(max(1, total)), label_ru=ACTION_LABELS_RU.get(action, action))
        for action, count in counts.most_common(5)
    ]


def _build_forecast(
    living_agents: list[Any],
    summaries: list[GenerationSummary],
    gene_tracks: list[GeneEvolutionTrack],
    social: SocialStructure,
    health: ColonyHealthIndex,
    observer: Any,
    observer_stress_trend: list[float],
    observer_energy_trend: list[float],
    observer_cohesion_trend: list[float],
) -> EvolutionaryForecast:
    mean_cortisol = _mean([_read_nm(agent, "cortisol", 0.0) for agent in living_agents])
    mean_energy = _mean([_safe_float(getattr(agent, "energy", 0.0), 0.0) for agent in living_agents])
    female_count = sum(1 for agent in living_agents if str(getattr(agent, "sex", "")).upper() == "F")
    female_fraction = female_count / float(max(1, len(living_agents)))
    diversity = health.components.get("diversity", 0.0)
    lt_track = next((track for track in gene_tracks if track.gene_key == "lt_max_lifespan_factor"), None)
    lt_trend = lt_track.trend_label if lt_track is not None else "↔ стабильно"
    extinction_risk = 1.0 - health.overall
    if observer is not None:
        try:
            extinction_risk = max(extinction_risk, _safe_float(observer.get_extinction_risk(), 0.0))
        except Exception:
            pass

    context = {
        "mean_cortisol": mean_cortisol,
        "lt_trend": lt_trend,
        "diversity": diversity,
        "female_fraction": female_fraction,
        "mean_energy_at_death": summaries[-1].mean_energy_at_death if summaries else mean_energy,
        "cohesion": social.cohesion_index,
        "extinction_risk": extinction_risk,
        "stress_trend": _trend_from_values(observer_stress_trend or [summary.mean_stress_at_death for summary in summaries]),
        "cortisol_trend": _trend_from_values([summary.mean_cortisol_at_death for summary in summaries]),
        "social_trend": _trend_from_values(observer_cohesion_trend),
        "mean_offspring_per_agent": summaries[-1].mean_total_offspring if summaries else 0.0,
    }
    risk_rules = [
        (context["mean_cortisol"] > 0.80, "Хронический кортизол блокирует репродукцию"),
        (context["lt_trend"] == "↘ снижается", "Потенциальная продолжительность жизни сокращается"),
        (context["diversity"] < 0.15, "Низкое генетическое разнообразие - founder effect"),
        (context["female_fraction"] < 0.35 or context["female_fraction"] > 0.65, "Половой дисбаланс угрожает размножению"),
        (context["mean_energy_at_death"] < 0.15, "Агенты умирают с истощёнными энергетическими резервами"),
        (context["cohesion"] < 0.10, "Слабая социальная сплочённость - изоляция особей"),
        (context["extinction_risk"] > 0.50, "Высокий риск вымирания по оценке ColonyPopulationObserver"),
    ]
    opportunity_rules = [
        (context["lt_trend"] == "↗ растёт", "Ген долголетия под положительным отбором"),
        (context["stress_trend"] == "↘ снижается", "Стресс снижается - репродуктивный потенциал растёт"),
        (context["cortisol_trend"] == "↘ снижается", "Кортизол снижается - адаптация к стрессу работает"),
        (context["social_trend"] == "↗ растёт", "Социальная сплочённость растёт - колония укрепляется"),
        (context["diversity"] > 0.30, "Высокое генетическое разнообразие - хороший эволюционный потенциал"),
        (context["mean_offspring_per_agent"] > 2.5, "Высокая репродуктивная успешность"),
    ]
    risks = [text for condition, text in risk_rules if condition]
    opportunities = [text for condition, text in opportunity_rules if condition]
    adapting = [track.gene_key for track in gene_tracks if track.is_under_selection][:5]
    stagnant = [track.gene_key for track in gene_tracks if not track.is_under_selection][-5:]
    if mean_cortisol > 0.65:
        pressure = "хронический стресс"
    elif social.cohesion_index < 0.15:
        pressure = "социальная изоляция"
    elif health.components.get("energy", 0.0) < 0.35:
        pressure = "энергетический дефицит"
    else:
        pressure = "умеренный отбор по устойчивости"
    if extinction_risk > 0.70:
        risk_label = "высокий"
    elif extinction_risk > 0.40:
        risk_label = "умеренный"
    else:
        risk_label = "низкий"
    summary = (
        f"Колония сейчас оценивается как: {health.verdict.lower()}. "
        f"Главный фактор отбора - {pressure}. "
        f"Активно адаптируются: {', '.join(adapting[:3]) if adapting else 'выраженных генов под отбором нет'}. "
        f"Ключевой риск: {risks[0] if risks else 'критических рисков не выявлено'}."
    )
    return EvolutionaryForecast(
        extinction_risk=_clamp(extinction_risk),
        extinction_risk_label=risk_label,
        dominant_pressure=pressure,
        adapting_traits=adapting,
        stagnant_traits=stagnant,
        key_risks=risks,
        key_opportunities=opportunities,
        summary=summary,
    )


def _empty_social() -> SocialStructure:
    return SocialStructure(0, 0, 0, 0, 0.0, 0.0, 0)


def build_swarm_analytics(
    runner: Any,
    observer: Any = None,
    generation_index_map: dict[str, int] | None = None,
) -> SwarmAnalytics:
    """Build a full analytical snapshot. Never raises."""

    try:
        living_agents = list(getattr(runner, "agents", []) or [])
    except Exception:
        living_agents = []
    try:
        registry = getattr(runner, "death_registry", None)
        dead_count = len(_memorials(registry))
    except Exception:
        registry = None
        dead_count = 0
    try:
        snapshot_time = _safe_float(getattr(runner, "sim_time", 0.0), 0.0)
    except Exception:
        snapshot_time = 0.0

    try:
        generation_summaries = build_generation_summaries(living_agents, registry)
    except Exception:
        generation_summaries = []
    try:
        gene_tracks = build_gene_tracks(generation_summaries)
    except Exception:
        gene_tracks = []
    social = build_social_structure(living_agents, observer)
    health = compute_health_index(living_agents, observer, getattr(runner, "swarm", None), generation_summaries)
    stress_trend = _observer_trend(observer, "mean_stress")
    energy_trend = _observer_trend(observer, "mean_energy")
    population_trend = _observer_trend(observer, "agent_count")
    cohesion_trend = _observer_cohesion_trend(observer)
    forecast = _build_forecast(
        living_agents,
        generation_summaries,
        gene_tracks,
        social,
        health,
        observer,
        stress_trend,
        energy_trend,
        cohesion_trend,
    )

    generations = [summary.generation for summary in generation_summaries]
    generation_range = (min(generations), max(generations)) if generations else (0, 0)
    try:
        total_ever = max(_safe_int(getattr(registry, "total_ever_lived", lambda: 0)(), 0), len(living_agents) + dead_count)
    except Exception:
        total_ever = len(living_agents) + dead_count
    resources = getattr(runner, "resources", None)
    current_metrics = {
        "mean_stress": _mean([_read_axis(agent, "stress", 0.0) for agent in living_agents]),
        "std_stress": _std([_read_axis(agent, "stress", 0.0) for agent in living_agents]),
        "mean_cortisol": _mean([_read_nm(agent, "cortisol", 0.0) for agent in living_agents]),
        "std_cortisol": _std([_read_nm(agent, "cortisol", 0.0) for agent in living_agents]),
        "mean_energy": _mean([_safe_float(getattr(agent, "energy", _read_axis(agent, "energy", 0.0)), 0.0) for agent in living_agents]),
        "std_energy": _std([_safe_float(getattr(agent, "energy", _read_axis(agent, "energy", 0.0)), 0.0) for agent in living_agents]),
        "mean_social_drive": _mean([_safe_float(getattr(agent, "social_drive", _read_axis(agent, "social_drive", 0.0)), 0.0) for agent in living_agents]),
        "mean_curiosity": _mean([_read_axis(agent, "curiosity", 0.0) for agent in living_agents]),
        "female_count": float(sum(1 for agent in living_agents if str(getattr(agent, "sex", "")).upper() == "F")),
        "male_count": float(sum(1 for agent in living_agents if str(getattr(agent, "sex", "")).upper() == "M")),
        "sleeping_count": float(sum(1 for agent in living_agents if bool(getattr(agent, "is_sleeping", False)))),
        "mean_dopamine": _mean([_read_nm(agent, "dopamine", 0.0) for agent in living_agents]),
        "mean_serotonin": _mean([_read_nm(agent, "serotonin", 0.0) for agent in living_agents]),
        "mean_norepinephrine": _mean([_read_nm(agent, "norepinephrine", 0.0) for agent in living_agents]),
        "mean_acetylcholine": _mean([_read_nm(agent, "acetylcholine", 0.0) for agent in living_agents]),
        "mean_age": _mean([_safe_float(getattr(agent, "age", 0.0), 0.0) for agent in living_agents]),
    }
    hippocampus_sizes = [
        _safe_float(len(getattr(getattr(agent, "hippocampus", None), "experiences", []) or []), 0.0)
        for agent in living_agents
    ]
    cortex_sizes = [
        _safe_float(len(getattr(getattr(agent, "cortex", None), "patterns", []) or []), 0.0)
        for agent in living_agents
    ]
    return SwarmAnalytics(
        snapshot_time=snapshot_time,
        total_ever_lived=total_ever,
        living_count=len(living_agents),
        dead_count=dead_count,
        generation_range=generation_range,
        generation_summaries=generation_summaries,
        gene_tracks=gene_tracks,
        most_evolved_genes=[track.gene_key for track in gene_tracks[:5]],
        most_stable_genes=[track.gene_key for track in sorted(gene_tracks, key=lambda track: track.trend_magnitude)[:5]],
        current_action_distribution=build_action_distribution(living_agents),
        current_social=social,
        health_index=health,
        observer_stress_trend=stress_trend,
        observer_energy_trend=energy_trend,
        observer_population_trend=population_trend,
        observer_cohesion_trend=cohesion_trend,
        forecast=forecast,
        resources={
            "food_pellets": _safe_float(getattr(resources, "food_pellets", 0.0), 0.0),
            "hay": _safe_float(getattr(resources, "hay", 0.0), 0.0),
            "water": _safe_float(getattr(resources, "water", 0.0), 0.0),
        },
        current_metrics=current_metrics,
        personality_distribution=_build_personality_distribution(living_agents),
        dominant_habits=_dominant_habits(living_agents),
        mean_hippocampus_size=_mean(hippocampus_sizes),
        std_hippocampus_size=_std(hippocampus_sizes),
        mean_cortex_patterns=_mean(cortex_sizes),
        std_cortex_patterns=_std(cortex_sizes),
    )


__all__ = [
    "ALL_TRACKED_GENES",
    "TRACKED_GENE_GROUPS",
    "BehaviorPattern",
    "ColonyHealthIndex",
    "EvolutionaryForecast",
    "GeneEvolutionTrack",
    "GenerationSummary",
    "SocialStructure",
    "SwarmAnalytics",
    "build_action_distribution",
    "build_gene_tracks",
    "build_generation_summaries",
    "build_social_structure",
    "build_swarm_analytics",
    "compare_first_last_third",
    "compute_health_index",
]
