# Package B Specification — EpigenomeSnapshot

Russian version: [SPEC_B_EpigenomeSnapshot.ru.md](SPEC_B_EpigenomeSnapshot.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Project:** NOWA (extension of the existing project)  
**File:** `src/epigenome.py`  
**Dependencies:** the Python standard library only (`math`, `random`, `dataclasses`, `typing`)  
**External dependencies:** none (data are passed as dictionaries — without a direct import of NOWA modules)  
**Specification version:** 1.0

---

## 1. Purpose

`EpigenomeSnapshot` is a partial transfer of consolidated memory from parents to an offspring.  
Unlike the genome (architectural parameters), the epigenome carries **acquired knowledge**:  
behavioural patterns, semantic actions, and valuations of states.

Biological analogy: epigenetic inheritance plus cultural transmission.  
An agent is born not with a blank memory, but with the "memories of ancestors" — noisy,  
partial, yet real.

**Key principle:** injection of the epigenome occurs **before the first sleep** of the new agent.  
Sleep consolidates inherited patterns on a par with the agent's own experience.

The colony birth path copies the genome by crossover and mutation. The inspector genome tab of a seeded run shows that portrait and the shifts from the parental midpoint: [Evolution in action](../README.md#evolution-in-action).

---

## 2. Data sources

The epigenome is extracted from three NOWA modules:

### 2.1 CortexMemory — stable patterns

Source: `agent.cortex` — patterns with a high `reinforcement_count`.  
What is transferred: context → action + pattern strength.

```python
# Structure of one pattern record
@dataclass
class InheritedPattern:
    context_signature: str    # hash of the context
    action: str               # preferred action
    strength: float           # pattern strength [0.0, 1.0]
    reinforcement_count: int  # how many times it was reinforced
```

### 2.2 ActionSelector SAC metadata — semantic actions

Source: `agent.selector.action_metadata` — records with a high `stability_score`.  
What is transferred: `predicted_effect`, `semantic_confidence`, `stability_score`.

```python
# Structure of one action record
@dataclass
class InheritedAction:
    action_id: str                       # action identifier
    predicted_effect: Dict[str, float]   # expected effects
    semantic_confidence: float           # confidence [0.0, 1.0]
    stability_score: float               # stability [0.0, 1.0]
    success_rate: float                  # historical success [0.0, 1.0]
```

### 2.3 ValueLayer — valuations of states

Source: `agent.value_layer` — records with a high `confirmation_count`.  
What is transferred: state key + value estimate + confidence.

```python
# Structure of one value record
@dataclass
class InheritedValue:
    state_key: str          # state key (a hash string)
    value: float            # value estimate [-1.0, 1.0]
    confidence: float       # confidence [0.0, 1.0]
    confirmation_count: float  # number of confirmations
```

---

## 3. Structure of EpigenomeSnapshot

```python
@dataclass(frozen=True)
class EpigenomeSnapshot:
    patterns: Tuple[InheritedPattern, ...]    # patterns from cortex
    actions: Tuple[InheritedAction, ...]      # SAC metadata
    values: Tuple[InheritedValue, ...]        # value_layer estimates
    source_generation: int                    # generation of the source
    source_lineage_id: str                    # lineage of the source
    extraction_timestamp: float               # time of extraction
```

**Constraints:**
- `len(patterns) <= MAX_PATTERNS` (default: 32)
- `len(actions) <= MAX_ACTIONS` (default: 16)
- `len(values) <= MAX_VALUES` (default: 24)
- all numeric fields lie in the stated ranges
- `source_generation >= 0`

---

## 4. API

### 4.1 Extraction

```python
@classmethod
def extract(
    cls,
    cortex_patterns: List[dict],
    action_metadata: Dict[str, dict],
    value_profiles: Dict[str, dict],
    source_generation: int = 0,
    source_lineage_id: str = "",
    max_patterns: int = 32,
    max_actions: int = 16,
    max_values: int = 24,
    min_reinforcement: int = 2,
    min_stability: float = 0.5,
    min_confirmation: float = 1.0,
) -> "EpigenomeSnapshot":
    """
    Extract an epigenome from the raw data of NOWA modules.

    Accepts data as dictionaries — without a direct import of NOWA modules.
    
    Arguments:
        cortex_patterns: a list of cortex pattern dictionaries
            expected keys: "context_signature", "action",
                             "strength", "reinforcement_count"
        action_metadata: a dictionary {action_id: metadata_dict}
            expected keys: "predicted_effect", "semantic_confidence",
                             "stability_score", "success_rate"
        value_profiles: a dictionary {state_key: profile_dict}
            expected keys: "value", "confidence", "confirmation_count"
        source_generation: generation of the source agent
        source_lineage_id: lineage_id of the source agent
        max_patterns: maximum number of patterns to keep
        max_actions: maximum number of actions to keep
        max_values: maximum number of value estimates to keep
        min_reinforcement: minimum reinforcement_count for including a pattern
        min_stability: minimum stability_score for including an action
        min_confirmation: minimum confirmation_count for including a value

    Selection:
        patterns: top-N by reinforcement_count (descending)
        actions: top-N by stability_score (descending), only consolidated=True
        values: top-N by confirmation_count (descending)

    Returns: EpigenomeSnapshot
    
    Constraints:
        - empty sources yield empty collections (not an error)
        - malformed records are skipped silently
        - max_* is clamped to [1, 256]
    """
```

### 4.2 Injection

```python
def inject(
    self,
    target_cortex_patterns: list,
    target_action_metadata: dict,
    target_value_profiles: dict,
    noise_level: float = 0.1,
    rng: random.Random = None,
) -> dict:
    """
    Implant inherited data into the structures of a new agent.
    
    Accepts and returns dictionaries — without a direct import of NOWA modules.
    Modifies the passed structures IN-PLACE and returns statistics.
    
    Noise mechanism:
        - numeric values: value += N(0, noise_level * value_range)
        - actions: semantic_confidence *= (1 - noise_level * U(0,1))
        - values: value += N(0, noise_level), confidence *= (1 - noise_level/2)
    
    Priority on conflicts:
        - if the key already exists in the target: do NOT overwrite
        - inheritance is added only for keys that are absent
        - exception: patterns with strength > existing_strength replace the existing one
    
    Arguments:
        target_cortex_patterns: the new agent's pattern list (may be empty)
        target_action_metadata: the new agent's metadata (may be empty)
        target_value_profiles: the new agent's value profiles (may be empty)
        noise_level: noise level at injection [0.0, 1.0]
            0.0 = an exact copy (cloning, not recommended)
            0.1 = nominal (recommended)
            1.0 = maximum noise (the inheritance is almost lost)
        rng: random-number generator
    
    Returns: a dict of statistics
    {
        "patterns_injected": int,
        "patterns_skipped": int,
        "actions_injected": int,
        "actions_skipped": int,
        "values_injected": int,
        "values_skipped": int,
        "noise_level": float,
    }
    
    Constraints:
        - noise_level is clamped to [0.0, 1.0]
        - at noise_level=0.0 returns exact copies
        - numeric values after noise are clamped to the admissible ranges
        - never raises an exception on malformed data
    """
```

### 4.3 Blending of epigenomes

```python
def blend(
    self,
    other: "EpigenomeSnapshot",
    alpha: float = 0.5,
    rng: random.Random = None,
) -> "EpigenomeSnapshot":
    """
    Cross two epigenomes into one.
    
    Used when an offspring has two parents.
    
    Algorithm:
        patterns: unite; on duplicates take the one with the greater strength
                  final size <= MAX_PATTERNS (selection by strength)
        actions:  unite; on duplicates take the one with the greater stability_score
                  final size <= MAX_ACTIONS
        values:   when state_key coincides:
                      value = alpha * self.value + (1-alpha) * other.value
                      confidence = min(self.confidence, other.confidence)
                  unique entries are added as they are
                  final size <= MAX_VALUES (selection by confirmation_count)
    
    Arguments:
        other: the second epigenome
        alpha: weight of the first epigenome for values [0.0, 1.0]
        rng: unused at present, reserved for future modes
    
    Returns: a new EpigenomeSnapshot
        source_generation = max(self.source_generation, other.source_generation)
        source_lineage_id = f"{self.source_lineage_id}+{other.source_lineage_id}"[:64]
    
    Constraints:
        - alpha is clamped to [0.0, 1.0]
        - the result does not exceed the MAX_* limits
        - all numeric values are clamped to the admissible ranges
    """
```

### 4.4 Serialisation

```python
def to_dict(self) -> dict:
    """
    Serialise to a dictionary.
    
    Returns:
    {
        "version": "1.0",
        "source_generation": int,
        "source_lineage_id": str,
        "extraction_timestamp": float,
        "patterns": [
            {
                "context_signature": str,
                "action": str,
                "strength": float,
                "reinforcement_count": int,
            },
            ...
        ],
        "actions": [
            {
                "action_id": str,
                "predicted_effect": dict,
                "semantic_confidence": float,
                "stability_score": float,
                "success_rate": float,
            },
            ...
        ],
        "values": [
            {
                "state_key": str,
                "value": float,
                "confidence": float,
                "confirmation_count": float,
            },
            ...
        ],
    }
    """

@classmethod
def from_dict(cls, data: dict) -> "EpigenomeSnapshot":
    """
    Restore from a dictionary.
    
    Malformed records are skipped with a warning.
    Missing fields are filled with neutral values.
    Collection sizes are clamped to the MAX_* limits.
    """

@classmethod
def empty(cls) -> "EpigenomeSnapshot":
    """Create an empty epigenome (for the first generation)."""
```

### 4.5 Diagnostics

```python
def is_empty(self) -> bool:
    """All collections are empty."""

def size(self) -> dict:
    """
    {
        "patterns": int,
        "actions": int,
        "values": int,
        "total": int,
    }
    """

def validate(self) -> List[str]:
    """
    Check the correctness of the epigenome.
    Returns a list of warnings (empty = everything is in order).
    Checks: ranges, NaN/Inf, duplicate keys.
    """

def summary(self) -> dict:
    """
    Brief statistics.
    {
        "patterns_count": int,
        "actions_count": int,
        "values_count": int,
        "mean_pattern_strength": float,
        "mean_action_stability": float,
        "mean_value_confidence": float,
        "source_generation": int,
    }
    """
```

---

## 5. Constants

```python
EPIGENOME_VERSION = "1.0"

MAX_PATTERNS = 32   # maximum number of patterns in an epigenome
MAX_ACTIONS = 16    # maximum number of actions
MAX_VALUES = 24     # maximum number of value estimates

# Ranges of numeric fields
PATTERN_STRENGTH_RANGE = (0.0, 1.0)
ACTION_CONFIDENCE_RANGE = (0.0, 1.0)
ACTION_STABILITY_RANGE = (0.0, 1.0)
ACTION_SUCCESS_RANGE = (0.0, 1.0)
VALUE_RANGE = (-1.0, 1.0)
VALUE_CONFIDENCE_RANGE = (0.0, 1.0)
```

---

## 6. Implementation constraints

1. `EpigenomeSnapshot`, `InheritedPattern`, `InheritedAction`, `InheritedValue` — all `frozen=True`.
2. Collections are stored as `Tuple`, not `List` — for immutability.
3. No imports of NOWA modules — data arrive as dictionaries.
4. No numpy — the standard library only.
5. `inject()` modifies the passed structures IN-PLACE — the caller is responsible for copying if a copy is needed.
6. `extract()` never raises an exception on malformed data — it only skips records.
7. The file `epigenome.py` does not import `genome.py` — zero dependencies between packages A and B.
8. Python version: 3.10+

---

## 7. Test cases

### TC-01: Empty epigenome

```python
epigenome = EpigenomeSnapshot.empty()

assert epigenome.is_empty() is True
assert len(epigenome.patterns) == 0
assert len(epigenome.actions) == 0
assert len(epigenome.values) == 0
assert epigenome.source_generation == 0
assert epigenome.validate() == []
```

### TC-02: Extraction from well-formed data

```python
cortex_patterns = [
    {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5},
    {"context_signature": "ctx_b", "action": "sleep", "strength": 0.7, "reinforcement_count": 3},
    {"context_signature": "ctx_c", "action": "play", "strength": 0.3, "reinforcement_count": 1},
]
action_metadata = {
    "eat": {
        "predicted_effect": {"hunger": -0.5},
        "semantic_confidence": 0.85,
        "stability_score": 0.9,
        "success_rate": 0.8,
        "consolidated": True,
    },
    "play": {
        "predicted_effect": {"energy": -0.3},
        "semantic_confidence": 0.4,
        "stability_score": 0.3,  # below min_stability
        "success_rate": 0.6,
        "consolidated": True,
    },
}
value_profiles = {
    "state_abc": {"value": 0.7, "confidence": 0.8, "confirmation_count": 5.0},
    "state_def": {"value": -0.2, "confidence": 0.3, "confirmation_count": 0.5},  # below min_confirmation
}

epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=cortex_patterns,
    action_metadata=action_metadata,
    value_profiles=value_profiles,
    min_reinforcement=2,
    min_stability=0.5,
    min_confirmation=1.0,
)

# Patterns: ctx_a (5) and ctx_b (3) passed, ctx_c (1) did not
assert len(epigenome.patterns) == 2
assert any(p.context_signature == "ctx_a" for p in epigenome.patterns)
assert any(p.context_signature == "ctx_b" for p in epigenome.patterns)

# Actions: "eat" (stability 0.9) passed, "play" (0.3) did not
assert len(epigenome.actions) == 1
assert epigenome.actions[0].action_id == "eat"

# Values: state_abc (confirmation 5.0) passed, state_def (0.5) did not
assert len(epigenome.values) == 1
assert epigenome.values[0].state_key == "state_abc"
```

### TC-03: Top-N selection of patterns by reinforcement_count

```python
# 10 patterns, max_patterns=3
patterns = [
    {"context_signature": f"ctx_{i}", "action": "eat",
     "strength": 0.5, "reinforcement_count": i}
    for i in range(10)
]

epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=patterns,
    action_metadata={},
    value_profiles={},
    max_patterns=3,
    min_reinforcement=0,
)

assert len(epigenome.patterns) == 3
# Top-3 by reinforcement_count = 9, 8, 7
counts = [p.reinforcement_count for p in epigenome.patterns]
assert sorted(counts, reverse=True) == counts
assert counts[0] == 9
```

### TC-04: Injection with noise does not alter the original

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

original_strength = epigenome.patterns[0].strength

target_patterns = []
target_actions = {}
target_values = {}

stats = epigenome.inject(
    target_cortex_patterns=target_patterns,
    target_action_metadata=target_actions,
    target_value_profiles=target_values,
    noise_level=0.3,
    rng=random.Random(42),
)

# The original is unchanged
assert epigenome.patterns[0].strength == original_strength

# Something was injected
assert stats["patterns_injected"] == 1
assert len(target_patterns) == 1
```

### TC-05: Injection does not overwrite existing keys

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[],
    action_metadata={
        "eat": {
            "predicted_effect": {"hunger": -0.5},
            "semantic_confidence": 0.9,
            "stability_score": 0.8,
            "success_rate": 0.7,
            "consolidated": True,
        }
    },
    value_profiles={},
    min_reinforcement=0,
    min_stability=0.0,
)

# An action that already exists in the target
existing_confidence = 0.3
target_actions = {
    "eat": {
        "semantic_confidence": existing_confidence,
        "stability_score": 0.1,
    }
}

epigenome.inject(
    target_cortex_patterns=[],
    target_action_metadata=target_actions,
    target_value_profiles={},
    noise_level=0.0,
)

# The existing key was not overwritten
assert target_actions["eat"]["semantic_confidence"] == existing_confidence
```

### TC-06: Injection with noise_level=0 — exact values

```python
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[],
    action_metadata={},
    value_profiles={
        "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
    },
    min_reinforcement=0,
    min_stability=0.0,
    min_confirmation=0.0,
)

target_values = {}
epigenome.inject(
    target_cortex_patterns=[],
    target_action_metadata={},
    target_value_profiles=target_values,
    noise_level=0.0,
    rng=random.Random(0),
)

# The exact value, without noise
assert abs(target_values["state_x"]["value"] - 0.6) < 1e-9
assert abs(target_values["state_x"]["confidence"] - 0.8) < 1e-9
```

### TC-07: Blending — union of patterns

```python
epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5},
    ],
    action_metadata={}, value_profiles={},
    min_reinforcement=0,
)

epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_b", "action": "sleep",
         "strength": 0.7, "reinforcement_count": 3},
    ],
    action_metadata={}, value_profiles={},
    min_reinforcement=0,
)

blended = epi_a.blend(epi_b, alpha=0.5)

# Both patterns are present
sigs = {p.context_signature for p in blended.patterns}
assert "ctx_a" in sigs
assert "ctx_b" in sigs
```

### TC-08: Blending — duplicates on state_key are averaged

```python
epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=[], action_metadata={},
    value_profiles={
        "state_x": {"value": 0.8, "confidence": 0.9, "confirmation_count": 4.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
)

epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=[], action_metadata={},
    value_profiles={
        "state_x": {"value": 0.2, "confidence": 0.7, "confirmation_count": 2.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
)

blended = epi_a.blend(epi_b, alpha=0.5)

assert len(blended.values) == 1
blended_val = blended.values[0]
# alpha=0.5: 0.5*0.8 + 0.5*0.2 = 0.5
assert abs(blended_val.value - 0.5) < 1e-9
# confidence = min(0.9, 0.7) = 0.7
assert abs(blended_val.confidence - 0.7) < 1e-9
```

### TC-09: Serialisation round-trip

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5},
    ],
    action_metadata={
        "eat": {
            "predicted_effect": {"hunger": -0.5},
            "semantic_confidence": 0.85,
            "stability_score": 0.9,
            "success_rate": 0.8,
            "consolidated": True,
        }
    },
    value_profiles={
        "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
    },
    min_reinforcement=0, min_stability=0.0, min_confirmation=0.0,
    source_generation=3,
    source_lineage_id="abc",
)

data = epi.to_dict()
restored = EpigenomeSnapshot.from_dict(data)

assert len(restored.patterns) == len(epi.patterns)
assert len(restored.actions) == len(epi.actions)
assert len(restored.values) == len(epi.values)
assert restored.source_generation == epi.source_generation
assert restored.source_lineage_id == epi.source_lineage_id

# Numeric values are preserved
assert abs(restored.patterns[0].strength - epi.patterns[0].strength) < 1e-9
assert abs(restored.values[0].value - epi.values[0].value) < 1e-9
```

### TC-10: from_dict with malformed records does not fail

```python
data = {
    "version": "1.0",
    "source_generation": 1,
    "source_lineage_id": "test",
    "extraction_timestamp": 0.0,
    "patterns": [
        {"context_signature": "good", "action": "eat",
         "strength": 0.8, "reinforcement_count": 3},
        {"context_signature": None, "action": None,  # malformed
         "strength": "bad", "reinforcement_count": -1},
    ],
    "actions": [],
    "values": [],
}

# Must not raise an exception
epi = EpigenomeSnapshot.from_dict(data)

# The well-formed record was accepted
assert len(epi.patterns) == 1
assert epi.patterns[0].context_signature == "good"
```

### TC-11: validate detects problems

```python
# Build via from_dict with deliberately bad data
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    data = {
        "version": "1.0",
        "source_generation": -1,  # a violation
        "source_lineage_id": "",
        "extraction_timestamp": 0.0,
        "patterns": [
            {"context_signature": "ctx", "action": "eat",
             "strength": 1.5,  # outside [0, 1]
             "reinforcement_count": 3},
        ],
        "actions": [],
        "values": [],
    }
    epi = EpigenomeSnapshot.from_dict(data)

issues = epi.validate()
assert len(issues) > 0
```

### TC-12: Blending does not exceed the MAX_* limits

```python
# Build two epigenomes with MAX_PATTERNS patterns each
patterns_a = [
    {"context_signature": f"ctx_a_{i}", "action": "eat",
     "strength": 0.9, "reinforcement_count": 10}
    for i in range(MAX_PATTERNS)
]
patterns_b = [
    {"context_signature": f"ctx_b_{i}", "action": "sleep",
     "strength": 0.8, "reinforcement_count": 8}
    for i in range(MAX_PATTERNS)
]

epi_a = EpigenomeSnapshot.extract(
    cortex_patterns=patterns_a, action_metadata={}, value_profiles={},
    min_reinforcement=0, max_patterns=MAX_PATTERNS,
)
epi_b = EpigenomeSnapshot.extract(
    cortex_patterns=patterns_b, action_metadata={}, value_profiles={},
    min_reinforcement=0, max_patterns=MAX_PATTERNS,
)

blended = epi_a.blend(epi_b)

assert len(blended.patterns) <= MAX_PATTERNS
```

### TC-13: summary contains the expected keys

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.8, "reinforcement_count": 4}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

s = epi.summary()

required_keys = [
    "patterns_count", "actions_count", "values_count",
    "mean_pattern_strength", "mean_action_stability",
    "mean_value_confidence", "source_generation",
]
for key in required_keys:
    assert key in s, f"Missing key: {key}"

assert s["patterns_count"] == 1
assert abs(s["mean_pattern_strength"] - 0.8) < 1e-9
```

### TC-14: Determinism under a fixed rng

```python
epi = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "ctx_a", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

target1, target2 = [], []

epi.inject(target_cortex_patterns=target1, target_action_metadata={},
           target_value_profiles={}, noise_level=0.3, rng=random.Random(42))

epi.inject(target_cortex_patterns=target2, target_action_metadata={},
           target_value_profiles={}, noise_level=0.3, rng=random.Random(42))

assert target1[0]["strength"] == target2[0]["strength"]
```

### TC-15: empty() passes validate

```python
epi = EpigenomeSnapshot.empty()
assert epi.validate() == []
assert epi.is_empty() is True
assert epi.size()["total"] == 0
```

### TC-16: lineage_id on blend is truncated to 64 characters

```python
long_id = "x" * 100
epi_a = EpigenomeSnapshot.empty()
epi_b = EpigenomeSnapshot.empty()

# Replace lineage_id via from_dict
data_a = epi_a.to_dict()
data_a["source_lineage_id"] = long_id
epi_a = EpigenomeSnapshot.from_dict(data_a)

data_b = epi_b.to_dict()
data_b["source_lineage_id"] = long_id
epi_b = EpigenomeSnapshot.from_dict(data_b)

blended = epi_a.blend(epi_b)
assert len(blended.source_lineage_id) <= 64
```

---

## 8. Notes for the implementing agent

- `InheritedPattern`, `InheritedAction`, `InheritedValue` are `frozen=True` dataclasses
- Store the collections in `EpigenomeSnapshot` as `tuple`, not `list`
- `extract()` is a classmethod and accepts only dictionaries (dict); no direct references to NOWA objects
- When injecting patterns: append a dictionary `{"context_signature": ..., "action": ..., "strength": ..., "reinforcement_count": ...}` to the list `target_cortex_patterns`
- When injecting actions: add or skip keys in the `target_action_metadata` dict
- When injecting values: add keys to the `target_value_profiles` dict
- Noise for a pattern's `strength`: `N(0, noise_level * 0.1)`, clamp to [0, 1]
- Noise for a value's `value`: `N(0, noise_level * 0.2)`, clamp to [-1, 1]
- Noise for `confidence`: multiply by `(1 - noise_level * U(0, 0.5))`, clamp to [0, 1]
- Fill `extraction_timestamp` via `time.time()` when `extract()` is called
- On restoration, `from_dict()`: if `source_generation < 0`, set it to 0
- The order of patterns/actions/values in `to_dict()` is descending by strength/stability/confirmation respectively
