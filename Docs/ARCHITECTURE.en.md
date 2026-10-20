# Architecture of NOWA Cognitive

Russian version: [ARCHITECTURE.ru.md](ARCHITECTURE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## System overview

NOWA is a general-purpose cognitive core that:

- **Writes stable parameters only in sleep** (`Agent.sleep()` under `learning_guard.learning_allowed()`)
- **Writes a bounded labile layer while awake** (fast Q/Go/NoGo offsets that decay before consolidation)
- **Uses memory** (hippocampus & cortex) for behaviour with effective stable + labile values
- **Is regulated by affect** and by neuromodulators (fast state; slow affect statistics consolidate in sleep)
- **Selects actions** through the selector and basal-ganglia gate
- **Consolidates experience** in sleep (replay Q, capture channel tags, habit EMA, cortex, SHY)

See [docs/architecture/two-tier-plasticity.en.md](../docs/architecture/two-tier-plasticity.en.md) and [SLEEP.en.md](SLEEP.en.md).

---

## System Components

### 1. Multilevel Memory

```
┌─────────────────────────────────┐
│      Memory System              │
├─────────────────────────────────┤
│                                 │
│  Hippocampus (Episodic)        │
│  ├─ Stores recent experiences  │
│  ├─ Outcomes → labile tags      │
│  └─ Episodes until consolidated │
│                                 │
│  Cortex (Semantic)             │
│  ├─ Consolidated patterns       │
│  ├─ Abstract knowledge          │
│  └─ Modified only in sleep      │
│                                 │
└─────────────────────────────────┘
```

### 2. Neuromodulator System (Phase 2)

**Global regulators of behaviour:**

```
┌────────────────────────────────────────────┐
│   Neuromodulators (Phase 2 - NEW!)        │
├────────────────────────────────────────────┤
│                                            │
│  DOPAMINE (DA)                            │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Reward prediction error    │
│  ├─ Effects:                             │
│  │  └─ Learning rate ↑                   │
│  │  └─ Consolidation strength ↑          │
│  └─ Update: reward > 0 → DA += 0.25*R   │
│                                            │
│  SEROTONIN (HT)                           │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Stability & temporal depth │
│  ├─ Effects:                             │
│  │  └─ Temporal horizon ↑                │
│  │  └─ Habit formation ↑                 │
│  └─ Update: reward > 0, conflict==0      │
│            → HT += 0.05*reward           │
│                                            │
│  NOREPINEPHRINE (NE)                      │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Uncertainty & arousal      │
│  ├─ Effects:                             │
│  │  └─ Exploration level ↑               │
│  │  └─ Chain generation ↑                │
│  └─ Update: NE += 0.30*novelty           │
│            NE += 0.15*conflict           │
│                                            │
│  CORTISOL (CORT)                          │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.05  │
│  ├─ Function: Stress & threat response   │
│  ├─ Effects:                             │
│  │  └─ Forgetting rate ↑                 │
│  │  └─ Consolidation threshold ↑         │
│  └─ Update: reward < 0 → CORT += 0.2*|R|│
│            CORT += 0.25*conflict         │
│                                            │
│  Decay: Exponential toward baseline      │
│  Half-life: ~90 seconds                  │
│                                            │
└────────────────────────────────────────────┘
```

### 3. Affective system

```
┌──────────────────────────────┐
│   AffectiveState            │
├──────────────────────────────┤
│                              │
│ Valence [-1.0 to +1.0]      │
│ Arousal [0.0 to 2.0]        │
│ Threat [0.0 to 1.0]         │
│ Curiosity [0.0 to 1.0]      │
│ Entity associations (dict)   │
│                              │
│ Effects:                     │
│ └─ Modifies action pressure  │
│ └─ Influences habit strength │
│                              │
└──────────────────────────────┘
```

### 3.5. Affective Persistence (Phase 3.5)

```
┌──────────────────────────────┐
│  AffectivePersistenceLayer  │
├──────────────────────────────┤
│  Durable affective traces   │
│  ├─ anxiety / tension       │
│  ├─ satisfaction / interest │
│  ├─ slow decay              │
│  ├─ accumulation            │
│  └─ age tracking            │
│                              │
│ Reads: affect, neuromods,   │
│       temporal T1/T2        │
│                              │
│ ⚠️ Does NOT select actions  │
│ ⚠️ No direct selector input │
└──────────────────────────────┘
```

### 3.75. Affective Background Field (Phase 3.75)

```
┌──────────────────────────────┐
│  AffectiveBackgroundField    │
├──────────────────────────────┤
│  Inertial background field   │
│  from affective traces       │
│  + lifetime modulation       │
│  + wakefulness noise only    │
│                              │
│ Reads: traces + lifetime     │
│ Writes: background_*         │
│                              │
│ ⚠ No direct action input     │
│ ⚠ No neuromodulator control  │
└──────────────────────────────┘
```

### 4. Action-selection system

```
┌─────────────────────────────────────┐
│      Action Selection               │
├─────────────────────────────────────┤
│                                     │
│  Inputs:                            │
│  ├─ Hippocampal activations        │
│  ├─ Cortical patterns              │
│  ├─ Intent memory (habits)          │
│  ├─ Affective modifier              │
│  └─ Prediction layer (advisory)    │
│                                     │
│  Selector                           │
│  ├─ Confidence-based stochastic    │
│  ├─ NOT learnable                   │
│  └─ Deterministic at high conf.     │
│                                     │
│  Output: action_name                │
│                                     │
│  ⚠️ ONLY selector chooses actions  │
│  ⚠️ Nothing else can override      │
│                                     │
└─────────────────────────────────────┘
```

### 5. Habit system (Intent Memory)

```
┌──────────────────────────────┐
│    Intent Memory (Habits)    │
├──────────────────────────────┤
│                              │
│ context → action mapping     │
│ strength: how often used     │
│ affective valence: quality   │
│                              │
│ Waking: note_selection only  │
│   (strength-0 traces)        │
│ During sleep:                │
│ ├─ Outcome-gated EMA         │
│ ├─ Degrade unused (sleep)    │
│ └─ Slow affect replay        │
│                              │
└──────────────────────────────┘
```

### 6. Sleep and Consolidation

```
┌────────────────────────────────────┐
│   Sleep Manager                    │
├────────────────────────────────────┤
│                                    │
│ ONLY stable-tier writer            │
│                                    │
│ Two-tier pass (once per sleep):    │
│  1. Capture κ of labile Go/NoGo   │
│  2. Compensated η_eff channel step │
│  3. Habit EMA + visit transfer     │
│  4. Slow affect + external hooks   │
│                                    │
│ Then per cycle: replay stable Q,   │
│  cortex, SHY, chains, SAC, …     │
│                                    │
│ Waking: labile tags only           │
│                                    │
└────────────────────────────────────┘
```

### 7. Prediction Layer (Plan C)

```
┌─────────────────────────────────┐
│  Prediction Layer               │
├─────────────────────────────────┤
│                                 │
│ Role: ADVISORY only             │
│ ├─ Creates pressure, not choice │
│ ├─ Selector still decides       │
│ └─ Can be ignored               │
│                                 │
│ Updates:                        │
│ ├─ Positive prediction → ↑ P   │
│ ├─ Negative prediction → ↓ P   │
│ └─ Noisy predictions ignored    │
│                                 │
│ No feedback from selector       │
│                                 │
└─────────────────────────────────┘
```

---

## The Full Process in Operation

### Phase 1: Waking

```
1. Receive context events
                  ↓
2. Activate memories (hippocampus + cortex)
                  ↓
3. Get intent habits (from intent_memory)
                  ↓
4. Get affective state & neuromodulators
                  ↓
5. Compute action pressures
                  ↓
6. Selector chooses action (confidence-based)
                  ↓
7. Store experience (immutable in hippocampus)
                  ↓
8. Update affect & neuromodulators (state)
                  ↓
9. Known outcomes → labile Q/Go/NoGo only
   (host should pass dt for decay)
```

### Phase 2: Sleep

```
1. Get consolidation candidates
                  ↓
2. Cluster similar experiences
                  ↓
3. Abstract into patterns
                  ↓
4. Store in cortex (semantic memory)
                  ↓
5. Apply neuromodulator effects:
   ├─ DA: boost consolidation
   ├─ HT: stabilize
   ├─ NE: form chains
   └─ CORT: increase forgetting
                  ↓
6. Degrade unused habits
                  ↓
7. Stable tier updates (Q replay,
   capture, habits, cortex, …)
```

---

## Cycle of mutual influence among modules

```
Environment
    ↓
    │ reward, novelty, conflict signals
    ↓
AffectiveState ←→ Neuromodulators
    ↓              ↓
    │              │ modifies learning params
    │              ↓
    └────→ Selector (confidence-based)
              ↓
              Action
              ↓
          Experience (stored)
              ↓
           Sleep ← Stable learning + labile capture
              ↓
         Consolidation (modified by neuromodulators)
              ↓
        Cortex patterns updated
```

---

## Eight neuromodulator modifier methods

| Method | Effect | Range |
|-------|--------|----------|
| `get_learning_rate_modifier()` | Learning rate | 0.5 - 1.5 |
| `get_consolidation_strength()` | Strengthening of consolidation | 0.5 - 1.5 |
| `get_temporal_discount()` | Temporal horizon | 0.5 - 1.5 |
| `get_exploration_level()` | Exploratory behaviour | 0.0 - 1.0 |
| `get_temporal_chain_generation()` | Chain formation | 0.0 - 1.0 |
| `get_forgetting_rate()` | Rate of forgetting | 0.1 - 0.9 |
| `get_consolidation_threshold()` | Consolidation threshold | 0.1 - 0.9 |
| `get_affective_arousal_modifier()` | Modification of arousal | 0.5 - 1.5 |

---

## Hard constraints (anti-abuse)

**Not permitted:**
- Selecting an action on the basis of DA
- Writing `if DA > X then action`
- Storing preferences in the neuromodulators
- Changing the neuromodulators from outside (except through update_from_signals)

**Permitted:**
- Changing coefficients (modifier methods)
- Influencing the rate of forgetting
- Changing the weight of the prediction layer
- Reading state (snapshot)

---

## A typical evolution of the neuromodulators

```
Scenario: Agent meets success

Time 0:     DA=0.1, HT=0.1, NE=0.1, CORT=0.05 (baseline)
            ↓
Step 1:     reward=+0.8 (success!)
            ↓
Immediate:  DA: 0.1 → 0.30 (↑200%)
            HT: 0.1 → 0.14 (↑40%)
            
During Sleep:
            consolidation ↑ from DA
            habit strengthened from HT
            
At Rest:    DA → 0.1 (decay over ~90s)
            HT → 0.1 (slow decay)
```

---

## Biological rationale

| Modulator | Biological correlate | Function |
|-----------|----------------------|---------|
| Dopamine | Ventral tegmental area | Reward and motivation |
| Serotonin | Dorsal raphe nuclei | Mood and persistence |
| Norepinephrine | Locus coeruleus | Arousal and attention |
| Cortisol | HPA axis | Stress response |

---

## Key documents

- [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md) — a short overview of Phase 2
- [FINAL_REPORT_NEUROMODULATORS_PHASE2.md](FINAL_REPORT_NEUROMODULATORS_PHASE2.en.md) — the full report
- [LEARNING.md](LEARNING.en.md) — principles of learning
- [README_AFFECTIVE_SYSTEM.md](README_AFFECTIVE_SYSTEM.en.md) — the affective system

---

**Built on the specification of Phase 2 — Neuromodulator**

All requirements of the specification are observed
219/219 tests PASSED
Production-ready code
