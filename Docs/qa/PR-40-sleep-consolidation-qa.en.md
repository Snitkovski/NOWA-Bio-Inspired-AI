# QA PR #40 — sleep consolidation (PR B of #13)

Branch: `team/core-sleep-consolidation` @ `9276b97` (plus this QA commit).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/40
Spec: `Docs/specs/issue-13-two-tier-plasticity.en.md`, including "Owner decisions after PR A".
Previous QA: `Docs/qa/PR-37-labile-layer-qa.en.md`.
Scope: one pass over the sleep consolidation commit. Core and demo source were not edited. No headless demo run. No seed sweep beyond the three `PYTHONHASHSEED` values named below and seed 1 inside the QA checks.

## Verdict

**PASS with notes**

One sleep consolidates each known episode once. A second sleep does not repeat capture, the compensated Go/NoGo step, the habit EMA, or Q replay. The isolated once-pass is exactly κ = 0.5 of the remaining tag plus `η_c_sleep_eff` = 0.07, which is 0.08 on an undecayed reward of +1, and it does not write stable Q. Habit EMA, visit transfer, the slow-affect fingerprint, the named guards, and the NaN/±inf rule hold on `step`, `commit`, and `apply_feedback`.

The note that matters: the same night's existing replay path still adds its own Go/NoGo/habit deltas after that 0.08 step, up to the PR #35 weight cap. The 0.08 identity is the once-pass, not the state after `sleep(cycles=1)`. Details below. The colony survival failure is pre-existing.

## Pytest

| Suite | Result | Time |
| --- | --- | --- |
| `pytest tests -q` | **891 passed, 5 skipped** | 211 s |
| `pytest Demo -q` | **998 passed, 6 skipped, 1 failed** | 111 s |

The five core skips are the pre-existing ones. 891 = the author's 878 plus the 13 checks in `tests/test_qa_pr40_sleep_consolidation.py`.

The Demo failure is `Demo/Colony chinchillas/tests/test_resources.py::test_tc01_two_agents_basic_survival_loop`: `agent_1.sim_time` was 204, not > 290. Same assert the author saw at 103. Counted under checklist 8. Tamagotchi, Virtual company, and Warriner tests in that run passed.

## Checklist

### 1. Exactly once

A known episode is marked on the first sleep (`two_tier_consolidated == 1`, `consolidated_revision == outcome_revision`, `consolidated_reward` stored). The labile contribution is removed in that pass.

`sleep(cycles=0)` runs the once-pass and the mark, and does not run a `sleep_cycle`, so there is no SHY, no `degrade_unused`, and no cortex multiply. A second `sleep(cycles=0)` with no new episode returns `two_tier_consolidated == 0` and leaves the stable fingerprint bit-exact. Go stays 0.58, habit stays 0.20, Q stays 0.

A second `sleep(cycles=1)` after a real first night also returns `two_tier_consolidated == 0` and `total_replays == 0`. Stable Q is unchanged. These fingerprint fields are unchanged: `value_layer`, `slow_affect`, `visit_counts`, `strategies` (including neuromodulator baselines).

What the second cycle does change, and only this:

| Field | Rule | Measured on one rewarded episode |
| --- | --- | --- |
| `go_weight`, `nogo_weight`, `habit_strength` | SHY, one cycle: `w' = prior + (w − prior) · (1 − decay_rate_sleep)`. Default decay is 0.02, so the factor is 0.98. Not another +0.08 and not another EMA. | go 0.7254 → 0.720892, nogo 0.338976 → 0.342197, habit 0.224664 → 0.220171, priors 0.5 / 0.5 / 0 |
| Intent traces with strength > 0 | `degrade_unused(0.8)` once per cycle (spec step 11). Not a second outcome EMA. | 0.160 → 0.128 |
| Cortex pattern strength | `_apply_neuromodulators_during_sleep`: `strength *= 1 + dopamine · 0.05` once per cycle. Dopamine itself stayed 0.29146. | 1.014573 → 1.029358 |

Same rating after consolidation (`commit` reward 1, then feedback `+2`): `updated=True`, `outcome_revision` unchanged, fingerprint unchanged. The next `sleep(cycles=1)` marks 0 episodes, replays 0, and leaves Q unchanged. Channel SHY from that cycle still applies, as in the table.

Changed rating (`+1` consolidated, then feedback `−2`): waking Q is untouched and the revision counter moves. The next once-pass does not roll the first write back. From the post-first-sleep weights (go 0.58, habit 0.20) it adds the new step: go 0.58 → 0.54 (−0.04) and habit EMA toward 0, 0.20 → 0.16. A planted TD history with variance 1.0 does not trip `rejected_due_to_td_variance` (stays 0); replay runs and Q falls (0.075 → about 0 on one cycle, because three capped replay steps of 0.025 equal the Q the first night wrote). The previous stable write is not subtracted as a correction; the new reward is applied again, and the replay budget happens to cancel that one-cycle Q.

### 2. Capture, Q, eviction

Config: `capture_kappa = 0.5`, `eta_channel_sleep = 0.08`, `eta_labile_channel = 0.02`, so `η_eff = 0.07`.

One undecayed reward +1, then `sleep(cycles=0)` so replay and SHY cannot move the channel:

| | Tag | κ · tag | Step | Total | Weights |
| --- | --- | --- | --- | --- | --- |
| Go | +0.02 | +0.01 | +0.07 | **+0.08** | 0.50 → 0.58 |
| NoGo | −0.01 | −0.005 | −0.035 | **−0.04** | 0.50 → 0.46 |

Stable Q stays 0. Labile Q and the channel tag for that episode are cleared. `g_DA` stays 1: dopamine set to 0.95 still stores the tag (0.02, −0.01) and still lands on go 0.58.

A tag aged by one τ (`advance_time(1000)` with `expected_wake_interval_s = 1000`) is captured at its decayed size, and the 0.07 step is not scaled down. Go delta = `0.5 · 0.02 · e^(−1) + 0.07` ≈ 0.07368, which is less than 0.08.

After a full `sleep(cycles=1)` the channel is no longer at 0.58. With decay forced to 0, go lands at 0.73 and Q at 0.075, with `total_replays == 3`. The extra +0.15 of Go is three hits of `delta_weight_max_per_sleep` (0.05) inside `_apply_replay_td_bg_unlocked`, and the 0.075 of Q is three hits of the value cap 0.025. Default decay 0.02 then SHY-adjusts that to go 0.7254. `sleep(cycles=3)` lands Q at 0.225 and go at 0.99. See the medium note.

An episode removed from the hippocampus without the eviction helper keeps its tag across sleep and then decays by `e^(−1)` over the next τ. A real eviction (capacity 1) increments `lost_unconsolidated`, drops the contribution, and leaves that state-action Q at 0 while the survivor’s Q rises.

### 3. Priority

`consolidation_order` is `1.0·|δ| + 0.5·|r| + 0.25·novelty + 0.25·emotional_salience`, ties broken by `episode_id` ascending. For a cold terminal table, δ = r, so the three probes score 1.5, 0.55, 0.55 and come out `ep-1`, `ep-2`, `ep-3`. Zero weights tie-break to sorted `episode_id`. The same order and the same scores were printed under `PYTHONHASHSEED` 0, 1, and 7.

The order is the once-pass order. It is not the capped EDPC score. Changing `plasticity.replay_priority_weights` to `(9,9,9,9)` left `_compute_replay_priority` unchanged, and the two episodes that tie at 0.55 have different capped scores (about 0.213 and 0.203). That matches owner question 5 in the PR, and it does not match the spec sentence "Extends `_compute_replay_priority`".

### 4. Habits and visits

Waking `commit` of reward +1 leaves channel `habit_strength` at 0 and every intent trace at strength 0.

Sleep EMA is `rate = 0.20 · clamp(affect_gain_at_encoding, 0.25, 1.5)`. Gain on this path was 1, so both the channel habit and the intent trace move 0 → 0.20 in the once-pass. Reward 0 does not move Go, NoGo, channel habit, or intent strength (`total_replays == 0` as well, salience filter). The zero-reward episode is still marked consolidated, so a later night will not pick it up. The queued slow-affect record for that step is flushed (tension and a sadness activation appear). That is the sleep-only statistic, not a habit write.

Three waking `step` visits stay at 3.0 across 500 s (they do not decay), transfer to `_action_visit_counts[("bin","go")] == 3` on sleep, and the labile counter resets to 0. A second sleep leaves the stable count at 3. `commit_executed_transition` itself does not count a visit; `step` does. Override commits count the executed action.

### 5. Slow affect and the guard

Four waking rewarded steps leave `stable_fingerprint` unchanged. Semantic emotions stay empty. The pending slow-affect queue grows. Emotional-regulation output does change while awake and is outside the fingerprint, as the PR says.

`sleep(cycles=1)` empties the queue, writes semantic emotions (love and fear on this input), and changes the fingerprint. The slow-affect section of the payload is part of that change.

Strict mode (`NOWA_STRICT_LEARNING=1`) raises `WakingLearningError` for direct `go_weight`, `nogo_weight`, `habit_strength`, `ValueLayer._set_value`, `consolidate_habits`, and `apply_sleep_learning`. The live channel and the fingerprint stay put. `apply_sleep_learning` does not open the guard. `register_action_channel("seeded", go_weight=0.8, habit_strength=0.3)` writes 0.8, because it enters `initializing()` itself, and `learning_is_open()` is false again after the call.

Production (`NOWA_STRICT_LEARNING=0`): two direct `go_weight` assignments leave the weight at 0.5 and log `ActionChannel.go_weight skipped` once. `consolidate_habits` and `apply_sleep_learning` each log their own writer once and do not change the live channel.

Remaining holes, not on the `step` / `commit` / feedback path:

- `SleepManager._apply_replay_td_bg` still enters `learning_allowed()` for a direct caller. One waking call moved stable Q from 0 to 0.025 and changed the fingerprint. The episode was not marked consolidated. The wrapper was already there before this PR. This PR closed the same pattern on `_consolidate_bg_outcome_cache` and on `apply_sleep_learning`.
- `value_layer.values[key] = ...` and `bg_action_channels[id] = ActionChannel(...)` skip the guarded setters. `agent_factory._apply_value_profiles` writes the dict during construction. `storage.load_agent` builds new channel objects rather than assigning through the setter, and does not enter `initializing()`.
- `IntentMemory.apply_habit_affect_modulation` assigns `trace.strength` with no guard. Nothing in `src/` calls it.
- One sleep created a temporal chain (`chain_memory` length 1). Category A item 5 includes temporal chains. `stable_fingerprint` still does not. That omission is from PR A; this PR did not add it.

### 6. NaN and infinities

| Call | NaN or `"nope"` | `+inf` | `−inf` |
| --- | --- | --- | --- |
| `step` | episode not outcome-committed, no labile contribution | committed reward +1 | committed reward −1 |
| `commit_executed_transition` | same, no contribution | — | committed reward −1 |
| `apply_feedback_to_last_experience` | `updated=False`, fingerprint unchanged | `reward_signal` +1, stored +1 | `reward_signal` −1 |

### 7. Pre-existing tests

Rule: **equivalent** — same claim, same threshold. **justified-by-spec** — the waking-stable or cache claim was replaced by the sleep contract, and the new assert fails if that contract is absent. **weakened-coverage** — a numeric bar dropped. **hides-regression** — the assert passes when the named behavior is absent.

`test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` no longer hides a dead writer. It now asserts waking stable Q is 0, then `Q > 0` after `sleep(cycles=3)`, and that some intent strength is in `(0, 1]`. A sleep that does not write Q or the habit EMA fails. The 25 waking steps are still there, so the unit-interval checks remain.

| Test | Change in this PR | Verdict |
| --- | --- | --- |
| `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` | Dropped `Q_after > 0 or q_before <= 0`. Requires `q_before == 0`, `q_after > 0`, and a positive habit strength after `sleep(cycles=3)`. | justified-by-spec |
| `test_td_transition.py` stable Q | `> 0.2` raised to `> 0.22`. Measured Q after `sleep(cycles=3)` is 0.225. One missing replay cycle (0.075 per cycle under the cap) fails 0.22. The old 0.8 bar was already removed in PR A. | justified-by-spec |
| `test_qa_issue32` stable Q (`terminal bootstrap`, `single_action`) | Same `> 0.2` → `> 0.22`. | justified-by-spec |
| `test_qa_issue32` NoGo block | Direct `go_weight` / `nogo_weight` assignment moved inside `learning_allowed()`. The 15-choice assert is unchanged. | equivalent |
| `test_qa_pr35` `test_one_positive_record_is_read_in_sleep_and_cache_is_cleared` | Cache spy removed. One episode, decay 0: go rises, cache stays empty, a second sleep does not move go. | justified-by-spec |
| `test_qa_pr35` `test_zero_outcome_is_not_a_sleep_punishment` | `record_action_outcome(0)` replaced by `commit` reward 0. Go and NoGo still match a no-episode control and stay at the seeded weights. | equivalent |
| `test_qa_pr35` `test_same_feedback_does_not_append_the_sleep_cache_twice` | Cache length replaced by one labile contribution. Go still does not move on the repeated rating. | equivalent |
| `test_issue10` `test_repeated_positive_evidence_outruns_decay` | Twelve cache rewrites replaced by twelve committed episodes. Bars kept: evidence go `> 0.55` and `> rested + 0.05`. | justified-by-spec |
| `test_issue10` `test_outcome_cache_is_applied_before_it_is_cleared` | One episode replaces the cache row. Go and habit must rise; the cache stays empty. | justified-by-spec |
| `test_sleep_replay_td_bg.py::test_instability_blocks_replay_and_reinforcement` | `total_replays == 0` kept. `after == before` became `after > before`, because the once-per-episode Go step is not the variance-gated replay. | justified-by-spec |
| `test_agent.py` feedback cache assert | `bg_sleep_memories` membership replaced by `replay_action_id` and `td_outcome_committed` on the episode. | justified-by-spec |
| `test_qa_pr37` idempotency | One cache row replaced by one labile contribution. | equivalent |
| `test_issue13` `test_feedback_is_idempotent_and_a_changed_rating_replaces` | Same one-line swap, contribution count instead of the cache. | equivalent |
| `test_semantic_emotions_integration.py` | One `sleep()` added so `snapshot()` sees the slow write. | justified-by-spec |
| `test_conflict_arbitration_integration.py` | Sixteen `register_outcome` calls moved inside `learning_allowed()`. The inhibit assert is unchanged. | justified-by-spec |
| `test_qa_pr35`, `test_issue9`, `test_issue10`, `test_sleep_replay_td_bg`, `test_phase_6_2` | New autouse `learning_allowed()` wraps the whole test, not only the seed lines. `test_issue9` and `test_phase_6_2` have no other edits. Invariant W stays in `test_issue13_two_tier.py`. | equivalent |

No row is weakened-coverage or hides-regression. The autouse does mean those five modules will not notice a waking call into a writer they happen to touch. The numeric bars they do have still run.

### 8. Flaky colony survival test

`test_tc01_two_agents_basic_survival_loop` is unseeded. It runs 300 s at `dt=1` and requires both `sim_time > 290`. It was not edited. Isolated runs are a fresh pytest process each time. `main` is `cbce2fb` (before the labile tier). `5fb1235` is the parent of this PR (after PR #37, before the consolidation commit). Compared with worktrees, not by checking this branch out.

| Code | Isolated runs | Result |
| --- | --- | --- |
| This branch `9276b97` | 10 | **10 pass, 0 fail** |
| Parent `5fb1235` (PR #37 only) | 10 | **5 pass, 5 fail** — `sim_time` 115, 228, 235, 240, 257 |
| `main` `cbce2fb` | 10 | **9 pass, 1 fail** — `sim_time` 109 on line 16 |

The full `pytest Demo` on this branch then failed the same test once (`sim_time` 204, line 17). That is the author's "failed in a full run, passed alone" shape. PR #40 did not introduce it: `main` already fails the same assert, and the commit before this PR failed it more often in this sample. Not fixed.

On the two-tier builds the failure log also says `expected_wake_interval_s` is unset (fallback 3600 s) and `dt` was not passed (wall-clock fallback). The colony sim calls core `step` / `commit` without `dt`. That is the issue #39 shape. `main` has the early death without those log lines, because the host clock did not exist yet.

### 9. Tamagotchi

`Demo/Tamagochi Chinchilla/src/main.py` differs from the parent in two places only, both required by the guard change:

- `_run_sleep_consolidation` wraps `apply_sleep_learning` and `consolidate_habits` in `learning_allowed()`, then still copies the returned clone onto `self.bg_channels`. Without the wrapper, strict mode raises inside `update_weights` and the live channel stays at its old weight. Inside the wrapper, one positive memory at learning rate 0.05 moves that clone's go above 0.5 and its habit above 0 (`test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn`). The night still learns.
- `load_nowa_state` assigns saved `go_weight` / `nogo_weight` / `habit_strength` inside `initializing()`.

No Tamagotchi test file was edited. Those tests passed inside the Demo run. Core was not tuned to demo timings. Colony, Virtual company, and Warriner source were not changed. The colony credit assert in `test_qa_pr36_colony_core.py` is live on seed 4: the reflex override records `hide`, the committed reward is about −0.085, stable Go of `hide` and `rest` stay equal at 0.5, and the labile Go tag is nonzero only on `hide`.

## Notes (not failing the sleep contract)

### Medium — replay still writes Go, NoGo, and channel habit in the same night

`_apply_episode_channel_and_habit` is the spec step (capture + 0.07 + habit EMA) and it runs once. Then each `sleep_cycle` calls `_apply_replay_td_bg_unlocked`, which still does `go_delta = beta_sleep · go_scale · td_error` (and NoGo and `habit_delta = beta_sleep · td_error · 0.2`), clipped by `delta_weight_max_per_sleep` (0.05). Spec step 4 is TD replay of stable Q. Step 7 is the Go/NoGo step whose total, with capture, stays `η_c_sleep`.

Repro: one terminal reward +1, `decay_rate_sleep = 0`, `sleep(cycles=1)`. Go goes 0.50 → 0.73, not 0.58. Q goes 0 → 0.075. `total_replays` is 3. The once-pass alone (`sleep(cycles=0)`) is 0.58 and Q stays 0. `sleep(cycles=3)` with default decay reaches go 0.99 and Q 0.225.

The PR states the 0.08 identity and that SHY runs afterwards. It does not say that replay BG is still added. PR #35's formula was left in place (the spec lists those formulas as out of scope to redesign). The magnitude of one night is the sum of both writers. Owner question below.

### Low — `_apply_replay_td_bg` opens the guard

Repro, strict mode, no `Agent.sleep`: `agent.sleep_manager._apply_replay_td_bg([episode])` after one waking reward. Q moves 0 → 0.025, fingerprint changes, `learning_is_open()` is false after the call, the episode is not marked. `sleep_cycle` / `deep_sleep` also open the guard, which is the consolidation API. This method opens it for a partial replay with no exactly-once mark.

### Low — fingerprint still omits temporal chains

Not a wrong writer. One consolidated episode produces a chain that `stable_fingerprint` will not see change.

## Open questions

The PR's six questions stand. Measurements that bear on them:

1. Unscaled `η_eff` is what the code does. Dopamine 0.95 does not change the tag or the 0.58 landing. Confirm.
2. A rating changed after consolidation is a new observation. The first go 0.58 is not restored; the new step is added (−0.04 on the once-pass) and replay applies the new reward. Confirm.
3. `register_action_channel` enters `initializing()` itself and leaves the guard closed. Confirm that shape.
4. Fast affect (regulation output measured here) changes while awake and stays out of the fingerprint. Slow stores change on sleep and are in it. Confirm.
5. The four-term score orders the once-pass only. The capped EDPC return is unchanged. Confirm, against the spec line that says the priority extends `_compute_replay_priority`.
6. `sleep(cycles=3)` Q is 0.225 for one rewarded episode (the same budget the PR cites for 10, 30, or 80). `Q > 0.8` stays out of reach while the PR #35 caps stay. The suite's `> 0.22` fails if a cycle is skipped.

Added from this pass:

7. Should replay stop writing Go/NoGo/channel habit now that the compensated episode step exists? Until it does, one night is 0.08 plus up to 0.05 per replay, not 0.08, and SHY only pulls that sum toward the prior.
8. Should `_apply_replay_td_bg` stop opening `learning_allowed()` for a direct caller, the way `apply_sleep_learning` now does?

---
