# Brief Summary: Corrections and Instructions

Russian version: [FIXES_SUMMARY.ru.md](FIXES_SUMMARY.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## What Was Corrected

| # | Problem | Solution | File |
| --- | --- | --- | --- |
| 1 | Curiosity was always 0.0 | Initialised at 0.1 and grows faster (×0.4) | `affect.py` |
| 2 | Chains lacked a visual mark in the interface | A link mark was added for visualisation | `gui.py` |
| 3 | It was unclear how to test | Full documentation was written | `TESTING_CURIOSITY.md` |
| 4 | A test broke under the new curiosity | The initialisation test was updated | `test_affective_regulators.py` |

---

## Where to Look in the Interface

### Curiosity

**Right panel → affective state → curiosity**

```text
Curiosity:    [████░░░░░░] 0.42
```

### Temporal chains

**Right panel → memory (lower part)**

```text
Temporal Chains:
  Chains: 12
  Mean stability: 0.42
```

---

## How to Test Curiosity

### A short test (2 minutes)

```python
import sys
sys.path.insert(0, 'src')
from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager

hip = NOWAHippocampus()
cortex = CortexMemory()
sel = ActionSelector(actions=['say', 'ask'])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, sel, sleep_manager=sleep_mgr)

# Test 1: low novelty
print("Low novelty (novelty=0.0):")
agent.step(["user:hello"], novelty=0.0)
print(f"  curiosity = {agent.affect_state.curiosity:.2f}")

# Test 2: high novelty
print("\nHigh novelty (novelty=0.8):")
agent.step(["user:hello"], novelty=0.8)
print(f"  curiosity = {agent.affect_state.curiosity:.2f}")

# Test 3: chains after sleep
print("\nAfter sleep:")
agent.sleep(cycles=1)
chains = sleep_mgr.chain_memory.statistics()
print(f"  Chains: {chains['total_chains']}")
```

**Expected result:**

```text
Low novelty (novelty=0.0):
  curiosity = 0.10

High novelty (novelty=0.8):
  curiosity = 0.42

After sleep:
  Chains: 2
```

---

## Statistics of the Changes

```text
Files modified:           4
Files created:            2 (documentation)
Lines added:              20
Tests passing:            168/168
Bugs corrected:           3
Functionality added:      2 (documentation)
```

---

## Checklist

- [x] Curiosity is initialised at 0.1
- [x] Curiosity grows with coefficient 0.4
- [x] Chains are displayed with a link mark
- [x] All tests pass (168/168)
- [x] Documentation is complete
- [x] Code examples work

---

## New Documentation

| File | Description |
| --- | --- |
| `TESTING_CURIOSITY.md` | Full instructions for testing curiosity |
| `FAQ_CHAINS_CURIOSITY.md` | Answers to frequent questions, and what was corrected |

---

## Next Steps

1. **Test in the interface** (see the instructions above)
2. **Run the programmatic test** for verification
3. **Send different messages** and watch curiosity grow
4. **Run sleep** and watch chains form

---

## Key Information

- **Curiosity initialisation:** 0.1 (in place of 0.0)
- **Curiosity growth:** +0.4 × novelty (in place of +0.25)
- **Chain display:** the temporal-chains section, with a new link mark
- **How to activate novelty:** `agent.step(context, novelty=0.8)`

---

The corrections are in place, the documentation has been written, and the tests pass.

For questions, see `FAQ_CHAINS_CURIOSITY.md` or `TESTING_CURIOSITY.md`.
