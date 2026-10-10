# Ethological Agent: Scientific Account of the Platform

Russian version: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md)

### 1. Subject

The platform studies the expressibility of the NOWA architecture in the behaviour of a single individual under continuous display. The observables are the selected action, its realisation in animation and sound, the affective state, and session persistence. Population, reproduction, and the protocol body are outside this platform.

Scientific description of the complex: [SCIENTIFIC_DESCRIPTION.en.md](../../../Docs/SCIENTIFIC_DESCRIPTION.en.md).

### 2. Composition of the current build

Cognitive modules are imported from the repository core (the root `src/`, or `nowa_src` when packaged). In `src/main.py` they include, among others, `affective_space`, `autonomous_organism` (`DriveSystem`, `EnergySystem`), `basal_ganglia`, `conflict_arbitration`, `emotional_regulation`, `hippocampus`, `neuromodulators`, `sleep`, `wakefulness`, `value_layer`, `intent_memory`, `decision_arbitrator`, `hippocampal_imagine_engine`, the layers of persistence, background, semantic emotions, narratives, and expectations, and also `external_interaction_layer` and `storage`.

The local layer of the platform supplies the ethological repertoire and the presentation:

| Module | Function |
|---|---|
| `behavioral_chains.py` | Behavioural chains |
| `demo_action_realizer.py` | Realisation of an intention as animation parameters |
| `scheduling_system.py` | Local need cycle; retained alongside the core `DriveSystem` |
| `memory_system.py` | Preference memory of chain outcomes |
| `audio_system.py` | Sound accompaniment |
| `pygame_engine.py`, `gui.py` | Display |
| `dataset_loader.py`, `config.py` | Repertoire from datasets |

The early documents `PHASE2_MEMORY_SYSTEM.md` and `PHASE3_SCHEDULING_SYSTEM.md` describe intermediate mechanisms of preference and of the need cycle. `NOWA_INTEGRATION_SPEC.md` and `IMPLEMENTATION_SPEC.md` are normative protocols of further work; they are not a report that the local scheduler has been removed. The current build binds both contours: core modules and the local ethological layer are present together.

### 3. Invariants carried from the core

The canonical affective state remains the eight-dimensional vector of the core. Action gating belongs to the basal ganglia. Consolidation of slow memory is confined to the core sleep cycle. Local preference memory is an additional trace of the platform and does not replace the hippocampus.

### 4. Reproduction

Organism entry point: `Demo/Tamagochi Chinchilla/src/main.py`. Interface: `src/gui.py`. Checks: the directory `Demo/Tamagochi Chinchilla/tests`. Numerical test summaries from early laboratory notes are not carried into the present account.

### 5. Limits

The platform demonstrates a single individual. Demographic conclusions of the colony, and conclusions about the protocol body, do not transfer to it. A quantitative estimate of similarity to the ethology of *Chinchilla lanigera* is not asserted by this text: the repertoire is set by datasets and serves as a controlled environment in which to observe the architecture.

## 6. Documents of the platform

Other documents of this platform:

- [Chinchilla Agent — Technical Specification](chinchilla_agent_spec.en.md)
- [Chinchilla Agent — Implementation Specification](IMPLEMENTATION_SPEC.en.md)
- [NOWA-Powered Chinchilla — Integration Specification](NOWA_INTEGRATION_SPEC.en.md)
- [Phase 2: Learning & Memory Consolidation - Implementation Complete](PHASE2_MEMORY_SYSTEM.en.md)
- [Phase 3: Scheduling System - Autonomous Affect Cycles - Implementation Complete](PHASE3_SCHEDULING_SYSTEM.en.md)
- [Ethological Agent: Composition and Document Status](PROJECT_COMPLETE_SUMMARY.en.md)
