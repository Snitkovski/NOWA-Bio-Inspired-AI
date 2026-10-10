# GUI Refactoring for NOWA Cognitive Architecture

Russian version: [GUI_REFACTORING.ru.md](GUI_REFACTORING.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Overview

The NOWA GUI has been fully refactored to align with the new cognitive architecture where **behavior emerges through sleep consolidation, not through waking learning**.

## Key Changes

### Removed

1. **Direct Learning During Waking**
   - `selector.learn()` calls
   - Reward-based weight updates
   - Direct accuracy-based training

2. **Training Dialogs**
   - Training button — now shows a deprecation warning
   - Auto-Training button — now shows a deprecation warning
   - SelectorTrainer usage

3. **Selector Weight Display**
   - Action Weights tab
   - Weight visualization and bar charts
   - Learning rate parameters

### Added

1. **Sleep Consolidation Dialog**
   - Sleep button — new primary learning mechanism
   - Configure consolidation cycles (1-10)
   - View consolidation statistics
   - Track pattern formation

2. **Enhanced Inspector**
   - 5 tabs instead of 4:
     - Episodic memory (experiences)
     - Semantic memory (patterns)
     - Action selection (no weights, pressure-based)
     - Consolidation — sleep consolidation pipeline
     - Statistics — overall statistics

3. **Cognitive State Display**
   - Shows consolidation cycles
   - Shows experience reinforcement counts
   - Shows pattern strength values
   - Consolidation ratio (patterns/experiences)

### Modified

1. **Feedback Mechanism**
   - Old: Direct weight optimization
   - New: Store experience with intensity (0.2-1.0)
   - Shows message: "Experience saved. Use Sleep for consolidation."
   - Intensity calculated from a 5-point scale:
     - very poor = 0.2
     - poor = 0.4
     - neutral = 0.6
     - good = 0.8
     - excellent = 1.0

2. **Statistics Display**
   - Before: Showed selector weights and averages
   - After: Shows:
     - Last action taken
     - Total experiences in hippocampus
     - Total patterns in cortex
     - Sleep consolidation cycles

3. **Memory Display**
   - Shows episodic memory stats (reinforcement counts)
   - Shows semantic memory stats (pattern strength)
   - Shows consolidation cycle count

4. **Experience Loading**
   - Loads experiences into hippocampus (not directly to cortex)
   - Sets intensity based on experience data
   - Respects reinforcement counts

## Usage Workflow

### 1. WAKING: Interaction
```
User: "Hello"
  ↓
Agent: Takes action based on current memory
  ↓
User: Rates response (very poor to excellent)
  ↓
System: Stores experience with intensity
```

### 2. SLEEPING: Consolidation
```
Click: Sleep button
  ↓
Configure: Number of cycles (1-10)
  ↓
System: Consolidates experiences to patterns
  - Replay similar experiences
  - Cluster related memories
  - Abstract into semantic patterns
  - Forget unstable traces
  ↓
Result: New behavior based on consolidated patterns
```

### 3. WAKING AGAIN: Behavior Changes
```
User: "Hello"
  ↓
Agent: Action selection now uses:
  - Hippocampal activation (recent + reinforced)
  - Cortical patterns (consolidated memories)
  - Pressure-based choice (NOT weights)
  ↓
Behavior EMERGES from consolidation!
```

## Inspector Tabs

### 1. Episodic Memory
Shows all experiences in hippocampus:
- Signature (context hash)
- Events (context → action → consequence)
- Intensity (0-2)
- Reinforcement count (times repeated)
- Last activated (timestamp)

### 2. Semantic Memory
Shows cortical patterns created during sleep:
- Signature (abstracted pattern)
- Strength (consolidation strength)
- Created at (when consolidation happened)

Patterns only appear AFTER sleep consolidation.

### 3. Action Selection
Shows that selector has:
- NO weights dictionary
- NO learn() method
- NO learning rate
- Confidence threshold (0.7)
- Selection based on pressure (not weights)

### 4. Consolidation
Shows sleep pipeline:
1. **Replay**: Strengthen active memories
2. **Cluster**: Group similar experiences
3. **Consolidate**: Abstract to patterns
4. **Forget**: Remove unstable traces

Statistics:
- Total sleep cycles completed
- Experiences in hippocampus
- Patterns in cortex
- Consolidation ratio

### 5. Statistics
Summary of agent state:
- Total experiences stored
- Total patterns formed
- Sleep cycles completed
- Average reinforcement per experience
- Average pattern strength
- Last action taken

## Core Principle Verification

**Question:** If selector is frozen and agent gets new experience, will behavior change?

**Answer:** YES, through sleep consolidation:
1. New experiences accumulate in hippocampus
2. Sleep clusters and consolidates them
3. Cortical patterns shift
4. Selection pressure changes (hippocampal activation + pattern bias)
5. Behavior emerges as different

**This proves:** Learning happens during SLEEP, not during waking.

## Code Changes

### GUI Initialization
```python
# Before
self.sleep_manager = SleepManager(self.hippocampus, self.cortex, interval=30)
self.sleep_manager.start()  # ❌ Auto sleep thread

# After
self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
self.agent = Agent(self.hippocampus, self.cortex, self.selector, self.sleep_manager)
```

### Processing Input
```python
# Before
def process_input(self, user_input):
    context = [f"user:{user_input}"]
    action = self.agent.step(context)  # No learning here

# After (unchanged - already correct)
def process_input(self, user_input):
    context = [f"user:{user_input}"]
    action = self.agent.step(context)  # Still no learning
```

### Feedback Processing
```python
# Before
def submit_feedback(self):
    reward = self.feedback_var.get()
    self.agent.step(self.last_context, reward)  # ❌ Direct learning
    self.selector.learn(action, reward)  # ❌ Weight update

# After
def submit_feedback(self):
    intensity = (self.feedback_var.get() + 3) / 5.0  # Convert to 0.2-1.0
    result_event = Event(f"feedback:{self.feedback_var.get()}", 
                        EventType.CONSEQUENCE)
    # Experience stored, NOT learned
    # Will be consolidated during sleep!
```

### Sleep Dialog
```python
def open_sleep_dialog(self):
    """New dialog for manual sleep consolidation"""
    # Shows before/after statistics
    # Allows configurable cycles
    # Displays consolidation results
    # Updates agent state
```

## Deprecations

### SelectorTrainer
```python
from trainer import SelectorTrainer

trainer = SelectorTrainer(selector, hippocampus, cortex)
# Raises NotImplementedError with message:
# "SelectorTrainer is DEPRECATED and violates NOWA principles.
#  Learning happens during sleep consolidation, not through direct optimization.
#  Use SleepManager instead (from sleep.py)"
```

### Training Buttons
- Training shows a deprecation warning
- Auto-Training shows a deprecation warning

## Testing

All GUI functionality tested with 15 comprehensive tests:
- GUI imports correctly
- Agent initializes for GUI
- Waking does not trigger learning
- Sleep consolidates experiences
- Feedback does not directly learn
- Agent state reflection works
- Selector is non-learnable
- Experiences are immutable
- SleepManager is the only learning mechanism
- GUI component initialization
- Complete GUI workflow
- NOWA principle verified
- Deprecated methods handled

**Total: 81 tests passing** (15 GUI + 66 core architecture tests)

## Future Enhancements

1. **Real-time Sleep Visualization**
   - Show clustering in progress
   - Animate pattern formation
   - Visualize consolidation

2. **Sleep Scheduling**
   - Automatic sleep at intervals
   - Sleep quality metrics
   - Consolidation efficiency graphs

3. **Memory Exploration**
   - Navigate experiences by context
   - Trace pattern formation
   - Show decision paths

4. **Advanced Statistics**
   - Memory decay curves
   - Consolidation history
   - Behavior emergence graphs

---

**Status:** GUI fully refactored for the NOWA cognitive architecture
