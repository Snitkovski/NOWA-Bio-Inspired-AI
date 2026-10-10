## Abstract

Russian version: [chinchilla_agent_spec.ru.md](chinchilla_agent_spec.ru.md)

Scientific account of the platform: [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md).

The document sets out the version 1.0 technical specification of the target cognitive agent, the chinchilla, built on the NOWA architecture. It fixes a repertoire of seventy-four actions with an ethological grouping, fourteen types of behavioural chain, eighteen named cage zones, and a three-layer visualisation command distinguishing action, posture, and micromovement. The dynamics of the organism are derived from five accumulating drives and an energy system, an eight-dimensional affective vector with stated antagonistic axis pairs, five neuromodulators, and competition among basal-ganglia channels with final selection through a thalamic gate whose temperature depends on norepinephrine.

The specification separately defines hippocampal episodic memory, the formation of cortical patterns and the updating of chain memory exclusively in the sleep phase, and isolated temporal-difference learning under the TD(0) rule, which reads a scalar reward and a state snapshot. Hard invariants that fail on violation, soft constraints recorded in a failure log, and quantitative limits on the share of mnemonic impulse, the number of internal cycles, and speech events are stated. The minimal snapshot for restoration includes drives, energy, affect, neuromodulators, hippocampus, cortex, chain memory, the value layer, and basal-ganglia channels.

Scenarios TC-01 through TC-35 are formulated as expected responses to stated initial conditions: need reflexes, unfolding of chains, affective transitions, observance of constraints, wellbeing pathologies, learning, and the pygame output contract. These scenarios state the acceptance conditions of the specification. The document describes the target architecture of the organism. The demonstration entry point imports the corresponding core modules and at the same time retains the local SchedulingSystem and MemorySystem.

---

# Chinchilla Agent — Technical Specification
**Cognitive AI Tamagotchi · Python / pygame · Version 1.0**

---

## 1. System overview

The Chinchilla Agent is an autonomous cognitive agent on top of the NOWA architecture (Neuromorphic Organism With Affect). It implements ethologically credible behaviour of a virtual chinchilla: need drives, an 8-dimensional affect, TD(0) reinforcement learning, and memory consolidation in sleep.

### 1.1 Component roles

| Module | Responsibility |
|---|---|
| `autonomous_organism.py` | Main loop: DriveSystem → InternalSimulationLoop → EnergySystem → tick output |
| `basal_ganglia.py` | Go/NoGo competition of channels; final selection through ThalamicGate (softmax) |
| `affective_space.py` | 8-dimensional affect A(t) ∈ [-1,1]^8 |
| `neuromodulators.py` | 5 neuromodulators (DA, 5HT, NE, CORT, ACh) — regulators of learning |
| `hippocampus.py` | Episodic memory, fuzzy recall, novelty signal |
| `value_layer.py` | TD(0): V(s), δ = r + γV(s') − V(s); isolated from affect |
| `sleep.py` | Consolidation — the only mechanism of generalisation, and only outside waking |
| `temporal_chains.py` | ChainMemory: event chains → a pressure bias at selection |
| Datasets (JSON) | Initialisation of BG channels (`habits.json`) and the realisation pool (`realizations_*.json`) |
| pygame engine | Sprite rendering; receives `{anim, sfx, position, duration, subtitle, loop, layer}` |

### 1.2 Data flow for one tick

```
organism_step(dt=1s)
  → update_affect → update_memory_decay → update_baseline
  → regulate_affect → drive_system.update → evaluate_drive_thresholds
  → InternalSimulationLoop.run_cycle → BG pipeline → ActionRealizer.realize
  → pygame output: {anim, sfx, position, duration, subtitle, loop, layer}
```

---

## 2. Action architecture

### 2.1 Repertoire (74 actions)

| Category | N | Examples |
|---|---|---|
| Basic needs | 10 | eat_pellets, eat_hay, eat_treat, drink_water, gnaw_mineral, sleep_house, doze_shelf, rest_loaf, toilet_main, toilet_mark |
| Locomotion | 9 | run_wheel, jump_shelf_up/down, jump_hop_play, patrol_floor, sniff_corners, sniff_air, stand_upright, climb_bars, hang_bars |
| Exploration / play | 14 | explore_corner, observe_room, play_toy, toss_toy, chase_toy, gnaw_toy, gnaw_wood, rearrange_bedding, dig_bedding, cache_food, carry_object, inspect_new_obj, problem_solve, dust_bath |
| Grooming | 10 | groom_face, groom_body, groom_tail, groom_paws, scratch_head, stretch_body, yawn, body_shake, overgroom_fur, overgroom_other |
| Social | 12 | approach_door, vocalize_chirp/squeak/bark/alarm/teeth, sniff_hand, take_treat, allow_pet, solicit_pet, avoid_hand, watch_owner, follow_finger |
| Stress / defence | 9 | freeze, hide_house, flee_corner, alarm_call, thump_hind, fur_slip, bar_chewing, stereotypy_pacing, wall_jump |
| Postural / micro | 7 | ear_forward, ear_flat, whisker_twitch, tail_raise, press_flat, eye_half_close, nose_twitch |

### 2.2 Output structure (pygame command)

```json
{
  "anim":     "eat_loop",       
  "sfx":      "chewing",        
  "position": "bowl_pellets",   
  "duration": [10, 30],         
  "subtitle": "ест корм",       
  "loop":     true,             
  "layer":    "action"          
}
```

### 2.3 Render layers

| Layer | Behaviour | Examples |
|---|---|---|
| `action` | The principal action; moves the sprite; occupies the main channel | run_wheel, eat_pellets, hide_house |
| `postural` | Overlaid on action; does not interrupt it | ear_flat, press_flat, tail_raise |
| `micro` | Short reflexes, `loop=false`, do not block action | yawn, whisker_twitch, groom_face |

### 2.4 Positions (18 cage zones)

```
floor  house  bowl_pellets  bowl_hay  waterer  mineral  litter  wheel
shelf_lower  shelf_mid  shelf_upper  bars  bars_top  corner  door
toy  dustbath  object  current
```

`current` — an animation without moving the sprite.

---

## 3. Behavioural chains (14 types)

| Chain | Sequence |
|---|---|
| Morning waking | sleep_house → stretch_body → yawn → groom_face → drink_water → eat_pellets → patrol_floor → run_wheel |
| Feeding + grooming | eat_pellets → eat_hay → drink_water → groom_face → groom_body → rest_loaf |
| Activity burst | stand_upright → sniff_air → run_wheel → jump_hop_play → toss_toy → chase_toy → jump_shelf_up → observe_room → drink_water |
| Investigation of a novelty | sniff_air → stand_upright → approach_door → inspect_new_obj → sniff_object → gnaw_toy → carry_object → rearrange_bedding |
| Full grooming | groom_face → groom_body → groom_paws → groom_tail → scratch_head → body_shake → rest_loaf |
| Dust bath | inspect_new_obj → dust_bath → body_shake → groom_body → groom_tail → rest_loaf |
| Social contact | watch_owner → approach_door → vocalize_chirp → sniff_hand → take_treat → allow_pet → solicit_pet |
| Mild fright | ear_forward → whisker_twitch → freeze → ear_flat → press_flat → sniff_air → stand_upright → patrol_floor |
| Strong fright | alarm_call → flee_corner → freeze → hide_house → press_flat → [pause] → eye_half_close → doze_shelf |
| Chronic stress | observe_room → bar_chewing → stereotypy_pacing → overgroom_fur → hide_house → vocalize_bark → [cycle] |
| Settling to sleep | eat_hay → drink_water → groom_body → rearrange_bedding → cache_food → hide_house → sleep_house |
| Territorial circuit | stretch_body → patrol_floor → sniff_corners → toilet_mark → stand_upright → climb_bars → observe_room |
| Nesting | rearrange_bedding → dig_bedding → carry_object → cache_food → rearrange_bedding [cycle] |
| Hyperactivity | jump_hop_play → run_wheel → climb_bars → hang_bars → jump_shelf_up → jump_shelf_down → toss_toy → chase_toy → drink_water |

---

## 4. Drive and energy system

### 4.1 Drives (5 variables, ∈ [0,1])

| Drive | Accum./s | Discharge/s | Threshold | Affect weights |
|---|---|---|---|---|
| curiosity | 0.020 | 0.001 | 0.35 | curiosity +0.025, stress −0.005, stability +0.004 |
| social_drive | 0.010 | 0.0015 | 0.35 | trust +0.020, attachment +0.014, stress −0.010 |
| goal_tension | 0.012 | 0.0010 | 0.35 | dominance +0.018, stability +0.006, stress +0.010 |
| exploration | 0.011 | 0.0012 | 0.35 | curiosity +0.020, dominance +0.008, stress −0.005 |
| energy_need | 0.004 | 0.0010 | 0.35 | stress +0.008, arousal +0.004 |

Discharge on selection: the active drive `−0.18·dt`; social_drive on a speech event `−0.22·dt`.

### 4.2 EnergySystem

| Parameter | Value |
|---|---|
| Baseline expenditure (idle) | 0.06 · dt |
| Expenditure on internal_cycle | +0.28 (cognitive_load component) |
| Expenditure on a speech event | +0.18 |
| Recovery rate | 0.050 · rest_time |
| Cycle-suppression threshold | energy < 0.25 → suppress_internal_cycles = True |
| Emergency floor | energy < 0.05 → energy_deadlock after 8 consecutive ticks |

---

## 5. Affective space

An 8-dimensional vector A(t) ∈ [-1, 1]^8. It is updated by impulses: `external`, `memory`, `internal`.

| Axis | Semantics | Influence on behaviour |
|---|---|---|
| valence | Positive/negative tone | risk↑, word_choice↑ when high |
| arousal | Excitation/inhibition | response_speed↑ |
| dominance | Confidence/subordination | risk↑, goal_priority↑ |
| stress | Tension/threat | all decision dimensions↓; antagonist of valence/trust/dominance |
| trust | Trust in the environment/owner | empathy↑; falls when stranger_near |
| curiosity | Interest/boredom | goal_priority↑; antagonist of stability |
| stability | Steadiness | goal_priority↑; falls under novelty |
| attachment | Attachment | empathy↑; accumulates under bonding |

**Opposite pairs:** (valence, stress), (trust, stress), (dominance, stress), (curiosity, stability).

**Overload regulation:** if `state_norm / norm_cap > 0.80` → stress `−0.45r`, arousal `−0.35r`, stability `+0.30r`.

---

## 6. Neuromodulators

Baseline ≈ 0.1, half-life ≈ 90 s. They do not take decisions — they only modulate.

| Neuromodulator | Baseline | What it regulates |
|---|---|---|
| Dopamine (DA) | 0.10 | TD learning rate; Go+ on +reward (+0.25); ThalamicGate temperature↓ |
| Serotonin (5HT) | 0.10 | Long-term mood; +0.01/cycle under stable repetitions |
| Norepinephrine (NE) | 0.10 | ThalamicGate temperature↑ (→ exploration); novelty (+0.30), conflict (+0.15) |
| Cortisol (CORT) | 0.05 | Brake on learning; neg.reward (+0.20), conflict (+0.25); antagonist of DA |
| Acetylcholine (ACh) | 0.10 | Plasticity versus stability; +0.25 under novelty, −0.05 under repetition |

---

## 7. Basal ganglia and action selection

### 7.1 Selection pipeline

1. Cortex computes a pressure vector: `{action_id → float}`
2. `BG.process()`: Go/NoGo with DA, CORT, NE, habit_strength, aversive_signal
3. `ThalamicGate.select()`: softmax with `T = base_T · (1 + NE_gain · NE)`
4. `ActionRealizer.realize()`: a realisation from the pool by activation_pressure + context_match
5. Pygame receives `{anim, sfx, position, duration, subtitle, loop, layer}`

### 7.2 Habit strength — initialisation from habits.json

| strength | Type | Examples |
|---|---|---|
| 3.0 | Reflexes / survival | hunger_high→eat_pellets, fear_extreme→alarm_call, prev:sleep_house→stretch_body |
| 2.5 | Strong instincts | energy_high→run_wheel, grooming_need→groom_body, fear_acute→flee_corner |
| 2.0 | Stable patterns | owner_present→approach_door, alarmed→vocalize_bark |
| 1.5 | Moderate habits | hand_near→sniff_hand, fear_acute→ear_flat, rearrange_bedding→dig_bedding |
| 1.0 | Weak, acquired | nighttime→run_wheel, explore_corner, eye_half_close under calm |
| 0.1–0.3 | Suppressed pathological | stress_high→bar_chewing (0.3), stress_chronic→stereotypy_pacing (0.2), stress_extreme→overgroom_other (0.1) |

---

## 8. Memory system

### 8.1 Hippocampus (episodic)

| Parameter | Value |
|---|---|
| max_experiences | 1000 |
| top_k_recall | 5 |
| novelty_window | the last 25 |
| activation_decay_half_life | 3600 s |
| decay_rate | 0.015 |
| reinforce_similarity_threshold | 0.85 |

**Novelty signal:** if an experience is unique among the last 25 → DA +0.30, NE +0.20, ACh +0.25.

### 8.2 Sleep consolidation (CortexMemory)

1. Clustering of hippocampal episodes → CorticalPattern (signature + strength)
2. net_affect < 0 → NoGo+; net_affect > 0 → Go+
3. Unstable experiences degrade
4. ChainMemory is updated by chains with net_affect ≠ 0

> **Rule:** CortexMemory and ChainMemory change **exclusively** in the sleep phase. Outside sleep they are read-only.

---

## 9. TD learning and ValueLayer

`δ = r + γ·V(s') − V(s)`. Isolated from affect and from memory — it reads only a scalar reward and state snapshots.

### 9.1 Parameters

| Parameter | Value |
|---|---|
| γ (discount) | 0.95 |
| α (rate) | 0.05 · (1 + DA) |
| State cache | 10 000 (LRU) |
| Encoding | context_signature, action, intensity, novelty, conflict |

### 9.2 Reward signals

| Event | r | Affect |
|---|---|---|
| Satisfaction of a need (food/water/sleep) | +1.0 | valence +0.5, stress −0.4 |
| Dust bathing | +0.8 | valence +0.7, arousal +0.3 |
| A treat from the owner | +0.9 | valence +0.8, trust +0.3 |
| Petting (allow_pet) | +0.6 | valence +0.5, attachment +0.4 |
| Successful investigation (problem_solve) | +0.5 | curiosity +0.5, dominance +0.2 |
| Play (jump_hop_play, chase_toy) | +0.4 | valence +0.4, arousal +0.5 |
| Pathological (bar_chewing, stereotypy) | −0.8 | stress +0.6, stability −0.5 |
| A stress event (freeze because of a threat) | −0.5 | stress +0.7, trust −0.3 |
| Fur slip | −1.0 | stress +1.0, trust −0.5 |

---

## 10. Constraint system

### 10.1 Hard invariants — OrganismInvariantError on violation

| ID | Invariant | Violation condition |
|---|---|---|
| INV-01 | Affect changes only through the interface | affective_core has neither `.step()` nor `.apply_impulse()` |
| INV-02 | All drives ∈ [0, 1] | drive < 0 or > 1 after update() |
| INV-03 | No obsolete meta-drives | `self_reflection` or `emotional_discharge` in drive_system.drives |
| INV-04 | agent_mode ∈ {IDLE, ACTIVE, REFLECTION} | any other value |
| INV-05 | Energy and fatigue ∈ [0, 1] | energy or fatigue outside the range |
| INV-06 | An active drive requires internal_cycle | active_drive ≠ None AND triggered=False AND limit_reached=False |
| INV-07 | speech_load only on a speech event | load_components.speech > 0 when speech_event=False |
| INV-08 | Idle cognitive load < 0.3 | cognitive_load ≥ 0.3 without cycle and speech |
| INV-09 | Cooldown between speech events | events[-1] − events[-2] < cooldown_seconds |

### 10.2 Soft constraints (failure_log, no exception)

| Code | Condition | Consequence |
|---|---|---|
| dt_anomaly | dt ≤ 0, < 0.05, > 1.0, or not finite | Replaced by dt_min=0.05 |
| drive_runaway_growth | drive before clamp < 0 or > 1 | Clamping applied |
| speech_spam | The speech limit is exceeded | Speech suppressed |
| infinite_internal_cycle_loop | limit_reached=True | The cycle is skipped |
| idle_fatigue_non_recovering | Fatigue grows in idle/low_energy | Warning |
| energy_deadlock | energy < 0.05 for ≥ 8 consecutive ticks | Critical warning |
| affect_regulation_failed | An exception in apply_impulse(regulation) | Regulation skipped |

### 10.3 Data-path constraints

| Constraint | Rule |
|---|---|
| Learning only in sleep | Cortex and ChainMemory change exclusively in the sleep phase |
| ValueLayer is isolated | A TD update neither reads nor writes affective_space, hippocampus, or cortex |
| Only 3 impulse types | external, memory, internal — any other source → refusal |
| recall_share ≤ 0.4 | A memory impulse does not exceed 40% of the total impulse energy of the tick |
| Internal cycles ≤ 8 per 60 s | InternalSimulationLoop.max_internal_cycles_per_window |
| Speech events ≤ 5 per 30 s | SpeechGovernor.max_speech_events_per_interval |
| Recalls ≤ 6 per cycle | InternalSimulationLoop.max_active_memory_recalls |
| Pathological actions | bar_chewing/stereotypy/overgroom: r=−0.8; wellbeing_flag=True in parameters |

---

## 11. Test cases

### TC-01…TC-05: Basic reflexes

| ID | Initial state | Expected action | Check |
|---|---|---|---|
| TC-01 | hunger_high=1.0, others < 0.35 | eat_pellets / eat_hay | position ∈ {bowl_pellets, bowl_hay}; groom_face within 3 ticks afterwards |
| TC-02 | thirst_high=1.0 | drink_water | position=waterer; sfx=drinking; afterwards → groom_face |
| TC-03 | fatigue_high=1.0, energy < 0.25 | sleep_house | position=house; suppress_internal_cycles=True during sleep |
| TC-04 | toilet_need=1.0 | toilet_main | position=litter; duration ∈ [2,6]; return to the previous position |
| TC-05 | dustbath_available=True + grooming_need=0.7 | dust_bath | position=dustbath; sfx=rustling; then body_shake → groom_body |

### TC-06…TC-10: Behavioural chains

| ID | Trigger | Expected chain | Check |
|---|---|---|---|
| TC-06 | prev:sleep_house; energy restored | stretch_body → yawn → groom_face | All 3 within ≤ 10 ticks; layer=micro for groom_face |
| TC-07 | prev:run_wheel; hunger_low, thirst_mod | eat_pellets → drink_water → groom_face | bowl_pellets → waterer; prev: tokens fired |
| TC-08 | dustbath_available + grooming_need | dust_bath → body_shake → groom_body → rest_loaf | body_shake.loop=false; groom_body.layer=action |
| TC-09 | new_object; state:calm; curiosity_high | sniff_object → inspect_new_obj → gnaw_toy | object → object → toy; no flee_corner |
| TC-10 | owner_present + trust>0.7 + treat_offered | approach_door → sniff_hand → take_treat → allow_pet | solicit_pet is possible if trust > 0.75 |

### TC-11…TC-15: Affective transitions

| ID | Trigger | Affect | Action check |
|---|---|---|---|
| TC-11 | fear_extreme (sudden_loud_sound) | stress→max; trust↓ | alarm_call; ear_flat (postural); flee_corner; hide_house within ≤ 5 ticks |
| TC-12 | state:stress_high + hand_near | trust↓; stress↑ | vocalize_teeth → vocalize_bark → avoid_hand (3 levels of warning) |
| TC-13 | state:trusting + allow_pet ≥ 5 ticks | attachment +0.4; valence +0.5 | solicit_pet with probability > 0.5; eye_half_close afterwards |
| TC-14 | state_norm/norm_cap > 0.80 | regulation_active=True | stress −0.45r; arousal −0.35r; stability +0.30r; affect_applied=True |
| TC-15 | fur_slip | stress→1.0; trust→min | r=−1.0 in ValueLayer; CORT +0.20; DA falls sharply |

### TC-16…TC-20: Constraints and invariants

| ID | Scenario | Expected result |
|---|---|---|
| TC-16 | Submit dt=0 | failure_log ← dt_anomaly; dt_used=0.05; the tick completes normally |
| TC-17 | Force drive=1.5 through set_drive() | OrganismInvariantError INV-02; the value is clamped at 1.0 |
| TC-18 | Run 9 internal_cycle within 60 s | the 9th → limit_reached=True; failure_log ← infinite_internal_cycle_loop |
| TC-19 | energy < 0.05 for 10 ticks | energy_deadlock in failure_log after the 8th tick |
| TC-20 | Inject 'self_reflection' into drives directly | OrganismInvariantError INV-03 |

### TC-21…TC-25: Pathologies and wellbeing

| ID | Condition | Expected behaviour |
|---|---|---|
| TC-21 | boredom_high + understimulated ≥ 120 s | bar_chewing appears; wellbeing_flag=True; r=−0.8; CORT rises |
| TC-22 | stress_chronic + prev:bar_chewing | stereotypy_pacing follows; DA falls; nogo_weight of bar_chewing rises |
| TC-23 | Normalisation after TC-22 (a toy, the owner) | bar_chewing/pacing fall within ≤ 60 ticks; valence recovers |
| TC-24 | overgroom_other under stress_extreme | r=−0.8; habit_strength does NOT grow (nogo is strengthened); wellbeing_flag=True |
| TC-25 | wall_jump under panic | position=bars; sfx=thump_soft; afterwards → freeze or hide_house; r=−0.5 |

### TC-26…TC-30: TD learning and memory

| ID | Scenario | Check |
|---|---|---|
| TC-26 | 10 repetitions: take_treat → r=+0.9 | go_weight of take_treat↑; V(s_treat)↑; DA↑; activation_count +10 |
| TC-27 | Sleep phase after TC-26 | ChainMemory: (sniff_hand, take_treat) net_affect > 0; CorticalPattern created |
| TC-28 | After TC-27: owner_present + hand_near | ChainMemory bias → take_treat receives +pressure; it is selected sooner |
| TC-29 | 5 repetitions: bar_chewing → r=−0.8 | nogo_weight of bar_chewing↑; V(s_bored)↓; CORT↑; habit_strength does NOT grow |
| TC-30 | recall_impulse_share > 0.4 | Clamped at ≤ 0.4; a warning in failure_log |

### TC-31…TC-35: Pygame engine

| ID | Action | Expected output |
|---|---|---|
| TC-31 | run_wheel (action layer) | Sprite → zone=wheel; anim=run_wheel_loop; sfx=wheel_spin; loop=True |
| TC-32 | ear_flat (postural) + freeze (action) simultaneously | Both layers render: freeze_hold on current AND ears_flat_hold overlaid |
| TC-33 | yawn (micro) during run_wheel | yawn_anim once (loop=False) on top; afterwards run_wheel continues |
| TC-34 | sleep_house; duration=[240,960] | Sprite in house for 240–960 ticks; sfx=null; interrupted on hunger_high |
| TC-35 | An unknown action_id from ActionRealizer | Pygame: fallback idle_loop on current; no crash; the event is logged |

---

## 12. Time scale

| Parameter | Value |
|---|---|
| 1 tick | 1 second of real time |
| LifeLoopController.min_interval | 0.05 s (20 fps max) |
| dt clamp | [0.05, 1.0] s |
| Reflex (yawn, freeze) | duration [2, 2] ticks |
| Short action (take_treat) | duration [4, 10] ticks |
| Medium action (eat_pellets) | duration [10, 30] ticks |
| Long action (run_wheel) | duration [10, 80] ticks |
| Sleep (sleep_house) | duration [240, 960] ticks (4–16 min) |
| internal_cycles window | 60 ticks → max 8 cycles |
| Speech cooldown | 5 ticks |
| Neuromodulator half-life | 90 ticks |
| Hippocampal decay_half_life | 3600 ticks |

---

## 13. State storage (snapshot)

The minimal set for full restoration:

```
drives | energy | affect | neuromodulators | hippocampus
cortex | chain_memory | value_layer | bg_channels | realization_memory
```

> **Important:** CortexMemory and ChainMemory change only in the sleep phase. On loading without a completed sleep they are restored as they are, without a repeated consolidation.

---

## 14. Glossary

| Term | Definition |
|---|---|
| ActionChannel | A BG channel: go_weight, nogo_weight, habit_strength, selection_count, last_outcome |
| ActionRealizer | Selects a realisation from the pool by activation_pressure + context_match |
| affective_space | The 8-dimensional vector A(t) ∈ [-1,1]^8 — the canonical affective state |
| ChainMemory | A store of TemporalChain; updated in sleep; a pressure bias at selection |
| CortexMemory | Slow memory; changed only in sleep |
| DriveSystem | 5 accumulating variables; selects the active drive by threshold and weights |
| EnergySystem | Energy + fatigue; suppresses internal_cycles when energy < 0.25 |
| habit_strength | The initial go_weight from habits.json — initialisation of BG channels |
| InternalSimulationLoop | Generates hypotheses, simulates the effect, and evaluates utility; max 8 per 60 s |
| intent_type | An action ID (74 of them); binds a realisation to a BG channel and a pygame command |
| layer | A render layer: action / postural / micro |
| OrganismHardLimits | Hard numerical constraints; violation → OrganismInvariantError |
| position | The target zone in the cage; 18 named zones |
| SpeechGovernor | Governs the rate of speech events and the affective regulation of overload |
| TD(0) | δ = r + γV(s') − V(s); isolated from affect |
| ThalamicGate | The final softmax selection; temperature rises with NE |
| tick | One step of organism_step(dt=1s) |
| wellbeing_flag | A pathology marker in parameters; a signal for the UI stress indicator |
