# Phase 2 Extension: Wakefulness, Circadian Process C, and Prefrontal Cortex Modulation

Russian version: [Phase2_Wakefulness_PFC_Extension.ru.md](Phase2_Wakefulness_PFC_Extension.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Status

Implemented in code (`src/wakefulness.py`, `src/agent.py`, `src/storage.py`) as of 23 March 2026.

---

## Aim

To maintain a physiological state of wakefulness that:
- does not make decisions,
- is not an emotion or a neuromodulator,
- modulates the reliability of cognitive control (PFC),
- influences the existing neuromodulator system through separate deltas,
- combines the homeostatic sleep pressure (Process S) and the circadian signal (Process C).

---

## WakefulnessState (Current Model)

```python
class WakefulnessState:
    wakefulness: float              # Process S, [0.0 .. 1.0]
    last_update_ts: float
    accumulated_waking_time: float
    total_sleep_time: float

    circadian_time_hours: float
    circadian_period_hours: float   # default 24.0
    circadian_amplitude: float      # default 0.3
    circadian_phase: float          # default 0.0
```

Interpretation:
- `wakefulness = 0.0` — minimal sleep pressure (rested).
- `wakefulness = 1.0` — high sleep deprivation.

---

## Process S (Sleep Pressure)

### Accumulation during wakefulness

```text
wakefulness += dt * ACCUMULATION_RATE
ACCUMULATION_RATE = 1 / (16 * 60 * 60)
```

### Recovery during sleep

```text
wakefulness -= dt * RECOVERY_RATE
RECOVERY_RATE = 1 / (8 * 60 * 60)
```

Constraint: the value is always clamped to the range `[0, 1]`.

---

## Process C (Circadian Rhythm)

Formula:

```text
C(t) = A * sin(2π * t / T + phase)
```

Where:
- `A = circadian_amplitude` (default `0.3`)
- `T = circadian_period_hours` (default `24h`)
- `t = circadian_time_hours`

In the current implementation, `circadian_time_hours` advances in:
- `update_waking(...)`
- `update_sleeping(...)`

---

## Derived Wakefulness Signals (Borbély)

```text
sleep_pressure = Process S = wakefulness
circadian_signal = Process C
wake_drive = circadian_signal - sleep_pressure
alertness = base_alertness - sleep_pressure + circadian_signal
```

By default:
- `base_alertness = 1.0`
- `cognitive_reliability = clamp(alertness, 0..1)`

---

## Influence on Neuromodulators

On every update:

```text
cortisol       += wakefulness * 0.01
norepinephrine += wakefulness * 0.02
serotonin      -= wakefulness * 0.015
```

Constraints:
- all values are clamped,
- dopamine is not altered directly by this module.

---

## Influence on the PFC

### Signal strength and noise

```text
get_pfc_signal_strength_modifier() -> 1.0
get_pfc_signal_noise_modifier()    -> 1.0 + wakefulness * 0.7
```

Meaning:
- the nominal strength of the PFC does not change,
- fatigue increases the noise and the unreliability of the signal.

### Conflict-dependent reduction of PFC weight

```text
effective_PFC_weight *= (1 - conflict * wakefulness)
```

---

## Persistence (save/load)

The following fields are saved and restored:
- `wakefulness`, `last_update_ts`, `accumulated_waking_time`, `total_sleep_time`
- `circadian_time_hours`, `circadian_period_hours`, `circadian_amplitude`, `circadian_phase`

---

## Test Cases (Current)

1. Accumulation of Process S (8 h ≈ 0.5, 16 h ≈ 1.0).
2. Recovery of Process S in sleep (8 h from high fatigue tends toward 0).
3. Monotone growth of cortisol as `wakefulness` grows.
4. PFC strength is constant; PFC noise grows with `wakefulness`.
5. `effective_PFC_weight` falls under high conflict and high fatigue.
6. Process C:
   - `t=0` → the signal is near `0`,
   - `t=T/4` → the signal is near `+amplitude`,
   - a phase shift changes the value correctly.
7. A save/load round-trip preserves the circadian parameters.
