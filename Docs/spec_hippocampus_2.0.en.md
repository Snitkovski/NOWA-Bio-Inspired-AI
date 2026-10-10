# Hippocampus 2.0 Specification

Russian version: [spec_hippocampus_2.0.ru.md](spec_hippocampus_2.0.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**Module:** Episodic Memory System  
**Role:** Pattern Completion + Novelty Signaling  
**Biological Analogy:** CA3 (autoassociation), CA1 (novelty), Dentate Gyrus (pattern separation)

---

## 1. Design Objectives

- Remove exact signature matching
- Implement fuzzy recall
- Add CA3-like autoassociative reconstruction
- Implement CA1-like novelty detection
- Introduce contextual-temporal encoding
- Preserve computational stability

---

## 2. Conceptual Model

Hippocampus 2.0 stores not events, but distributed state signatures.

A signature is:

```python
signature = {
    "features": set[str],
    "drive_state": vector,
    "context_hash": int,
    "timestamp": int
}
```

---

## 3. Data Structures

### 3.1 Episodic Store

```python
class EpisodicMemory:
    signatures: List[Signature]
    decay_rate: float
    max_capacity: int
```

### 3.2 Signature Structure

```python
class Signature:
    feature_set: Set[str]
    drive_vector: np.array
    context_vector: np.array
    timestamp: int
    activation_weight: float
```

---

## 4. Pattern Separation (Dentate Gyrus proxy)

Before writing:

- Feature sparsification is applied
- Low-information features are removed
- The size of `feature_set` is limited

```python
if len(feature_set) > max_features:
    feature_set = top_k_by_salience(feature_set)
```

Aim:

- minimize overlap
- increase discrimination

---

## 5. CA3-like Pattern Completion

### 5.1 Similarity Function

Principal metric (Jaccard similarity):

```
similarity(A, B) = |A ∩ B| / |A ∪ B|
```

### 5.2 Recall Algorithm

```python
def recall(current_signature):
    sims = []
    for stored in memory:
        sims.append(similarity(current, stored))

    top_k = select_k_highest(sims)
    return reconstruct(top_k)
```

### 5.3 Reconstruction

```python
def reconstruct(top_k):
    weighted_union = union(features weighted by similarity)
    return weighted_union
```

Weight:

```
w_i = similarity_i / sum(similarity_k)
```

This is an approximation of autoassociative recall.

---

## 6. CA1-like Novelty Detection

Novelty is defined as:

```
novelty = 1 - max_similarity(current, recent_N)
```

where `recent_N` is the last N episodes (EMA window).

### 6.1 Interpretation

| Novelty   | Meaning       |
|-----------|---------------|
| < 0.2     | familiar      |
| 0.2–0.6   | partial match |
| > 0.6     | novel         |
| > 0.85    | high novelty  |

### 6.2 Downstream Effects

Novelty is used for:

- increased exploration drive
- increased consolidation probability
- increased learning rate
- increased conflict sensitivity

---

## 7. Temporal Context Encoding

A `context_vector` is added:

```python
context_vector = [
    time_bucket,
    rolling_state_hash,
    discretized_drive_state
]
```

### 7.1 Time Bucketing

```python
time_bucket = t % cycle_length
```

It models circadian / rhythmic coding.

### 7.2 Rolling Hash

```python
rolling_hash = hash(last_k_events)
```

It creates contextual dependence.

---

## 8. Consolidation Gate

Consolidation probability:

```
P(consolidate) = f(novelty, repetition_count, reward_signal)
```

Example:

```
P = novelty * reward_weight + repetition_factor
```

---

## 9. Memory Decay

Activation weight:

```python
activation_weight *= (1 - decay_rate)
```

Deletion:

```python
if activation_weight < threshold:
    delete(signature)
```

---

## 10. Computational Constraints

- Recall complexity: O(N)
- Optimization through an inverted index is possible
- `max_capacity` is bounded
- decay prevents exponential growth

---

## 11. Interface API

### 11.1 Store

```python
hippocampus.store(current_signature)
```

### 11.2 Recall

```python
reconstructed = hippocampus.recall(current_signature)
```

Returns:

```json
{
    "reconstructed_features": "set",
    "novelty_score": 0.0,
    "similarity_top_k": []
}
```

---

## 12. Experimental Validation Plan

### 12.1 Partial Input Recovery

- Remove 30–50% of features
- Check reconstruction

Target: 70% reconstruction fidelity.

### 12.2 Novelty versus Reward Prediction Error

Check the correlation:

```
corr(novelty, TD_error)
```

A positive correlation is expected.

### 12.3 Noise Robustness

- Add random feature perturbations
- Check the false recall rate

---

## 13. Failure Modes

| Failure             | Cause               | Mitigation             |
|---------------------|---------------------|------------------------|
| Over-recall         | low threshold       | dynamic threshold      |
| Memory collapse     | high overlap        | stronger sparsification|
| Recall explosion    | large N             | decay tuning           |
| Novelty always high | bad feature encoding| feature normalization  |
