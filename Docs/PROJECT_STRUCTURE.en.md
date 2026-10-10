# Project Structure of NOWA with Affective Regulators

Russian version: [PROJECT_STRUCTURE.ru.md](PROJECT_STRUCTURE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

```
e:\git\NOWA-Cognitive\
│
├── Documentation (completion reports)
│   ├── PROJECT_COMPLETION_CONFIRMATION.md  ← start here
│   ├── QUICK_START_RU.md  ← for a quick start
│   ├── FINAL_SUMMARY_RU.md ← full summary in Russian
│   ├── COMPLETE_PROJECT_REPORT.en.md ← exhaustive report
│   ├── GUI_AFFECTIVE_VISUALIZATION_REPORT.md ← the GUI in detail
│   ├── FILES_CHANGES_COMPLETE_LIST.md ← all changes
│   ├── IMPLEMENTATION_REPORT.md ← technical report
│   ├── CHANGES_SUMMARY.md ← list of changes
│   └── GUI_HABITS_IMPLEMENTATION.md ← archival documentation
│
├── src/ (source code)
│   │
│   ├── New files (affective regulators)
│   │   ├── affect.py ← principal module with AffectiveState
│   │   └── self_model.py ← module for introspection
│   │
│   ├── Modified files (integration)
│   │   ├── agent.py ← affect_state added, step() improved
│   │   ├── selector.py ← support for affect_modifier
│   │   ├── intent_memory.py ← methods reevaluate/consolidate
│   │   ├── action_realizer.py ← modulation by affect
│   │   └── gui.py ← principal change: GUI visualisation
│   │
│   └── Remaining components (unchanged)
│       ├── cortex.py
│       ├── hippocampus.py
│       ├── intent_memory.py (reworked)
│       ├── trainer.py
│       ├── experience.py
│       ├── storage.py
│       └── ...and others
│
├── tests/ (testing)
│   │
│   ├── New tests (affective system)
│   │   ├── test_affective_regulators.py (25 tests)
│   │   ├── test_affect_integration.py (12 tests)
│   │   └── conftest.py ← pytest configuration
│   │
│   ├── Updated tests
│   │   └── test_intent_memory.py ← methods updated
│   │
│   └── Remaining tests (unchanged)
│       ├── test_agent.py
│       ├── test_selector.py
│       ├── test_hippocampus.py
│       └── ...and others
│
├── datasets/ (data)
│   ├── habits.json
│   ├── realizations_*.json
│   └── test.json
│
├── saves/ (saves)
│
├── Docs/ (archival documentation)
│
└── test_gui_affective.py ← GUI tests at the top level

═══════════════════════════════════════════════════════════════════════

```

## Project statistics

```
CODE STATISTICS:
─────────────────────────────
New lines:                1,500+
├── Modules:               550
├── Tests:                 600
└── Documentation:      150+ pages

TESTS:
─────────────────────────────
Tests in total:            37
Passed:                    37 (100%)
Errors:                     0
Regressions:                0

FILES:
─────────────────────────────
New:                         5
Modified:                    6
Documents:                   6
Touched in total:           17

DOCUMENTATION:
─────────────────────────────
Pages:                    20+
Words:                 30,000+
Examples:                 15+
Diagrams:                 10+
```

## Where to look

### For beginning users
1. `PROJECT_COMPLETION_CONFIRMATION.md` — what was done
2. `QUICK_START_RU.md` — how to use it
3. Run: `python src/gui.py`

### For developers
1. `COMPLETE_PROJECT_REPORT.en.md` — the full technical architecture
2. `FILES_CHANGES_COMPLETE_LIST.md` — a detailed list of changes
3. `GUI_AFFECTIVE_VISUALIZATION_REPORT.md` — GUI details
4. Code: `src/affect.py`, `src/self_model.py`

### For analysis
1. `FINAL_SUMMARY_RU.md` — the full summary
2. `IMPLEMENTATION_REPORT.md` — the implementation
3. `CHANGES_SUMMARY.md` — the history of changes

## Quick commands

```bash
# Запуск GUI с визуализацией
python src/gui.py

# Запуск всех тестов (37/37 PASSED ✅)
pytest tests/test_affective_regulators.py tests/test_affect_integration.py -v

# Запуск только GUI тестов
pytest test_gui_affective.py -v

# Запуск одного теста
pytest tests/test_affective_regulators.py::TestAffectiveState::test_affective_state_initialization -v
```

## GUI components (new)

```
GUI Window (1200x750)
│
├── Left panel: chat
│   ├── Message history
│   ├── Input field
│   └── Send button
│
├── Right panel: analysis
│   │
│   ├── New: affective state
│   │   ├── Valence       [████░░░░░░] 0.24
│   │   ├── Arousal       [██░░░░░░░░] 0.60
│   │   ├── Threat        [████░░░░░░] 0.36
│   │   ├── Curiosity     [██░░░░░░░░] 0.23
│   │   └── Readiness:    0.50 (Processing)
│   │
│   ├── Statistics
│   │   ├── Experience
│   │   ├── Habits
│   │   └── Tests
│   │
│   ├── Feedback
│   │   ├── Rating slider
│   │   └── Save button
│   │
│   ├── Memory
│   │   └── View and edit
│   │
│   ├── Sleep
│   │   └── Memory consolidation
│   │
│   ├── Affective state (inspector)
│   │   ├── Current state
│   │   ├── Limiting factors
│   │   ├── Supporting factors
│   │   └── Pattern analysis
│   │
│   └── Inspector (other tabs)
```

## Colour scheme of the indicators

```
Valence:
negative pole ──────────→ positive pole
-1.0           +1.0
Sad            Happy

Arousal:
low ──────────→ high
0.0            2.0
Calm           Hyperactive

Threat:
low ──────────→ high
0.0            1.0
Safe           Critical

Curiosity:
low ──────────→ high
0.0            1.0
Indifferent    Exploring
```

## Process of use

```
1. THE USER WRITES A MESSAGE
   │
   ↓
2. THE AGENT PROCESSES IT
   ├── Generates a reply
   ├── Computes signals (reward/novelty/conflict)
   └── Updates affect_state
   │
   ↓
3. THE GUI UPDATES
   ├── Colours the indicators
   ├── Updates the values
   ├── Shows readiness status
   └── Updates the inspector
   │
   ↓
4. THE USER SEES THE RESULT
   ├── Colours change in real time
   ├── Numbers are updated
   ├── The analysis shows factors
   └── The reply can be rated
   │
   ↓
5. THE USER RATES THE REPLY (-2 to +2)
   │
   ↓
6. VALENCE IS UPDATED
   ├── It reflects the rating
   ├── Readiness may change
   └── The process repeats
```

## Installation check

### Confirm that every file is present:

```python
# Проверка импортов
from src.affect import AffectiveState          # ✅ Должен работать
from src.self_model import SelfModel           # ✅ Должен работать
from src.agent import Agent                    # ✅ Должен работать

# Проверка тестов
pytest tests/test_affective_regulators.py      # ✅ Должно быть 25/25
pytest tests/test_affect_integration.py        # ✅ Должно быть 12/12

# Проверка GUI
python src/gui.py                              # ✅ GUI должен запуститься
```

## If something does not work

```
1. Import error?
   → Check that src/ is on the Python path
   → pytest uses conftest.py automatically

2. The GUI does not start?
   → Check that tkinter is installed
   → Run from the project root

3. Tests do not pass?
   → Delete .pytest_cache/
   → Reinstall packages: pip install -r requirements.txt

4. Indicators do not update?
   → Check the console for errors
   → Confirm that Send was pressed
```

## Documentation hierarchy

```
LEVEL 1: Overview (5 minutes)
├── PROJECT_COMPLETION_CONFIRMATION.md
└── QUICK_START_RU.md

LEVEL 2: Use (30 minutes)
├── FINAL_SUMMARY_RU.md
└── GUI_AFFECTIVE_VISUALIZATION_REPORT.md

LEVEL 3: Development (2 hours)
├── COMPLETE_PROJECT_REPORT.en.md
├── FILES_CHANGES_COMPLETE_LIST.md
└── IMPLEMENTATION_REPORT.md

LEVEL 4: Source code
├── src/affect.py
├── src/self_model.py
├── src/gui.py (modified)
└── tests/*.py
```

## Key concepts

### AffectiveState (affect.py)
- 4 parameters: valence, arousal, threat, curiosity
- Automatic management of bounds
- Natural decay
- Update methods for various stimuli

### SelfModel (self_model.py)
- Operational introspection
- Without anthropomorphism
- Analysis of limiting and supporting factors
- Computation of readiness to learn

### GUI visualisation
- Indicators based on a canvas
- Colour coding
- Updates in real time
- An inspector for analysis

---

**Last update:** 20 January 2025
**Version:** 1.0 Production Ready
**Status:** complete
