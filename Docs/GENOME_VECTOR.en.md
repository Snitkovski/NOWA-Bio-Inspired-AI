# GenomeVector Implementation Guide (Package A)

Russian version: [GENOME_VECTOR.ru.md](GENOME_VECTOR.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

Last verified: March 27, 2026.

---

## Scope

`src/genome.py` implements an evolvable genome representation for NOWA agents. The module is standalone and uses only the Python standard library.

Key goals:
1. deterministic gene ordering and reproducible operations with a fixed RNG
2. bounded numeric ranges per gene
3. mutation and crossover utilities for evolutionary workflows
4. conversion to module-level parameter dictionaries for agent construction

---

## Implemented Objects

### `GeneDescriptor`

Metadata for one gene:
- `key`
- `module`
- `min_val`, `max_val`
- `default`
- `sigma`
- `description`

Validation is enforced on descriptor creation (`min < max`, `default` in range, `sigma > 0`).

### `GENE_REGISTRY`

A deterministic ordered registry of genes grouped by prefix:
- `NM` (neuromodulators)
- `AF` (affective space)
- `WK` (wakefulness and circadian rhythm)
- `DR` (autonomous drives)
- `LR` (learning and memory)
- `IM` (imagination)
- `LT` (lifespan and time)

A notable DR addition for swarm integration:
- `dr_perception_radius_factor` (range `0.5..2.0`, default `1.0`)

### `GenomeVector`

Core methods:
- creation: `default()`, `random(rng)`, `from_dict(data)`, `from_array(array, generation=0)`
- transforms: `mutate(rate, sigma_scale, rng)`, `crossover(other, alpha, mode, rng)`
- metrics: `distance(other)`, `similarity(other)`, `summary()`, `validate()`
- serialization: `to_dict()`, `to_array()`
- expansion: `to_agent_params()`

Supported crossover modes:
- `arithmetic`
- `uniform`
- `sbx` (eta=2)

---

## Serialization Contracts

### `to_dict()`

Returns:

```python
{
    "version": "1.0",
    "generation": int,
    "lineage_id": str,
    "genes": {key: value, ...},
}
```

### `from_dict()`

- ignores unknown gene keys
- fills missing keys by defaults
- clamps out-of-range values to descriptor bounds (with a warning)

### Array round-trip

- `to_array()` preserves registry order
- `from_array()` requires the exact length or raises `ValueError`

---

## Agent Parameter Expansion

`GenomeVector.to_agent_params()` expands genes into module configuration blocks:
- `affective_space`
- `wakefulness`
- `neuromodulators`
- `autonomous`
- `value_layer`
- `hippocampus`
- `sleep`
- `imagination`
- `mortality`

Swarm-related mapping:
- `autonomous.perception_radius_factor <- dr_perception_radius_factor`

Mortality-related mapping:
- `mortality.max_lifespan_factor <- lt_max_lifespan_factor`

This mapping is intended for factory-style agent initialization pipelines.

---

## Determinism and Safety

1. All stochastic operations accept an external `random.Random`.
2. A fixed RNG seed gives deterministic mutation and crossover results.
3. All gene updates are clamped to biologically bounded ranges.
4. The distance metric is normalized Euclidean distance in `[0.0, 1.0]`.

---

## Test Coverage

Primary suite:
- `tests/test_genome_vector.py`

Coverage includes:
- TC-01..TC-14 from `Docs/SPEC_A_GenomeVector.md`
- additional checks for SBX determinism and lineage truncation

Latest local run:

```text
python -m pytest tests/test_genome_vector.py -q
17 passed in 0.04s
```

Project-wide regression (excluding Demo):

```text
python -m pytest tests -q
723 passed, 3 skipped
```
