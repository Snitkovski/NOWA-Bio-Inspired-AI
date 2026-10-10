"""Summarize a Stage 1a seed sweep and extract the baseline.

Implements the reporting half of spec sections 27.2 and 27.3: read the result
JSON of several independent Stage 1a runs, print the readiness table, check the
two transition criteria from section 26.7, and optionally write the
``stage_1a_baseline`` that Stage 1b's non-regression guard needs.

Usage::

    python -m nowa_sandbox.stage1a_report results/stage1a_seed*.json \\
        --write-baseline results/stage_1a_baseline.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

if __package__ in (None, ""):  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA
from nowa_sandbox.stage_baseline import (
    HIGH_VOLATILITY_IQR,
    compute_stage_1a_baseline,
    save_baseline,
    successful_quarters,
)


MIN_GRADUATED_RUNS = 3
"""Section 26.7: at least 3 of 5 independent runs must graduate."""

MAX_SPREAD_RATIO = 0.5
"""Section 26.7: relative half-width of the allowed band around the mean."""

MIN_ABSOLUTE_HALF_WIDTH = 5
"""Floor on that half-width, in quarters.

Pure ±50% of the mean breaks down when Stage 1a graduates early (q* ≈ 1–3):
a mean of 2.75 yields a band of only ~[1.4, 4.1], so graduating at Q1 *or*
Q6 both fail even though the curriculum is clearly healthy. Flooring the
half-width at 5 quarters keeps the ±50% rule for typical late graduations
while treating early clusters as stable. Wide spreads like [2, 15, 28]
still fail.
"""


def summarize_run(
    path: str, method: str = "median_all"
) -> Dict[str, Any]:
    """Reduce one run's result JSON to the row of the section 27.2 table."""
    quarters = json.loads(Path(path).read_text(encoding="utf-8"))
    good = successful_quarters(quarters)
    first = good[0] if good else None
    payload: Dict[str, Any] = {}
    baseline_error: Optional[str] = None
    if quarters:
        try:
            payload = compute_stage_1a_baseline(quarters, method=method)
        except ValueError as exc:
            baseline_error = str(exc)
            # Still show a diagnostic mean_best row when median_all is refused
            # for short runs, so the readiness table stays readable.
            if method == "median_all":
                try:
                    payload = compute_stage_1a_baseline(
                        quarters, method="mean_best"
                    )
                    payload["method"] = "mean_best_fallback"
                except ValueError:
                    payload = {}

    return {
        "path": path,
        "name": Path(path).stem,
        "n_quarters": len(quarters),
        "graduated": bool(good),
        "n_graduated_quarters": len(good),
        "first_graduation_quarter": (first or {}).get("quarter_index"),
        "baseline": payload.get("stage_1a_baseline", {}),
        "spread_iqr": payload.get("stage_1a_spread_iqr", {}),
        "baseline_method": payload.get("method"),
        "baseline_error": baseline_error,
        "baseline_from_successful": payload.get("from_successful_quarters", False),
        "baseline_quarters": payload.get("computed_from_quarters", []),
        "baseline_payload": payload,
    }


def check_readiness(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate the Stage 1a -> Stage 1b transition criteria (section 26.7).

    Spread rule: every graduated run's ``q*`` must lie within
    ``half_width = max(mean * MAX_SPREAD_RATIO, MIN_ABSOLUTE_HALF_WIDTH)``
    of the mean. ``spread_ratio`` is reported as
    ``max_deviation / half_width`` so values ≤ 1.0 mean within tolerance.
    """
    graduated = [r for r in rows if r["graduated"]]
    quarters = [
        r["first_graduation_quarter"] for r in graduated
        if r["first_graduation_quarter"] is not None
    ]

    spread_ok = True
    spread_ratio = 0.0
    half_width = 0.0
    if len(quarters) >= 2:
        mean_q = statistics.fmean(quarters)
        if mean_q > 0:
            half_width = max(mean_q * MAX_SPREAD_RATIO, float(MIN_ABSOLUTE_HALF_WIDTH))
            max_dev = max(abs(q - mean_q) for q in quarters)
            spread_ratio = max_dev / half_width if half_width > 0 else 0.0
            spread_ok = max_dev <= half_width + 1e-9

    enough = len(graduated) >= MIN_GRADUATED_RUNS
    return {
        "n_runs": len(rows),
        "n_graduated": len(graduated),
        "enough_graduated": enough,
        "graduation_quarters": sorted(quarters),
        "spread_ratio": round(spread_ratio, 3),
        "spread_half_width": round(half_width, 3),
        "spread_within_tolerance": spread_ok,
        "ready_for_stage_1b": bool(enough and spread_ok),
    }


def pick_baseline_run(rows: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Choose the run whose baseline to keep: median of the graduated ones.

    The median rather than the best, so the guard reflects typical Stage 1a
    competence instead of a lucky ceiling that Stage 1b could never hold.
    """
    graduated = [
        r for r in rows
        if r["graduated"] and r.get("baseline") and not r.get("baseline_error")
    ]
    if not graduated:
        # Fall back to any graduated run that at least has numbers (e.g. short
        # exploratory runs that used the mean_best display fallback).
        graduated = [r for r in rows if r["graduated"] and r.get("baseline")]
    if not graduated:
        return None
    ranked = sorted(
        graduated, key=lambda r: statistics.fmean(r["baseline"].values() or [0.0])
    )
    return ranked[len(ranked) // 2]


def print_baseline_summary(payload: Dict[str, Any]) -> None:
    """Print median + IQR with a HIGH VOLATILITY flag (spec v1.2)."""
    method = payload.get("method") or "?"
    print(f"\n=== Stage 1a baseline (method={method}) ===")
    print(
        f"Quarters used: {payload.get('n_quarters_used', 0)} "
        f"(passed: {payload.get('n_quarters_passed', 0)})"
    )
    print()
    baseline = payload.get("stage_1a_baseline") or {}
    spread = payload.get("stage_1a_spread_iqr") or {}
    for criterion in STAGE_1A_CRITERIA:
        median = float(baseline.get(criterion, 0.0))
        iqr = float(spread.get(criterion, 0.0))
        flag = "  HIGH VOLATILITY" if iqr > HIGH_VOLATILITY_IQR else ""
        print(f"  {criterion:24s} median={median:.4f}  IQR={iqr:.4f}{flag}")

    high_vol = [
        c for c in STAGE_1A_CRITERIA
        if float(spread.get(c, 0.0)) > HIGH_VOLATILITY_IQR
    ]
    if high_vol:
        print(
            f"\n  {len(high_vol)} criteria show high quarter-to-quarter "
            f"volatility: {', '.join(high_vol)}."
        )
        print(
            "    This is normal Stage 1a variance, not regression — the "
            "non-regression floor accounts for it (see spec v1.2)."
        )


# Same short labels the training summary prints, so the two are readable side
# by side.
CRITERION_LABELS = {
    "cost_efficiency": "cost_eff",
    "stockout_avoidance": "stockout_avoid",
    "budget_discipline": "budget_disc",
    "reaction_to_risk_events": "risk_react",
}


def format_table(rows: Sequence[Dict[str, Any]]) -> str:
    """Render the section 27.2 readiness table; ``q*`` is first graduation."""
    header = (
        f"{'run':<22} {'grad':>5} {'q*':>4} {'n_ok':>5}  "
        + "  ".join(f"{CRITERION_LABELS[c]:>14}" for c in STAGE_1A_CRITERIA)
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        quarter = row["first_graduation_quarter"]
        lines.append(
            f"{row['name']:<22} "
            f"{('yes' if row['graduated'] else 'no'):>5} "
            f"{(quarter if quarter is not None else '-'):>4} "
            f"{row['n_graduated_quarters']:>5}  "
            + "  ".join(
                f"{row['baseline'].get(c, 0.0):>14.3f}" for c in STAGE_1A_CRITERIA
            )
        )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", help="Stage 1a result JSON files")
    parser.add_argument(
        "--write-baseline",
        default=None,
        help="write the stage_1a_baseline of the median graduated run here",
    )
    parser.add_argument(
        "--baseline-method",
        choices=["median_all", "mean_best"],
        default="median_all",
        help="median_all (recommended): robust to quarter-to-quarter "
             "volatility, used for --write-baseline. mean_best: legacy v1.1 "
             "behaviour, shown for comparison only, refuses to be written as "
             "a guard baseline (see B1).",
    )
    args = parser.parse_args(argv)

    if args.write_baseline and args.baseline_method == "mean_best":
        print(
            "Refusing to write a baseline computed with method=mean_best. "
            "This method reflects peak performance from cherry-picked quarters, "
            "not typical behaviour, and produces a non-regression floor that "
            "flags normal Stage 1a variance as regression (see patch v1.2). "
            "Use --baseline-method median_all, or omit --write-baseline to "
            "view mean_best for comparison only."
        )
        return 1

    rows = [summarize_run(path, method=args.baseline_method) for path in args.results]
    print(format_table(rows))

    readiness = check_readiness(rows)
    print(
        f"\nGraduated runs: {readiness['n_graduated']}/{readiness['n_runs']}"
        f" (need {MIN_GRADUATED_RUNS})"
    )
    print(f"Graduation quarters: {readiness['graduation_quarters']}")
    half = readiness.get("spread_half_width") or 0.0
    print(
        f"Spread ratio: {readiness['spread_ratio']}"
        f" (half-width={half:g}; "
        f"{'within' if readiness['spread_within_tolerance'] else 'outside'}"
        " tolerance)"
    )
    print(
        "READY for Stage 1b" if readiness["ready_for_stage_1b"]
        else "NOT READY for Stage 1b"
    )

    for row in rows:
        payload = row.get("baseline_payload") or {}
        if payload.get("stage_1a_baseline"):
            print_baseline_summary(payload)
            if row.get("baseline_error"):
                print(f"  note: {row['baseline_error']}")

    if args.write_baseline:
        chosen = pick_baseline_run(rows)
        if chosen is None:
            print("\nNo graduated run: refusing to write a baseline.")
            return 1
        if chosen.get("baseline_error") and args.baseline_method == "median_all":
            print(
                f"\nRefusing to write baseline from {chosen['name']}: "
                f"{chosen['baseline_error']}"
            )
            return 1
        payload = dict(chosen.get("baseline_payload") or {})
        payload["stage_1a_baseline"] = chosen["baseline"]
        if chosen.get("spread_iqr"):
            payload["stage_1a_spread_iqr"] = chosen["spread_iqr"]
        payload["computed_from_quarters"] = chosen["baseline_quarters"]
        payload["from_successful_quarters"] = chosen["baseline_from_successful"]
        payload["method"] = chosen.get("baseline_method") or args.baseline_method
        save_baseline(args.write_baseline, payload, source=chosen["path"])
        print(f"\nBaseline from {chosen['name']} -> {args.write_baseline}")
        print_baseline_summary(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
