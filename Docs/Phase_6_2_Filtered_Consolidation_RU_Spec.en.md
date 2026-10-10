# Phase 6.2 --- Filtered Consolidation

Russian version: [Phase_6_2_Filtered_Consolidation_RU_Spec.ru.md](Phase_6_2_Filtered_Consolidation_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Purpose

A mechanism of selective consolidation of episodic memory into long-term
representations.

## Architectural boundaries

-   Does not change reward
-   Does not change TD error
-   Does not affect online alpha
-   Operates only in sleep

## Admission criteria

An episode is admitted if: - \|TD_mean\| ≥ td_threshold - salience ≥
salience_threshold - reinforcement_count ≥ min_reinforcement -
value_variance_ratio \< variance_gate_threshold - ACh_effective ≥
ach_min_for_consolidation

## Constraints

-   sleep_alpha ≤ sleep_alpha_cap
-   max_l2_update_per_cycle
-   global_sleep_update_budget
-   consolidation_cap
-   variance gate is mandatory
-   ACh does not affect sleep_alpha

## Anti-Patterns

-   Consolidation of every episode
-   Removal of the variance gate
-   Increasing sleep_alpha via ACh
-   Ignoring the budget

## Test cases

1.  A noisy episode → is not consolidated
2.  A repeated significant episode → is consolidated
3.  High variance → no consolidation
4.  High ACh with low TD → no consolidation
5.  Budget exceeded → sleep stops
