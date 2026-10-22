# QA PR #37 — waking labile tier (PR A of #13)

Branch: `team/core-labile-layer` (base `c2f8b1a`).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/37
Spec: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/issues/13#issuecomment-6261798711
Scope of this pass: labile layer, learning guard, host time (`dt` / `advance_time`). Sleep capture, κ, replay priorities, exactly-once, and habit EMA during sleep are PR B and are not failures of this PR. Core code was not edited.

## Verdict

**PASS with notes**

The waking contract holds on the paths a host actually calls: `step`, `commit_executed_transition`, feedback, and queued external feedback leave the stable fingerprint unchanged; choice moves through the labile tier inside the clamps; decay, `dt` slicing, feedback replacement, save/load, and the existing sleep writers (replay Q and the BG outcome cache) behave as specified for PR A. Notes below are guard holes the author already listed, slow affective statistics left for PR B, and one test assert that became vacuously true.

## Pytest

| Suite | Result | Time |
| --- | --- | --- |
| `pytest tests -q` | **869 passed, 5 skipped** | 217 s |
| `pytest Demo -q` | **999 passed, 6 skipped** | 108 s |

The five core skips and six demo skips are the pre-existing ones. The core count is the author's 860 plus the 9 checks in `tests/test_qa_pr37_labile_layer.py`. No headless demo run. No seed sweep beyond the seeds inside those checks (seeds 1–8, one scenario each).

## Checklist

1. **Fingerprint.** Twelve waking cycles (rewarded commit, override, rating then a changed rating, queued external feedback) leave `stable_fingerprint` unchanged. Stable visit counts stay empty, stable Go stays 0.5, `online_update_count` stays 0, habit strength stays 0. `|L_Q| ≤ 0.2`, `|L_channel| ≤ 0.1`.
2. **Choice without sleep.** Seed 1, 40 rewarded commits of `red`, no sleep: P(`red`) rises. A single `td_error=100` / `reward=100` contribution is clamped to `|ΔQ| ≤ 0.05` and `|Δchannel| ≤ 0.1`, and the stored offsets stay inside 0.2 / 0.1.
3. **Decay and time.** After `5·τ_L`, residual `|L_Q| < 1%` of the value just written. `advance_time(8)` and four `advance_time(2)` match to `1e-12` on Q, channel offsets, and timestamps. `τ_L` follows `expected_wake_interval_s`. With the interval unset, `resolved_tau_s()` is 3600 and construction logs the fallback warning once.
4. **Feedback.** The same rating three times matches one application (one BG sleep-log row). A later same rating returns `updated=True` and does not move tags. Rating `+2`, then 50 s, then `-2`, matches a single `-2` applied at that later clock (Q and channels, `1e-12`). Unknown `episode_id` returns `updated=False` and does not move tags or the fingerprint.
5. **Save/load.** A save round-trips the labile layer, host clock, and `PlasticityConfig`. After load, another 30 s of `advance_time` decays in step with the original agent. A pickle with `labile_layer`, `plasticity_config`, and `host_clock_s` removed loads an empty layer and clock 0, replacing any labile state the target already had.
6. **Sleep.** Twelve terminal rewards of `+1` on `go`, then `sleep(cycles=3)`: stable Q `0 → 0.225`, stable Go `0.5 → 0.967`. Habit strength does not rise (PR B). The strength-0 waking trace was dropped by the existing `degrade_unused` path.
7. **Guard.** With `NOWA_STRICT_LEARNING=1`, `ValueLayer.update` raises `WakingLearningError` and the fingerprint does not change. With the variable unset/`0`, the same call returns `skipped=True`, the fingerprint does not change, and the warning is logged once across two calls. `step(reward=NaN)` does not commit a labile tag. `step(reward=±inf)` stores `±1` and does write a tag.

`step` / `commit` pass an explicit `dt` without reading `time.time()` for the host clock (covered by `tests/test_issue13_two_tier.py` and left as the author wrote it).

## Defects

### Medium — one pre-existing assert no longer checks sleep

`tests/test_qa_issue32_reward_learning.py`, `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep`. The line was not edited. It reads:

```python
assert _q(agent, ["ctx"], "go") > 0.0 or q_before <= 0.0
```

`q_before` is stable Q after waking feedback and before `deep_sleep`. Stable Q is now 0 while awake, so `q_before <= 0` is true and the post-sleep check passes even if sleep leaves Q at 0 or writes a negative value. The comment still says sleep must not destroy a learned sign. Other tests still require stable Q to rise (`test_td_transition`, the successor block in this file, and the QA sleep check: 0.225). This is a coverage hole, not a broken writer.

Repro: 25 waking `step` + feedback on `["ctx"]`, read stable Q (0), call `sleep_manager.deep_sleep(cycles=1)`. The assert cannot fail on the sign.

### Medium — stable writers outside the guard (confirmed, one addition)

These match the author's owner notes, checked by direct call. They are not on the `step` / `commit` / feedback path. A later hardening pass should close them; this PR does not.

| Entry | What a waking call does | Severity |
| --- | --- | --- |
| `ValueLayer._set_value` | Writes `values` with no check. Fingerprint changes. Used by replay and load. | Medium |
| `channel.go_weight = ...` (and nogo / habit) | Direct assignment. `SleepManager._relax_channel_weight`, `_normalize_bg_weights`, and `_copy_bg_weights` assign this way. Safe only because `sleep_cycle` already holds the guard. | Medium |
| `BasalGangliaLearning.apply_sleep_learning` | Opens `learning_allowed()` itself. On a waking call the returned clone learned (`go` 0.5 → 0.54 for one positive memory at DA 0.8). The live channel stays 0.5 until the caller copies the clone back. Tamagotchi's sleep path does that copy, which is why the self-open exists. A waking caller that copies the result also writes stable Go. | Medium |
| `BasalGangliaLearning.consolidate_habits` | Not in the author's list. Assigns `habit_strength` on the clone with no guard (`selection_count=5` → strength ≈ 0.068). Installing that clone updates the fingerprint. | Medium |
| `Agent.register_action_channel` | Writes Go / NoGo / habit with no `initializing()` scope. `register_action_channel("new", go_weight=0.8, habit_strength=0.3)` changes the fingerprint. Spec decision 4 allows host seeding under `initializing()`; this method skips that scope so existing setup keeps working. | Low |

### Medium — slow affective statistics still move while awake (PR B)

Decision 3 says these are stable and sleep-only. The PR split puts them in PR B, and `stable_fingerprint` documents that they are excluded. They do change during `step`, so invariant W is not yet true for category A item 7, and the hash will not catch it.

After 6 waking steps (`reward ±1`, novelty 0.8, conflict 0.6) the fingerprint was unchanged and these moved:

- `affective_background`: anxiety / tension / satisfaction / interest from 0 to about 0.30–0.38
- `semantic_emotions.active_emotions` gained fear and love
- `emotional_memory`: traits, episodes, patterns, narrative fragments
- `emotional_expectations`: `dominant_forecast` empty → `love`, outlook `stabilizing` → `volatile`
- `conflict_arbitration`: `recent_failure_rate` 0 → 0.5, error history filled, `control_cost` > 0
- `emotional_regulation`: `learning_rate_scale` 1.0 → 1.36, arousal and valence moved

`learning_rate_scale` no longer multiplies a waking stable alpha, because that writer is gone. Nothing in the labile step reads it.

### Low — feedback NaN / ±inf

`step` / `commit` treat NaN as unknown (no labile tag) and ±inf as ±1. `apply_feedback_to_last_experience` goes through `int(...)`. NaN and ±inf raise, the handler stores rating 0, and the episode is committed with reward 0 (`updated=True`). A rating of 99 is clamped to `+1`, which is the intended integer scale. Spec 4.1.4 groups the NaN/inf rule with feedback. The integer rating API is what demos pass; this is a parser gap, not a broken idempotent path for `-2..2`.

### Low — `mode="online"` is still implemented

`ValueLayer.update` still has the online branch, behind the guard. The agent does not call it while awake. The author left it so expectation-profile tests keep an implementation. Full-spec item "remove `mode=online`" is not done. Acceptable for PR A as documented.

### Low — encoding field `outcome_revision` is absent

Episodes get `labile_contribution`, `encoded_at`, `td_outcome_committed`. There is no `outcome_revision` attribute. Exactly-once and post-consolidation revisions are PR B. Same-rating no-op does not need the counter to be correct for `-2..2`.

### Low — opt-in ACh test still expects a waking alpha

`test_long_horizon_ach_stability_metrics_normal_mode` is skipped unless `RUN_LONG_HORIZON_ACH=1`. It still asserts `fraction_alpha_above_default > 0.05`. Waking steps no longer set `last_alpha_effective`. Not part of the default 869.

## Test audit

Rule used: **equivalent** means the same claim under the two-tier model, same threshold. **justified-by-spec** means the old waking-stable claim was removed because PR A forbids it, and the replacement matches the spec (or is explicitly PR B). **weakened-coverage** means a numeric bar dropped and the new assert can pass on a smaller effect. **hides-regression** means the assert passes when the behavior it names is absent.

| Test | Change | Verdict |
| --- | --- | --- |
| `test_td_transition.py` | One labile write per rating; stable Q stays 0 while awake. `Q > 0.8` became effective Q in `(0.15, 0.2]` plus stable `Q > 0.2` after `sleep(cycles=3)`. Successor `Q > 0.4` became effective `> 0.01` against a cold agent, stable Q stays 0. | weakened-coverage |
| `test_reward_bandit.py` | `sleep(cycles=3)` every 20 trials. `_MIN_ACCURACY` remains 0.60. | equivalent |
| `test_qa_issue32_reward_learning.py` (bandit, idempotent backup, revision, channel) | Bandit sleeps every 20 trials; accuracy 0.60 kept. Daytime Q/Go asserts that fit the clamps use effective values. Stable Go stays 0.5; habit strength after a waking reward is 0 (was `> 0`). Thirty rewards: effective `> 0.05` (was stable `> 0.5`), then stable `> 0.2` after sleep. Revision loop grew from 8 to 70 steps; thresholds 0.15 and 0.05 kept on effective Q. | weakened-coverage |
| `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` (same file, line not edited) | `Q_after > 0 or q_before <= 0` is true whenever waking stable Q is 0. | hides-regression |
| `test_intent_memory_integration.py` | Waking rewards leave strength 0. `confidence > 0.5` is produced by `apply_outcome` inside `learning_allowed()`, not by `Agent.sleep`. | justified-by-spec |
| `test_qa_pr35_sleep_learning.py` | Expectation variance is written by `ValueLayer.update` under the guard after the waking sequence. Gate thresholds unchanged. | equivalent |
| `test_qa_pr36_colony_core.py` | Credit test reads effective Go (`> 0.5`) and asserts stable Go stays 0.5. Habit-key EMA runs under the guard; strength `> 0.9` stays. | equivalent |
| `test_conflict_arbitration_integration.py` | ACC no longer scales a waking alpha (`base*1.4`, high > low). Replacement: `update` not called, TD snapshots finite. A missing snapshot reads as 0.0 and still passes `isfinite`. | weakened-coverage |
| `test_emotional_regulation_integration.py` | CER scale `base*1.7` removed. Replacement: writer not called, and `td_error_snapshot != 0`. | weakened-coverage |
| `test_phase_6_1_ach.py` | Waking `last_alpha_effective > alpha_online_default` removed. ACh rise and high-ACh replay priority remain. The module-wide guard does not hide a returned `update` call: this test still asserts `online_update_count == 0`. | justified-by-spec |
| `test_value_layer_integration.py` | Autouse `learning_allowed()` only. No threshold edited. | equivalent |
| `test_external_interaction_layer.py` | Direct `apply_learning_hooks` runs inside the guard; weight inequalities unchanged. The agent path applies hooks on `sleep()` and then checks the same inequality. | equivalent |
| `test_k03_habit_signature.py`, `test_intent_memory.py`, `test_basal_ganglia.py`, `test_value_layer.py`, `test_value_layer_storage.py`, `test_phase_5_edpc.py`, `test_dopaminergic_td_layer.py`, `test_edpc_sac_synchronization.py`, `test_affect_integration.py`, `test_habits_loading.py` | Direct stable-writer calls run inside `learning_allowed()` (module autouse and/or a local `with`). Numeric asserts unchanged. | equivalent |

The 0.8 → 0.2 and 0.5 → 0.05 drops do not hide a dead writer: stable Q must still clear 0.2 after one existing sleep budget, and a single labile step of `η_L ≈ 0.003` does not clear 0.05. They do stop the suite from requiring Q near the reward. The successor check at 0.01 is the loosest of these.

Module-wide `learning_allowed()` means those files will not notice a waking call into the writer they are testing, except where they also assert `online_update_count == 0` or a frozen fingerprint. Invariant W is covered by `test_issue13_two_tier.py` and `test_qa_pr37_labile_layer.py`, not by those unit files.

## Demos (not fixed)

Later per-demo PRs. `pytest Demo` is green because the fallback still runs and Demo does not set `NOWA_STRICT_LEARNING`.

### Colony chinchillas

`ChinchillaAgent.sim_step(dt)` passes `dt` into physiology and **does not** pass it to `Agent.step(..., decision_only=True)` or `commit_executed_transition(reward=...)`. Every decision step hits the wall-clock fallback (first step uses a synthetic 1 s when no previous timestamp exists). The reward becomes a labile tag and a `bg_sleep_memories` row. Stable Q, Go, and habit strength do not move until the colony's own `sleep()`.

Tests that drive that path (they need `dt=` on the core calls, and an explicit sleep only if a scenario was relying on waking stable weights):

- `Demo/Colony chinchillas/tests/test_nowa_agent.py` (`sim_step`, including the test that the base `step` is called)
- `test_knowledge.py`, `test_reproduction.py`, `test_resources.py`, `test_social.py`, `test_storage.py` (`run_for` / `sim_step`)
- `tests/test_k01_colony_ablation.py`, `tests/test_k01_need_consumption.py`, `tests/test_k02_decide_act_learn.py`, `tests/test_qa_pr36_colony_core.py`

Colony tests that only construct an agent (lineage, genome portrait, most of the GUI unit tests) do not take this path.

### Tamagotchi Chinchilla

Not `Agent.step`. On a finished chain, `Demo/Tamagochi Chinchilla/src/main.py` calls `value_layer.update(..., mode="online")`. Under the production guard that write is skipped and warned once; under `NOWA_STRICT_LEARNING=1` it raises. Demo tests do not set the variable, so they stay green and do not assert Q.

Sleep in that file calls `BasalGangliaLearning.apply_sleep_learning` (the self-opening guard; learning still happens) and `consolidate_habits` (direct `habit_strength` assign, no guard).

Tests that run `sim_step` / the demo `step` and will need a strict-mode decision when the demo is adapted:

- `Demo/Tamagochi Chinchilla/tests/test_nowa_integration.py`
- `Demo/Tamagochi Chinchilla/tests/test_integration.py`
- `Demo/Tamagochi Chinchilla/tests/test_core.py`, `test_comprehensive.py` (construct and tick the agent; they do not assert stable Q)
- `tests/test_chinchilla_integration.py`

Wall-clock `dt` on core `Agent.step` is not this demo's dependency.

### Virtual company

`TrainingLoop._agent_step` calls `agent.step(context, decision_only=True)` with no `dt`, so each day hits the wall-clock fallback. The loop's own comment says it does not want a waking value update inside `step`; that part already matches PR A. Feedback that later calls `apply_feedback_to_last_experience` writes the labile tier, not stable Q.

Tests on the real core agent, no `dt`:

- `Demo/Virtual company/tests/test_agent_pipeline.py` (quarter runs, `decision_only`, and the test that a non-decision step stores an experience)
- `Demo/Virtual company/tests/test_agent_independence.py` (`agent.step(context)`)
- `test_sandbox_integration.py`, `test_run_sandbox.py`, `test_sandbox_checkpoint.py` (real `create_procurement_agent` sessions)

`test_training_loop.py` uses fake `step` methods. `test_agent_pipeline.py` asserts `value_layer.update` is not called on the decision-only path; that assert agrees with PR A and does not depend on daytime stable learning.

### Warriner Validation

`nowa_colony._run_agent_step` calls `agent.step(..., reward=memory_reward)` with no `dt` (wall-clock fallback and a waking labile tag). `Demo/Warriner Validation/tests/test_nowa_colony.py` and `test_hippocampus_seeder.py` use a `FakeAgent`. No current Warriner test drives the real core agent. The runtime path is what a later demo PR has to pass `dt` through.

## Open questions for the owner

1. Slow affective / expectation statistics (decision 3): confirm they stay writable, and outside the fingerprint, until PR B. Measured movement is listed above.
2. Confirm the unguarded primitives (`_set_value`, raw Go/NoGo/habit assignment, `consolidate_habits`) and the self-opening `apply_sleep_learning` stay as they are for this PR.
3. `register_action_channel` does not enter `initializing()`. Keep that so current setup works?
4. `g_DA` is fixed at 1.0 inside `_record_known_outcome`. There is no phasic-DA gain field. Confirm.
5. Labile visit counts do not decay; stable visit counts stay frozen. Confirm.
6. Habit EMA is not applied in this sleep. A strength-0 waking trace can disappear in `degrade_unused`. Confirm that is acceptable until PR B.
7. Should `apply_feedback_to_last_experience(NaN | ±inf)` follow the step/commit rule (unknown / ±1), or is the integer rating scale the only contract?
8. The vacuous `q_before <= 0` assert: fix in a follow-up on this branch, or leave it until the test rewrite in PR B?
9. Docs sweep remains PR C. In-code docstrings on the touched agent and sleep paths were updated; `Docs/` was not.

---
