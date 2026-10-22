# QA: PR #33 — core reward learning (C01–C06, C09)

> **Superseded for core learning contract by issue #13 two-tier plasticity** (PR #37 labile layer, PR #40 sleep consolidation). Waking stable writes described here are no longer current; see `Docs/specs/issue-13-two-tier-plasticity.en.md` and `Docs/architecture/two-tier-plasticity.en.md`.
>
> **Superseded by #13 two-tier model** for the core learning contract (PR #37, PR #40). Waking stable writes from this report are obsolete.

Branch: `team/issue-32-reward-learning`
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/33
Product code was not changed. QA artifacts: this report and `tests/test_qa_issue32_reward_learning.py`.

Out of scope and not run as acceptance criteria: #9 (C07 sleep replay), #10 (C08 BG sleep decay), #12 (C10 neuromodulator fixed points), colony #19–#21. Sleep and affect were checked only as regression of adjacent contour (habit bounds and Q finiteness).

## Verdict

FAIL

The contextual bandit closes umbrella #32: frozen policy above random on extra seeds, mappings, `PYTHONHASHSEED`, and under reward noise. Issues #3, #4, #7, and #11 hold on checked scenarios. Issues #5, #6, and #8 are not fully closed: revising an old rating clobbers shared Q, repeated same feedback accumulates Go/NoGo and habit, `step(reward=...)` does not move habit and channel, non-finite reward aborts `step()`, and after save/load the episode counter restarts and `ep-1` points at a different episode.

## Coverage

- scenarios: 11 passed / 7 failed / 4 not run
- product `pytest tests` before adding QA file: 764 passed, 5 skipped, 17.73 s (matches senior-dev claim; PR CI green on commit `3cad48d`)
- `pytest tests/test_qa_issue32_reward_learning.py`: 11 passed, 7 failed, 35.58 s

Passed:

1. Frozen bandit, seed 2, 3, 5, 8, 13, 21, 42 × 4 mappings outside PR set (including same best answer in both contexts and actions `left/stay/right`). Threshold as in PR: accuracy ≥ 0.60, each context ≥ 0.50. `decision_only` evaluation, no learning in measurement window.
2. Frozen bandit with `PYTHONHASHSEED` 2, 3, 4, 11, 99 × 2 mappings (PR had only 0, 1, 7).
3. Noise: uniform ±0.35 on ±1 (threshold 0.60/0.50); gauss σ=0.5 and 10% sign flips (threshold “above random”: 0.45 / 0.35).
4. Two runs with same `rng_seed` and `random.seed(11)`: 40 steps matched symbol by symbol.
5. Same trace with `PYTHONHASHSEED` 0, 1, 7, 12345 (`random.seed` and `rng_seed` fixed).
6. Feedback by id: 0 mismatches over 120 steps at capacity 1, 2, and 40. Evicted id returns `updated=False` and does not change surviving episode reward.
7. Empty memory, feedback before first `step`, unknown reward (`reward=None` does not TD), zero reward (exactly one TD), string `"not-a-number"` not treated as known outcome.
8. Repeated same rating does not add second TD update. Single terminal step with reward 0 does not create value from empty bootstrap.
9. Sole action is chosen and learns. All visited channels with `go_weight=0`, `nogo_weight=1`, and cortisol 1 yield `NO_ACTION`. Stress increases NoGo of its channel and leaves action with positive surplus available.
10. Untried action gets larger bonus and enters softmax within 40 picks.
11. 25 steps at `valence=1` and one `deep_sleep` cycle: habit strength and channel weights stay in `[0, 1]`, Q finite and keeps positive sign.

Failed: see defects 1–5 (seven tests, five defects: NaN and inf — one cause, counter reset and save/load — one cause).

Not run: #9, #10, #12, colony #19–#21.

## DoD cross-check

| Issue | Result | Basis |
| --- | --- | --- |
| #3 C01 sign and pressure scale | done | `ActionSelector._signed_recall_means`: mean signed reward, energy = intensity×activation, result via `tanh`. Product test 20×`reward=-1` vs 2×`reward=+1` not weakened. Bandit learns. |
| #4 C02 salted `hash()` | done | No `hash()` call in `src/agent.py`. Cold start: sha256 and `self._rng`. Trace independent of `PYTHONHASHSEED`. |
| #5 C03 feedback addressing | partial | In-process id from `last_episode_id` stable, including at capacity 1. After `_episode_seq` reset (fresh process after load because counter not in `AgentStorage`) new step gets `ep-1` again and `get_experience("ep-1")` returns new episode. |
| #6 C04 one TD and V(s') | partial | While rating unchanged, one online update per transition, repeated same rating does not duplicate TD. Terminal bootstrap 0. Revising old episode overwrites shared Q cell from original prior and erases later updates of same `(s, a)`. |
| #7 C05 NO_ACTION and untried | done | `step()` no longer substitutes `NO_ACTION`. Gated score 0 not in softmax. Visit bonus larger at `n=0`, untried action stays in choice. |
| #8 C06 habits | partial | `IntentMemory.apply_outcome`: EMA to 1 or 0, strength in `[0, 1]`, affect only scales rate clamped `[0.25, 1.5]`. Sleep does not break bound. `step(reward=1.0)` updates Q, not habit and Go/NoGo. Repeated same feedback moves them again. |
| #11 C09 NoGo | done | NoGo = `nogo_weight * (0.05 + 0.12 * stress_drive)`, no global `\|pressure\|` multiplier. Stress does not zero channel with positive surplus. Full NoGo on visited actions gives `NO_ACTION`. |
| #32 bandit | done | Frozen policy above threshold on seed / mapping / hash seed / noise matrix wider than PR set. |

## Old test edits

Justified and not replaced by weaker checks:

- `tests/test_selector.py`, `tests/test_affect_integration.py`, `tests/test_affective_persistence.py`, `tests/test_agent.py` set `reward=1.0` because pressure now comes from outcome sign, not intensity. Choice asserts unchanged.
- `tests/test_basal_ganglia.py::test_threat_effect_inhibition` no longer requires high NoGo to beat high Go. That was defect #11. New assert: under threat high-Go stays ahead of high-NoGo and choice does not collapse to one `NO_ACTION`. Separate QA check confirmed NoGo rises with aversive/cortisol.
- `tests/test_intent_memory_integration.py` rewards one action and punishes others. Rewarded action dominates, not repetition count. Confidence threshold > 0.5 kept. Stochastic “≥ 60% picks” replaced by pressure comparison: bounded EMA has no old frequency counter, and new condition still fails if rewarded action is not on top.

Note, not a defect of this edit: `test_no_learning_during_waking` still checks only absence of `selector.weights`. Waking TD on explicit `reward` already exists; test does not see it.

## Defects

### [MAJOR] Revising old rating clobbers later updates of same Q

- **Steps**: 8 terminal steps in one context with one action, each feedback `+2`. Remember Q. Repeat first episode feedback with rating `-2`.
- **Expected**: editing one transition shifts Q by about one backup. Other seven rewarded transitions remain in cell.
- **Actual**: Q falls from `0.2163` to `-0.0277`. `-0.0277` is one step from original prior `0` as if other updates never happened. `_apply_feedback_value_update` on reward change substitutes first commit's `td_prior_value` and `_set_value` overwrites shared table cell.
- **Where**: `src/agent.py` `_apply_feedback_value_update`; `src/value_layer.py` `update(prior_value=...)`
- **Severity**: major
- **Test**: `tests/test_qa_issue32_reward_learning.py::test_qa_revising_an_older_rating_must_not_clobber_later_updates`

### [MAJOR] Repeated same feedback moves Go/NoGo, habit, and sleep memory again

- **Steps**: one `step`, twice `apply_feedback_to_last_experience(2)` on same `episode_id`.
- **Expected**: second call with same outcome changes nothing. TD does (`online_update_count` stays 1).
- **Actual**: before “same reward” check, `_apply_outcome_to_habits`, `_apply_outcome_to_channel`, and `record_action_outcome` run. Measured on action `stop`: habit `0.20 → 0.36`, go `0.58 → 0.66`, nogo `0.46 → 0.42`, `bg_sleep_memories` `1 → 2`. TD not duplicated.
- **Where**: `src/agent.py` `apply_feedback_to_last_experience` (habit and channel update above early exit on `same_reward`)
- **Severity**: major
- **Test**: `tests/test_qa_issue32_reward_learning.py::test_qa_repeated_feedback_is_idempotent`

### [MAJOR] Known reward in step() teaches Q but not habit and channel

- **Steps**: `step(["bin"], reward=1.0, terminal=True)` without `apply_feedback_to_last_experience`.
- **Expected**: known outcome moves Q, habit EMA, and Go/NoGo of that channel. Foreign channel unchanged.
- **Actual**: TD update present, Q of chosen action `go` became `0.03`. `go_weight` stayed `0.5`. Trace created via `note_selection` with `strength=0`. `_apply_outcome_to_habits` and `_apply_outcome_to_channel` only from feedback.
- **Where**: `src/agent.py` `step` (`outcome_known` branch) and `apply_feedback_to_last_experience`
- **Severity**: major
- **Test**: `tests/test_qa_issue32_reward_learning.py::test_qa_step_reward_teaches_habits_and_channel`

### [MAJOR] NaN and inf in step(reward=...) abort the step

- **Steps**: `step(["bin"], reward=float("nan"), terminal=True)` and same with `+inf` / `-inf`.
- **Expected**: step completes, episode reward and Q finite in working range.
- **Actual**: `ValueError: cannot convert float NaN to integer` and `OverflowError: cannot convert float infinity to integer` in `_discretize_drive`. Exception escapes `step()`. By then action chosen and visit recorded, episode not stored. Feedback path safer: non-numeric rating resets to 0.
- **Where**: `src/hippocampus.py` `_discretize_drive` (line with `int(round(...))`); `src/agent.py` `step` does not filter non-finite `reward` before `hippocampus.store`
- **Severity**: major
- **Tests**: `test_qa_nan_reward_does_not_abort_the_step`, `test_qa_inf_reward_does_not_abort_the_step`

### [MAJOR] After save/load episode id is reissued and no longer points at old episode

- **Steps**: 4 steps with feedback `+2` (`ep-1`…`ep-4`), `AgentStorage.save_agent` / `load_agent` to new agent. Before next step `get_experience("ep-1")` finds episode reward `1.0`, Q matches. Then `step(["after-load"])`.
- **Expected**: new episode gets new id. `get_experience("ep-1")` still returns first episode reward `1.0`.
- **Actual**: `_episode_seq`, `_episodes_by_id`, and `last_episode_id` not in save. After load counter is 0, next episode again `ep-1`. Two objects with id `ep-1` in list. `get_experience("ep-1")` returns new (reward 0, after feedback `-1`). Same without file: zero `_episode_seq` and index on live agent, step — `get_experience(first_id)` is different object. Episodes themselves not erased on load: `_ensure_signature_store` restores signatures, Q value layer reads back.
- **Where**: `src/hippocampus.py` `_assign_episode_id`, `_sync_episode_index`; `src/storage.py` `save_agent` / `load_agent`
- **Severity**: major
- **Tests**: `test_qa_episode_id_survives_a_sequence_reset_like_reload`, `test_qa_save_load_keeps_episode_identity`

### [MINOR] rng_seed does not control thalamic choice

- **Steps**: two agents with `rng_seed=5`, no repeat `random.seed`. Before second run advance global `random` by 5 calls.
- **Expected**: with fixed agent seed action trace is identical.
- **Actual**: traces diverged on first action (`red...` and `green...`). Cold prior from `self._rng`, `ThalamicGate.select` calls `random.choices` on module `random`. Match only if both `rng_seed` and global `random` seeded.
- **Where**: `src/basal_ganglia.py` `ThalamicGate.select`; `src/agent.py` `_stable_bootstrap_prior`
- **Severity**: minor

### [TRIVIAL] Docstrings describe old formulas

- **Steps**: read docstring `BasalGangliaGate.process`, module docstring `src/agent.py`, docstring `Agent.step`.
- **Expected**: text matches channel NoGo and waking TD.
- **Actual**: `process` still says `NoGo = |pressure| * (gamma * cortisol + delta * aversive)`. `agent.py` still “Learning happens ONLY during sleep” and “NO learning happens here”.
- **Where**: `src/basal_ganglia.py` `process`; `src/agent.py`
- **Severity**: trivial

## Questions / blockers

No run blockers: environment up, `pytest` and issues readable.

Disputed, not separate defects:

- Visit bonus capped `cer_bonus_cap_abs=0.05`. On checked matrix bandit still beats random, so cap not marked defect.
- Product bandit still calls feedback inside evaluation window. Frozen QA evaluation also passes threshold, so PR did not hide weakness.
- `record_trace` / `strengthen_trace` can still raise strength to 64. `Agent.step` waking uses `note_selection` and `apply_outcome`. Direct call remains in `src/gui.py`. Not attributed to core DoD.

## Recommendations

1. Rating revision should adjust current Q (target difference), not write one backup from first commit's `td_prior_value`.
2. On repeated feedback with same rating exit before habit, channel, and `bg_sleep_memories` updates.
3. In `outcome_known` branch of `step()` call same `_apply_outcome_to_habits` and `_apply_outcome_to_channel` as feedback.
4. Clamp reward to finite range before `hippocampus.store`. In `_discretize_drive` do not call `int(round(...))` on NaN/inf.
5. Persist `_episode_seq` in save/load (and do not issue id already in list). Also `last_episode_id` and `_action_visit_counts`, else “untried” bonus restarts after load.
6. Give softmax agent seed, not global `random`.
7. Do not treat PR green on `pytest tests` while `tests/test_qa_issue32_reward_learning.py` is in tree: seven tests red documenting defects above. Product set without that file — 764 passed, 5 skipped.

## Release readiness

no

Bandit and contours #3, #4, #7, #11 are ready to demonstrate learning. Too early to merge as closure of #5, #6, #8: rating revision and repeated feedback corrupt learned state, and episode id after save is no longer identity.
