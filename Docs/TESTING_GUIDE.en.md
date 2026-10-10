# Testing Guide

Russian version: [TESTING_GUIDE.ru.md](TESTING_GUIDE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**For**: QA engineers, developers writing tests, architects validating systems  
**Time**: 1-2 hours to fully understand  
**Version**: 2.0

---

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Phase 3 Tests](#phase-3-tests)
4. [Writing Tests](#writing-tests)
5. [Test Patterns](#test-patterns)
6. [Running Tests](#running-tests)
7. [Best Practices](#best-practices)

---

## Overview

### Test Strategy

The project uses **comprehensive pytest-based testing** covering:

- **Unit Tests**: Individual component behavior
- **Integration Tests**: Component interactions
- **System Tests**: End-to-end agent behavior
- **Specification Tests**: Validation against requirements

### Test Coverage

```
Total Tests: 297
├── Phase 3 Basal Ganglia: 29 tests 
├── Phase 4 (pre) Affective Space: 8 tests 
├── Neuromodulators: 20+ tests 
├── Affective System: 30+ tests 
├── Agent: 50+ tests 
├── Sleep/Learning: 20+ tests 
└── Legacy/Integration: 150+ tests 

Success Rate: 100% (297/297 PASSING)
Execution Time: ~1.5 seconds
```

---

## Test Structure

### Directory Organization

```
tests/
├── test_basal_ganglia.py         # 29 Phase 3 tests
├── test_basal_ganglia_advanced.py # Advanced BG tests
├── test_agent.py                  # Agent integration (50+ tests)
├── test_affective_regulators.py   # Affective system
├── test_neuromodulators.py        # Neuromodulator effects
├── test_sleep.py                  # Sleep learning
├── test_integration.py            # Full system tests
└── ... (20+ other test files)
```

### Test Naming Convention

```python
# Good
def test_basal_ganglia_chooses_higher_net_pressure():
    """BG selects action with highest net pressure."""
    
def test_dopamine_increases_go_signal():
    """High dopamine multiplies Go signals."""

def test_cortisol_increases_nogo_signal():
    """High cortisol multiplies NoGo signals."""

# Avoid
def test_1():
    pass
    
def test_bg():
    pass
```

---

## Phase 3 Tests

### Test Categories (29 total)

#### 1. ActionChannel Tests (8 tests)

Test individual action channel behavior:

```python
# test_basal_ganglia.py::TestActionChannel

def test_action_channel_creation():
    """ActionChannel stores weights correctly."""
    
def test_action_channel_get_go_signal():
    """Go signal computed correctly."""
    
def test_action_channel_get_nogo_signal():
    """NoGo signal computed correctly."""
    
def test_action_channel_habit_learning():
    """Habit strength increases with reinforcement."""
    
# ... 4 more tests for edge cases
```

#### 2. BasalGangliaGate Tests (12 tests)

Test action selection mechanism:

```python
# test_basal_ganglia.py::TestBasalGangliaGate

def test_basic_action_selection():
    """BG selects the action with highest net pressure."""
    
def test_go_nogo_competition():
    """Strong Go bias action is preferred."""
    
def test_dopamine_effect():
    """High dopamine makes all actions more likely."""
    
def test_cortisol_effect():
    """High cortisol inhibits NoGo-based actions."""
    
def test_pfc_pressure_effect():
    """PFC pressure modifies selection."""
    
def test_habit_strength_effect():
    """Higher habit strength increases selection probability."""
    
# ... 6 more tests including specification tests TC1-TC6
```

#### 3. BasalGangliaLearning Tests (4 tests)

Test habit formation during sleep:

```python
# test_basal_ganglia.py::TestBasalGangliaLearning

def test_habit_consolidation_during_sleep():
    """Habit strengthened after successful action."""
    
def test_habit_differential_learning():
    """Successful actions get stronger habits."""
    
def test_habitmax_cap():
    """Habit strength capped at maximum."""
    
def test_habit_unused_decay():
    """Unused actions decay slowly."""
```

#### 4. Integration Tests (2 tests)

Test Phase 3 with full agent:

```python
def test_agent_basal_ganglia_integration():
    """Agent uses BG correctly for action selection."""
    
def test_agent_learning_from_outcomes():
    """Agent updates habit strength from outcomes."""
```

#### 5. Edge Case Tests (3 tests)

Test boundary conditions:

```python
def test_empty_channels_raises():
    """Choosing from empty channels raises error."""
    
def test_extreme_neuromodulators():
    """Very high/low neuromodulators handled correctly."""
    
def test_no_habit_learning():
    """Zero habit_strength means minimal preference."""
```

### Specification Test Cases

Tests TC1-TC6 validate against specification requirements:

```python
# TC1: Basic Go/NoGo Competition
agent.register_action_channel("go_strong", 0.8, 0.2)   # Go-biased
agent.register_action_channel("nogo_strong", 0.2, 0.8) # NoGo-biased
# With balanced neuromodulators → "go_strong" selected more often

# TC2: Dopamine Effect
# High DA → increases Go signals for all channels
choices_high_da = [...]
choices_low_da = [...]
assert choices_high_da has more exploitation

# TC3: Cortisol Effect
# High cortisol → increases NoGo inhibition
choices_high_cortisol = [...]
# NoGo-biased actions selected more

# TC4: PFC Pressure Effect
# High PFC pressure → nudges toward certain actions
choices_pfc_high = [...]
# If PFC pressure for specific action → higher selection

# TC5: Habit Integration
# Higher habit_strength → higher selection probability
agent.record_successful_outcomes(...)
agent.sleep()
# Successful action's habit increased

# TC6: Temperature from Neuromodulation
# High NE → more exploration (temperature increase)
choices_high_ne = [...]
# More variety in choices with high NE
variety_high_ne > variety_low_ne
```

---

## Writing Tests

### Test Template

```python
def test_feature_description():
    """
    Test description: What is being tested
    
    Setup: Initial conditions
    Action: What we're testing
    Expected: What should happen
    """
    # ARRANGE - Setup
    gate = BasalGangliaGate()
    channels = [
        ActionChannel("a", go_weight=0.8, nogo_weight=0.2),
        ActionChannel("b", go_weight=0.2, nogo_weight=0.8),
    ]
    neuromodulators = NeuromodulatorState(dopamine=1.0, cortisol=0.5)
    
    # ACT - Execute
    action = gate.choose(channels, neuromodulators=neuromodulators)
    
    # ASSERT - Verify
    assert action == "a", f"Expected 'a', got '{action}'"
```

### Common Patterns

#### Pattern 1: Testing Neuromodulator Effects

```python
def test_dopamine_increases_action_selection():
    """High dopamine makes actions more likely."""
    gate = BasalGangliaGate()
    channel = ActionChannel("attack", 0.8, 0.2)
    
    # Count selections with low dopamine
    low_da_count = 0
    for _ in range(100):
        neuromod = NeuromodulatorState(dopamine=0.5)
        if gate.choose([channel], neuromodulators=neuromod) == "attack":
            low_da_count += 1
    
    # Count selections with high dopamine
    high_da_count = 0
    for _ in range(100):
        neuromod = NeuromodulatorState(dopamine=2.0)
        if gate.choose([channel], neuromodulators=neuromod) == "attack":
            high_da_count += 1
    
    assert high_da_count > low_da_count, \
        f"High DA should increase selection: {high_da_count} vs {low_da_count}"
```

#### Pattern 2: Testing Habit Learning

```python
def test_habit_learns_from_success():
    """Habit strength increases after successful outcomes."""
    agent = Agent()
    
    # Register action
    agent.register_action_channel("good", go_weight=0.5, nogo_weight=0.5)
    
    # Record many successful outcomes
    for _ in range(10):
        agent.record_action_outcome("good", success=True, dopamine=2.0)
    
    # Sleep to consolidate
    agent.sleep()
    
    # Check habit increased
    state = agent.get_basal_ganglia_state()
    habit = state['action_channels']['good']['habit_strength']
    assert habit > 0.1, f"Expected habit > 0.1, got {habit}"
```

#### Pattern 3: Testing Selection Probabilities (Stochastic)

```python
def test_net_pressure_determines_probability():
    """Higher net pressure → higher selection probability."""
    gate = BasalGangliaGate()
    
    channels = [
        ActionChannel("strong", go_weight=0.8, nogo_weight=0.0),
        ActionChannel("weak", go_weight=0.2, nogo_weight=0.0),
    ]
    
    # Run many selections
    strong_count = 0
    for _ in range(200):
        action = gate.choose(channels)
        if action == "strong":
            strong_count += 1
    
    # Strong should be selected >150 times out of 200 (>75%)
    assert strong_count > 150, \
        f"Expected >75% 'strong' selections, got {strong_count}/200"
```

#### Pattern 4: Testing Edge Cases

```python
def test_empty_channels_raises_error():
    """Choosing from empty list should raise ValueError."""
    gate = BasalGangliaGate()
    
    with pytest.raises(ValueError):
        gate.choose([])
```

---

## Test Patterns

### Pattern: Single Responsibility

Each test should test ONE thing:

```python
# Good - tests one aspect
def test_dopamine_increases_go_signal():
    gate = BasalGangliaGate()
    channel = ActionChannel("a", 0.8, 0.2)
    
    low_da = gate.choose([channel], neuromodulators=NeuromodulatorState(dopamine=0.5))
    high_da = gate.choose([channel], neuromodulators=NeuromodulatorState(dopamine=2.0))
    # Both should select "a", high_da more often
    
# Bad - tests multiple things
def test_everything():
    # Test dopamine
    # Test cortisol
    # Test habit
    # Test PFC
    # ...
    pass
```

### Pattern: Naming Clarity

```python
# Good
def test_cortisol_inhibits_nogo_biased_actions():
    """When cortisol high, NoGo-biased actions are inhibited."""

# Bad
def test_cortisol():
    """Tests cortisol."""
```

### Pattern: Docstring

Always include docstring:

```python
def test_my_feature():
    """
    Brief description.
    
    Testing: What aspect is being tested
    Scenario: Under what conditions
    Expected: What should happen
    """
```

---

## Running Tests

### Run All Tests

```bash
# Quick run
pytest tests/ -q
# Output: 279 passed in 1.51s 

# Verbose output
pytest tests/ -v

# With coverage
pytest --cov=src tests/
```

### Run Specific Tests

```bash
# Run Phase 3 tests only
pytest tests/test_basal_ganglia.py -v

# Run specific test class
pytest tests/test_basal_ganglia.py::TestActionChannel -v

# Run specific test
pytest tests/test_basal_ganglia.py::test_basic_action_selection -v

# Run tests matching pattern
pytest -k "dopamine" -v
```

### Watch Mode

```bash
# Requires pytest-watch: pip install pytest-watch
ptw tests/
# Re-runs tests when files change
```

### Just Syntax Check (No Execution)

```bash
# Check for syntax errors without running
python -m pytest tests/ --collect-only
```

---

## Best Practices

### 1. Test Isolation

Each test should be independent:

```python
# Good - each test creates its own objects
def test_action_a():
    gate = BasalGangliaGate()
    # ...

def test_action_b():
    gate = BasalGangliaGate()  # New instance
    # ...

# Bad - tests depend on order
shared_gate = None

def test_first():
    global shared_gate
    shared_gate = BasalGangliaGate()

def test_second():
    global shared_gate
    # Depends on test_first running first!
```

### 2. Use Fixtures for Common Setup

```python
# Good
import pytest

@pytest.fixture
def basic_channels():
    return [
        ActionChannel("a", 0.8, 0.2),
        ActionChannel("b", 0.2, 0.8),
    ]

def test_choice_1(basic_channels):
    gate = BasalGangliaGate()
    action = gate.choose(basic_channels)
    assert action in ["a", "b"]

def test_choice_2(basic_channels):
    gate = BasalGangliaGate()
    action = gate.choose(basic_channels)
    assert action in ["a", "b"]
```

### 3. Clear Assertions

```python
# Good
assert high_da_count > low_da_count, \
    f"High DA should increase count: {high_da_count} vs {low_da_count}"

# Bad
assert high_da_count > low_da_count
```

### 4. Sufficient Sample Size for Stochastic Tests

```python
# Good - large sample for stochastic behavior
choices = [gate.choose(channels) for _ in range(1000)]
assert choices.count("action") > 750

# Bad - small sample, flaky
choices = [gate.choose(channels) for _ in range(10)]
assert choices.count("action") > 8
```

### 5. Test Both Happy and Sad Paths

```python
def test_success_case():
    """Test when everything works."""
    agent.record_action_outcome("action", success=True, dopamine=1.5)
    agent.sleep()
    habit = agent.get_habit("action")
    assert habit > 0.1

def test_failure_case():
    """Test when action fails."""
    agent.record_action_outcome("action", success=False, dopamine=0.0)
    agent.sleep()
    habit = agent.get_habit("action")
    assert habit < 0.5  # Habit decay
```

---

## Debugging Failed Tests

### Step 1: Read the Error

```
AssertionError: assert 45 > 60
  where 45 = high_da_count
```

What failed? Variable value is wrong. Why? Need to investigate.

### Step 2: Run with Verbose Output

```bash
pytest tests/test_basal_ganglia.py::failing_test -v --tb=long
```

### Step 3: Add Debug Prints

```python
def test_something():
    result = gate.choose(channels)
    print(f"DEBUG: result = {result}")
    print(f"DEBUG: channels = {channels}")
    assert result == expected  # Now you see debug output
```

Run with: `pytest -s` (don't capture output)

### Step 4: Use Debugging Tools

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # Now you can step through code
```

---

## Common Issues

### Issue: Flaky Test (Sometimes Passes, Sometimes Fails)

**Cause**: Stochastic behavior with insufficient samples

**Solution**: Increase sample size

```python
# Flaky (50 samples)
for _ in range(50):
    action = gate.choose(channels)
# Assertion on frequency might pass or fail randomly

# Robust (1000 samples)
for _ in range(1000):
    action = gate.choose(channels)
# Much more stable statistics
```

### Issue: Test Fails Intermittently

**Cause**: Floating point comparison or randomness

**Solution**: Use tolerances

```python
# Can fail due to floating point
assert habit == 0.5

# Better with tolerance
import math
assert math.isclose(habit, 0.5, rel_tol=1e-5)
```

### Issue: Test Passes but Shouldn't

**Cause**: Wrong assertion or not actually testing anything

**Solution**: Make assertion fail intentionally to verify it's working

```python
def test_my_feature():
    # Intentionally swap expected to make it fail
    assert action == "wrong_action"  # Should fail
    # If it doesn't fail, something is wrong with the test!
```

---

## Test Documentation Template

When writing complex tests, explain the test:

```python
def test_complex_scenario():
    """
    Test: Action selection with competing factors
    
    Scenario:
      - Two actions: "aggressive" (go=0.8, nogo=0.1) vs "cautious" (go=0.2, nogo=0.8)
      - High cortisol (stress) makes NoGo dominate
      - Even with go_weight advantage, NoGo-biased action should win
    
    Expected Behavior:
      - With high cortisol, "cautious" selected more often
      - Cortisol effect: multiplies nogo_weight
      
    Verification:
      - 100 selections, count distribution
      - Assert "cautious" > "aggressive" with high cortisol
      - Assert opposite with low cortisol
    """
    # Test code here...
```

---

## Next Steps

1. **Run existing tests** - Understand how they work
2. **Read test files** - Study testing patterns
3. **Write simple test** - Start with basic case
4. **Write complex test** - Add edge cases, stochastic behavior
5. **Integrate into test suite** - Run full test suite

---

## Resources

- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.en.md) - Developer reference
- [QUICK_START.md](QUICK_START.en.md) - Quick examples
- [pytest documentation](https://docs.pytest.org/) - Official pytest guide
- Source code in `src/` - See patterns there

---

**Last Updated:** February 2026  
**Status:** Complete and Current
