# Issue #13 — Colony demo on two-tier plasticity

Stage: adapt `Demo/Colony chinchillas` to the merged core (PRs #37, #40, #41).
The core in `src/` is not retuned for the colony. Host rules: [Docs/architecture/two-tier-plasticity.en.md](../architecture/two-tier-plasticity.en.md).
Normative core spec: [issue-13-two-tier-plasticity.md](issue-13-two-tier-plasticity.en.md) (owner decisions after PR A and PR B included).

---

## 1. Goal

`ChinchillaAgent` is a host of the general-purpose core.

- Every simulation tick supplies game `dt` (seconds) on the host-clock contract.
- Waking outcomes stay in the labile tier.
- Stable parameters change only inside `Agent.sleep()` (which opens the learning guard). `SleepManager.sleep_cycle` is the same guard when the core calls it from that path.
- Construction, save/load restore, genome application, and channel registration run under `initializing()`.

## 2. Host time

`sim_step(dt)` advances the core host clock by that game `dt` once:

- When the tick calls `step(..., decision_only=True)`, it passes `dt=dt`. The following `commit_executed_transition` omits `dt`, so the tick is not applied twice.
- When the tick does not call `step` (continued sleep recovery, or `replaced_policy_action`), it calls `advance_time(dt)` before `commit_executed_transition`.

The wall-clock fallback in `Agent._advance_host_clock` is not used and is not modified. Non-finite or negative `dt` is passed as `0`, which is still an explicit `dt`.

`step` stores that same `dt` as `time_elapsed` for the later commit. On ticks that call `step`, fast affect therefore integrates game seconds. Ticks that skip `step` only move the host clock via `advance_time` and leave the previous commit context's `time_elapsed` as the core already did.

`expected_wake_interval_s` is `colony_expected_wake_interval_s()`:

- sleep onset at `SLEEP_WAKEFULNESS_THRESHOLD` (0.7);
- waking resumes at `0.7 * SLEEP_HYSTERESIS` (0.49);
- span `0.21`;
- each simulation second adds `WAKEFULNESS_ACCUMULATION_FACTOR` (30) physiological seconds;
- physiological pressure climbs at `WakefulnessState.ACCUMULATION_RATE` (`1 / (16 * 3600)`).

That is `0.21 * 16 * 3600 / 30 = 403.2` simulation seconds: the steady gap between sleep bouts, in the same units as `dt`. `tau_labile_s` stays the core default (`1.0 *` that interval). The first bout from full rest is longer; the configured value is the repeating wake, not the 3600 s core fallback.

Colony sleep consolidation is unchanged: `_apply_sleep_recovery` still calls `Agent.sleep(cycles, sleep_duration_seconds=0.0)` after `SLEEP_CONSOLIDATION_INTERVAL_S` of compressed sleep. That call is the stable writer.

## 3. What may be written while awake

Waking `commit_executed_transition(reward=...)` tags `L_Q` and channel `L_go` / `L_nogo` only. Habit strength, stable Q/V, Go/NoGo, slow affect statistics, and temporal chains are not written by colony code on a waking tick.

Fast affect (axis position on `affective_space`) remains state and may move while awake. Dataset habit priors are copied in `_seed_habit_bootstrap` inside `initializing()`, once, at construction. They are not refreshed from outcomes while awake.

## 4. Initialization and load

- `register_action_channel` enters `initializing()` itself (core, owner decision after PR B). The colony does not assign `go_weight` / `nogo_weight` / `habit_strength` directly.
- A genome passed to the constructor, and a recombined genome on a newborn, is applied inside `initializing()`.
- `ColonyStorage` builds a new agent (habit seed and channels included) and restores saved physiology, fast affect, and social fields inside `initializing()`. The colony JSON does not store Q/V or habit tables; those stay on the fresh agent until the next `Agent.sleep()`.

## 5. Check

`Demo/Colony chinchillas/tests/test_two_tier_host.py`: four waking `sim_step(1)` calls leave `stable_fingerprint` unchanged, the host clock equals `4`, and `_dt_warning_sent` stays false. One `Agent.sleep(cycles=1)` changes the fingerprint. The test sets `NOWA_STRICT_LEARNING=1`.

The colony suite under that variable must not raise `WakingLearningError`.

## 6. Out of scope

- Issue #39 (exhaustion / unmet-need cost not invariant at ×10). Existing `xfail` stays.
- Backlog issues #14–#31. Not fixed here.
- Tamagochi Chinchilla, Virtual company, Warriner Validation.
- Core fallbacks, replay caps, and plasticity coefficients.

## 7. Acceptance

1. Colony ticks pass game `dt` and do not depend on the wall-clock fallback.
2. `expected_wake_interval_s` is the derived wake bout above, not 3600.
3. Waking colony learning does not change `stable_fingerprint`. Sleep through `Agent.sleep` does.
4. Habit seeding, genome application, and colony load run under `initializing()`.
5. `pytest` of `Demo/` passes with and without `NOWA_STRICT_LEARNING=1`, with no `WakingLearningError` from the colony.
