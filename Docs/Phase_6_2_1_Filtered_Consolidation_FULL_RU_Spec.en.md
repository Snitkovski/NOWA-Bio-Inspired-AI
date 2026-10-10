# Phase 6.2.1 — Filtered Consolidation (Full Specification)

Russian version: [Phase_6_2_1_Filtered_Consolidation_FULL_RU_Spec.ru.md](Phase_6_2_1_Filtered_Consolidation_FULL_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## 1. Purpose

A strict mechanism of selective consolidation of episodic memory into long-term representations.

Aims:
- exclusion of noisy consolidation
- transfer of stable patterns
- preservation of the stability of the Value Layer
- prevention of self-amplifying loops

## 2. Architectural Constraints

It is NOT admitted to:
- alter reward
- alter TD error
- modify online alpha
- influence decision policy
- modulate sleep_alpha through ACh

The mechanism operates only in sleep mode.

## 3. Admission Criteria

An episode is admitted if:
- |TD_mean| ≥ td_threshold
- TD_variance ≤ td_variance_cap
- salience ≥ salience_threshold
- reinforcement_count ≥ min_reinforcement
- value_variance_ratio < variance_gate_threshold
- ACh_effective ≥ ach_min_for_consolidation
- stability_flag == TRUE

## 4. Consolidation Score

```text
ACh_effective = max(0, ACh_snapshot - ach_baseline)

consolidation_score =
    w_td * |TD_mean| +
    w_salience * salience +
    w_importance * importance +
    w_ach * ACh_effective +
    w_encoding * encoding_strength
```

Constraint:

```text
consolidation_score ≤ consolidation_cap
```

## 5. Update in Sleep

```text
delta_value =
    sleep_alpha *
    consolidation_score *
    sign(TD_mean)
```

Constraints:
- sleep_alpha ≤ sleep_alpha_cap
- |delta_value| ≤ per_update_cap
- L2(delta_value_total) ≤ max_l2_update_per_cycle
- Σ|delta_value| ≤ global_sleep_update_budget

## 6. Variance Gate

```text
variance_gate = max(0, 1 - value_variance_ratio)
delta_value *= variance_gate
```

If value_variance_ratio ≥ 1.0, sleep is prohibited.

## 7. Diagnostics

The following are logged:
- total_episodes_examined
- total_episodes_consolidated
- rejected_due_to_* reasons
- mean_consolidation_score
- sleep_update_l2_total
- variance_ratio
- consolidation_ratio

## 8. Anti-patterns

- Consolidation of every episode
- Removal of the variance gate
- Ignoring the sleep budget
- Direct modification of TD

## 9. Test Cases

1. Noise is not consolidated
2. High TD together with stability leads to consolidation
3. High variance blocks sleep
4. Budget overflow stops sleep
5. A stress test of 5000 cycles shows no growth of variance
