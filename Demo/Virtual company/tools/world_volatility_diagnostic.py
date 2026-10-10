"""World volatility / stockout-zero correlation diagnostic (spec v1.2–v1.3).

Two modes:

1. **Results correlation** (v1.3 primary): given a Stage 1a results JSON,
   compare ``world_summary`` fields between low-stockout ("zero") quarters
   and high-stockout ("good") quarters — tests whether stockout zeros track
   world difficulty rather than agent decisions (open Q3).

2. **No-agent simulation** (v1.2): simulate empty worlds across seeds and
   report exogenous stress variance; also probes sleep hooks (open Q2).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def analyze_results_correlation(
    quarters: Sequence[dict],
    zero_threshold: float = 0.10,
    good_threshold: float = 0.80,
) -> Dict[str, Any]:
    """Compare world_summary stats for zero vs good stockout quarters."""
    zero_quarters = [
        q for q in quarters
        if safe_float((q.get("fitness") or {}).get("stockout_avoidance")) < zero_threshold
    ]
    good_quarters = [
        q for q in quarters
        if safe_float((q.get("fitness") or {}).get("stockout_avoidance")) >= good_threshold
    ]

    fields = [
        "n_orders_placed",
        "n_orders_delivered",
        "n_suppliers_defaulted",
        "total_stockout_units",
        "total_holding_cost",
        "spent_ratio",
    ]

    def _group_stats(group: Sequence[dict]) -> Dict[str, Dict[str, float]]:
        ws_list = [q.get("world_summary") or {} for q in group]
        out: Dict[str, Dict[str, float]] = {}
        for field in fields:
            vals = [
                safe_float(ws.get(field))
                for ws in ws_list
                if ws.get(field) is not None
            ]
            if not vals:
                continue
            out[field] = {
                "mean": statistics.mean(vals),
                "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
                "n": float(len(vals)),
            }
        return out

    return {
        "n_quarters": len(quarters),
        "zero_threshold": zero_threshold,
        "good_threshold": good_threshold,
        "n_zero": len(zero_quarters),
        "n_good": len(good_quarters),
        "zero_indices": [q.get("quarter_index") for q in zero_quarters],
        "good_indices": [q.get("quarter_index") for q in good_quarters],
        "zero_stats": _group_stats(zero_quarters),
        "good_stats": _group_stats(good_quarters),
    }


def print_results_correlation(report: Dict[str, Any]) -> None:
    print(f"Total quarters: {report['n_quarters']}")
    print(
        f"Zero quarters (sa < {report['zero_threshold']}): {report['n_zero']}"
    )
    print(
        f"Good quarters (sa >= {report['good_threshold']}): {report['n_good']}"
    )
    print()

    for label, key in (("ZERO quarters", "zero_stats"), ("GOOD quarters", "good_stats")):
        stats = report[key]
        if not stats:
            print(f"=== {label} ===\n  (no data)\n")
            continue
        print(f"=== {label} ===")
        for field, s in stats.items():
            print(
                f"  {field:28s} mean={s['mean']:.3f} std={s['std']:.3f}"
            )
        print()

    print(f"Zero quarter indices: {report['zero_indices']}")
    good = report["good_indices"]
    preview = good[:10]
    suffix = "..." if len(good) > 10 else ""
    print(f"Good quarter indices: {preview}{suffix}")

    # Interpretation hints
    zero = report["zero_stats"]
    good_s = report["good_stats"]
    print("\n=== Interpretation ===")
    if report["n_zero"] == 0:
        print("No zero quarters — stockout floor looks healthy under current params.")
        return
    if report["n_good"] == 0:
        print("No good quarters — agent/world never clears stockout>=0.80.")
        return

    notes = []
    z_def = (zero.get("n_suppliers_defaulted") or {}).get("mean", 0.0)
    g_def = (good_s.get("n_suppliers_defaulted") or {}).get("mean", 0.0)
    if z_def > g_def * 1.5 + 0.05:
        notes.append(
            "n_suppliers_defaulted higher in ZERO → supplier_default_probability may be too high."
        )
    z_spent = (zero.get("spent_ratio") or {}).get("mean", 0.0)
    g_spent = (good_s.get("spent_ratio") or {}).get("mean", 0.0)
    if z_spent > 0.9 and z_spent > g_spent + 0.1:
        notes.append(
            "spent_ratio near 1.0 in ZERO → budget compression may force under-ordering."
        )
    z_so = (zero.get("total_stockout_units") or {}).get("mean", 0.0)
    g_so = (good_s.get("total_stockout_units") or {}).get("mean", 0.0)
    if abs(z_def - g_def) < 0.1 and abs(z_spent - g_spent) < 0.1 and z_so > g_so:
        notes.append(
            "world_summary fields similar aside from stockout itself → "
            "likely agent strategy, not world parameters."
        )
    if not notes:
        notes.append(
            "No strong world_summary differential — compare lead-time/volatility "
            "distributions via a longer instrumented run if needed."
        )
    for note in notes:
        print(f"  - {note}")


def _quarter_difficulty(seed: int, config: ProcurementWorldConfig) -> Dict[str, Any]:
    """Run an empty (no-agent) quarter and report exogenous stress signals."""
    cfg = ProcurementWorldConfig(
        n_products=config.n_products,
        n_suppliers=config.n_suppliers,
        days_per_quarter=config.days_per_quarter,
        initial_budget=config.initial_budget,
        demand_shock_probability=config.demand_shock_probability,
        late_delivery_probability_base=config.late_delivery_probability_base,
        max_lead_time_days=config.max_lead_time_days,
        max_demand_per_day=config.max_demand_per_day,
        min_reorder_days=config.min_reorder_days,
        max_reorder_days=config.max_reorder_days,
        min_initial_stock_days=config.min_initial_stock_days,
        max_initial_stock_days=config.max_initial_stock_days,
        max_demand_volatility=config.max_demand_volatility,
        min_supplier_reliability=config.min_supplier_reliability,
        max_price_volatility=config.max_price_volatility,
        seed=seed,
    )
    world = ProcurementWorld(cfg)
    shocks = 0
    stockouts = 0
    late = 0
    for _ in range(cfg.days_per_quarter):
        world.tick()
        for event in world.day_events:
            etype = event.get("type")
            if etype == "demand_shock":
                shocks += 1
            elif etype == "stockout":
                stockouts += 1
            elif etype == "order_arrived" and event.get("on_time") is False:
                late += 1
    summary = world.summary()
    return {
        "seed": seed,
        "demand_shocks": shocks,
        "stockout_events": stockouts,
        "late_deliveries": late,
        "total_stockout_units": float(summary.get("total_stockout_units", 0.0) or 0.0),
        "budget": float(summary.get("budget", 0.0) or 0.0),
    }


def analyze_world_volatility(
    n_quarters: int = 30,
    base_seed: int = 1,
    config: Optional[ProcurementWorldConfig] = None,
) -> Dict[str, Any]:
    config = config or ProcurementWorldConfig()
    rows = [
        _quarter_difficulty(base_seed * 10_000 + i, config)
        for i in range(1, n_quarters + 1)
    ]
    shocks = [r["demand_shocks"] for r in rows]
    stockouts = [r["stockout_events"] for r in rows]
    stockout_units = [r["total_stockout_units"] for r in rows]

    def _stats(values: List[float]) -> Dict[str, float]:
        return {
            "mean": statistics.fmean(values) if values else 0.0,
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values) if values else 0.0,
            "max": max(values) if values else 0.0,
        }

    return {
        "n_quarters": n_quarters,
        "demand_shock_probability": config.demand_shock_probability,
        "late_delivery_probability_base": config.late_delivery_probability_base,
        "max_lead_time_days": config.max_lead_time_days,
        "demand_shocks": _stats([float(v) for v in shocks]),
        "stockout_events": _stats([float(v) for v in stockouts]),
        "total_stockout_units": _stats(stockout_units),
    }


def analyze_sleep_hooks() -> Dict[str, Any]:
    """Coarse check that the procurement agent exposes a sleep cycle."""
    import random

    from nowa_sandbox.sandbox_agent_factory import create_procurement_agent

    agent = create_procurement_agent(
        "sleep_probe", rng=random.Random(0), seed_intuition=False
    )
    sleep_manager = getattr(agent, "sleep_manager", None)
    has_cycle = callable(getattr(sleep_manager, "sleep_cycle", None))
    return {
        "has_sleep_manager": sleep_manager is not None,
        "has_sleep_cycle": has_cycle,
        "note": (
            "Presence of sleep_cycle does not prove consolidation retains "
            "useful patterns across reseeded worlds — profile hippocampus/"
            "cortex between specific quarters for that (open question 2)."
            if has_cycle
            else "No sleep_cycle found on the agent."
        ),
    }


def print_report(world: Dict[str, Any], sleep: Dict[str, Any]) -> None:
    print("=== World volatility diagnostic (no agent) ===\n")
    print(
        f"Quarters simulated: {world['n_quarters']}  "
        f"demand_shock_p={world['demand_shock_probability']}  "
        f"late_delivery_p={world['late_delivery_probability_base']}  "
        f"max_lead={world.get('max_lead_time_days')}"
    )
    for key in ("demand_shocks", "stockout_events", "total_stockout_units"):
        s = world[key]
        print(
            f"  {key:22s} mean={s['mean']:.3f}  stdev={s['stdev']:.3f}  "
            f"range=[{s['min']:.3f}, {s['max']:.3f}]"
        )
    units = world["total_stockout_units"]
    relative = (units["stdev"] / units["mean"]) if units["mean"] > 0 else 0.0
    high_vol = relative > 0.15 or world["demand_shocks"]["stdev"] > 1.0
    print()
    if high_vol:
        print(
            "VERDICT: exogenous quarter difficulty is HIGHLY VARIABLE even "
            "with no agent."
        )
    else:
        print(
            "VERDICT: exogenous quarter difficulty looks relatively stable."
        )

    print("\n=== Sleep consolidation hooks ===\n")
    print(f"  sleep_manager present : {sleep['has_sleep_manager']}")
    print(f"  sleep_cycle callable  : {sleep['has_sleep_cycle']}")
    print(f"  {sleep['note']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose world volatility / stockout-zero correlations."
    )
    parser.add_argument(
        "results_json",
        nargs="?",
        default=None,
        help="Stage 1a results JSON (correlation mode). Omit for no-agent sim.",
    )
    parser.add_argument(
        "--zero-threshold",
        type=float,
        default=0.10,
        help="stockout_avoidance below this counts as a zero quarter.",
    )
    parser.add_argument("--good-threshold", type=float, default=0.80)
    parser.add_argument("--quarters", type=int, default=30)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--demand-shock-p", type=float, default=None)
    parser.add_argument("--late-delivery-p", type=float, default=None)
    args = parser.parse_args(argv)

    if args.results_json:
        quarters = json.loads(Path(args.results_json).read_text(encoding="utf-8"))
        if not isinstance(quarters, list):
            quarters = (quarters or {}).get("quarters") or []
        report = analyze_results_correlation(
            quarters,
            zero_threshold=args.zero_threshold,
            good_threshold=args.good_threshold,
        )
        print_results_correlation(report)
        return 0

    config = ProcurementWorldConfig()
    if args.demand_shock_p is not None:
        config.demand_shock_probability = float(args.demand_shock_p)
    if args.late_delivery_p is not None:
        config.late_delivery_probability_base = float(args.late_delivery_p)

    world = analyze_world_volatility(
        n_quarters=args.quarters, base_seed=args.seed, config=config
    )
    sleep = analyze_sleep_hooks()
    print_report(world, sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
