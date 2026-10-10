# Neuromodulator Interaction Layer

Russian version: [spec_neuromodulator_interaction_layer.ru.md](spec_neuromodulator_interaction_layer.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Problem

At present the neuromodulators are merely scalars without interactions:

```text
DA
5HT
NE
ACh
```

In the brain there are pairwise interactions:

```text
DA  ↔ ACh
NE  ↔ ACh
5HT ↔ DA
```

and topography (locality) also matters.

---

## Minimal Improvement

Full maps are not required. An **interaction matrix and slow dynamics** are added.

**Formerly:**

```text
DA_t+1 = f(signal)
```

**Becomes:**

```text
M = [DA, 5HT, NE, ACh]

dM/dt = base_signal
      + W * M
      - decay * M
```

Where `W` is the interaction matrix.

---

## Interaction Matrix

```text
       DA    5HT   NE    ACh
DA   [  0   -0.2   0.1  -0.3 ]
5HT  [  0.1   0   -0.1   0   ]
NE   [  0.2  -0.1   0    0.2 ]
ACh  [ -0.3   0    0.2   0   ]
```

---

## Code Structure

**New class:** `NeuromodulatorField`

```python
def update(signals):

    M = self.levels

    interaction = W @ M

    dM = signals + interaction - decay * M

    M += dt * dM
```

---

## Why This Matters

Biologically plausible effects appear:

```text
high NE  → suppress ACh
high DA  → suppress ACh
high 5HT → damp DA
```
