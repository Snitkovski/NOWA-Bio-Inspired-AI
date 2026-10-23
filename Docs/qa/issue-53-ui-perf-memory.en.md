# QA issue #53 — colony UI rate and episode memory

Branch: `team/issue-53-ui-perf-memory` @ `dbc351b` (code under test; this note is the next commit).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/55
Issue: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/issues/53
Baseline: `main` @ `c3bbd62` (merge-base, PR #48).
Russian: [issue-53-ui-perf-memory.ru.md](issue-53-ui-perf-memory.ru.md).
Scope: read-only check of the two commits on this branch. Product code was not changed. No `Docs/specs/` pair for issue #53 exists in the tree.

Machine: Python 3.12.3, pygame 2.6.1, pytest 9.1.1. Not the machine behind the ~8x figure in the issue.

## Verdict

**FAIL**

Fresh runs match `main` when the clock is held still: actions, positions, episode features, rewards, recall, decay, eviction, and one sleep are the same, capacity stays 1024, `MAX_TICK_DT` stays 0.25, and an unmet need still spends energy. Same-version `copy`, `deepcopy`, and pickle round-trip. The full suite is green.

A core save written on `main` does not open on this branch (`AttributeError` on `Path`). That is a broken upgrade of `AgentStorage`. Colony JSON saves do not store episodes and are outside this failure.

## Coverage

| Check | Result |
| --- | --- |
| Biology not simplified; subticks and `MAX_TICK_DT=0.25` kept | Pass |
| `tick_history` trimmed to 1; no reader of older ticks | Pass |
| `__slots__` writes, same-version pickle / copy / deepcopy | Pass |
| Load of a `main` pickle on this branch | **Fail** |
| 9 agents, seed 7, 1x step 0.25 s and step 2.5 s vs `main` | Pass (frozen clock, identical hash) |
| `abs=1e-4` on the colony test | Justified for the wall-clock gap the test measures |
| Each chinchilla is its own `Agent` | Pass |
| SDL dummy: language, card click, pause, +/- speed, panel cache | Pass |
| Mouse-wheel scroll under SDL dummy | Driver cannot move the pointer; the same handler scrolls on display `:1` |
| `bench_speed.py --agents 9` on `main` and the branch | Measured |
| `python3 -m pytest -q` | **1930 passed, 11 skipped, 26 warnings**, exit 0, 1422.72 s |
| `test_founders_do_not_die_of_exhaustion_at_10x` (hay about 0.5) | Did not fail on this run |

### 1. Biology and the 1x / 2.5 s clock

`git diff c3bbd62...dbc351b` does not touch `MAX_TICK_DT`, hippocampal capacity, recall, decay, eviction, sleep consolidation, or the labile layer. `SimulationRunner.MAX_TICK_DT` is still 0.25. A 2.5 s colony tick is 10 subticks; 60 s at `dt=0.25` and at `dt=2.5` both take 240 `_tick_once` calls.

Nine `ChinchillaAgent`s, seed 7, `PYTHONHASHSEED=0`, `time.time` fixed at 1_700_000_000. Final state SHA-256 is the same on `main` and on the branch, for both step sizes:

`c8f1d7e6770e7d715cd4aff8a71054b2bef3b16dd702050372be862de4ef8b90`

Actions, positions, episode counts, feature sets, rewards, and activation match with max abs delta 0. Each agent is its own `Agent`, with its own hippocampus and selector. Every hippocampus capacity is 1024.

Core dump with the same frozen clock (8 waking steps, `sleep(cycles=2)`, then 24 stores into a hippocampus of 16): actions, memory, affect, channel weights, and the 16 survivors match `main` byte for byte. Waking does not move Go/NoGo/habit weights. Eviction still keeps 16 of 24.

Unmet hunger at the need threshold, action `idle`, `dt=1`: energy 0.95 → 0.93, delta 0.02, equal to `UNMET_HUNGER_ENERGY_PER_S`. That function is not in the diff.

### 2. `tick_history`

`TICK_HISTORY_RETAIN = 1`. Grep of `tick_history` across the repo (code and docs):

- `src/autonomous_organism.py` appends the new tick and drops the tail.
- `src/gui.py` reads only `tick_history[-1]` (physiology mode and the latest tick fields).
- `src/agent.py` `restore_autonomous_state` clears the list and sets `_completed_ticks = 0`. The saved count stays in `_autonomous_tick_count_offset`. `get_autonomous_state` adds that offset.
- Tests read the latest tick or assert length 1. Nothing walks older ticks for save/load, snapshot biology, diagnostics, or sleep.

Same-version organism save: 4 ticks, `len(tick_history)==1`, `get_autonomous_state()["tick_count"]==4`. After load the count is still 4. One more tick makes it 5. `runtime.snapshot()["tick_count"]` after that extra tick is 1, because the Tk view calls `runtime.snapshot()` and does not add the offset. The same split exists on `main` (there the snapshot count is `len(tick_history)`, which restore also clears). Not a new defect.

### 3. Slots, intern, pickle

`Experience`, `Event`, and `Path` use `__slots__`. `SignatureTrace` and `EmotionalTrace` use `dataclass(slots=True)`. Names of events and feature tokens of length ≤ 80 are interned (`ctx:nest` is one `str`).

An AST pass over attribute assignments to `exp` / `experience` / `episode` / `stored_experience` / `sig` / `best_sig` / `event` / `path` found no name outside the slot or field list. The Warriner seeder sets `warriner_word`, `warriner_valence_norm`, `warriner_arousal_norm`, `warriner_dominance_norm`, `warriner_seed_events`, all present on `Experience`. `IntentTrace` and `AffectiveTrace` are other classes and are not slotted here.

Same-version `copy.copy`, `copy.deepcopy`, and pickle succeed for `Event`, `Path`, `Experience` (with an emotional trace), `EmotionalTrace`, `SignatureTrace`, and `NOWAHippocampus`. The restored path, reward, activation, and impulse intensity match. The full pytest run raised no `AttributeError` from a missing slot.

### 4. Colony float tolerance `abs=1e-4`

`tests/test_issue53_trajectory_and_gui.py` compares actions and positions with equality. Floats (energy, hunger, thirst, stress, activation, weight, reward) use `pytest.approx(..., abs=1e-4)`. The comment attributes that to wall-clock decay.

With `PYTHONHASHSEED=0` and a live clock, back-to-back runs:

| Comparison | Actions / positions | Max abs float |
| --- | --- | --- |
| 3 agents, 2.5 s, `dt=0.25` vs `dt=2.5` (the test shape) | match | 3.7e-7 |
| 9 agents, 2.5 s, `dt=0.25` vs `dt=2.5` | match | 1.1e-6 |
| 9 agents, 30 s, `dt=0.25` vs `dt=2.5` | match | 5.9e-5 |

The allowance is about 270× the 2.5 s gap and still above the 30 s gap. It does not hide an action or position change. A second 1x run started after those 30 s runs diverged (6 positions, 5 actions) because absolute `time.time()` had moved. That coupling is already on `main`: the frozen-clock hash above is identical on both commits. Two processes with different `PYTHONHASHSEED` also diverge; the committed test runs both colonies in one process, so it does not hit that.

### 5. GUI (SDL dummy, plus one display check)

`SDL_VIDEODRIVER=dummy`, 12 agents, `speed=1`, `wall_s=2.8`.

- 66 paints in 2.78 s (23.8 fps), under `RENDER_FPS_CAP` 30. Simulation advanced 1.88 s.
- `G`: language `en` → `ru`. Click on the EN button: `ru` → `en`.
- Click on the first card `(1139, 89)` opens the inspector for `gui-0`.
- Space holds `sim_time` at 0.230667 s across four paints. The next space resumes; sim time then moves.
- `=`: speed 1.0 → 2.0. `-`: 2.0 → 1.0.
- Right-panel cache: a second draw with the same inputs reuses the surface. Stress 0.10 → 0.90, energy 0.80 → 0.15, action `idle` → `eat`, language `en` → `ru`, and `scroll_offset` 0 → 48 all change pixels. Hit y moves by 48. Stress 0.10 → 0.104 keeps the surface: both values render as `0.10` (`f"{value:.2f}"` and `round(value, 2)`). The label is not stale.

Wheel scroll under dummy does not run: `pygame.mouse.get_pos()` stays `(0, 0)` after `set_pos` and after a posted `MOUSEMOTION`, and the handler ignores the wheel unless x ≥ `PANEL_RIGHT_X`. On display `:1` the same gesture (`y=-3`) sets `_right_panel_scroll` to 72. The handler is fine; the dummy pointer is not.

Cards during the live loop showed different actions and different stress/energy (for example drink 0.01/0.97 and wheel 0.02/0.96). The stats strip can still read "Agents: 0" until `observer.get_latest()` exists (`has_data` is false). The cache token includes that dict, so a later sample repaints. Not introduced by the surface cache.

### 6. Bench

Command, both trees: `python3 "Demo/Colony chinchillas/tools/bench_speed.py" --agents 9`.

Warmup stops at a full hippocampus or 60 s. Both filled 1024/1024 at sim 258 s (branch 50.9 s wall, `main` 49.8 s). RSS is the sampled peak of `VmRSS` (0.5 s), including child processes. `main`'s script has no GUI section; the branch script measures headless and the pygame loop.

## Defects

### [MAJOR] A core pickle from `main` does not load

Steps:

1. On `main` (`c3bbd62`), build an `Agent`, `hip.store` one path (`ctx:nest`, `action:go`), `AgentStorage.save_agent` to `from_main.pkl`.
2. On this branch, `AgentStorage.load_agent` of that file.

Expected: hippocampus restores, one episode, no exception.

Actual: `pickle.load` raises `AttributeError: 'Path' object has no attribute '__dict__'`.

Where: `src/storage.py` `load_agent` (`pickle.load`). `Path` in `src/experience.py` gained `__slots__` and no `__getstate__` / `__setstate__`. The same load of a `main` blob fails for `Experience`, `EmotionalTrace` (`src/affective_space.py`, `slots=True`), `SignatureTrace`, and `NOWAHippocampus`, all because the graph contains a `Path` or a slotted trace. `Event` has a custom state pair and was not the object that raised.

A pickle written on this branch loads on this branch (path, reward, activation, impulse) and, in this probe, also loads on `main`. Colony JSON (`colony_storage.py`) stores an experience count, not the episode objects.

### [MINOR] Issue #53 has no spec pair

The issue acceptance asks for `Docs/specs/` `.en.md` / `.ru.md`. The branch diff has no such pair. Behavior above was checked against the issue text and the PR body.

## Bench main vs branch

| Run | main `c3bbd62` | branch `dbc351b` |
| --- | --- | --- |
| Warmup | 49.8 s, sim 258 s, memory 1024/1024 | 50.9 s, sim 258 s, memory 1024/1024 |
| Headless 1x | 0.98x (sim 7.9 s / wall 8.0 s, 32 ticks) | 0.98x (sim 7.9 s / wall 8.0 s, 32 ticks) |
| Headless 10x | 2.64x (sim 23.5 s / wall 8.9 s, 10 ticks) | 2.86x (sim 23.5 s / wall 8.2 s, 10 ticks) |
| GUI 1x | not in the `main` script | 0.97x (sim 7.6 s / wall 8.0 s, 152 paints) |
| GUI 10x | not in the `main` script | 1.90x (sim 16.0 s / wall 8.6 s, 7 paints, sim 98.5% of the loop) |
| Peak RSS | 306792 KiB (299.6 MiB) | 228512 KiB (223.2 MiB) |
| RSS at process end | 306792 KiB | 227612 KiB (222.3 MiB) |

Peak RSS is 78280 KiB lower on the branch (−25.5%). Headless 1x matches. Headless 10x is 2.64x → 2.86x on this VM. GUI 10x stays simulation-bound (7 paints, 98.5% sim) and is not close to the headless 2.86x of the same run. These are not the PR's 4.47x / 3.76x / 191 MiB figures; those were a different measurement.

## Recommendations

1. Give `Path` (and any slotted type that pickle already persisted) a `__getstate__` / `__setstate__` that accepts the old `__dict__` payload, then load a `main` `AgentStorage` file in a test.
2. Add the missing `Docs/specs/issue-53-*.en.md` and `.ru.md` pair.
3. Do not treat `abs=1e-4` as slack for actions or positions. Keep those exact. The float band matches a short back-to-back wall-clock gap; it will not hold two runs separated by a long pause.
4. Re-measure GUI 10x on the machine that produced the issue's ~8x headless number before calling the speed acceptance met. On this VM the cap is in force and the frame is still the hippocampus.

## Release readiness

Not ready. Correctness against `main` and the suite are in place. Shipping cuts off existing core pickle saves until they load, or until that break is an explicit, documented decision.
