# Phase 4.5 — Stability Monitoring and Drift Control

Russian version: [Phase_4_5_Stability_Monitoring_RU_Spec.ru.md](Phase_4_5_Stability_Monitoring_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## 1. Purpose of the Phase

Phase 4.5 introduces a meta-level of monitoring the stability of the emotional–neuromodulatory system.

The phase does NOT:
- alter emotions
- alter the background
- alter neuromodulators
- participate in action selection
- influence learning

The phase ONLY:
- measures
- analyses long-term metrics
- sets diagnostic flags of stability

This is a read-only layer.

---

## 2. Architectural Boundaries

### 2.1 Access to Data

Permitted:
- reading emotional_state
- reading affective_background
- reading neuromodulators
- reading expectations (global_outlook)
- reading activation logs of Phase 4.4

Prohibited:
- any write into the structures named above
- invocation of regulators
- alteration of memory T1/T2/T3
- alteration of BG, TD-learning, and related mechanisms

---

## 3. Temporal Window of Analysis

A sliding window W is used:

W = 500–2000 ticks (configurable)

All computations are performed on aggregated values within the window.

---

## 4. Stability Metrics

### 4.1 Regulation Activation Rate

regulation_activation_rate = activations_4_4 / window_length

Threshold: > 0.15 → regulation_overuse_flag = True

---

### 4.2 Background Drift

mean_background = mean(background_anxiety over W)

If mean_background > baseline_background + 0.20 → background_drift_flag = True

---

### 4.3 Neuromodulator Drift

For each modulator:

mean_mod = mean(level over W)

If |mean_mod − baseline_mod| > 0.25 → neuromodulator_drift_flag = True

---

### 4.4 Dominant Emotion Lock

If one and the same emotion:

- dominates more than 70% of the time in the window
- without a corresponding growth of intensity
- without new triggers

→ dominant_emotion_lock_flag = True

---

### 4.5 Outlook Bias

escalating_ratio = fraction(global_outlook == "escalating")

If escalating_ratio > 0.7 → outlook_bias_flag = True

---

## 5. Stability Index

stability_index = 1.0 − weighted_sum(flags)

Example weights:
- regulation_overuse: 0.25
- background_drift: 0.25
- neuromodulator_drift: 0.25
- dominant_emotion_lock: 0.15
- outlook_bias: 0.10

The index is bounded to the range [0.0, 1.0]

---

## 6. Returned Structure

```python
{
  "stability_index": float,
  "drift_flags": {
      "regulation_overuse": bool,
      "background_drift": bool,
      "neuromodulator_drift": bool,
      "dominant_emotion_lock": bool,
      "outlook_bias": bool
  },
  "recommendation": "none" |
                    "inspect_expectations" |
                    "inspect_memory" |
                    "inspect_regulation" |
                    "inspect_background" |
                    "inspect_neuromodulators"
}
```

recommendation is formed logically:
- regulation_overuse → inspect_regulation
- neuromodulator_drift → inspect_neuromodulators
- background_drift → inspect_background
- outlook_bias → inspect_expectations
- dominant_emotion_lock → inspect_memory
- otherwise → none

---

## 7. Safety Constraints

1. Phase 4.5 CANNOT alter the state of the system.
2. Phase 4.5 CANNOT initiate regulation.
3. Phase 4.5 DOES NOT participate in the computation of reward.
4. Phase 4.5 DOES NOT influence TD-learning.
5. Phase 4.5 DOES NOT pass signals directly into Phase 4.4.

A link with Phase 5 is admissible only through reading stability_index.

---

## 8. Invariants

- Read-only access
- Absence of write side-effects
- Use of smoothed metrics
- Presence of hysteresis (at least 2 consecutive windows to register drift)

---

## 9. Future Extensions

- Integration of circadian rhythms (after Phase 5)
- Separation of short-term and long-term stability
- Adaptive thresholds based on the history of the system

---

## 10. Implementation Notes (Actual State)

- baseline_background is NOT fixed by the first tick.
- baseline_background is calibrated on a warm-up sample (the median of the first N ticks; by default N = window_size).
- Until warm-up is complete, background_drift is not activated.
- Calibration state and history are preserved in save/load (through emotional_stability).

---

Status: Implemented v1.1
