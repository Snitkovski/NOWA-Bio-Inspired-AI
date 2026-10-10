# Continuous Emotional Regulation (CER)

Russian version: [spec_continuous_emotional_regulation.ru.md](spec_continuous_emotional_regulation.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Version: 1.1  
Status: implemented in `src/emotional_regulation.py`  
Last verification: February 25, 2026

---

## 1. Purpose

CER is a continuous layer of affective regulation that:
1. integrates the signals `reward`, `prediction_error`, `novelty`, `policy_entropy`, `resolution_success`;
2. maintains an inertial state (`valence`, `arousal`, `uncertainty_tension`);
3. modulates the parameters of the basal ganglia, the value layer, and the hippocampus, without making decisions directly.

CER does not choose an action and does not store episodes.

---

## 2. Input and Output Contract

### Update inputs (`update`)
1. `reward_signal` in `[-1, 1]`
2. `prediction_error` (`abs` plus an exponential moving average is used)
3. `novelty_score` in `[0, 1]`
4. `policy_entropy` in `[0, 1]`
5. `resolution_success` in `[0, 1]`
6. `time_delta`

### Outputs
1. Core state:
   - `valence` `[-1, 1]`
   - `arousal` `[0, 1]`
   - `uncertainty_tension` `[0, 1]`
2. `modulation_factors`:
   - `exploration_bias`
   - `learning_rate_scale`
   - `novelty_sensitivity_scale`
   - `decision_threshold_shift`
   - `habit_gain_scale`
3. `neuromodulator_guidance`:
   - `dopamine`
   - `norepinephrine`
   - `serotonin`
   - `cortisol`

---

## 3. Dynamics of CER

### 3.1 Basic principles
1. An exponential moving average for `sustained_prediction_error` with `ema_alpha >= 0.85`.
2. Nonlinear saturating functions (tanh/exp/sigmoid) in the state update.
3. Threshold effects for surprise, prediction error, and resolution.
4. A per-step jump guard: the change of each core variable is at most `0.3` per step.

### 3.2 Valence
A combination is used:
1. a reward drive with `tanh` saturation;
2. a penalty from sustained prediction error (linear plus threshold components);
3. a reduction of reward efficacy under a high `depressive_bias`.

### 3.3 Arousal
A combination is used:
1. a saturating novelty drive;
2. a saturating prediction-error drive;
3. a threshold surprise drive;
4. cooling through `resolution_success`;
5. a saturation guard under prolonged high arousal.

### 3.4 Uncertainty tension
A combination is used:
1. a saturating entropy drive;
2. a surprise drive;
3. a nonlinear relief from `resolution_success`.

---

## 4. Protective Mechanisms

### 4.1 Runaway prevention
If `valence < -0.9` for more than 50 steps:
1. `recovery_mode` is activated;
2. decay is strengthened;
3. `learning_rate_scale` is reduced;
4. exploration is raised moderately.

### 4.2 Saturation guard
If `arousal > 0.95` for more than 30 steps:
1. the effective contribution of novelty is reduced;
2. the decay of arousal is increased;
3. additional guard cooling is applied.

### 4.3 Hard bounds
1. All core-state variables and factors are clamped.
2. The jump limit `<= 0.3` is mandatory.
3. CER must not produce unbounded growth of Go in the basal ganglia.

---

## 5. Modulation Factors

### 5.1 `exploration_bias`
A function of arousal and negative valence, with a separate correction in recovery mode.

### 5.2 `learning_rate_scale`
A function of arousal plus uncertainty, with a penalty from chronic negative valence.
Range: `[0.5, 2.0]`.

### 5.3 `novelty_sensitivity_scale`
A function of arousal and depressive bias.
Range: `[0.5, 2.0]`.

### 5.4 `decision_threshold_shift`
A function of uncertainty and positive valence.
Range: `[-0.5, 0.8]`.

### 5.5 `habit_gain_scale`
A CER modulation of the formation of automatisms:
1. it grows under `chronic_negative_valence` and `uncertainty_tension`;
2. it falls under stably positive valence;
3. it may grow further in `recovery_mode`.

Range: `[0.75, 1.6]`.

---

## 6. Neuromodulator Guidance

CER forms slow top-down deltas of the neuromodulators.

### Constraints
1. Each delta is clamped to the range `[-0.006, +0.006]`.
2. Application through `apply_neuromodulator_guidance(...)` remains bounded and passes the system clamps of the neuromodulator state.

### Biological interpretation
This is an indirect modulation of parameter level (an engineering approximation), not a direct bypass of the basic neuromodulator dynamics.

---

## 7. Integration

### 7.1 Basal Ganglia
CER passes to the basal ganglia:
1. `exploration_bias`
2. `decision_threshold_shift`
3. `habit_gain_scale`

The basal ganglia must:
1. bound the exploration bonus by an absolute cap;
2. bound Go through an envelope cap;
3. clamp `habit_gain_scale`.

### 7.2 Hippocampus
CER passes `novelty_sensitivity_scale`.
The hippocampus scales novelty before the recall and novelty-score computations.

### 7.3 Value layer
CER passes `learning_rate_scale`.
The agent scales the online alpha of the value layer within safe limits.

### 7.4 Neuromodulators
CER passes `neuromodulator_guidance`.
The agent applies the guidance with a controlled `gain`.

---

## 8. Invariants

1. CER does not make decisions in place of the selector, the basal ganglia, or the thalamus.
2. CER does not change the action directly.
3. CER does not store episodic memory.
4. CER influences only through parameters and bounded guidance.
5. All dynamics are numerically stable and bounded.

---

## 9. Test Contract

Mandatory tests:
1. `tests/test_emotional_regulation.py`
2. `tests/test_emotional_regulation_integration.py`

Covered scenarios:
1. Sustained positive reward.
2. Chronic failure plus recovery mode.
3. A high-novelty burst plus the saturation guard.
4. A spike of policy entropy.
5. Resolution success reduces uncertainty.
6. Oscillation stability plus the jump guard.
7. Nonlinearity of valence dynamics (saturation).
8. Growth of `habit_gain_scale` under chronic negative valence.
9. Bounded neuromodulator guidance (`<= 0.006`).

---

## 10. Definition of Done

CER is considered valid if:
1. it passes the test contract;
2. it does not violate the stability of the basal ganglia;
3. it does not break the hippocampus, value, or update pipeline;
4. it preserves bounded behaviour on long runs.
