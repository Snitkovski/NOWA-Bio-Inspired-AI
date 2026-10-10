# Developer Guide

Russian version: [DEVELOPER_GUIDE.ru.md](DEVELOPER_GUIDE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**For**: Developers adding features, fixing bugs, extending the system  
**Time**: 2-4 hours to fully understand  
**Prerequisites**: Python 3.13+, basic async knowledge

---

## Table of Contents

1. [Setup](#setup)
2. [Architecture Overview](#architecture-overview)
3. [Key Components](#key-components)
4. [Phase 3: Basal Ganglia](#phase-3-basal-ganglia)
5. [Adding Features](#adding-features)
6. [Testing](#testing)
7. [Common Tasks](#common-tasks)
8. [Best Practices](#best-practices)

---

## Setup

### 1. Install Project

```bash
cd e:\git\NOWA-Cognitive
pip install -r requirements.txt
python -m pytest tests/ -q
# Should show: 279 passed ✅
```

### 2. Verify Installation

```python
# test_setup.py
from src.agent import Agent
from src.basal_ganglia import ActionChannel, BasalGangliaGate

agent = Agent()
print(f"✅ Agent created: {agent.agent_name}")
print(f"✅ Imports working!")
```

### 3. IDE Setup

**Recommended**: VS Code with Python extensions:
- Pylance (type checking)
- Python (syntax highlighting)
- Pytest Explorer (test runner)

---

## Architecture Overview

### High-Level Structure

```
┌─────────────────────────────────────┐
│         AGENT (main class)          │
└─────────────────────────────────────┘
         ↓⬅️⬆️↓⬅️⬆️↓
┌──────────────────────────────────────────────────────────────┐
│ Basal Ganglia    │ PFC Advisory │ Neuromodulators │ Sleep    │
├──────────────────┼──────────────┼─────────────────┼──────────┤
│ Go/NoGo          │ Pressure     │ Dopamine        │ Learning │
│ Selection        │ Signal       │ Cortisol        │ Pipeline │
│ Habit Learning   │ Modulation   │ Norepinephrine  │          │
└──────────────────────────────────────────────────────────────┘
         ↓⬅️⬆️↓⬅️⬆️↓
┌─────────────────────────────────────┐
│  Affective Regulators (4 states)    │
│  - Valence, Arousal, Threat, Curiosity
└─────────────────────────────────────┘
```

### Component Relationships

1. **Agent**: Main orchestrator, holds all subsystems
2. **BasalGanglia**: Implements action selection via Go/NoGo
3. **ActionChannel**: Individual action with weights and habit
4. **Neuromodulators**: Chemical modulators affecting behavior
5. **AffectiveState**: Emotional state parameters
6. **Sleep**: Learning consolidation during sleep

---

## Key Components

### 1. ActionChannel (src/basal_ganglia.py)

Represents a single executable action:

```python
class ActionChannel:
    """Individual action in Basal Ganglia decision."""
    
    action_id: str              # Unique identifier
    go_weight: float            # "Approach" weight (0-1)
    nogo_weight: float          # "Avoid" weight (0-1)
    habit_strength: float       # Learned habit strength (0-1)
    last_outcome: float         # Last success indicator
```

**Key operations**:
- `get_go_signal()` - Compute Go signal
- `get_nogo_signal()` - Compute NoGo signal
- `learn_from_outcome()` - Update habit_strength based on success

### 2. BasalGangliaGate (src/basal_ganglia.py)

Implements the action selection mechanism:

```python
class BasalGangliaGate:
    """Go/NoGo competition for action selection."""
    
    def choose(
        self,
        channels: list[ActionChannel],
        pfc_pressure: float = 0.5,    # PFC advisory signal
        affective_state: AffectiveState = None,
        neuromodulators: NeuromodulatorState = None
    ) -> str:
        """Select action via Go/NoGo competition.
        
        Formula: Net = Go - 0.5×NoGo + PFC + habit×0.3
        - Go: approach tendency
        - NoGo: avoid tendency  
        - PFC: prefrontal cortex pressure
        - habit: learned behavior strength
        """
```

**Key Formula**:
```
For each channel:
  Go = go_weight × dopamine × (1 + norepinephrine)
  NoGo = nogo_weight × cortisol
  Net = Go - 0.5×NoGo + pfc_pressure + habit_strength×0.3
  
Select action with highest Net (softmax with temperature)
```

### 3. Neuromodulators (src/neuromodulators.py)

Chemical signals affecting behavior:

```python
class NeuromodulatorState:
    dopamine: float             # Motivation (default: 1.0)
    cortisol: float             # Stress (default: 0.5)
    norepinephrine: float       # Attention (default: 0.8)
    serotonin: float            # Mood (default: 0.7)
```

**Effects**:
- **Dopamine**: Multiplies Go signal
- **Cortisol**: Multiplies NoGo signal
- **Norepinephrine**: Softmax temperature (exploration)
- **Serotonin**: Affects learning rate

---

## Phase 3: Basal Ganglia

### What is Phase 3?

Complete implementation of action selection via biological Go/NoGo circuit found in basal ganglia.

### Key Features

1. **Action Registration**
   ```python
   agent.register_action_channel(
       action_id="attack",
       go_weight=0.8,      # Strong approach tendency
       nogo_weight=0.2     # Weak avoid tendency
   )
   ```

2. **Action Selection**
   ```python
   action = agent.choose_action_via_basal_ganglia(
       pfc_pressure=1.0    # Strong directive from PFC
   )
   ```

3. **Learning from Outcome**
   ```python
   agent.record_action_outcome(
       action=action,
       success=True,       # Did it work?
       dopamine=1.5        # How much reward?
   )
   ```

4. **Consolidation During Sleep**
   ```python
   agent.sleep()  # Habit strengths based on success history
   ```

### Test Coverage

Phase 3 has 29 tests covering:

```
ActionChannel (8 tests):
  ✅ Signal computation
  ✅ Habit learning
  ✅ Outcome recording

BasalGangliaGate (12 tests):
  ✅ Basic action selection
  ✅ Go/NoGo competition
  ✅ Neuromodulator effects
  ✅ PFC pressure effects
  ✅ Test cases TC1-TC6

Learning (4 tests):
  ✅ Habit consolidation
  ✅ Success tracking
  ✅ Dopamine effects

Integration (2 tests):
  ✅ Full agent use
  ✅ Multi-episode learning

Edge Cases (3 tests):
  ✅ No actions registered
  ✅ Empty parameters
  ✅ Extreme values
```

Run them:
```bash
pytest tests/test_basal_ganglia.py -v
# Output: 29 passed ✅
```

---

## Adding Features

### Add a New Neuromodulator

1. **Update NeuromodulatorState** (src/neuromodulators.py):

```python
class NeuromodulatorState:
    # ... existing fields ...
    my_new_modulator: float = 1.0  # Default value
```

2. **Add effect in choose()** (src/basal_ganglia.py):

```python
net = channel.go_weight * neuromodulators.dopamine
# Add your modulator effect:
net *= (1 + neuromodulators.my_new_modulator * 0.5)
```

3. **Add test** (tests/test_basal_ganglia.py):

```python
def test_my_new_modulator():
    """Test that my_new_modulator affects choice."""
    # ...test code...
    assert action == expected_action
```

4. **Run tests**:
```bash
pytest tests/test_basal_ganglia.py::test_my_new_modulator -v
```

### Add a New Learning Mechanism

1. **Create new class** in src/basal_ganglia.py:

```python
class MyLearningMechanism:
    """Description of your learning mechanism."""
    
    def learn(self, outcome: float) -> None:
        """Update based on outcome."""
        pass
```

2. **Integrate into BasalGangliaLearning**:

```python
class BasalGangliaLearning:
    def consolidate_during_sleep(self, ...):
        # ... existing code ...
        my_mechanism = MyLearningMechanism()
        # ... use it ...
```

3. **Test thoroughly**:

```python
def test_my_learning_mechanism():
    """Test learning behavior."""
    pass
```

---

## Testing

### Test Structure

```
tests/
├── test_basal_ganglia.py      # Phase 3 tests (29)
├── test_agent.py              # Agent integration
├── test_affective_regulators.py
└── ... (250 other tests)
```

### Write a Test

```python
def test_my_feature():
    """Test description.
    
    Tests: action_selection with specific neuromodulator
    Expected: specific behavior
    """
    # Setup
    gate = BasalGangliaGate()
    channels = [
        ActionChannel("a", go_weight=0.8, nogo_weight=0.2),
        ActionChannel("b", go_weight=0.2, nogo_weight=0.8),
    ]
    
    # Execute
    action = gate.choose(channels, pfc_pressure=1.0)
    
    # Verify
    assert action == "a", f"Expected 'a', got {action}"
```

### Run Tests

```bash
# All tests
pytest tests/ -q

# Specific test class
pytest tests/test_basal_ganglia.py::TestActionChannel -v

# Specific test
pytest tests/test_basal_ganglia.py::test_basic_action_selection -v

# With coverage
pytest --cov=src tests/

# Watch mode (requires pytest-watch)
ptw tests/
```

### Test Best Practices

1. **One assertion per test** (or related assertions)
2. **Clear test names** - Describe what's being tested
3. **Use docstrings** - Explain what and why
4. **Arrange-Act-Assert pattern**:
   ```python
   # Arrange - setup
   gate = BasalGangliaGate()
   
   # Act - execute
   action = gate.choose(channels)
   
   # Assert - verify
   assert action == expected
   ```

---

## Common Tasks

### Task 1: Add a new action to an agent

```python
# Create agent
agent = Agent(agent_name="MyBot")

# Register action
agent.register_action_channel(
    action_id="my_action",
    go_weight=0.7,      # 0-1
    nogo_weight=0.3     # 0-1
)

# Use it
action = agent.choose_action_via_basal_ganglia()
assert "my_action" in [a for a in agent.get_basal_ganglia_state()...]
```

### Task 2: Test neuromodulator effects

```python
agent = Agent()
agent.register_action_channel("brave", go_weight=0.8, nogo_weight=0.2)
agent.register_action_channel("cautious", go_weight=0.2, nogo_weight=0.8)

# Test 1: High dopamine makes agent brave
agent.neuromodulators.dopamine = 2.0
brave_count = sum(
    agent.choose_action_via_basal_ganglia() == "brave"
    for _ in range(100)
)
assert brave_count > 70, f"Expected >70, got {brave_count}"

# Test 2: High cortisol makes agent cautious
agent.neuromodulators.dopamine = 1.0
agent.neuromodulators.cortisol = 2.0
cautious_count = sum(
    agent.choose_action_via_basal_ganglia() == "cautious"
    for _ in range(100)
)
assert cautious_count > 70, f"Expected >70, got {cautious_count}"
```

### Task 3: Train an agent

```python
agent = Agent()
agent.register_action_channel("good_action", go_weight=0.5, nogo_weight=0.5)
agent.register_action_channel("bad_action", go_weight=0.5, nogo_weight=0.5)

# Train for 100 episodes
for episode in range(100):
    action = agent.choose_action_via_basal_ganglia()
    
    # "good_action" always succeeds
    success = (action == "good_action")
    dopamine = 1.5 if success else 0.0
    
    agent.record_action_outcome(action, success=success, dopamine=dopamine)
    
    # Sleep every 10 episodes to consolidate
    if episode % 10 == 0:
        agent.sleep()

# Check learning
state = agent.get_basal_ganglia_state()
good_habit = state['action_channels']['good_action']['habit_strength']
bad_habit = state['action_channels']['bad_action']['habit_strength']

print(f"Good action habit: {good_habit:.3f}")
print(f"Bad action habit: {bad_habit:.3f}")
assert good_habit > bad_habit, "Agent should have learned good_action"
```

---

## Best Practices

### 1. Type Hints

Always use type hints:

```python
# ✅ Good
def choose(self, channels: list[ActionChannel]) -> str:
    pass

# ❌ Avoid
def choose(self, channels):
    pass
```

### 2. Docstrings

Document all public methods:

```python
def choose(self, channels: list[ActionChannel]) -> str:
    """Select action via Go/NoGo competition.
    
    Args:
        channels: List of possible actions
        
    Returns:
        Action ID string of selected action
        
    Formula:
        Net = Go - 0.5×NoGo + PFC + habit×0.3
    """
```

### 3. Constants

Define magic numbers as constants:

```python
# ✅ Good
HABIT_GAIN = 0.3
NOGO_MULTIPLIER = 0.5

net = (channel.go_weight - NOGO_MULTIPLIER * channel.nogo_weight
       + pfc_pressure + channel.habit_strength * HABIT_GAIN)

# ❌ Avoid
net = channel.go_weight - 0.5 * channel.nogo_weight + pfc_pressure + channel.habit_strength * 0.3
```

### 4. Error Handling

Handle edge cases gracefully:

```python
# ✅ Good
if not channels:
    raise ValueError("At least one action channel required")

# ❌ Avoid
channels[0]  # Crash if empty
```

### 5. Testing

Test public APIs thoroughly:

```python
# ✅ Good
def test_choose_raises_on_empty_channels():
    gate = BasalGangliaGate()
    with pytest.raises(ValueError):
        gate.choose([])

# ❌ Avoid
def test_choose():
    gate = BasalGangliaGate()
    gate.choose([ActionChannel(...)])
```

---

## Code Navigation

### Key Files

```
src/
├── agent.py                    # Main Agent class (400+ lines)
├── basal_ganglia.py           # Phase 3 implementation (600+ lines)
├── neuromodulators.py         # Neuromodulator effects (200+ lines)
├── affective_regulators.py    # Affective state (300+ lines)
├── sleep.py                   # Learning consolidation (200+ lines)
└── gui.py                     # Visualization interface (800+ lines)

tests/
├── test_basal_ganglia.py      # 29 Phase 3 tests
├── test_agent.py              # Integration tests
└── ... (20+ other test files)

Docs/
├── QUICK_START.md             # First 5 minutes
├── PHASE_3_GUIDE.md           # Detailed Phase 3
├── ARCHITECTURE.md            # Full system design
└── API.md                     # API reference
```

### Find Things

```bash
# Find a class
grep -r "class ActionChannel" src/

# Find a method
grep -r "def choose" src/

# Find imports of something
grep -r "from src.basal_ganglia import" tests/

# Find all test files
find tests/ -name "test_*.py"
```

---

## Troubleshooting

### Issue: Tests fail with "ModuleNotFoundError"

**Solution**:
```bash
# Make sure you're in project root
cd e:\git\NOWA-Cognitive

# Verify all tests pass
pytest tests/ -q

# If still failing, reinstall
pip install -r requirements.txt
```

### Issue: "AttributeError: module has no attribute X"

**Solution**:
1. Check if the class/function exists
2. Verify import path is correct
3. Check for circular imports

```python
# Debug imports
python -c "from src.basal_ganglia import BasalGangliaGate; print('✅')"
```

### Issue: Test occasionally fails (flaky test)

**Solution**: Tests involving randomness need larger sample sizes:

```python
# ❌ Flaky (small sample)
choices = [gate.choose(channels) for _ in range(10)]
assert choices.count("a") > 8

# ✅ More robust (larger sample)
choices = [gate.choose(channels) for _ in range(1000)]
assert choices.count("a") > 800
```

---

## Next Steps

1. **Read PHASE_3_GUIDE.md** - Comprehensive Phase 3 documentation
2. **Read ARCHITECTURE.md** - Full system design
3. **Review test files** - Learn by example from tests
4. **Start coding** - Pick a feature to add or improve

---

## Questions?

1. Check [API.md](API.en.md) for API reference
2. Read test files for usage examples
3. Check docstrings in source code
4. Search issues/discussions if stuck

---

**Happy coding!**

**Last Updated**: February 2026  
**Status**: Complete and Current
