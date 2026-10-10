# GUI Temporal Visualization — Implementation Summary

Russian version: [TEMPORAL_GUI_IMPLEMENTATION.ru.md](TEMPORAL_GUI_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Objective Completed
Added comprehensive temporal levels visualization to the NOWA GUI to display the four-tier temporal architecture (T0/T1/T2/T3) for debugging and studying agent behavior patterns over time.

## What Was Added

### 1. New GUI Panel — Temporal Levels
The panel title in the interface is `Временные уровни`.
**Location**: Right panel, after affective state display
**Size**: 7 display lines + window indicator

**Components**:
- **T0 (Instant)** — Instantaneous state
  - Current affect values: valence, arousal, threat, curiosity
  - Updates every agent step
  
- **T1 (Trend)** — Short-term trend (10-item window)
  - Shows deltas from T0 with +/- indicators
  - Reveals temporal direction of affect changes
  - Window fill indicator (x/10)
  
- **T2 (Baseline)** — Consolidated mid-term reference
  - Slow drift during waking (micro-consolidation)
  - Stabilized during sleep consolidation
  - Reference for measuring drift
  
- **T3 (Attractor)** — Long-term behavior attractors
  - Very slow evolution
  - Represents learned emotional personality bias

### 2. Update Method — `update_temporal_display()`
**Location**: src/gui.py, lines 430-471
**Integration**: Called from:
- `process_input()` after each user interaction (line 495)
- Sleep consolidation callback (lines 1317-1318)

**Features**:
- Extracts data from `agent.temporal.get_levels()`
- Formats T0 as absolute values
- Formats T1 as relative deltas
- Displays window fill status
- Graceful error handling

### 3. Visual Integration
- Color-coded for easy visual tracking:
  - T0 (Blue): Current state
  - T1 (Teal): Short-term trend
  - T2 (Purple): Consolidated baseline
  - T3 (Red): Long-term attractors
- Light blue background (#f0f8ff) for visual separation

## Code Changes

### File: src/gui.py
**Total additions**: 90 lines

1. **UI Initialization** (lines 248-285)
   - New temporal_frame with 4 display sections
   - Label widgets for T0/T1/T2/T3
   - Window indicator

2. **Update Method** (lines 430-471)
   - Extract temporal levels
   - Format for display
   - Error handling

3. **Integration Points**
   - process_input(): Add update_temporal_display() call (line 495)
   - Sleep callback: Add update_temporal_display() call (lines 1317-1318)

### Testing
- Syntax validation: no errors in gui.py
- Import verification: NOWAGUI imports successfully
- Method existence: `update_temporal_display()` present
- Unit tests: all 167 tests passing
- Standalone test: `test_temporal_gui.py` verification passing
- No regressions: the same 167 tests all green

## How It Works

### Waking Phase (Agent.step())
```
Agent.step(context)
  → temporal.log(snapshot)        # T0 created
  → temporal.t1.append(snapshot)  # T1 window updated (micro-consolidation when full)
  → GUI.process_input()
    → update_temporal_display()   # Display updated
```

### Sleep Phase (Agent.sleep())
```
Agent.sleep(cycles=N)
  → temporal.sleep()              # T1→T2, T2→T3 consolidation
  → sleep_manager updates affect_state from temporal
  → GUI displays update
    → update_temporal_display()   # T2/T3 now visible
```

## Usage and Benefits

### For Debugging:
1. **Stuck behaviors**: Check T3 — are attractors biased?
2. **Volatility**: Check T1 deltas — high variance means instability
3. **Learning**: Check T2 drift during waking and T2/T3 update after sleep
4. **Personality**: T3 attractors show learned emotional profile

### For Research:
1. **Real-time observation** of affect state evolution
2. **Temporal patterns** visible at multiple scales (T0/T1/T2/T3)
3. **Consolidation effects** visible immediately after sleep
4. **Behavior attribution** — understand why the agent acts a certain way

## Testing Results

```
============================= test session starts =============================
Platform: win32 -- Python 3.13.1, pytest-9.0.2

Test Summary:
  ✅ All 167 tests passing
  ✅ No regressions from GUI changes
  ✅ Temporal integration tests passing
  ✅ GUI imports working
  ✅ update_temporal_display() callable
  ✅ Standalone temporal display test passing

Time: 0.92 seconds
```

The session reports that all 167 tests pass, that the interface changes introduce no regressions, that the temporal integration tests pass, that the interface imports, that `update_temporal_display()` is callable, and that the standalone temporal display test passes. Elapsed time is 0.92 seconds.

## Documentation

New file: `Docs/TEMPORAL_GUI_VISUALIZATION.md`
- Complete implementation details
- Visual structure diagrams
- Data flow documentation
- Debugging guide
- Testing verification
- Future enhancement ideas

## Integration Status

**Fully integrated**:
- GUI panel added and styled
- Update method implemented
- Update hooks in place
- All tests passing
- No breaking changes
- Backward compatible
- Error handling in place
- Ready for production use

## Next Steps (Optional Enhancements)

1. **Temporal Graphs**: Mini line charts showing T1 trends over last N snapshots
2. **Heatmap**: Color intensity showing T3 attractor strength
3. **Consolidation Progress**: Visual indication of sleep cycle progress
4. **Timeline View**: Historical temporal state evolution
5. **Deviation Indicator**: T0 versus T1 deviation impacting action selection

## Files Summary

| File | Change | Lines |
|------|--------|-------|
| src/gui.py | Added UI panel + method + hooks | +90 |
| Docs/TEMPORAL_GUI_VISUALIZATION.md | New documentation | +147 |
| test_temporal_gui.py | Standalone verification test | +92 |

**Total**: 3 files, 329 lines added, 0 files modified beyond additions

## Verification Commands

```bash
# Verify imports
python -c "import sys; sys.path.insert(0, 'src'); from gui import NOWAGUI; print('✅ OK')"

# Verify method exists
python -c "import sys; sys.path.insert(0, 'src'); from gui import NOWAGUI; print(hasattr(NOWAGUI, 'update_temporal_display'))"

# Run all tests
pytest tests/ -q

# Run standalone temporal test
python test_temporal_gui.py
```

## User Experience

When using the GUI:
1. A new temporal-levels panel appears; its interface title is `Временные уровни`
2. T0 values change with each step
3. The T1 window fills from 0/10 to 10/10
4. T2 drifts during waking and stabilizes after sleep
5. T3 attractors emerge after multiple sleep cycles
6. This shows the agent's emotional state at different temporal scales

This visualization helps understand how the agent's affective state evolves and consolidates over time — essentially seeing the agent's life in the time dimension.

---
**Status**: complete and tested
**Date**: January 31, 2025
**Tests**: 167/167 passing
