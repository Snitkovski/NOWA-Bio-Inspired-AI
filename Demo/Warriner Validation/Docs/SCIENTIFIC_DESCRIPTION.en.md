# Lexical Validation: Scientific Account of the Platform

Russian version: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md)

### 1. Subject

The platform compares the affective response of a colony of sovereign NOWA agents with human norms of affective word meaning. The reference is the valence and arousal ratings of Warriner, Kuperman, and Brysbaert (2013), the field `V.Mean.Sum` for valence. The question addressed by a run is whether the mean valence shift of the colony agrees with the rank of the human norm.

Scientific description of the complex: [SCIENTIFIC_DESCRIPTION.en.md](../../../Docs/SCIENTIFIC_DESCRIPTION.en.md). The implementation contract is `NOWA_Warriner_Validation_Spec_2.1.md` and the preceding specification in the same directory.

The Streamlit dashboard and `run_quick.py` open in English. `--lang ru` or `NOWA_LANG=ru` switches the labels; the dashboard sidebar has separate EN and RU buttons, and the active one is highlighted. `--lang` wins over `NOWA_LANG`.

### 2. Method

The environment translates a word into context events and delivers them to each agent separately. Each agent performs its own `step`. The environment reads public state after the step and aggregates shifts. Shared memory, a shared command bus, and a central controller are absent. Hippocampal seeding, when performed, is applied to each agent separately; the corpus order for an agent is shuffled by that agent's generator.

Dependent quantities: the mean valence shift of the colony and the mean arousal shift. Measures of association with the norm: Spearman's rank correlation, Pearson's coefficient, and concordance correlation. The protocol further provides for the association of the dopamine shift and the cortisol shift with the valence norm. The report also contains standard deviations, the fraction of zero memory activation, and a breakdown by colony archetypes.

Thresholds recorded in the normative specification (for example, the bounds of a weak and of a stronger signal) are rules of the demonstration protocol. They are not a correlation magnitude established by the present text. A numerical outcome is produced by running the validator and is not entered here as a constant.

### 3. Invariants

1. An agent does not receive the stimulus through a shared method of the colony. The loop visits individuals.
2. The environment does not write the agent's internal state.
3. The axes of \(A(t)\) are not extended to fit the Warriner scales. The shift is read from the canonical state.
4. The observer is passive with respect to action selection.

### 4. Reproduction

Orchestration code: `src/nowa_validation/` (`warriner_validator.py`, `word_stimulus_encoder.py`, `nowa_colony.py`, `hippocampus_seeder.py`). A short launch is provided by `run_quick.py`; the graphical contour is `demo_app.py`. Checks are placed beside the platform according to its adopted test layout.

### 5. Limits of interpretation

Agreement of ranks with a lexical norm is a test of affective mapping, not a demonstration of semantic understanding. A zero or weak correlation is compatible with a sound architecture if the stimulus encoder does not activate relevant traces. A strong correlation under one encoder mode does not transfer to another mode without a separate run.

## 6. Documents of the platform

Other documents of this platform:

- [NOWA × Warriner Validation Demo — Technical Specification](NOWA_Warriner_Validation_Spec.en.md)
- [NOWA × Warriner Validation Demo — Technical Specification](NOWA_Warriner_Validation_Spec_2.1.en.md)
