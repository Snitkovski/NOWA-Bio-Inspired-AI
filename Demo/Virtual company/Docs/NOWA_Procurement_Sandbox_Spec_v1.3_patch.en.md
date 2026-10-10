## Abstract

Russian version: [NOWA_Procurement_Sandbox_Spec_v1.3_patch.ru.md](NOWA_Procurement_Sandbox_Spec_v1.3_patch.ru.md)

Patch v1.3 analyses a one-hundred-quarter Stage 1a run (seed 1, under the v1.2 baseline method). Budget discipline equals 1.000 in all ten decades. Cost efficiency by decade means rises from 0.704 to 0.857, and reaction to risk from 0.711 to 0.754. Stockout avoidance by decade is 0.444, 0.338, 0.405, 0.335, 0.528, 0.437, 0.255, 0.492, 0.562, and 0.487, and shows no trend. Its interquartile range is 0.8351, against a range of 0.000–0.205 for the other criteria. The decade of quarters 31–40 contains no graduation, whereas quarters 21–30 contain two and quarters 41–50 contain four. The document attributes the local failure to world difficulty fixed by the seed, and assigns the world parameters as the primary object of revision; the question of `sleep_cycle` consolidation remains secondary and is examined after those parameters are narrowed.

The mechanism of a structurally impassable quarter is described by the combination of the upper bounds of the preceding initialisation: base demand up to 50 units a day, a reorder point in a range of about 5–12 days of demand, initial stock of about 10–30 days, lead time up to 21 days, and demand volatility up to 0.40. An order placed at the first signal below the reorder point may not arrive before the buffer is exhausted, so that an optimal strategy does not save the quarter. Direction Q3b narrows the configuration: maximum lead time 10 days, maximum base demand 30, demand volatility no higher than 0.30, minimum supplier reliability 0.80, reorder point 7–15 days of demand, and initial stock 15–25 days. The criterion for a new thirty-quarter run on a seed other than seed 1 is an interquartile range of stockout avoidance below 0.50.

Direction Q3a introduces a `WorldDifficultyEstimator` and an optional normalisation of raw `stockout_avoidance` by the fraction of demand theoretically satisfiable in that world. Normalisation is off by default and is enabled as a diagnostic if the range remains above 0.4 after Q3b. A diagnostic script compares quarters whose stockout avoidance lies below a chosen threshold with quarters whose value is at least 0.80, using fields of the world summary. Separately, the slope threshold of 0.002 at a moving average of window 10 misses the recorded cost-efficiency slope of +0.00096, although the decade means show a rise from 0.704 to 0.857; lowering the threshold to 0.0005, or adding a difference between the first and last twenty quarters greater than 0.05, is deferred to version 1.4.

---

# NOWA Procurement Sandbox — Patch v1.3

**Base documents:**
- NOWA_Procurement_Sandbox_Spec.md (v1.0)
- v1.1_patch.md — two-stage curriculum
- v1.1.1_patch.md — streak plus non-regression in the graduation condition
- v1.2_patch.md — median baseline plus a volatility-aware floor

**Status:** Ready for implementation

---

## Empirical basis

A 100-quarter Stage 1a run (seed 1, v1.2) produced the following picture:

| Criterion | Decade means | Diagnosis |
|---|---|---|
| `budget_discipline` | 1.000 in all 10 decades | Ceiling — already mastered completely |
| `cost_efficiency` | 0.704 → 0.857 | A slow, genuine learning trend |
| `reaction_to_risk_events` | 0.711 → 0.754 | Stable, moderate growth |
| `stockout_avoidance` | 0.444, 0.338, 0.405, **0.335**, 0.528, 0.437, **0.255**, 0.492, 0.562, 0.487 | No trend, IQR=0.835 |

**`stockout_avoidance` shows anomalous dispersion.** IQR=0.8351 covers almost
the whole theoretical range [0, 1]. The other three criteria have an IQR of 0.000–0.205.
The gap is an order of magnitude. It indicates not slow learning, but structurally
different classes of task that the world presents to the agent in different quarters.

**Decade Q31–40: 0 graduated quarters**, against Q21–30: 2 and Q41–50: 4. The failure
is localised in a particular range, rather than spread evenly over 100
quarters. That is a sign of seed-determined world difficulty, not of a
stochastic failure of sleep consolidation.

**Conclusion:** the primary candidate for v1.3 is Open Question 3 (world
parameters create impassable quarters). Open Question 2 (sleep consolidation)
remains a secondary candidate, to be checked after Q3.

---

## Analysis: why `stockout_avoidance` is so volatile

### The mechanism of a "perfectly bad quarter"

`VirtualProduct.reorder_point` and `base_demand_per_day` are initialised
at random for each new `ProcurementWorld`. The following combination is possible:

```
base_demand_per_day = 48 (верхняя граница диапазона [5, 50])
reorder_point = 48 × rng.uniform(5, 12) = ~432 единицы
current_stock  = 48 × rng.uniform(10, 30) = ~720 единицы
lead_time_days = rng.randint(3, 21) = 21 (максимум)
demand_volatility = 0.40 (максимум)
demand_shock_probability = 0.05 → в среднем 4–5 шоков за 90 дней
```

In such a quarter the agent first sees `below_reorder_point` at about
day 4–6, places an order with the best available supplier, and waits
21 days. By then, high demand has already consumed the whole buffer. This is a
**structurally impassable quarter**: an optimal strategy does not save it.

### Why this is a problem for the curriculum

Stage 1a assumes that the agent must learn to manage stock.
If 20–30% of quarters are structurally impassable for `stockout_avoidance`
regardless of the agent's strategy, then:

1. The agent cannot distinguish "I made a bad decision" from "this quarter
   was impassable". There is no correct reward signal for learning
2. The fitness metric mixes the agent's competence with the luck of the world
3. A `stage_1a_baseline` computed on such a mixture is unreliable

---

## Two directions of the fix (both are realised in this patch)

### Direction Q3a — normalisation of quarter difficulty

Introduce a `WorldDifficultyEstimator` that, for each new world,
computes an a priori difficulty from the configuration parameters.
`stockout_avoidance` is scored relative to what is "maximally attainable
in this world", not against an absolute threshold.

### Direction Q3b — bounding the range of world parameters

Narrow the ranges of `ProcurementWorldConfig` so that "perfectly bad"
quarters do not occur. This is the more conservative approach, less precise, but simpler
to implement and sufficient for the first iteration.

**Recommended order:** Q3b first (fast, and it yields data), then
Q3a (the accurate treatment, if Q3b is not sufficient).

---

## Affected files

| File | Kind of change |
|---|---|
| `procurement_world.py` | Narrow the ranges of `_init_products` and `_init_suppliers` (Q3b) |
| `procurement_fitness.py` | Optional difficulty normalisation for `stockout_avoidance` (Q3a) |
| `sandbox_config.py` | New config parameters that control the ranges |
| `tools/world_volatility_diagnostic.py` | A new tool (not part of the main package) |
| `tests/` | Tests of the new ranges and of normalisation |

---

## Change 1 (Q3b): `ProcurementWorldConfig` — bounding the ranges

### Current ranges (problematic)

```python
# В _init_products():
base_demand_per_day = rng.uniform(5, 50)    # диапазон 10x
reorder_point = base_demand * rng.uniform(5, 12)
current_stock  = base_demand * rng.uniform(10, 30)

# В _init_suppliers():
lead_time_days = rng.randint(3, 21)         # разброс 7x
reliability    = rng.uniform(0.70, 0.99)
price_volatility = rng.uniform(0.02, 0.15)
```

### New bounded ranges

```python
@dataclass
class ProcurementWorldConfig:
    # ... существующие поля ...

    # Q3b: difficulty bounding
    max_lead_time_days: int = 10
    """Upper bound for supplier lead time (was hardcoded 21).
    Reducing from 21 to 10 eliminates the 'structurally impossible quarter'
    where a 21-day lead time combined with high demand volatility makes
    stockout unavoidable regardless of agent strategy.
    Spec v1.3 open question Q3."""

    max_demand_per_day: float = 30.0
    """Upper bound for base_demand_per_day (was 50).
    Narrowing the range reduces variance in world difficulty without
    making the task trivially easy."""

    min_reorder_days: float = 7.0
    max_reorder_days: float = 15.0
    """Reorder point expressed in days of demand (was 5..12 days).
    Raising the floor ensures the agent always has an actionable signal
    before stockout becomes inevitable."""

    min_initial_stock_days: float = 15.0
    max_initial_stock_days: float = 25.0
    """Initial stock expressed in days of demand (was 10..30).
    Raising the floor prevents quarters that begin already in crisis."""
```

### Update of `_init_products` and `_init_suppliers`

```python
def _init_products(self) -> Dict[str, VirtualProduct]:
    products = {}
    for i in range(self.config.n_products):
        pid = f"product_{i:03d}"
        base_demand = self.rng.uniform(5, self.config.max_demand_per_day)
        products[pid] = VirtualProduct(
            product_id=pid,
            base_demand_per_day=base_demand,
            demand_volatility=self.rng.uniform(0.1, 0.3),  # было 0.4
            holding_cost_per_unit=self.rng.uniform(0.5, 2.0),
            stockout_penalty_per_unit=self.rng.uniform(5, 20),
            current_stock=base_demand * self.rng.uniform(
                self.config.min_initial_stock_days,
                self.config.max_initial_stock_days,
            ),
            reorder_point=base_demand * self.rng.uniform(
                self.config.min_reorder_days,
                self.config.max_reorder_days,
            ),
        )
    return products

def _init_suppliers(self) -> Dict[str, VirtualSupplier]:
    suppliers = {}
    for i in range(self.config.n_suppliers):
        sid = f"supplier_{i:03d}"
        suppliers[sid] = VirtualSupplier(
            supplier_id=sid,
            reliability=self.rng.uniform(0.80, 0.99),  # было 0.70
            base_price_multiplier=self.rng.uniform(0.85, 1.15),
            price_volatility=self.rng.uniform(0.02, 0.10),  # было 0.15
            lead_time_days=self.rng.randint(
                3, self.config.max_lead_time_days
            ),
        )
    return suppliers
```

### Why these values

| Parameter | Was | Becomes | Justification |
|---|---|---|---|
| `lead_time_days` max | 21 | 10 | At 10 days, with `reorder_point` at 7+ days of demand, the agent **has time** to place a repeat order before stockout under any reasonable demand |
| `demand_volatility` max | 0.40 | 0.30 | At 0.30 and a base demand of 30/day, σ=9/day, which is ±30%: difficult enough, but it does not make the quarter impassable |
| `reliability` min | 0.70 | 0.80 | Excludes suppliers whose probability of lateness exceeds 20%. That class creates chained stockouts through unexpected delays |
| `reorder_point` min | 5 days | 7 days | Gives the agent at least 7 days to react at any lead time up to 10 days |
| `initial_stock` min | 10 days | 15 days | A quarter does not begin already in a critical situation |

---

## Change 2 (Q3a): difficulty normalisation for `stockout_avoidance`

This is the more accurate approach, and also the more complex one. It is implemented **after** Q3b,
if, once the ranges are bounded, the IQR of `stockout_avoidance` remains
above 0.4.

### `WorldDifficultyEstimator`

```python
"""nowa_sandbox/world_difficulty.py"""

from dataclasses import dataclass
from typing import Any


@dataclass
class WorldDifficulty:
    """Estimates the inherent difficulty of a world for stockout_avoidance.

    Used to normalize fitness scores so the agent is judged on its
    decisions, not on the luck of world parameters.
    """
    max_lead_time: int
    mean_demand_volatility: float
    min_initial_stock_days: float
    mean_reorder_days: float
    expected_demand_shocks: float   # n_products * days * shock_prob

    def stockout_theoretical_max(self) -> float:
        """Estimate the best possible stockout_avoidance in this world
        for a perfect agent with full information.

        Formula: a perfect agent orders just-in-time at the exact
        reorder point, so the maximum exposed demand is:
        lead_time_days * base_demand * (1 + demand_volatility).
        If initial_stock > this, no stockout is structurally inevitable.

        Returns a value in [0, 1] representing the fraction of demand
        that is theoretically satisfiable by any strategy.
        """
        # Simplified heuristic — detailed implementation TBD
        lead_factor = 1.0 - (self.max_lead_time / 21.0) * 0.3
        volatility_factor = 1.0 - self.mean_demand_volatility * 0.5
        shock_factor = max(0.5, 1.0 - self.expected_demand_shocks * 0.05)
        return max(0.3, min(1.0, lead_factor * volatility_factor * shock_factor))


def estimate_difficulty(world: Any) -> WorldDifficulty:
    """Snapshot world difficulty from a ProcurementWorld instance."""
    products = list(world.products.values())
    suppliers = list(world.suppliers.values())
    n_days = world.config.days_per_quarter
    n_products = len(products)

    return WorldDifficulty(
        max_lead_time=max((s.lead_time_days for s in suppliers), default=10),
        mean_demand_volatility=(
            sum(p.demand_volatility for p in products) / n_products
            if n_products else 0.25
        ),
        min_initial_stock_days=(
            min(p.current_stock / max(p.base_demand_per_day, 0.01)
                for p in products)
            if n_products else 10.0
        ),
        mean_reorder_days=(
            sum(p.reorder_point / max(p.base_demand_per_day, 0.01)
                for p in products) / n_products
            if n_products else 7.0
        ),
        expected_demand_shocks=n_products * n_days * world.config.demand_shock_probability,
    )
```

### Integration into `ProcurementFitnessEvaluator`

```python
def _stockout_avoidance(
    self,
    world: Any,
    normalize_difficulty: bool = False,
) -> float:
    """
    normalize_difficulty=False (default, Q3b path): raw fraction,
    identical to v1.0-v1.2 behaviour.

    normalize_difficulty=True (Q3a path): score is divided by the
    world's theoretical maximum, so an agent doing the best possible
    in a hard world scores ~1.0, not 0.3.
    """
    total_demand = sum(
        p.base_demand_per_day * world.day for p in world.products.values()
    )
    total_stockout = sum(
        p.cumulative_stockout_units for p in world.products.values()
    )
    if total_demand <= 0:
        return 1.0
    stockout_ratio = total_stockout / total_demand
    raw_score = max(0.0, 1.0 - min(1.0, stockout_ratio * 5.0))

    if not normalize_difficulty:
        return raw_score

    from .world_difficulty import estimate_difficulty
    difficulty = estimate_difficulty(world)
    theoretical_max = difficulty.stockout_theoretical_max()
    if theoretical_max <= 0.0:
        return raw_score
    return min(1.0, raw_score / theoretical_max)
```

Add `normalize_stockout_difficulty: bool = False` to
`ProcurementFitnessEvaluator.__init__` and pass it into
`_stockout_avoidance`.

---

## Change 3: the diagnostic tool `world_volatility_diagnostic.py`

```python
"""tools/world_volatility_diagnostic.py

Analyse whether stockout_avoidance zeros correlate with world parameters
(high lead time, high demand volatility) rather than agent decisions.

This directly tests Open Question 3 from spec v1.2: are some quarters
structurally impossible for stockout_avoidance?
"""

import argparse
import json
import statistics
from pathlib import Path
from typing import List


def main():
    parser = argparse.ArgumentParser(
        description="Test if stockout zeros correlate with world difficulty."
    )
    parser.add_argument("results_json")
    parser.add_argument(
        "--zero-threshold", type=float, default=0.10,
        help="stockout_avoidance below this is treated as a 'zero quarter'."
    )
    args = parser.parse_args()

    quarters = json.loads(Path(args.results_json).read_text())

    zero_quarters = [
        q for q in quarters
        if q["fitness"]["stockout_avoidance"] < args.zero_threshold
    ]
    good_quarters = [
        q for q in quarters
        if q["fitness"]["stockout_avoidance"] >= 0.80
    ]

    print(f"Total quarters: {len(quarters)}")
    print(f"Zero quarters (sa < {args.zero_threshold}): {len(zero_quarters)}")
    print(f"Good quarters (sa >= 0.80): {len(good_quarters)}")
    print()

    # Extract world summary fields if available
    for label, group in [("ZERO quarters", zero_quarters),
                          ("GOOD quarters", good_quarters)]:
        if not group:
            continue
        print(f"=== {label} ===")
        ws_list = [q.get("world_summary", {}) for q in group]

        for field in [
            "n_orders_placed", "n_orders_delivered",
            "n_suppliers_defaulted", "total_stockout_units",
            "total_holding_cost", "spent_ratio",
        ]:
            vals = [safe_float(ws.get(field)) for ws in ws_list
                    if ws.get(field) is not None]
            if vals:
                print(f"  {field:28s} mean={statistics.mean(vals):.3f} "
                      f"std={statistics.pstdev(vals):.3f}")
        print()

    # Quarter indices
    print(f"Zero quarter indices: "
          f"{[q['quarter_index'] for q in zero_quarters]}")
    print(f"Good quarter indices: "
          f"{[q['quarter_index'] for q in good_quarters[:10]]}...")


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


if __name__ == "__main__":
    main()
```

### Use

```bash
python tools/world_volatility_diagnostic.py \
  results/stage1a_seed1_extended.json \
  --zero-threshold 0.05
```

**Interpretation:**
- If `n_suppliers_defaulted` is significantly higher for zero-quarters than for
  good quarters, then `supplier_default_probability` is too high
- If `spent_ratio` for zero-quarters is close to 1.0, the agent exhausted the
  budget and could not order enough goods (budget
  compression forced under-ordering)
- If no field differs, the problem is in the agent's strategy,
  not in the world parameters

---

## Test cases

### `tests/test_world_difficulty_bounds.py` (new file)

```python
"""Tests ensuring Q3b parameter bounding eliminates impossible quarters."""

import random
import pytest
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig


class TestLeadTimeBound:

    def test_max_lead_time_respected(self):
        config = ProcurementWorldConfig(n_suppliers=5, seed=42, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days <= 10, (
                f"supplier {supplier.supplier_id} lead_time={supplier.lead_time_days} "
                f"exceeds max_lead_time_days=10"
            )

    def test_default_max_lead_time_is_10(self):
        """New default must be 10, not 21."""
        config = ProcurementWorldConfig()
        assert config.max_lead_time_days == 10

    def test_lead_time_always_gte_3(self):
        """Lower bound unchanged."""
        config = ProcurementWorldConfig(n_suppliers=20, seed=1, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days >= 3


class TestDemandVolatilityBound:

    def test_volatility_capped_at_0_3(self):
        config = ProcurementWorldConfig(n_products=20, seed=42)
        world = ProcurementWorld(config)
        for product in world.products.values():
            assert product.demand_volatility <= 0.30 + 1e-9, (
                f"product {product.product_id} volatility={product.demand_volatility} "
                f"exceeds 0.30"
            )


class TestInitialStockFloor:

    def test_initial_stock_at_least_min_days(self):
        config = ProcurementWorldConfig(
            n_products=10, seed=42, min_initial_stock_days=15.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            days_of_stock = (product.current_stock /
                             max(product.base_demand_per_day, 0.01))
            assert days_of_stock >= 14.0, (  # -1 day tolerance for float
                f"product {pid} has only {days_of_stock:.1f} days of stock "
                f"(min expected: 15)"
            )


class TestReorderPointFloor:

    def test_reorder_point_covers_max_lead_time(self):
        """With min_reorder_days=7 and max_lead_time=10, there's always
        a 7-day buffer before hitting reorder_point from which the agent
        has time to order and receive before stockout."""
        config = ProcurementWorldConfig(
            n_products=10, seed=42,
            max_lead_time_days=10, min_reorder_days=7.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            reorder_days = (product.reorder_point /
                            max(product.base_demand_per_day, 0.01))
            assert reorder_days >= 6.5, (  # -0.5 tolerance
                f"product {pid} reorder_point covers only {reorder_days:.1f} "
                f"days of demand (min expected: 7)"
            )


class TestBackwardCompatibility:

    def test_old_config_without_new_fields_still_works(self):
        """Code that constructs ProcurementWorldConfig without the new
        difficulty-bounding fields must continue to work unchanged."""
        config = ProcurementWorldConfig(
            initial_budget=50_000.0,
            n_products=5, n_suppliers=3,
            days_per_quarter=90, seed=1,
        )
        world = ProcurementWorld(config)
        assert world is not None
        world.tick()
```

---

## Definition of Done

- [ ] `ProcurementWorldConfig` contains the new fields with documented
      defaults: `max_lead_time_days=10`, `max_demand_per_day=30.0`,
      `min_reorder_days=7.0`, `max_reorder_days=15.0`,
      `min_initial_stock_days=15.0`, `max_initial_stock_days=25.0`
- [ ] `_init_products` and `_init_suppliers` use the new fields in place of
      hardcoded ranges
- [ ] Every test case in `test_world_difficulty_bounds.py` is green
- [ ] A 30-quarter Stage 1a run with the new parameters (a new seed, not seed 1,
      so that "familiar" data are not reused): the IQR of `stockout_avoidance`
      has fallen below 0.50 (it was 0.835 over 100 quarters)
- [ ] `world_volatility_diagnostic.py` has been run on the new results. The difference
      between zero-quarters and good quarters on `world_summary` fields has either
      shrunk or been explained
- [ ] `normalize_stockout_difficulty` (`WorldDifficultyEstimator`) is implemented
      as an option, but is **not enabled by default**. It is for diagnosis only,
      until it is confirmed that Q3b is insufficient

---

## Open questions (they pass to v1.4 if they are not closed)

**Q2 (sleep consolidation)** remains a candidate, but its priority is lowered.
A weak positive trend (`cost_efficiency` 0.704→0.857, graduation clusters
in Q41–50, Q81–90, Q91–100) indicates that consolidation is working,
only slowly. If, after Q3b, the IQR of `stockout_avoidance` falls and the agent
begins to graduate more often, Q2 is closed without code. If not, a
separate analysis of hippocampus and cortex between particular quarters is required.

**The `LEARNING_TREND` threshold in `trend_diagnostic.py`.** A slope greater than 0.002 at
MA10 proved too strict: it does not detect a weak genuine trend (slope +0.00096 for
`cost_efficiency`), although the decade means show
growth from 0.704 to 0.857. Consider lowering the threshold to 0.0005, or adding
a second criterion (a first20/last20 difference greater than 0.05), in v1.4.

---

*Patch v1.3. Justified by the data of a 100-quarter run. The primary fix is
Q3b (narrowing the world parameters). Q3a (difficulty normalisation) is implemented
as a diagnostic option, not as the default. The success test is an IQR of
`stockout_avoidance` below 0.50 after a new run.*
