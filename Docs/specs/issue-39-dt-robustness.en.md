# Issue #39 — Colony dt robustness: implementation spec

Closes #39 (demo host only). Related: [fix-colony-no-rest.en.md](fix-colony-no-rest.en.md) (sleep bout without onset), PR #36 (portion rule), PR #48.

The cognitive **core** in `src/` is not retuned. Each chinchilla remains its own `Agent`. `PHYSIOLOGY_AS_POLICY=True` stays on.

---

## 1. Problem

At UI speed 10×, founders of `Demo/Colony chinchillas` die of **exhaustion** (energy ≤ 0.08) within minutes while food, hay, and water are still plentiful. Death records show low stress and positive valence — a “calm and fed” exhaustion.

Observed on `main` after PR #36, seed 7, four founders:

| tick `dt` | policy | sim time | deaths |
| --- | --- | --- | --- |
| 1/12 (×1) | True | 142 s | none |
| 0.25 (×1 under GUI load) | True | 395 s | none (min energy 0.65) |
| **2.5 (×10 × 0.25)** | **True** | 2400 s | **2 (212.5 s, 1195 s)** |
| 2.5 | False | 2400 s | none |

`ColonyGUI._sim_tick` advances the runner by `real_dt * speed`. Under load, `SIM_MAX_STEP_S = 0.25` (`app.py`), so a live 10× frame is `0.25 × 10 = 2.5` s per decision boundary before sub-stepping.

---

## 2. Root cause (demo host)

1. **Decision rate vs penalty integration.** `_apply_unmet_need_cost` charges energy per simulated second (hunger ≥ 0.60 → 0.02/s, thirst ≥ 0.58 → 0.025/s, sleep deficit → 0.02/s). One agent decision ran per `tick(dt)`. At `dt = 2.5`, a single missed eat/drink costs ~0.0625 energy; ~8 consecutive misses are lethal. At ×1 the same gap costs 25–30× less per wall second of sim time because decisions are more frequent.

2. **Dead zone.** Eat/drink availability used the same thresholds as the penalty (`HUNGER_NEED_THRESHOLD` 0.60, `THIRST_NEED_THRESHOLD` 0.58). Between “cannot act” and “penalty starts” the animal paid the penalty with no relief path.

3. **Sleep trap.** A voluntary nap below Process S onset could be treated like a physiological bout; thirst penalty continued while drink was impossible in sleep. Energy could fall from ~0.49 to ~0.04 in ~22.5 s sim time.

4. **Metabolism dt bug.** `_metabolism_tick` reset to 0 after each second bucket instead of subtracting 1.0, so hunger/thirst advanced once per tick, not once per simulated second.

5. **Sleep recovery dt bug.** `SLEEP_MIN_RECOVERY_DURATION_S` (30) acted as a per-tick floor, so short steps restored energy and Process S faster than one long step over the same simulated second.

6. **Design note (not a bug).** Eating, drinking, and `rest` do not restore energy; only sleep and passive body rest do.

**Core:** not responsible for demo timing. Side observation: `autonomous_organism` clamps `dt` to 1.0 and `rest_time` is per call, not × `dt` — addressed in the host via body slicing (see [fix-colony-no-rest.en.md](fix-colony-no-rest.en.md)), not by retuning the core.

---

## 3. Design (implemented items)

### A. Sub-ticking and HUD actual speed

**File:** `Demo/Colony chinchillas/src/simulation_runner.py`

- `MAX_TICK_DT = 0.25` (matches load-adapted 1× step, `app.SIM_MAX_STEP_S`).
- `tick(dt)`: if `dt > MAX_TICK_DT`, split into `ceil(dt / 0.25)` equal sub-ticks; each sub-tick calls `_tick_once` once (one `agent.sim_step` per agent).
- Nominal ×1 (`dt = 1/12`) stays under the cap — no extra coarsening.
- Nominal ×10 on the 1/12 base (`10/12` s) is still split so each slice ≤ 0.25 s.

**Files:** `colony_gui/colony_gui.py`, `colony_gui/app.py`

- `ColonyGUI.note_sim_pace(real_dt, sim_advanced)` tracks simulation seconds gained vs `real_dt * speed` over ~0.5 s wall window.
- `achieved_speed_ratio < 0.85` → HUD shows `actual x…` / `факт x…` via `format_speed_status_line`.
- Sub-stepping increases CPU work; a slow machine may fall behind the selected acceleration.

### B. Unmet-need penalty while acting is impossible — **intentionally unchanged**

Issue #39 originally proposed skipping `_apply_unmet_need_cost` during sleep, exclusive social actions, or empty bowls. **This PR does not implement that.** An unmet need keeps spending energy at `rate × dt` even when the animal cannot drink or eat (including a real sleep bout). That cost can be fatal; waking uses penalty-band thresholds (item D) so relief is possible before exhaustion.

**Regression lock:** `test_unmet_need_still_costs_energy_while_asleep` — thirst 0.70, real need bout, energy drops by `UNMET_THIRST_ENERGY_PER_S * dt` at both 0.25 s and 2.5 s steps.

### C. Availability vs penalty thresholds (dead zone removed)

**File:** `colony_agent.py`

| Constant | Value | Role |
| --- | --- | --- |
| `HUNGER_AVAILABILITY_THRESHOLD` | 0.50 | `_needs_eat_action`, resource acquire |
| `THIRST_AVAILABILITY_THRESHOLD` | 0.48 | `_needs_drink_action`, resource acquire |
| `HUNGER_NEED_THRESHOLD` | 0.60 | unmet-need hunger penalty |
| `THIRST_NEED_THRESHOLD` | 0.58 | unmet-need thirst penalty |

Below availability: no portion relief (PR #36 rule unchanged). Between availability and need threshold: eat/drink work; penalty not yet applied.

### D. Sleep trap (`_sleep_entered_by_need`, `_must_wake_to_drink_or_eat`)

**File:** `colony_agent.py`

- `_sleep_entered_by_need`: set when a bout opens at real onset (`wake >= SLEEP_WAKEFULNESS_THRESHOLD` 0.7). Voluntary `sleep` below onset becomes `rest` and does not discharge Process S (overlaps [fix-colony-no-rest.en.md](fix-colony-no-rest.en.md)).
- `_should_continue_sleeping()`: only true for a need-opened bout above hysteresis resume (`0.7 × 0.7 = 0.49`) and not overridden by wake-to-drink/eat.
- `_must_wake_to_drink_or_eat()`: true when thirst ≥ 0.58 or hunger ≥ 0.60 **and** wake &lt; `SLEEP_CRITICAL_THRESHOLD` (0.9). Uses penalty thresholds, not `THIRST_CRITICAL_THRESHOLD` (0.82) / `HUNGER_CRITICAL_THRESHOLD` (0.85), because at 0.025 energy/s exhaustion precedes those constants.
- When `_must_wake_to_drink_or_eat()` and sleeping / need bout: `_wake_from_sleep()` runs **before** perceive/decide so drink/eat is possible on the same tick.
- **Process S ≥ 0.9** keeps the night: `_must_wake_to_drink_or_eat()` is false; waking would skip recovery and risk sleep-deprivation death on the same tick.

**Storage:** `colony_storage.py` persists `sleep_entered_by_need` and `_body_step_carry` on save/load.

### E. dt-invariant metabolism and sleep recovery

**Metabolism:** `_resource_metabolism_step` accumulates `dt`; `while _metabolism_tick >= 1.0 - 1e-9` subtract 1.0 and call `_apply_metabolism_second()` (slack avoids float loss on ten × 0.1 s steps).

**Body:** `_advance_autonomous_body` applies full `COLONY_BODY_STEP_S` (1/12) slices from `_body_step_carry` remainder (see fix-colony-no-rest).

**Sleep recovery:** `_sleep_recovery_duration_s(dt) = dt * SLEEP_RECOVERY_DURATION_FACTOR` (22.0). `SLEEP_MIN_RECOVERY_DURATION_S` (30) is documented as historical only — not applied per tick.

---

## 4. Constants (summary)

| Name | Value |
| --- | --- |
| `SimulationRunner.MAX_TICK_DT` | 0.25 |
| `HUNGER_AVAILABILITY_THRESHOLD` | 0.50 |
| `THIRST_AVAILABILITY_THRESHOLD` | 0.48 |
| `HUNGER_NEED_THRESHOLD` (penalty) | 0.60 |
| `THIRST_NEED_THRESHOLD` (penalty) | 0.58 |
| `UNMET_HUNGER_ENERGY_PER_S` | 0.02 |
| `UNMET_THIRST_ENERGY_PER_S` | 0.025 |
| `UNMET_SLEEP_ENERGY_PER_S` | 0.02 |
| `SLEEP_WAKEFULNESS_THRESHOLD` | 0.7 |
| `SLEEP_CRITICAL_THRESHOLD` | 0.9 |
| `SLEEP_RECOVERY_DURATION_FACTOR` | 22.0 |
| `HUNGER_ACCUMULATION_PER_S` | 0.0035 |
| `THIRST_ACCUMULATION_PER_S` | 0.0045 |
| Metabolism accumulator slack | 1e-9 |
| HUD lag display threshold | `achieved_ratio < 0.85` |

---

## 5. Acceptance criteria

1. At load-adapted ×1 (`dt = 0.25`) and ×10 (`dt = 2.5`), the same simulated interval yields the same number of `sim_step` calls per agent (decisions per simulated second match on the 5 s check).
2. Hunger and thirst after 10 s sim match for fine (`0.1` s) and coarse (`2.5` s) step schedules when not eating.
3. Eat/drink relieve needs in the band between availability and penalty thresholds; penalty still scales as `rate × dt` at 1/12 vs 2.5.
4. Voluntary sleep below onset does not trap; need bout wakes on penalty-band thirst/hunger unless Process S ≥ 0.9.
5. Seed 7, four founders, 600 s at `dt = 2.5`: zero exhaustion deaths.
6. Item B: unmet thirst during a real sleep bout still deducts `0.025 * dt` energy.
7. Save/load preserves `_sleep_entered_by_need` and `_body_step_carry`.
8. `test_tc01_two_agents_survive_300s` xfail for #39 removed when the suite passes.

---

## 6. Tests

**Primary file:** `Demo/Colony chinchillas/tests/test_colony_dt_invariance.py` (items A, C, D, E, B regression).

**Companion:** `tests/test_fix_colony_no_rest.py` (onset bout, long-run seed 2 at 10×).

### 1× vs 10× reference numbers (from PR #48)

| Check | 1× | 10× |
| --- | --- | --- |
| Decisions in 5 s, load step 0.25 vs 2.5 | 20 (4.0 / s) | 20 (4.0 / s) |
| Decisions in 5 s, nominal 1/12 vs 10/12 | 61 (12.2 / s) | 24 (4.8 / s) |
| Hunger / thirst after 10 s, not eating | 0.235 / 0.245 | 0.235 / 0.245 |
| Forced explore, 12 s, hunger / thirst / energy | 0.292 / 0.274 / 1.0 | same, delta 0 |
| Seed 7, 4 founders, 600 s at `dt = 2.5` | — | 0 deaths |
| Seed 7, 4 founders, 90 s at `1/12` and `2.5` | alive, min energy &gt; 0.2 | alive, min energy &gt; 0.2 |
| Seed 2, 4 founders, 1600 s at `dt = 2.5` | — | alive, asleep at end; pellets 0.389, hay 1.0, water 0.73 |

### Relaxed pellets bound (`test_founders_do_not_die_of_exhaustion_at_10x`)

After correct once-per-second metabolism and earlier eat availability, seed 2 at 1600 s × 10× draws the pellet bowl down further than the old once-per-tick metabolism. Measured `food_pellets ≈ 0.389` (hay 1.0, water 0.73). The assertion was relaxed from `> 0.4` to **`> 0.2`** so the run still proves no exhaustion while allowing realistic consumption. Hay remains `> 0.5`, water `> 0.4`, all agents `energy > 0.2`, someone sleeping.

### Test map

| Test | Item |
| --- | --- |
| `test_a_large_tick_splits_into_quarter_second_decisions` | A |
| `test_a_decision_rate_matches_at_1x_load_and_10x` | A |
| `test_a_nominal_10x_does_not_collapse_to_one_decision` | A |
| `test_speed_line_shows_actual_rate_when_sim_lags` | A (HUD) |
| `test_c_eat_and_drink_relieve_before_the_penalty` | C |
| `test_c_penalty_still_starts_at_the_need_threshold_for_both_steps` | C |
| `test_d_voluntary_sleep_does_not_trap_at_either_speed` | D |
| `test_d_need_bout_continues_until_resume_threshold` | D |
| `test_d_penalty_band_thirst_wakes_a_need_bout_at_both_speeds` | D |
| `test_d_critical_sleep_still_outranks_thirst` | D |
| `test_unmet_need_still_costs_energy_while_asleep` | B (unchanged) |
| `test_e_hunger_and_thirst_match_across_step_sizes` | E |
| `test_e_sim_step_needs_match_at_1x_and_10x_when_not_eating` | E |
| `test_seed7_founders_do_not_die_of_exhaustion_at_10x` | integration |
| `test_founders_survive_the_same_interval_at_1x_and_10x` | integration |
| `test_sleep_flag_and_body_carry_roundtrip` | D + storage |
| `test_founders_do_not_die_of_exhaustion_at_10x` (`test_fix_colony_no_rest.py`) | long run + pellets bound |

---

## 7. Performance at 10x

Commit `df816c895d561b2ea4b719be59b763bfb284e55d` (PR #48). Behavioral correctness at 10× was already fixed by items A–E; the colony was still slow because **each sub-tick runs one full decision per chinchilla**, and a full hippocampus (capacity 1024) on every decision scanned every signature, scored eviction, decayed every trace, and summed recall impulse per activated episode. Rendering was already once per frame; pygame never ranked in the top 20 under cProfile.

**Principle:** biological fidelity is preserved — no sampling, no coarser decay, no shortcut eviction; sleep consolidation and two-tier plasticity unchanged; item B unchanged; no GPU; `src/` stays stdlib-only. `MAX_TICK_DT` remains 0.25; capacity remains 1024; `activate` and `store` still run on every decision.

### Profiling before and after (4 vCPU, 4 founders, noisy)

| Run | Before | After |
| --- | --- | --- |
| Headless `tick(2.5)` (~800 memories) | **2.5–2.7×** (20 sim s / 8.1 s wall) | **6.66×** (15.0 sim s / 2.253 s; ticks 345–398 ms; holding 10× needs ≤250 ms/tick) |
| GUI `bench_speed.py`, 10×, 8 s | **5.10×** sim while HUD read **×10.0** (50 ms frame cap discarded stall time) | **8.09×** (sim 65.8 s / wall 8.1 s; HUD **×8.70**; 27 ticks; memory 1024) |
| GUI `bench_speed.py`, 1×, 8 s | — | **0.98×** (sim 7.8 s / wall 8.0 s; HUD ×1.00; 33 ticks) |

Before: cProfile on 10 sim s at ~840 memories took 12.7 s wall; top cumulative costs included `activate` 5.3 s, affective `step` 2.8 s, `commit` 2.4 s, context similarity 2.2 s, `store` 1.8 s, decay 1.6 s, signature rebuild 1.4 s. At capacity the profiler showed the eviction cliff (`store` / `enforce` / novelty / `activate`).

After (hippocampus 1024/1024): one profiled `tick(2.5)` 0.824 s wall (inflated vs ~0.35–0.40 s unprofiled). Cumulative: `Agent.step` 0.40 s, `commit` 0.31 s, `store` 0.18 s, `activate` 0.15 s, `enforce` 0.11 s, body 0.10 s, novelty 0.09 s, decay 0.09 s, recall 0.07 s.

### Root cause (demo host × memory core)

Sub-ticking (item A) fixed decision *rate* but multiplied work: a 2.5 s frame becomes ten 0.25 s sub-ticks × four agents × full `Agent.step` each. The dominant cost was hippocampus maintenance and recall on every decision, not pygame.

### Equivalence-preserving optimizations

| Area | File(s) | Change |
| --- | --- | --- |
| Feature scan | `src/hippocampus.py` | Bitmask Jaccard (`_mask_jaccard`) matches set Jaccard; per-query feature similarity cache; `activate` uses drive `(1, 0, 1)` with drive similarity stored on the signature; **safe threshold pruning** skips a signature only when `0.80 × feature + 0.15 × drive + 0.05` is already below threshold (upper bound — context ≤ 1) |
| Decay | `src/hippocampus.py` | `_decay_factor_for`: same blend `0.90 × 0.5**(elapsed/half_life) + 0.10 × (1−decay_rate)**(elapsed/half_life)`, clamped 0..1; **one factor per distinct `last_decay_ts`**; applied on every decay call — a 2.5 s gap is `factor(2.5)`, not ten `factor(0.25)` products; prune walk only when a weight can fall under activation threshold |
| Eviction | `src/hippocampus.py` | Same score (novelty blend, novelty, reinforcement, last activation, stable index); chronological order; overflow of one episode uses linear minimum → **same victim as full sort**; incremental novelty window; runner-up promoted only on equal similarity |
| Recall | `src/hippocampus.py`, `src/affective_space.py` | One impulse per activated trace, same per-impulse and L2 caps; `constrained_recall_from_experiences` sums in **one pass** for `decision_only`; core axis tuples cached on impulse and trace |
| Intent recency | `src/intent_memory.py` | Still `2**(-age/half_life)`; one `time.time()` per table |
| Selector | `src/selector.py` | Caches action names on episode (real tuple only — `Mock` not treated as cache) |
| Agent ids | `src/agent.py` | Episode ids O(1) when index complete; rebuilt after reload clears index |
| HUD clock | `Demo/Colony chinchillas/src/colony_gui/app.py` | `SIM_FRAME_DT_CAP_S = 1.0` credits real frame time to sim accumulator; sprite smoothing still `MAX_FRAME_DT_S = 0.05`; `note_sim_pace` uses raw frame so HUD cannot show 10× while discarding slow-tick wall time |

**Bench:** `Demo/Colony chinchillas/tools/bench_speed.py` replays GUI catch-up pacing.

### Verification

- **Equivalence:** `tests/test_memory_speed_equivalence.py` — closed-form decay (including that one 2.5 s gap ≠ product of ten 0.25 s factors), `activate` vs full similarity scan, eviction vs full score sort, recall vs one impulse per episode, same actions / episode state / affect for load 1× step (`dt = 0.25`) vs 10× frame split into ten such steps.
- **Full suite:** `python -m pytest -q` — **1924 passed, 11 skipped** (~14 min 47 s after these edits). Colony `test_colony_dt_invariance.py`: 16 passed.

### Rejected options (would change results)

| Option | Why rejected | Expected gain on reference VM |
| --- | --- | --- |
| Skip decay when gap &lt; `1e-4` of half-life (~0.36 s at 3600 s) | Energy and eviction weights change | Decay ~76 ms tottime inside one profiled `tick(2.5)` |
| Top-k recall or drop traces | Hundreds of 1024 episodes match above 0.20 on colony queries; decisions would change | Recall+affect ~100–200 ms / 10 sim s (early); one-pass recall ~74 ms cumulative on one `tick(2.5)` |
| Skip zero feature-overlap signatures | Threshold 0.20 reachable from drive+context alone (`0.15 + 0.05`); safe bound fired on 0/1024 | No measured saving |
| Oldest-only eviction or capped novelty scan | Different dropped episode | Enforce + novelty ~0.11 s + ~0.09 s on one `tick(2.5)` |
| Collapse body slices into one `autonomous_tick(dt)` | Rest and energy change, including unmet-need cost (item B) | Body path ~0.10 s cumulative on same tick |
| GPU (torch / cupy) | Not a numeric kernel; launch overhead; new dependency forbidden in `src/` | None expected |
| Raise `MAX_TICK_DT`, skip `activate`/`store`, lower capacity, share one `Agent` | Decision rate or who learns changes | Would remove most per-decision cost; not measured as an option |

A machine that sustains `tick(2.5)` ≤ 250 ms wall can hold requested 10×; the reference VM at full hippocampus does not reliably sustain 10×.

---

## 8. Out of scope / open questions

- Food or `rest` restoring energy; low-energy bias toward rest/sleep (demo design).
- Core physiological bias scale vs BG `pressure_vector` (separate measurement).
- Retuning unmet-need rates or implementing issue #39 item B (penalty waiver when impossible).
