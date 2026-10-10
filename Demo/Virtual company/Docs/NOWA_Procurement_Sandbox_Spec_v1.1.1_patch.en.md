## Abstract

Russian version: [NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.ru.md](NOWA_Procurement_Sandbox_Spec_v1.1.1_patch.ru.md)

Patch v1.1.1 closes a gap measured on a twenty-quarter Stage 1b run against the seed-1 baseline: `cost_efficiency` = 0.7523, `stockout_avoidance` = 0.9493, `budget_discipline` = 1.0, `reaction_to_risk_events` = 0.7894. Stockout avoidance regresses in all twenty quarters. The floor is 0.9493 × 0.9 = 0.854. By the end of the series the values fall into the interval 0.000–0.023 in quarters 41, 42, 44, and 47. Meanwhile `all_passed` is true in eight of the twenty quarters — 31, 32, 34, 36, 41, 42, 45, and 48 — and in every one of them stockout avoidance lies below the floor. With `stop_on_graduation=True` training would have stopped at quarter 31, although total stockout in neighbouring quarters reaches 4,621–6,002 units. The longest consecutive run of `all_passed` is two quarters. In the v1.1 implementation the graduation report and the non-regression check are both computed correctly and do not affect each other.

For Stage 1b a quarter enters the graduation streak only when the gating criteria pass and the `non_regression` map contains no false value. Graduation occurs after `GRADUATION_MIN_STREAK` = 3 such quarters in a row. The field `graduated_at_quarter` points at the first quarter of the streak, that is, at the onset of sustained competence. The streak is a pure function of the quarters already stored in `result.quarters`, so resuming from a checkpoint does not reset it. Stage 1a is unchanged: when there is no baseline, `non_regression` is `None`, and a single `all_passed` suffices. The patch does not rewrite `graduation_report` or `_non_regression_for` themselves.

The second change aligns the strictness of baseline loading with the strictness of the report-writing command. If `load_baseline` receives a raw result list and no quarter has graduated, the function refuses to build a floor and raises an error. `compute_stage_1a_baseline` remains permissive for the diagnostic table, including a fallback over all quarters; strictness is added only at the boundary where the number enters the non-regression guard. An already written curated file with a `stage_1a_baseline` key is read as before. Re-running the same trial after the patch must leave `result.graduated` false across all twenty quarters shown.

---

# NOWA Procurement Sandbox — Patch v1.1.1

**Base documents:**
NOWA_Procurement_Sandbox_Spec.md (v1.0)
NOWA_Procurement_Sandbox_Spec_v1.1_patch.en.md (Stage 1a/1b curriculum)

**Status:** Ready for implementation — a critical fix on top of the already implemented and working v1.1 code

---

## Empirical basis (not a hypothesis — a recorded fact)

A Stage 1b run (20 quarters, `stage_1a_baseline` from seed1:
`cost_efficiency=0.7523, stockout_avoidance=0.9493, budget_discipline=1.0,
reaction_to_risk_events=0.7894`) showed:

**`stockout_avoidance` regresses in 20 of 20 consecutive Stage 1b quarters,
with not a single exception.** Floor = 0.9493 × 0.9 = 0.854. By the end of the run
the values fall to 0.000–0.023 (quarters 41, 42, 44, 47) — the agent
has in effect ceased to manage stock.

**Meanwhile `all_passed: true` fires in 8 of 20 quarters** (31, 32,
34, 36, 41, 42, 45, 48) — **in each of these eight** `stockout_avoidance`
is simultaneously regressed below the floor.

With the default `stop_on_graduation=True`, training would have stopped at
**quarter 31** with a formal `"GRADUATED"`, although `total_stockout_units`
in neighbouring quarters reaches 4,621–6,002 units. The streak check (≥3
in a row, section 26.7) protects in part — the longest sequence of
`all_passed=true` in this run is 2 (Q31–32, Q41–42) — but it does not solve
the problem completely if the streak is not bound explicitly to non-regression.

Conclusion: `graduation_report()` and `check_non_regression()` in the v1.1 implementation
are both computed correctly and independently, but **do not affect each other**.
`result.graduated` in `run_quarters` / `run_stage1b_persistent` looks
only at `graduation.get("all_passed")`.

---

## Files affected

| File | Kind of change |
|---|---|
| `training_loop.py` | The condition `result.graduated` for stage="1b" must require non-regression on the streak, not only `all_passed` on a single quarter |
| `stage_baseline.py::load_baseline` | Bring it to the strictness of `stage1a_report.py::pick_baseline_run` — refuse a baseline built from quarters that did not pass, unless there is an explicit override |
| `tests/` | A regression test on the exact scenario of this run (see the section "Test cases") |

---

## Change 1: `training_loop.py` — graduation requires sustained non-regression

### Current behaviour (v1.1)

```python
# In run_quarters(), after each quarter:
if graduation.get("all_passed") and not result.graduated:
    result.graduated = True
    result.graduated_at_quarter = q_idx
    if stop_on_graduation:
        break
```

This condition does not take into account `non_regression`, computed in the same cycle
through `self._non_regression_for(fitness)` and stored in
`QuarterResult.non_regression` — but not used for the graduation decision.

### Required behaviour

For `stage == "1a"` the behaviour does not change — there `non_regression` is always
`None` (there is no baseline, and nothing to check), and the `all_passed` logic remains
the only condition.

For `stage == "1b"` graduation must require:
1. `graduation.get("all_passed")` — as before
2. **And** `non_regression` contains no `False` for any criterion
   (or `non_regression is None` if `stage_1a_baseline` was not passed —
   this is already covered by the existing warning `--stage 1b requires
   --baseline-from`)
3. **And** this holds **across `min_streak` consecutive
   quarters** (section 26.7: `min_streak=3` by default), not on a single quarter

```python
GRADUATION_MIN_STREAK = 3
"""Section 26.7: Stage 1b graduation must hold for this many consecutive
quarters, not trigger on the first lucky pass."""


def _quarter_qualifies(quarter: "QuarterResult") -> bool:
    """A quarter counts toward the graduation streak only if it passed
    AND did not buy that pass by regressing Stage 1a competence.

    For Stage 1a runs, non_regression is always None (no baseline to
    check against), so the check is a no-op and only all_passed matters —
    this keeps existing Stage 1a behaviour unchanged.
    """
    if not quarter.graduation.get("all_passed"):
        return False
    if quarter.non_regression is None:
        return True
    return not any(
        ok is False for ok in quarter.non_regression.values()
    )


# In run_quarters(), replace the graduation-detection block:
qualifying_streak = 0
for offset in range(...):
    # ... existing per-quarter computation, including non_regression ...

    quarter_result = QuarterResult(..., non_regression=self._non_regression_for(fitness))
    result.quarters.append(quarter_result)

    if _quarter_qualifies(quarter_result):
        qualifying_streak += 1
    else:
        qualifying_streak = 0

    if qualifying_streak >= GRADUATION_MIN_STREAK and not result.graduated:
        result.graduated = True
        # Graduated at the FIRST quarter of the qualifying streak, not the
        # last — this is when sustained competence actually began, and
        # matches how a resumed run should report it.
        result.graduated_at_quarter = quarter_result.quarter_index - GRADUATION_MIN_STREAK + 1
        if stop_on_graduation:
            break
```

### Important clarification: `qualifying_streak` must survive resume

If training is interrupted by a checkpoint in the middle of streak accumulation, the streak
must not be reset on `--resume-from`. `qualifying_streak` must be computed
**from the history `result.quarters`**, and not stored as
a separate field of the trainer — then resume is automatically correct:

```python
def _current_qualifying_streak(quarters: List["QuarterResult"]) -> int:
    """Recompute the streak from history instead of tracking it as
    mutable trainer state, so a checkpoint resume gets the right answer
    for free — the streak is a pure function of the quarters already run.
    """
    streak = 0
    for quarter in reversed(quarters):
        if _quarter_qualifies(quarter):
            streak += 1
        else:
            break
    return streak
```

Use `_current_qualifying_streak(result.quarters)` at the start
of every call to `run_quarters` / `run_stage1b_persistent`, instead of
an incremental counter.

### Do not change

- `_non_regression_for()` — it is computed correctly; do not touch it
- `graduation_report()` in `procurement_fitness.py` — `all_passed` there
  remains an honest answer to "did this particular quarter pass"; this is not the place
  for streak logic (the streak is a property of a sequence of quarters,
  not of a single quarter)
- Stage 1a logic — the change affects only the path `stage == "1b"`

---

## Change 2: `stage_baseline.py::load_baseline` — symmetric strictness

### The current asymmetry

`stage1a_report.py::pick_baseline_run` **refuses** to write a baseline
if there is not a single graduated run:

```python
if chosen is None:
    print("\nNo graduated run: refusing to write a baseline.")
    return 1
```

But `stage_baseline.py::load_baseline`, when it receives a raw list of
results (not a baseline file, but `results/stage1a_seedN.json` directly
via `--baseline-from`), silently calls `compute_stage_1a_baseline`,
which **itself** falls back to "all quarters" instead of only the successful ones, without
a refusal:

```python
def compute_stage_1a_baseline(quarters, last_n=BASELINE_QUARTERS):
    good = successful_quarters(quarters)
    from_successful = bool(good)
    selected = (good or quarters)[-max(1, int(last_n)):]  # <- silent fallback
```

An operator can accidentally pass to `--baseline-from` a run in which the
Stage 1a agent never graduated at all, and obtain a baseline computed over
failed quarters — the non-regression guard in Stage 1b then protects
not "typical competence" but "the average performance
of an agent that did not pass the course", which is meaningless.

### Required behaviour

`load_baseline`, when it builds a baseline from a raw result list
(`isinstance(data, list)` — the path without an explicit `stage_1a_baseline` key),
must require `from_successful_quarters=True`; otherwise it must raise an explicit
error, rather than degrade silently:

```python
def load_baseline(path: str) -> Dict[str, float]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if isinstance(data, list):
        payload = compute_stage_1a_baseline(data)
        if not payload["from_successful_quarters"]:
            raise ValueError(
                f"{path} contains no graduated Stage 1a quarters. "
                f"Refusing to build a non-regression baseline from failed "
                f"quarters — this would guard Stage 1b against nothing. "
                f"Run more Stage 1a quarters, or use "
                f"stage1a_report.py --write-baseline on a run that "
                f"actually graduated."
            )
        return dict(payload["stage_1a_baseline"])

    # ... existing mapping-based path unchanged ...
```

### Do not change

- `compute_stage_1a_baseline()` itself — its signature and fallback
  behaviour remain as they are, because `stage1a_report.py::summarize_run`
  legitimately uses it for the diagnostic table (section 27.2),
  where showing "a baseline even from an unsuccessful run" is a meaningful
  diagnostic, not a final decision. Strictness is required only at the boundary
  `load_baseline`, where the result goes directly into `check_non_regression`.

---

## Test cases

### `tests/test_graduation_non_regression.py` (new file)

```python
"""Regression test built directly from the v1.1 run that exposed the gap:
Stage 1b graduated on quarter 31 while stockout_avoidance was regressed
in every one of the 20 Stage 1b quarters observed."""

import pytest
from nowa_sandbox.training_loop import (
    QuarterResult, SandboxTrainingResult,
    GRADUATION_MIN_STREAK, _quarter_qualifies, _current_qualifying_streak,
)


def _fake_quarter(index, all_passed, non_regression=None):
    from nowa_sandbox.procurement_fitness import ProcurementFitnessVector
    vector = ProcurementFitnessVector(
        cost_efficiency=0.5, stockout_avoidance=0.5, budget_discipline=1.0,
        supplier_diversification=0.5, decision_consistency=0.5,
        reaction_to_risk_events=0.5, n_days=90, n_orders=90,
    )
    return QuarterResult(
        quarter_index=index,
        fitness=vector,
        graduation={"all_passed": all_passed, "stage": "1b"},
        world_summary={},
        processing_time_s=0.0,
        non_regression=non_regression,
    )


class TestQuarterQualifies:

    def test_fails_all_passed_disqualifies(self):
        q = _fake_quarter(1, all_passed=False, non_regression={"stockout_avoidance": True})
        assert _quarter_qualifies(q) is False

    def test_regressed_criterion_disqualifies_even_if_all_passed(self):
        """The exact bug: all_passed=True but stockout_avoidance regressed."""
        q = _fake_quarter(
            31, all_passed=True,
            non_regression={
                "cost_efficiency": False, "stockout_avoidance": False,
                "budget_discipline": True, "reaction_to_risk_events": True,
            },
        )
        assert _quarter_qualifies(q) is False

    def test_all_passed_with_clean_non_regression_qualifies(self):
        q = _fake_quarter(
            1, all_passed=True,
            non_regression={
                "cost_efficiency": True, "stockout_avoidance": True,
                "budget_discipline": True, "reaction_to_risk_events": True,
            },
        )
        assert _quarter_qualifies(q) is True

    def test_stage_1a_none_non_regression_qualifies_on_all_passed_alone(self):
        """Stage 1a has no baseline to check; non_regression is None by
        design and must not block graduation there."""
        q = _fake_quarter(1, all_passed=True, non_regression=None)
        assert _quarter_qualifies(q) is True


class TestQualifyingStreak:

    def test_streak_resets_on_disqualifying_quarter(self):
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": True}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
            _fake_quarter(3, True, {"stockout_avoidance": False}),  # regressed
        ]
        assert _current_qualifying_streak(quarters) == 0

    def test_streak_counts_trailing_run_only(self):
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": False}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
            _fake_quarter(3, True, {"stockout_avoidance": True}),
        ]
        assert _current_qualifying_streak(quarters) == 2

    def test_reproduces_actual_run_never_reaches_min_streak(self):
        """Sequence taken from the real Stage 1b run (quarters 31-50):
        all_passed pattern is T T F T F F T T F T T T F F T F F T F F,
        with stockout_avoidance regressed in all 20. Max observed streak
        under the old (broken) rule was 2 quarters (Q31-32, Q41-42) —
        under the fix, since every quarter has stockout_avoidance
        regressed, the qualifying streak must never exceed 0.
        """
        all_passed_pattern = [
            True, True, False, True, False, False, True, True, False,
            True, True, True, False, False, True, False, False, True,
            False, False,
        ]
        quarters = [
            _fake_quarter(
                31 + i, all_passed,
                {"cost_efficiency": True, "stockout_avoidance": False,
                 "budget_discipline": True, "reaction_to_risk_events": True},
            )
            for i, all_passed in enumerate(all_passed_pattern)
        ]
        assert _current_qualifying_streak(quarters) == 0


class TestGraduationRequiresStreak:

    def test_single_qualifying_quarter_does_not_graduate(self, mini_world_config):
        """One good quarter is not enough — GRADUATION_MIN_STREAK requires
        several in a row, per section 26.7."""
        # Built via a trainer double whose fitness_evaluator always returns
        # a passing, non-regressed vector for exactly one quarter and then
        # a regressed one — asserts result.graduated stays False after
        # quarter 1 and result.graduated_at_quarter is None.
        ...

    def test_sustained_streak_graduates_at_streak_start(self):
        """When GRADUATION_MIN_STREAK consecutive quarters all qualify,
        graduated_at_quarter should be the FIRST quarter of that streak,
        not the last — this is when sustained competence began."""
        ...


class TestResumePreservesStreak:

    def test_streak_recomputed_from_history_not_reset_on_resume(self):
        """A checkpoint saved mid-streak, then resumed, must not lose
        credit for quarters already run — streak is a pure function of
        result.quarters, never trainer-local mutable state."""
        quarters = [
            _fake_quarter(1, True, {"stockout_avoidance": True}),
            _fake_quarter(2, True, {"stockout_avoidance": True}),
        ]
        result = SandboxTrainingResult(quarters=quarters)
        assert _current_qualifying_streak(result.quarters) == 2
        # A subsequent qualifying quarter must bring the streak to 3 and
        # trigger graduation, exactly as if the run had never stopped.
```

### `tests/test_stage_baseline_strictness.py` (new file)

```python
"""load_baseline must be as strict as stage1a_report.py's
--write-baseline: refuse rather than silently build a guard from
non-graduated quarters."""

import json
import pytest
from nowa_sandbox.stage_baseline import load_baseline


def test_refuses_baseline_from_all_failed_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": i,
            "fitness": {
                "cost_efficiency": 0.3, "stockout_avoidance": 0.1,
                "budget_discipline": 1.0, "reaction_to_risk_events": 0.2,
            },
            "graduation": {"all_passed": False},
        }
        for i in range(1, 6)
    ]
    path = tmp_path / "all_failed.json"
    path.write_text(json.dumps(quarters))

    with pytest.raises(ValueError, match="no graduated Stage 1a quarters"):
        load_baseline(str(path))


def test_accepts_baseline_from_graduated_quarters(tmp_path):
    quarters = [
        {
            "quarter_index": 1,
            "fitness": {
                "cost_efficiency": 0.8, "stockout_avoidance": 0.9,
                "budget_discipline": 1.0, "reaction_to_risk_events": 0.7,
            },
            "graduation": {"all_passed": True},
        }
    ]
    path = tmp_path / "graduated.json"
    path.write_text(json.dumps(quarters))

    baseline = load_baseline(str(path))
    assert baseline["cost_efficiency"] == 0.8


def test_curated_baseline_file_unaffected(tmp_path):
    """The mapping-based path (a file already produced by
    stage1a_report.py --write-baseline) must keep working unchanged."""
    payload = {
        "stage_1a_baseline": {
            "cost_efficiency": 0.7523, "stockout_avoidance": 0.9493,
            "budget_discipline": 1.0, "reaction_to_risk_events": 0.7894,
        },
        "computed_from_quarters": [6, 9, 19, 23, 26],
        "from_successful_quarters": True,
    }
    path = tmp_path / "curated.json"
    path.write_text(json.dumps(payload))

    baseline = load_baseline(str(path))
    assert baseline["stockout_avoidance"] == 0.9493
```

---

## Constraints (not to be circumvented)

| # | Constraint |
|---|---|
| **NR1** | Stage 1a graduation logic **is not changed** by this patch — `non_regression is None` there always, and `_quarter_qualifies` for Stage 1a is equivalent to the old `graduation.get("all_passed")` |
| **NR2** | `qualifying_streak` is computed from `result.quarters` (a pure function); it is not stored as mutable trainer state — otherwise resume after a checkpoint breaks the count |
| **NR3** | `graduated_at_quarter` points at the **first** quarter of the streak, not the last — this is the moment at which sustained competence began |
| **NR4** | The strictness of `load_baseline` applies **only** to the path "raw result list"; curated baseline files (already passed through `stage1a_report.py --write-baseline`) are not affected |
| **NR5** | `compute_stage_1a_baseline()` as a function remains permissive (for the diagnostic of section 27.2) — strictness is added only at the `load_baseline` boundary |

---

## Check after implementation

Re-run exactly the same Stage 1b scenario (the same `stage_1a_baseline`,
the same seed) and confirm:

- [ ] `result.graduated` remains `False` across all 20 quarters shown
      (the streak never reaches 3 while `stockout_avoidance`
      is regressed in every quarter)
- [ ] The log explicitly shows `qualifying_streak` after every quarter —
      useful for debugging, not only for the final decision
- [ ] `test_reproduces_actual_run_never_reaches_min_streak` is green
- [ ] An attempt `--baseline-from results/stage1a_seed_never_graduated.json`
      (a hypothetical run in which Stage 1a passed no quarter)
      ends with an explicit error, not with the silent construction of a useless baseline

---

*Patch v1.1.1. Justified empirically by the data of a real run.
Ready to be handed to the implementing agent.*
