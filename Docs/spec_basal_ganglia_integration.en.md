# Mandatory Basal Ganglia Integration Specification (Implemented)

Russian version: [spec_basal_ganglia_integration.ru.md](spec_basal_ganglia_integration.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


Last verified: February 25, 2026.

This document is the source of truth for action selection flow in the current codebase.

---

## 1. Goal

Make Basal Ganglia (BG) a mandatory stage of decision-making.
No final action may bypass BG + thalamic gating.

---

## 2. Mandatory Decision Flow

Current runtime flow:

```text
ActionSelector.compute_pressures(...) -> pressure_vector
                     |
                     v
BasalGangliaGate.process(...)
                     |
                     v
ThalamicGate.select(...)
                     |
                     v
final_action (or NO_ACTION)
```

This flow is used in:
1. `Agent.step(...)` live decisions
2. Internal simulation proposal path in `InternalSimulationLoop`

---

## 3. Responsibility Split (No Double Modulation)

### Selector responsibility
`ActionSelector.compute_pressures(...)` returns cortical/cognitive competition only:
1. hippocampal traces
2. cortical patterns
3. intent pressure
4. temporal-chain advisory pressure
5. prediction-layer advisory pressure

`compute_pressures(...)` does not apply biological modulation.

### BG responsibility
`BasalGangliaGate.process(...)` applies biological modulation:
1. dopamine (Go amplification)
2. cortisol + aversive signal (NoGo amplification)
3. habit contribution
4. channel modulators (go_weight, nogo_weight)
5. CER modulation:
   - `exploration_bias`
   - `decision_threshold_shift`
   - `habit_gain_scale`

Invariant:
1. affect/threat must not be applied in both selector and BG for the same pipeline pass.

---

## 4. BG Process Contract

Input:
1. `pressure_vector`
2. `dopamine_level`
3. `cortisol_level`
4. `norepinephrine_level` (for temperature hint / final gate coupling)
5. `habit_strengths`
6. `aversive_signal`
7. `channel_modulators`
8. `exploration_bias`
9. `decision_threshold_shift`
10. `habit_gain_scale`

Current formula per action:

```text
uncertainty_bonus_raw = exploration_bias * max(0, 0.25 - |pressure|) * cer_bonus_gain
uncertainty_bonus = min(cer_bonus_cap_abs, uncertainty_bonus_raw)

habit_term = beta * habit_gain_scale * habit
Go_raw = (pressure * (1 + alpha * dopamine) + habit_term + uncertainty_bonus) * go_weight

go_cap = (
    cer_go_pressure_cap_ratio * |pressure * (1 + alpha * dopamine)|
    + habit_term
    + cer_bonus_cap_abs
) * go_weight
Go = min(Go_raw, go_cap)

NoGo = (|pressure| * (gamma * cortisol + delta * aversive_signal)) * nogo_weight
Net = Go - NoGo
effective_threshold = threshold + decision_threshold_shift
gated_score = max(Net - effective_threshold, 0)
```

CER safety invariants:
1. `uncertainty_bonus <= cer_bonus_cap_abs`
2. `Go <= go_cap`
3. `habit_gain_scale` is clamped in BG

---

## 5. Wakefulness/Fatigue Semantics

Wakefulness-based cognitive reliability must be interpreted as:

```text
wake_mod = get_cognitive_reliability() if available else (1 - wakefulness)  # legacy fallback
```

Current `WakefulnessState.get_cognitive_reliability()` semantics:

```text
sleep_pressure = Process S
circadian_signal = Process C
reliability = clamp(base_alertness - sleep_pressure + circadian_signal, 0..1)
```

So:
1. rested state -> higher cognitive reliability
2. fatigued state -> lower PFC contribution

---

## 6. Threat and Aversive Signal

In channel-based `choose(...)`, aversive path is:

```text
aversive_signal = threat
```

Threat is read from:
1. `affective_space.axes["stress"]` (preferred)
2. legacy `affect_state.threat` fallback

No extra ad-hoc threat pressure term is allowed outside this contract.

---

## 7. Thalamic Gate Contract

`ThalamicGate.select(gated_scores, norepinephrine_level, exploration_bias=0.0)`:
1. returns `NO_ACTION` when all gated scores are zero (or absent)
2. otherwise samples by softmax over non-negative gated scores
3. uses NE- and CER-modulated temperature:
   `temperature = base_temperature * (1 + ne_gain * norepinephrine) * (1 + 0.8 * exploration_bias)`

Invariant:
1. if gate returns `NO_ACTION`, runtime must not replace it with random action.

---

## 8. Neutral-State Behavior Guardrail

Selector-level forced baseline pressure in fully neutral state is disallowed.

Current runtime compromise in `Agent.step(...)`:
1. if selector pressure vector is fully zero
2. and context is non-empty
3. inject tiny bootstrap pressure (`0.12`) for one context-derived action

This keeps context responsiveness without forcing action in truly neutral/no-input states.

---

## 9. Internal Simulation Parity

Internal simulation proposal must stay aligned with live runtime:

```text
compute_pressures -> BG.process -> ThalamicGate.select
```

This prevents divergence between simulated and real choices.

---

## 10. Test Contract

Required regression coverage:
1. `tests/test_basal_ganglia.py`
2. `tests/test_basal_ganglia_integration_spec.py`

Mandatory scenarios:
1. high dopamine amplifies Go output
2. high cortisol suppresses action output
3. habits can dominate weak pressure
4. zero pressure + aversive conditions can produce `NO_ACTION`
5. internal simulation proposal matches live BG/Thalamic pipeline
6. CER exploration bonus is bounded by cap
7. CER habit gain scaling increases habitual channel under stress-like conditions
