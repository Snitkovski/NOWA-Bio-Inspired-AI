# Circadian Process C

Russian version: [spec_circadian_process_c.ru.md](spec_circadian_process_c.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Status

Implemented in `WakefulnessState` (23 March 2026).

---

## Model

The formalisation of Borbély is used:

```text
sleep_pressure = Process S
circadian_signal = Process C
wake_drive = Process C - Process S
```

Where:

```text
Process C: C(t) = A * sin(2π * t / T + phase)
```

---

## Influence on Wakefulness

```text
alertness = base_alertness - sleep_pressure + circadian_signal
```

In the project:
- `sleep_pressure = wakefulness`
- `base_alertness = 1.0` (by default)
- `cognitive_reliability = clamp(alertness, 0..1)`

---

## Parameters

```python
circadian_period_hours = 24.0
circadian_amplitude = 0.3
circadian_phase = 0.0
```

---

## Binding to the API

In `src/wakefulness.py`:
- `get_circadian_signal()`
- `get_wake_drive()`  # `Process C - Process S`
- `get_alertness(base_alertness=None, clamp=True)`

In `src/agent.py` (`get_wakefulness_state()`):
- `circadian_signal`
- `wake_drive`
- `alertness`

Persistence (`src/agent.py`, `src/storage.py`):
- `circadian_time_hours`
- `circadian_period_hours`
- `circadian_amplitude`
- `circadian_phase`

---

## Verification

Covered by tests:
- `tests/test_wakefulness.py::TestCircadianProcessC`
- `tests/test_agent_lifetime_save_load.py::test_wakefulness_and_autonomous_runtime_persistence`
