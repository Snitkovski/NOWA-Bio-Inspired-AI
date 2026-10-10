# NOWA — Plan for Introducing Neuromodulators

Russian version: [NOWA_Neuromodulators_Plan.ru.md](NOWA_Neuromodulators_Plan.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

*A stage before Plan C and before the implementation of feelings*

---

## 0. Aim of the Stage

Introduce neuromodulator fields as:

- indirect regulators of learning and selection
- global modifiers of dynamics
- a source of long-term shifts in behaviour

**Without:**

- subjective experience
- symbolic emotions
- the logic "if X, then I feel Y"

> **Neuromodulators are the physics of the system, not its psychology.**

---

## 1. Principled Architectural Position

### 1.1 What a neuromodulator is in NOWA

**A neuromodulator is:**

- a slowly changing scalar field
- something that affects probabilities, rates, and thresholds of processes

**It does not:**

- make decisions
- store meaning
- constitute a feeling

**It affects:**

- learning
- consolidation
- forgetting
- exploration
- stabilization of strategies

---

## 2. Minimal Neuromodulator Set (v1)

### 2.1 Dopamine (DA) — reinforcement / value

**Source:**

- positive reward
- positive net_affect of chains
- successful stabilization of patterns

**Affects:**

- strengthening of Temporal Chains
- growth of pattern stability
- increase of the weight of successful actions
- lowering of the repetition threshold

**Does not:**

- choose an action
- encode pleasure

### 2.2 Norepinephrine (NE) — mobilization / surprise

**Source:**

- novelty
- conflict
- abrupt changes of affect
- unexpected consequences

**Affects:**

- increase of exploration
- acceleration of updates
- increase of selector sensitivity
- reduction of habit inertia

### 2.3 Serotonin (5-HT) — stability / satiation

**Source:**

- absence of conflicts
- repeated neutral or moderately positive outcomes
- stabilized chains

**Affects:**

- reduction of arousal
- slowing of learning
- increase of pattern robustness
- suppression of abrupt changes

### 2.4 Cortisol (CORT) — stress / overload

**Source:**

- high threat
- repeated negativity
- unresolved conflict

**Affects:**

- accelerated forgetting
- suppression of exploration
- simplification of strategies
- shortening of temporal chains

---

## 3. Where They Live in the Architecture

### 3.1 New module: `neuromodulators.py`

```python
class NeuromodulatorState:
    dopamine: float
    norepinephrine: float
    serotonin: float
    cortisol: float
    timestamp: float
```

- values are normalized (for example 0.0–1.0)
- there is decay over time
- there are no direct calls from ActionSelector

### 3.2 Connection to Agent

In Agent:

```python
self.neuromodulators = NeuromodulatorState()
```

**Update occurs:**

- after a consequence
- after sleep
- under strong novelty or conflict

---

## 4. Points of Influence (strictly limited)

### 4.1 Hippocampus

Neuromodulators affect:

- activation_energy
- the probability of entering the sleep candidates

**Example:**

- high DA increases activation
- high CORT decreases retention

### 4.2 SleepManager

During sleep:

- DA strengthens consolidation
- CORT strengthens forgetting
- 5-HT stabilizes patterns that are already strong

> **Important:** sleep is the principal channel through which modulators act

### 4.3 Temporal Chains (Plan B)

- DA increases the stability of chains with positive net_affect
- CORT decreases the max_len of chains
- NE increases the probability of forming new chains

### 4.4 ActionSelector (indirectly)

**Not directly.**

Through:

- affect_modifier
- exploration/noise
- confidence_threshold

---

## 5. What This Stage Strictly Does Not Do

Forbidden at this stage:

- naming modulators as feelings
- showing them in the GUI as "emotions"
- using them in if/else
- adding self-reference
- binding them to "I feel"

---

## 6. GUI (minimal)

Diagnostic display only:

```
Neuromodulators:
  DA: 0.42
  NE: 0.31
  5-HT: 0.58
  CORT: 0.12
```

No interpretations.

---

## 7. Test Cases (required)

### 7.1 Repeated success

- DA rises
- chains stabilize
- exploration falls

### 7.2 Abrupt surprise

- NE jumps
- choice becomes less deterministic

### 7.3 Prolonged negativity

- CORT rises
- old chains decay
- strategies simplify

### 7.4 Prolonged stability

- 5-HT rises
- the system "settles"
- learning slows

---

*The document describes an architectural approach to introducing a neuromodulator system into NOWA without anthropomorphization, and with attention on the physical mechanisms of modulation.*
