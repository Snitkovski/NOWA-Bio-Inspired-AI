# Neuromodulator Interaction Layer

Russian version: [NEUROMODULATOR_INTERACTION_LAYER.ru.md](NEUROMODULATOR_INTERACTION_LAYER.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last updated: March 22, 2026

Source implementation:
- `src/neuromodulators.py`

Related specification:
- `Docs/spec_neuromodulator_interaction_layer.md`

---

## Summary

The project now includes a coupled interaction layer for four neuromodulators:
- dopamine (`DA`)
- serotonin (`5HT`)
- norepinephrine (`NE`)
- acetylcholine (`ACh`)

This layer is implemented as `NeuromodulatorField` and integrated into `NeuromodulatorState.update_from_signals(...)`.

---

## Dynamics

State vector:

```text
M = [DA, 5HT, NE, ACh]
```

Interaction matrix (`W`, taken from the specification):

```text
       DA    5HT   NE    ACh
DA   [  0   -0.2   0.1  -0.3 ]
5HT  [  0.1   0   -0.1   0   ]
NE   [  0.2  -0.1   0    0.2 ]
ACh  [ -0.3   0    0.2   0   ]
```

Implemented update (baseline-centered for stability):

```text
dM/dt = base_signal + W * (M - baseline) - decay * (M - baseline)
```

Where:
- `base_signal` comes from reward, novelty, and conflict, plus the ACh novelty and repetition logic.
- `baseline` is the per-modulator baseline (`DA`, `5HT`, `NE`, and `ach_baseline`).

---

## Integration in `NeuromodulatorState`

Added or updated behaviour:
- `interaction_field: Optional[NeuromodulatorField]`
- synchronization helpers:
  - `_sync_field_from_state()`
  - `_sync_state_from_field()`
  - `_apply_interaction_dynamics(...)`
- `update_from_signals(...)` now:
  1. builds `base_signal`,
  2. applies cortisol updates,
  3. computes the ACh delta,
  4. runs the coupled interaction dynamics,
  5. clamps values and updates the timestamp.

Persistence:
- `to_dict()` includes `interaction_field`
- `from_dict()` restores `interaction_field` (with backward compatibility if it is missing)

---

## Testing

New dedicated tests:
- `tests/test_neuromodulator_interaction_layer.py`
  - baseline stability without signals
  - high serotonin dampens dopamine
  - high dopamine suppresses acetylcholine
  - follow-up step coupling in `NeuromodulatorState`
  - persistence of the interaction field

Validation commands:

```bash
pytest -q tests/test_neuromodulator_interaction_layer.py
pytest -q tests/test_neuromodulators_phase2.py tests/test_neuromodulator_integration.py tests/test_neuromodulator_interaction_layer.py
pytest -q tests
```

Latest observed results:
- `tests/test_neuromodulator_interaction_layer.py`: `5 passed`
- combined neuromodulator bundle: `29 passed`
- full core suite (excluding Demo): `589 passed, 3 skipped`
