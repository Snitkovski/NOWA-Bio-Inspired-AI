# Development Guide for NOWA Cognitive

Russian version: [DEVELOPMENT.ru.md](DEVELOPMENT.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Contributing Guidelines

### Before You Start

1. **Read:** [ARCHITECTURE.md](ARCHITECTURE.en.md) - understand the system
2. **Check:** [API.md](API.en.md) - know the interfaces
3. **Test:** Run `pytest tests/ -v` - ensure baseline passes

---

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone your fork (or use main repo if contributor)
git clone https://github.com/yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive

# Create feature branch
git checkout -b feature/your-feature-name

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dev dependencies (if available)
pip install -r requirements-dev.txt
```

### 2. Make Changes

**Example: Adding a new feature to neuromodulators**

```bash
# Edit file
code src/neuromodulators.py

# Or in your editor:
# 1. Add new method
# 2. Add docstring
# 3. Add type hints
```

### 3. Write Tests

```bash
# Create test file
code tests/test_my_feature.py

# Write test template:
# def test_my_feature():
# """Description of what you're testing"""
# # Arrange
# # Act
# # Assert
```

### 4. Run Tests

```bash
# Run your new tests
python -m pytest tests/test_my_feature.py -v

# Run all tests to ensure nothing broke
python -m pytest tests/ -v

# Expected: 219+ passed (including your new tests)
```

### 5. Commit & Push

```bash
# Stage changes
git add src/ tests/ docs/

# Commit with clear message
git commit -m "feat: add new feature to neuromodulators

- Description of what changed
- Why it was necessary
- Any breaking changes (if none, omit)"

# Push to your fork
git push origin feature/your-feature-name
```

### 6. Open Pull Request

- Go to GitHub
- Click "Compare & pull request"
- Write clear description
- Wait for review

---

## Code Style Guide

### Python Style (PEP 8)

```python
# GOOD: 4 spaces, clear names, docstrings
class NeuromodulatorState:
    """State of all neurotransmitter levels."""
    
    def __init__(self):
        self.dopamine = 0.1
        self.serotonin = 0.1
    
    def update_from_signals(self, reward: float, novelty: float, conflict: float):
        """Update all modulators based on environmental signals.
        
        Args:
            reward: [-1.0, 1.0] reward prediction error
            novelty: [0.0, 1.0] environment novelty
            conflict: [0.0, 1.0] action conflict
        """
        if reward > 0:
            self.dopamine += 0.25 * reward

# BAD: Unclear names, no docstrings, poor formatting
class NM:
    def __init__(self):
        self.d=0.1
    def upd(self,r,n,c):
        if r>0:self.d+=0.25*r
```

### Naming Conventions

```python
# Classes: PascalCase
class NeuromodulatorState:
    pass

class AffectiveState:
    pass

# Functions/Methods: snake_case
def update_from_signals(self, reward: float):
    pass

def get_learning_rate_modifier(self) -> float:
    pass

# Constants: UPPER_SNAKE_CASE
DA_BASELINE = 0.1
DECAY_HALF_LIFE = 90

# Private methods: _leading_underscore
def _clamp_all(self):
    pass
```

### Type Hints

```python
# ALWAYS use type hints for clarity
from typing import Dict, List, Optional

def consolidate_pattern(
    experience_cluster: List[dict],
    strength: float
) -> Dict[str, float]:
    """Consolidate experiences into pattern."""
    return {}

# Optional for simple cases
def decay_over_time(self, seconds: float) -> None:
    """Decay all modulators over time."""
    pass
```

### Docstrings

```python
class NeuromodulatorState:
    """State of all neurotransmitter levels.
    
    Phase 2 Implementation with 4 modulators:
    - Dopamine (DA): Reward prediction & motivation
    - Serotonin (HT): Stability & temporal depth
    - Norepinephrine (NE): Arousal & attention
    - Cortisol (CORT): Stress response
    
    Range: [0.0, 1.0] for all, clamped automatically.
    Baseline: DA=0.1, HT=0.1, NE=0.1, CORT=0.05
    
    Attributes:
        dopamine (float): Current dopamine level
        serotonin (float): Current serotonin level
        norepinephrine (float): Current norepinephrine level
        cortisol (float): Current cortisol level
    """
    
    def update_from_signals(
        self,
        reward: float,
        novelty: float,
        conflict: float
    ) -> None:
        """Update all modulators based on environmental signals.
        
        Implements Phase 2 specification exactly.
        
        Args:
            reward: [-1.0, 1.0] reward prediction error
            novelty: [0.0, 1.0] environmental novelty
            conflict: [0.0, 1.0] action conflict/uncertainty
            
        Returns:
            None (updates internal state)
            
        Raises:
            ValueError: If parameters are out of valid ranges
            
        Note:
            All values are clamped to [0.0, 1.0] after update.
            
        Example:
            >>> state = NeuromodulatorState()
            >>> state.update_from_signals(0.8, 0.3, 0.0)
            >>> state.dopamine
            0.3
        """
```

---

## Architecture Principles

### 1. Neuromodulators Don't Decide

**WRONG:**
```python
def choose_action(self):
    if self.dopamine > 0.5:
        return "attack"  # VIOLATION!
```

**RIGHT:**
```python
def choose_action(self):
    # Selector chooses, neuromodulators only modify
    base_confidence = compute_confidence()
    modified_rate = base_confidence * self.get_learning_rate_modifier()
    return selector.choose(modified_rate)
```

### 2. No Learning During Waking

**WRONG:**
```python
def step(self):
    # Store experience
    self.hippocampus.add(experience)
    # WRONG: Learning during waking!
    self.cortex.consolidate(experience)
```

**RIGHT:**
```python
def step(self):
    # Only store experience, don't learn
    self.hippocampus.add(experience)
    
def sleep(self):
    # Learning only happens here
    self.sleep_manager.consolidate()
```

### 3. Immutable Episodic Memory

**WRONG:**
```python
# Trying to modify hippocampal memories
experience.reward = 0.9  # This changes the past!
```

**RIGHT:**
```python
# Hippocampus stores immutable records
experience = Experience(reward=0.8)
hippocampus.add(experience)  # Stored forever, unchanged
```

### 4. Selector is ONLY Action Chooser

**WRONG:**
```python
# Directly returning action from affect
def choose_action(affect):
    if affect.valence > 0:
        return "happy_action"  # Only Selector can choose!
```

**RIGHT:**
```python
# Get pressures from all sources
pressures = {
    "action1": 0.8,
    "action2": 0.3,
}
# Only selector decides
return selector.choose(pressures)
```

---

## Testing Requirements

### For Any Code Change

1. **Unit Tests Required**
   - Test individual methods
   - Mock external dependencies
   - Cover happy path + edge cases

2. **Integration Tests**
   - Test module interactions
   - Verify signals propagate correctly
   - Check state consistency

3. **Test Coverage**
   - Minimum 80% code coverage
   - All public methods tested
   - All branches tested

### Example Test File

```python
import pytest
from src.neuromodulators import NeuromodulatorState

class TestNewFeature:
    """Test suite for new neuromodulator feature."""
    
    def test_basic_functionality(self):
        """Test basic operation of new feature."""
        state = NeuromodulatorState()
        # ... test code ...
        assert state.dopamine > 0.0
    
    def test_edge_case_zero_input(self):
        """Test with zero input values."""
        state = NeuromodulatorState()
        state.update_from_signals(0.0, 0.0, 0.0)
        assert state.dopamine == 0.1  # No change from baseline
    
    def test_edge_case_max_input(self):
        """Test with maximum input values."""
        state = NeuromodulatorState()
        state.update_from_signals(1.0, 1.0, 1.0)
        # All should be clamped to <= 1.0
        assert state.dopamine <= 1.0
        assert state.serotonin <= 1.0
    
    def test_consistency_with_spec(self):
        """Verify Phase 2 specification compliance."""
        state = NeuromodulatorState()
        state.dopamine = 0.1
        state.update_from_signals(reward=1.0, novelty=0.0, conflict=0.0)
        # From spec: DA increases by 0.25 * reward
        assert state.dopamine == 0.1 + 0.25 * 1.0
```

---

## Common Development Tasks

### Adding a New Modifier Method

```python
# In src/neuromodulators.py

def get_my_new_modifier(self) -> float:
    """Description of what this modifier does.
    
    Returns:
        float: Modifier value in valid range
        
    Example:
        >>> state = NeuromodulatorState()
        >>> state.dopamine = 0.8
        >>> modifier = state.get_my_new_modifier()
        >>> 0.0 <= modifier <= 1.0
        True
    """
    # Compute modifier based on neuromodulator state
    modifier = 1.0 + 0.3 * self.dopamine
    
    # ALWAYS clamp to valid range
    return max(MIN_VALUE, min(MAX_VALUE, modifier))
```

**Then test it:**
```python
def test_my_new_modifier():
    state = NeuromodulatorState()
    
    # Test low state
    state.dopamine = 0.0
    mod_low = state.get_my_new_modifier()
    assert mod_low >= 0.0
    
    # Test high state
    state.dopamine = 1.0
    mod_high = state.get_my_new_modifier()
    assert mod_high <= 1.5
    
    # Test it increases with input
    assert mod_high > mod_low
```

### Modifying update_from_signals

**BE VERY CAREFUL** - This is validated by Phase 2 spec tests!

```python
# Phase 2 specification (DO NOT CHANGE without good reason):
# Dopamine: reward > 0 → DA += 0.25 * reward
# Serotonin: reward > 0 ∧ conflict == 0 → HT += 0.05 * reward
# Norepinephrine: NE += 0.30 * novelty + 0.15 * conflict
# Cortisol: CORT += 0.20 * |reward| + 0.25 * conflict

# If you must change:
# 1. Get approval from project maintainers
# 2. Update specification document
# 3. Update ALL tests
# 4. Run: pytest tests/test_neuromodulators_phase2.py -v
# 5. Verify all 14 tests still pass
```

---

## Debugging Tips

### Use Print Statements

```python
def update_from_signals(self, reward, novelty, conflict):
    print(f"[DEBUG] Input: reward={reward}, novelty={novelty}, conflict={conflict}")
    
    if reward > 0:
        self.dopamine += 0.25 * reward
        print(f"[DEBUG] Updated dopamine to {self.dopamine}")
```

### Use pytest -v and --tb

```bash
# Verbose output
python -m pytest tests/test_something.py -v

# Full traceback
python -m pytest tests/test_something.py -v --tb=long

# Print debugging output
python -m pytest tests/test_something.py -v -s
```

### Use pdb (Python Debugger)

```python
def problematic_function(self):
    import pdb; pdb.set_trace()  # Execution stops here
    # You can now:
    # p variable_name    - print variable
    # n                   - next line
    # c                   - continue
    # l                   - list code
```

### Check Assertions

```python
def test_something():
    state = NeuromodulatorState()
    state.dopamine = 0.5
    
    # If this fails, pytest shows what was expected vs actual
    assert state.dopamine == 0.5  # Clear failure message
```

---

## Performance Optimization

### Before Optimizing

1. **Measure:** Does it actually slow things down?
   ```bash
   python -m pytest tests/ --durations=10
   ```

2. **Profile:** Which part is slow?
   ```python
   import cProfile
   cProfile.run("agent.step(event)")
   ```

3. **Optimize:** Only after measurement

### Common Bottlenecks

- Memory access (use numpy for numerical operations)
- List operations (use appropriate data structures)
- Repeated calculations (cache results)

---

## Documentation Requirements

### Code Documentation

Every public method must have:
- Docstring (what it does)
- Type hints (what parameters/return types)
- Example (how to use it)

### File Documentation

Start each file with:
```python
"""Module description and purpose.

This module implements [what it does] for [which part of system].

Key classes:
- ClassName1: Brief description
- ClassName2: Brief description

Example:
    >>> from src.module import Class
    >>> obj = Class()
    >>> result = obj.method()
"""
```

### Markdown Documentation

Update relevant docs when adding features:
- [ARCHITECTURE.md](ARCHITECTURE.en.md) - System changes
- [API.md](API.en.md) - New methods/classes
- [TESTING.en.md](TESTING.en.md) - New test categories

---

## Git Commit Messages

### Format

```
type(scope): brief message

Longer explanation of what changed and why.
Can be multiple paragraphs.

- List specific changes
- Can include bullet points

Fixes #123  (if related to issue)
```

### Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Test changes
- `refactor:` Code reorganization
- `perf:` Performance improvement

### Examples

```bash
git commit -m "feat(neuromodulators): add dopamine spike mechanism

- Dopamine now increases 25% more on unexpected positive rewards
- Updated get_learning_rate_modifier() to consider spike state
- Added tests for spike behavior (3 new unit tests)

Implements feature requested in issue #42"

git commit -m "fix(selector): ensure stochastic selection works for low confidence"

git commit -m "docs: update API reference with new modifier methods"
```

---

## Code Review Checklist

Before submitting PR, verify:

- All tests pass: `pytest tests/ -v`
- Code style follows guide above
- Type hints on all public methods
- Docstrings with examples
- Tests cover new code (80%+ coverage)
- No hardcoded values without justification
- Neuromodulators only modify, never decide
- No learning during waking phase
- Selector still only action chooser
- Updated docs if API changed
- Meaningful commit message
- No debug prints or commented code left

---

## Resources

### Internal Documentation
- [ARCHITECTURE.md](ARCHITECTURE.en.md) - System design
- [API.md](API.en.md) - Component interfaces
- [TESTING.en.md](TESTING.en.md) - Test guide
- [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md) - Phase 2 spec

### External Resources
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [pytest Documentation](https://docs.pytest.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Git Commit Best Practices](https://chris.beams.io/posts/git-commit/)

---

## Getting Help

1. **Ask questions in PR comments**
   - Maintainers will help!

2. **Check test examples**
   - Look at similar tests for patterns

3. **Read ARCHITECTURE.md**
   - Explains design decisions

4. **Check git history**
   - `git log -p src/file.py` shows how code evolved

---

## Release Process (for maintainers)

```bash
# Update version
# 1. Update src/__version__.py
# 2. Update version in setup.py or pyproject.toml

# Run full test suite
python -m pytest tests/ -v

# Create tag
git tag v1.2.0

# Push to main
git push origin main
git push origin v1.2.0

# Create release on GitHub
# - Summary of changes
# - Breaking changes warning
# - Link to full changelog
```

---

**Happy hacking!**

Remember: Write tests first, code second, optimize last!
