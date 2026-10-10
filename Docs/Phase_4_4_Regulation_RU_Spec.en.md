# Phase 4.4 — Regulation Based on Emotional Expectations

Russian version: [Phase_4_4_Regulation_RU_Spec.ru.md](Phase_4_4_Regulation_RU_Spec.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Document Status

Phase: 4.4  
Generation date: 2026-02-12T08:27:23.447697 UTC  
Dependencies: Phase 4.2 — Emotional Memory & Narratives; Phase 4.3 — Emotional Expectations

---

# 1. Purpose

Phase 4.4 introduces a strictly bounded regulatory layer that uses the forecasts of Phase 4.3 for gentle homeostatic stabilisation of the background state.

The layer performs ONLY stabilisation.

PROHIBITED:
- altering semantic_emotions
- altering the affective space directly
- altering memory (4.2)
- altering expectations (4.3)
- influencing action selection or planning (Phase 5)
- altering utility / decision weights

PERMITTED:
- a small correction of background parameters
- a small correction of neuromodulators

---

# 2. Architectural Boundaries

| Layer | May modify |
| --- | --- |
| 4.2 | Memory only |
| 4.3 | Nothing external |
| 4.4 | Background parameters only |
| 5.x | Behaviour |

Phase 4.4 DOES NOT INTERSECT with Phase 5.

---

# 3. Inputs of update()

- expectations_snapshot: Dict
- affective_background_snapshot: Dict[str, float]
- neuromodulators_snapshot: Dict[str, float]
- agent_lifetime: float
- timestamp: float

All inputs are read-only.

---

# 4. Output of update()

```text
{
  "regulation_active": bool,
  "regulation_mode": "none" | "stabilizing" | "dampening" | "containment",
  "applied_adjustments": {
      "background_shift": "...",
      "neuromodulator_shift": "..."
  }
}
```

Constraints:
- |delta| ≤ 0.1 per step
- L2-norm of all corrections ≤ 0.15

---

# 5. Activation Triggers

Regulation is enabled if:

1. probability ≥ 0.8 AND confidence ≥ 0.6
2. risk_of_repetition == True
3. global_outlook == "escalating"

Otherwise:
- regulation_active = False
- mode = "none"

---

# 6. Modes

## 6.1 Stabilizing

Conditions:
- escalating outlook
- rising activation

Effect:
- arousal −≤0.05
- relaxation +≤0.05

Aim: gentle damping of escalation.

---

## 6.2 Dampening

Conditions:
- obsessive pattern
- risk_of_repetition == True

Effect:
- reduction of emotional_gain ≤0.05
- reduction of dominance bias

---

## 6.3 Containment

Conditions:
- high probability
- increasing trend
- high confidence

Effect:
- limitation of neuromodulator amplification
- gentle reduction of amplification

---

# 7. Critical Constraints

## 7.1 Prohibition of Positive Feedback

Regulation MUST NOT increase the probability of the predicted emotion.

## 7.2 Prohibition of Altering semantic_emotions

Direct alterations are prohibited.

## 7.3 Prohibition of Altering Memory

episodes/patterns/narratives are not changed.

## 7.4 Prohibition of Influence on Behaviour

No alteration of utility, ranking, or planning.

## 7.5 Bound on the Strength of Correction

Corrections are small and bounded by a norm.

---

# 8. Anti-Patterns

1. A self-amplifying loop
2. Over-regulation
3. Permanently active regulation
4. Covert influence on planning
5. Complete emotional flattening

---

# 9. Test Cases

## 9.1 Escalation of Joy

Expected:
- mode = stabilizing
- arousal decreases
- the probability of joy does not rise because of regulation

## 9.2 Obsessive Fear

Expected:
- mode = dampening
- emotional_gain decreases
- fear probability is not increased by regulation

## 9.3 Neutral State

Expected:
- regulation_active = False

## 9.4 Volatility

Expected:
- minimal regulation

## 9.5 Combined Risk

Expected:
- mode = containment
- the constraints are observed

---

# 10. Completion Criteria

1. No self-reinforcing cycles over 1000 steps.
2. Behaviour is identical to the version without 4.4.
3. Memory and Expectations are not altered by regulation.
4. All anti-pattern tests pass.

---

End of the Phase 4.4 specification.
