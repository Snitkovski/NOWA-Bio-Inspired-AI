## Abstract

Russian version: [NOWA_Procurement_Sandbox_Spec_v1.1_patch.ru.md](NOWA_Procurement_Sandbox_Spec_v1.1_patch.ru.md)

Patch v1.1 answers a recorded thirty-quarter run in which `all_passed` occurred only in quarters 17 and 19. The criteria `decision_consistency` and `supplier_diversification` count choices by the string `supplier_id`, whereas `ProcurementWorld` redraws reliability, price multiplier, and lead time under the same identifiers every quarter. The agent's hippocampus is retained across quarters, so what was learned about a supplier in quarter N points in quarter N+1 at a different random entity. The observed symptom is that `supplier_diversification` takes the value 0.1333… for five consecutive quarters, in step with `decision_consistency` approaching 1.0.

The curriculum is divided into two stages of one contour, rather than into two worlds. Stage 1a keeps rotating suppliers and graduates the agent on four criteria that do not depend on a stable identifier: cost efficiency, stockout avoidance, budget discipline, and reaction to risk events. Stage 1b carries supplier attributes across quarters by `export_supplier_state` and `carry_supplier_state`, resetting only the default flag, and graduates on decision consistency and diversification. The four Stage 1a criteria remain in the report; the `check_non_regression` floor is 0.9 of the Stage 1a baseline, taken as the means of the last successful quarters. Budget is not carried between Stage 1b quarters in the first implementation. Alternating persistent and disposable worlds is deferred until both stages have been confirmed separately.

The execution order is mandatory. The already collected `results/sandbox_run_001.json` is first re-scored with the Stage 1a formula without a new simulation; five independent Stage 1a runs follow; the baseline is then fixed; only after that is the persistent-supplier code written. Stage 1a readiness requires graduation in at least three of five seeds, with the spread in quarters-to-graduation no greater than ±50%. Stage 1b readiness requires graduation held for at least three consecutive quarters, a cleared floor in every such quarter, and success in at least two of five independent Stage 1b runs against the same baseline.

---

# NOWA Procurement Sandbox — Patch v1.1

**Base document:** NOWA_Procurement_Sandbox_Spec.md (v1.0, sections 1–25)
**Status:** Ready for implementation — a point change on top of code that is
already implemented and tested
**Context:** The first real run (30 quarters, one agent,
`results/sandbox_run_001.json`) revealed a structural problem: two of the
six fitness criteria (`decision_consistency`, `supplier_diversification`)
measure the constancy of particular `supplier_id` values across quarters, but the
physics of the world (`ProcurementWorld`) recreates supplier attributes under the same IDs
every quarter. Graduation therefore fires only by chance (2 of 30
quarters), not stably.

**What to change:** only the modules listed in the section "Affected files"
below. All other v1.0 code (tick physics in `procurement_world.py`,
`sandbox_encoder.py`, `sandbox_agent_factory.py`, `sandbox_checkpoint.py`,
`sandbox_config.py`, `sandbox_observer.py`) remains unchanged in this
revision.

---

## Affected files

| File | Kind of change |
|---|---|
| `procurement_fitness.py` | Add a `stage` parameter, split criteria into gating/monitored, add `check_non_regression` |
| `procurement_world.py` | Add `persistent_suppliers` to the config, and the methods `export_supplier_state`/`carry_supplier_state` |
| `training_loop.py` | Add the method `run_stage1b_persistent` |
| `run_sandbox.py` | Add the CLI flags `--stage`, `--baseline-from` |
| `tests/` | New test files for staged graduation, persistent suppliers, and the non-regression guard |

---

## Mandatory execution order (do not violate)

This is a process requirement as well as an architectural one. The steps are strictly
sequential and are not to be parallelised:

1. **Step 27.1** — recompute graduation on the data already collected in
   `results/sandbox_run_001.json` with the new 4-criterion Stage 1a formula,
   WITHOUT a repeated simulation (script below). This confirms the diagnosis
   quantitatively in seconds, before any code is changed.
2. **Step 27.2** — only if the diagnosis is confirmed: apply the changes to
   `procurement_fitness.py` and run 5 independent Stage 1a runs
   with different `--seed` values.
3. **Step 27.3** — fix `stage_1a_baseline` from the best or median
   run.
4. **Step 27.4** — only after 27.3: implement `persistent_suppliers`
   (`procurement_world.py`, `training_loop.py`) and Stage 1b.

**Do not write Stage 1b code in parallel with collecting the 5-seed Stage 1a sweep.**

---

## 26. Revision v1.1 — two-stage curriculum (Stage 1a / Stage 1b)

### 26.1 Diagnosis that led to this revision

The first real run (30 quarters, one agent) yielded `all_passed=true`
only in quarters 17 and 19: not stable graduation, but a chance hit
in a narrow window. Analysis of the cause:

`ProcurementWorld._init_suppliers()` recreates suppliers **every
quarter** with new random `reliability`/`base_price_multiplier`/
`lead_time_days`, while keeping the previous `supplier_id` values (`supplier_000` and
so on). The agent's hippocampus is not reset between quarters (constraint V1
permits this). Consequently, what was learned in quarter N, that "supplier_002
is reliable", points in quarter N+1 at a different random entity under the
same label. The agent either relearns from scratch every quarter or
sticks to one ID against the economic sense of the choice.

Observed symptom: `supplier_diversification` takes the exact value
`0.1333...` (a mathematical artefact of monopoly on a single supplier)
for five quarters in a row, in step with `decision_consistency → 1.0`.

### 26.2 Criteria classified by sensitivity to identity carry-over

| Criterion | Depends on constancy of `supplier_id` across periods? |
|---|---|
| `cost_efficiency` | No — compares the observed price with a statistical market band |
| `stockout_avoidance` | No — counts units of stockout |
| `budget_discipline` | No — takes the budget minimum over the period |
| `reaction_to_risk_events` | No — compares days of reaction, not the choice of counterparty |
| `decision_consistency` | **Yes** — a `Counter` over particular `supplier_id` values |
| `supplier_diversification` | **Yes** — the share of orders placed with the most frequent `supplier_id` |

Four criteria measure **general professional competence**
(recognising the signals "cheap/expensive" and "reliable/risky" from observed
attributes, rather than from identity). Two criteria measure **stability
of relations with particular counterparties that do not change**, and that is meaningful
only in a world where the counterparty truly does not change.

### 26.3 New model: two stages of one curriculum, not two different worlds

```
Stage 1a — "профшкола"           Stage 1b — "стажировка в фирме"
────────────────────────         ──────────────────────────────
Много независимых миров          Один персистентный мир
(текущее поведение,              (НОВЫЙ режим)
поставщики пересоздаются
каждый квартал)

Градация только по 4 критериям:  Градация только по 2 критериям:
  cost_efficiency                  decision_consistency
  stockout_avoidance                supplier_diversification
  budget_discipline               (плюс 4 предыдущих как
  reaction_to_risk_events          необходимый, но не
                                   достаточный минимум —
                                   не должны деградировать)

Цель: абстрактная стратегия,     Цель: устойчивая, но не
переносимая в cortex             монопольная связь с реальными
(не привязана к конкретным ID)   (для этого мира) партнёрами
```

**Mandatory sequencing condition:** Stage 1b is started only
after the agent has passed Stage 1a graduation. A mixed mode (alternating
persistent and disposable worlds in one run) is the subject of a future revision
v1.2, and is implemented only after Stage 1a and Stage 1b have each been
confirmed separately (section 26.7).

### 26.4 Changes in `procurement_fitness.py`

```python
# Новая константа: два набора критериев вместо одного монолитного

STAGE_1A_CRITERIA = [
    "cost_efficiency",
    "stockout_avoidance",
    "budget_discipline",
    "reaction_to_risk_events",
]

STAGE_1B_CRITERIA = [
    "decision_consistency",
    "supplier_diversification",
]

# PROCUREMENT_CRITERIA остаётся как объединение обоих — используется
# для полного диагностического вывода (JSON по-прежнему содержит все 6),
# но graduation_report получает параметр stage.


class ProcurementFitnessEvaluator:
    def __init__(
        self,
        thresholds: Optional[Mapping[str, float]] = None,
        stage: Literal["1a", "1b"] = "1a",
    ):
        self.stage = stage
        merged = dict(GRADUATION_THRESHOLDS)
        for criterion, value in dict(thresholds or {}).items():
            if criterion in merged:
                merged[criterion] = clamp(safe_float(value, merged[criterion]), 0.0, 1.0)
        self.thresholds = merged

    def graduation_report(self, vector: ProcurementFitnessVector) -> dict:
        """
        Все 6 критериев по-прежнему вычисляются и попадают в отчёт
        (полная прозрачность), но all_passed зависит ТОЛЬКО от критериев
        текущей stage. Критерии другой stage помечаются как
        "monitored" (не блокируют graduation, но видны в отчёте —
        не должны катастрофически деградировать, см. раздел 26.5).
        """
        active_criteria = (
            STAGE_1A_CRITERIA if self.stage == "1a" else STAGE_1B_CRITERIA
        )
        criteria_results: Dict[str, dict] = {}
        for criterion, threshold in self.thresholds.items():
            value = safe_float(getattr(vector, criterion, 0.0), 0.0)
            criteria_results[criterion] = {
                "value": round(value, 4),
                "threshold": threshold,
                "passed": value >= threshold,
                "gating": criterion in active_criteria,
            }

        gating_results = {
            k: v for k, v in criteria_results.items() if v["gating"]
        }
        report: Dict[str, Any] = dict(criteria_results)
        report["stage"] = self.stage
        report["all_passed"] = all(r["passed"] for r in gating_results.values())
        report["n_days"] = vector.n_days
        report["n_orders"] = vector.n_orders
        return report
```

### 26.5 Non-regression guard for criteria outside the current stage

Stage 1b must not permit the four Stage 1a criteria to degrade in order to
maximise `decision_consistency`/`supplier_diversification`. Otherwise the
agent would "build loyalty" by purchasing from a poor supplier at an inflated
price, which is not the objective.

```python
# Добавить в graduation_report:

NON_REGRESSION_FLOOR = 0.9  # доля от исходного Stage 1a порога

def check_non_regression(
    self, vector: ProcurementFitnessVector, stage_1a_baseline: Dict[str, float]
) -> Dict[str, bool]:
    """
    Вызывается только в Stage 1b. stage_1a_baseline — средние значения
    четырёх Stage 1a критериев за последние N кварталов Stage 1a
    (сохраняются в чекпоинте при переходе между стадиями).
    """
    result = {}
    for criterion in STAGE_1A_CRITERIA:
        current = safe_float(getattr(vector, criterion, 0.0), 0.0)
        baseline = stage_1a_baseline.get(criterion, 0.0)
        floor = baseline * NON_REGRESSION_FLOOR
        result[criterion] = current >= floor
    return result
```

### 26.6 Changes in `procurement_world.py` — persistent-world mode

New parameter in `ProcurementWorldConfig`:

```python
@dataclass
class ProcurementWorldConfig:
    # ... существующие поля без изменений ...
    persistent_suppliers: bool = False
    """
    False (по умолчанию, Stage 1a): supplier_id стабилен как строка,
    но VirtualSupplier-объект пересоздаётся с новыми случайными
    атрибутами при каждом ProcurementWorld.__init__.

    True (Stage 1b): при создании нового ProcurementWorld для следующего
    квартала атрибуты поставщиков (reliability, base_price_multiplier,
    lead_time_days, reputation, total_orders) переносятся из предыдущего
    квартала, а не генерируются заново. Только is_defaulted СБРАСЫВАЕТСЯ
    в False в начале нового квартала — иначе дефолт поставщика в
    Stage 1b был бы перманентным на весь прогон, что не даёт агенту
    возможности проверить восстановление доверия к ранее рискованному
    поставщику.
    """
```

New method `training_loop.py::SandboxTrainer`:

```python
def run_stage1b_persistent(
    self,
    n_quarters: int,
    world_config: ProcurementWorldConfig,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> SandboxTrainingResult:
    """
    Отличие от run_quarters(): поставщики (кроме is_defaulted) переносятся
    между кварталами через carry_supplier_state. Мир по-прежнему
    пересоздаётся каждый квартал (для сброса дней/pending_orders/budget
    resetting остаётся под вопросом — см. 26.6.1), но идентичность
    поставщиков сохраняется.
    """
    config = replace(world_config, persistent_suppliers=True)
    result = SandboxTrainingResult()
    carried_suppliers: Optional[Dict[str, VirtualSupplier]] = None

    for q_idx in range(1, n_quarters + 1):
        if progress_callback:
            progress_callback(q_idx, n_quarters)

        world = ProcurementWorld(replace(config, seed=q_idx))
        if carried_suppliers is not None:
            world.carry_supplier_state(carried_suppliers)

        decision_log = self._run_single_quarter(world, config.days_per_quarter)
        carried_suppliers = world.export_supplier_state()

        fitness = self.fitness_evaluator.evaluate(world, decision_log)
        graduation = self.fitness_evaluator.graduation_report(fitness)
        result.quarters.append(QuarterResult(
            quarter_index=q_idx, fitness=fitness, graduation=graduation,
            world_summary=world.summary(), processing_time_s=0.0,
        ))
        if graduation["all_passed"]:
            result.graduated = True
            result.graduated_at_quarter = q_idx

    return result
```

New methods of `ProcurementWorld`:

```python
def export_supplier_state(self) -> Dict[str, VirtualSupplier]:
    """Снимок поставщиков для переноса в следующий квартал (deep copy)."""
    import copy
    return {sid: copy.deepcopy(s) for sid, s in self.suppliers.items()}

def carry_supplier_state(self, carried: Dict[str, VirtualSupplier]) -> None:
    """
    Заменяет только что сгенерированных поставщиков перенесёнными,
    сбрасывая is_defaulted (26.6, обоснование восстановления доверия).
    Вызывается сразу после __init__, до первого tick().
    """
    for sid, supplier in carried.items():
        if sid in self.suppliers:
            supplier.is_defaulted = False
            self.suppliers[sid] = supplier
```

#### 26.6.1 Open question: budget and demand across Stage 1b quarters

Not finally decided. Recorded as a question, not as a finished solution:

If `persistent_suppliers=True`, should the **budget** also be carried
across quarters (the agent truly manages one continuous P&L), or does
each quarter still start from `initial_budget` (an isolated
per-quarter evaluation with persistent partners)?

Argument for carrying the budget: it is closer to the reality of an "internship in one
firm". Money does not appear from nowhere every 90 days.

Argument against: one bad quarter (for example, a supplier default
on day 85) then collapses the rest of the run, and `budget_discipline`
ceases to be a per-quarter metric, which complicates comparison of quarters
with one another.

**Recommendation for the first implementation:** the budget is NOT carried (easier
to diagnose); only supplier identity is carried. If, after introduction,
this turns out to create an unrealistic "reset" of the agent's motivation,
revisit the question in v1.2.

### 26.7 Criteria for transition between stages (update of section 20)

Section 20 of the parent specification ("readiness criteria for Phase 3")
now applies in two sub-steps:

**Readiness Stage 1a → Stage 1b:**
- [ ] `all_passed` (on the 4 Stage 1a criteria) in at least 3 of 5 independent
      runs with different top-level seeds
- [ ] Spread in quarters-to-graduation no greater than ±50% across runs
- [ ] A snapshot is retained of the mean values of the 4 criteria over the last 5
      successful quarters — this is `stage_1a_baseline` for the non-regression guard

**Readiness Stage 1b → Phase 3 (parent specification):**
- [ ] `all_passed` (on the 2 Stage 1b criteria) is reached and **held**
      for at least 3 consecutive quarters (not a single hit, as in
      the diagnosed run of section 26.1)
- [ ] `check_non_regression` — all 4 Stage 1a criteria clear the floor
      in every quarter where `all_passed=true`
- [ ] At least 2 of 5 independent Stage 1b runs (different top-level seed,
      but the same `stage_1a_baseline`) reach stable graduation

### 26.8 New test cases

```python
class TestStagedGraduation:

    def test_stage_1a_ignores_diversification(self, small_world, fitness_evaluator):
        """
        Агент, залипший на одном поставщике (низкий diversification),
        всё равно должен пройти Stage 1a graduation, если остальные
        4 критерия хороши — diversification не gating в этой stage.
        """
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        # decision_log с единственным supplier_id на всех заказах
        ...
        report = evaluator.graduation_report(vector)
        assert report["supplier_diversification"]["gating"] is False
        # all_passed зависит только от 4 других критериев

    def test_stage_1b_requires_diversification(self, fitness_evaluator):
        """Stage 1b: те же данные должны требовать diversification для all_passed."""
        evaluator = ProcurementFitnessEvaluator(stage="1b")
        report = evaluator.graduation_report(vector_with_monopoly)
        assert report["supplier_diversification"]["gating"] is True
        assert report["all_passed"] is False  # низкий diversification блокирует


class TestPersistentSuppliers:

    def test_carry_supplier_state_preserves_reliability(self):
        """После carry_supplier_state атрибуты (кроме is_defaulted) идентичны."""
        config = ProcurementWorldConfig(n_suppliers=3, seed=1)
        world1 = ProcurementWorld(config)
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=2))
        world2.carry_supplier_state(exported)

        for sid, supplier in world1.suppliers.items():
            assert world2.suppliers[sid].reliability == supplier.reliability
            assert world2.suppliers[sid].base_price_multiplier == supplier.base_price_multiplier

    def test_carry_supplier_state_resets_default_flag(self):
        """Дефолтнувший поставщик получает второй шанс в следующем квартале."""
        config = ProcurementWorldConfig(n_suppliers=1, seed=1)
        world1 = ProcurementWorld(config)
        list(world1.suppliers.values())[0].is_defaulted = True
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=1, seed=2))
        world2.carry_supplier_state(exported)

        assert list(world2.suppliers.values())[0].is_defaulted is False

    def test_non_persistent_mode_unaffected(self, small_world_config):
        """persistent_suppliers=False (default) не меняет текущее поведение."""
        assert small_world_config.persistent_suppliers is False


class TestNonRegressionGuard:

    def test_regression_detected_when_cost_efficiency_drops(self, fitness_evaluator):
        baseline = {"cost_efficiency": 0.8, "stockout_avoidance": 0.9,
                     "budget_discipline": 1.0, "reaction_to_risk_events": 0.8}
        degraded_vector = ProcurementFitnessVector(
            cost_efficiency=0.5,  # ниже 0.9 * 0.8 = 0.72 floor
            stockout_avoidance=0.9, budget_discipline=1.0,
            supplier_diversification=0.9, decision_consistency=0.9,
            reaction_to_risk_events=0.8, n_days=90, n_orders=30,
        )
        result = fitness_evaluator.check_non_regression(degraded_vector, baseline)
        assert result["cost_efficiency"] is False
        assert result["stockout_avoidance"] is True
```

### 26.9 CLI: the `--stage` flag

```python
parser.add_argument(
    "--stage", choices=["1a", "1b"], default="1a",
    help="1a: rotating suppliers, general strategy. "
         "1b: persistent suppliers, relationship building. "
         "Requires prior 1a graduation baseline (see --baseline-from)."
)
parser.add_argument(
    "--baseline-from", default=None,
    help="path to a Stage 1a checkpoint/result, required when --stage=1b "
         "for the non-regression guard.",
)
```

### 26.10 What this revision does NOT include (explicitly deferred)

- A mixed or alternating mode (what was proposed as "variant 2")
  is implemented only after section 26.7 has been confirmed for both stages
  separately
- Carrying the budget across Stage 1b quarters (section 26.6.1) is an open
  question; the default decision is not to carry it
- Multi-agent competition for the same persistent suppliers
  is outside the scope of Stage 1/1b altogether and belongs to section 8 of the parent
  specification (multi-agent organization)

---

*Revision v1.1. Section 26 was added after analysis of the first real
run (30 quarters, graduation in 2 of 30, a synchronous anomaly of
diversification/consistency). It justifies and specifies a two-stage
curriculum in place of a single graduation on all 6 criteria at once.*

---

## 27. Execution plan — from the current state to a confirmed Stage 1a

### 27.1 Immediate next step (not Stage 1b, but revalidation of Stage 1a)

Before writing persistent-supplier code (section 26.6), the existing code must
produce the **correct** Stage 1a evaluation. That is,
run `ProcurementFitnessEvaluator(stage="1a")` on the **already collected**
30 quarters of the first run, without running the simulation again. This is cheap
and shows at once whether the matter was only the mismatch of the two groups of criteria.

```bash
python -c "
from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
import json

data = json.load(open('results/sandbox_run_001.json'))
evaluator = ProcurementFitnessEvaluator(stage='1a')

# Пересчитать graduation по сохранённым fitness-векторам без повторной симуляции
passed_count = 0
for q in data:
    f = q['fitness']
    gating = ['cost_efficiency', 'stockout_avoidance', 'budget_discipline', 'reaction_to_risk_events']
    thresholds = {'cost_efficiency': 0.60, 'stockout_avoidance': 0.85,
                  'budget_discipline': 0.95, 'reaction_to_risk_events': 0.50}
    passed = all(f[c] >= thresholds[c] for c in gating)
    passed_count += int(passed)
    print(f\"Q{q['quarter_index']:2d}: 1a_passed={passed}  \" +
          ' '.join(f'{c}={f[c]:.2f}' for c in gating))

print(f'
Stage 1a passed: {passed_count}/30 quarters')
"
```

**Expectation:** the number of quarters with `1a_passed=True` should be noticeably
greater than 2 (the current result under all 6 criteria). If so,
the diagnosis of section 26.1 is confirmed quantitatively, and the plan can
proceed. If the number barely changes, the problem is deeper than
a mismatch of criteria, and analysis must return to the world and the encoder
themselves before two-stage graduation is introduced.

### 27.2 Step 2 — update `procurement_fitness.py` and run 5 independent Stage 1a runs

After the diagnosis is confirmed, apply the changes of section 26.4 and run
the readiness criterion of section 26.7:

```bash
for SEED in 1 2 3 4 5; do
  python -m nowa_sandbox.run_sandbox \
    --stage 1a \
    --quarters 30 --seed $SEED \
    --output results/stage1a_seed${SEED}.json \
    --checkpoint checkpoints/stage1a_seed${SEED}.ckpt
done
```

Collect a summary table:

| seed | graduated | quarter | mean(4 criteria) over the last 5 quarters |
|---|---|---|---|
| 1 | ? | ? | ? |
| 2 | ? | ? | ? |
| 3 | ? | ? | ? |
| 4 | ? | ? | ? |
| 5 | ? | ? | ? |

Transition criterion (section 26.7): at least 3 of 5 graduated, with the spread in quarters
to graduation no greater than ±50%.

### 27.3 Step 3 — fix `stage_1a_baseline`

From the best (or median) run, take the mean values of the 4 criteria
over the last 5 successful quarters. These enter the non-regression guard
for Stage 1b (section 26.5). Save them as a separate JSON file:

```json
{
  "stage_1a_baseline": {
    "cost_efficiency": 0.82,
    "stockout_avoidance": 0.91,
    "budget_discipline": 1.0,
    "reaction_to_risk_events": 0.85
  },
  "source_checkpoint": "checkpoints/stage1a_seed3.ckpt",
  "computed_from_quarters": [26, 27, 28, 29, 30]
}
```

### 27.4 Step 4 — only after 27.3: implementation of Stage 1b

Section 26.6 (`export_supplier_state`/`carry_supplier_state`,
`run_stage1b_persistent`) is implemented at this step, not earlier. Open
question 26.6.1 (carrying the budget) is settled empirically after the first
trial Stage 1b run. If an agent that begins Stage 1b immediately after a
Stage 1a checkpoint behaves reasonably under the default "do not carry the budget",
the question is closed without a further revision.

### 27.5 Do not start both at once

An explicit process constraint: do not write Stage 1b code (section 26.6) and do not
collect the 5-seed Stage 1a sweep (27.2) in parallel within one development
session. First 27.1, then 27.2, then 27.3, then 27.4. This is a direct consequence
of the decision to work out the first variant before moving to the
second. It is recorded as a process constraint, and not only as an
architectural one.

---

*Section 27 is the concrete plan for carrying out revision v1.1. The sequence
of steps 27.1→27.4 is mandatory in that order.*
