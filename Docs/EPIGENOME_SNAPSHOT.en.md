# EpigenomeSnapshot Implementation Guide (Package B)

Russian version: [EPIGENOME_SNAPSHOT.ru.md](EPIGENOME_SNAPSHOT.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 24, 2026.

---

## Scope

`src/epigenome.py` implements inherited consolidated memory transfer for NOWA agents. The module is standalone and uses only the Python standard library.

Key goals:
1. an immutable snapshot container (`frozen=True` dataclasses and tuple collections)
2. safe extraction from raw dictionary payloads (no imports from NOWA runtime modules)
3. in-place injection into target dictionaries with bounded noise
4. deterministic behaviour with a fixed RNG
5. robust serialization and validation diagnostics for storage and lineage workflows

---

## Implemented Objects

### `InheritedPattern`

Fields:
- `context_signature: str`
- `action: str`
- `strength: float` in `[0.0, 1.0]`
- `reinforcement_count: int`

### `InheritedAction`

Fields:
- `action_id: str`
- `predicted_effect: Dict[str, float]`
- `semantic_confidence: float` in `[0.0, 1.0]`
- `stability_score: float` in `[0.0, 1.0]`
- `success_rate: float` in `[0.0, 1.0]`

### `InheritedValue`

Fields:
- `state_key: str`
- `value: float` in `[-1.0, 1.0]`
- `confidence: float` in `[0.0, 1.0]`
- `confirmation_count: float`

### `EpigenomeSnapshot`

Core methods:
- creation: `extract(...)`, `from_dict(...)`, `empty()`
- transfer: `inject(...)`
- crossover: `blend(...)`
- diagnostics: `is_empty()`, `size()`, `validate()`, `summary()`
- serialization: `to_dict()`

---

## API Behaviour

### `extract(...)`

Input:
- `cortex_patterns: List[dict]`
- `action_metadata: Dict[str, dict]`
- `value_profiles: Dict[str, dict]`

Selection behaviour:
1. patterns: top-N by `reinforcement_count` (descending), thresholded by `min_reinforcement`
2. actions: top-N by `stability_score` (descending), requires `consolidated=True`, thresholded by `min_stability`
3. values: top-N by `confirmation_count` (descending), thresholded by `min_confirmation`

Safety behaviour:
1. malformed entries are skipped
2. numeric fields are clamped to the declared ranges
3. `max_patterns`, `max_actions`, and `max_values` are clamped to `[1, 256]`
4. `source_generation` is normalized to `>= 0`
5. `extraction_timestamp` is set with `time.time()`

### `inject(...)`

Behaviour:
1. modifies `target_cortex_patterns`, `target_action_metadata`, and `target_value_profiles` in place
2. returns transfer statistics:
   - `patterns_injected`, `patterns_skipped`
   - `actions_injected`, `actions_skipped`
   - `values_injected`, `values_skipped`
   - `noise_level`

Conflict policy:
1. actions and values: existing keys are not overwritten
2. patterns: an existing context entry is replaced only if the inherited `strength` is higher

Noise behaviour:
1. `noise_level` is clamped to `[0.0, 1.0]`
2. pattern-strength noise: Gaussian `N(0, noise_level * 0.1)`, then clamp to `[0, 1]`
3. value noise: Gaussian `N(0, noise_level * 0.2)`, then clamp to `[-1, 1]`
4. confidence attenuation: a multiplicative factor with a bounded uniform component, then clamp to `[0, 1]`

### `blend(...)`

Behaviour:
1. patterns are merged by `context_signature`; duplicates keep the stronger `strength`
2. actions are merged by `action_id`; duplicates keep the higher `stability_score`
3. values with the same `state_key` are blended:
   - `value = alpha * self + (1 - alpha) * other`
   - `confidence = min(self.confidence, other.confidence)`
4. the output is capped by `MAX_PATTERNS`, `MAX_ACTIONS`, and `MAX_VALUES`
5. `alpha` is clamped to `[0.0, 1.0]`
6. lineage is composed as `f"{self.source_lineage_id}+{other.source_lineage_id}"[:64]`

### Serialization and diagnostics

1. `to_dict()` outputs sorted collections:
   - patterns by strength, descending
   - actions by stability, descending
   - values by confirmation, descending
2. `from_dict()` restores a snapshot safely:
   - malformed rows are skipped with warnings
   - `source_generation < 0` is normalized to `0`
3. `validate()` checks:
   - bounds and finite numeric values
   - duplicate keys for patterns, actions, and values
   - negative counters where they are disallowed
4. `summary()` returns compact aggregate metrics and counts

---

## Test Coverage

Primary suite:
- `tests/test_epigenome_snapshot.py`

Coverage includes:
- TC-01..TC-16 from `Docs/SPEC_B_EpigenomeSnapshot.md`

Latest local run:

```text
python -m pytest tests/test_epigenome_snapshot.py -q
16 passed in 0.04s
```

Project-wide regression (excluding Demo):

```text
python -m pytest tests -q
643 passed, 3 skipped
```
