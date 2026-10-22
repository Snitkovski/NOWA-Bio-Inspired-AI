# QA round 1: PR #35 — sleep value replay, BG sleep, neuromodulator fixed points

> **Superseded in part by issue #13** (two-tier plasticity, PR #37–#40). Sleep replay and BG decay remain; episode capture, exactly-once habits/Go/NoGo, and labile/stable split are documented in `Docs/specs/issue-13-two-tier-plasticity.en.md`.
>
> **Partially superseded by issue #13** (PR #37–#40). Replay and SHY from PR #35 remain; capture and labile/stable split are in spec #13.

Branch: `team/sleep-learning-core` (`33c3dc3` plus QA commit)
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/35
Issues: #9, #10, #12
Comparison base: `d55eeef` (merged PR #33). Product code was not changed. Senior test asserts were not weakened.

## Verdict

PASS

## Coverage

- scenarios: 16 passed / 0 failed / 0 not run
- `pytest tests`: 820 passed, 5 skipped
- independent file `tests/test_qa_pr35_sleep_learning.py`: 16 passed
- 5 skips are pre-existing (`autonomous runtime` / Drive MCP), unrelated to this PR

Passed:

1. #9. Table with different V: δ = r + γV(s') − Q. With Q(s)=0.10, V(s')=0.80, γ=0.95, r=0 and TD snapshot = −1 replay raises Q by 0.132 (step 0.2·δ) without overshooting the target. Snapshot with “plus” sign when Q is already above target moves Q down; over 16 passes Q does not go below target and approaches within 0.05.
2. #9. Terminal bootstrap = 0 even when V(s')=0.90. Open transition with same r and current Q gets a larger step than terminal.
3. #9. Gate on state value variance. Constant reward 0.4 (24 steps, one action): variance < 0.5, sleep replays, `rejected_due_to_variance_gate` = 0. Alternating ±1 (40 steps, same action): variance 0.88, 0 replays, variance gate rejection present, Q unchanged.
4. #9. Credit. Agent writes `episode_step` 0,1,2 and new `trajectory_id` after `terminal=True`. Mixed with foreign trajectory, depth is computed inside its own: left reward anchor does not become right anchor. `_compute_offline_td_error` is called from `_replay_signed_td`.
5. #10. 50 cycles with no new outcomes and no episodes: Go/NoGo/habit move toward prior by (1−0.05)^50, not to 0. Go stays around 0.44 with prior 0.40 and start 0.90.
6. #10. Sleep with cap 1.6: two channels with L1 0.9 and 0.8 unchanged, channel with L1 3 shrinks only that one to L1 1.6.
7. #10. One positive record visible in `apply_sleep_learning` (`forget_rate=0`), Go rises above prior 0.50, cache empty after `sleep()`.
8. #10. Zero outcome on sleep path does not move Go/NoGo relative to sleep without record (both stay 0.62 / 0.41). Cache empty after sleep.
9. #12. 40 updates with reward and `use_reward_for_dopamine=False`: DA = 0.084, not 0 and within 0.05 of baseline 0.1. Rest without signal: DA and ACh stay at baseline.
10. #12. 40 agent steps with reward 1: DA = 0.216, not 0 and not 1. Novelty spike after repetition opens ACh gate (agent 0 → 0.142, ACh 0.059 → 0.231). `apply_impulses` clamps impulse ±0.25 both ways.
11. Old save without `prior_*`, `trajectory_*`, `episode_step`, and `ach_running_mean` opens. Go/NoGo/habit and Q unchanged. Prior taken as loaded weight, `ach_running_mean` becomes baseline. Five decay cycles after that do not shift weights.
12. Regressions #33. Full pytest includes contextual bandit (`PYTHONHASHSEED` 0/1/7, `tests/test_reward_bandit.py`) and prior QA checks for feedback addressing, idempotency, and `rng_seed`. Separately: repeated same rating does not lengthen `bg_sleep_memories`; feedback on old episode id does not overwrite new episode; two runs with `rng_seed=7` give one 8-step trace.

## Defects

None new.

## Old tests: what asserts mean

Retargeted to new contract, not weakened.

- `test_phase_6_2_filtered_consolidation.py`. Spread of V across table no longer required to silence replay: test requires `value_variance_ratio >= 1`, `total_replay_blocked == 0`, `total_replays >= 1`, `rejected_due_to_variance_gate == 0`. Sleep budget in overflow test reduced from 0.03 to 0.004 because recalculated TD step is smaller than old signed step. Same check: sum of steps not above budget and `replay_blocked is True`. `per_update_cap` untouched.
- `test_sleep_replay_td_bg.py`. Blocking comes from `expected_reward_var` of the state, not foreign cells. Outcome cache cleared so outcome does not mask replay ban. Same asserts: variance gate refusal, zero replays, Go unchanged. Sign test expects move against stale snapshot and still holds step in `per_update_cap`.
- `test_phase_6_1_ach.py`. Priority does not change from cross-state spread and falls from variance of this state's estimate. “High variance gives lower priority” comparison preserved.
- `test_credit_assignment_spec_011a.py`. Non-anchors reward 0.05 so they stay below anchor threshold and live TD is non-zero. TD snapshot is no longer an update. Depths and `sleep_update_count == 3` in place.

## Senior questions

Not decided here. Measurements on this commit:

1. DA around 0.22 at constant TD +0.1 and ACh around 0.06. On agent after 40 reward steps: DA = 0.2164, ACh = 0.0616, `ach_running_mean` = 0.0618, ACh gate = 0. Separate run “rest + DA impulse +0.1” gives DA = 0.2309 and ACh = 0.0583. Field without separate DA signal over same 40 reward steps stays at baseline: DA = 0.0842, ACh = 0.1037. One integrator step without new impulse drops agent DA from 0.2164 to 0.1153. So 0.22 is level right after impulse, not a fixed point of the field. Gate does not stick: next step with novelty=1 raises ACh to 0.2308 and gate to 0.142. Whether 0.06 level vs baseline 0.1 is acceptable remains author decision: “gate opens again” holds, “field rest = baseline” holds.

2. `forget_rate>0` in `apply_sleep_learning`. Direct call with `forget_rate=0.10` and empty memory moves Go 0.80 → 0.72, toward zero, not prior. Sleep passes `forget_rate=0` then decays toward prior. Direct API vs sleep path mismatch confirmed, not closed.

3. TD impulse outside main integrator. In `Agent.step`, `update_from_signals` then `apply_impulses` with TD dopamine (impulse capped ±0.1 in `compute_dopamine_delta` and again ±0.25 in `apply_impulses`). Impulse is not in the same tick's Euler step. So DA read at end of step is above baseline by not-yet-relaxed impulse. Next integrator step without impulse returns DA to baseline as above.

Nearby, not a defect of this DoD: direct `apply_sleep_learning` with outcome 0 and `forget_rate=0` still takes punishment branch (Go 0.62 → 0.60, NoGo 0.41 → 0.42). Sleep path drops `|outcome| <= 1e-12` before call and does not punish Go/NoGo. `ActionChannel.record_outcome` still increments `failure_count` on zero; does not affect Go/NoGo weights. Episodes without `trajectory_id` land in one credit group — new steps write ids, old save without field still opens.

## Recommendations

- Keep direct `forget_rate>0` and zero outcome in `apply_sleep_learning` an explicit decision: same prior and zero filter as sleep, or short docstring that this is not the `sleep()` path.
- For DA/ACh on agent, fix which reading is the fixed point: field before impulse or level at end of step. End of step now sits around 0.22 / 0.06 by design.

## Release readiness

Yes, with caveats on the three senior questions above. They do not break #9, #10, #12 checks on sleep and agent step paths. Merge if author accepts DA ~0.22 and ACh ~0.06 as post-impulse level, not as departure of the fixed point.
