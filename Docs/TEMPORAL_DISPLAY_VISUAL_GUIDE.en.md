# NOWA GUI — Visualization of Temporal Levels

Russian version: [TEMPORAL_DISPLAY_VISUAL_GUIDE.ru.md](TEMPORAL_DISPLAY_VISUAL_GUIDE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Visual Layout — Right Panel Structure

```
┌──────────────────────────────────────────────────────────┐
│  NOWA — Cognitive Agent with an Affective Architecture  │ ← Main window title
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: [User message box]  [Send] [Sleep] [Save]       │ ← Control panel
│                                                          │
├─────────────────────┬──────────────────────────────────┤
│                     │                                    │
│  Chat History       │  RIGHT PANEL (NEW TEMPORAL)      │
│  ─────────────────  │  ──────────────────────────────  │
│                     │                                    │
│  User: Hello        │  Affective state                 │ ← Existing
│                     │  ─────────────────────────────  │
│  NOWA: Hi!          │  Valence:      [████░░░░░]      │
│                     │  Activation:   [░███████░]      │
│  User: How are you? │  Threat:       [░░░░░░░░░]      │
│                     │  Curiosity:    [███████░░]      │
│  NOWA: I'm fine...  │  Readiness: high (84%)          │
│                     │                                    │
│  ...                │  Temporal levels                 │ ← NEW SECTION
│                     │  ─────────────────────────────  │
│                     │                                    │
│                     │  T0 (Instant):                   │
│                     │  val:0.15 arl:0.42 thr:0.00 cur:0.28
│                     │                                    │
│                     │  T1 (Trend):                     │
│                     │  val:+0.05 arl:+0.12 thr:-0.02 cur:+0.08
│                     │                                    │
│                     │  T2 (Baseline — slow drift):     │
│                     │  val:0.10 arl:0.35 thr:0.05 cur:0.20
│                     │                                    │
│                     │  T3 (Attractor — very slow):     │
│                     │  val:0.08 arl:0.32 thr:0.08 cur:0.18
│                     │                                    │
│                     │  T1 window: 7/10                 │
│                     │                                    │
│                     │  Statistics:                     │ ← Existing
│                     │  ─────────────────────────────  │
│                     │  Experiences: 42                  │
│                     │  Patterns: 8                      │
│                     │  Sleep cycles: 3                  │
│                     │  ...                              │
│                     │                                    │
└─────────────────────┴──────────────────────────────────┘
```

## Data Format Examples

### T0 — Current Instantaneous State
```
T0 (Instant):
val:+0.25 arl:+0.42 thr:+0.10 cur:+0.33

Interpretation:
- Positive valence (0.25): the agent is in a good mood
- High arousal (0.42): the agent is active and alert
- Low threat (0.10): not afraid
- Medium curiosity (0.33): somewhat interested
```

### T1 — Short-term Trend (10-item window)
```
T1 (Trend):
val:+0.08 arl:+0.15 thr:-0.03 cur:+0.12

Interpretation:
- The T1 mean is 0.08 higher than T0 (0.17 vs 0.25)
- Shows whether the agent is becoming happier (+) or sadder (-)
- The trend shows the direction of emotional movement
- The window fills from 0/10 to 10/10 as the agent steps
```

### T2 — Consolidated Mid-term Baseline
```
T2 (Baseline — slow drift):
val:+0.12 arl:+0.38 thr:+0.06 cur:+0.22

Interpretation:
- A stable reference state after consolidation
- Represents the "learned" baseline emotional state
- Slow drift during waking (micro-consolidation)
- Strengthened during sleep consolidation
- Usually less extreme than T0 (smoothed)
```

### T3 — Long-term Attractor
```
T3 (Attractor):
val:+0.10 arl:+0.35 thr:+0.07 cur:+0.20

Interpretation:
- A very stable "personality" of the agent
- Emerges after many sleep cycles
- Represents a long-term behavioural bias
- Rarely changes (very slow evolution)
```

## Real-time Behaviour Examples

### Example 1: Positive Feedback
```
Step 1: The user praises the agent
  T0: val:+0.15, arl:+0.30, cur:+0.25
  
Step 2: The agent processes the praise
  T0: val:+0.35 (happiness increased)
  T1 mean: +0.25 (the trend is positive)
  
Step 3: More positive interactions
  T0: val:+0.42 (peak happiness)
  T1 mean: +0.32 (the trend continues upward)
  T1 window: 8/10 (filling up)
```

### Example 2: Threat Detected
```
Step 1: A conflict is mentioned
  T0: threat:+0.05, arl:+0.35
  
Step 2: The agent interprets it as a threat
  T0: threat:+0.45 (fear triggered)
  T0: arl:+0.65 (arousal spiked)
  
Step 3: Resolution
  T0: threat:+0.15 (fear decreases)
  T0: arl:+0.40 (arousal normalizes)
  The T1 mean shows the whole trajectory
```

### Example 3: After Sleep Consolidation
```
Before sleep:
  T0: val:+0.30, arl:+0.50 (volatile)
  T1 mean: +0.25, +0.45 (erratic)
  T2: val:+0.15, arl:+0.35 (old baseline)
  T3: val:+0.10, arl:+0.30 (old attractor)

After sleep (2 cycles):
  T0: val:+0.25, arl:+0.42 (normalized)
  T1 mean: +0.22, +0.40 (smoothed)
  T2: val:+0.22, arl:+0.40 (updated)
  T3: val:+0.18, arl:+0.35 (shifted toward the positive)
  
Result: the agent learned to be slightly happier and more aroused
```

## Debugging with the Temporal Display

### Problem: the agent gets stuck in a negative state
```
Diagnosis with the temporal display:
T0:  val:-0.80 (very sad)
T1:  val:-0.75 (trend negative)
T2:  val:-0.60 (the baseline is sad)
T3:  val:-0.55 (the attractor is pulled toward sadness)

Solution: 
- Run positive interactions to shift T0 upward
- Sleep consolidation will gradually lift T2 and T3
- The agent's emotional personality can be reshaped
```

### Problem: erratic behaviour
```
Diagnosis:
T0:  varies: +0.8, -0.6, +0.4, -0.3 (jumping around)
T1:  mean: +0.05 (wildly different from T0)
T1 window: 4/10 (not enough history)

Solution:
- The agent has not yet accumulated enough experience
- Give it more interactions to fill the T1 window
- Let sleep consolidation stabilize the patterns
```

### Problem: learning is not working
```
Diagnosis:
T0: changes during waking (good)
T1: accumulating (good)
T2: does NOT update after sleep
T3: does NOT update after sleep

Solution:
- Check the consolidation cycles of sleep_manager
- Verify that temporal.sleep() is being called
- Ensure that sleep cycles are at least 2 for effective consolidation
```

## Colour Indicators

| Level | Colour | Meaning |
|-------|-------|---------|
| T0 | Blue | Current immediate state |
| T1 | Teal | Trend (what is happening) |
| T2 | Purple | Baseline (what should be) |
| T3 | Red | Attractor (what it prefers) |
| Panel | Light blue | Visual grouping |

## When Each Level Updates

| Level | Updated on | Frequency |
|-------|-----------|-----------|
| T0 | Agent.step() | Every interaction |
| T1 | Agent.step() | Every interaction (deque) |
| T2 | Agent.step() and Agent.sleep() | Waking drift and consolidation |
| T3 | Agent.sleep() | Only during deep consolidation |

## Window Indicator (T1)

```
T1 window: 0/10  → just started, 1 snapshot collected
T1 window: 5/10  → half-full window, 5 snapshots
T1 window: 10/10 → full window, 10 snapshots (maximum)
T1 window: 10/10 → after 10 or more, the oldest continues to be replaced
```

The T1 window keeps the 10 most recent affect snapshots. A full window (10/10) means the trend data are adequate.

---

**Implementation location**: `src/gui.py` lines 248-1318
**Total code added**: 90 lines
**Test status**: 167/167 passing
**User impact**: a visual account of the agent's emotional evolution over time
