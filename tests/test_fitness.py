import math

from fitness import CRITERIA_ORDER, FitnessEvaluator, FitnessVector


class _Channel:
    def __init__(self, selection_count: int):
        self.selection_count = selection_count


class _ValueLayer:
    def __init__(self, last_td_error: float = 0.1, online_update_count: int = 100, sleep_update_count: int = 50):
        self._snapshot = {
            "last_td_error": last_td_error,
            "online_update_count": online_update_count,
            "sleep_update_count": sleep_update_count,
        }

    def snapshot(self):
        return dict(self._snapshot)


class _Neuromodulators:
    def __init__(self, cortisol: float):
        self.cortisol = cortisol


class _Experience:
    def __init__(self, consolidation_weight: float):
        self.consolidation_weight = consolidation_weight


class _Hippocampus:
    def __init__(self, experiences=None):
        self.experiences = list(experiences or [])


class _Genome:
    def __init__(self, generation: int):
        self.generation = generation


class MockAgent:
    lived_steps = 500
    expected_lifetime_steps = 1000
    affective_history = [{"valence": 0.3, "arousal": 0.5}] * 10
    td_error_history = [0.1, 0.2, 0.15]
    cortisol_history = [0.05, 0.08, 0.06]
    bg_action_channels = {
        "eat": _Channel(5),
        "sleep": _Channel(3),
        "play": _Channel(2),
    }
    value_layer = _ValueLayer(last_td_error=0.1, online_update_count=100, sleep_update_count=50)
    hippocampus = _Hippocampus()
    neuromodulators = _Neuromodulators(cortisol=0.07)
    agent_id = "test_agent"
    genome = _Genome(generation=2)


def _build_fitness(agent_id: str, values: tuple[float, float, float, float, float, float, float]) -> FitnessVector:
    return FitnessVector(
        longevity=values[0],
        affective_range=values[1],
        prediction_skill=values[2],
        stress_resilience=values[3],
        behavioral_diversity=values[4],
        learning_efficiency=values[5],
        memory_quality=values[6],
        agent_id=agent_id,
        generation=1,
        evaluation_step=100,
    )


def test_tc_01_evaluate_returns_valid_fitness_vector():
    evaluator = FitnessEvaluator()
    fitness = evaluator.evaluate(MockAgent())

    for criterion in CRITERIA_ORDER:
        value = getattr(fitness, criterion)
        assert 0.0 <= value <= 1.0

    assert abs(fitness.longevity - 0.5) < 1e-9
    assert fitness.agent_id == "test_agent"
    assert fitness.generation == 2
    assert fitness.evaluation_step == 500


def test_tc_02_evaluate_with_empty_agent_is_safe():
    class EmptyAgent:
        pass

    evaluator = FitnessEvaluator()
    fitness = evaluator.evaluate(EmptyAgent())

    assert isinstance(fitness, FitnessVector)
    for criterion in CRITERIA_ORDER:
        assert 0.0 <= getattr(fitness, criterion) <= 1.0


def test_tc_03_longevity_is_clamped_to_one():
    class LongLivedAgent:
        lived_steps = 99999
        expected_lifetime_steps = 1000

    evaluator = FitnessEvaluator()
    fitness = evaluator.evaluate(LongLivedAgent())
    assert fitness.longevity == 1.0


def test_tc_04_behavioral_diversity_uniform_distribution_is_one():
    class UniformAgent:
        bg_action_channels = {f"action_{i}": _Channel(10) for i in range(4)}

    evaluator = FitnessEvaluator()
    fitness = evaluator.evaluate(UniformAgent())
    assert abs(fitness.behavioral_diversity - 1.0) < 1e-9


def test_tc_05_behavioral_diversity_single_action_is_zero():
    class SingleActionAgent:
        bg_action_channels = {
            "eat": _Channel(100),
            "sleep": _Channel(0),
            "play": _Channel(0),
        }

    evaluator = FitnessEvaluator()
    fitness = evaluator.evaluate(SingleActionAgent())
    assert abs(fitness.behavioral_diversity - 0.0) < 1e-9


def test_tc_06_dominates_definition_is_correct():
    evaluator = FitnessEvaluator()

    a = _build_fitness("a", (0.9, 0.8, 0.7, 0.9, 0.8, 0.7, 0.8))
    b = _build_fitness("b", (0.8, 0.7, 0.6, 0.8, 0.7, 0.6, 0.7))
    c = _build_fitness("c", (0.9, 0.9, 0.5, 0.9, 0.8, 0.7, 0.8))

    assert evaluator.dominates(a, b) is True
    assert evaluator.dominates(b, a) is False
    assert evaluator.dominates(a, c) is False
    assert evaluator.dominates(c, a) is False


def test_tc_07_equal_vectors_do_not_dominate_each_other():
    evaluator = FitnessEvaluator()
    a = _build_fitness("a", (0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8))
    b = _build_fitness("b", (0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8))

    assert evaluator.dominates(a, b) is False
    assert evaluator.dominates(b, a) is False


def test_tc_08_pareto_rank_single_agent():
    evaluator = FitnessEvaluator()
    fitness = _build_fitness("solo", (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5))

    ranks = evaluator.pareto_rank([fitness])

    assert len(ranks) == 1
    assert ranks[0].rank == 1
    assert ranks[0].crowding_distance == float("inf")


def test_tc_09_pareto_rank_with_clear_dominance():
    evaluator = FitnessEvaluator()
    dominant = _build_fitness("dominant", (0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9))
    dominated = _build_fitness("dominated", (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5))

    ranks = evaluator.pareto_rank([dominant, dominated])
    rank_map = {item.agent_id: item.rank for item in ranks}

    assert rank_map["dominant"] == 1
    assert rank_map["dominated"] == 2


def test_tc_10_pareto_rank_with_incomparable_agents():
    evaluator = FitnessEvaluator()
    a = _build_fitness("a", (0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1))
    b = _build_fitness("b", (0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.9))

    ranks = evaluator.pareto_rank([a, b])
    rank_map = {item.agent_id: item.rank for item in ranks}

    assert rank_map["a"] == 1
    assert rank_map["b"] == 1


def test_tc_11_pareto_crowding_distance_extremes_are_inf():
    evaluator = FitnessEvaluator()
    vectors = [
        _build_fitness("a0", (0.1, 0.5, 0.9, 0.5, 0.5, 0.5, 0.5)),
        _build_fitness("a1", (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
        _build_fitness("a2", (0.9, 0.5, 0.1, 0.5, 0.5, 0.5, 0.5)),
    ]

    ranks = evaluator.pareto_rank(vectors)
    rank_one = [item for item in ranks if item.rank == 1]
    crowding = {item.agent_id: item.crowding_distance for item in rank_one}

    assert crowding["a0"] == float("inf")
    assert crowding["a2"] == float("inf")
    assert crowding["a1"] < float("inf")


def test_tc_12_scalar_score_is_in_range_and_matches_mean_for_equal_weights():
    evaluator = FitnessEvaluator()
    fitness = _build_fitness("test", (0.7, 0.6, 0.8, 0.9, 0.5, 0.4, 0.6))

    score = evaluator.scalar_score(fitness)

    assert 0.0 <= score <= 1.0
    expected = (0.7 + 0.6 + 0.8 + 0.9 + 0.5 + 0.4 + 0.6) / 7.0
    assert abs(score - expected) < 1e-9


def test_tc_13_scalar_score_respects_custom_weights():
    weights = {
        "longevity": 2.0,
        "affective_range": 1.0,
        "prediction_skill": 1.0,
        "stress_resilience": 1.0,
        "behavioral_diversity": 1.0,
        "learning_efficiency": 1.0,
        "memory_quality": 1.0,
    }
    evaluator = FitnessEvaluator(weights=weights)
    fitness = _build_fitness("test", (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    score = evaluator.scalar_score(fitness)
    assert abs(score - (2.0 / 8.0)) < 1e-9


def test_tc_14_fitness_dict_round_trip():
    evaluator = FitnessEvaluator()
    original = _build_fitness("agent_42", (0.7, 0.6, 0.8, 0.9, 0.5, 0.4, 0.6))

    data = evaluator.fitness_to_dict(original)
    restored = evaluator.fitness_from_dict(data)

    for criterion in CRITERIA_ORDER:
        assert abs(getattr(original, criterion) - getattr(restored, criterion)) < 1e-12
    assert restored.agent_id == original.agent_id
    assert restored.generation == original.generation
    assert restored.evaluation_step == original.evaluation_step


def test_tc_15_evaluate_population_preserves_input_order():
    class SimpleAgent:
        def __init__(self, steps: int, agent_id: str):
            self.lived_steps = steps
            self.expected_lifetime_steps = 1000
            self.agent_id = agent_id

    evaluator = FitnessEvaluator()
    agents = [SimpleAgent(100 * i, f"agent_{i}") for i in range(5)]
    results = evaluator.evaluate_population(agents)

    assert len(results) == 5
    for idx, result in enumerate(results):
        assert result.agent_id == f"agent_{idx}"


def test_tc_16_pareto_rank_empty_list():
    evaluator = FitnessEvaluator()
    assert evaluator.pareto_rank([]) == []


def test_tc_17_stress_resilience_inverts_cortisol():
    class HighCortisolAgent:
        cortisol_history = [0.9] * 20
        neuromodulators = _Neuromodulators(cortisol=0.9)

    class LowCortisolAgent:
        cortisol_history = [0.05] * 20
        neuromodulators = _Neuromodulators(cortisol=0.05)

    evaluator = FitnessEvaluator()
    high = evaluator.evaluate(HighCortisolAgent())
    low = evaluator.evaluate(LowCortisolAgent())

    assert high.stress_resilience < low.stress_resilience
    assert high.stress_resilience < 0.2
    assert low.stress_resilience > 0.8


def test_tc_18_criteria_names_are_deterministic():
    evaluator = FitnessEvaluator()
    names = evaluator.criteria_names()

    assert names == CRITERIA_ORDER
    assert len(names) == 7


def test_fitness_from_dict_defaults_for_missing_fields():
    evaluator = FitnessEvaluator()
    restored = evaluator.fitness_from_dict({})

    for criterion in CRITERIA_ORDER:
        assert getattr(restored, criterion) == 0.0
    assert restored.agent_id == ""
    assert restored.generation == 0
    assert restored.evaluation_step == 0


def test_pareto_results_are_sorted_by_rank_then_descending_crowding_distance():
    evaluator = FitnessEvaluator()
    vectors = [
        _build_fitness("x0", (0.1, 0.5, 0.9, 0.5, 0.5, 0.5, 0.5)),
        _build_fitness("x1", (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
        _build_fitness("x2", (0.9, 0.5, 0.1, 0.5, 0.5, 0.5, 0.5)),
        _build_fitness("x3", (0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2)),
    ]

    ranked = evaluator.pareto_rank(vectors)
    ordered_pairs = [(item.rank, item.crowding_distance) for item in ranked]
    sorted_pairs = sorted(
        ordered_pairs,
        key=lambda item: (item[0], float("-inf") if math.isinf(item[1]) else -item[1]),
    )
    assert ordered_pairs == sorted_pairs
