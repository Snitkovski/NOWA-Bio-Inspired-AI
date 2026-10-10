# Temporal Levels: Interface Visualisation

Russian version: [TEMPORAL_GUI_VISUALIZATION.ru.md](TEMPORAL_GUI_VISUALIZATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Overview

A comprehensive visualisation of temporal levels was added to the NOWA interface in order to display the four-level temporal architecture (T0/T1/T2/T3) for debugging and for understanding the patterns of agent behaviour over time.

## Implementation

### 1. Addition of an Interface Panel (`src/gui.py`)

A new section, Temporal Levels, was added to the right panel:
- **Location**: after the affective-state display, before the statistics section
- **Lines**: 248–285

#### Display components

- **T0 (instant)**: the instantaneous current affect state
  - Displays: valence, arousal, threat, curiosity (current values)
  - Updates on every agent step

- **T1 (trend)**: the short-term trend (sliding window)
  - Displays: mean values over a window of 10 items, plus deltas from T0
  - Shows the direction of change (+/−) for each affect dimension
  - Window-fill indicator (0/10 to 10/10)

- **T2 (baseline)**: the consolidated medium-term baseline
  - Displays: a stable reference state with slow waking drift
  - Updated during waking (micro-consolidation) and during sleep consolidation cycles

- **T3 (attractor)**: long-term attractors (very slow evolution)
  - Displays: a very stable behavioural bias
  - Updated only during deep sleep cycles

### 2. Display Update Method (`src/gui.py`)

**Method**: `update_temporal_display()` (lines 430–471)

Features:

```python
def update_temporal_display(self):
    """Обновить визуализацию временных уровней (T0/T1/T2/T3)"""
    # Extract levels from agent.temporal.get_levels()
    # Format and display each level
    # Update window size indicator
```

Implementation details:
- Extracts levels from `agent.temporal.get_levels()`
- Formats T0 as current values: `val:0.00 arl:0.00 thr:0.00 cur:0.00`
- Formats T1 as deltas: `val:+0.00 arl:+0.00 thr:-0.00 cur:+0.00`
- Shows window fill status: `5/10`
- Handles a missing temporal structure without failure

### 3. Points of Update Integration

**Process input** (line 495): calls `update_temporal_display()` after each user interaction.  
**Sleep consolidation** (lines 1317–1318): calls `update_temporal_display()` after sleep cycles complete.

### 4. Colour Scheme

```text
T0 - Blue (#2980b9): Current immediate state
T1 - Teal (#16a085): Trend over window
T2 - Purple (#8e44ad): Consolidated baseline
T3 - Red (#c0392b): Long-term attractors
Panel - Light blue (#f0f8ff): Visual hierarchy
```

## Visual Structure

```text
+---------------------------------------------+
| Temporal levels                             |
+---------------------------------------------+
| T0 (instant):                               |
| val:0.00 arl:0.00 thr:0.00 cur:0.00        |
|                                             |
| T1 (trend):                                 |
| val:+0.00 arl:+0.00 thr:-0.00 cur:+0.00    |
|                                             |
| T2 (baseline - slow drift):                 |
| val:0.00 arl:0.00 thr:0.00 cur:0.00        |
|                                             |
| T3 (attractor):                             |
| val:0.00 arl:0.00 thr:0.00 cur:0.00        |
|                                             |
| T1 window: 5/10                             |
+---------------------------------------------+
```

## Data Flow

### During agent steps (waking)

```text
User Input → Agent.step() → temporal.log(snapshot) → T0 updated
                         → T1 accumulates (deque, max 10)
                         → T2 drifts when T1 window is full
                         → GUI.process_input() → update_temporal_display()
```

### During sleep consolidation

```text
Agent.sleep(cycles=N) → temporal.sleep() → consolidate T1→T2, T2→T3
                     → update affect aggregates
                     → GUI.update_temporal_display()
```

## Testing

### Verification tests

1. The agent has a `temporal` attribute (an instance of `TemporalLevels`)
2. T0 contains all affect dimensions (valence, arousal, threat, curiosity)
3. T1 accumulates a window of 10 items correctly
4. T2 drifts during waking and updates after sleep consolidation
5. T3 attractors track long-term patterns
6. The display handles missing data without failure
7. All 167 unit tests still pass (no regressions)

### Manual testing steps

1. Run the interface: `python src/gui.py`
2. Observe T0 change as you interact with the agent
3. Watch the T1 trend accumulate (0/10 → 10/10)
4. Submit feedback and see affect changes propagate
5. Activate consolidation in order to run sleep cycles
6. Observe T2 and T3 stabilise after consolidation

## Use in Debugging

### Understanding agent behaviour

- **T0 values**: what the agent is undergoing at this moment
- **T1 deltas**: whether the agent is becoming more anxious, content, or curious
- **T2 baseline**: the agent’s default emotional state after learning
- **T3 attractors**: the emotional pattern toward which the agent is drawn in the long term

### Debugging scenarios

1. **The agent is stuck in a negative state**: inspect the T3 attractors and whether they are biased negative
2. **Behaviour changes erratically**: inspect the T1 window; high volatility indicates instability
3. **Learning is not taking effect**: inspect T2 drift during waking and the T2/T3 update after sleep (consolidation cycles)
4. **An unexpected personality**: inspect T3; long-term attractors reflect the learned personality

## Files Modified

- `src/gui.py`: temporal display added (48 new lines) plus the update method (42 lines)
- `test_temporal_gui.py`: a standalone script for the temporal display

## Integration with the Existing System

There are no breaking changes. The addition is backward compatible:
- the existing affect display still works
- the statistics panel is unchanged
- the memory display is unchanged
- all 167 tests pass without modification
- if the temporal system is missing, the display degrades safely (`try/except`)

## Possible Later Extensions

Possible visual improvements:
1. Small graphs of T1 trends over time
2. A heat map of T3 attractor patterns
3. A consolidation progress bar during sleep
4. A historical timeline of temporal state
5. A comparison of the T0/T1 deviation with action selection
