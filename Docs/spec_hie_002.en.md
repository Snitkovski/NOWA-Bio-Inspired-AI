# HIE-002 Specification

Russian version: [spec_hie_002.ru.md](spec_hie_002.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Hippocampal Imagine Engine v2 — Structured Prospective Simulation

**Status:** EXTENSION  
**Compatible with:** HIE-001

---

## Purpose

Add structured imagination:

- **temporal stitching** — joining unrelated memory episodes
- **goal-biased imagination** — preference for trajectories that lead to valuable states
- **state novelty discovery** — discovery of new states
- **trajectory confidence** — assessment of trajectory reliability

---

## 1. New capabilities

| Function                   | Description                               |
|----------------------------|-------------------------------------------|
| trajectory recombination   | joining different episodes                |
| goal bias                  | search for valuable states                |
| trajectory confidence      | reliability assessment                    |
| novelty scoring            | discovery of new states                   |
| imagined transition graph  | internal simulation graph                 |

---

## 2. New agent parameters

Add to `Agent.__init__`:

```python
# HIE-002 parameters
self.imagination_goal_bias              = 0.35
self.imagination_confidence_decay       = 0.9
self.imagination_state_novelty_weight   = 0.4
self.imagination_value_blend            = 0.6
self.imagination_max_graph_nodes        = 96
self.imagination_max_graph_edges        = 192
```

**Constraints:**

```
0 ≤ goal_bias            ≤ 1
0 ≤ confidence_decay     ≤ 1
0 ≤ novelty_weight       ≤ 1
0 ≤ value_blend          ≤ 1
```

---

## 3. New object: ImaginedTrajectory

```python
@dataclass
class ImaginedTrajectory:
    states:         list
    actions:        list
    rewards:        list
    value_estimate: float
    novelty_score:  float
    confidence:     float
    depth:          int
```

---

## 4. New method: generate_structured_imagination

Add to `HippocampalImagineEngine`.

### Signature

```python
def generate_structured_imagination(
    self,
    *,
    start_state:  Mapping[str, Any],
    action_id:    str,
    experiences:  Sequence[Any],
    depth:        int,
    gamma:        float,
    value_layer:  Optional[ValueLayer],
) -> Dict[str, Any]:
```

### Returns

```python
{
    "trajectories":  List[ImaginedTrajectory],
    "values":        List[float],
    "nodes_visited": int,
    "novelty_hits":  int
}
```

---

## 5. Algorithm

### Step 1 — Selection of seed episodes

```python
seed = choose_top_similar(start_state)  # использует _select_candidates
```

### Step 2 — Temporal stitching

Episodes may be joined by the criterion:

```
exp_A.next_state ≈ exp_B.state
similarity >= similarity_threshold
```

### Step 3 — Trajectory construction

```
state₀ → exp₁ → state₁ → exp₂ → state₂ → ...
```

Until `depth` or `max_nodes` is reached.

### Step 4 — Reward accumulation

```
R = Σ γ^t * reward_t
```

Where: `γ_effective = gamma * reward_decay`.

### Step 5 — Novelty

```
novelty_score = count(states not in observed_states) / depth
```

### Step 6 — Confidence

```
confidence = similarity_mean * (confidence_decay ^ depth)
```

### Step 7 — Value estimate

```
value_estimate =
    R
    + goal_bias * V(last_state)
    + novelty_weight * novelty_score
```

Where: `V(last_state) = value_layer.get_value(...)`.

---

## 6. Final trajectory score

```
trajectory_value = value_estimate * confidence
```

---

## 7. Return of values

```python
values.append(trajectory_value)
```

---

## 8. Complexity limits

```
samples   ≤ 8
depth     ≤ 5
branching ≤ 4
nodes     ≤ 96
edges     ≤ 192
```

---

## 9. Integration with Agent

In `_apply_deliberative_planning`, replace `_generate_imagined_rollouts` with `generate_structured_imagination`.

**Computation of `imagined_value`:**

```python
imagined_value = quantile(values, 0.7)
```

**Combination:**

```python
rollout_value = max(memory_rollout_value, imagined_value)
```

---

## 10. Telemetry

Add fields:

- `planning_imagined_trajectory_count`
- `planning_imagined_confidence_mean`
- `planning_imagined_novelty_mean`

---

## 11. Invariants

| #  | Invariant                                        |
|----|--------------------------------------------------|
| I1 | `values_count ≤ imagination_samples`             |
| I2 | `nodes_visited ≤ imagination_max_nodes`          |
| I3 | `depth ≤ imagination_depth`                      |
| I4 | `confidence ∈ [0, 1]`                            |

---

## 12. Test cases

**File:** `tests/test_hie_002.py`

### TEST 1 — Trajectory recombination

**Memory:** `A → B`, `C → D`.  
**Expected:** the agent imagines `A → B → D`.

### TEST 2 — Novelty bonus

A new state must increase `value`.

### TEST 3 — Confidence decay

Long trajectories yield lower `confidence`.

### TEST 4 — Goal bias

If `value_layer(last_state)` is high, the trajectory must win.

### TEST 5 — Complexity guard

**Input:** `samples = 20`, `depth = 10`.  
**Expected:** `samples ≤ 8`, `depth ≤ 5`.

---

## 13. Expected behavior

After HIE-002 the agent begins to:

- predict future states
- join different memories
- search for new states
- evaluate long plans

> This is already very close to a **hippocampal cognitive map + imagination**.

---

## 14. What appears after HIE-002

The agent can build a plan from unrelated memories:

```
memory:
    berry bush
    cave
    wolf

imagination:

    go to bush
        ↓
    cave
        ↓
    safety
```

> Even though no such trajectory was present in experience.
