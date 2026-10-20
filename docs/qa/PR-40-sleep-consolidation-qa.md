# QA PR #40 — sleep consolidation (PR B of #13)

Branch: `team/core-sleep-consolidation` @ `9276b97` (plus this QA commit).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/40
Spec: `docs/specs/issue-13-two-tier-plasticity.md`, including "Owner decisions after PR A".
Previous QA: `docs/qa/PR-37-labile-layer-qa.md`.
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

# QA PR #40 — консолидация во сне (PR B задачи #13)

Ветка: `team/core-sleep-consolidation` @ `9276b97` (плюс этот QA-коммит).
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/40
Спека: `docs/specs/issue-13-two-tier-plasticity.md`, включая «Решения владельца после PR A».
Прошлый QA: `docs/qa/PR-37-labile-layer-qa.md`.
Объём: один проход по коммиту консолидации. Исходники ядра и демо не менялись. Headless-прогона демо нет. Перебора сидов нет, кроме трёх значений `PYTHONHASHSEED` ниже и сида 1 в QA-проверках.

## Вердикт

**PASS with notes**

Один сон консолидирует каждый эпизод с известным исходом один раз. Второй сон не повторяет захват, компенсированный шаг Go/NoGo, EMA привычки и replay Q. Изолированный однократный проход — это ровно κ = 0.5 оставшейся метки плюс `η_c_sleep_eff` = 0.07, то есть 0.08 на незатухшей награде +1, и стабильный Q он не пишет. EMA привычки, перенос визитов, отпечаток медленного аффекта, названные guard и правило NaN/±inf выполняются в `step`, `commit` и `apply_feedback`.

Существенная оговорка: replay той же ночи по-прежнему добавляет свои дельты Go/NoGo/habit после шага 0.08, до потолка весов из PR #35. Тождество 0.08 — это однократный проход, а не состояние после `sleep(cycles=1)`. Провал теста выживания колонии существовал до этого PR.

## Pytest

| Набор | Результат | Время |
| --- | --- | --- |
| `pytest tests -q` | **891 passed, 5 skipped** | 211 с |
| `pytest Demo -q` | **998 passed, 6 skipped, 1 failed** | 111 с |

Пять skip ядра — прежние. 891 = 878 у автора плюс 13 проверок в `tests/test_qa_pr40_sleep_consolidation.py`.

Единственный провал Demo: `Demo/Colony chinchillas/tests/test_resources.py::test_tc01_two_agents_basic_survival_loop`, `agent_1.sim_time` = 204, не > 290. Тот же ассерт, который автор видел на 103. Разбор в пункте 8. Тесты тамагочи, виртуальной компании и Warriner в этом прогоне прошли.

## Проверка по пунктам

### 1. Ровно один раз

Эпизод с известным исходом помечается в первый сон (`two_tier_consolidated == 1`, `consolidated_revision == outcome_revision`, записан `consolidated_reward`). Лабильный вклад снимается в этом проходе.

`sleep(cycles=0)` делает однократный проход и пометку и не вызывает `sleep_cycle`: нет SHY, нет `degrade_unused`, нет домножения коры. Второй `sleep(cycles=0)` без нового эпизода возвращает `two_tier_consolidated == 0` и оставляет отпечаток бит-в-бит. Go остаётся 0.58, привычка 0.20, Q остаётся 0.

Второй `sleep(cycles=1)` после настоящей первой ночи тоже даёт `two_tier_consolidated == 0` и `total_replays == 0`. Стабильный Q не меняется. Не меняются поля отпечатка: `value_layer`, `slow_affect`, `visit_counts`, `strategies` (включая базовые линии нейромодуляторов).

Что меняет второй цикл, и только это:

| Поле | Правило | Замер на одном вознаграждённом эпизоде |
| --- | --- | --- |
| `go_weight`, `nogo_weight`, `habit_strength` | SHY, один цикл: `w' = prior + (w − prior) · (1 − decay_rate_sleep)`. Дефолт decay 0.02, множитель 0.98. Это не ещё один +0.08 и не ещё одна EMA. | go 0.7254 → 0.720892, nogo 0.338976 → 0.342197, habit 0.224664 → 0.220171, prior 0.5 / 0.5 / 0 |
| Следы намерения с силой > 0 | `degrade_unused(0.8)` раз за цикл (шаг 11 спеки). Не вторая EMA исхода. | 0.160 → 0.128 |
| Сила коркового паттерна | `_apply_neuromodulators_during_sleep`: `strength *= 1 + dopamine · 0.05` раз за цикл. Сам дофамин остался 0.29146. | 1.014573 → 1.029358 |

Та же оценка после консолидации (`commit` с наградой 1, затем feedback `+2`): `updated=True`, `outcome_revision` не меняется, отпечаток не меняется. Следующий `sleep(cycles=1)` помечает 0 эпизодов, replay 0, Q не двигает. SHY каналов в этом цикле всё равно есть, как в таблице.

Изменённая оценка (`+1` уже консолидирован, затем feedback `−2`): днём Q не трогается, счётчик ревизии растёт. Следующий однократный проход не откатывает первую запись. От весов после первого сна (go 0.58, привычка 0.20) он прибавляет новый шаг: go 0.58 → 0.54 (−0.04), EMA привычки к 0: 0.20 → 0.16. Подложенная история TD с дисперсией 1.0 не даёт `rejected_due_to_td_variance` (остаётся 0); replay идёт, Q падает (0.075 → около 0 за один цикл, потому что три ограниченных шага replay по 0.025 равны Q первой ночи). Прежняя стабильная запись не вычитается как коррекция; новая награда применяется ещё раз, и бюджет replay как раз гасит Q одного цикла.

### 2. Захват, Q, вытеснение

Конфиг: `capture_kappa = 0.5`, `eta_channel_sleep = 0.08`, `eta_labile_channel = 0.02`, поэтому `η_eff = 0.07`.

Одна незатухшая награда +1, затем `sleep(cycles=0)`, чтобы replay и SHY не двигали канал:

| | Метка | κ · метка | Шаг | Итого | Веса |
| --- | --- | --- | --- | --- | --- |
| Go | +0.02 | +0.01 | +0.07 | **+0.08** | 0.50 → 0.58 |
| NoGo | −0.01 | −0.005 | −0.035 | **−0.04** | 0.50 → 0.46 |

Стабильный Q остаётся 0. Лабильный Q и метка канала этого эпизода очищаются. `g_DA` остаётся 1: дофамин 0.95 всё равно пишет метку (0.02, −0.01) и всё равно приходит к go 0.58.

Метка возрастом в один τ (`advance_time(1000)` при `expected_wake_interval_s = 1000`) захватывается в затухшем размере, шаг 0.07 не уменьшается. Дельта Go = `0.5 · 0.02 · e^(−1) + 0.07` ≈ 0.07368, это меньше 0.08.

После полного `sleep(cycles=1)` канал уже не 0.58. При decay = 0 go садится на 0.73, Q на 0.075, `total_replays == 3`. Лишние +0.15 Go — это три удара `delta_weight_max_per_sleep` (0.05) внутри `_apply_replay_td_bg_unlocked`, а 0.075 Q — три удара потолка значения 0.025. Дефолтный decay 0.02 затем даёт SHY до go 0.7254. `sleep(cycles=3)` даёт Q 0.225 и go 0.99. См. замечание средней тяжести.

Эпизод, убранный из гиппокампа в обход помощника вытеснения, сохраняет метку через сон и затем затухает на `e^(−1)` за следующий τ. Настоящее вытеснение (ёмкость 1) увеличивает `lost_unconsolidated`, снимает вклад и оставляет Q этого состояния-действия на 0, пока Q выжившего растёт.

### 3. Приоритет

`consolidation_order` — это `1.0·|δ| + 0.5·|r| + 0.25·novelty + 0.25·emotional_salience`, ничья по `episode_id` по возрастанию. На холодной терминальной таблице δ = r, три пробы дают 1.5, 0.55, 0.55 и порядок `ep-1`, `ep-2`, `ep-3`. Нулевые веса дают порядок отсортированных `episode_id`. Тот же порядок и те же счёта напечатаны при `PYTHONHASHSEED` 0, 1 и 7.

Этот порядок — порядок однократного прохода. Это не ограниченный счёт EDPC. Смена `plasticity.replay_priority_weights` на `(9,9,9,9)` не меняет `_compute_replay_priority`, а два эпизода с ничьёй 0.55 имеют разные ограниченные счёта (около 0.213 и 0.203). Это совпадает с вопросом 5 владельца в PR и не совпадает с фразой спеки «расширяет `_compute_replay_priority`».

### 4. Привычки и визиты

Дневной `commit` награды +1 оставляет `habit_strength` канала на 0 и все следы намерения на силе 0.

EMA во сне: `rate = 0.20 · clamp(affect_gain_при_кодировании, 0.25, 1.5)`. Gain на этом пути был 1, поэтому и привычка канала, и след намерения идут 0 → 0.20 в однократном проходе. Награда 0 не двигает Go, NoGo, привычку канала и силу намерения (`total_replays == 0`, фильтр salience). Эпизод с нулевой наградой всё равно помечается консолидированным, и следующая ночь его не возьмёт. Запись медленного аффекта этого шага сбрасывается (появляются tension и активация sadness). Это сонная статистика, не запись привычки.

Три дневных визита `step` остаются 3.0 через 500 с (не затухают), во сне переносятся в `_action_visit_counts[("bin","go")] == 3`, лабильный счётчик обнуляется. Второй сон оставляет стабильный счёт на 3. Сам `commit_executed_transition` визит не считает; считает `step`. Commit с override считает исполненное действие.

### 5. Медленный аффект и guard

Четыре дневных шага с наградой не меняют `stable_fingerprint`. Семантические эмоции пусты. Очередь медленного аффекта растёт. Выход эмоциональной регуляции днём меняется и в отпечаток не входит, как написано в PR.

`sleep(cycles=1)` опустошает очередь, пишет семантические эмоции (на этом входе love и fear) и меняет отпечаток. Секция медленного аффекта входит в это изменение.

Строгий режим (`NOWA_STRICT_LEARNING=1`) бросает `WakingLearningError` на прямую запись `go_weight`, `nogo_weight`, `habit_strength`, на `ValueLayer._set_value`, `consolidate_habits` и `apply_sleep_learning`. Живой канал и отпечаток остаются. `apply_sleep_learning` guard не открывает. `register_action_channel("seeded", go_weight=0.8, habit_strength=0.3)` пишет 0.8, потому что сам входит в `initializing()`, и после вызова `learning_is_open()` снова ложь.

Прод (`NOWA_STRICT_LEARNING=0`): два прямых присваивания `go_weight` оставляют вес 0.5 и один раз пишут в лог `ActionChannel.go_weight skipped`. `consolidate_habits` и `apply_sleep_learning` каждый один раз логируют своего писателя и живой канал не меняют.

Оставшиеся дыры, не на пути `step` / `commit` / feedback:

- `SleepManager._apply_replay_td_bg` по-прежнему сам входит в `learning_allowed()`. Один дневной вызов сдвинул стабильный Q с 0 на 0.025 и изменил отпечаток. Эпизод не помечен консолидированным. Обёртка была ещё до этого PR. Этот PR закрыл тот же приём у `_consolidate_bg_outcome_cache` и у `apply_sleep_learning`.
- `value_layer.values[key] = ...` и `bg_action_channels[id] = ActionChannel(...)` обходят защищённые сеттеры. `agent_factory._apply_value_profiles` пишет словарь при построении. `storage.load_agent` создаёт новые объекты каналов, а не идёт через сеттер, и не входит в `initializing()`.
- `IntentMemory.apply_habit_affect_modulation` пишет `trace.strength` без guard. В `src/` вызовов нет.
- Один сон создал временную цепочку (`chain_memory` длины 1). Пункт 5 категории A включает временные цепочки. `stable_fingerprint` их по-прежнему не содержит. Пропуск из PR A; этот PR его не закрывал.

### 6. NaN и бесконечности

| Вызов | NaN или `"nope"` | `+inf` | `−inf` |
| --- | --- | --- | --- |
| `step` | исход эпизода не зафиксирован, лабильного вклада нет | зафиксированная награда +1 | зафиксированная награда −1 |
| `commit_executed_transition` | то же, вклада нет | — | зафиксированная награда −1 |
| `apply_feedback_to_last_experience` | `updated=False`, отпечаток не меняется | `reward_signal` +1, в эпизоде +1 | `reward_signal` −1 |

### 7. Прежние тесты

Правило: **equivalent** — то же утверждение, тот же порог. **justified-by-spec** — дневное стабильное утверждение или кэш заменены контрактом сна, и новый ассерт падает, если контракта нет. **weakened-coverage** — числовой порог снижен. **hides-regression** — ассерт проходит, когда названного поведения нет.

`test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` больше не прячет мёртвого писателя. Теперь он требует, чтобы дневной стабильный Q был 0, затем `Q > 0` после `sleep(cycles=3)`, и чтобы какая-то сила намерения была в `(0, 1]`. Сон, который не пишет Q или EMA привычки, падает. 25 дневных шагов на месте, проверки единичного интервала остались.

| Тест | Что изменилось в этом PR | Вердикт |
| --- | --- | --- |
| `test_qa_habits_stay_in_unit_interval_across_affect_and_sleep` | Убрано `Q_after > 0 or q_before <= 0`. Нужны `q_before == 0`, `q_after > 0` и положительная сила привычки после `sleep(cycles=3)`. | justified-by-spec |
| Стабильный Q в `test_td_transition.py` | `> 0.2` поднят до `> 0.22`. Замеренный Q после `sleep(cycles=3)` — 0.225. Пропущенный цикл replay (0.075 за цикл под потолком) 0.22 не проходит. Порог 0.8 убран ещё в PR A. | justified-by-spec |
| Стабильный Q в `test_qa_issue32` (`terminal bootstrap`, `single_action`) | То же `> 0.2` → `> 0.22`. | justified-by-spec |
| Блок NoGo в `test_qa_issue32` | Прямая запись `go_weight` / `nogo_weight` перенесена внутрь `learning_allowed()`. Ассерт 15 выборов не менялся. | equivalent |
| `test_qa_pr35` `test_one_positive_record_is_read_in_sleep_and_cache_is_cleared` | Шпион кэша убран. Один эпизод, decay 0: go растёт, кэш пуст, второй сон go не двигает. | justified-by-spec |
| `test_qa_pr35` `test_zero_outcome_is_not_a_sleep_punishment` | `record_action_outcome(0)` заменён на `commit` с наградой 0. Go и NoGo по-прежнему совпадают с контролем без эпизода и остаются на посеянных весах. | equivalent |
| `test_qa_pr35` `test_same_feedback_does_not_append_the_sleep_cache_twice` | Длина кэша заменена одним лабильным вкладом. Повторная оценка go не двигает. | equivalent |
| `test_issue10` `test_repeated_positive_evidence_outruns_decay` | Двенадцать перезаписей кэша заменены двенадцатью эпизодами. Пороги те же: go свидетельств `> 0.55` и `> rested + 0.05`. | justified-by-spec |
| `test_issue10` `test_outcome_cache_is_applied_before_it_is_cleared` | Один эпизод вместо строки кэша. Go и привычка должны вырасти; кэш пуст. | justified-by-spec |
| `test_sleep_replay_td_bg.py::test_instability_blocks_replay_and_reinforcement` | `total_replays == 0` сохранён. `after == before` стало `after > before`: однократный шаг Go — не replay под гейтом дисперсии. | justified-by-spec |
| Ассерт кэша в `test_agent.py` | Вхождение в `bg_sleep_memories` заменено на `replay_action_id` и `td_outcome_committed` у эпизода. | justified-by-spec |
| Идемпотентность в `test_qa_pr37` | Одна строка кэша заменена одним лабильным вкладом. | equivalent |
| `test_issue13` `test_feedback_is_idempotent_and_a_changed_rating_replaces` | Та же однострочная замена: число вкладов вместо кэша. | equivalent |
| `test_semantic_emotions_integration.py` | Добавлен один `sleep()`, чтобы `snapshot()` увидел медленную запись. | justified-by-spec |
| `test_conflict_arbitration_integration.py` | Шестнадцать `register_outcome` перенесены внутрь `learning_allowed()`. Ассерт inhibit не менялся. | justified-by-spec |
| `test_qa_pr35`, `test_issue9`, `test_issue10`, `test_sleep_replay_td_bg`, `test_phase_6_2` | Новый autouse `learning_allowed()` оборачивает весь тест, не только строки посева. У `test_issue9` и `test_phase_6_2` других правок нет. Инвариант W остаётся в `test_issue13_two_tier.py`. | equivalent |

Ни одна строка не `weakened-coverage` и не `hides-regression`. Autouse значит, что эти пять модулей не заметят дневной вызов писателя, которого они касаются. Числовые пороги, которые у них есть, по-прежнему выполняются.

### 8. Плавающий тест выживания колонии

`test_tc01_two_agents_basic_survival_loop` без сида. Он идёт 300 с при `dt=1` и требует оба `sim_time > 290`. Файл не менялся. Каждый изолированный прогон — новый процесс pytest. `main` — это `cbce2fb` (до лабильного слоя). `5fb1235` — родитель этого PR (после PR #37, до коммита консолидации). Сравнение через worktree, без checkout этой ветки.

| Код | Изолированные прогоны | Результат |
| --- | --- | --- |
| Эта ветка `9276b97` | 10 | **10 pass, 0 fail** |
| Родитель `5fb1235` (только PR #37) | 10 | **5 pass, 5 fail** — `sim_time` 115, 228, 235, 240, 257 |
| `main` `cbce2fb` | 10 | **9 pass, 1 fail** — `sim_time` 109, строка 16 |

Полный `pytest Demo` на этой ветке затем уронил тот же тест один раз (`sim_time` 204, строка 17). Это форма «упал в полном прогоне, отдельно проходит», которую описал автор. PR #40 его не внёс: на `main` тот же ассерт уже падает, а коммит до этого PR в этой выборке падал чаще. Не чинилось.

На сборках с двумя уровнями в логе падения ещё сказано, что `expected_wake_interval_s` не задан (запас 3600 с) и `dt` не передан (запас по настенным часам). Сим колонии зовёт `step` / `commit` ядра без `dt`. Это форма issue #39. На `main` ранняя смерть есть и без этих строк: часов хоста ещё не было.

### 9. Тамагочи

`Demo/Tamagochi Chinchilla/src/main.py` отличается от родителя только в двух местах, и оба нужны из-за guard:

- `_run_sleep_consolidation` оборачивает `apply_sleep_learning` и `consolidate_habits` в `learning_allowed()`, затем по-прежнему копирует возвращённый клон в `self.bg_channels`. Без обёртки строгий режим бросает исключение внутри `update_weights`, и живой канал остаётся при старом весе. Внутри обёртки одна положительная память при learning rate 0.05 поднимает go клона выше 0.5 и привычку выше 0 (`test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn`). Ночь по-прежнему учится.
- `load_nowa_state` пишет сохранённые `go_weight` / `nogo_weight` / `habit_strength` внутри `initializing()`.

Файлы тестов тамагочи не менялись. Они прошли внутри прогона Demo. Ядро под тайминги демо не подстраивалось. Исходники колонии, виртуальной компании и Warriner не менялись. Ассерт кредита колонии в `test_qa_pr36_colony_core.py` на сиде 4 живой: рефлекторный override записывает `hide`, зафиксированная награда около −0.085, стабильный Go у `hide` и `rest` остаётся равным 0.5, лабильная метка Go ненулевая только у `hide`.

## Замечания (контракт сна из-за них не падает)

### Среднее — replay в ту же ночь всё ещё пишет Go, NoGo и привычку канала

`_apply_episode_channel_and_habit` — это шаг спеки (захват + 0.07 + EMA привычки), и он идёт один раз. Затем каждый `sleep_cycle` зовёт `_apply_replay_td_bg_unlocked`, который по-прежнему делает `go_delta = beta_sleep · go_scale · td_error` (и NoGo, и `habit_delta = beta_sleep · td_error · 0.2`), с обрезкой `delta_weight_max_per_sleep` (0.05). Шаг 4 спеки — TD-replay стабильного Q. Шаг 7 — шаг Go/NoGo, который вместе с захватом остаётся равен `η_c_sleep`.

Воспроизведение: одна терминальная награда +1, `decay_rate_sleep = 0`, `sleep(cycles=1)`. Go идёт 0.50 → 0.73, не 0.58. Q идёт 0 → 0.075. `total_replays` равен 3. Один только однократный проход (`sleep(cycles=0)`) даёт 0.58, Q остаётся 0. `sleep(cycles=3)` при дефолтном decay доходит до go 0.99 и Q 0.225.

PR называет тождество 0.08 и что SHY идёт следом. Он не говорит, что replay BG всё ещё прибавляется. Формула PR #35 оставлена (спека выводит эти формулы из объёма переделки). Величина одной ночи — сумма обоих писателей. Вопрос владельцу ниже.

### Низкое — `_apply_replay_td_bg` открывает guard

Воспроизведение, строгий режим, без `Agent.sleep`: `agent.sleep_manager._apply_replay_td_bg([episode])` после одной дневной награды. Q идёт 0 → 0.025, отпечаток меняется, после вызова `learning_is_open()` ложь, эпизод не помечен. `sleep_cycle` / `deep_sleep` тоже открывают guard: это API консолидации. Этот метод открывает его для частичного replay без пометки «ровно один раз».

### Низкое — отпечаток по-прежнему не содержит временных цепочек

Писатель не ошибочен. Один консолидированный эпизод создаёт цепочку, изменение которой `stable_fingerprint` не увидит.

## Вопросы владельцу

Шесть вопросов PR остаются. Замеры, которые к ним относятся:

1. Немасштабированный `η_eff` — это то, что делает код. Дофамин 0.95 не меняет метку и посадку 0.58. Подтвердите.
2. Оценка, изменённая после консолидации, — новое наблюдение. Первые go 0.58 не восстанавливаются; новый шаг прибавляется (−0.04 на однократном проходе), replay берёт новую награду. Подтвердите.
3. `register_action_channel` сам входит в `initializing()` и оставляет guard закрытым. Подтвердите эту форму.
4. Быстрый аффект (здесь замерен выход регуляции) днём меняется и в отпечаток не входит. Медленные хранилища меняются во сне и входят в него. Подтвердите.
5. Четырёхчленный счёт задаёт только порядок однократного прохода. Ограниченный возврат EDPC не меняется. Подтвердите, на фоне строки спеки, что приоритет расширяет `_compute_replay_priority`.
6. Q после `sleep(cycles=3)` равен 0.225 на одном вознаграждённом эпизоде (тот же бюджет, который PR называет для 10, 30 или 80). `Q > 0.8` недостижим, пока потолки PR #35 на месте. Порог набора `> 0.22` падает, если пропущен цикл.

Добавлено этим проходом:

7. Должен ли replay перестать писать Go/NoGo/привычку канала теперь, когда есть компенсированный шаг эпизода? Пока он пишет, одна ночь — это 0.08 плюс до 0.05 на replay, а не 0.08, и SHY лишь тянет эту сумму к prior.
8. Должен ли `_apply_replay_td_bg` перестать сам открывать `learning_allowed()` для прямого вызова, как это уже сделано у `apply_sleep_learning`?

---

## Re-check

Commit `70fc8e0` on `team/core-sleep-consolidation`. The three notes above are closed. Verdict of this pass: **PASS**.

1. One terminal reward +1, `decay_rate_sleep = 0`. Go is 0.58 after `sleep(cycles=1)` and after `sleep(cycles=3)` (IEEE 0.50+0.08, within 1e-9). `total_bg_delta_sleep` and `total_weight_delta` are 0. Q is 0 after `sleep(cycles=0)` (no replay) and 0.075 / 0.225 after 1 / 3 cycles (3 and 9 replays). NoGo 0.46 and habit 0.20 stay at the once-pass values.
2. A direct daytime `SleepManager._apply_replay_td_bg` raises `WakingLearningError` in strict mode. Fingerprint and Q stay put, and the episode is not marked. With `NOWA_STRICT_LEARNING=0` the call returns `replays_applied = 0`, logs `SleepManager._apply_replay_td_bg skipped` once, and leaves Q and the fingerprint unchanged.
3. `stable_payload` now has `temporal_chains`. Each row is `signature`, `net_affect`, `stability`, `usage_count`. The chain object still stores `created_at` and `last_updated`; changing those does not change `stable_fingerprint`, changing `net_affect` does. One `sleep(cycles=1)` forms a chain and moves the fingerprint; an agent with no chains serializes `[]`.
4. Audit of the tests touched in `70fc8e0`:

| Test | Change | Verdict |
| --- | --- | --- |
| `test_replay_positive_strengthens_habit_and_value` | Channel coupling `total_bg_delta_sleep == total_weight_delta` became both exactly 0. Q still rises, Go still rises, `total_replays > 0`. | **justified-by-spec** (decision 7). A replay that writes channels again fails the zero delta; a missing capture fails `after_go > before_go`. |
| `test_replay_negative_weakens_habit_without_negative_runaway` | Docstring only. Go still falls, NoGo still rises, weights stay in `[0, 1]`. | **equivalent** |
| `test_credit_assignment_spec_011a` autouse `_replay_q_under_the_sleep_guard` | Module fixture holds `learning_allowed()` around direct `_apply_replay_td_bg` calls. Numeric asserts are unchanged. | **justified-by-spec** (decision 8). The daytime raise is covered by `test_direct_replay_does_not_open_the_learning_guard`. |

5. `docs/specs/issue-13-two-tier-plasticity.md` ends with **Owner decisions after PR B (2026-10-19)** items 1–8 in English and **Решения владельца после PR B (2026-10-19)** items 1–8 in Russian. Items 7 and 8 are the answers to the questions this report added.

`pytest tests -q`: **893 passed, 5 skipped**, 201.67s (891 before this commit; the two new checks in `test_issue13_two_tier.py` account for the difference). `pytest Demo -q`: **999 passed, 6 skipped**, 105.10s. The colony survival test did not fail on this run.

## Повторная проверка

Коммит `70fc8e0` на `team/core-sleep-consolidation`. Три замечания выше закрыты. Вердикт этого прохода: **PASS**.

1. Одна терминальная награда +1, `decay_rate_sleep = 0`. Go равен 0.58 после `sleep(cycles=1)` и после `sleep(cycles=3)` (IEEE-сумма 0.50+0.08, в пределах 1e-9). `total_bg_delta_sleep` и `total_weight_delta` равны 0. Q равен 0 после `sleep(cycles=0)` (replay не было) и 0.075 / 0.225 после 1 / 3 циклов (3 и 9 replay). NoGo 0.46 и привычка 0.20 остаются на значениях однократного прохода.
2. Прямой дневной `SleepManager._apply_replay_td_bg` в строгом режиме бросает `WakingLearningError`. Отпечаток и Q не меняются, эпизод не помечается. При `NOWA_STRICT_LEARNING=0` вызов возвращает `replays_applied = 0`, один раз пишет в лог `SleepManager._apply_replay_td_bg skipped` и не меняет Q и отпечаток.
3. В `stable_payload` появился `temporal_chains`. Строка — это `signature`, `net_affect`, `stability`, `usage_count`. У объекта цепочки по-прежнему есть `created_at` и `last_updated`; их правка не меняет `stable_fingerprint`, правка `net_affect` меняет. Один `sleep(cycles=1)` создаёт цепочку и сдвигает отпечаток; агент без цепочек сериализует `[]`.
4. Аудит тестов, затронутых в `70fc8e0`:

| Тест | Изменение | Вердикт |
| --- | --- | --- |
| `test_replay_positive_strengthens_habit_and_value` | Связка `total_bg_delta_sleep == total_weight_delta` заменена на оба значения ровно 0. Q по-прежнему растёт, Go по-прежнему растёт, `total_replays > 0`. | **justified-by-spec** (решение 7). Replay, который снова пишет каналы, уронит нулевую дельту; пропавший захват уронит `after_go > before_go`. |
| `test_replay_negative_weakens_habit_without_negative_runaway` | Только docstring. Go по-прежнему падает, NoGo растёт, веса в `[0, 1]`. | **equivalent** |
| autouse `_replay_q_under_the_sleep_guard` в `test_credit_assignment_spec_011a` | Фикстура модуля держит `learning_allowed()` вокруг прямых вызовов `_apply_replay_td_bg`. Числовые ассерты не менялись. | **justified-by-spec** (решение 8). Дневной бросок закрыт тестом `test_direct_replay_does_not_open_the_learning_guard`. |

5. `docs/specs/issue-13-two-tier-plasticity.md` заканчивается разделом **Owner decisions after PR B (2026-10-19)**, пункты 1–8 на английском, и **Решения владельца после PR B (2026-10-19)**, пункты 1–8 на русском. Пункты 7 и 8 — ответы на вопросы, которые добавил этот отчёт.

`pytest tests -q`: **893 passed, 5 skipped**, 201.67 с (до коммита было 891; разница — две новые проверки в `test_issue13_two_tier.py`). `pytest Demo -q`: **999 passed, 6 skipped**, 105.10 с. Тест выживания колонии в этом прогоне не упал.
