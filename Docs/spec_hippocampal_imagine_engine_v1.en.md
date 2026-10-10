# Hippocampal Imagine Engine v1 Specification

Russian version: [spec_hippocampal_imagine_engine_v1.ru.md](spec_hippocampal_imagine_engine_v1.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**SPEC VERSION:** HIE-001
**TARGET:** `Agent.deliberative_planning` pipeline
**STATUS:** implementation-ready

**Dependencies:**
- Experience graph
- `state_similarity()`
- `ValueLayer`
- `action_index`

---

## 1. Motivation

Current planning uses memory trajectories. Animals (hippocampus), however, perform **replay + recombination + imagination**: they simulate trajectories that never occurred.

**Example:**

```
ctx_food + action=go_left
ctx_food + action=climb_tree
```

The hippocampus can imagine:

```
ctx_food → climb_tree → eat
```

even if that sequence never happened.

Therefore:

```
rollout source =
    memory trajectories
  + imagined trajectories
```

---

## 2. Design Overview

A module `HippocampalImagineEngine` is added. It generates `imagined_rollouts` from similar states, the experience graph, and action transitions.

**Pipeline:**

```
decision
   ↓
deliberative planning
   ↓
HIE (generate imagined trajectories)
   ↓
rollout evaluation
   ↓
pressure modulation
```

---

## 3. Agent Configuration

The following parameters are added:

```python
self.imagination_enabled: bool              = True

self.imagination_samples: int               = 8
self.imagination_depth: int                 = 4
self.imagination_branching: int             = 3
self.imagination_similarity_threshold: float = 0.6

self.imagination_reward_decay: float        = 0.9
self.imagination_novelty_bonus: float       = 0.05

self.imagination_max_nodes: int             = 64
```

**Hard limits:**

```
imagination_samples   ≤ 8
imagination_depth     ≤ 5
imagination_branching ≤ 4
```

---

## 4. Core API

The following method is added:

```python
def _generate_imagined_rollouts(
    self,
    start_state: Mapping[str, Any],
    action_id: str,
    experiences: list,
    depth: int,
) -> list[float]:
```

**Returns:** a list of imagined trajectory values, where each value is a discounted cumulative reward.

---

## 5. Imagination Algorithm

**Pseudocode:**

```
for sample in imagination_samples:

    node = random similar experience

    for step in depth:

        candidate_experiences =
            experiences with similar state

        choose random transition

        accumulate reward

        move to next state
```

**Formal pseudocode:**

```python
values = []

for s in range(samples):

    current = random_similar_experience()

    total    = 0
    discount = 1

    for d in range(depth):

        next_candidates =
            find experiences with similar state

        if empty:
            break

        next_exp = random_choice(next_candidates)
        reward   = next_exp.reward

        total    += discount * reward
        discount *= gamma * imagination_reward_decay
        current   = next_exp

    values.append(total)
```

---

## 6. Similarity Search

The existing function `state_similarity(a, b)` is used.

**Filter:** `similarity >= imagination_similarity_threshold`.
**Limit:** `max candidates = imagination_branching`.
**Selection:** top K by similarity.

---

## 7. Integration with Planning

`_apply_deliberative_planning()` is modified.

**Before:**

```python
rollout_value = estimate_rollout_value(...)
```

**After:**

```python
memory_value    = estimate_rollout_value(...)
imagined_values = generate_imagined_rollouts(...)

imagined_value  = quantile(imagined_values, 0.7)

rollout_value   = max(memory_value, imagined_value)
```

---

## 8. Novelty Bonus

Exploration of imagined trajectories is encouraged. If an imagined trajectory uses a state **never observed with the given action**:

```
value += imagination_novelty_bonus
```

---

## 9. Safety Guards

Limits that prevent combinatorial explosion:

```
total_nodes ≤ imagination_max_nodes
```

Termination also occurs if:

```
discount < 0.02
```

---

## 10. Complexity Budget

**Upper bound:** `O(actions × samples × depth)`.

**Limits:**

```
actions ≤ 32
samples ≤ 8
depth   ≤ 5
```

**Worst case:** `32 × 8 × 5 = 1280` node visits — safe.

---

## 11. Telemetry

The following fields are added to planning metadata:

- `imagination_enabled`
- `imagination_samples`
- `imagination_depth`
- `imagined_rollouts_used`
- `imagined_value_mean`
- `imagined_value_max`
- `imagination_novelty_hits`

---

## 12. Behavioural Effects

The agent acquires the capacity for:

**1. Shortcut discovery:**

```
A → B → C
A → D → C

agent may imagine: A → D → B → C
```

**2. Reward propagation** — a long-delayed reward becomes visible.

**3. Planning under sparse reward** — even when memory is incomplete.

---

## 13. Test Cases

**File:** `tests/test_imagination_engine_spec_001.py`

### Test 1 — Imagination produces trajectories

**Memory:** `A → B (0)`, `B → C (1)`. The agent imagines `A → B → C`.
**Assert:** `imagined_value > 0`.

### Test 2 — Similarity filtering

Experiences with `similarity < threshold` must be ignored.

### Test 3 — Bounded rollout count

**Ensure:** `imagined_rollouts ≤ imagination_samples`.

### Test 4 — Bounded depth

**Ensure:** `depth ≤ imagination_depth`.

### Test 5 — Planning integration

When `imagination_enabled = True`: `planned_pressure > baseline` for reward-delayed actions.

### Test 6 — Disabled mode

When `imagination_enabled = False`: the planner behaves identically to the previous version.

---

## 14. Expected Cognitive Behaviour

The system is equivalent to:

| Architectural component | Biological analogue        |
|-------------------------|----------------------------|
| Experience graph        | episodic memory            |
| Similarity search       | place cell overlap         |
| Rollout sampling        | hippocampal replay         |
| Planning Q value        | prefrontal evaluation      |

This is observed in rodents and in humans, in navigation tasks.

---

## 15. Minimal Implementation (~120 lines)

| Component                        | Size       |
|----------------------------------|------------|
| `_generate_imagined_rollouts`    | ~70 lines  |
| Integration in planning          | ~20 lines  |
| Config + telemetry               | ~30 lines  |
| **Total**                        | **~120 lines** |

---

## 16. What This Unlocks Next

After HIE the agent can support:

| Capability                | Mechanism                                      |
|---------------------------|------------------------------------------------|
| Cognitive Map             | hippocampal graph                              |
| Goal Directed Search      | A\*, Dyna-Q, successor representation          |
| Counterfactual reasoning  | *"what if I did X"*                            |

---

## 17. Implementation Priority

Recommended order:

```
1  add config
2  implement generator
3  integrate into planning
4  add telemetry
5  add tests
```
