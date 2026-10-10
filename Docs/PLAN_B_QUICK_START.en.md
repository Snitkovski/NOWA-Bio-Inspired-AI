# Plan B: Temporal Chains Implementation — Quick Start

Russian version: [PLAN_B_QUICK_START.ru.md](PLAN_B_QUICK_START.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## What Is New

**Temporal chains** enable the NOWA agent to exhibit proto-strategic behaviour through retrospective credit assignment. There is no learning, no gradients, and no planning — only lightweight sequence memory and outcome biasing.

## Quick Start

### 1. Enable Chains (Automatic)

Chains are formed automatically during sleep if a `SleepManager` with `ChainMemory` is initialised:

```python
from sleep import SleepManager

sleep_mgr = SleepManager(hip, cortex, intent_memory)
# chain_memory is created automatically
```

### 2. Train the Agent in the Ordinary Way

```python
agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

# Waking behavior (no chains yet)
for i in range(50):
    context = ["user:question"]
    reward = 1.0 if i < 25 else -1.0
    action = agent.step(context, reward=reward)
    response = agent.realize_action(action)  # or similar
    
    print(f"Action: {action}, Reward: {reward}")
```

### 3. Sleep in Order to Consolidate (Forms Chains)

```python
# Chain formation happens here!
stats = agent.sleep(cycles=3)

print(f"Chains formed: {stats.get('chains_formed', 0)}")
print(f"Patterns consolidated: {stats['patterns_consolidated']}")
```

### 4. Observe Proto-Strategy

After sleep, the agent exhibits proto-strategic preferences without explicit planning:

```python
# Agent now slightly prefers action sequences that led to reward
action = agent.step(["user:question"])  # May differ from pure random
```

## Interface Display

### Memory Panel (Right Side)

An added section:

```text
Temporal Chains:
  Chains: 8
  Mean stability: 0.38
```

The interface labels the counts in the language of the panel.

### Inspector Window

A new area under the sleep tab:
- shows the total number of chains and the stability metrics
- displays the details of the formation process

## How Chains Work

### Formation (During Sleep)

1. Extract all event names from recent experiences
2. Build all subsequences (2–7 events long)
3. Compute retrospective **net_affect**:
   - from the consequence, if it is available
   - otherwise from the experience intensity
4. Store or update the chain with net_affect

### Bias (During Action Selection)

1. Check the recent event history against all chains
2. For matching chains: `bias[action] += net_affect × (0.5 + 0.5×stability)`
3. If no other pressures exist, select the action with the highest bias
4. Otherwise integrate the bias into the ordinary pressure calculation

## Example: Delayed Valuation

```python
# Scenario A: Positive reward path
agent.step(["user:greeting"], reward=+1.0)  # Context
agent.step(["user:greeting"], reward=+1.0)  # Action A
agent.sleep(cycles=3)  # Forms chain: ("user:greeting", "action:A") → net_affect +1.0

# Scenario B: Same context, different action
agent.step(["user:greeting"], reward=-1.0)  # Action B
agent.sleep(cycles=3)  # Forms chain: ("user:greeting", "action:B") → net_affect -1.0

# Result: Agent now slightly prefers A over B in greeting context
# WITHOUT being told about the connection or learning weights
```

## Key Characteristics

| Feature | Value |
| --- | --- |
| **Chain length** | 2–7 events (configurable) |
| **Formation trigger** | Sleep only |
| **Net affect source** | Consequence or experience intensity |
| **Bias strength** | Moderate (0.5 base + 0.5×stability) |
| **Decision type** | Proto-strategic (biased, not deterministic) |
| **Gradient requirement** | None |
| **Planning required** | No |
| **Self-description** | No narrative |

## Testing

Comprehensive tests are in `tests/test_temporal_chains.py`:

```bash
pytest tests/test_temporal_chains.py -q
```

All tests pass:
- chain formation during sleep
- computation and application of bias
- the selector uses chain bias correctly
- integration with the other modules

## Files Modified

- **New:** `src/temporal_chains.py` — classes `TemporalChain` and `ChainMemory`
- **New:** `tests/test_temporal_chains.py` — unit tests of Plan B
- **New:** `Docs/PLAN_B_IMPLEMENTATION.md` — full technical documentation
- **Modified:** `src/sleep.py` — chain formation step
- **Modified:** `src/selector.py` — chain bias logic
- **Modified:** `src/agent.py` — chain bias computation
- **Modified:** `src/gui.py` — display of chain statistics

## Status

Complete and tested:
- 168/168 tests passing
- full backward compatibility
- all specification requirements met
- documentation complete

## Next: Plan C

Value landscapes, long-horizon drift, and T3 attractor dynamics

---

For the detailed technical documentation, see [PLAN_B_IMPLEMENTATION.md](PLAN_B_IMPLEMENTATION.en.md)
