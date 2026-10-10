## Abstract

Russian version: [NOWA_INTEGRATION_SPEC.ru.md](NOWA_INTEGRATION_SPEC.ru.md)

Scientific account of the platform: [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md).

The document sets out a normative protocol for integrating the demonstration organism, the chinchilla, with the cognitive core of the repository. The protocol prescribes replacement of local subsystems by canonical components: the four-dimensional affect adapter by an eight-dimensional affective space; the local scheduler of three need cycles by the drive system together with the energy system; heuristic selection of behavioural chains by a competing basal-ganglia circuit with thalamic selection; and consolidation of local memory by the sleep manager, the hippocampus, and cortical memory. Separate tasks introduce neuromodulatory state, wakefulness state, an emotional-regulation layer, and a conflict-arbitration layer.

The ten tasks form a sequence of interface replacements. For each task the protocol records the local entry point to be removed or retained, the initialisation of the core module, the mapping from drives to behavioural chains, and the call site within the simulation step. Learning in basal-ganglia channels and cortical consolidation are assigned to the sleep phase. Wakefulness is linked to a preference for bedtime chains and to an estimate of cognitive reliability passed to the visualisation layer. The closing tasks specify a debug display of the core layers and serialisation of core state across sessions.

The protocol fixes the target composition of the replacement and the order of the work. The demonstration entry point simultaneously imports core modules, including affective space, basal ganglia, hippocampus, sleep, neuromodulators, and wakefulness, and the local classes SchedulingSystem and MemorySystem. Attachment of individual modules and completion of the replacement programme are distinct statuses.

---

# NOWA-Powered Chinchilla — Integration Specification

Aim: replace every custom subsystem of the tamagotchi with genuine NOWA components.
After implementation, the demonstration must make the operation of each NOWA layer visible.

---

## Map of replacements

| What exists now | NOWA component | File |
|---|---|---|
| `AffectAdapter` (four-dimensional stub) | `AffectiveSpace` (8D) + `AffectiveState` | `affective_space.py` |
| `SchedulingSystem` (3 cycles) | `DriveSystem` from `autonomous_organism.py` | `autonomous_organism.py` |
| `_build_candidate_chains()` | `BasalGangliaGate` + `ThalamicGate` | `basal_ganglia.py` |
| No analogue | `NeuromodulatorState` | `neuromodulators.py` |
| No analogue | `WakefulnessState` | `wakefulness.py` |
| `memory.consolidate_memory()` | `SleepManager` + `CortexMemory` | `sleep.py` |
| No analogue | `EmotionalRegulationLayer` | `emotional_regulation.py` |
| No analogue | `ConflictArbitrationLayer` | `conflict_arbitration.py` |

---

## Task 1 — Replace SchedulingSystem with DriveSystem

**Remove:** `scheduling_system.py` and every import of `SchedulingSystem` from `main.py`  
**File:** `main.py`, class `ChinchillaAgent.__init__()`

### Initialisation

```python
from autonomous_organism import DriveSystem, DriveRule, default_drive_rules, EnergySystem

# In __init__():
self.drives = DriveSystem(
    rules={
        # Override the default rules for chinchilla biology
        "energy_need": DriveRule(
            accumulation_rate=0.006,   # hunger rises more slowly than in a human
            discharge_rate=0.001,
            decay_rate=0.001,
            affect_weights={"stress": 0.010, "arousal": 0.004},
        ),
        "exploration": DriveRule(
            accumulation_rate=0.011,
            discharge_rate=0.0012,
            decay_rate=0.0012,
            affect_weights={"curiosity": 0.020, "dominance": 0.008, "stress": -0.005},
        ),
        "social_drive": DriveRule(
            accumulation_rate=0.008,
            discharge_rate=0.0015,
            decay_rate=0.0010,
            affect_weights={"trust": 0.020, "attachment": 0.014, "stress": -0.010},
        ),
        "curiosity": DriveRule(
            accumulation_rate=0.018,
            discharge_rate=0.001,
            decay_rate=0.001,
            affect_weights={"curiosity": 0.025, "stress": -0.005, "stability": 0.004},
        ),
        "goal_tension": DriveRule(
            accumulation_rate=0.010,
            discharge_rate=0.0010,
            decay_rate=0.0015,
            affect_weights={"dominance": 0.018, "stability": 0.006, "stress": 0.008},
        ),
    }
)
self.energy = EnergySystem()
```

### Mapping DriveSystem to BEHAVIORAL_CHAINS

Replace `DRIVE_TO_CHAINS` in `_build_candidate_chains()`:

```python
DRIVE_TO_CHAINS = {
    "energy_need":   ["eating_and_grooming", "morning_awakening", "bedtime_routine"],
    "exploration":   ["exploration", "territorial_patrol", "nesting"],
    "social_drive":  ["social_contact"],
    "curiosity":     ["activity_burst", "hyperactivity", "exploration"],
    "goal_tension":  ["territorial_patrol", "nesting", "full_grooming"],
}
```

### Call to DriveSystem.update() in sim_step()

Replace the block `cycle_changes = self.scheduler.update(...)`:

```python
# Update DriveSystem — it accepts an 8D affect snapshot
affect_snapshot = self.affect_space.legacy_axes_snapshot()
discharge_overrides = {}

# Discharge a drive if the chinchilla is actively in a chain
current_chain = self.chain_executor.current_chain
if current_chain in ("eating_and_grooming", "morning_awakening", "bedtime_routine"):
    discharge_overrides["energy_need"] = 0.08   # rapid reduction of hunger
if current_chain in ("exploration", "territorial_patrol", "nesting"):
    discharge_overrides["exploration"] = 0.06
if current_chain == "social_contact":
    discharge_overrides["social_drive"] = 0.07
if current_chain in ("activity_burst", "hyperactivity"):
    discharge_overrides["curiosity"] = 0.05

drive_snapshot = self.drives.update(
    dt=dt,
    affect_snapshot={"axes": affect_snapshot},
    discharge_overrides=discharge_overrides,
    energy_level=self.energy.snapshot()["level"],
)

# Update EnergySystem
physiology_mode = "low_energy" if drive_snapshot.get("energy_need", 0) > 0.7 else "passive"
self.energy.update(dt=dt, cognitive_load=0.3, rest_time=0.0)
```

### get_drive_suggestions() — adapter

`_build_candidate_chains()` accepts `drive_suggestions: Dict[str, float]`.
Pass `drive_snapshot` directly: DriveSystem already returns `{drive_name: value}`.

---

## Task 2 — Replace AffectAdapter with AffectiveSpace

**Remove:** the class `AffectAdapter` from `main.py`  
**Add:** a wrapper around `AffectiveSpace`

### Initialisation

```python
from affective_space import AffectiveSpace, EmotionalImpulse

# In __init__():
self.affect_space = AffectiveSpace(
    # Initial state of the chinchilla — calm, curious
    initial_state={
        "valence":    0.3,
        "arousal":    0.5,
        "dominance":  0.4,
        "stress":     0.0,
        "trust":      0.5,
        "curiosity":  0.6,
        "stability":  0.5,
        "attachment": 0.3,
    },
    # Decay parameters toward neutral
    decay_params={
        "valence": 0.98, "arousal": 0.97, "dominance": 0.99,
        "stress": 0.96, "trust": 0.995, "curiosity": 0.97,
        "stability": 0.995, "attachment": 0.998,
    },
)

# Compatibility: self.affect.state remains as an alias
@property
def _affect_state(self):
    return self.affect_space.legacy_axes_snapshot()
```

### Update of AffectiveSpace in sim_step()

Replace `self.affect.update(dt=dt)`:

```python
# 1. Impulse from the neuromodulators (Task 3)
nm_impulse = EmotionalImpulse(
    source="neuromodulators",
    payload={
        "valence":   self.neuromod.dopamine * 0.3 - self.neuromod.cortisol * 0.4,
        "arousal":   self.neuromod.norepinephrine * 0.5 + self.neuromod.dopamine * 0.2,
        "stress":    self.neuromod.cortisol * 0.6,
        "curiosity": self.neuromod.acetylcholine * 0.4,
        "stability": self.neuromod.serotonin * 0.3 - self.neuromod.cortisol * 0.2,
    },
    intensity=0.4,
)
self.affect_space.update(
    dt=dt,
    impulses=[nm_impulse],
    wakefulness=self.wakefulness.wakefulness,
)
```

### Backward compatibility: self.affect.state

Wherever the code reads `self.affect.state`, replace it with:

```python
# Add a property on ChinchillaAgent:
@property
def affect(self):
    """Backward compatibility: returns a pseudo-object with .state"""
    return _AffectProxy(self.affect_space, self.drives)

class _AffectProxy:
    def __init__(self, space, drives):
        snap = space.legacy_axes_snapshot()
        # Supplement drives with affect keys for SchedulingSystem compatibility
        d = drives.snapshot()
        self.state = {
            **snap,
            "hunger":    d.get("energy_need", 0.0),
            "tiredness": d.get("goal_tension", 0.0),   # goal_tension approximates fatigue from tasks
            "boredom":   1.0 - d.get("curiosity", 0.5),
        }
    def get_state(self): return dict(self.state)
    def get_chain_context(self): return {"affect": self.state, **self.state}
```

---

## Task 3 — Add NeuromodulatorState

**File:** `main.py`

### Initialisation

```python
from neuromodulators import NeuromodulatorState

# In __init__():
self.neuromod = NeuromodulatorState()
```

### Update in sim_step()

```python
# 1. Decay on every tick
self.neuromod.decay_over_time(elapsed=dt)

# 2. Deltas from WakefulnessState (Task 4)
wake_deltas = self.wakefulness.get_neuromodulator_deltas()
self.neuromod.cortisol      += wake_deltas["cortisol"]      * dt
self.neuromod.norepinephrine += wake_deltas["norepinephrine"] * dt
self.neuromod.serotonin     += wake_deltas["serotonin"]     * dt
self.neuromod._clamp_all()

# 3. Update by chain — chains affect the neuromodulators
chain = self.chain_executor.current_chain
if chain == "hyperactivity":
    self.neuromod.update_from_signals(novelty=0.6, reward=0.1)  # NE up, DA up
elif chain == "chronic_stress":
    self.neuromod.update_from_signals(conflict=0.7, reward=-0.3)  # CORT up
elif chain in ("eating_and_grooming", "full_grooming", "dust_bathing"):
    self.neuromod.update_from_signals(reward=0.3, stable_repetition=True)  # 5HT up
elif chain in ("activity_burst", "exploration"):
    self.neuromod.update_from_signals(novelty=0.4, reward=0.15)  # ACh up, NE up
elif chain == "social_contact":
    self.neuromod.update_from_signals(reward=0.2, stable_repetition=False)  # DA up
```

### Passing neuromodulators into the basal ganglia (Task 5)

`BasalGangliaGate.process()` accepts `dopamine_level`, `cortisol_level`, and `norepinephrine_level` directly from `self.neuromod`.

---

## Task 4 — Add WakefulnessState

**File:** `main.py`

### Initialisation

```python
from wakefulness import WakefulnessState

# In __init__():
self.wakefulness = WakefulnessState(initial_wakefulness=0.1)  # slightly rested
```

### Update in sim_step()

```python
# Detect the sleep mode from the current chain
sleeping_chains = {"bedtime_routine", "extreme_fear"}  # hide_house/doze_shelf
sleeping_actions = {"sleep_house", "doze_shelf", "hide_house"}
is_sleeping = (
    self.chain_executor.current_chain in sleeping_chains or
    (self.current_action or {}).get("action_id", "") in sleeping_actions
)

if is_sleeping:
    self.wakefulness.update_sleeping(elapsed_seconds=dt)
else:
    self.wakefulness.update_waking(elapsed_seconds=dt)

# Pass to PygameEngine for the postural layer
reliability = self.wakefulness.get_cognitive_reliability()
# reliability < 0.3 → the chinchilla yawns and the eyes close
```

### Effect of wakefulness on chain selection

```python
# In _build_candidate_chains(): if wakefulness > 0.7, boost bedtime_routine
wake = self.wakefulness.wakefulness
if wake > 0.7:
    chain_scores["bedtime_routine"] = chain_scores.get("bedtime_routine", 0.1) + wake * 0.5
    chain_scores["full_grooming"]   = chain_scores.get("full_grooming", 0.1)  + wake * 0.2
```

---

## Task 5 — Replace _build_candidate_chains() with the basal-ganglia pipeline

**Remove:** the current implementation of `_build_candidate_chains()`  
**Add:** `BasalGangliaGate` + one `ActionChannel` per chain

### Initialisation

```python
from basal_ganglia import BasalGangliaGate, ActionChannel, BasalGangliaLearning, NO_ACTION

# In __init__():
# One ActionChannel for each behavioural chain
self.bg_channels: Dict[str, ActionChannel] = {
    chain_name: ActionChannel(action_id=chain_name)
    for chain_name in BEHAVIORAL_CHAINS
}
self.bg_gate = BasalGangliaGate(
    temperature=0.8,
    threshold=0.0,
    go_gain_alpha=0.9,
    habit_gain_beta=0.6,
    cortisol_gain_gamma=1.2,
    aversion_gain_delta=0.8,
)
self.bg_learning = BasalGangliaLearning(learning_rate=0.05)
```

### New _build_candidate_chains()

```python
def _build_candidate_chains(self, drive_suggestions: Dict[str, float]) -> List[str]:
    """BG Go/NoGo competition over chain channels."""

    DRIVE_TO_CHAINS = {
        "energy_need":  ["eating_and_grooming", "morning_awakening", "bedtime_routine"],
        "exploration":  ["exploration", "territorial_patrol", "nesting"],
        "social_drive": ["social_contact"],
        "curiosity":    ["activity_burst", "hyperactivity", "exploration"],
        "goal_tension": ["territorial_patrol", "nesting", "full_grooming"],
    }

    # Build pressure_vector from drive_suggestions onto chains
    pressure_vector: Dict[str, float] = {}
    for drive, chains in DRIVE_TO_CHAINS.items():
        drive_val = drive_suggestions.get(drive, 0.0)
        for chain in chains:
            pressure_vector[chain] = pressure_vector.get(chain, 0.0) + drive_val * 0.5

    # A base pressure for every chain, so that none drops out of the competition
    for chain in BEHAVIORAL_CHAINS:
        pressure_vector.setdefault(chain, 0.05)

    # Habit strengths from ActionChannels
    habit_strengths = {
        chain: ch.habit_strength
        for chain, ch in self.bg_channels.items()
    }

    # BG processing
    gated_scores = self.bg_gate.process(
        pressure_vector=pressure_vector,
        dopamine_level=self.neuromod.dopamine,
        cortisol_level=self.neuromod.cortisol,
        norepinephrine_level=self.neuromod.norepinephrine,
        habit_strengths=habit_strengths,
        aversive_signal=self.affect_space.legacy_axes_snapshot().get("stress", 0.0),
        exploration_bias=self.neuromod.get_exploration_level(),
    )

    # ThalamicGate stochastic selection
    selected = self.bg_gate.thalamic_gate.select(
        gated_scores=gated_scores,
        norepinephrine_level=self.neuromod.norepinephrine,
        exploration_bias=self.neuromod.get_exploration_level(),
    )

    if selected == NO_ACTION:
        return []

    # Top 3 of gated_scores as a fallback list
    sorted_chains = sorted(gated_scores.items(), key=lambda x: x[1], reverse=True)
    candidates = [selected] + [c for c, _ in sorted_chains if c != selected][:2]
    return candidates
```

### Recording outcomes for basal-ganglia learning (Sleep, Task 7)

```python
# In sim_step(), after a chain finishes:
if prev_chain and prev_chain != self.chain_executor.current_chain:
    reward = self._calculate_chain_reward(prev_chain)
    if prev_chain in self.bg_channels:
        self.bg_channels[prev_chain].record_outcome(reward)
```

---

## Task 6 — Add EmotionalRegulationLayer

**File:** `main.py`

### Initialisation

```python
from emotional_regulation import EmotionalRegulationLayer

# In __init__():
self.cer = EmotionalRegulationLayer()
```

### Call in sim_step() — autoregulation of affect

```python
# Update CER after the AffectiveSpace update
axes = self.affect_space.legacy_axes_snapshot()
cer_result = self.cer.update(
    reward=last_chain_reward,                    # reward from the last chain
    prediction_error=abs(last_chain_reward),     # unexpectedness of the outcome
    novelty=self.neuromod.get_exploration_level(),
    resolution=1.0 if chain_just_finished else 0.0,
)

# CER emits modulation factors — apply them to the basal ganglia on the next cycle
# cer_result.exploration_bias → BasalGangliaGate exploration_bias
# cer_result.decision_threshold_shift → BasalGangliaGate decision_threshold_shift
# cer_result.habit_gain_scale → BasalGangliaGate habit_gain_scale

# Direct application: reduction of stress through autoregulation
if axes.get("stress", 0) > 0.6:
    # CER applies reappraisal — an anti-stress impulse
    reg_impulse = EmotionalImpulse(
        source="cer_regulation",
        payload={"stress": -cer_result.valence * 0.15, "stability": 0.05},
        intensity=0.3,
    )
    self.affect_space.update(dt=0.0, impulses=[reg_impulse])
```

---

## Task 7 — Replace memory.consolidate_memory() with SleepManager

**Remove:** `memory_system.py` (or retain only `save_memory()` / `load_memory()` for persistence)  
**Add:** `SleepManager` + `CortexMemory` + `NOWAHippocampus`

### Initialisation

```python
from sleep import SleepManager, CortexMemory
from hippocampus import NOWAHippocampus

# In __init__():
self.hippocampus = NOWAHippocampus(capacity=500)
self.cortex = CortexMemory()
self.sleep_manager = SleepManager(
    hippocampus=self.hippocampus,
    cortex=self.cortex,
    clustering_similarity_threshold=0.7,
    forget_stability_threshold=0.15,
)
self._sleep_consolidation_pending = False
```

### Recording episodes in the hippocampus during chains

```python
# In sim_step(), after a chain finishes:
from experience import Event, Path, EventType

if chain_just_finished and last_chain_name:
    # Build a Path from the chain for the hippocampus
    chain_reward = self._calculate_chain_reward(last_chain_name)
    events = [
        Event(
            event_type=EventType.ACTION,
            name=last_chain_name,
            features={last_chain_name, self._affect_label()},
        )
    ]
    path = Path(events=events)
    self.hippocampus.store(
        path=path,
        consequence=chain_reward,
        intensity=abs(chain_reward) + 0.1,
    )
```

### Consolidation only during sleep

```python
# In sim_step():
is_deep_sleep = (
    (self.current_action or {}).get("action_id") == "sleep_house" and
    self.wakefulness.wakefulness < 0.3
)

if is_deep_sleep and not self._sleep_consolidation_pending:
    self._sleep_consolidation_pending = True
    self._run_sleep_consolidation()

if not is_deep_sleep:
    self._sleep_consolidation_pending = False

def _run_sleep_consolidation(self) -> None:
    """NOWA: learning occurs only during sleep."""
    self.sleep_manager.consolidate(
        neuromodulators=self.neuromod,
        max_patterns=20,
    )
    # Basal-ganglia sleep learning
    memories: Dict[str, List] = {}
    for chain, channel in self.bg_channels.items():
        if channel.last_outcome is not None:
            memories[chain] = [(
                channel.last_outcome,
                self.neuromod.dopamine,
                self.neuromod.cortisol,
                self.neuromod.serotonin,
            )]
    self.bg_channels_list = list(self.bg_channels.values())
    updated = self.bg_learning.apply_sleep_learning(
        channels=self.bg_channels_list,
        memories=memories,
        neuromodulators=self.neuromod,
    )
    updated = self.bg_learning.consolidate_habits(updated, self.neuromod.serotonin)
    for ch in updated:
        self.bg_channels[ch.action_id] = ch
    self.logger.info(
        f"[NOWA] Sleep consolidation: "
        f"DA={self.neuromod.dopamine:.2f} "
        f"5HT={self.neuromod.serotonin:.2f} "
        f"CORT={self.neuromod.cortisol:.2f}"
    )
```

---

## Task 8 — Add ConflictArbitrationLayer

**File:** `main.py`

### Initialisation

```python
from conflict_arbitration import ConflictArbitrationLayer

# In __init__():
self.conflict_arb = ConflictArbitrationLayer()
```

### Call before chain selection

```python
# In _try_start_chain(), before the call to _build_candidate_chains():
gated = self.bg_gate.last_gated  # from the previous call to process()

if gated:
    scores = list(gated.values())
    # Entropy is a measure of uncertainty of the choice
    import math
    total = sum(scores) + 1e-9
    entropy = -sum((s/total) * math.log(s/total + 1e-9) for s in scores)
    # top-2 gap
    sorted_s = sorted(scores, reverse=True)
    top2_gap = (sorted_s[0] - sorted_s[1]) / (sorted_s[0] + 1e-9) if len(sorted_s) > 1 else 1.0

    arb_result = self.conflict_arb.update(
        candidate_scores=list(gated.values()),
        prediction_error=abs(self._last_chain_reward or 0.0),
        recent_failure_rate=self._recent_failure_rate(),
        wm_load=len(gated) / 14.0,   # normalised load (14 chains)
        task_complexity=len(gated) / 14.0,
        latency=self.chain_cooldown_s,
    )
    # arb_result.exploration_bias → pass into _build_candidate_chains
    # arb_result.decision_threshold_shift → pass into the basal ganglia
```

---

## Task 9 — Debug display: visualisation of the NOWA layers

**File:** `pygame_engine.py`

Add the method `set_nowa_state()` and extend the debug overlay.

```python
def set_nowa_state(self, nowa_snapshot: dict) -> None:
    """Accepts a full snapshot of NOWA state for the heads-up display."""
    self._nowa_snapshot = nowa_snapshot

def _draw_nowa_hud(self) -> None:
    """Draw the NOWA layers in debug mode."""
    if not self.show_debug or not hasattr(self, '_nowa_snapshot'):
        return
    s = self._nowa_snapshot
    x, y = 10, 60
    line_h = 14

    sections = [
        ("── NEUROMODULATORS ──", [
            f"DA  {s.get('dopamine',0):.2f}  | 5HT {s.get('serotonin',0):.2f}",
            f"NE  {s.get('norepinephrine',0):.2f}  | CORT {s.get('cortisol',0):.2f}",
            f"ACh {s.get('acetylcholine',0):.2f}",
        ]),
        ("── DRIVES ──", [
            f"energy_need  {s.get('energy_need',0):.2f}",
            f"curiosity    {s.get('curiosity',0):.2f}",
            f"exploration  {s.get('exploration',0):.2f}",
            f"social_drive {s.get('social_drive',0):.2f}",
            f"goal_tension {s.get('goal_tension',0):.2f}",
        ]),
        ("── AFFECT (8D) ──", [
            f"valence  {s.get('valence',0):+.2f}  arousal {s.get('arousal',0):.2f}",
            f"stress   {s.get('stress',0):.2f}   trust  {s.get('trust',0):.2f}",
            f"curiosity {s.get('curiosity_a',0):.2f}  stab {s.get('stability',0):.2f}",
        ]),
        ("── WAKEFULNESS ──", [
            f"wake  {s.get('wakefulness',0):.2f}  reliability {s.get('cognitive_reliability',0):.2f}",
        ]),
        ("── BG TOP-3 ──", [
            f"{i+1}. {chain:<22} {score:.3f}"
            for i, (chain, score) in enumerate(s.get('bg_top3', []))
        ]),
    ]

    for title, lines in sections:
        surf = self.font_dbg.render(title, True, (200, 180, 120))
        self.screen.blit(surf, (x, y)); y += line_h
        for line in lines:
            surf = self.font_dbg.render(line, True, (180, 200, 180))
            self.screen.blit(surf, (x + 6, y)); y += line_h
        y += 4
```

### NOWA snapshot in main.py

```python
# In sim_step(), after every update:
if self.pygame_engine and self.pygame_engine.show_debug:
    bg_top3 = sorted(
        self.bg_gate.last_gated.items(),
        key=lambda x: x[1], reverse=True
    )[:3]
    self.pygame_engine.set_nowa_state({
        # Neuromodulators
        "dopamine":        self.neuromod.dopamine,
        "serotonin":       self.neuromod.serotonin,
        "norepinephrine":  self.neuromod.norepinephrine,
        "cortisol":        self.neuromod.cortisol,
        "acetylcholine":   self.neuromod.acetylcholine,
        # Drives
        **self.drives.snapshot(),
        # Affect, 8D
        **self.affect_space.legacy_axes_snapshot(),
        # Wakefulness
        "wakefulness":          self.wakefulness.wakefulness,
        "cognitive_reliability": self.wakefulness.get_cognitive_reliability(),
        # Basal ganglia
        "bg_top3": bg_top3,
        # CER
        "cer_exploration": getattr(self.cer, 'exploration_bias', 0.0),
    })
```

---

## Task 10 — Saving and loading NOWA state

**File:** `main.py`

Replace `memory_system.save_memory()` with a full snapshot of NOWA state.

### save_nowa_state()

```python
def save_nowa_state(self) -> None:
    import json
    saves_dir = self.demo_dir / "saves"
    saves_dir.mkdir(exist_ok=True)

    state = {
        "neuromodulators": self.neuromod.to_dict(),
        "drives": self.drives.snapshot(),
        "wakefulness": self.wakefulness.get_statistics(),
        "bg_channels": {
            name: {
                "go_weight":      ch.go_weight,
                "nogo_weight":    ch.nogo_weight,
                "habit_strength": ch.habit_strength,
                "selection_count": ch.selection_count,
                "success_count":  ch.success_count,
            }
            for name, ch in self.bg_channels.items()
        },
        "cortex_patterns": len(self.cortex.patterns),
        "hippocampus_size": len(self.hippocampus._traces)
            if hasattr(self.hippocampus, '_traces') else 0,
        "total_sim_time": self.total_sim_time,
    }

    with open(saves_dir / "nowa_state.json", "w") as f:
        json.dump(state, f, indent=2)
    self.logger.info("[NOWA] State saved")
```

### load_nowa_state()

```python
def load_nowa_state(self) -> bool:
    import json
    path = self.demo_dir / "saves" / "nowa_state.json"
    if not path.exists():
        return False
    try:
        with open(path) as f:
            state = json.load(f)
        self.neuromod = NeuromodulatorState.from_dict(state["neuromodulators"])
        for name, vals in state.get("bg_channels", {}).items():
            if name in self.bg_channels:
                ch = self.bg_channels[name]
                ch.go_weight      = vals.get("go_weight", 0.5)
                ch.nogo_weight    = vals.get("nogo_weight", 0.5)
                ch.habit_strength = vals.get("habit_strength", 0.0)
                ch.selection_count = vals.get("selection_count", 0)
                ch.success_count  = vals.get("success_count", 0)
        self.logger.info("[NOWA] State loaded")
        return True
    except Exception as e:
        self.logger.error(f"[NOWA] Load failed: {e}")
        return False
```

### Call sites

```python
# In __init__(), after every component has been initialised:
self.load_nowa_state()

# In cleanup():
self.save_nowa_state()

# In sim_step(), periodically:
if self.total_sim_time - self._last_nowa_save >= 120.0:
    self.save_nowa_state()
    self._last_nowa_save = self.total_sim_time
```

---

## Implementation order

| # | Task | Depends on | Complexity |
|---|---|---|---|
| 3 | NeuromodulatorState | — | Low |
| 4 | WakefulnessState | — | Low |
| 2 | AffectiveSpace | 3 | Medium |
| 1 | DriveSystem | 2 | Medium |
| 5 | BasalGangliaGate | 1, 3, 4 | Medium |
| 6 | EmotionalRegulationLayer | 2, 5 | Medium |
| 8 | ConflictArbitrationLayer | 5 | Medium |
| 7 | SleepManager | 4, 5 | High |
| 9 | Debug display | 1–6 | Low |
| 10 | Save/Load | 1–7 | Low |

Tasks 3 and 4 come first: they are independent and unblock everything else.
Task 7 (sleep) comes last: it is the most difficult and requires a working basal-ganglia circuit and wakefulness.
