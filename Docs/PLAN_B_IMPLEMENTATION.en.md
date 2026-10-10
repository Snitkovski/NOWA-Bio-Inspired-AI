# Plan B Implementation: Temporal Chains, Proto-Strategy, and Credit Assignment

Russian version: [PLAN_B_IMPLEMENTATION.ru.md](PLAN_B_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Overview

**Plan B** has been successfully integrated into the NOWA-Cognitive project. This document describes the implementation, architecture, and how to use the new Temporal Chains system.

---

## What is Plan B?

Plan B introduces **Temporal Chains** — lightweight memory structures that capture behavioral sequences and apply retrospective credit assignment without requiring gradients or explicit planning. This creates a **proto-strategy**: behavior that emerges as patterns of chained actions, with each chain biased by its retrospective (net) outcome.

**Key Properties:**
- No learning during waking behavior
- Chains are formed **only during sleep consolidation**
- Chains are purely advisory — they bias but do not dictate action selection
- No gradients, goals, or self-narrative
- Credit is assigned retrospectively through net affect, not by backpropagation

---

## Architecture

### 1. TemporalChain (temporal_chains.py)

```python
class TemporalChain:
    signature: Tuple[str, ...]      # Event sequence (e.g., ("user:hello", "action:say_hello"))
    net_affect: float               # Retrospective aggregate outcome (-1 to +1)
    stability: float                # Consolidation strength (0 to 1)
    usage_count: int                # How many times this chain has been seen
    created_at: float               # Timestamp
    last_updated: float             # Last update time
```

**Methods:**
- `update(net_affect)` — Incrementally update chain's net_affect and stability
- `matches_suffix(event_sequence)` — Check if chain matches tail of recent events

### 2. ChainMemory (temporal_chains.py)

Manager for storing and querying TemporalChains:

```python
class ChainMemory:
    chains: Dict[Tuple, TemporalChain]  # Signature -> TemporalChain
```

**Methods:**
- `add_or_update(signature, net_affect)` — Create or update chain
- `match_bias(recent_sequence)` — Return dict of action -> bias for matching chains
- `statistics()` — Return summary stats (total_chains, avg_stability, avg_net_affect)

### 3. Integration into SleepManager (sleep.py)

During sleep consolidation, a new step forms chains from recent experiences:

```python
def sleep_cycle(self) -> dict:
    # ... existing consolidation logic ...
    
    # 4.5 Form temporal chains from recent experiences (Plan B)
    formed = self._form_chains_from_recent()
    stats["chains_formed"] = formed
    
    return stats
```

**Chain Formation Algorithm:**
1. Extract all event names from recent hippocampal experiences
2. Build all possible sub-sequences of length 2–7 (tunable)
3. For each subsequence, compute retrospective net_affect:
   - If consequence event exists, extract numeric value
   - Otherwise, use mean intensity of contributing experiences
4. Call `chain_memory.add_or_update(signature, net_affect)`

### 4. Integration into ActionSelector (selector.py)

The selector now accepts an optional `temporal_chains_bias` parameter:

```python
action = selector.choose(
    hippocampal_exps,
    cortical_patterns,
    intent_pressure=intent_pressure,
    affect_modifier=affect_modifier,
    temporal_chains_bias=chain_bias    # NEW: optional chain biasing
)
```

**Bias Application Logic:**
1. If no other pressures exist (base_total_pressure == 0) and chains have bias:
   - Directly select action with highest chain bias → **proto-strategy choice**
2. If chains are present and contribute to top action:
   - Return top action deterministically → **proto-strategy enforcement**
3. Otherwise, apply normal confidence-based selection

### 5. Integration into Agent (agent.py)

Before action selection, the agent computes chain bias from recent history:

```python
try:
    if hasattr(self.sleep_manager, 'chain_memory'):
        recent = self.hippocampus.experiences[-50:]
        flat = []
        for exp in recent:
            flat.extend(list(exp.path.signature()))
        chain_bias = self.sleep_manager.chain_memory.match_bias(flat)
except Exception:
    chain_bias = None

action = self.selector.choose(
    hip_exps, ctx_patterns,
    intent_pressure=intent_pressure,
    affect_modifier=affect_modifier,
    temporal_chains_bias=chain_bias
)
```

---

## Key Behaviors

### Delayed Valuation

**Test:** `test_chain_formation_and_bias`
- Create sequence A → B → good_outcome
- Create sequence A → C → bad_outcome
- After sleep, agent slightly prefers B after A (no planning, just statistical preference)

### Contextual Strategy

Chains distinguish between:
- Same action in different contexts
- Different action sequences leading to the same outcome

### No Learning Without Sleep

- Waking steps store experiences but never form chains
- Chains only appear after `agent.sleep(cycles=3)` is called
- This mirrors biological memory consolidation

---

## GUI Updates

The GUI now displays Temporal Chains statistics in:

1. **Memory Display Panel** (right panel, lower):
   - Shows the number of chains and their mean stability

2. **Inspector, Sleep Tab**:
   - New section showing total chains and average stability

3. **Feedback Integration**:
   - User ratings set the consequence net_affect used in chain formation

---

## Usage Example

```python
from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from experience import Event, EventType

# Setup
hip = NOWAHippocampus()
cortex = CortexMemory()
sel = ActionSelector(actions=["action_a", "action_b", "action_c"])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, sel, sleep_manager=sleep_mgr)

# Waking behavior (no chain formation)
for i in range(10):
    context = ["context:test"] if i % 2 == 0 else ["context:other"]
    reward = 1.0 if i < 5 else -1.0
    action = agent.step(context, reward=reward, intensity=1.0)
    print(f"Step {i}: Action={action}, Reward={reward}")

# Sleep consolidation (chains formed here)
sleep_stats = agent.sleep(cycles=3)
print(f"Chain formation: {sleep_stats}")

# Check chains
chains_stats = sleep_mgr.chain_memory.statistics()
print(f"Total chains: {chains_stats['total_chains']}")
```

---

## Testing

All Plan B functionality is covered by unit tests in `tests/test_temporal_chains.py`:

- `test_chain_formation_and_bias`: Verify chains form during sleep and provide bias
- Integration tests confirm chains work alongside hippocampus, cortex, and selector

Run tests:
```bash
pytest tests/test_temporal_chains.py -q
```

---

## Design Constraints (Per Specification)

- **No gradients:** Chains use only simple running averages
- **No planning:** Chains look backward only (retrospective)
- **No goals:** Chains are outcome-neutral, purely statistical
- **No self-narrative:** Chains exist but agent doesn't describe them
- **Chains only in sleep:** Formation happens exclusively during consolidation
- **Short fixed-length:** Max 7 steps per chain
- **Credit assignment without backprop:** Retrospective net_affect distribution

---

## Future Enhancements

- **Plan C (Value Landscapes):** Long-horizon drift and attractor dynamics
- **Temporal decay:** Chains lose stability over time if unused
- **Chain clustering:** Group similar chains to reduce memory
- **Hierarchical chains:** Support multi-level temporal abstraction

---

## Files Modified

- `src/temporal_chains.py` — NEW: TemporalChain and ChainMemory classes
- `src/sleep.py` — Added `_form_chains_from_recent()` method
- `src/selector.py` — Extended `choose()` to accept and use temporal_chains_bias
- `src/agent.py` — Compute chain_bias before action selection
- `src/gui.py` — Display chain statistics in memory panel and inspector
- `tests/test_temporal_chains.py` — NEW: Comprehensive Plan B tests

---

**Completion Date:** February 4, 2026  
**Status:** Complete and tested (168 tests passing)
