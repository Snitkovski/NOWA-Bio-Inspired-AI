# Cognitive Architecture — Research Roadmap

Russian version: [cognitive_architecture_roadmap.ru.md](cognitive_architecture_roadmap.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Overall Objective

Develop a cognitive architecture that includes:

- Fuzzy hippocampus (CA3/CA1-like)
- Cortical strategy layer (logit-based policy)
- Drive-modulated action selection
- Continuous emotional regulation
- Conflict and arbitration (ACC-like)
- Dopaminergic TD learning (actor–critic)
- External sensory integration
- Consolidation pipeline

---

## Phase 1 (Months 1–2) — Hippocampus 2.0: Pattern Completion and Novelty

### 1.1 Objectives

- Remove exact-match
- Implement fuzzy recall
- Add novelty detection
- Introduce contextual-temporal encoding

### 1.2 Research tasks

#### A. Fuzzy Similarity Recall

Metric:

```
similarity = jaccard(signature_A, signature_B)
```

Experiments:

- Recall accuracy under partial input (20–60% missing features)
- False recall rate
- Recall latency

Success criterion: 70% pattern restoration under 40% input loss.

#### B. Autoassociative Reconstruction (CA3 proxy)

- Top-k similarity aggregation
- Weighted union reconstruction

Metrics:

- Reconstruction fidelity score
- Noise amplification index

#### C. Novelty Signal (CA1 proxy)

```python
novelty = 1 - max_similarity(current, recent_N)
```

Verify:

- Correlation of novelty with reward prediction error
- Effect of novelty on exploration rate

#### D. Temporal Context Encoding

Introduce:

- rolling state hash
- drive snapshot embedding
- time bucket encoding

Metrics:

- Context recall differentiation
- False context collision rate

### Phase 1 Exit Criteria

- Recall does not degrade as memory grows
- Novelty correlates with RPE
- No exponential growth of search time

> **Expected result:** Hippocampus 8/10 in biological plausibility.

---

## Phase 2 (Months 3–4) — Continuous Emotional Regulation

### 2.1 Objective

Remove binary regulation and move to tonic modulation.

### 2.2 Model

```
alpha = base_alpha * (1 + k * stability_index_centered)
```

Where:

- `stability_index` — EMA over recent volatility
- `alpha` — affective inertia

### 2.3 Experiments

#### A. Oscillation Suppression

Metrics:

- Variance reduction in affective state
- Overshoot frequency

#### B. Adaptation Speed

Metrics:

- Time-to-stability after a shock input
- Plasticity under low stability

### 2.4 Remove the 500-step warmup

Replace it with an EMA window of 30–50.

Test: short-session robustness (<100 steps).

### Phase 2 Exit Criteria

- Reduction of oscillation amplitude by at least 25%
- No hysteresis collapse
- No dead-zone behaviour

---

## Phase 3 (Months 5–6) — Conflict and Arbitration Layer (ACC-like)

### 3.1 Objective

Replace the symbolic critic with conflict dynamics.

### 3.2 Conflict signal

Variants:

```python
entropy(strategy_distribution)
```

or

```python
conflict = -variance(logits)
```

### 3.3 Arbitration Rules

If `conflict` rises:

- temperature decreases
- recall depth increases
- exploration weight increases
- novelty sensitivity increases

### 3.4 Experiments

#### A. Ambiguous Context Test

- Present alternatives that are close in value
- Measure the stability of choice

Metrics: flip rate, decision latency, confidence calibration.

#### B. Overconfidence Suppression

If `low entropy + high novelty`, is the strategy corrected?

### Phase 3 Exit Criteria

- Reduction of premature convergence
- No pathological indecision
- Conflict stabilizes behaviour

---

## Phase 4 (Month 7) — Dopaminergic TD-Learning Layer

### 4.1 Introduction of a Value Function

```python
delta = r + gamma * V(s') - V(s)
```

Update of:

- Drives
- Strategy logits
- Exploration rate

### 4.2 Actor–Critic Integration

```
Actor  = strategy logits
Critic = V(s)
```

### 4.3 Experiments

#### A. Delayed Reward Task

- Reward after N steps
- Verify credit assignment

Metrics: learning speed, reward maximization rate.

#### B. Stability Under Non-Stationarity

- Change of the reward structure
- Verify adaptability

### Phase 4 Exit Criteria

- Improvement of long-term return by at least 20%
- No runaway oscillations
- No value divergence

---

## Phase 5 (Months 8–9) — External World Integration and Consolidation

### 5.1 Sensory Gateway

External data pass to embeddings and then to the hippocampus. There is no direct rule-based ingestion.

### 5.2 Consolidation Pipeline

- Frequent patterns pass to the cortex
- Rare events are retained episodically
- Novelty gating sets consolidation probability

### 5.3 Self-Play / Simulation

Runs of:

- Parallel scenario simulation
- Counterfactual testing
- Exploration policy stress-test

### 5.4 Metrics

- Generalization score
- Catastrophic forgetting index
- Memory growth efficiency

---

## Global Research Metrics

| Metric                        | Target        |
|-------------------------------|---------------|
| Stability Index               | rises         |
| Oscillation Amplitude         | falls         |
| Recall Fidelity               | > 70%         |
| Long-term reward              | rises 20–40%  |
| Catastrophic forgetting       | < 10%         |
| Decision entropy calibration  | within 0.1    |

---

## Risk Matrix

| Risk                  | Mitigation                        |
|-----------------------|-----------------------------------|
| Overfitting recall    | similarity threshold tuning       |
| Conflict paralysis    | arbitration ceiling               |
| Value divergence      | TD clipping                       |
| Memory explosion      | decay + consolidation             |
| Oscillation loop      | tonic regulation                  |

---

## Target architecture

```
Sensory Input
    ↓
Hippocampus (fuzzy + novelty)
    ↓
Cortex (strategy logits)
    ↓
Drive modulation
    ↓
Conflict / Arbitration
    ↓
Action
    ↓
Environment
    ↓
Reward
    ↓
TD error
    ↓
Memory + Strategy update
```

---

## Strategic objective by the end of the programme

Not merely a decision engine, but a cognitive architecture that is:

- partly self-regulating
- biologically plausible
- distributed
- stably learning
- autonomous
