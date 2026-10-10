# Phase 5.A.1 --- Integration of the Basal Ganglia into the Sleep Cycle

Russian version: [Phase_5_A_1_BG_Sleep_Replay_RU_Spec.ru.md](Phase_5_A_1_BG_Sleep_Replay_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Replay-Driven TD Consolidation (Full Specification)

------------------------------------------------------------------------

# 1. Phase Status

Type: architectural extension\
Priority: high\
Dependencies: - Value Layer (Phase 5.0.1) - Temporal system (T1/T2/T3) -
BasalGangliaLearning (existing class) - Stability Monitor (Phase
4.5)

This phase does not change: - the planning layer - policy selection at runtime -
affective dynamics directly

------------------------------------------------------------------------

# 2. Purpose of the Phase

Implement biologically plausible offline consolidation of habits during
sleep, based on:

-   TD-error
-   episode replay
-   bounded reinforcement
-   strict protection against self-amplification

------------------------------------------------------------------------

# 3. Architectural Changes

`sleep_cycle()` must add:

1.  Formation of `replay_sample`
2.  Offline TD update
3.  BG reinforcement
4.  Soft decay
5.  Normalization
6.  Stability check

sleep_cycle(): if instability_flag: skip replay

    replay_sample = select_replay()

    for episode in replay_sample:
        td = compute_td_error_offline(...)
        update_value(td)
        update_bg_weights(td)

    apply_decay()
    normalize()

------------------------------------------------------------------------

# 4. Replay Selection

## 4.1 Priority Function

priority = w1 \* \|TD_error_snapshot\|\
+ w2 \* salience\
+ w3 \* importance

Where: - `TD_error_snapshot` was stored during wakefulness - salience does
not depend on the current affect - importance is computed without using
the current state of the axes

## 4.2 Constraints

-   replay_budget_per_sleep ≤ K
-   max_replay_per_episode ≤ N
-   stochastic weighted sampling
-   if variance(ValueLayer) \> threshold → replay is forbidden

------------------------------------------------------------------------

# 5. Offline TD Update

V(s) ← V(s) + alpha_sleep \* TD_error

Constraints:

-   alpha_sleep ≤ 0.25 \* alpha_online
-   TD_error must be passed through clip()
-   \|ΔV\| ≤ delta_value_max_per_sleep
-   the total \|ΔV\| over a sleep ≤ value_total_cap

Forbidden: - using the current affect as a multiplier of TD - increasing
gamma

------------------------------------------------------------------------

# 6. Basal Ganglia Reinforcement

W(s,a) ← W(s,a) + beta_sleep \* clipped(TD_error)

Constraints:

-   beta_sleep \< beta_online
-   \|ΔW\| ≤ delta_weight_max_per_sleep
-   the total weight increase ≤ weight_total_cap
-   TD_error is clipped

------------------------------------------------------------------------

# 7. Soft Decay

After replay:

W ← W \* (1 - decay_rate_sleep)

Requirements: - decay_rate_sleep is small (for example 0.01--0.05) - decay
is mandatory on every sleep

------------------------------------------------------------------------

# 8. Normalization

For each state s:

sum_a \|W(s,a)\| ≤ weight_norm_cap

If exceeded:

W(s,a) ← W(s,a) \* (weight_norm_cap / current_sum)

Normalization is mandatory.

------------------------------------------------------------------------

# 9. Anti-Runaway Safeguards

Mandatory mechanisms:

1.  The replay budget is bounded
2.  TD clipping
3.  ΔW is bounded
4.  ΔV is bounded
5.  The instability monitor blocks replay
6.  Affective state does not participate directly
7.  Normalization is mandatory

Without any of these items the phase is considered incorrect.

------------------------------------------------------------------------

# 10. System Invariants

After sleep:

-   All weights are finite
-   ValueLayer remains in the range \[-value_cap, value_cap\]
-   There is no exponential growth
-   There are no self-reinforcing loops

------------------------------------------------------------------------

# 11. Test Cases

## 11.1 Strengthening a Useful Habit

Condition: - A repeating s - TD_error \> 0

Expected: - Growth of W(s,a) - Growth of V(s) - weight_norm_cap is not exceeded

------------------------------------------------------------------------

## 11.2 Weakening a Harmful Habit

Condition: - TD_error \< 0

Expected: - Decrease of W(s,a) - No runaway negative growth

------------------------------------------------------------------------

## 11.3 Runaway Protection

Condition: - TD_error is high - Replay is frequent

Expected: - ΔW is bounded - Normalization fires - The system is stable

------------------------------------------------------------------------

## 11.4 Instability Blocking

Condition: - variance(ValueLayer) \> threshold

Expected: - Replay is not executed - Sleep ends without reinforcement

------------------------------------------------------------------------

## 11.5 Affective Isolation Test

Condition: - High affective activation - TD_error ≈ 0

Expected: - The episode does not receive priority - There is no weight growth

------------------------------------------------------------------------

## 11.6 Replay Budget Test

Condition: - replay_budget = K

Expected: - No more than K episodes are processed

------------------------------------------------------------------------

# 12. Phase Completion Criteria

The phase is considered complete if:

-   Habits are strengthened through repetition
-   Negative patterns weaken
-   There is no runaway dynamics
-   ValueLayer is stable
-   The affective circuit does not influence consolidation directly
