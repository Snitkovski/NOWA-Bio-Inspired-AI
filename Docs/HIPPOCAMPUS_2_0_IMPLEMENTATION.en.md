# Hippocampus 2.0 Implementation Notes

Russian version: [HIPPOCAMPUS_2_0_IMPLEMENTATION.ru.md](HIPPOCAMPUS_2_0_IMPLEMENTATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last updated: February 22, 2026

This document describes the implemented episodic-memory behaviour in `src/hippocampus.py` and the related tests in `tests/test_hippocampus_2_0.py`.

---

## Scope

Hippocampus 2.0 extends episodic memory with:
1. Pattern separation (feature sparsification).
2. Fuzzy matching and reinforcement (not exact signature equality only).
3. CA3-like pattern completion (`reconstructed_features` from weighted top-k recall).
4. CA1-like novelty signaling (`novelty_score`, novelty class bins).
5. Temporal context encoding (`time_bucket`, rolling hash, discretized drive bucket).
6. Capacity and decay controls suitable for long-running simulation.

---

## Public API

File: `src/hippocampus.py`

Main methods:
1. `store(path_or_signature, consequence=None, intensity=1.0, reward=0.0, encoding_strength=None) -> Experience`
2. `reinforce(path_or_signature, consequence=None, intensity=1.0) -> Experience`
3. `activate(context_events: list[str]) -> list[Experience]`
4. `get_candidates_for_sleep(min_reinforcement=2) -> list[Experience]`
5. `get_statistics() -> dict`

Recall methods:
1. `recall_signature(current_signature: dict) -> dict`
2. `recall_recent(limit: int | None = None) -> list[Experience]`
3. `recall_by_drive(active_drive: str, limit: int = 6) -> list[Experience]`
4. `recall(...)` remains as a backward-compatible dispatcher.

`recall_signature(...)` output schema:

```json
{
  "reconstructed_features": [],
  "novelty_score": 0.0,
  "novelty_class": "familiar|partial_match|novel|high_novelty",
  "similarity_top_k": []
}
```

---

## Behavioural Details

### Context Similarity

Context is not based on binary equality. Similarity combines:
1. Time-bucket proximity.
2. Soft hash distance.
3. Discretized drive-bucket proximity.
4. Partial overlap of rolling context tokens.

### Decay

Decay uses half-life as the primary mechanism, with a soft regularization from `decay_rate` to avoid an excessively fast collapse of activation traces.

### Capacity Pruning

Capacity pruning includes novelty-aware priority:
1. Activation retention.
2. Novelty contribution (`novelty_capacity_bias`).
3. Reinforcement count.
4. Recency.

### Reconstruction

The reconstruction threshold is adaptive to the current top-k evidence (`0.5 * max_score` with bounds), not fixed at a single hard constant.

---

## Main Tunables

Constructor parameters in `NOWAHippocampus(...)`:
1. `max_experiences`
2. `activation_decay_half_life`
3. `decay_rate`
4. `activation_threshold`
5. `max_features`
6. `top_k_recall`
7. `novelty_window`
8. `cycle_length`
9. `context_history_size`
10. `activation_similarity_threshold`
11. `reinforce_similarity_threshold`
12. `consolidation_min_probability`
13. `novelty_capacity_bias`

---

## Validation

Primary tests:
1. `tests/test_hippocampus.py` (legacy compatibility and baseline behaviour)
2. `tests/test_hippocampus_2_0.py` (specification behaviour and edge cases)

Focused command:

```bash
pytest -q tests/test_hippocampus.py tests/test_hippocampus_2_0.py
```

On the current baseline:
1. `tests/test_hippocampus_2_0.py`: `13 passed`
2. Combined hippocampus tests: `24 passed`
