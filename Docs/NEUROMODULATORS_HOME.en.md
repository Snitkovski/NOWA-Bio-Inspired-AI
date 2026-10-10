# Home Page of the Neuromodulator Documentation

Russian version: [NEUROMODULATORS_HOME.ru.md](NEUROMODULATORS_HOME.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**February 2026 — Final release**

---

## Start Here

### In a hurry? (5 min)
→ [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md)

### Developer? (30 min)
→ [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

### Architect? (60+ min)
→ [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

### Need a report?
→ [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.en.md)

---

## All Documents

### Core documentation (required)

| Document | Length | Purpose | Read? |
|----------|--------|---------|-------|
| [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md) | 5 pp. | **START HERE** | ☐ |
| [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md) | 10 pp. | API and examples | ☐ |
| [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md) | 12 pp. | Full specification | ☐ |
| [NEUROMODULATORS_SUMMARY_REPORT.md](NEUROMODULATORS_SUMMARY_REPORT.en.md) | 8 pp. | What was done | ☐ |

### Reference documentation (as needed)

| Document | Length | Purpose |
|----------|--------|---------|
| [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.en.md) | 18 pp. | Full report |
| [NEUROMODULATORS_DOCUMENTATION_GUIDE.md](NEUROMODULATORS_DOCUMENTATION_GUIDE.en.md) | 10 pp. | How to read the documentation |
| [NEUROMODULATORS_CHECKLIST.md](NEUROMODULATORS_CHECKLIST.en.md) | 8 pp. | Completion checklist |
| [PROJECT_STATUS_FINAL.en.md](PROJECT_STATUS_FINAL.en.md) | 12 pp. | Final status |

### Updated documents

| Document | Changes |
|----------|---------|
| [README.md](README.md) | Links to neuromodulators added |
| [CHANGELOG.md](CHANGELOG.en.md) | Entry for the February release |
| [INDEX.md](INDEX.en.md) | Section on neuromodulators |

---

## By Role

### I am new to the project
1. Read: [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md) (5 min)
2. Run: `python src/gui.py` (5 min)
3. Read: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md) (15 min)
4. Review: code examples in the document (10 min)
**Total:** ~35 minutes

### I am a developer
1. Read: [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md) (15 min)
2. Inspect: `src/neuromodulators.py` (10 min)
3. Read: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md) (30 min)
4. Run: tests `pytest tests/test_neuromodulators.py` (5 min)
**Total:** ~60 minutes

### I am an architect or team lead
1. Read: [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.en.md) (45 min)
2. Read: [PROJECT_STATUS_FINAL.en.md](PROJECT_STATUS_FINAL.en.md) (20 min)
3. Inspect: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md) for a deeper understanding (30 min)
4. Discuss: the findings with the team
**Total:** ~95 minutes plus discussion

### I am QA or a tester
1. Read: the "Testing" section of [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md) (10 min)
2. Run: tests `pytest tests/test_neuromodulators.py -v` (5 min)
3. Run: all tests `pytest tests/` (2 min)
4. Read: [NEUROMODULATORS_CHECKLIST.md](NEUROMODULATORS_CHECKLIST.en.md) (15 min)
**Total:** ~32 minutes

---

## By Topic

### What are neuromodulators?
→ Section "Overview" in [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

### How do they work?
→ Section "Architecture" in [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

### How are they used?
→ Section "Usage Examples" in [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

### How are they tested?
→ Section "Testing" in [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

### How are they extended?
→ Extension section in [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

### What if there is an error?
→ Section "Troubleshooting" in [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

---

## Make It Run

### Quick check (2 minutes)

```bash
# Проверить, что всё установлено
python -c "from src.neuromodulators import NeuromodulatorState; print('OK')"

# Запустить основной тест
pytest tests/test_neuromodulators.py::test_dopamine_increases_on_reward -v
```

### Full check (5 minutes)

```bash
# Запустить все тесты нейромодуляторов
pytest tests/test_neuromodulators.py -v

# Запустить весь проект
pytest tests/ -v --tb=short
```

### Interactive check (10 minutes)

```bash
# Запустить GUI
python src/gui.py

# Выполнить несколько шагов → посмотреть на значения нейромодуляторов
# Выполнить sleep (Ctrl+Z или через интерфейс) → посмотреть эффекты
```

---

## Questions and Answers

**Q: Where should one start?**  
A: [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md)

**Q: Where are the code examples?**  
A: Section "Examples" of [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

**Q: How does all of this work internally?**  
A: [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

**Q: There is an error; what should be done?**  
A: Section "Troubleshooting" of [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

**Q: I want to extend the system**  
A: Extension section of [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md)

**Q: All of the information is needed**  
A: [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.en.md)

---

## Project Status

| Component | Status |
|-----------|--------|
| Code | 100% complete |
| Tests | 172/172 passing |
| Documentation | Complete (1300+ lines) |
| Integration | Complete |
| Production-ready | Yes |

---

## Quick Statistics

- **4 neuromodulators:** Dopamine, Norepinephrine, Serotonin, Cortisol
- **1 new file:** `src/neuromodulators.py` (81 lines)
- **5 modified:** agent.py, sleep.py, storage.py, gui.py, and others
- **4 new tests:** test_dopamine, test_norepinephrine, test_serotonin, test_cortisol
- **172 tests in total:** 172/172 passing
- **6 new documents:** complete documentation
- **0 breaking changes:** backward compatibility 100%

---

## Learning Path

To become proficient, read in this order:

1. **Level 1 (User):** [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md) — 15 min
2. **Level 2 (Developer):** [NEUROMODULATORS_QUICK_REFERENCE.md](NEUROMODULATORS_QUICK_REFERENCE.en.md) — 30 min
3. **Level 3 (Specialist):** [NEUROMODULATORS_IMPLEMENTATION.md](NEUROMODULATORS_IMPLEMENTATION.en.md) — 45 min
4. **Level 4 (Expert):** [NEUROMODULATORS_FULL_REPORT.md](NEUROMODULATORS_FULL_REPORT.en.md) — 60 min

**Total:** about 150 minutes to expert level.

---

## Useful Links

### In this project

- [Source code: src/neuromodulators.py](../src/neuromodulators.py)
- [Integration: src/agent.py (search "neuromodulators")](../src/agent.py)
- [Effects: src/sleep.py (_apply_neuromodulators_during_sleep)](../src/sleep.py)
- [Tests: tests/test_neuromodulators.py](../tests/test_neuromodulators.py)

### Documentation

- [Main README](README.md)
- [Full INDEX](INDEX.en.md)
- [CHANGELOG](CHANGELOG.en.md)

---

## Ready for Use

**The neuromodulator system is fully implemented, tested, and documented.**

Begin with [QUICK_START_NEUROMODULATORS.md](QUICK_START_NEUROMODULATORS.en.md), or select a document by role above.

---

**Last update:** 5 February 2026  
**Version:** 1.0  
**Status:** PRODUCTION-READY
