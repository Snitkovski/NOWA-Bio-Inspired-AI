# Slow Tonic Dopamine

Russian version: [spec_slow_tonic_dopamine.ru.md](spec_slow_tonic_dopamine.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Problem

Tonic DA is updated too quickly. In the brain:

```
tonic DA  → slow baseline
phasic DA → fast spikes
```

---

## Solution

The phasic and tonic components are separated.

**Phasic:**

```
DA_phasic = reward_prediction_error
```

**Tonic:**

```
DA_tonic(t+1) = DA_tonic + k * (mean(DA_phasic) - DA_tonic)
```

Where `k ≈ 0.01`.

**Code:**

```python
tonic_DA += slow_rate * (mean_phasic - tonic_DA)
```

---

## Effect

```
phasic → spikes
tonic  → baseline drift
```
