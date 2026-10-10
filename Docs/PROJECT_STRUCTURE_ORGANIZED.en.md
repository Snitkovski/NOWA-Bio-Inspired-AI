# Organized Structure of the NOWA-Cognitive Project

Russian version: [PROJECT_STRUCTURE_ORGANIZED.ru.md](PROJECT_STRUCTURE_ORGANIZED.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**Date**: 31 January 2026  
**Status**: reorganized

---

## New project structure

```
NOWA-Cognitive/
├── src/                          # Source code
│   ├── action_intent.py
│   ├── action_realizer.py
│   ├── agent.py
│   ├── affect.py                    # New: affective system
│   ├── cortex.py
│   ├── dataset.py
│   ├── experience.py
│   ├── gui.py
│   ├── hippocampus.py
│   ├── intent_memory.py
│   ├── loader.py
│   ├── player.py
│   ├── sample.py
│   ├── selector.py
│   ├── sleep_manager.py
│   ├── sleep.py
│   ├── storage.py
│   ├── train_from_dataset.py
│   ├── trainer.py
│   ├── usage_example.py
│   └── dataset/
│       └── dialog_experience.json
│
├── tests/                        # All tests
│   ├── __init__.py
│   ├── test_adaptive_mouth.py
│   ├── test_affective_regulators.py  # New: affect regulators
│   ├── test_affect_integration.py     # New: affect integration
│   ├── test_agent.py
│   ├── test_dataset_loading.py
│   ├── test_dialog_loading.py
│   ├── test_experience_immutability.py
│   ├── test_fix.py
│   ├── test_gui_affective.py          # Moved: from the root
│   ├── test_gui_refactoring.py
│   ├── test_habits_loading.py         # Moved: from the root
│   ├── test_hippocampus.py
│   ├── test_intent_memory.py
│   ├── test_intent_memory_integration.py
│   ├── test_save_load_affect.py       # Moved: from the root (new)
│   ├── test_selector.py
│   ├── test_sleep_consolidation.py
│   ├── test_trainer.py
│   ├── test_trainer_deprecated.py
│   └── __pycache__/
│
├── Docs/                         # All documentation
│   ├── README.md                    # Principal documentation
│   ├── ADAPTIVE_MOUTH_QUICK_REFERENCE.md
│   ├── ADAPTIVE_MOUTH_REFACTORING_COMPLETE.md
│   ├── ADAPTIVE_MOUTH_SUMMARY.py
│   ├── CHANGELOG.md
│   ├── CHANGES_SUMMARY.md           # Moved: from the root
│   ├── COMPLETE_PROJECT_REPORT.en.md   # Moved: from the root
│   ├── DATASET_LOADING_FIX.md
│   ├── DELIVERY_SUMMARY.md
│   ├── EXECUTIVE_SUMMARY.md         # Moved: from the root
│   ├── FILES_CHANGES_COMPLETE_LIST.md # Moved: from the root
│   ├── FINAL_PROJECT_SUMMARY.md     # Moved: from the root
│   ├── FINAL_REPORT.md              # Moved: from the root
│   ├── FINAL_SUMMARY_RU.md          # Moved: from the root
│   ├── GUI_AFFECTIVE_VISUALIZATION_REPORT.md # Moved: from the root
│   ├── GUI_COMPLETE.md
│   ├── GUI_HABITS_IMPLEMENTATION.md # Moved: from the root
│   ├── GUI_QUICK_REFERENCE.md
│   ├── GUI_REFACTORING.md
│   ├── GUI_REFACTORING_SUMMARY.md
│   ├── GUIDE_AUTO_TRAINING.md
│   ├── IMPLEMENTATION_REPORT.md     # Moved: from the root
│   ├── INDEX.md                     # Moved: from the root
│   ├── INTENT_MEMORY.md
│   ├── INTENT_MEMORY_IMPLEMENTATION.md
│   ├── LEARNING.md
│   ├── PROJECT_COMPLETION_CONFIRMATION.md # Moved: from the root
│   ├── PROJECT_STATISTICS.md        # Moved: from the root
│   ├── PROJECT_STRUCTURE.md         # Moved: from the root
│   ├── QUICK_START_RU.md            # Moved: from the root
│   ├── README_AFFECTIVE_SYSTEM.md   # Moved: from the root
│   ├── README_AUTO_TRAINING.md
│   ├── README_REFACTORED.md
│   ├── REALIZATIONS_EXPANSION.md
│   ├── REFACTORING_COMPLETE.md
│   ├── REFACTORING_STATUS.md
│   ├── SAVE_LOAD_AFFECT_STATE.md    # Moved: from the root (new)
│   ├── START_HERE.md                # Moved: from the root
│   ├── SUMMARY.md
│   ├── nowa_affective_refactor_plan.md
│   ├── nowa_refactoring_plan_intent_memory.md
│   ├── nowa_refactoring_plan_v_2.md
│   └── refactoring_plan_adaptive_mouth.md
│
├── Demo/                         # Examples and demonstrations
│   ├── demo_intent_memory.py
│   ├── demo_realizations.py
│   └── examples_training.py
│
├── datasets/                     # Training data
│   ├── habits.json
│   ├── realizations_advanced.json
│   ├── realizations_basic.json
│   ├── realizations_extended.json
│   └── test.json
│
├── saves/                        # Saved agent states
│
├── .venv/                        # Python virtual environment
│
├── .pytest_cache/                # pytest cache
│
├── __pycache__/                  # Python cache
│
├── LICENSE                       # Project license
├── .gitignore                    # Git ignore
└── README.md                     # (link to Docs/README.md)
```

---

## Reorganization statistics

### Before reorganization
```
Project root:
  ├─ 18 .md files (documentation)
  ├─ 3 .py files (tests)
  └─ Other files
```

### After reorganization
```
All 18 documents moved to Docs/
All 3 additional tests moved to tests/
Project root cleaned
```

### New figures
- **Docs/**: 43 files (was 25, 18 added)
- **tests/**: 22 files (was 19, 3 added)
- **src/**: 24 files (unchanged)
- **Root**: configuration files and data only

---

## What moved

### Into Docs/ (18 files)
```
CHANGES_SUMMARY.md
COMPLETE_PROJECT_REPORT.en.md
EXECUTIVE_SUMMARY.md
FILES_CHANGES_COMPLETE_LIST.md
FINAL_PROJECT_SUMMARY.md
FINAL_REPORT.md
FINAL_SUMMARY_RU.md
GUI_AFFECTIVE_VISUALIZATION_REPORT.md
GUI_HABITS_IMPLEMENTATION.md
IMPLEMENTATION_REPORT.md
INDEX.md
PROJECT_COMPLETION_CONFIRMATION.md
PROJECT_STATISTICS.md
PROJECT_STRUCTURE.md
QUICK_START_RU.md
README_AFFECTIVE_SYSTEM.md
SAVE_LOAD_AFFECT_STATE.md
START_HERE.md
```

### Into tests/ (3 files)
```
test_save_load_affect.py
test_habits_loading.py
test_gui_affective.py
```

---

## Purpose of each folder

### src/
**Purpose**: project source code  
**Contains**: Python modules of the system core
- Agent core (agent.py, cortex.py, hippocampus.py)
- Affective system (affect.py)
- GUI (gui.py)
- Training and learning (trainer.py, train_from_dataset.py)
- Storage (storage.py)

### tests/
**Purpose**: all project tests  
**Contains**: unit tests and integration tests (22 files)
- Core tests (test_agent.py, test_cortex.py)
- Affective-system tests (test_affective_regulators.py, test_affect_integration.py)
- GUI tests (test_gui_affective.py, test_gui_refactoring.py)
- Memory tests (test_hippocampus.py, test_intent_memory.py)
- Save and load tests (test_save_load_affect.py)
- And much else

### Docs/
**Purpose**: complete project documentation  
**Contains**: 43 markdown files
- Principal documentation (README.md)
- Implementation reports (IMPLEMENTATION_REPORT.md, DELIVERY_SUMMARY.md)
- Guides (QUICK_START_RU.md, GUIDE_AUTO_TRAINING.md)
- Refactoring plans and detailed reports
- Final documents on project completion

### Demo/
**Purpose**: examples and demonstrations  
**Contains**: Python scripts that demonstrate functionality
- demo_intent_memory.py — demonstration of intent memory
- demo_realizations.py — demonstration of realizations
- examples_training.py — training examples

### datasets/
**Purpose**: training data  
**Contains**: JSON files with data
- habits.json — agent habits
- realizations_*.json — realizations of different levels
- test.json — test data

### saves/
**Purpose**: saved states  
**Contains**: files of saved agent states

---

## Advantages of the new structure

- **Clarity**: the project root contains only critically important files
- **Logic**: each kind of file is in its place
- **Scalability**: new documents and tests are easy to add
- **Professional form**: it matches standards of project organization
- **Navigation**: the project structure is easier to follow

---

## Recommendations

1. **When adding new documents**: place them in `Docs/`
2. **When adding new tests**: place them in `tests/`
3. **When adding new examples**: place them in `Demo/`
4. **When adding new data**: place them in `datasets/`
5. **When saving state**: `saves/` is used (automatically)

---

## Navigation

- **Getting started**: [START_HERE.md](START_HERE.en.md)
- **Quick start**: [QUICK_START_RU.md](QUICK_START_RU.en.md)
- **Principal documentation**: [README.md](README.md)
- **Document index**: [INDEX.md](INDEX.en.md)

---

**Update date**: 31 January 2026  
**Structure version**: 2.0  
**Status**: organized and ready
