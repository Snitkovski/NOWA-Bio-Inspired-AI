# FitnessEvaluator Implementation Guide (Package D)

Russian version: [FITNESS_EVALUATOR.ru.md](FITNESS_EVALUATOR.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 25, 2026.

---

## Scope

`src/fitness.py` implements a standalone multi-objective fitness evaluator for NOWA agents. The module uses only the Python standard library and reads agent state through public attributes.

Key goals:
1. compute bounded fitness vectors across 7 criteria
2. keep evaluation side-effect free (read-only)
3. support deterministic Pareto ranking (NSGA-II style fronts and crowding distance)
4. provide scalar fallback scoring with configurable normalized weights
5. support serialization for evolutionary workflows

---

## Implemented Objects

### `FitnessVector` (`frozen=True`)

Fields:
- `longevity`
- `affective_range`
- `prediction_skill`
- `stress_resilience`
- `behavioral_diversity`
- `learning_efficiency`
- `memory_quality`
- `agent_id`
- `generation`
- `evaluation_step`

Behaviour:
1. all criteria are clamped to `[0.0, 1.0]` in `__post_init__`
2. `generation` and `evaluation_step` are normalized to non-negative integers
3. `agent_id` is always normalized to a string

### `ParetoRank` (`frozen=True`)

Fields:
- `agent_id`
- `rank`
- `crowding_distance`
- `fitness`

### `FitnessEvaluator`

Public API:
- `evaluate(agent) -> FitnessVector`
- `evaluate_population(agents) -> List[FitnessVector]`
- `pareto_rank(fitness_vectors) -> List[ParetoRank]`
- `scalar_score(fitness) -> float`
- `dominates(a, b) -> bool`
- `criteria_names() -> List[str]`
- `fitness_to_dict(fitness) -> dict`
- `fitness_from_dict(data) -> FitnessVector`

---

## Criteria Contracts

Implemented criteria from `Docs/SPEC_D_FitnessEvaluator.md`:
1. `longevity`: `min(1.0, lived_steps / expected_lifetime_steps)`
2. `affective_range`: average per-axis `std(affective_history)` normalized by `0.5`
3. `prediction_skill`: `1.0 - mean(abs(td_error_history))` with fallback to `value_layer.snapshot()["last_td_error"]`
4. `stress_resilience`: `1.0 - mean(cortisol_history)` with fallback to `neuromodulators.cortisol`
5. `behavioral_diversity`: normalized entropy over `bg_action_channels[*].selection_count`
6. `learning_efficiency`: `(sleep_update_count / (online_update_count + 1)) / 3.0`, clamped
7. `memory_quality`: mean `consolidation_weight` over the last 128 hippocampus experiences

Robustness rules:
1. malformed or missing fields degrade to the criterion value `0.0`
2. the evaluator does not raise during the evaluation path
3. the evaluator never mutates agent state

---

## Agent Runtime Support

`Agent` now maintains rolling histories used by package D:
- `agent.affective_history: List[dict]`
- `agent.td_error_history: List[float]`
- `agent.cortisol_history: List[float]`

Runtime behaviour in `Agent.step()`:
1. append the current affective-axes snapshot
2. append the current TD error (from the current `value_update` or `value_layer.snapshot`)
3. append the current cortisol value
4. keep only the recent `256` entries (`agent._fitness_history_limit`)

This support is implemented in:
- `src/agent.py`

---

## Pareto Ranking Behaviour

`FitnessEvaluator.pareto_rank(...)` implements deterministic NSGA-II style ranking:
1. build the non-dominated front (`rank=1`)
2. iteratively remove fronts and assign increasing ranks
3. compute crowding distance inside each front
4. assign `float("inf")` crowding distance to the min and max boundary points per criterion
5. return a list sorted by `(rank ASC, crowding_distance DESC)` with a stable index tie-break

---

## Test Coverage

Primary suites:
- `tests/test_fitness.py`
- `tests/test_fitness_agent_integration.py`

Coverage includes:
1. TC-01..TC-18 from `Docs/SPEC_D_FitnessEvaluator.md`
2. dictionary round-trip and default handling
3. deterministic Pareto ordering behaviour
4. agent-level history accumulation and rolling-limit behaviour

Latest local run:

```text
python -m pytest tests/test_fitness.py tests/test_fitness_agent_integration.py -q
21 passed in 0.22s
```

Project-wide regression (excluding Demo):

```text
python -m pytest tests -q
681 passed, 3 skipped
```
