# HIE-003 Specification

Russian version: [spec_hie_003.ru.md](spec_hie_003.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Multi-Action Hippocampal Imagination Tree

### Objective

Extend `HippocampalImagineEngine` so that the system can generate trajectories with **sequences of actions**, and not only evaluate a fixed initial action.

This brings the system closer to:

- hippocampal forward sweep
- vicarious trial-and-error (VTE)

and forms a primitive world model.

---

## 1. New functionality

**Previously:**

```
start_state → actionX → trajectory
```

**Now:**

```
start_state
   ↓
action1
   ↓
state1
   ↓
action2
   ↓
state2
   ↓
action3
```

---

## 2. New agent parameters

Add to `Agent.__init__`:

```python
# HIE-003: multi-action imagination tree
self.imagination_enable_action_sequences: bool  = True
self.imagination_action_branching: int           = 3
self.imagination_max_tree_nodes: int             = 128
self.imagination_action_temperature: float       = 0.7
self.imagination_value_backup: float             = 0.8
```

| Parameter                              | Meaning                                      |
|----------------------------------------|----------------------------------------------|
| `imagination_enable_action_sequences`  | enables the new mode                         |
| `imagination_action_branching`         | how many actions to try from a state         |
| `imagination_max_tree_nodes`           | tree limit                                   |
| `imagination_action_temperature`       | stochasticity of action choice               |
| `imagination_value_backup`             | how far value propagates upward              |

---

## 3. Extension of ImaginedTrajectory

Add fields:

```python
root_action:            str
terminal_state_value:   float
cumulative_reward:      float
```

**Resulting structure:**

```python
ImaginedTrajectory:
    states
    actions
    rewards
    root_action
    cumulative_reward
    terminal_state_value
    value_estimate
    novelty_score
    confidence
    depth
```

---

## 4. New engine method

Add to `HippocampalImagineEngine`:

```python
def generate_action_tree_imagination(
    *,
    start_state:        Mapping[str, Any],
    candidate_actions:  Sequence[str],
    experiences:        Sequence[Any],
    depth:              int,
    gamma:              float,
    value_layer:        Optional[ValueLayer],
) -> Dict[str, Any]:
```

---

## 5. Tree generation algorithm

### Step 1 — Selection of initial actions

```python
root_actions = top_k_actions(candidate_actions, imagination_action_branching)

for root_action in root_actions:
    expand_action(root_action)
```

### Step 2 — Construction of the tree

**Tree node:**

```python
TreeNode:
    state
    action
    reward
    parent
    children
    depth
```

**Algorithm:**

```python
queue = [root_nodes]

while queue and nodes < max_tree_nodes:

    node = pop(queue)

    if node.depth >= depth_limit:
        continue

    candidate_experiences = select_similar_experiences(node.state)

    for exp in top_k(candidate_experiences):

        next_state = exp.next_state
        action     = exp.action
        reward     = exp.reward

        child = create_node()

        add_edge(node, child)
        queue.push(child)
```

---

## 6. Generation of trajectories

After the tree has been built:

```python
leaf_nodes = nodes with no children

for leaf in leaf_nodes:
    trajectory = trace_path_to_root(leaf)
```

---

## 7. Value estimate of a trajectory

```
reward_total     = Σ (gamma^t * reward_t)

terminal_value   = value_layer.get_value(terminal_state)

novelty          = novelty_weight * novelty_score

value_estimate   =
    reward_total
  + goal_bias * terminal_value
  + novelty
```

Then:

```
trajectory_value = value_estimate * confidence
```

---

## 8. Backup of value to the root action

Aggregation of value by `root_action`:

```
action_values[root_action] =
    quantile(values_of_trajectories_for_action, 0.7)
```

---

## 9. Returned structure

```python
{
    "trajectories":  List[ImaginedTrajectory],
    "values":        List[float],
    "action_values": Dict[action_id, float],
    "nodes_visited": int,
    "edges_visited": int,
    "novelty_hits":  int
}
```

---

## 10. Change to Agent planning

In `_apply_deliberative_planning`:

```python
if imagination_enable_action_sequences:

    imagination_result =
        imagination_engine.generate_action_tree_imagination(...)

    imagined_value =
        imagination_result["action_values"].get(action_id, 0.0)

else:
    # fallback to HIE-002
```

---

## 11. Value blending (correction of HIE-002)

**Previously:**

```python
rollout_value = max(memory_rollout_value, imagined_value)
```

**Becomes:**

```python
blend = self.imagination_value_blend

rollout_value =
    (1 - blend) * memory_rollout_value +
    blend * imagined_value
```

---

## 12. New telemetry

Add fields:

- `planning_imagination_tree_nodes`
- `planning_imagination_tree_edges`
- `planning_imagination_action_count`
- `planning_imagination_branching`

---

## 13. Complexity constraint

Hard limits (otherwise planning becomes exponential):

```
max_tree_nodes ≤ 128
branching      ≤ 4
depth          ≤ 5
```

---

## 14. Expected result

After HIE-003 the system will be able to imagine counterfactual sequences:

```
action1 → action2 → action3
action1 → action4 → action2
action2 → action3 → action1
```

> This is already **model-based planning**.

---

## 15. Architecture after HIE-003

```
episodic memory
        ↓
hippocampal imagination tree
        ↓
trajectory evaluation
        ↓
action value aggregation
        ↓
basal ganglia selection
```

---

## 16. What this gives the system

After HIE-003 the agent will be able to:

- plan multi-step actions
- avoid delayed punishment
- discover long reward chains
- simulate strategies

> That is: a **primitive world model**.
