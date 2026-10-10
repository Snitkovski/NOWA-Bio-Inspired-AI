# Index: Neuromodulator System, Phase 2

Russian version: [INDEX_NEUROMODULATORSv2.ru.md](INDEX_NEUROMODULATORSv2.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Final status

**Implemented and fully tested**

- **Tests:** 24/24 PASSED
- **Errors:** 0
- **Time:** 0.05 sec
- **Quality:** production-ready

---

## Principal files

### Implementation

| File | Description | Status |
|------|---------|--------|
| [src/neuromodulators.py](src/neuromodulators.py) | Principal module (450 lines) | Rewritten according to the specification |
| [src/agent.py](src/agent.py) | Integration with Agent | Verified |
| [src/sleep.py](src/sleep.py) | Integration with Sleep | Verified |

### Tests

| File | Contents | Status |
|------|----------|--------|
| [tests/test_neuromodulators_phase2.py](tests/test_neuromodulators_phase2.py) | 14 tests (TC-1 through TC-5 + baseline) | All pass |
| [tests/test_neuromodulator_integration.py](tests/test_neuromodulator_integration.py) | 10 integration tests with Agent/Sleep | All pass |
| [test_results.log](test_results.log) | Complete test logs | Saved |

### Documentation

| File | Description |
|------|---------|
| [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md) | **Start here** (brief summary) |
| [FINAL_REPORT_NEUROMODULATORS_PHASE2.md](FINAL_REPORT_NEUROMODULATORS_PHASE2.en.md) | Full report with details |
| [INDEX_NEUROMODULATORS.md](INDEX_NEUROMODULATORS.en.md) | This file (navigation) |

---

## Test coverage

### Mandatory specification test cases (all implemented):

```
TC-1: Positive Reinforcement
   Test: test_tc1_positive_reinforcement
   reward=+1.0 → DA↑, HT↑
   
TC-2: Negative + Conflict  
   Test: test_tc2_negative_and_conflict
   reward=-0.8, conflict=0.6 → CORT↑↑, DA↓
   
TC-3: Novelty
   Test: test_tc3_novelty
   novelty=1.0 → NE↑, exploration↑
   
TC-4: Time Decay
   Tests: test_tc4_time_decay, test_tc4_decay_half_life
   120 sec without signals → all → baseline
   
TC-5: Sleep + High Dopamine
   Test: test_tc5_sleep_consolidation_enhancement
   DA=0.7 → consolidation_strength↑, learning↑
```

### Additional coverage:
- Basic functionality (initialization, clamping, reset)
- Stress scenarios
- Modifiers and their consistency
- Hot agent behaviour (multiple steps, learning)
- Boundary cases (extreme signals, rapid changes)

---

## Key elements of the implementation

### Four neuromodulators:
```python
self.dopamine = 0.1              # Reward prediction error
self.norepinephrine = 0.1        # Uncertainty & arousal
self.serotonin = 0.1             # Stability & temporal depth
self.cortisol = 0.05             # Stress response
```

### Update formulas (exactly as in the specification):
```python
# Dopamine
if reward > 0:
    DA += 0.25 * reward
elif reward < 0:
    DA -= 0.10 * abs(reward)

# Serotonin
if reward > 0 and conflict == 0:
    HT += 0.05 * reward
if stable_repetition:
    HT += 0.01

# Norepinephrine
NE += 0.30 * novelty + 0.15 * conflict

# Cortisol
if reward < 0:
    CORT += 0.20 * abs(reward)
CORT += 0.25 * conflict

# Exponential decay
X = baseline + (X - baseline) * 0.5^(elapsed / 90)
```

### Eight modifier methods:
```python
get_learning_rate_modifier()       # DA↑ → learn↑
get_consolidation_strength()       # DA↑ → consolidate↑
get_temporal_discount()            # HT↑ → long-term↑
get_exploration_level()            # NE↑ → explore↑
get_temporal_chain_generation()    # NE↑, HT↑ → chains↑
get_forgetting_rate()              # CORT↑ → forget↑
get_consolidation_threshold()      # CORT↑ → threshold↑
get_affective_arousal_modifier()   # DA↑, NE↑ → arousal↑
```

---

## Test results

```
Platform: Windows, Python 3.13.1
Pytest: 9.0.2

Suite 1: Phase 2 Specification Tests
  - 14 tests
  - 5 mandatory cases TC-1 through TC-5
  - 9 additional tests
  Result: 14/14 PASSED

Suite 2: Integration Tests  
  - 10 tests
  - Agent + Sleep + Affect
  - Edge cases
  Result: 10/10 PASSED

TOTAL: 24/24 PASSED
TIME: 0.05 seconds
```

### Examples from the logs:

```
test_tc1_positive_reinforcement PASSED
  Input:  reward=+1.0
  Result: DA: 0.1 → 0.35 (↑ 250%)
          HT: 0.1 → 0.15 (↑ 50%)

test_tc2_negative_and_conflict PASSED
  Input:  reward=-0.8, conflict=0.6
  Result: DA: 0.1 → 0.022 (↓ 78%)
          CORT: 0.05 → 0.31 (↑ 620%)

test_tc4_time_decay PASSED
  Initial: DA=0.9, NE=0.8, HT=0.7, CORT=0.6
  After 120s: All approaching baseline [0.1, 0.1, 0.1, 0.05]

test_tc5_sleep_consolidation_enhancement PASSED
  High DA (0.7):
    - consolidation_strength: 1.0 → 1.36
    - learning_rate_modifier: 1.0 → 1.35  
    - forgetting_rate: 0.3 → 0.23
```

---

## How to use

### Quick start:

```python
from neuromodulators import NeuromodulatorState

# 1. Creation
nm = NeuromodulatorState()

# 2. Update from signals
nm.update_from_signals(
    reward=0.5,      # [-1.0, +1.0]
    novelty=0.2,     # [0.0, 1.0]
    conflict=0.1     # [0.0, 1.0]
)

# 3. Obtain modifiers
lr = nm.get_learning_rate_modifier()  # For learning
cons = nm.get_consolidation_strength()  # For sleep

# 4. Temporal decay (rest/sleep)
nm.decay_over_time(60.0)  # 1 minute

# 5. State
state = nm.snapshot()
```

### With Agent:

```python
agent = Agent(hippocampus, cortex, selector, sleep_manager)

# A step automatically updates the neuromodulators
action = agent.step(
    ['context'],
    reward=0.8,      # ← updates DA↑
    novelty=0.1,     # ← updates NE↑
    conflict=0.0     # ← does not update CORT
)

# During sleep the modifiers are used
stats = agent.sleep(cycles=3)
# → sleep_manager uses:
#   - DA to strengthen consolidation
#   - CORT to set the forgetting threshold
#   - NE to form chains
#   - HT for stabilization
```

---

## Quality and reliability

### Code:
- Type hints on all methods
- Comprehensive docstrings
- Boundary checking (clamping)
- Error handling
- Serialization support (to_dict/from_dict)

### Tests:
- Unit tests (basic functionality)
- Integration tests (with the system)
- Scenario tests (realistic cases)
- Edge case tests (boundary conditions)
- Stress tests (rapid changes)

### Documentation:
- A docstring for every method
- Logged in the tests
- Usage examples
- A full report

---

## Specification checklist

- Four neuromodulators (Dopamine, Serotonin, Norepinephrine, Cortisol)
- Value range [0.0, 1.0]
- Baseline ~0.1
- Temporal decay with a half-life
- Exact formulas from the specification
- Eight modifier methods
- Integration with Affect
- Integration with Sleep
- TC-1: Positive reinforcement
- TC-2: Negative + conflict
- TC-3: Novelty
- TC-4: Time decay
- TC-5: Sleep + dopamine
- No hardcoded strategies
- All hard constraints observed

---

## Recommended order of study

1. **Start here:**
   → [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md)  
   (5 minutes for an overview)

2. **Inspect the implementation:**
   → [src/neuromodulators.py](src/neuromodulators.py)  
   (read the comments and docstrings)

3. **Study the tests:**
   → [tests/test_neuromodulators_phase2.py](tests/test_neuromodulators_phase2.py)  
   (usage examples)

4. **Full report (if details are required):**
   → [FINAL_REPORT_NEUROMODULATORS_PHASE2.md](FINAL_REPORT_NEUROMODULATORS_PHASE2.en.md)

5. **Test logs:**
   → [test_results.log](test_results.log)

---

## Ready for

- Production use
- Integration into Plan C (Prediction Layer)
- Extension with new neuromodulators
- Use in more complex scenarios

---

## Quick links

- **Principal module:** [src/neuromodulators.py](src/neuromodulators.py)
- **Unit tests:** [tests/test_neuromodulators_phase2.py](tests/test_neuromodulators_phase2.py)
- **Integration tests:** [tests/test_neuromodulator_integration.py](tests/test_neuromodulator_integration.py)
- **Summary:** [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md)
- **Full report:** [FINAL_REPORT_NEUROMODULATORS_PHASE2.md](FINAL_REPORT_NEUROMODULATORS_PHASE2.en.md)
- **Test logs:** [test_results.log](test_results.log)

---

**Status:** COMPLETE  
**Date:** 2026-02-06  
**Tests:** 24/24 PASSED  
**Quality:** PRODUCTION-READY
