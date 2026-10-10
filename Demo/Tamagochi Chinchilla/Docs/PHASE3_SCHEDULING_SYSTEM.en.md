# Phase 3: Scheduling System - Autonomous Affect Cycles - Implementation Complete

Russian version: [PHASE3_SCHEDULING_SYSTEM.ru.md](PHASE3_SCHEDULING_SYSTEM.ru.md)

## Abstract

Scientific account of the platform: [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md).

The document is a report on the local scheduling system of the demonstration organism, constituting the third phase of the work. It describes an autonomous-cycle class and a controlling class that maintain three needs—hunger, tiredness, and boredom—with separate rates of increase and satiation, thresholds of critical and satisfied states, and an acceleration of tiredness during activity. A circadian rhythm with a period of about twenty minutes of simulation time is attached to the cycles. Drive suggestions are combined with weights accumulated by the memory subsystem and take part in behavioural-chain selection when the combined weight exceeds the threshold of 0.8 stated in the report.

The report records the embedding in the agent step: updating cycles from active chains, transferring increments into affective state, and including cycle status, drives, and circadian phase in the state snapshot. As behavioural consequences it describes competition among needs and regularities derived from hunger, activity, and boredom. Tunable cycle parameters are given, together with the list of files created for the local scheduler and the accompanying checks.

In the results section the report states that sixteen scheduler checks, six integration checks, five checks of basic functionality, and ten memory checks passed, summing these as thirty-seven out of thirty-seven. These figures are given as statements of the report itself. The circuit described is the local SchedulingSystem; the demonstration entry point imports it together with the modules of the cognitive core.

---

## Overview

Phase 3 implementation adds autonomous affect cycles that drive behavior selection. The system creates realistic needs that build over time and influence the chinchilla's decision-making, creating emergent behavioral patterns.

## Architecture

### Core Components

#### 1. **AffectCycle** (Dataclass)

Represents individual autonomous cycles (hunger, tiredness, boredom):

- **Natural Increase**: Cycles build up over time when unsatisfied
- **Satiation Decay**: Rapid decay when needs are being met
- **Thresholds**: Critical vs satisfied states
- **Activity Boost**: Some cycles (tiredness) increase faster during activity

#### 2. **SchedulingSystem** (Main Class)

Manages all autonomous cycles:

- **Cycle Updates**: Applies changes based on active chains and time
- **Drive Suggestions**: Provides urgency scores for chain selection
- **Circadian Rhythm**: Time-of-day activity patterns
- **Affect Integration**: Modifies affect state with cycle changes

### Cycle Parameters (Realistic 20-minute periods)

| Cycle | Increase Rate | Decay Rate | Critical | Satisfied | Notes |
|-------|---------------|------------|----------|-----------|-------|
| Hunger | 0.0008/sec | 0.08/sec | 0.75 | 0.2 | Food-seeking behavior |
| Tiredness | 0.0006/sec | 0.1/sec | 0.7 | 0.15 | Sleep/rest behavior |
| Boredom | 0.0012/sec | 0.06/sec | 0.8 | 0.25 | Play/exploration behavior |

**Time to Critical**: ~15-20 minutes per cycle at realistic rates

### Drive-Based Chain Selection

The system provides weighted suggestions for chain selection:

```python
drives = scheduler.get_drive_suggestions()
# Returns: {'eating': 0.4, 'bedtime_routine': 0.1, 'play': 0.6, ...}
```

**Combined Weight Formula:**

```
combined_weight = 1.0 + (learned_weight - 1.0) * 0.5 + drive_weight * 0.3
```

Where:

- **Base Weight**: 1.0 (neutral)
- **Learned Weight**: Memory-based preferences (±0.5)
- **Drive Weight**: Cycle urgency (0-0.8)

Chains are only selected if `combined_weight > 0.8`.

## Integration Points

### 1. ChinchillaAgent Step Method

**Cycle Updates:**

```python
# Update scheduling system
active_chains = {"eating": 1} if eating else {}
cycle_changes = self.scheduler.update(dt, active_chains)

# Apply to affect state
for affect_key, change in cycle_changes.items():
    self.affect.state[affect_key] = max(-1.0, min(1.0, 
        self.affect.state.get(affect_key, 0) + change))
```

**Chain Selection:**

```python
# Get drive suggestions
drive_suggestions = self.scheduler.get_drive_suggestions()

# Apply combined weights
chain_weights = self.memory.get_chain_weights([chain])
drive_weight = drive_suggestions.get(chain, 0.0)
combined_weight = 1.0 + (chain_weights.get(chain, 1.0) - 1.0) * 0.5 + drive_weight * 0.3

if combined_weight > 0.8:
    # Select this chain
```

### 2. State Tracking

**Enhanced State Snapshot:**

```python
snapshot = {
    "cycles": self.scheduler.get_cycle_status(),
    "drives": self.scheduler.get_drive_suggestions(), 
    "circadian": self.scheduler.get_circadian_state(),
    # ... existing fields
}
```

**Enhanced Status Display:**

```
Tick: 1500 | Time: 1500.0s
Chains Completed: 23
Affect: {'valence': 0.2, 'arousal': 0.4, ...}
Hunger: 0.45 | Tiredness: 0.32 | Boredom: 0.67
Circadian: Phase 0.42 | Activity: 0.91
```

## Behavioral Emergence

### Hunger Cycle

- **Buildup**: Natural increase during inactivity
- **Critical**: >0.75 triggers urgent food-seeking
- **Satiation**: Eating chain reduces hunger rapidly
- **Effect**: Chinchilla becomes more motivated to eat as hunger increases

### Tiredness Cycle

- **Buildup**: Increases during activity (grooming, play)
- **Critical**: >0.7 triggers sleep-seeking
- **Satiation**: Bedtime routine reduces tiredness rapidly
- **Effect**: Active play makes chinchilla tire out naturally

### Boredom Cycle

- **Buildup**: Fastest increase, drives exploration
- **Critical**: >0.8 triggers urgent play-seeking
- **Satiation**: Play/exploration chains reduce boredom
- **Effect**: Chinchilla seeks stimulation when bored

### Circadian Rhythm

- **20-minute day/night cycle** in simulation time
- **Activity Level**: sin(phase × π) creates natural activity patterns
- **Night Effect**: Slight tiredness increase during "night"
- **Day Effect**: Higher activity during "day"

## Test Coverage

**Scheduling System Tests (16/16 passing):**

1. Cycle initialization and parameters
2. Natural increase over time
3. Satiation decay when needs met
4. Satisfaction/critical thresholds
5. System initialization
6. Cycle updates with active chains
7. Eating satiation (hunger reduction)
8. Sleep satiation (tiredness reduction)
9. Play satiation (boredom reduction)
10. Drive suggestions calculation
11. Circadian rhythm phases
12. Cycle status reporting
13. Value clamping (0-1 bounds)
14. Activity boost to tiredness
15. Cycle reset functionality
16. Complete cycle: buildup → critical → satiation

**Integration Tests (6/6 passing):**

1. Scheduling system integration in ChinchillaAgent
2. Cycle changes affect the affect system
3. Drive suggestions influence chain selection
4. State snapshots include cycle information
5. Memory and scheduling systems work together
6. Full system integration with all components

**Core Tests (5/5 passing):** All existing functionality preserved

## Emergent Behaviors

The system creates realistic behavioral patterns:

1. **Hunger-Driven Eating**: Chinchilla naturally seeks food as hunger builds
2. **Activity-Induced Tiredness**: Play and exploration lead to natural fatigue
3. **Boredom-Driven Play**: Chinchilla seeks stimulation when inactive
4. **Circadian Patterns**: Activity levels follow day/night cycles
5. **Learned Preferences**: Memory system biases toward successful behaviors
6. **Need Competition**: Multiple drives compete for behavioral selection

## Performance Characteristics

- **Update Frequency**: Every simulation step (~20Hz)
- **Memory Usage**: Minimal (3 cycle objects)
- **Calculation Cost**: O(1) per update
- **Integration Cost**: O(1) affect state modifications
- **Persistence**: No additional files (cycles reset on startup)

## Configuration

Cycles can be tuned via parameters:

```python
hunger_cycle = AffectCycle(
    cycle_type=CycleType.HUNGER,
    increase_rate=0.0008,  # Adjust for faster/slower hunger
    decay_rate=0.08,       # Adjust for faster/slower satiation
    critical_threshold=0.75,
    satisfaction_threshold=0.2,
)
```

## Files Created

1. **src/scheduling_system.py** (280+ lines)
   - AffectCycle and SchedulingSystem classes
   - Cycle management and drive calculation
   - Circadian rhythm implementation

2. **tests/test_scheduling_system.py** (400+ lines)
   - 16 comprehensive tests for cycle behavior
   - Edge cases and realistic scenarios

3. **tests/test_scheduling_integration.py** (150+ lines)
   - 6 integration tests with ChinchillaAgent
   - Full system verification

## Integration with Existing Systems

- **AffectSystem**: Receives cycle-driven affect changes
- **MemorySystem**: Provides learned preferences for chain selection
- **BehavioralChains**: Selected based on combined learned + drive weights
- **AudioSystem**: Unaffected (runs independently)

## Future Enhancements

1. **Dynamic Rates**: Cycle rates could change based on age/health
2. **Chain Dependencies**: Some chains might affect multiple cycles
3. **Social Cycles**: Loneliness cycle for social interaction
4. **Environmental Effects**: Weather/time-of-year influences
5. **Health Integration**: Illness affects cycle rates
6. **Learning Effects**: Successful chains could modify cycle parameters

## Testing Results

**All Tests Passing:**

- Scheduling System: 16/16
- Integration Tests: 6/6
- Core System: 5/5
- Memory System: 10/10
- Total: 37/37 tests passing

**System Status:**

- Autonomous cycles drive realistic behavior
- Memory system learns from outcomes
- Audio system provides feedback
- Full integration working correctly

---

**Status:** Phase 3 Complete - Autonomous scheduling system fully integrated
**Tests:** 37/37 passing
**Features:** Hunger, tiredness, boredom cycles with circadian rhythm
**Integration:** All systems working together for emergent behavior
