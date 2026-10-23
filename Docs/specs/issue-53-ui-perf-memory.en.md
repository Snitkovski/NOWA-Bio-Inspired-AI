# Issue #53 — Colony UI speed and episode memory: implementation spec

Closes #53. Baseline: `main` @ `c3bbd62` (merge-base after PR #48). QA: [issue-53-ui-perf-memory.en.md](../qa/issue-53-ui-perf-memory.en.md). Russian: [issue-53-ui-perf-memory.ru.md](issue-53-ui-perf-memory.ru.md).

Sub-ticking from issue #39 (`SimulationRunner.MAX_TICK_DT = 0.25`) stays. Hippocampal capacity (1024 per agent), recall, decay, eviction, sleep consolidation, and two-tier plasticity are unchanged. Each chinchilla remains its own `Agent`. Unmet-need energy cost is unchanged.

---

## 1. Problem

After PR #48, headless benchmarks on a well-provisioned machine reach roughly **8×** real speed at 10× acceleration. In the **Colony chinchillas** demo with the pygame UI and nine agents, observed speedup was only about **2–3×**, while long sessions held about **1 GB** RAM.

Rendering shaders did not change. Likely causes (verified on this branch):

1. **Single-thread coupling.** The GUI loop advanced simulation and painted on one thread; a slow hippocampus-bound tick blocked the next paint, and full repaints of the right-hand cards and stats strip ran every frame.
2. **Per-tick organism history.** `AutonomousOrganismAgent` appended a full tick dict to `tick_history` every step. Nine agents × thousands of ticks × ~5 KB per dict inflated RSS over a session.
3. **Episode object overhead.** `Experience`, paths, events, and traces used ordinary instances; repeated feature and event strings were not shared.

Issue #53 acceptance also requires a spec pair and a QA report with measured before/after numbers.

---

## 2. Goals and non-goals

### Goals

| Area | Target |
| --- | --- |
| UI at 10× | Decouple **paint rate** from **simulation catch-up**; cap interactive drawing; cache static and slowly changing UI surfaces. |
| Memory | Shrink per-episode and per-tick footprint **without** reducing hippocampus capacity or episode counts. |
| Equivalence | Same biology and trajectories as `main` at 1× and 10× (sub-tick semantics preserved). |
| Persistence | `AgentStorage` pickles written on `main` must load on this branch. |
| Measurement | `bench_speed.py` reports headless and GUI achieved speed plus RSS on the same colony. |

### Non-goals

- Moving simulation to a second thread or process (would break deterministic catch-up on the GUI thread).
- Retuning hippocampal algorithms, thresholds, or plasticity.
- Changing colony JSON save format (still stores experience counts, not episode graphs).

---

## 3. GUI: render cap and panel caches

**Files:** `Demo/Colony chinchillas/src/colony_gui/app.py`, `colony_gui/colony_gui.py` (read-model unchanged).

### 3.1 Fixed render cadence

- `RENDER_FPS_CAP = 30` — interactive window paints at most ~30 fps.
- `SIM_FRAME_DT_CAP_S = 1.0` — wall time fed into catch-up is not clipped to 50 ms, so 10× can use long steps when the CPU allows.
- Simulation substeps remain governed by `SIM_MAX_STEP_S = 0.25`, `SIM_MAX_CATCHUP_STEPS`, and `SIM_ACCUMULATOR_MAX_STEPS` (unchanged semantics from issue #39).
- Between paints the loop **continues** `_sim_tick` catch-up; a slow 10× session is simulation-bound rather than paint-bound.

**Exceptions (paint every iteration):** frame capture (`frame_dt_s`, `on_frame`, `max_frames`) and tests that pass those hooks.

High population still raises `target_fps` via `HIGH_POP_RENDER_FPS` / `VERY_HIGH_POP_RENDER_FPS`; at ≥90 agents the cap stays 30.

### 3.2 Caches

| Surface | Behavior |
| --- | --- |
| Cage background | Already cached (`static_scene`); unchanged. |
| Right agent cards | `_right_panel_cache_token(...)` — rebuild blit only when card inputs (metrics, action, language, scroll, selection, etc.) change. |
| Stats strip under cage | `_stats_panel_cache_token(...)` — same pattern for abundance, bars, and observer snapshot fields. |
| Label text | Existing `panel_text_surface_cache` / `name_surface_cache` retained. |

Skipped paints still advance sprite smoothing by accumulated `visual_elapsed_s`.

### 3.3 Profiling hook

`run_pygame_demo(..., frame_profile=profile)` fills wall-time buckets: `sim_s`, `snapshot_s`, `background_s`, `agents_s`, `labels_s`, `stats_s`, `panel_s`, `flip_s`, plus `paints` and `sim_advanced_s`. Used by `bench_speed.py` and `test_capped_pygame_loop_advances_simulation`.

---

## 4. Memory: slots, interning, tick history

### 4.1 Slotted episode graph

**Files:** `src/experience.py`, `src/affective_space.py`, `src/hippocampus.py`.

| Type | Mechanism |
| --- | --- |
| `Experience` | `__slots__` |
| `Event` | `__slots__` + custom `__getstate__` / `__setstate__` |
| `Path` | `__slots__` + pickle state |
| `SignatureTrace` | `@dataclass(slots=True)` |
| `EmotionalTrace` | `@dataclass(slots=True)` |
| `NOWAHippocampus` | slot layout + `__setstate__` for cache fields added on this branch |

Event names and feature tokens of length ≤ 80 are **interned** (`sys.intern`) via `_intern_short_token` / `_intern_token_collection` so shared tokens (e.g. `ctx:nest`) are one `str` object.

`IntentTrace` and `AffectiveTrace` are out of scope for this issue (not slotted here). Warriner seeder fields on `Experience` remain valid slot names.

### 4.2 `tick_history` retention

**File:** `src/autonomous_organism.py`

- `TICK_HISTORY_RETAIN = 1` — after each tick, drop older entries; only the latest tick dict remains.
- `get_autonomous_state()["tick_count"]` still reports total completed ticks via `_completed_ticks` and `_autonomous_tick_count_offset` after restore (`src/agent.py`).
- Readers: `src/gui.py` physiology view uses `tick_history[-1]` only; no save/load or diagnostics path walks older ticks.

**Known split (pre-existing on `main`):** Tk `runtime.snapshot()["tick_count"]` reflects `len(tick_history)` after restore, not the offset-augmented count.

---

## 5. Pickle compatibility with `main`

Round 1 on this branch failed to load `AgentStorage` blobs from `main` (`AttributeError: 'Path' object has no attribute '__dict__'` after `__slots__`).

**Fix (commit `4945e24`):** `__setstate__` on `Event`, `Path`, `Experience`, `EmotionalTrace`, `SignatureTrace`, and `NOWAHippocampus` accepts the legacy `__dict__` payload from pickles written before slots, as well as the slotted pickle layout. New hippocampus cache fields default to empty when absent.

**Regression assets:**

- Fixture: `tests/fixtures/agent_from_main_c3bbd62.pkl` (agent saved on `main` @ `c3bbd62`).
- Tests: `tests/test_main_pickle_compat.py` (load fixture, round-trip on branch, frozen-clock behavior after load).

Pickles written on this branch load on `main` in QA probes. Colony JSON saves are unaffected.

---

## 6. Biology equivalence guarantee

Optimizations are **implementation-only** (memory layout, indexing, shared decay factors). Formulas for Jaccard overlap, decay, eviction ordering, and recall impulses are locked by tests.

**Trajectory lock (nine agents, seed 7, `PYTHONHASHSEED=0`, `time.time` fixed at `1_700_000_000`, 60 s sim):**

Final-state SHA-256 on `main` and on this branch (both `dt=0.25` and `dt=2.5`):

`c8f1d7e6770e7d715cd4aff8a71054b2bef3b16dd702050372be862de4ef8b90`

Max absolute delta 0 for actions, positions, episode features, rewards, and activation. Hippocampus capacity remains 1024 per agent. `MAX_TICK_DT` and sub-tick counts unchanged (60 s at 0.25 s vs 2.5 s → same number of `_tick_once` calls).

`git diff c3bbd62...dbc351b` does not modify hippocampal recall/decay/eviction/sleep logic or the labile layer.

---

## 7. Benchmark tool

**File:** `Demo/Colony chinchillas/tools/bench_speed.py`

- Warms the colony at 10× until every hippocampus is full (1024 episodes) or `--warmup-wall` (default 60 s) elapses.
- **Headless:** same catch-up math as the GUI (`_sim_tick`, load adaptation) without pygame paint.
- **GUI:** `run_pygame_demo` with SDL dummy driver (`SDL_VIDEODRIVER=dummy`).
- Prints achieved multiplier = simulated seconds / wall seconds (matches HUD “actual x”).
- `--agents N` (default 4; QA used `--agents 9`). `--headless-only` skips GUI section.

Command:

```bash
python3 "Demo/Colony chinchillas/tools/bench_speed.py" --agents 9
```

---

## 8. QA measurements (independent VM)

Source: [issue-53-ui-perf-memory.en.md](../qa/issue-53-ui-perf-memory.en.md) (Python 3.12.3, pygame 2.6.1; **not** the machine behind the ~8× headless figure in issue #39).

Compared `main` @ `c3bbd62` vs branch @ `dbc351b` after warmup to 1024/1024 episodes:

| Metric | `main` | Branch |
| --- | --- | --- |
| Peak RSS | 299.6 MiB (306792 KiB) | 223.2 MiB (228512 KiB) |
| Headless 10× achieved | 2.64× | 2.86× |
| Headless 1× achieved | 0.98× | 0.98× |
| GUI 10× achieved | (not in `main` script) | 1.90× (7 paints; **sim 98.5%** of loop wall time) |
| GUI 1× achieved | — | 0.97× |

Peak RSS on the branch is **78280 KiB lower (−25.5%)**. GUI 10× remains simulation-bound on this VM; render cap is active (QA: 23.8 fps over 2.78 s under cap 30).

Round 2 (`4945e24`) re-verified trajectory hash and `main` pickle load. Full pytest: **1932 passed**, 1 failed (see §9).

---

## 9. Tests

| Test module | Role |
| --- | --- |
| `Demo/Colony chinchillas/tests/test_issue53_trajectory_and_gui.py` | Same-seed trajectories; 10×0.25 s vs 1×2.5 s equivalence (`abs=1e-4` on floats only); capped pygame loop advances `sim_time`. |
| `tests/test_memory_speed_equivalence.py` | Decay, eviction, recall sums, impulse mapping vs reference formulas; pickle round-trip of slotted types. |
| `tests/test_main_pickle_compat.py` | Load `agent_from_main_c3bbd62.pkl`; branch round-trip; post-load `step` / `sleep` / `activate`. |
| `tests/test_autonomous_organism.py` | `tick_history` length 1 with correct `tick_count` across save/load. |

**Flaky (pre-existing, not a regression of this branch):** `Demo/Colony chinchillas/tests/test_fix_colony_no_rest.py::test_founders_do_not_die_of_exhaustion_at_10x` — founders built without `rng_seed`; bowl hay level is non-deterministic. QA round 2: one full-suite failure (hay 0.4846 < 0.5), immediate re-run passed; not filed as a new defect.

---

## 10. Files touched (summary)

| Path | Change |
| --- | --- |
| `Demo/Colony chinchillas/src/colony_gui/app.py` | Render cap, panel/stats caches, `frame_profile`, sim/paint decoupling |
| `Demo/Colony chinchillas/tools/bench_speed.py` | Headless + GUI measurement, RSS sampling |
| `src/experience.py`, `src/affective_space.py`, `src/hippocampus.py` | Slots, interning, pickle `__setstate__` |
| `src/autonomous_organism.py`, `src/agent.py` | `TICK_HISTORY_RETAIN`, tick count offset |
| `tests/*`, `tests/fixtures/agent_from_main_c3bbd62.pkl` | Equivalence, pickle compat, organism history |

---

## 11. Related documents

- Issue: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/issues/53
- PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/55
- QA report: [issue-53-ui-perf-memory.en.md](../qa/issue-53-ui-perf-memory.en.md)
- Sub-tick host behavior: [issue-39-dt-robustness.en.md](issue-39-dt-robustness.en.md)
