# Deliberative Planning v2

Russian version: [spec_deliberative_planning_v2.ru.md](spec_deliberative_planning_v2.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Episodic Rollout + Exploration Bonus + Uncertainty-Adaptive Depth + HIE-003 Tree Overlay**

---

## 1. Goal

Strengthen the agent's deliberative mode by means of:

- **Episodic trajectory rollout** — use of experience sequences from the hippocampus
- **Uncertainty-adaptive planning depth** — planning depth depends on global uncertainty
- **Value-of-information exploration bonus** — encouragement of actions in states of low confidence

The aim is to raise learning speed, the quality of decisions in novel states, and the efficiency of the deliberative mode.

---

## 2. Constraints

### Architectural constraints

The solution must not change:

- `BasalGangliaGate`
- `ThalamicGate`
- `SleepManager` learning pipeline
- `ValueLayer` update rules

> Planning may only modify `pressure_vector`.

### Computational constraints

Planning must remain light:

```
max_rollout_samples_per_action  ≤ 8
max_rollout_depth               ≤ 6
max_actions_per_planning        ≤ 32
```

Worst-case complexity: `O(actions × samples × depth)`.  
Typically: fewer than 500 operations.

### Memory constraints

Planning must not:

- create new persistent structures
- modify hippocampus memory
- store trajectories

> Only existing `Experience` objects are used.

---

## 3. Configuration Parameters

Added to `Agent`:

```python
planning_rollout_depth           = 3
planning_rollout_samples         = 6
planning_uncertainty_depth_gain  = 2.0
planning_exploration_gain        = 0.15
planning_min_confidence          = 0.2
```

### Parameter semantics

| Parameter                         | Description                                              |
|-----------------------------------|----------------------------------------------------------|
| `planning_rollout_depth`          | Base simulation depth (`depth_base = 3`)                 |
| `planning_rollout_samples`        | How many episodic trajectories to use (`= 6`)            |
| `planning_uncertainty_depth_gain` | Increases depth under high uncertainty                   |
| `planning_exploration_gain`       | Weight of the exploration bonus                          |

---

## 4. Planning Pipeline

Planning runs only if:

```
decision_mode == DELIBERATIVE
```

**Full algorithm:**

```
1  retrieve experiences per action
2  estimate reward_mean
3  compute rollout value
4  combine with model value
5  add exploration bonus
6  bias pressure_vector
```

---

## 5. Rollout Estimation

### Definition

A rollout is a simulation of a reward sequence through the replay graph.

### Algorithm

```python
for each experience:
    simulate trajectory
    accumulate discounted reward
return max trajectory value
```

### Formula

```
trajectory_value = Σ γ^t * reward_t
```

Where `γ = value_layer.gamma_default`.

---

### 5.A HIE-003 Tree Overlay (implemented, with HIE-002 fallback)

Planning rollout is now a two-source estimate:

1. `memory_rollout_value` from episodic replay trajectories.
2. `imagined_value` from hippocampal imagination:
   - HIE-003 tree mode (`imagination_enable_action_sequences=True`):
     `generate_action_tree_imagination(...)` and `action_values[action_id]`.
   - HIE-002 fallback mode (`imagination_enable_action_sequences=False`):
     `generate_structured_imagination(...)` with `quantile(values, 0.7)`.

Aggregation rule:

```python
blend = imagination_value_blend
rollout_value = (
    (1 - blend) * memory_rollout_value
    + blend * imagined_value
)
```

Hard limits for HIE-003 tree path:

```text
imagination_action_branching <= 4
imagination_max_tree_nodes   <= 128
imagination_depth            <= 5
```

Hard limits for HIE-002 fallback path:

```text
imagination_samples          <= 8
imagination_depth            <= 5
imagination_branching        <= 4
imagination_max_graph_nodes  <= 96
imagination_max_graph_edges  <= 192
imagination_max_nodes        <= 96
trajectory_confidence        in [0, 1]
discount_stop                < 0.02
```

Imagination value terms:

```text
value_estimate =
    discounted_reward
    + imagination_goal_bias * V(last_state)
    + imagination_state_novelty_weight * novelty_score

trajectory_value = value_estimate * confidence * (imagination_value_backup ** (depth - 1))
```

## 6. Q-value Evaluation

For each action the following is computed:

```
Q(action) =
      reward_mean
    + γ * max(model_value, rollout_value)
    + edpc_bias
    + exploration_bonus
```

### Components

**`reward_mean`** — mean reward from similar states.

**`model_value`** — ValueLayer prediction: `V(s')`.

**`rollout_value`** — the aggregated estimate from the memory rollout and the imagined rollout:
`(1 - imagination_value_blend) * memory_rollout_value + imagination_value_blend * imagined_value`.

**`exploration_bonus`:**

```
exploration_bonus = exploration_gain × (1 − confidence)
```

Where `confidence ∈ [0, 1]`.

---

## 7. Uncertainty-Adaptive Depth

Rollout depth depends on `global_uncertainty`:

```
rollout_depth =
    planning_rollout_depth
  + global_uncertainty × planning_uncertainty_depth_gain
```

**Example:**

| uncertainty | depth |
|-------------|-------|
| 0.0         | 3     |
| 0.5         | 4     |
| 1.0         | 5     |

---

## 8. Pressure Biasing

After the Q values have been computed:

```
1  normalize Q
2  scale by support
3  add to pressure_vector
```

**Formula:**

```
pressure[action] += gain × Q_norm × support
```

---

## 9. Safety and Protection against Degradation

Planning must ignore an action if:

```
support < 0.05
```

or:

```
confidence < planning_min_confidence
```

> This prevents amplification of noise.

---

## 10. Telemetry

Added to `Agent._last_decision_arbitration_output`.

**New fields:**

- `planning_rollout_depth`
- `planning_rollout_samples`
- `planning_rollout_used`
- `planning_exploration_bonus_mean`
- `planning_imagination_enabled`
- `planning_imagination_samples`
- `planning_imagination_depth`
- `planning_imagined_rollouts_used`
- `planning_imagined_value_mean`
- `planning_imagined_value_max`
- `planning_imagined_trajectory_count`
- `planning_imagined_confidence_mean`
- `planning_imagined_novelty_mean`
- `planning_imagination_novelty_hits`
- `planning_imagination_tree_nodes`
- `planning_imagination_tree_edges`
- `planning_imagination_action_count`
- `planning_imagination_branching`

---

## 11. Test Cases

### Test 1 — Rollout improves the decision

**Setup:**

```
A1: immediate reward = 0.2
A2: immediate reward = 0.0, trajectory → reward 0.8
```

**Expected:** the planner chooses A2.

### Test 2 — Uncertainty increases depth

**Setup:** `uncertainty = 0.9`, `base_depth = 3`, `gain = 2`.

**Expected:** `depth = 4` or `5`.

### Test 3 — Exploration bonus

**Setup:** `confidence = 0.1`, `exploration_gain = 0.15`.

**Expected:** `bonus ≈ 0.135`.

### Test 4 — Planning disabled

**Setup:** `deliberative_planning_enabled = False`.

**Expected:** `pressure_vector` unchanged.

### Test 5 — Memory absent

**Setup:** the hippocampus is empty.

**Expected:** planning is skipped.

### Test 6 — HIE-003 tree mode telemetry

**Setup:** `imagination_enable_action_sequences = True`, multi-action candidates.

**Expected:** metadata includes non-negative:
`planning_imagination_tree_nodes`,
`planning_imagination_tree_edges`,
`planning_imagination_action_count`,
`planning_imagination_branching`.

---

## 12. Performance

- Expected overhead per step: **< 1 ms**
- Memory overhead: **0**

---

## 13. Backward Compatibility

Complete. If the parameters are absent, the system falls back to current behaviour.

---

## 14. Acceptance Criteria

The feature is considered implemented if:

- all tests pass
- deliberative decisions change when trajectories exist
- runtime overhead < 2 ms
- no change to learning during wake
- no modification of hippocampus memory

---

## 15. Expected Effect

| Metric                 | Before   | After    |
|------------------------|----------|----------|
| learning speed         | baseline | ↑        |
| exploration efficiency | low      | ↑↑       |
| planning depth         | fixed    | adaptive |
| decision quality       | medium   | ↑        |
