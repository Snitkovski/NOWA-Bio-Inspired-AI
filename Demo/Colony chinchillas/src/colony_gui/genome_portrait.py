"""
Genome portrait module for Colony Chinchilla inspector.

Builds personality portraits, mutation analysis and lineage trends
from agent genome data. Pure Python — no pygame dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
#  Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GeneRange:
    key: str
    group: str
    default: float
    low: float
    high: float
    low_label: str
    high_label: str
    trait_category: str
    weight: float
    polarity: str   # "high_good" | "low_good" | "neutral" | "both_extreme_bad"


@dataclass
class TraitScore:
    category: str
    score: float          # [0..1]
    label: str            # текстовый ярлык
    contributing_genes: list[str]


@dataclass
class MutationEffect:
    gene_key: str
    parent_midpoint: float
    current_value: float
    delta: float
    direction: str        # "up" | "down" | "neutral"
    valence: str          # "positive" | "negative" | "neutral"
    consequence_short: str
    consequence_detail: str
    magnitude: str        # "major" | "moderate" | "minor"


@dataclass
class LineageTrendPoint:
    agent_id: str
    display_name: str
    generation: int
    gene_values: dict[str, float]
    stress_at_death: float
    cortisol_at_death: float
    lived_steps: int


@dataclass
class GenomePortrait:
    trait_scores: dict[str, TraitScore]
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    neutral_traits: list[str]
    mutations: list[MutationEffect]
    lineage_trend: list[LineageTrendPoint] | None = None


# ─────────────────────────────────────────────────────────────────────────────
#  Gene registry — full semantic definitions
# ─────────────────────────────────────────────────────────────────────────────

GENE_REGISTRY: dict[str, GeneRange] = {

    # ── АФФЕКТ ───────────────────────────────────────────────────────────────
    "af_decay_stress": GeneRange(
        key="af_decay_stress", group="af", default=0.70, low=0.55, high=0.88,
        low_label="быстро успокаивается",
        high_label="долго носит стресс",
        trait_category="temperament", weight=0.9,
        polarity="low_good",
    ),
    "af_decay_valence": GeneRange(
        key="af_decay_valence", group="af", default=0.92, low=0.80, high=0.98,
        low_label="настроение меняется быстро",
        high_label="стабильное настроение",
        trait_category="temperament", weight=0.5,
        polarity="neutral",
    ),
    "af_decay_arousal": GeneRange(
        key="af_decay_arousal", group="af", default=0.80, low=0.60, high=0.92,
        low_label="возбуждение быстро спадает",
        high_label="долго остаётся возбуждённым",
        trait_category="temperament", weight=0.6,
        polarity="low_good",
    ),
    "af_decay_dominance": GeneRange(
        key="af_decay_dominance", group="af", default=0.97, low=0.88, high=0.99,
        low_label="доминирование нестабильно",
        high_label="устойчивый доминантный статус",
        trait_category="social", weight=0.4,
        polarity="neutral",
    ),
    "af_decay_curiosity": GeneRange(
        key="af_decay_curiosity", group="af", default=0.78, low=0.60, high=0.90,
        low_label="любопытство быстро угасает",
        high_label="устойчивый исследовательский интерес",
        trait_category="cognition", weight=0.7,
        polarity="high_good",
    ),
    "af_decay_trust": GeneRange(
        key="af_decay_trust", group="af", default=0.95, low=0.85, high=0.99,
        low_label="доверие быстро теряется",
        high_label="крепкое долгосрочное доверие",
        trait_category="social", weight=0.7,
        polarity="high_good",
    ),
    "af_decay_attachment": GeneRange(
        key="af_decay_attachment", group="af", default=0.93, low=0.85, high=0.99,
        low_label="привязанности непостоянны",
        high_label="крепко держится за близких",
        trait_category="social", weight=0.8,
        polarity="high_good",
    ),
    "af_lambda_reg": GeneRange(
        key="af_lambda_reg", group="af", default=0.05, low=0.01, high=0.15,
        low_label="слабая аффективная регуляция",
        high_label="сильная эмоциональная саморегуляция",
        trait_category="temperament", weight=0.8,
        polarity="high_good",
    ),

    # ── НЕЙРОМОДУЛЯТОРЫ ───────────────────────────────────────────────────────
    "nm_decay_half_life": GeneRange(
        key="nm_decay_half_life", group="nm", default=60.0, low=20.0, high=200.0,
        low_label="быстрые нейромодуляторы",
        high_label="долгоживущие нейрохимические состояния",
        trait_category="temperament", weight=0.5,
        polarity="neutral",
    ),
    "nm_da_ne_weight": GeneRange(
        key="nm_da_ne_weight", group="nm", default=0.0, low=-0.5, high=0.5,
        low_label="дофамин тормозит норадреналин",
        high_label="дофамин усиливает норадреналин",
        trait_category="temperament", weight=0.35,
        polarity="neutral",
    ),
    "nm_ne_da_weight": GeneRange(
        key="nm_ne_da_weight", group="nm", default=0.0, low=-0.5, high=0.5,
        low_label="норадреналин тормозит дофамин",
        high_label="норадреналин усиливает дофамин",
        trait_category="temperament", weight=0.35,
        polarity="neutral",
    ),
    "nm_da_ach_weight": GeneRange(
        key="nm_da_ach_weight", group="nm", default=0.0, low=-0.5, high=0.5,
        low_label="дофамин подавляет ацетилхолин",
        high_label="дофамин усиливает ацетилхолин",
        trait_category="cognition", weight=0.3,
        polarity="neutral",
    ),
    "nm_ach_da_weight": GeneRange(
        key="nm_ach_da_weight", group="nm", default=0.0, low=-0.5, high=0.5,
        low_label="ацетилхолин подавляет дофамин",
        high_label="ацетилхолин усиливает дофамин",
        trait_category="cognition", weight=0.3,
        polarity="neutral",
    ),
    "nm_acc_k_ne": GeneRange(
        key="nm_acc_k_ne", group="nm", default=0.8, low=0.3, high=1.0,
        low_label="слабая реакция норадреналина",
        high_label="острая норадреналиновая реакция",
        trait_category="temperament", weight=0.5,
        polarity="neutral",
    ),
    "nm_acc_k_cort": GeneRange(
        key="nm_acc_k_cort", group="nm", default=0.7, low=0.3, high=1.0,
        low_label="слабая реакция на кортизол",
        high_label="высокая кортизол-чувствительность",
        trait_category="temperament", weight=0.85,
        polarity="low_good",
    ),
    "nm_acc_k_ht": GeneRange(
        key="nm_acc_k_ht", group="nm", default=0.5, low=0.2, high=0.9,
        low_label="низкая серотониновая чувствительность",
        high_label="высокая серотониновая чувствительность",
        trait_category="temperament", weight=0.5,
        polarity="high_good",
    ),

    # ── БОДРСТВОВАНИЕ ─────────────────────────────────────────────────────────
    "wk_accumulation_factor": GeneRange(
        key="wk_accumulation_factor", group="wk", default=1.0, low=0.5, high=2.0,
        low_label="медленно устаёт",
        high_label="быстро накапливает усталость",
        trait_category="endurance", weight=0.75,
        polarity="low_good",
    ),
    "wk_recovery_factor": GeneRange(
        key="wk_recovery_factor", group="wk", default=0.85, low=0.4, high=1.0,
        low_label="долго восстанавливается после сна",
        high_label="быстро приходит в норму",
        trait_category="endurance", weight=0.85,
        polarity="high_good",
    ),
    "wk_circadian_amplitude": GeneRange(
        key="wk_circadian_amplitude", group="wk", default=0.3, low=0.05, high=0.6,
        low_label="слабый суточный ритм",
        high_label="выраженный суточный цикл",
        trait_category="endurance", weight=0.4,
        polarity="neutral",
    ),
    "wk_circadian_phase": GeneRange(
        key="wk_circadian_phase", group="wk", default=0.0, low=-1.0, high=1.0,
        low_label="ночной тип активности",
        high_label="дневной тип активности",
        trait_category="social", weight=0.3,
        polarity="neutral",
    ),

    # ── ДРАЙВЫ ────────────────────────────────────────────────────────────────
    "dr_curiosity_baseline": GeneRange(
        key="dr_curiosity_baseline", group="dr", default=0.4, low=0.1, high=0.8,
        low_label="апатичный исследователь",
        high_label="ненасытно любопытный",
        trait_category="cognition", weight=0.75,
        polarity="high_good",
    ),
    "dr_social_drive_baseline": GeneRange(
        key="dr_social_drive_baseline", group="dr", default=0.45, low=0.1, high=0.8,
        low_label="одиночка",
        high_label="выраженный социальный инстинкт",
        trait_category="social", weight=0.9,
        polarity="high_good",
    ),
    "dr_perception_radius_factor": GeneRange(
        key="dr_perception_radius_factor", group="dr", default=1.0, low=0.5, high=2.0,
        low_label="узкое восприятие",
        high_label="широкое поле восприятия",
        trait_category="cognition", weight=0.5,
        polarity="high_good",
    ),

    # ── ОБУЧЕНИЕ ──────────────────────────────────────────────────────────────
    "lr_gamma": GeneRange(
        key="lr_gamma", group="lr", default=0.85, low=0.5, high=0.99,
        low_label="живёт настоящим",
        high_label="думает о долгосрочных последствиях",
        trait_category="cognition", weight=0.7,
        polarity="high_good",
    ),
    "lr_alpha": GeneRange(
        key="lr_alpha", group="lr", default=0.05, low=0.005, high=0.2,
        low_label="медленно но стабильно обучается",
        high_label="быстро адаптируется, но нестабилен",
        trait_category="cognition", weight=0.75,
        polarity="both_extreme_bad",
    ),
    "lr_similarity_threshold": GeneRange(
        key="lr_similarity_threshold", group="lr", default=0.6, low=0.2, high=0.9,
        low_label="широкое обобщение опыта",
        high_label="строгое разграничение ситуаций",
        trait_category="cognition", weight=0.4,
        polarity="neutral",
    ),
    "lr_tonic_slow_rate": GeneRange(
        key="lr_tonic_slow_rate", group="lr", default=0.02, low=0.001, high=0.1,
        low_label="стабильные базовые убеждения",
        high_label="быстро пересматривает опыт",
        trait_category="cognition", weight=0.35,
        polarity="neutral",
    ),
    "lr_consolidation_threshold": GeneRange(
        key="lr_consolidation_threshold", group="lr", default=0.5, low=0.2, high=0.9,
        low_label="легко консолидирует опыт в паттерны",
        high_label="консолидирует только сильный опыт",
        trait_category="cognition", weight=0.4,
        polarity="neutral",
    ),

    # ── ДОЛГОЛЕТИЕ ────────────────────────────────────────────────────────────
    "lt_max_lifespan_factor": GeneRange(
        key="lt_max_lifespan_factor", group="lt", default=1.0, low=0.7, high=1.5,
        low_label="короткоживущий",
        high_label="потенциальный долгожитель",
        trait_category="lifespan", weight=1.0,
        polarity="high_good",
    ),
}

# Категории черт
TRAIT_CATEGORIES = ["temperament", "social", "endurance", "cognition", "lifespan"]

TRAIT_LABELS_RU: dict[str, str] = {
    "temperament": "Темперамент",
    "social":      "Социальность",
    "endurance":   "Выносливость",
    "cognition":   "Когниция",
    "lifespan":    "Долгожитие",
}

# Гены которые отслеживаются в трендах линии
LINEAGE_TRACKED_GENES: list[str] = [
    "lt_max_lifespan_factor",
    "af_decay_stress",
    "nm_acc_k_cort",
    "dr_social_drive_baseline",
    "wk_recovery_factor",
    "lr_alpha",
]

LINEAGE_GENE_LABELS_RU: dict[str, str] = {
    "lt_max_lifespan_factor": "Долгожитие",
    "af_decay_stress": "Накопление стресса",
    "nm_acc_k_cort": "Чувствительность к кортизолу",
    "dr_social_drive_baseline": "Социальность",
    "wk_recovery_factor": "Восстановление",
    "lr_alpha": "Темп обучения",
}

LINEAGE_TREND_MEANINGS_RU: dict[str, dict[str, str]] = {
    "lt_max_lifespan_factor": {
        "up": "потенциал жизни усиливается",
        "down": "потенциал жизни снижается",
        "flat": "потенциал жизни стабилен",
    },
    "af_decay_stress": {
        "up": "стресс держится дольше",
        "down": "стресс рассеивается быстрее",
        "flat": "стрессовая реакция стабильна",
    },
    "nm_acc_k_cort": {
        "up": "реакция на кортизол усиливается",
        "down": "реакция на кортизол смягчается",
        "flat": "кортизоловая реакция стабильна",
    },
    "dr_social_drive_baseline": {
        "up": "социальный драйв растёт",
        "down": "социальный драйв снижается",
        "flat": "социальный драйв стабилен",
    },
    "wk_recovery_factor": {
        "up": "восстановление ускоряется",
        "down": "восстановление замедляется",
        "flat": "восстановление стабильно",
    },
    "lr_alpha": {
        "up": "обучение становится резче",
        "down": "обучение становится осторожнее",
        "flat": "темп обучения стабилен",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  Mutation consequence texts
# ─────────────────────────────────────────────────────────────────────────────

# gene_key → { "up": (short, detail), "down": (short, detail) }
MUTATION_CONSEQUENCES: dict[str, dict[str, tuple[str, str]]] = {

    "af_decay_stress": {
        "down": (
            "стресс рассеивается быстрее",
            "Агент легче восстанавливается после конфликтов и испугов. "
            "Снижает риск хронического кортизола, что позитивно влияет "
            "на репродуктивный потенциал и социальную активность.",
        ),
        "up": (
            "стресс держится значительно дольше",
            "Однажды испуганный агент долго остаётся в режиме тревоги. "
            "Повышенный риск хронического кортизола при частых "
            "социальных конфликтах или дефиците ресурсов.",
        ),
    },

    "lt_max_lifespan_factor": {
        "up": (
            "потенциально живёт дольше родителей",
            "Сенесценция начнётся позже и будет менее интенсивной. "
            "Ген реализуется в полной мере только при низком кортизоле — "
            "иначе ускоренное старение компенсирует генетический бонус.",
        ),
        "down": (
            "укороченная потенциальная жизнь",
            "Агент достигнет сенесценции раньше. "
            "Частично компенсируется активным размножением "
            "в молодом возрасте при достаточной энергии.",
        ),
    },

    "wk_recovery_factor": {
        "down": (
            "медленнее восстанавливается после сна",
            "Требует более длительного отдыха для полного бодрствования. "
            "Уязвим к хронической усталости при высокой социальной "
            "активности или частых тревогах.",
        ),
        "up": (
            "быстро приходит в форму после сна",
            "Короткий сон даёт полное восстановление. "
            "Больше активного времени для исследования и социализации. "
            "Преимущество при высокой плотности колонии.",
        ),
    },

    "wk_accumulation_factor": {
        "up": (
            "быстрее накапливает усталость",
            "Требует частого сна. "
            "При высокой активности колонии рискует не успевать "
            "восстанавливаться между социальными взаимодействиями.",
        ),
        "down": (
            "медленно накапливает усталость",
            "Дольше остаётся активным без принудительного сна. "
            "Преимущество в напряжённые периоды жизни колонии "
            "и при высоком wakefulness_threshold.",
        ),
    },

    "nm_acc_k_cort": {
        "up": (
            "высокая чувствительность к кортизолу",
            "Стресс сильнее влияет на физиологию. "
            "При хроническом стрессе популяции быстрее истощается "
            "репродуктивный драйв через формулу (1 − cortisol).",
        ),
        "down": (
            "сниженная чувствительность к кортизолу",
            "Стресс меньше влияет на тело даже при высоком уровне кортизола. "
            "Более устойчив к волнам стресса в переуплотнённой колонии.",
        ),
    },

    "nm_acc_k_ht": {
        "up": (
            "повышенная серотониновая чувствительность",
            "Позитивный опыт сильнее поднимает настроение. "
            "Социальные взаимодействия более значимы — "
            "как позитивные, так и негативные.",
        ),
        "down": (
            "сниженная серотониновая чувствительность",
            "Менее выраженная реакция на позитивный опыт. "
            "Более ровное, но и менее живое эмоциональное состояние.",
        ),
    },

    "dr_social_drive_baseline": {
        "up": (
            "высокая базовая социальная потребность",
            "Активно ищет контакты, быстро строит социальные связи. "
            "Риск стресса при вынужденной изоляции или перегруженности "
            "сигналами от крупной колонии.",
        ),
        "down": (
            "низкая базовая социальная потребность",
            "Комфортно в одиночестве, меньше зависит от других агентов. "
            "Может иметь сложности с привлечением партнёра "
            "при конкуренции с высоко-социальными особями.",
        ),
    },

    "dr_curiosity_baseline": {
        "up": (
            "высокое базовое любопытство",
            "Активно исследует окружение, быстро обнаруживает ресурсы. "
            "Более высокая когнитивная нагрузка — тратит "
            "больше энергии на исследование.",
        ),
        "down": (
            "низкое базовое любопытство",
            "Предпочитает знакомые зоны и рутину. "
            "Экономит энергию, но медленнее адаптируется "
            "к изменениям в среде.",
        ),
    },

    "af_decay_attachment": {
        "up": (
            "крепкие долгосрочные привязанности",
            "Социальные связи устойчивы и долговечны. "
            "Важный вклад в сплочённость колонии и "
            "надёжность в воспитании потомства.",
        ),
        "down": (
            "привязанности непостоянны",
            "Быстро теряет эмоциональную связь без подкрепления. "
            "Социальные связи требуют частого поддержания "
            "через груминг и совместный сон.",
        ),
    },

    "af_decay_trust": {
        "up": (
            "доверие сохраняется долго",
            "Однажды установленное доверие устойчиво. "
            "Ключевой ген для формирования bonded-пар "
            "и стабильных социальных групп.",
        ),
        "down": (
            "доверие быстро угасает",
            "Требует постоянного подтверждения отношений. "
            "Социальная сеть нестабильна, "
            "но агент защищён от слепого доверия к незнакомцам.",
        ),
    },

    "af_lambda_reg": {
        "up": (
            "сильная эмоциональная саморегуляция",
            "Агент эффективно гасит аффективные всплески. "
            "Устойчив к панике при тревожных сигналах. "
            "Важный ген для лидерства в колонии.",
        ),
        "down": (
            "слабая эмоциональная саморегуляция",
            "Аффективные состояния развиваются более интенсивно. "
            "Уязвим к каскадному стрессу от alarm calls соседей.",
        ),
    },

    "lr_alpha": {
        "up": (
            "ускоренное обучение",
            "Быстро адаптируется к новым условиям и стратегиям. "
            "Риск нестабильности — может переобучиться на "
            "случайные события и резко менять поведение.",
        ),
        "down": (
            "медленное стабильное обучение",
            "Поведение предсказуемо и консервативно. "
            "Медленнее адаптируется к изменениям среды, "
            "зато не теряет выработанные стратегии.",
        ),
    },

    "lr_gamma": {
        "up": (
            "ориентирован на долгосрочные последствия",
            "При выборе действий учитывает будущее. "
            "Лучше справляется с отложенным вознаграждением "
            "и многошаговыми социальными стратегиями.",
        ),
        "down": (
            "ориентирован на немедленное вознаграждение",
            "Фокус на сиюминутной выгоде. "
            "Может упускать долгосрочно выгодные стратегии, "
            "зато быстро реагирует на острые угрозы.",
        ),
    },

    "wk_circadian_phase": {
        "down": (
            "смещение в ночной тип активности",
            "Активен когда большинство колонии спит. "
            "Меньше конкуренции за ресурсы, но и меньше "
            "социальных контактов в пиковые часы.",
        ),
        "up": (
            "смещение в дневной тип активности",
            "Совпадение с ритмом большинства колонии. "
            "Больше социальных возможностей, "
            "но выше конкуренция за ресурсы.",
        ),
    },

    "nm_decay_half_life": {
        "up": (
            "нейромодуляторы держатся дольше",
            "Как позитивные, так и негативные нейрохимические "
            "состояния более устойчивы. "
            "Дольше помнит как хорошее, так и плохое.",
        ),
        "down": (
            "нейромодуляторы быстро рассеиваются",
            "Быстрая нейрохимическая 'перезарядка'. "
            "Более гибкий эмоционально, "
            "но менее устойчив в длительных состояниях.",
        ),
    },

    "lr_similarity_threshold": {
        "up": (
            "строгое разграничение ситуаций",
            "Не переносит опыт на похожие ситуации. "
            "Требует много уникального опыта для обобщения.",
        ),
        "down": (
            "широкое обобщение опыта",
            "Легко переносит усвоенное на новые ситуации. "
            "Быстрее формирует поведенческие паттерны, "
            "но может ошибочно обобщать несхожие ситуации.",
        ),
    },

    "dr_perception_radius_factor": {
        "up": (
            "широкое поле восприятия",
            "Замечает агентов и сигналы на большем расстоянии. "
            "Более высокая когнитивная нагрузка "
            "от обработки большего числа сигналов.",
        ),
        "down": (
            "узкое поле восприятия",
            "Реагирует только на ближайших агентов. "
            "Экономичен когнитивно, но медленнее "
            "реагирует на угрозы и социальные сигналы.",
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  Summary templates
# ─────────────────────────────────────────────────────────────────────────────

def _generate_summary(
    trait_scores: dict[str, TraitScore],
    genes: dict[str, float],
    display_name: str,
) -> str:
    """Generate 2–3 sentence personality summary from trait scores."""

    dom = max(trait_scores.items(), key=lambda kv: kv[1].score, default=None)
    weak = min(trait_scores.items(), key=lambda kv: kv[1].score, default=None)
    dom_cat = dom[0] if dom else ""
    weak_cat = weak[0] if weak else ""
    dom_score = dom[1].score if dom else 0.5
    weak_score = weak[1].score if weak else 0.5

    name = display_name.split()[0] if display_name else "Агент"
    lifespan = trait_scores.get("lifespan")
    lifespan_score = lifespan.score if lifespan else 0.5
    social = trait_scores.get("social")
    social_score = social.score if social else 0.5
    temp = trait_scores.get("temperament")
    temp_score = temp.score if temp else 0.5
    endurance = trait_scores.get("endurance")
    endurance_score = endurance.score if endurance else 0.5
    cognition = trait_scores.get("cognition")
    cognition_score = cognition.score if cognition else 0.5

    # Выбираем шаблон по доминирующим трейтам
    if dom_score >= 0.70 and weak_score <= 0.35:
        # Выраженная сильная и слабая сторона
        if dom_cat == "temperament" and weak_cat == "social":
            return (
                f"{name} — эмоционально устойчивая особь с выраженной "
                f"независимостью от социального окружения. "
                f"Быстро гасит стресс и сохраняет ровное состояние "
                f"даже при тревоге в колонии. "
                f"Социальные связи формирует медленно, "
                f"но при наличии — держится за них крепко."
            )
        if dom_cat == "social" and weak_cat == "endurance":
            return (
                f"{name} — общительная особь с высокой потребностью "
                f"в контактах, но быстро утомляющаяся. "
                f"Активно строит связи и участвует в жизни колонии, "
                f"однако нуждается в частом отдыхе. "
                f"Риск хронической усталости при высокой плотности популяции."
            )
        if dom_cat == "lifespan" and weak_cat == "temperament":
            return (
                f"{name} несёт гены потенциального долгожителя, "
                f"однако чувствителен к хроническому стрессу. "
                f"Генетический бонус продолжительности жизни реализуется "
                f"только при низком кортизоле — "
                f"ключевой кандидат для отслеживания в будущих поколениях."
            )
        if dom_cat == "cognition" and weak_cat == "endurance":
            return (
                f"{name} — пытливый и быстро обучающийся агент "
                f"с ограниченной физической выносливостью. "
                f"Хорошо ориентируется в сложных ситуациях "
                f"и находит ресурсы, но требует частого сна. "
                f"Эффективен в стабильной среде с доступными ресурсами."
            )
        if dom_cat == "endurance" and weak_cat == "social":
            return (
                f"{name} — выносливая и физически крепкая особь-одиночка. "
                f"Долго остаётся активной без сна, "
                f"медленно накапливает усталость. "
                f"Социальные связи не являются приоритетом — "
                f"самодостаточна в условиях ресурсного дефицита."
            )

    # По доминирующей черте без явной слабой стороны
    if dom_score >= 0.70:
        if dom_cat == "temperament":
            return (
                f"{name} — эмоционально устойчивая особь "
                f"с хорошей аффективной регуляцией. "
                f"Быстро восстанавливается после стресса, "
                f"редко впадает в хронические тревожные состояния. "
                f"Надёжный член колонии в кризисных ситуациях."
            )
        if dom_cat == "social":
            return (
                f"{name} — высоко-социальная особь "
                f"с выраженным стадным инстинктом. "
                f"Активно участвует в грумингоe, формирует bonded-пары "
                f"и быстро интегрируется в новую социальную среду. "
                f"Ценный вклад в сплочённость колонии."
            )
        if dom_cat == "endurance":
            return (
                f"{name} — физически выносливая особь "
                f"с эффективным циклом сон-бодрствование. "
                f"Медленно устаёт и быстро восстанавливается, "
                f"что даёт преимущество при конкуренции "
                f"за ресурсы и партнёров."
            )
        if dom_cat == "cognition":
            return (
                f"{name} — любопытная и быстро обучающаяся особь "
                f"с широким полем восприятия. "
                f"Хорошо адаптируется к изменениям среды "
                f"и находит нестандартные решения. "
                f"Ценный исследователь в колонии."
            )
        if dom_cat == "lifespan":
            return (
                f"{name} несёт гены потенциального долгожителя. "
                f"При благоприятном кортизоле проживёт "
                f"значительно дольше среднего по колонии. "
                f"Ценный носитель опыта и генетического разнообразия "
                f"для будущих поколений."
            )

    # Сбалансированный профиль
    if max(ts.score for ts in trait_scores.values()) < 0.6 and \
       min(ts.score for ts in trait_scores.values()) > 0.4:
        return (
            f"{name} — особь со сбалансированным генетическим профилем "
            f"без выраженных крайностей. "
            f"Хорошо адаптируется к изменяющимся условиям "
            f"и не имеет критических уязвимостей. "
            f"Устойчивый, предсказуемый член колонии."
        )

    # Специфические комбинации
    if lifespan_score >= 0.65 and temp_score >= 0.60:
        return (
            f"{name} — перспективный долгожитель "
            f"с хорошей эмоциональной устойчивостью. "
            f"Сочетание длинного жизненного потенциала "
            f"и низкого хронического стресса — "
            f"оптимальная комбинация для эволюционного успеха линии."
        )

    if social_score >= 0.65 and cognition_score >= 0.60:
        return (
            f"{name} — социально развитая и любопытная особь. "
            f"Активно строит связи и исследует окружение, "
            f"быстро накапливает опыт взаимодействий. "
            f"Высокий потенциал для передачи знаний в колонии."
        )

    if endurance_score >= 0.65 and lifespan_score >= 0.60:
        return (
            f"{name} — физически крепкая особь "
            f"с генами долголетия. "
            f"Медленно устаёт и эффективно восстанавливается, "
            f"что позволяет реализовать генетический потенциал "
            f"длинной жизни в полной мере."
        )

    # Дефолт
    return (
        f"{name} — особь с умеренно выраженными чертами характера. "
        f"{'Наиболее развита сторона: ' + TRAIT_LABELS_RU.get(dom_cat, dom_cat) + '.' if dom_score >= 0.55 else ''} "
        f"{'Требует внимания: ' + TRAIT_LABELS_RU.get(weak_cat, weak_cat) + '.' if weak_score <= 0.40 else ''}"
    ).strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Core computation
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_gene(value: float, gene: GeneRange) -> float:
    span = gene.high - gene.low
    if span <= 0:
        return 0.5
    return max(0.0, min(1.0, (value - gene.low) / span))


def _gene_to_trait_score(normalized: float, polarity: str) -> float:
    if polarity == "high_good":
        return normalized
    if polarity == "low_good":
        return 1.0 - normalized
    if polarity == "both_extreme_bad":
        return 1.0 - abs(normalized - 0.5) * 2.0
    return 0.5   # neutral


def _trait_label(score: float) -> str:
    if score >= 0.80:
        return "очень высокое"
    if score >= 0.65:
        return "выше среднего"
    if score >= 0.45:
        return "умеренное"
    if score >= 0.30:
        return "ниже среднего"
    return "слабо выражено"


def _compute_trait_scores(genes: dict[str, float]) -> dict[str, TraitScore]:
    accum: dict[str, tuple[float, float, list[str]]] = {}
    for key, gene in GENE_REGISTRY.items():
        value = genes.get(key)
        if value is None:
            continue
        raw_score = _gene_to_trait_score(_normalize_gene(float(value), gene), gene.polarity)
        cat = gene.trait_category
        s, w, keys = accum.get(cat, (0.0, 0.0, []))
        accum[cat] = (s + raw_score * gene.weight, w + gene.weight, keys + [key])

    result: dict[str, TraitScore] = {}
    for cat in TRAIT_CATEGORIES:
        if cat not in accum:
            result[cat] = TraitScore(
                category=cat,
                score=0.5,
                label="нет данных",
                contributing_genes=[],
            )
            continue
        s, w, keys = accum[cat]
        score = s / w if w > 0 else 0.5
        result[cat] = TraitScore(
            category=cat,
            score=score,
            label=_trait_label(score),
            contributing_genes=keys,
        )
    return result


def _classify_strengths_weaknesses(
    trait_scores: dict[str, TraitScore],
) -> tuple[list[str], list[str], list[str]]:
    """Return (strengths, weaknesses, neutral) as human-readable strings."""

    STRENGTH_LABELS: dict[str, str] = {
        "temperament": "эмоциональная устойчивость",
        "social":      "социальный инстинкт",
        "endurance":   "физическая выносливость",
        "cognition":   "когнитивные способности",
        "lifespan":    "потенциал долгожития",
    }
    WEAKNESS_LABELS: dict[str, str] = {
        "temperament": "нестабильный темперамент",
        "social":      "слабые социальные драйвы",
        "endurance":   "низкая выносливость",
        "cognition":   "ограниченные когнитивные ресурсы",
        "lifespan":    "укороченный жизненный потенциал",
    }

    strengths, weaknesses, neutral = [], [], []
    for cat in TRAIT_CATEGORIES:
        ts = trait_scores.get(cat)
        if ts is None:
            continue
        if ts.score >= 0.68:
            strengths.append(STRENGTH_LABELS.get(cat, cat))
        elif ts.score <= 0.40:
            weaknesses.append(WEAKNESS_LABELS.get(cat, cat))
        elif 0.45 <= ts.score <= 0.58:
            neutral.append(TRAIT_LABELS_RU.get(cat, cat).lower())

    return strengths[:4], weaknesses[:4], neutral[:3]


def _analyze_mutations(
    genes: dict[str, float],
    inheritance_meta: dict[str, Any],
) -> list[MutationEffect]:
    """Build mutation effects from parent midpoint data."""
    if not isinstance(inheritance_meta, dict):
        return []

    midpoints = inheritance_meta.get("parent_midpoint_genes", {})
    if not isinstance(midpoints, dict) or not midpoints:
        # Fallback: use top_shifted_genes list if midpoint map absent
        shifted = inheritance_meta.get("top_shifted_genes", [])
        if not isinstance(shifted, list):
            return []
        # Reconstruct from shift alone
        effects: list[MutationEffect] = []
        for item in shifted:
            if not isinstance(item, dict):
                continue
            key = str(item.get("gene", item.get("key", "")))
            raw_delta = item.get("midpoint_shift", item.get("delta", 0.0))
            delta = float(raw_delta) if raw_delta else 0.0
            if not key or abs(delta) < 0.005:
                continue
            if key not in genes:
                continue
            parent_mid = float(genes[key]) - delta
            effects.append(_make_mutation(key, parent_mid, float(genes[key]), delta))
        return sorted(effects, key=lambda m: (
            {"major": 0, "moderate": 1, "minor": 2}.get(m.magnitude, 3),
            -abs(m.delta),
        ))[:8]

    effects = []
    for key, parent_mid in midpoints.items():
        current = genes.get(key)
        if current is None:
            continue
        delta = float(current) - float(parent_mid)
        if abs(delta) < 0.005:
            continue
        effects.append(_make_mutation(key, float(parent_mid), float(current), delta))

    return sorted(effects, key=lambda m: (
        {"major": 0, "moderate": 1, "minor": 2}.get(m.magnitude, 3),
        -abs(m.delta),
    ))[:8]


def _make_mutation(key: str, parent_mid: float, current: float, delta: float) -> MutationEffect:
    direction = "up" if delta > 0 else "down"
    magnitude = "major" if abs(delta) >= 0.15 else "moderate" if abs(delta) >= 0.05 else "minor"

    gene = GENE_REGISTRY.get(key)
    if gene is None:
        valence = "neutral"
        short = f"{'↑' if direction == 'up' else '↓'} сдвиг гена {key}"
        detail = f"Изменение на {delta:+.3f} относительно родительского среднего."
    else:
        # Determine valence
        if gene.polarity == "high_good":
            valence = "positive" if direction == "up" else "negative"
        elif gene.polarity == "low_good":
            valence = "positive" if direction == "down" else "negative"
        elif gene.polarity == "both_extreme_bad":
            norm = _normalize_gene(current, gene)
            valence = "negative" if (norm < 0.2 or norm > 0.8) else "positive"
        else:
            valence = "neutral"

        # Get consequence texts
        consequences = MUTATION_CONSEQUENCES.get(key, {})
        if direction in consequences:
            short, detail = consequences[direction]
        else:
            # Fallback to low_label/high_label
            if direction == "up":
                short = gene.high_label
            else:
                short = gene.low_label
            detail = f"Сдвиг {delta:+.3f} относительно родительского среднего."

    return MutationEffect(
        gene_key=key,
        parent_midpoint=parent_mid,
        current_value=current,
        delta=delta,
        direction=direction,
        valence=valence,
        consequence_short=short,
        consequence_detail=detail,
        magnitude=magnitude,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Lineage trend — BFS up to max_ancestors levels
# ─────────────────────────────────────────────────────────────────────────────

def build_lineage_trend(
    agent: Any,
    death_registry: Any,
    generation_index_map: dict[str, int],
    max_ancestors: int = 5,
) -> list[LineageTrendPoint] | None:
    """
    Build lineage trend by BFS through ancestor chain in DeathRegistry.

    Returns ordered list [oldest_ancestor, ..., current_agent]
    or None if no ancestor data is available.
    """
    if death_registry is None:
        return None

    def _safe_str(v: Any) -> str:
        return str(v) if v is not None else ""

    def _gene_vals(genome_genes: Any) -> dict[str, float]:
        if not isinstance(genome_genes, dict):
            return {}
        return {k: float(genome_genes.get(k, 0.0)) for k in LINEAGE_TRACKED_GENES
                if k in genome_genes}

    # BFS: collect ancestor chain
    ancestor_points: list[LineageTrendPoint] = []
    visited: set[str] = set()

    frontier_ids: list[str] = []
    raw_parents = getattr(agent, "parents", (None, None)) or (None, None)
    for pid in raw_parents:
        pid_s = _safe_str(pid).strip()
        if pid_s and pid_s not in visited:
            frontier_ids.append(pid_s)
            visited.add(pid_s)

    depth = 0
    while frontier_ids and depth < max_ancestors:
        next_frontier: list[str] = []
        for pid in frontier_ids:
            memorial = None
            try:
                memorial = death_registry.get_memorial(pid)
            except Exception:
                pass
            if memorial is None:
                continue

            name = _safe_str(getattr(memorial, "name", pid)) or pid
            point = LineageTrendPoint(
                agent_id=pid,
                display_name=name,
                generation=int(getattr(memorial, "generation", 0) or 0),
                gene_values=_gene_vals(getattr(memorial, "genome_genes", {})),
                stress_at_death=float(getattr(memorial, "final_stress", 0.0) or 0.0),
                cortisol_at_death=float(getattr(memorial, "final_cortisol", 0.0) or 0.0),
                lived_steps=int(getattr(memorial, "lived_steps", 0) or 0),
            )
            ancestor_points.append(point)

            # Queue grandparents
            gp_parents = getattr(memorial, "parents", (None, None)) or (None, None)
            for gp_id in gp_parents:
                gp_s = _safe_str(gp_id).strip()
                if gp_s and gp_s not in visited:
                    visited.add(gp_s)
                    next_frontier.append(gp_s)

        frontier_ids = next_frontier
        depth += 1

    if not ancestor_points:
        return None

    # Sort ancestors by generation ASC
    ancestor_points.sort(key=lambda p: (p.generation, p.agent_id))
    # Deduplicate by agent_id keeping first occurrence
    seen_ids: set[str] = set()
    unique_ancestors: list[LineageTrendPoint] = []
    for p in ancestor_points:
        if p.agent_id not in seen_ids:
            seen_ids.add(p.agent_id)
            unique_ancestors.append(p)

    # Add current agent at the end
    current_genome = getattr(agent, "genome", None)
    current_gene_source = getattr(current_genome, "genes", {}) if current_genome else getattr(agent, "genome_genes", {})
    current_genes = _gene_vals(current_gene_source)
    current_id = _safe_str(getattr(agent, "agent_id", ""))
    current_name = _safe_str(getattr(agent, "name", getattr(agent, "display_name", current_id))) or current_id
    current_point = LineageTrendPoint(
        agent_id=current_id,
        display_name=current_name,
        generation=int(getattr(agent, "generation", 0) or 0),
        gene_values=current_genes,
        stress_at_death=0.0,
        cortisol_at_death=0.0,
        lived_steps=int(getattr(agent, "lived_steps", 0) or 0),
    )

    result = unique_ancestors + [current_point]
    return result if len(result) >= 2 else None


# ─────────────────────────────────────────────────────────────────────────────
#  Trend analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_trend(points: list[LineageTrendPoint], gene_key: str) -> str:
    """Return direction string for gene trend across lineage points."""
    vals = [p.gene_values[gene_key] for p in points if gene_key in p.gene_values]
    if len(vals) < 2:
        return "↔"

    gene = GENE_REGISTRY.get(gene_key)
    span = (gene.high - gene.low) if gene else 1.0
    if span <= 0:
        span = 1.0

    bucket = max(1, len(vals) // 3)
    first_mean = sum(vals[:bucket]) / bucket
    last_mean = sum(vals[-bucket:]) / bucket
    total_delta = last_mean - first_mean
    threshold = span * 0.05   # 5% диапазона = значимое изменение

    if total_delta > threshold:
        # Проверяем монотонность
        if all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)):
            return "↗ стабильно растёт"
        return "↗ растёт"
    if total_delta < -threshold:
        if all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
            return "↘ стабильно снижается"
        return "↘ снижается"
    return "↔ стабильно"


def describe_lineage_trend(points: list[LineageTrendPoint], gene_key: str) -> str:
    """Return a short human-readable trend explanation in Russian."""
    vals = [p.gene_values[gene_key] for p in points if gene_key in p.gene_values]
    if len(vals) < 2:
        return "недостаточно данных"

    gene = GENE_REGISTRY.get(gene_key)
    span = (gene.high - gene.low) if gene else 1.0
    if span <= 0:
        span = 1.0
    bucket = max(1, len(vals) // 3)
    first_mean = sum(vals[:bucket]) / bucket
    last_mean = sum(vals[-bucket:]) / bucket
    delta = last_mean - first_mean
    threshold = span * 0.05

    if delta > threshold:
        direction = "up"
        direction_text = "растёт"
    elif delta < -threshold:
        direction = "down"
        direction_text = "снижается"
    else:
        direction = "flat"
        direction_text = "стабильно"

    meaning = LINEAGE_TREND_MEANINGS_RU.get(gene_key, {}).get(direction, "линия без выраженного сдвига")
    return f"{direction_text}: {meaning}"


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_portrait(
    genes: dict[str, float],
    genome_inheritance_meta: dict[str, Any],
    display_name: str = "",
) -> GenomePortrait:
    """Build complete genome portrait. Never raises."""
    try:
        trait_scores = _compute_trait_scores(genes)
        strengths, weaknesses, neutral = _classify_strengths_weaknesses(trait_scores)
        stress_gene = GENE_REGISTRY.get("af_decay_stress")
        if stress_gene is not None and "af_decay_stress" in genes:
            stress_norm = _normalize_gene(float(genes["af_decay_stress"]), stress_gene)
            if stress_norm >= 0.80 and not any("стресс" in item.lower() for item in weaknesses):
                weaknesses.insert(0, stress_gene.high_label)
                weaknesses = weaknesses[:4]
        summary = _generate_summary(trait_scores, genes, display_name)
        mutations = _analyze_mutations(genes, genome_inheritance_meta)
        return GenomePortrait(
            trait_scores=trait_scores,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            neutral_traits=neutral,
            mutations=mutations,
            lineage_trend=None,
        )
    except Exception:
        empty_scores = {
            cat: TraitScore(cat, 0.5, "нет данных", [])
            for cat in TRAIT_CATEGORIES
        }
        return GenomePortrait(
            trait_scores=empty_scores,
            summary="Генетические данные недоступны.",
            strengths=[],
            weaknesses=[],
            neutral_traits=[],
            mutations=[],
            lineage_trend=None,
        )


def wrap_text(text: str, max_chars: int = 60) -> list[str]:
    """Split text into lines by words. Max 8 lines."""
    words = text.split()
    lines: list[str] = []
    current = ""
    truncated = False
    for word in words:
        candidate = (current + " " + word).strip() if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= 8:
            truncated = True
            break
    if current and len(lines) < 8:
        lines.append(current)
    if len(lines) >= 8 and words:
        consumed = " ".join(lines).split()
        truncated = truncated or len(consumed) < len(words)
    if truncated and lines:
        suffix = "..."
        room = max(0, max_chars - len(suffix))
        lines[-1] = (lines[-1][:room].rstrip() + suffix) if room else suffix
    return lines or [""]
