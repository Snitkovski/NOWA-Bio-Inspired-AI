# Phase 4.2 — Emotional Memory and Narratives

Russian version: [phase_4_2_emotional_memory_narratives.ru.md](phase_4_2_emotional_memory_narratives.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Status

**A mandatory stage before Phase 4.3 and Phase 5**  
It does not influence decision-making or planning

---

## Aim of the Phase

To form the **emotional autobiography of the agent**:
- stable emotional patterns
- recurring emotional episodes
- elements of character
- emotional narratives

Phase 4.2 answers **only** the question:
> *“What have I lived through emotionally, and whom am I becoming?”*

---

## Input Data

### Required
- `SemanticEmotionsLayer` (Phase 4.1)
- `AffectiveSpace` (Phase 4)
- `AffectiveBackgroundField`
- `agent_lifetime`
- timestamps

### Prohibited
- Any forecasts
- Any expectations
- Any action candidates

---

## Output Data

### Structures

- **EmotionalEpisode**
  - emotion(s)
  - duration
  - mean activation
  - stability
  - obsessive flag

- **EmotionalPattern**
  - frequency
  - recurrence
  - inertia

- **NarrativeFragments** (textual)
  - “It often arises…”
  - “A tendency toward…”
  - “Usually this lasts…”

---

## Principal Functions

### 1. Aggregation
Aggregation of semantic emotions into temporal episodes

### 2. Consolidation
Union of recurring episodes into patterns  
Accounting for the recency of episodes (recency weighting)

### 3. Character Trace Formation
Formation of long-lived traits (for example, obsessiveness, anxiousness)

### 4. Narrative Rendering
Generation of **retrospective** textual descriptions  
A phrase of dominant shift is admissible: “Earlier X predominated; now Y arises more often”

---

## Strict Constraints

- No future tense
- No conditions of the form `if … then …`
- No utility
- No influence on the selector
- No recommendations of action
- Patterns and traits are not formed when the number of episodes is insufficient (`min_total_episodes`)

---

## Anti-patterns (Critically Important)

### 4.2 used as forecasting
> “Usually after this there will be…”

**Error:** that is Phase 4.3

---

### 4.2 used as optimisation
> “Such states are better avoided”

**Error:** Phase 5

---

### 4.2 used as substitution of memory by expectation
> “I know that next time I will feel…”

**Error:** destruction of temporal direction

---

### 4.2 used as a log instead of a narrative
> storage of raw logs without aggregation

**Error:** absence of character formation

---

## Test Cases

### Test 4.2.1 — Recurrent Sadness
**Input:** repeated sadness activations over a long lifetime  
**Expected:** a narrative of the form “Sadness often arises”

---

### Test 4.2.2 — Obsessive Pattern
**Input:** high inertia and a low fall_rate of emotions  
**Expected:** an obsessive flag in the pattern

---

### Test 4.2.3 — Mixed Episodes
**Input:** overlapping episodes of joy and tension  
**Expected:** a composite narrative fragment

---

### Test 4.2.4 — No Future Leakage
**Check:** the output contains no future-oriented words

---

### Test 4.2.5 — Stability Effect
**Input:** slowly changing emotions  
**Expected:** higher narrative confidence and persistence

---

### Test 4.2.6 — Direction Shift
**Input:** early dominance of emotion X, recent dominance of emotion Y  
**Expected:** a narrative of the form “Earlier X predominated; now Y arises more often”

---

## Architectural Role

Phase 4.2 is:
- not control
- not intelligence
- not planning

It is **emotional memory**, from which **character grows naturally**.

---

## Readiness Criterion

The phase is regarded as implemented if:
- the agent can describe its emotional patterns
- the descriptions are stable in time
- there is no influence on actions

---

## Note

Phase 4.2 is the **point of no return** to simple reactive agents.  
After it, the agent already *has a past*.
