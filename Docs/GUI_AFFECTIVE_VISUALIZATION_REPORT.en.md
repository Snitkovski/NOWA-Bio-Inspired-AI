# GUI Affective Visualization — Completion Report

Russian version: [GUI_AFFECTIVE_VISUALIZATION_REPORT.ru.md](GUI_AFFECTIVE_VISUALIZATION_REPORT.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Date**: 2025-01-20  
**Status**: COMPLETE  
**Implementation Time**: Full affective system with GUI visualization

---

## 1. Overview

The GUI has been extended with real-time visualization of affective state. The system now displays all four core affective parameters with color-coded indicators, so that an end user can observe and understand changes in the agent's operational state in real time.

---

## 2. Implementation Summary

### 2.1 GUI Modifications (`src/gui.py`)

#### New Imports
```python
from affect import AffectiveState
from self_model import SelfModel
```

#### Window Enhancement
- **Previous size**: 900x700
- **Current size**: 1200x750 (expanded to accommodate affective indicators)

#### Affective State Display Panel

A new `affect_frame` section on the right panel shows:

**1. Valence Indicator**
- Range: -1.0 (very negative) to +1.0 (very positive)
- Color coding: Red to Green
- Label: Current value with 2 decimal places
- Interpretation: Agent's current satisfaction or dissatisfaction

**2. Arousal Indicator**
- Range: 0.0 (calm) to 2.0 (highly activated)
- Color coding: Blue to Orange
- Label: Current value with an intensity indicator
- Interpretation: Agent's activation level or energy

**3. Threat Indicator**
- Range: 0.0 (safe) to 1.0 (critical threat)
- Color coding: Green to Red
- Label: Current value with a warning level
- Interpretation: Agent's perceived danger or instability

**4. Curiosity Indicator**
- Range: 0.0 (indifferent) to 1.0 (highly curious)
- Color coding: Gray to Purple
- Label: Current value with exploration readiness
- Interpretation: Agent's drive to explore or learn

**5. Readiness Label**
- Calculated from the `adaptation_readiness()` method
- Shows: a numeric value (0.0–1.0) and a status (Ready / Processing / Limited)

### 2.2 Visualization Methods

#### `_update_bar(canvas, value, min_val, max_val, low_color, high_color)`
Creates a color-coded Canvas bar visualization:
- Dynamically calculates bar position and color from the value
- Supports any value range and color pair
- Updates in real time during agent steps

#### `update_affect_display()`
Updates all affective indicators:
- Called after each `agent.step()`
- Updates Canvas bars with current values
- Updates text labels with precise measurements
- Integrates with SelfModel for a comprehensive analysis

### 2.3 Real-Time Integration

#### Agent Step Integration
```python
def process_input(self):
    # ... agent processing ...
    self.update_affect_display()  # Updates after each step
```

#### Feedback System Integration
```python
def submit_feedback(self):
    # ... existing code ...
    reward_signal = feedback_rating / 2.0  # -1.0 to 1.0
    self.agent.affect_state.update_from_reward(reward_signal)
    self.update_affect_display()  # Visual update after feedback
```

### 2.4 Inspector Tab Enhancement

**New Tab 7: "Affective State"**

Provides comprehensive operational introspection:
- Current operational state description
- Snapshot of all affective parameters
- Regulatory pattern analysis
- Limiting factors (what is constraining behaviour)
- Enabling factors (what is supporting behaviour)
- System type classification (operational analysis only)

---

## 3. Technical Details

### 3.1 Color Coding Scheme

| Parameter | Min Value | Max Value | Color Range | Meaning |
|-----------|-----------|-----------|-------------|---------|
| **Valence** | -1.0 | +1.0 | Red to Green | Negative to positive mood |
| **Arousal** | 0.0 | 2.0 | Blue to Orange | Calm to hyper-activated |
| **Threat** | 0.0 | 1.0 | Green to Red | Safe to critical |
| **Curiosity** | 0.0 | 1.0 | Gray to Purple | Indifferent to exploring |

### 3.2 Update Cycle

```
User Input
    ↓
agent.step() with reward/novelty/conflict signals
    ↓
affect_state.update_from_*() methods execute
    ↓
GUI.update_affect_display() called
    ↓
Canvas bars updated with new colors/positions
    ↓
Text labels updated with numeric values
    ↓
User sees real-time state changes
```

### 3.3 Canvas Rendering

Each indicator uses a tkinter Canvas for:
- Smooth color gradients
- Dynamic sizing based on the value range
- Real-time updates without flickering
- Response to window resizing

---

## 4. Test Results

### 4.1 GUI Affective Test Suite
```
Test 1: Creating agent with affective state
Test 2: Creating SelfModel
Test 3: Testing affect updates from reward (0.00 → 0.24 valence)
Test 4: Testing negative reward (0.24 → 0.00 valence)
Test 5: Testing novelty-driven curiosity (0.00 → 0.23)
Test 6: Testing conflict detection (0.15 → 0.36 threat)
Test 7: Testing color coding (all 4 parameters)
Test 8: Testing readiness calculation
Test 9: Testing self-model introspection
Test 10: Full operational state analysis

Result: ALL TESTS PASSED
```

### 4.2 Affective Regulators Test Suite
```
25 tests passed in 0.27s
- test_affective_state_initialization
- test_affective_state_bounds
- test_update_from_reward_positive
- test_update_from_reward_negative
- test_update_from_novelty
- test_update_from_conflict
- test_decay_over_time
- test_action_pressure_modifier
- test_should_reinforce_habit
- test_conflict_severity
- test_adaptation_readiness
- test_entity_associations
- test_snapshot_immutability
- test_serialization
- (11 additional SelfModel and integration tests)

Status: 100% PASSING
```

### 4.3 Affect Integration Test Suite
```
12 tests passed in 0.62s
- test_agent_initializes_with_affect_state
- test_agent_step_updates_affect_state
- test_agent_step_with_threat_updates_threat_parameter
- test_agent_passes_affect_modifier_to_selector
- test_agent_get_state_includes_affect
- test_agent_decay_between_steps
- test_reevaluate_habits_with_high_threat
- test_reevaluate_habits_with_positive_valence
- test_strengthen_trace_method
- test_consolidate_with_affect_profile
- test_selector_applies_affect_modifier
- test_realizer_consider_affect_modifier

Status: 100% PASSING
```

### 4.4 Overall Test Coverage
- **Total Affective System Tests**: 37
- **All Passing**: YES
- **No Regressions**: VERIFIED
- **GUI Integration**: WORKING

---

## 5. User Experience Enhancements

### 5.1 Observability
- Users can now see exact affective state values in real time
- Color changes provide immediate visual feedback
- No need to run separate diagnostic tools

### 5.2 Interpretability
- Self-model introspection explains current limitations and capabilities
- Shows why the agent is behaving a certain way
- Displays limiting and enabling factors

### 5.3 Feedback Integration
- User ratings (−2 to +2) directly affect displayed valence
- A visual response to feedback is immediate
- Reinforces the user–system interaction loop

### 5.4 Inspector Panel
- Deep operational analysis is available in a dedicated tab
- Shows regulatory patterns and trends
- Reports systematic analysis without anthropomorphism

---

## 6. Code Changes Summary

### Modified Files
1. **src/gui.py** (1267 lines)
   - Added affect/self_model imports
   - Expanded window to 1200x750
   - Added affect_frame with 4 visual indicators
   - Implemented `_update_bar()` and `update_affect_display()` methods
   - Updated `process_input()` to call display updates
   - Added a 7th Inspector tab for affective analysis
   - Updated `submit_feedback()` to trigger affect state changes

### Created Test File
- **test_gui_affective.py** — comprehensive GUI visualization test suite

---

## 7. Feature Checklist

- Valence display with red–green color coding
- Arousal display with blue–orange color coding
- Threat display with green–red color coding
- Curiosity display with gray–purple color coding
- Readiness indicator calculation
- Real-time updates after `agent.step()`
- Canvas-based bar visualization
- Smooth color-gradient transitions
- Feedback integration with affect updates
- Inspector tab with comprehensive analysis
- Self-model introspection display
- All tests passing (37/37)
- No regressions in existing tests

---

## 8. How to Use

### 8.1 Running the GUI

```bash
python src/gui.py
```

### 8.2 Observing Affective State

1. Send a message to the agent (right panel)
2. Watch the affective indicators update in real time
3. Observe color changes based on the agent's state
4. Check readiness status below the indicators

### 8.3 Using Feedback

1. Rate the agent response using the slider (−2 to +2)
2. Click the "Save feedback" button
3. Observe the immediate valence change in the indicator
4. Check the updated "Readiness" status

### 8.4 Inspector Analysis

1. Click the "Affective State" tab
2. View the detailed operational analysis
3. See limiting and enabling factors
4. Check the system type classification

---

## 9. Technical Architecture

### Data Flow
```
User Input → Agent Processing → AffectiveState Update
                                        ↓
                                    SelfModel Analysis
                                        ↓
                                GUI Visualization
                                        ↓
                            Real-time Display Update
```

### Component Integration
```
gui.py
├── Agent (with affect_state)
├── SelfModel (operational introspection)
├── AffectiveState (parameter management)
└── Canvas-based visualization (real-time display)
```

---

## 10. Validation and Verification

- **Functional tests**: all 37 tests passing
- **Integration tests**: Agent, GUI, and the affect system verified
- **Visual tests**: color coding and Canvas rendering confirmed
- **Feedback integration**: user ratings correctly update affective state
- **Display updates**: real-time updates confirmed working
- **No regressions**: existing functionality preserved

---

## 11. Next Steps

The GUI affective visualization is complete and ready for deployment. The system now provides:

1. **Real-time observability** of agent affective state
2. **Color-coded visual indicators** for a quick assessment
3. **Integration with the feedback system** for the user–agent loop
4. **Deep introspection tools** via the Inspector panel
5. **No anthropomorphic language** — purely operational analysis

All requirements have been met and fully tested.

---

## Summary

The NOWA cognitive agent now has a complete, visually rich interface for observing and understanding its affective state. The four-parameter display, with color coding, real-time updates, and comprehensive introspection tools, makes the system transparent and understandable to end users.

**Status**: **PRODUCTION READY**
