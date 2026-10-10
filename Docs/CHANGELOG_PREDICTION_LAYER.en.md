# Changelog — Prediction Layer (Plan C) Integration

Russian version: [CHANGELOG_PREDICTION_LAYER.ru.md](CHANGELOG_PREDICTION_LAYER.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Date: 2026-02-06

Brief description:

- The architectural component `Plan C` was renamed to `Prediction Layer`.
- `src/prediction_layer.py` was implemented — a minimal v1 implementation of the prediction layer.
- `PredictionLayer` was integrated into `Agent` and `Selector` via `prediction_pressure`.
- The logic governing curiosity and decay in the GUI was improved: `novelty` became graded (Jaccard), and `decay_over_time()` is called when an input is processed.
- A complete set of specification tests TC-C-01..TC-C-A3 and integration tests was added.

Changed and added files:

- `src/prediction_layer.py` — new PredictionLayer module
- `src/agent.py` — support for an optional `prediction_layer`
- `src/selector.py` — acceptance of `prediction_pressure` in `choose()` (advisory only)
- `src/affect.py` — softened growth of `curiosity`, and `decay_over_time()` is retained
- `src/gui.py` — graded novelty (Jaccard), an explicit decay call before the agent step
- `tests/test_prediction_layer.py` — basic unit tests for PredictionLayer
- `tests/test_prediction_layer_spec_compliance.py` — 15 specification tests (TC-C-01..TC-C-A3)
- `tests/test_affect_curiosity.py` and `tests/test_affect_curiosity_integration.py` — curiosity tests

Testing:

- Full test run: `pytest` → `193 passed`.
- Prediction Layer specification tests: `pytest tests/test_prediction_layer_spec_compliance.py` → `15 passed`.

Verification guide (quick commands):

```bash
# Run all tests
pytest -q

# Prediction Layer specifications
pytest tests/test_prediction_layer_spec_compliance.py -q

# Curiosity tests
pytest tests/test_affect_curiosity.py tests/test_affect_curiosity_integration.py -q
```

Notes on compatibility and further steps:

- `PredictionLayer.predict()` is a pure function: it performs no side effects and does not start learning.
- Learning and consolidation remain in `SleepManager`/`temporal_chains`.
- For v2: it is recommended to use `ChainMemory` as the source of training information, to add outcome statistics, and a probabilistic forward model.

If needed, a PR will be prepared with this changelog and a brief description in the PR body for review.
