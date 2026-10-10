# Specification — External Interaction Layer (implemented)

Russian version: [spec_external_interaction_layer.ru.md](spec_external_interaction_layer.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## 1. Architectural Position

The layer sits between the environment and the agent's cognitive loop:

```
[ Environment ]
       ↑ ↓
[ External Interaction Layer ]
       ↑ ↓
[ Agent / Selector / BG pipeline ]
       ↑ ↓
[ Drives + Internal Simulation ]
```

Key principle:
- `ActionSelector` remains the proposer (it proposes an action),
- `EnvironmentInterface` executes,
- `ExternalInteractionLayer` interprets feedback and applies learning hooks.

---

## 2. Data Models

### 2.1 Observation

```python
@dataclass
class Observation:
    timestamp: float
    source: str
    payload: Dict[str, Any]
    uncertainty: float  # clamp [0, 1]
```

Support for:
- noisy observations;
- history caching (`history_limit`);
- probabilistic interpretation (`confidence = 1 - uncertainty`).

### 2.2 ExternalAction

```python
@dataclass
class ExternalAction:
    action_type: str
    parameters: Dict[str, Any]
    expected_outcome: Optional[Hypothesis]
```

### 2.3 Feedback

```python
@dataclass
class Feedback:
    reward: float               # clamp [-1, 1]
    signal: Dict[str, Any]
    success_probability: float  # clamp [0, 1]
    latency: float              # >= 0
```

### 2.4 Hypothesis

```python
@dataclass
class Hypothesis:
    name: str
    prior: float
    likelihood: float
    likelihood_not_h: float
    posterior: float
    metadata: Dict[str, Any]
```

---

## 3. Learning Hooks (current implementation)

### 3.1 Drive update: decay + saturation + competition

The update is performed in `ExternalInteractionLayer.apply_learning_hooks(...)`.

Step 1: a base update from reward, with decay:

```
decayed = (1 - drive_decay) * current
edge_distance = |2*current - 1|
saturation_gate = max(0.05, 1 - drive_saturation * edge_distance)
delta = alpha * reward_signal * saturation_gate
raw = clamp(decayed + delta, 0, 1)
```

Step 2: competition among drives:

```
distribution = softmax(raw_drive_updates)
competitive = (1 - drive_competition) * raw
            + drive_competition * distribution * total_energy
```

Effect:
- there is no unbounded linear runaway;
- the risk of a sticky regime at the boundaries is reduced;
- several drives compete for a limited "energy".

### 3.2 Strategy update: logits + weight decay + softmax

Logit space and normalization are used:

```
td_residual = reward_signal - predicted_reward
drive_term = drive_policy_gain * strategy_drive_signal
new_logit = (1 - strategy_weight_decay) * current_logit
          + learning_rate * (td_residual + drive_term)
strategy_weights = softmax(strategy_logits, temperature)
```

Support for:
- `strategy_temperature` (control of policy sharpness),
- `strategy_weight_decay`,
- stable normalization (`sum(weights)=1`).

### 3.3 Coupling of drives to policy (the missing link is closed)

`strategy_drive_signal` is computed as a weighted projection of drive levels:

```
signal_s = clamp( Σ_d w(s,d) * (2*level_d - 1) / Σ_d |w(s,d)| , -1, 1 )
```

Sources of coupling:
1. An explicit `strategy_drive_coupling` (passed from Agent).
2. If it is not passed, a fallback heuristic is built.

Integration into Agent:
- coupling is taken from `selector.action_metadata[action]["predicted_effect"]["drives"]`,
- the sign is inverted by `-delta`, so that an expected decrease of a drive strengthens the strategy.

### 3.4 Hypothesis update: extended Bayesian form

An explicit `P(E|¬H)` and an optional `P(E)` are supported:

```
P(H|E) = P(E|H) * P(H) / P(E)
```

If `P(E|¬H)` is not given:
- the value from the hypothesis metadata or state is used,
- or it is derived through the base rate if `P(E)` is passed.

---

## 4. Asynchronous Layer

`AsyncInteractionScheduler` implements:
- `poll_observation_non_blocking()` — a non-blocking poll of the environment;
- `schedule_parallel_simulations(...)` — parallel internal simulation requests;
- `queue_feedback(...)` / `resolve_feedback(...)` — delayed feedback.

Guarantee:
- delayed signals are applied only when `due_step <= current_step`.

---

## 5. Integration into Agent

Public methods added:
- `observe_external_input(...)`
- `get_external_observation_history(...)`
- `create_external_action(...)`
- `poll_external_observation_non_blocking()`
- `poll_external_observation_once()`
- `execute_external_action(...)`
- `resolve_external_feedback(...)`
- `get_external_interaction_state()`
- `run_parallel_internal_simulations(...)`

Internal learning bridge:
- `Agent._apply_external_feedback_learning(...)` passes drives, strategies, and coupling into `apply_learning_hooks(...)`;
- after the update, the new `strategy_weights` are written into `selector.action_metadata[*]["strategy_weight"]`.

---

## 6. Integration into Selector Policy

Policy modulation was added in `ActionSelector.compute_pressures(...)`:
- `strategy_weight` is taken from `action_metadata`,
- it is centred relative to a uniform baseline,
- it is added to the pressure vector.

Result:
- learning in ExternalInteractionLayer affects the actual choice of action,
- the chain is closed: `feedback -> drives/strategies -> selector pressure -> action`.

---

## 7. GUI (interactive control)

A block for the external interaction layer was added in `src/gui.py`. The interface labels, given here in English, are:

- observation fields:
  - source
  - uncertainty
  - JSON data
- buttons:
  - Add observation
  - Poll the environment
- action fields:
  - action
  - prior
  - delay
  - forecast
  - JSON parameters
- buttons:
  - Execute action
  - Process deferred items
  - Refresh status
- status lines:
  - observations | pending | step | strategies
  - the last feedback.

---

## 8. Test Coverage

Coverage is in `tests/test_external_interaction_layer.py` and includes:
- the delayed feedback pipeline;
- strategy normalization (softmax);
- the explicit `P(E|¬H)` path for a hypothesis;
- drive-to-strategy coupling under a neutral reward;
- the effect of `strategy_weight` on selector pressures;
- agent-level integration (external action execution, delayed resolution, polling, parallel simulation).

Command:

```bash
python -m pytest -q tests/test_external_interaction_layer.py
```

---

## 9. Implementation Invariants

1. `reward` is clamped to `[-1, 1]`; probabilities are clamped to `[0, 1]`.
2. Drive intensities are bounded to `[0, 1]`.
3. Strategy weights are always normalized (softmax).
4. Delayed feedback is not applied before it is due.
5. Coupling of drives to strategies does not bypass the selector/BG pipeline; it modulates policy through pressures.
