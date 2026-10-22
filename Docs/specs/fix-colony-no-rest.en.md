# Fix — colony founders exhaust without a sleep bout

Part of #39 and #13. Does not close them.

The core in `src/` is not retuned. UI speed is a host clock. This note records the runs that located the failure and the host change that removes it.

---

## 1. What the owner saw

At UI speed 10x, founders of `Demo/Colony chinchillas` die of exhaustion while food, hay, and water are still available. They do not complete a sleep bout. The same death appears in offspring (observed here at generation 1, age 240 s). Speed 1x keeps the same founders alive and near full energy, but Process S stays near 0, so the night never starts there either.

## 2. How UI speed becomes `dt`

`ColonyGUI._sim_tick` advances the runner by `real_dt * speed` (`colony_gui.py`). The base `real_dt` is `SIM_BASE_STEP_S = 1/12` s (`app.py`). If a tick costs more than `SIM_STEP_COST_TARGET_S` (0.012 s), `_apply_sim_load_adaptation` widens that base up to `SIM_MAX_STEP_S` (0.25 s) and the speed multiply happens after. A live 10x UI therefore runs decisions of length `(1/12)*10 = 0.833` s at the first frames and `0.25*10 = 2.5` s once the step is slow. Decisions per simulation second: 12 at 1x, 1.2 at nominal 10x, 0.4 at load-adapted 10x.

## 3. Runs (4 founders, `GenomeVector.random`, headless, no window)

| Clock | dt | Seed | Sim time | Result |
| --- | --- | --- | --- | --- |
| 1x | 1/12 | 1 | 180 s | 4 alive. Energy 0.97–0.99. Food 1.00, water 0.86. Wake 0.0000–0.0006. |
| 10x load | 2.5 | 2 | 2000 s | Exhaustion at age 890 s (energy 0.065, wake 0.357) and an offspring at age 240 s (energy 0.066, wake 0.112). Bowls still above 0.9. |
| 10x load | 2.5 | 1 | 2000 s | Exhaustion at age 1325 s (energy 0.070, wake 0.493). 3 births. |

1x counters for seed 1: 2160 decisions. `update_waking(elapsed)` added the compressed sim time (accumulated waking time ~4820 s). 1071 chosen sleep actions were all below onset 0.7, and all 1071 aborted on the same tick (`kept = 0`). Those naps removed 0.402 of Process S. `Agent.step` still calls `wakefulness.update_waking()` with no elapsed (`src/agent.py` around the waking update, wall clock in `WakefulnessState.update_waking`). That wall contribution over the 180 s run summed to 0.016 of Process S. It is not the failure.

## 4. Cause

Two host clocks, both outside the core learning rules.

**Sleep bout.** `_apply_sleep_recovery` treated every chosen `sleep` as a physiological bout: at least `SLEEP_MIN_RECOVERY_DURATION_S` (30) physiological seconds, then `_should_wake_now` if Process S is under `0.7 * 0.7 = 0.49`. A nap taken while rested therefore discharges Process S and wakes on the same tick. At 12 decisions per second those naps erase accumulation (wake stays ~0, energy stays high because the body rests on every short tick). At 0.4 decisions per second the discharge no longer wins, so wake climbs, but a bout that starts below 0.7 still ends as soon as it falls through 0.49. The run never enters the onset path (`wake >= 0.7`, which already forces the bout via `_should_sleep_now`). No completed night, so sleep never restores the body.

**Body energy.** `autonomous_tick` spends `cognitive_cost * load * dt` and rests once per call (`rest_time` 0.3 or 1.0, not multiplied by `dt`). `organism_step` also clamps `dt` to 1 s. A 2.5 s UI tick therefore integrates about one second of body rest and one second of body cost, while colony unmet-need cost uses the full 2.5 s. Per simulation second the 1x run rests on every 1/12 s tick; the 10x run does not. Energy falls to the exhaustion threshold (0.08) with the bowls still full. Offspring use the same `sim_step`, so the death repeats.

`src/agent.py` wall-clock `update_waking()` is not changed. The colony already passes game `dt` into the host clock and applies its own compressed Process S update. Adding `dt` again inside the core would double-count, and the measured wall term is ~0.016 per 180 s.

## 5. Change

Host only, `Demo/Colony chinchillas/src/colony_agent.py`.

- A chosen `sleep` below onset becomes `rest` and does not call `update_sleeping`. Onset (`_should_sleep_now`) and an open bout (`_should_continue_sleeping`) still run recovery and hysteresis. Stable Q/V, habits, and Go/NoGo stay sleep-only.
- `_advance_autonomous_body` splits a UI `dt` into slices of `COLONY_BODY_STEP_S` (1/12 s, the speed-1 base) before `autonomous_tick`. Cost and rest then match speed 1 for the same simulation second. Asleep ticks still skip the body; the bout restores energy.

No core coefficient, threshold, or plasticity interval is edited.

## 6. Check

`Demo/Colony chinchillas/tests/test_fix_colony_no_rest.py`

- Exploratory sleep at Process S 0.2 does not discharge it, at a 2.5 s step.
- Onset starts a bout at both 1/12 s and 2.5 s.
- Four founders, seed 1, 90 s at 1/12: alive, energy > 0.5, bowls above half, max Process S > 0.03 (this is ~0 on the unfixed 1x run).
- Four founders, seed 2, 1600 s at 2.5 s: no exhaustion, energy > 0.2, bowls above 0.4, someone is in a sleep bout (seed 2 died at 890 s before the fix; onset is about 1344 s).

Issue #39's `xfail` on `test_tc01_two_agents_survive_300s` stays unless that test passes on its own. This fix does not retune unmet-need rates.
