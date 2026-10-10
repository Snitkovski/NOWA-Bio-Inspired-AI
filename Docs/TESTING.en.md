# Testing Guide - NOWA Cognitive (Hippocampus 2.0 + Phase 5 EDPC + Spec 011/011a + HIE-003/HIE-002 + Phase 6.2.1 + SAC + Autonomous Runtime + External Interaction Layer + CER + ACC + Dopaminergic TD + Packages A/B/C/D/E/F)

Russian version: [TESTING.ru.md](TESTING.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


Last verified: March 27, 2026.

---

## Current Status

Default codebase suite (excluding Demo):
```text
723 passed, 3 skipped
```

Command used:
```bash
pytest -q tests
```

GenomeVector focused run:
```text
17 passed in 0.04s
```

Command used:
```bash
pytest -q tests/test_genome_vector.py
```

EpigenomeSnapshot focused run:
```text
16 passed in 0.04s
```

Command used:
```bash
pytest -q tests/test_epigenome_snapshot.py
```

AgentFactory focused run:
```text
19 passed in 0.26s
```

Command used:
```bash
pytest -q tests/test_agent_factory.py
```

FitnessEvaluator focused run:
```text
21 passed in 0.22s
```

Command used:
```bash
pytest -q tests/test_fitness.py tests/test_fitness_agent_integration.py
```

SwarmEnvironment focused run:
```text
20 passed, 1 warning in 0.30s
```

Command used:
```bash
pytest -q tests/test_swarm_environment.py
```

Emergent evolution (Package F) focused run:
```text
20 passed in 0.08s
```

Command used:
```bash
pytest -q tests/test_emergent_evolution_v2.py
```

Wakefulness + circadian focused run:
```text
44 passed in 1.01s
```

Command used:
```bash
pytest -q tests/test_wakefulness.py tests/test_agent_lifetime_save_load.py
```

Neuromodulator interaction focused run:
```text
44 passed in 0.22s
```

Command used:
```bash
pytest -q tests/test_acc_conflict_modulation.py tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
```

Decision arbitration + planning + credit assignment focused run:
```text
68 passed in 0.40s
```

Command used:
```bash
pytest -q tests/test_decision_arbitration_spec_011.py tests/test_credit_assignment_spec_011a.py tests/test_deliberative_planning_spec_011.py tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py tests/test_sleep_replay_td_bg.py tests/test_value_layer.py
```

Hippocampal imagination focused run:
```text
15 passed in 0.20s
```

Command used:
```bash
pytest -q tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py
```

EDPC <-> SAC sync focused run:
```text
21 passed
```

Command used:
```bash
pytest -q tests/test_edpc_sac_synchronization.py tests/test_phase_5_edpc.py tests/test_value_layer.py tests/test_value_layer_storage.py
```

SAC focused run:
```text
16 passed in 0.44s
```

Command used:
```bash
pytest -q tests/test_semantic_action_consolidation.py tests/test_sleep_replay_storage.py
```

CER/BG focused run:
```text
19 passed in 0.22s
```

Command used:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py tests/test_basal_ganglia_integration_spec.py
```

ACC focused run:
```text
15 passed in 0.16s
```

Command used:
```bash
pytest -q tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

CER/BG/ACC focused run:
```text
34 passed in 0.71s
```

Command used:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py tests/test_basal_ganglia_integration_spec.py tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

External interaction focused run:
```text
15 passed in 0.27s
```

Command used:
```bash
pytest -q tests/test_external_interaction_layer.py
```

Long stress test (Phase 6.2 filtered consolidation, opt-in):
```text
1 passed, 9 deselected in 5.34s
```

Hippocampus 2.0 focused run:
```text
13 passed in 0.11s
```

Command used:
```bash
pytest -q tests/test_hippocampus_2_0.py
```

Combined hippocampus regression + spec run:
```text
24 passed in 0.28s
```

Command used:
```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

Command used (PowerShell):
```powershell
$env:RUN_LONG_HORIZON_FILTERED_CONSOLIDATION='1'
pytest -q tests/test_phase_6_2_filtered_consolidation.py -k stress_5000 -rs
Remove-Item Env:RUN_LONG_HORIZON_FILTERED_CONSOLIDATION
```

---

## Main Commands

Run all default tests:
```bash
pytest -q tests
```

Run GenomeVector tests:
```bash
pytest -q tests/test_genome_vector.py
```

Run EpigenomeSnapshot tests:
```bash
pytest -q tests/test_epigenome_snapshot.py
```

Run AgentFactory tests:
```bash
pytest -q tests/test_agent_factory.py
```

Run FitnessEvaluator tests:
```bash
pytest -q tests/test_fitness.py tests/test_fitness_agent_integration.py
```

Run SwarmEnvironment tests:
```bash
pytest -q tests/test_swarm_environment.py
```

Run emergent evolution tests (Package F):
```bash
pytest -q tests/test_emergent_evolution_v2.py
```

Run only Phase 6.1 tests:
```bash
pytest -q tests/test_phase_6_1_ach.py
```

Run neuromodulator interaction bundle:
```bash
pytest -q tests/test_acc_conflict_modulation.py tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
```

Run only Phase 6.2 tests:
```bash
pytest -q tests/test_phase_6_2_filtered_consolidation.py
```

Run SAC tests:
```bash
pytest -q tests/test_semantic_action_consolidation.py tests/test_sleep_replay_storage.py
```

Run only Phase 5 EDPC tests:
```bash
pytest -q tests/test_phase_5_edpc.py
```

Run Spec 011/011a regression bundle:
```bash
pytest -q tests/test_decision_arbitration_spec_011.py tests/test_credit_assignment_spec_011a.py tests/test_deliberative_planning_spec_011.py tests/test_imagination_engine_spec_001.py tests/test_hie_002.py tests/test_hie_003.py
```

Run replay regression tests:
```bash
pytest -q tests/test_sleep_replay_td_bg.py tests/test_phase_6_2_filtered_consolidation.py
```

Run dopaminergic TD/value-layer focused tests:
```bash
pytest -q tests/test_dopaminergic_td_layer.py tests/test_value_layer_integration.py tests/test_value_layer_storage.py
```

Run autonomous organism + persistence tests:
```bash
pytest -q tests/test_autonomous_organism.py tests/test_agent_lifetime_save_load.py
```

Run external interaction layer tests:
```bash
pytest -q tests/test_external_interaction_layer.py
```

Run hippocampus regression + spec tests:
```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

Run BG integration spec tests:
```bash
pytest -q tests/test_basal_ganglia_integration_spec.py
```

Run CER-focused tests:
```bash
pytest -q tests/test_emotional_regulation.py tests/test_emotional_regulation_integration.py
```

Run ACC-focused tests:
```bash
pytest -q tests/test_conflict_arbitration_layer.py tests/test_conflict_arbitration_integration.py tests/test_conflict_arbitration_storage.py
```

Run selector/BG/GUI regression bundle:
```bash
pytest -q tests/test_basal_ganglia.py tests/test_basal_ganglia_integration_spec.py tests/test_gui_refactoring.py
```

Run with short traceback:
```bash
pytest -q --tb=short
```

---

## Phase 5.x TD + EDPC Coverage

Files:
- `tests/test_dopaminergic_td_layer.py`
- `tests/test_value_layer_integration.py`
- `tests/test_value_layer_storage.py`
- `tests/test_phase_5_edpc.py`

Covered scenarios:
1. Signed phasic TD behavior (`delta_sign`, burst/dip) for positive/negative/zero surprise.
2. Raw-vs-clipped TD diagnostics (`delta`, `delta_modulated`, `delta_clipped`) under saturation.
3. CER stress effects: reduced effective alpha and amplified negative phasic dip.
4. Reward handling contract: `reward_raw` is preserved, optional `reward_scale` controls effective TD reward.
5. Clip saturation telemetry: `td_was_clipped`, `online_td_clip_count`, `online_td_clip_frequency`, EMA tracking.
6. Adaptive online TD clip tuning toward target clip-rate.
7. Exploration coupling sign and 20% cap behavior.
8. Zero-baseline exploration unfreeze via `exploration_unfreeze_floor`.
9. Agent-level guardrail in inhibit mode prevents exploration collapse (`0.05..0.20` floor).
10. Slow tonic dopamine drift relative to phasic spikes (`tonic_slow_rate`, `mean_phasic`, `tonic_level`).
11. Long-run tonic trend follows running phasic direction under sign flips.
12. Save/load persistence for TD/adaptive-clip and tonic-dynamics fields (`td_tonic_slow_rate`, `td_phasic_mean`, `td_tonic_target_base`).
13. Stable stream: confidence/stability grow, effective alpha dampens.
14. Noisy stream: expected mean converges with higher variance and lower confidence than stable stream.
15. Structural shift: high-confidence mismatch triggers prediction shock and temporary plasticity increase.
16. Replay-priority EDPC formula uses TD magnitude, shock flag, and expectation stability.
17. Runtime metrics exposure: confidence/stability distributions, shock frequency, alpha trajectory, replay diversity.

---

## Spec 011 / 011a Coverage

Files:
- `tests/test_decision_arbitration_spec_011.py`
- `tests/test_deliberative_planning_spec_011.py`
- `tests/test_imagination_engine_spec_001.py`
- `tests/test_hie_002.py`
- `tests/test_hie_003.py`
- `tests/test_credit_assignment_spec_011a.py`
- `tests/test_sleep_replay_td_bg.py`

Covered scenarios:
1. Decision mode switching (`HABITUAL`/`DELIBERATIVE`) with uncertainty hysteresis.
2. Uncertainty EMA and uncertainty-driven policy temperature.
3. Policy reliability coupling with action stability and replay causality.
4. Deliberative planning pressure bias before BG selection.
5. Rollout depth adaptation by uncertainty.
6. Similarity-filtered episodic planning candidates.
7. Rollout valuation as max discounted trajectory return.
8. Value-of-information exploration bonus (`gain * (1 - confidence)`).
9. Deliberative planning safety guards (`support >= 0.05`, `confidence >= planning_min_confidence`).
10. Deliberative planning complexity guards (`actions <= 32`, `samples <= 8`, `depth <= 6`).
11. Planning-disabled and empty-memory skip behavior.
12. HIE-001 compatibility path is preserved via `Agent._generate_imagined_rollouts(...)`.
13. HIE-002 structured imagination is integrated (`generate_structured_imagination`) with temporal stitching.
14. HIE-003 multi-action tree imagination is integrated (`generate_action_tree_imagination`) with root-action value aggregation.
15. HIE-003 complexity guards: `action_branching<=4`, `max_tree_nodes<=128`, `depth<=5`.
16. HIE-002 fallback complexity guards: `samples<=8`, `depth<=5`, `branching<=4`, `nodes<=96`, `edges<=192`.
17. HIE confidence invariant: trajectory confidence is clamped to `[0, 1]`.
18. Blend-based rollout composition is validated (`memory/imagined` interpolation via `imagination_value_blend`).
19. HIE-disabled mode keeps planning behavior on legacy memory-only path.
20. Reward-anchored causal depth assignment (explicit reward / TD shock / midpoint fallback).
21. Credit-window usage and eligibility-trace diagnostics in replay stats.

---

## Phase 6.1 Coverage

File: `tests/test_phase_6_1_ach.py`

Covered scenarios:
1. Novelty spike increases ACh, online alpha, and replay priority.
2. Stable repetition decreases ACh.
3. Novelty filter smooths noisy ACh spikes.
4. Saturation safety: ACh clamp and online alpha soft cap.
5. ACh decays toward baseline without novelty.
6. ACh does not change TD error directly.
7. No systematic alpha bias when ACh equals baseline.
8. Sleep alpha is not scaled by ACh.
9. Replay ACh gain is damped when value variance is high.
10. Encoding strength and sleep stats expose ACh metrics.
11. Long-horizon stability checks (2000 and 5000 steps, opt-in).

---

## Phase 6.2 / 6.2.1 + SAC Coverage

File: `tests/test_phase_6_2_filtered_consolidation.py`
Additional files:
- `tests/test_semantic_action_consolidation.py`
- `tests/test_sleep_replay_storage.py`

Covered scenarios:
1. Noise episode is rejected.
2. Repeated significant episode is consolidated.
3. High value variance blocks sleep replay.
4. Sleep budget overflow stops updates.
5. High ACh with low TD is rejected.
6. TD history updates mean/variance correctly in waking/feedback.
7. `td_variance_cap` rejects high-variance episodes.
8. `value_variance` is frozen per sleep cycle for deterministic behavior.
9. Sleep replay does not mutate TD history statistics (Variant A).
10. Stress-test 5000 cycles: no variance growth (opt-in).
11. SAC confirmed action updates semantic means/variance/risk.
12. SAC anomalous shock episodes are ignored.
13. SAC blocks updates on low replay count and low stability.
14. SAC enforces anti-confirmation-bias (`epsilon_divergence`).
15. SAC enforces hard constraint `sac_alpha_slow <= 0.01`.
16. SAC applies variance floor (`sac_sigma_floor`) to prevent crystallization.
17. SAC params and `selector_action_metadata` persist through save/load.
18. SWS phase updates contract sigma and non-decrease stability as expected.
19. REM phase expands sigma and non-increase stability as expected.
20. TRANSITIONAL phase keeps stability unchanged.
21. SAC enforces phase-threshold invariants (`theta_arousal_low < theta_arousal_high`, `theta_shock_low < theta_shock_high`).
22. SAC enforces hard constraints `sac_alpha_base <= 0.01` and `sac_lambda_sws > sac_lambda_rem`.
23. Global SAC phase reflects effective-updatable rows (post-filter), not raw potential rows.
24. Structural alert supports calm-cycle reset; REM stability floor prevents collapse; semantic-confidence step cap limits per-cycle growth.

---

## Autonomous Runtime Coverage (Spec v1 + Physiology Audit)

Files:
- `tests/test_autonomous_organism.py`
- `tests/test_agent_lifetime_save_load.py`

Covered scenarios:
1. Idle curiosity growth and long-horizon boundedness.
2. Energy suppression of internal cycles under low energy.
3. Speech cooldown and speech-drive discharge behavior.
4. Drive competition with weighted thresholds.
5. Emotional overload raises discharge drive.
6. Recall impulse share cap (`<= 40%`).
7. Idle physiology mode reduces fatigue with low cognitive load.
8. `dt` anomaly clamping and logging.
9. Internal affect apply failures are logged.
10. Save/load round-trip preserves autonomous and wakefulness state.

GUI trace notes:
1. Autonomous speech traces are emitted with `[AUTO] ...` tags.
2. Internal thought traces are emitted as `[AUTO] think: ...` when internal cycle is triggered.
3. Duplicate thought lines are suppressed in short windows (anti-spam behavior).

---

## External Interaction Layer Coverage

File:
- `tests/test_external_interaction_layer.py`

Covered scenarios:
1. Observation ingest/interpretation with uncertainty handling.
2. Action execution through environment adapter and feedback coercion.
3. Delayed feedback queue/resolve pipeline.
4. Drive update stability: decay, saturation, competition.
5. Strategy update stability: logits, decay, softmax, temperature.
6. Drive-to-strategy coupling under neutral reward.
7. Hypothesis recalibration with explicit `P(E|not H)`.
8. Selector pressure modulation via learned `strategy_weight`.
9. Agent-level integration: execute/resolve/poll/parallel simulation.

---
## BG Pipeline Regression Coverage

Files:
- `tests/test_basal_ganglia.py`
- `tests/test_basal_ganglia_integration_spec.py`

Covered scenarios:
1. High dopamine amplifies Go path.
2. High cortisol suppresses action via NoGo amplification.
3. Habit strength can dominate under weak cortical pressure.
4. Zero pressure under aversive conditions can yield `NO_ACTION`.
5. Internal simulation proposal path matches real BG/Thalamic decision pipeline.

---

## CER Coverage

Files:
- `tests/test_emotional_regulation.py`
- `tests/test_emotional_regulation_integration.py`

Covered scenarios:
1. Sustained positive reward dynamics.
2. Chronic failure and recovery-mode activation.
3. Saturation guard for prolonged high arousal.
4. Entropy-driven caution (`decision_threshold_shift` growth).
5. Resolution success lowers uncertainty.
6. Oscillation stability and per-step jump caps.
7. Nonlinear/saturating valence response.
8. Stress-like chronic negative valence increases `habit_gain_scale`.
9. CER neuromodulator guidance remains bounded (`<= 0.006` absolute).

---

## ACC Coverage

Files:
- `tests/test_conflict_arbitration_layer.py`
- `tests/test_conflict_arbitration_integration.py`
- `tests/test_conflict_arbitration_storage.py`

Covered scenarios:
1. Low conflict -> `habitual` mode and threshold decrease.
2. High conflict + high novelty -> `deliberative` mode with WM boost.
3. Repeated failures -> `inhibit` mode with additional-evaluation request.
4. High arousal with low conflict does not force `deliberative`.
5. Hysteresis + refractory prevent rapid mode oscillation.
6. Control-cost exhaustion forces downshift from high-control modes.
7. Conflict metric remains separated from CER valence/arousal.
8. `control_demand` includes decision latency.
9. Agent learning-rate boost depends on `error_likelihood` (not control mode alone).
10. `inhibit` path acts through threshold modulation, not direct pressure-vector suppression.
11. Combined CER+ACC threshold shift is capped to prevent over-suppression.
12. ACC state round-trip persistence through `AgentStorage`.

---

## Long-Horizon / Opt-In Tests

Default skipped tests:
1. `RUN_LONG_HORIZON_ACH=1` enables 2 long ACh tests (`tests/test_phase_6_1_ach.py`).
2. `RUN_LONG_HORIZON_FILTERED_CONSOLIDATION=1` enables 5000-cycle stress test (`tests/test_phase_6_2_filtered_consolidation.py`).

---

## Notes

1. Long-horizon checks are intentionally disabled in default runs for CI speed.
2. For release validation, run default suite + both opt-in groups.
3. Keep reported pass counts synchronized with `pytest -q -rs` output after each major phase merge.
