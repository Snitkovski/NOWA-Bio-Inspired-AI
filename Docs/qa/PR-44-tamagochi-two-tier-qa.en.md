# QA PR #44 — Tamagochi demo on two-tier plasticity

Branch: `team/demo-tamagochi-two-tier`. Round 2 reviews `7442837`. Round 1 reviewed `bcf4f16`.
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/44
Base: `origin/main` @ `8971960`.
Specs: `Docs/specs/issue-13-two-tier-plasticity.en.md`, `Docs/architecture/two-tier-plasticity.en.md`, `Docs/specs/issue-13-demo-tamagochi.en.md`.

## Round 2 — verdict

**PASS**

Commit `7442837` closes the three round-1 defects. Regression tests in `Demo/Tamagochi Chinchilla/tests/test_two_tier_host.py` fail if any of them comes back. `git diff --stat origin/main...HEAD -- src` is empty. Product code was not edited in this pass.

### The three fixes

1. Habit capture. `SleepManager` is constructed with the cage `intent_memory` (`main.py:532`) and `_rewire_two_tier_host` sets the same object (`:1056`). Probe: `sleep_manager.intent_memory is agent.intent_memory`. A strength-0 `note_selection(["idle"], "eating_and_grooming")` is still present after `_run_sleep_consolidation`, strength `0.0907` (floor is `0.08`). `test_sleep_capture_applies_intent_outcome` asserts the identity and `max(strength) > 0`.

2. One channel write. `apply_sleep_learning` and `consolidate_habits` are gone (zero call sites). After `deep_sleep` the cage only flushes owner ratings (`:3344-3350`). Probe, channel `eating_and_grooming` from the committed save: before `(go 0.523348, nogo 0.454799, habit 0.046013)`; after `deep_sleep` and after `_run_sleep_consolidation` the same object and the same weights `(0.599256, 0.418173, 0.227433)`. Capture still moves the weights. `test_deep_sleep_is_the_only_channel_writer` asserts object id and the three weights are unchanged across that boundary.

3. Waking `record_trace` is gone. Chain start calls `note_selection` (`:1823-1826`) and does not catch `Exception`. New traces stay at strength 0. `fail_if_waking_learning_error_was_caught` (`test_two_tier_host.py:17-40`) counts `WakingLearningError` even when a caller swallows it. `test_chain_start_does_not_write_stable_intent` starts a chain with `sim_step(0.1)`.

No new daytime stable writer. Search of `main.py`: no `record_trace`, no `strengthen_trace`, no `update_weights`, no `value_layer.update(mode="online")` call. `apply_learning_hooks` remains only inside `_flush_owner_feedback`.

### Consolidation still runs

Owner rating 5 is queued by `_apply_training_feedback` and does not change logits or `stable_fingerprint` while awake. `_run_sleep_consolidation` clears the queue. `strategy_logits` move (sample `eating_and_grooming` logit `0.08`). Softmax weights stay uniform because every logit moves together. Channel habit still moves inside `deep_sleep` (0.046013 → 0.227433).

### Both decays, one night

`deep_sleep(cycles=2)` runs `degrade_unused(0.8)` twice, then the cage runs `degrade_unused(0.85)` (`:3296`) after capture. Measured after the whole night: new outcome trace `0.0907`, a trace seeded at `0.2` also `0.0907`, a trace seeded at `0.6` is `0.2722`. All stay above `0.08`. They are not deleted on that night.

### Pytest

Python 3.12.3, pytest 9.1.1, repo root.

| Command | Result | Time |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **27 passed**, 15 warnings, exit 0 | 2.77 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **27 passed**, 15 warnings, exit 0 | 2.64 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **893 passed, 5 skipped**, 2 warnings, exit 0 | 194.57 s |

No `WakingLearningError` in the Tamagochi output. The 15 warnings are the same pre-existing `PytestReturnNotNoneWarning`.

### Remark

A single rewarded outcome ends at `0.0907`. The next `_run_sleep_consolidation`, with that episode already consolidated, deletes it: the first `degrade_unused(0.8)` drops it under `0.08`. A trace seeded at `0.6` is not in that band. The host test only asserts strength `> 0` after one night.

---

## Round 1 — verdict

**FAIL** at `bcf4f16`. Kept below as the record of that pass. Scope then: one read of the diff, the sleep-guard call graph, one daytime/sleep probe, and the pytest commands in this section. No full `Demo/` suite, no long sim, no seed loop. Product code was not edited.

`src/` is unchanged. Game `dt` reaches the core once per `sim_step`. `expected_wake_interval_s` is `10080` and matches the cage pressure constants. The new host test passes, and both Tamagochi pytest modes exit 0.

Three defects remain. Intent habits never receive the sleep outcome write. One deep sleep then applies a second Go/NoGo/habit update on the same channels. `IntentMemory.record_trace` is still called when a chain starts while awake; strict mode raises `WakingLearningError`, and the caller swallows it, so the suite stays green.

## Pytest

Python 3.12.3, pytest 9.1.1. Commands run from the repo root.

| Command | Result | Time |
| --- | --- | --- |
| `NOWA_STRICT_LEARNING=1 python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 warnings, exit 0 | 2.40 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest "Demo/Tamagochi Chinchilla" -q -p no:cacheprovider --tb=line` | **24 passed**, 15 warnings, exit 0 | 2.47 s |
| `env -u NOWA_STRICT_LEARNING python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **893 passed, 5 skipped**, 2 warnings, exit 0 | 190.55 s |
| `NOWA_STRICT_LEARNING=0 python3 -m pytest tests -q -p no:cacheprovider --tb=line` | **6 failed, 887 passed, 5 skipped**, 2 warnings, exit 1 | 190.34 s |

No `WakingLearningError` in the Tamagochi pytest output. The exception is raised and caught inside `sim_step` (defect 3); these two commands do not start a chain, because the committed save is mid-action (see the probe).

The 15 warnings are `PytestReturnNotNoneWarning` on older tests that `return True`. They are outside this diff.

### The six core failures are the forced-env artifact

`git diff --stat origin/main...HEAD -- src tests` is empty. The core suite at `bcf4f16` is the suite on `origin/main`.

`tests/conftest.py:10` does `os.environ.setdefault("NOWA_STRICT_LEARNING", "1")`. A process that already has `NOWA_STRICT_LEARNING=0` keeps `0`. The guard then skips the write and logs, and `pytest.raises(WakingLearningError)` fails. Each failure message is `Failed: DID NOT RAISE WakingLearningError`.

| Test | Assertion |
| --- | --- |
| `tests/test_issue13_two_tier.py::test_stable_fingerprint_is_unchanged_across_waking_calls` | `:93` |
| `tests/test_issue13_two_tier.py::test_direct_replay_does_not_open_the_learning_guard` | `:476` |
| `tests/test_issue13_two_tier.py::test_waking_guard_blocks_direct_stable_writes` | `:650` |
| `tests/test_qa_pr37_labile_layer.py::test_strict_guard_raises_and_production_skips_once` | `:357` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_named_guards_raise_in_strict_mode_and_skip_once_in_production` | `:422` |
| `tests/test_qa_pr40_sleep_consolidation.py::test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn` | `:536` |

With the variable unset, the same tree is **893 passed, 5 skipped**. These six are not a regression from this PR.

## Checklist

### 1. `src/` against `main` — pass

Diff of `bcf4f16` against `origin/main` is only:

- `Demo/Tamagochi Chinchilla/src/main.py`
- `Demo/Tamagochi Chinchilla/tests/test_two_tier_host.py`
- `Docs/specs/issue-13-demo-tamagochi.en.md`

### 2. Daytime stable writes — fail

Removed from the waking path, confirmed in the diff and by search of `main.py`: `value_layer.update(mode="online")` (comment only, `:1454`), `strengthen_trace`, `update_weights`, and a direct `apply_learning_hooks` on the rating click.

`apply_learning_hooks` remains only in `_flush_owner_feedback` (`:2085`). Callers are the light-sleep branch (`:1710`) and `_run_sleep_consolidation` (`:3372`). `_apply_training_feedback` (`:1978`) appends to `_pending_owner_feedback` and does not call it.

`learning_allowed()` blocks:

| Block | Reached from |
| --- | --- |
| `:1707-1711` flush, then `sleep_cycle()` | `sim_step` only when `is_light_sleep` (`:1700`) |
| `:3296-3298` habit modulation and `degrade_unused` | `_run_sleep_consolidation` |
| `:3371-3382` flush, `apply_sleep_learning`, `consolidate_habits` | `_run_sleep_consolidation` |

`_run_sleep_consolidation` is called from production code only at `:1699`, inside `is_deep_sleep`. The test calls it directly. These three wrappers are not on the waking path.

`initializing()` wraps channel restore (`:3536-3552`) and the fallback `ActionChannel` (`:2466-2469`). `nowa.register_action_channel` (`:2463`) enters `initializing()` in the core (`src/agent.py:2830-2832`).

Defect 3: `record_trace` at `:1823` is still a waking call.

### 3. `dt` once, wake interval `10080` — pass

`sim_step` calls `nowa.advance_time(_host_dt(dt))` once (`main.py:1114-1115`). There is no second `advance_time`, no `Agent.step`, and no `commit_executed_transition`. `Agent.advance_time` uses `_advance_host_clock(..., wall_fallback=False)` (`src/agent.py:4627-4629`). Non-finite or negative `dt` becomes `0` in `_host_dt` (`main.py:292-299`).

`tamagochi_expected_wake_interval_s` (`:276-289`) returns `_SLEEP_ONSET_PRESSURE / _WAKE_PRESSURE_RATE` = `0.7 / (1/(4*3600))` = `10080`. The cage installs that rate on `WakefulnessState` (`:430-432`). Bedtime pressure is boosted when wake pressure exceeds `0.7` (`:2581-2582`). The constructor starts at `0.1` (`:431`), so the first climb is `(0.7-0.1)*14400` = `8640` s. `SchedulingSystem()` keeps the default `cycle_period` of `1200` (`scheduling_system.py:77`, constructed at `main.py:394`). Recovery is `1/(2*3600)` (`:433`); `960` s of `sleep_house` (`config.py:224`) drops pressure by at most `960/7200` ≈ `0.133`. No other `PlasticityConfig` field is set. `src/` is untouched, so core coefficients are not retuned.

`test_two_tier_host.py` asserts the interval, `+4` on `_host_clock_s`, `_dt_warning_sent is False`, an unchanged fingerprint after four `sim_step(1)` and one waking outcome, and a changed fingerprint after `_run_sleep_consolidation`. That test passed inside the 24.

### 4. Shared `nowa` with `sleep_manager=None` — fail

`_bind_two_tier_host` builds `Agent(..., sleep_manager=None)` (`:979-987`), so `Agent.__init__` does not attach its private value layer to the cage manager (`src/agent.py:160-174`). `_rewire_two_tier_host` (`:991-1053`) then points `nowa` at the cage `value_layer`, `bg_channels`, and `sleep_manager`, and sets `labile`, `plasticity`, and `_host_agent` on that manager.

Probe after `ChinchillaAgent(...)` (loads the committed `Demo/Tamagochi Chinchilla/saves/nowa_state.json`): `nowa.bg_action_channels`, `agent.bg_channels`, and `sleep_manager.bg_action_channels` are one dict; the three value layers are one object; `nowa.sleep_manager` is the cage manager. `deep_sleep` therefore runs `_consolidate_two_tier_once` on the cage channels. Q replay is that `deep_sleep`, not a second `Agent.sleep`. `Agent.sleep` is not called.

`SleepManager` is constructed without `intent_memory` (`:529-534`). Rewire does not set it. `nowa.intent_memory` is the cage object, and `sleep_manager.intent_memory` stays `None`. Core habit EMA reads the manager (`src/sleep.py:2921-2928`) and does not run. Defect 1.

After that capture, the cage calls `apply_sleep_learning` and `consolidate_habits` on the same channels and replaces the dict entries (`:3371-3384`). Defect 2.

### 5. Tests — pass, with defect 3 hidden by `except`

Both Tamagochi modes and the default core run passed. The six `NOWA_STRICT_LEARNING=0` failures are the conftest artifact above. The suite does not fail on defect 3 because `record_trace` is inside `except Exception` (`:1828`).

### 6. Fingerprint day vs sleep — pass as written

`test_waking_ticks_hold_stable_tier_until_sleep` passed. It does not read intent-trace strength and does not compare channel weights after `deep_sleep` with weights after the cage BG block. Those two gaps are defects 1 and 2.

### 7. Spec vs code — fail on the two sleep writers

Matching: host is not an `Agent` subclass; `sleep_manager=None` then rewire; one `advance_time` per tick; interval `10080` and the `8640` / `1200` / `0.133` figures; waking chain outcome goes through `_record_known_outcome`; owner ratings are queued; channel restore and `register_action_channel` use `initializing()`; `deep_sleep(cycles=2)` and one `sleep_cycle` are the schedule; `src/` is unchanged.

Not matching: spec §3 says `note_selection` leaves strength 0 until sleep. Sleep does not run `apply_outcome` on the cage memory, then `degrade_unused(0.85)` deletes the strength-0 trace (defect 1). Spec acceptance 5 says the suite must not raise `WakingLearningError`. `record_trace` raises it on a waking chain start (defect 3). The spec's "cage's own sleep writers" matches the second BG write being present; it does not say that write is a second Go/NoGo/habit step after core capture (defect 2).

## Defects

### 1. High — sleep never applies the intent outcome

`Demo/Tamagochi Chinchilla/src/main.py:529-534` and `:1044-1053`. Capture uses `src/sleep.py:2921`.

`SleepManager.intent_memory` is `None` for the life of the cage. `_apply_episode_channel_and_habit` therefore skips `IntentMemory.apply_outcome`. The daytime path now calls `note_selection` (`main.py:1580-1584`), which stores strength 0. `_run_sleep_consolidation` then runs `degrade_unused(0.85)` (`:3298`). Strength 0 is below `min_strength_for_trace` (0.1), so the trace is deleted. `stable_fingerprint` ignores strength `<= 0` (`src/learning_guard.py:124-126`), so the host test still passes.

Reproduce, from the repo root, with `NOWA_STRICT_LEARNING=1` and `src` plus `Demo/Tamagochi Chinchilla/src` on `sys.path`:

1. `agent = ChinchillaAgent(demo_dir="Demo/Tamagochi Chinchilla", use_pygame=False, use_gui=False)`.
2. Store one hippocampal episode for `eating_and_grooming` with reward `1.0`, call `_commit_waking_chain_outcome` with that episode, and `note_selection(["idle"], "eating_and_grooming")`.
3. Observe `sleep_manager.intent_memory is None` and the new trace strength `0.0`.
4. Call `_run_sleep_consolidation`.

Observed: after `deep_sleep` the trace strength is still `0.0`; after the cage degrade the key `eating_and_grooming:ec2f993a` is gone.

### 2. Medium — one deep sleep writes Go/NoGo/habit twice

`Demo/Tamagochi Chinchilla/src/main.py:3199` then `:3371-3384`.

`deep_sleep(cycles=2)` already runs the once-per-sleep channel capture and two decay cycles on the shared `bg_channels`. The following block clones those channels through `BasalGangliaLearning.apply_sleep_learning` and `consolidate_habits`, then replaces the dict values (`:3383-3384`). Core replay does not update Go/NoGo (`src/sleep.py:1427-1433`). This second formula does.

Same probe as defect 1, channel `eating_and_grooming`, weights `(go, nogo, habit)` from the committed `nowa_state.json`:

| Point | go | nogo | habit |
| --- | --- | --- | --- |
| Before sleep | 0.523348 | 0.454799 | 0.046013 |
| After `deep_sleep` returns | 0.599256 | 0.418173 | 0.227433 |
| After `_run_sleep_consolidation` returns | 0.667727 | 0.376987 | 0.251192 |

The channel object id changes on the second step. `last_outcome` was set by waking `record_outcome` (`:1484-1485`), which is what `apply_sleep_learning` reads.

### 3. Medium — waking `record_trace` raises, and the caller hides it

`Demo/Tamagochi Chinchilla/src/main.py:1821-1829`. Guard: `src/intent_memory.py:161`.

`_try_start_chain` calls `intent_memory.record_trace` with no `learning_allowed()` or `initializing()`. In strict mode that raises `WakingLearningError: IntentMemory.record_trace writes the stable tier while awake.` The `except Exception` at `:1828` discards it. The trace is not written (`traces` stayed 0). Pytest stays green.

Reproduce: construct the agent as above (the committed save has `action_remaining_s` ≈ 330.6 on `sleep_house`, so a short `sim_step` loop does not start a chain). Set `running = True`, `action_remaining_s = 0`, `chain_cooldown_s = 0`, `current_chain = None`, `current_action = None`, `wakefulness = 0.1`. One `sim_step(0.1)` started `mild_fear` and raised that error once. The step still completed.

## Remarks

The host test's four `sim_step(1)` calls run against the committed save (`tick_count` 74772, `sleep_house` still in progress). `advance_time` still runs, so the clock and fingerprint assertions are real. They do not reach `record_trace` or the sleep branches. `sim_step` returns at `:1679` while `action_remaining_s > 0`, so the pressure band is sampled when the sleep action ends, which is the schedule spec §6 already describes.

`nowa`'s own slow-affect queue stays empty because the cage does not call `Agent.step`. Spec §6. Light sleep calls `sleep_cycle` and does not call `_consolidate_two_tier_once`. That matches spec §2: capture is on `deep_sleep`.

`tests/test_complete_flow.py` and `tests/test_debug_load.py` execute at import and delete `saves/*.pkl`. Two overlapping `pytest tests` processes can make collection raise `FileNotFoundError`. A single run collected them. `tests/` is unchanged in this PR.

---
