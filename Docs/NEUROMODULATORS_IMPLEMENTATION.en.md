# Neuromodulators — Implementation and Integration

Russian version: [NEUROMODULATORS_IMPLEMENTATION.ru.md](NEUROMODULATORS_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Date of implementation:** February 2026
**Status:** Complete
**Test status:** 172/172 tests pass

---

## Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Integration](#integration)
5. [Usage examples](#usage-examples)
6. [Testing](#testing)

---

## Overview

The neuromodulator system implements **four global regulatory signals** that influence memory consolidation, chain formation, and system behaviour **without subjective experience**.

### Principal principle

> **Neuromodulators are the physics of the system, not its psychology.**

They do not take decisions and they do not store meaning; they only modulate the probabilities, rates, and thresholds of processes.

---

## Architecture

### System level

```
┌─────────────────────────────────────────────────┐
│                  Agent (principal class)        │
├─────────────────────────────────────────────────┤
│  • Hippocampus (episodic memory)               │
│  • Cortex (consolidated patterns)              │
│  • Selector (action selection)                 │
│  • SleepManager (consolidation)                │
│  • NeuromodulatorState (neuromodulators) ← NEW │
│  • AffectiveState (affective state)            │
│  • TemporalLevels (temporal hierarchies)       │
└─────────────────────────────────────────────────┘
         ↓
    agent.step()  ← update of neuromodulators
         ↓
  agent.sleep()   ← application of effects during sleep
```

---

## Components

### 1. NeuromodulatorState (`src/neuromodulators.py`)

A simple container for neuromodulator state:

```python
class NeuromodulatorState:
    dopamine: float          # 0.0–1.0
    norepinephrine: float    # 0.0–1.0
    serotonin: float         # 0.0–1.0
    cortisol: float          # 0.0–1.0
    timestamp: float
```

#### Methods

| Method | Description |
|-------|---------|
| `update_from_signals(reward, novelty, conflict)` | Update from ambient signals |
| `decay_over_time(elapsed)` | Exponential decay toward the baseline |
| `to_dict() / from_dict()` | Serialisation |
| `snapshot()` | Snapshot of the current state |

---

### 2. Four neuromodulators

#### DA (Dopamine) — Reinforcement / Value

**Source:**
- Positive reward (reward > 0)
- Successful stabilisation of patterns
- Strengthening of positive chains

**Influences:**
- Increase of the strength of cortical patterns (during sleep)
- Increase of the probability of action repetition
- Lowering of the consolidation threshold

**Range:** 0.0 – 1.0

---

#### NE (Norepinephrine) — Mobilisation / Novelty

**Source:**
- Novelty (unexpectedness > 0)
- Conflicts (conflict > 0)
- Abrupt changes

**Influences:**
- Increase of exploration
- Acceleration of memory updating
- Formation of additional chains (during sleep)

**Range:** 0.0 – 1.0

---

#### 5-HT (Serotonin) — Stability / Satiety

**Source:**
- Absence of conflicts
- Repeated neutral outcomes
- Stabilised patterns

**Influences:**
- Increase of pattern stability
- Reduction of arousal
- Slowing of aggressive learning

**Range:** 0.0 – 1.0

---

#### CORT (Cortisol) — Stress / Overload

**Source:**
- Negative reward (reward < 0)
- A high threat estimate
- Conflicts without resolution

**Influences:**
- Accelerated forgetting of unstable traces
- Suppression of exploration
- Simplification of strategies

**Range:** 0.0 – 1.0

---

## Integration

### Stage 1: Initialisation in Agent

```python
# src/agent.py
from neuromodulators import NeuromodulatorState

class Agent:
    def __init__(self, ...):
        self.neuromodulators = NeuromodulatorState()  # ← initialisation
        # Attach to sleep_manager so that effects can be applied
        if self.sleep_manager:
            setattr(self.sleep_manager, "neuromodulators", self.neuromodulators)
```

### Stage 2: Update during step()

```python
def step(self, context_events, ..., reward=0.0, novelty=0.0, conflict=0.0):
    # ... principal logic ...
    
    # Update neuromodulators from signals
    self.neuromodulators.update_from_signals(
        reward=reward, 
        novelty=novelty, 
        conflict=conflict
    )
```

### Stage 3: Application during sleep()

```python
# src/sleep.py
class SleepManager:
    def sleep_cycle(self):
        # ... consolidation ...
        
        # Apply neuromodulator effects
        if hasattr(self, 'neuromodulators'):
            self._apply_neuromodulators_during_sleep()
```

### Stage 4: Save and load

```python
# src/storage.py
def save_agent(self, ..., neuromodulators=None):
    if neuromodulators:
        agent_state['neuromodulators'] = neuromodulators.to_dict()

def load_agent(self, ..., neuromodulators_data):
    # Restore neuromodulators
    nm = NeuromodulatorState.from_dict(neuromodulators_data)
```

### Stage 5: Visualisation in the GUI

```python
# src/gui.py
# Diagnostic output in the interface:
# DA: 0.42  (Dopamine)
# NE: 0.31  (Norepinephrine)
# 5-HT: 0.58 (Serotonin)
# CORT: 0.12 (Cortisol)
```

---

## Usage examples

### Example 1: A basic cycle with neuromodulators

```python
from agent import Agent
from neuromodulators import NeuromodulatorState

agent = Agent(hippocampus, cortex, selector, sleep_manager)

# Step 1: A positive experience
action = agent.step(
    context=["user:hello"],
    reward=+1.0,      # Positive reinforcement
    novelty=0.2,      # Slight novelty
    conflict=0.0      # No conflicts
)
# → DA rises, 5-HT rises

# Step 2: An unexpected event
action = agent.step(
    context=["user:something_unusual"],
    reward=0.0,
    novelty=0.8,      # High unexpectedness
    conflict=0.3
)
# → NE jumps, CORT rises slightly

# Step 3: A negative event
action = agent.step(
    context=["user:bad_thing"],
    reward=-0.5,      # Negative reinforcement
    novelty=0.0,
    conflict=0.6      # Conflict
)
# → CORT rises, DA falls

# Consolidation with neuromodulator effects included
stats = agent.sleep(cycles=2)
print(stats)
# During sleep the effects are applied:
# - DA strengthens cortical patterns
# - NE promotes chain formation
# - CORT removes unstable traces
# - 5-HT stabilises existing patterns
```

### Example 2: A test case from the plan

```python
# Case: Repeated success
for i in range(5):
    agent.step(
        context=[f"user:routine{i}"],
        reward=+0.8,  # Constant positive reinforcement
        novelty=0.0,  # No novelty
        conflict=0.0  # No conflicts
    )

# Result:
# ✓ DA rises and stabilises (~0.6-0.7)
# ✓ 5-HT rises (~0.4-0.5)
# ✓ Chains stabilise
# ✓ Exploration falls

agent.sleep(cycles=1)
# During sleep: DA strengthens successful patterns, 5-HT stabilises
```

---

## Testing

### Test file: `tests/test_neuromodulators.py`

Four principal tests cover every case from the plan:

| Test | Description | Status |
|------|---------|--------|
| `test_dopamine_increases_on_reward` | DA rises under positive reward | Pass |
| `test_norepinephrine_increases_on_novelty` | NE rises under unexpectedness | Pass |
| `test_serotonin_stable_neutral` | 5-HT rises under stable conditions | Pass |
| `test_prolonged_negative_increases_cortisol_and_forgetting` | CORT rises and forgetting is activated | Pass |

### Running the tests

```bash
# Run the neuromodulator tests
python -m pytest tests/test_neuromodulators.py -v

# Run all tests
python -m pytest -q
# Result: 172/172 tests pass
```

---

## Effects during sleep

### DopamineEffect (DA > 0.05)

```python
factor = 1.0 + (da * 0.05)
for pattern in cortex.patterns:
    pattern.strength *= factor
```

**Result:** Patterns under high DA are strengthened by 5–7%

### Cortisol Effect (CORT > 0.4)

```python
threshold = forget_stability_threshold + (cortisol * 0.2)
kept = [exp for exp in hippocampus if exp.stability >= threshold ...]
```

**Result:** Under high CORT, forgetting becomes more aggressive

### Norepinephrine Effect (NE > 0.4)

```python
self._form_chains_from_recent(max_len=9)  # Enlarged window
```

**Result:** Longer and more complex chains are formed

### Serotonin Effect (5-HT > 0.1)

```python
for exp in hippocampus.experiences[-50:]:
    exp.stability = min(1.0, exp.stability + serotonin * 0.01)
```

**Result:** Experiences stabilise more slowly, but more reliably

---

## Architectural decisions

### 1. Why are neuromodulators separate from Affect?

| Property | Affect | Neuromodulators |
|---|---|---|
| **Rate of change** | Fast | Slow |
| **Time scale** | The current moment | A long-term trend |
| **Role** | Control of behaviour | Modulation of learning |
| **Visibility** | Yes (in the GUI) | Diagnostics |

### 2. Normalisation to [0, 1]

All neuromodulators are normalised in order to provide:
- Uniform influence
- Comparability with one another
- Extensibility (new ones are easy to add)

### 3. Decay toward the baseline

```python
baseline = 0.1  # Baseline background level
# Exponential decay over ~10 seconds
```

**Purpose:** The system returns to a calm state after stress

---

## Integration with the GUI

### Diagnostic block "Neuromodulators"

Placement: the right side panel, above the statistics

```
Affective state
  Valence: 0.00
  Activation: 0.00
  Threat: 0.00
  Curiosity: 0.00
  
Neuromodulators:        ← NEW
  DA: 0.42
  NE: 0.31
  5-HT: 0.58
  CORT: 0.12
```

**Access:** Visible in real time while the GUI is in use

---

## Files changed

| File | Changes |
|------|-----------|
| `src/neuromodulators.py` | New file — class `NeuromodulatorState` |
| `src/agent.py` | Initialisation and update of neuromodulators added in `step()` |
| `src/sleep.py` | Methods for applying effects added: `_apply_neuromodulators_during_sleep()` |
| `src/storage.py` | Save and load of neuromodulators in `save_agent()` / `load_agent()` |
| `src/gui.py` | Diagnostic output of DA/NE/5-HT/CORT in the side panel |
| `tests/test_neuromodulators.py` | New file — 4 tests verifying functionality |

---

## FAQ

### Q: Why do neuromodulators not influence ActionSelector directly?

**A:** Because that would violate the principle of "physics without psychology". Neuromodulators influence **only consolidation and forgetting**, which indirectly change the patterns and chains that are available. Action selection remains deterministic and is based on active experiences and patterns.

### Q: May the neuromodulator parameters be changed?

**A:** Yes. All parameters reside in the method `update_from_signals()`:
```python
self.dopamine = self.clamp(self.dopamine + 0.2 * reward)  # 0.2 — coefficient
```

### Q: Why is the baseline equal to 0.1?

**A:** This provides:
- A small background tone
- Rapid decay toward the norm
- A difference between low and high states

### Q: How is this related to TemporalChains?

**A:** During sleep, under high NE, chains of greater length are formed, which allows the system to remember longer sequences at uncertain moments.

---

## Further improvements (plan)

- [ ] Dynamic coefficients of influence (dependent on state)
- [ ] Interaction among neuromodulators (synergy / antagonism)
- [ ] Long-term adaptation of the baseline
- [ ] Prediction of neuromodulator state

---

**Document current as of:** February 2026
**Version:** 1.0
**Author:** NOWA Development Team
