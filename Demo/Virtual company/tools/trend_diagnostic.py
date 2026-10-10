"""Moving-average trend diagnostic for Stage 1a runs.

Not part of nowa_sandbox itself — a standalone analysis script that reads
an existing results JSON and reports whether per-criterion performance shows
any learning trend when smoothed, or remains pure noise (open question 1
from patch v1.2).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import List, Optional, Sequence

# Allow `python tools/trend_diagnostic.py ...` from the Virtual company root.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def moving_average(values: Sequence[float], window: int = 10) -> List[float]:
    if len(values) < window:
        return []
    return [
        statistics.mean(values[i : i + window])
        for i in range(len(values) - window + 1)
    ]


def trend_slope(smoothed: Sequence[float]) -> float:
    """Simple linear regression slope over the smoothed series.

    Near-zero slope with the raw series noisy = no learning signal.
    Clearly positive slope = agent is improving despite per-quarter noise.
    """
    n = len(smoothed)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(smoothed)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(smoothed))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


LEARNING_SLOPE_STRICT = 0.002
"""Original v1.2 threshold — high bar, missed weak real trends on 100Q."""

LEARNING_SLOPE_RELAXED = 0.0005
"""Softer bar suggested by v1.3 open questions (cost_efficiency slope ~0.001)."""

FIRST_LAST_DELTA = 0.05
"""Secondary signal: mean(last20) - mean(first20) above this counts as lift."""


def _first_last_delta(raw: Sequence[float], window: int = 20) -> float:
    if len(raw) < window * 2:
        return 0.0
    return statistics.mean(raw[-window:]) - statistics.mean(raw[:window])


def classify_trend(
    slope: float,
    first_last_delta: float = 0.0,
    *,
    strict: float = LEARNING_SLOPE_STRICT,
    relaxed: float = LEARNING_SLOPE_RELAXED,
) -> Dict[str, str]:
    """Return both strict (v1.2) and dual (v1.3-aware) verdicts."""
    if slope > strict:
        strict_v = "LEARNING TREND"
    elif abs(slope) <= strict:
        strict_v = "NO CLEAR TREND"
    else:
        strict_v = "DECLINING TREND"

    if slope > relaxed or first_last_delta > FIRST_LAST_DELTA:
        dual_v = "LEARNING TREND"
    elif slope < -relaxed or first_last_delta < -FIRST_LAST_DELTA:
        dual_v = "DECLINING TREND"
    else:
        dual_v = "NO CLEAR TREND"

    return {"strict": strict_v, "dual": dual_v}


def analyze(quarters: Sequence[dict], window: int = 10) -> dict:
    from nowa_sandbox.procurement_fitness import STAGE_1A_CRITERIA

    report = {}
    print(f"=== Trend diagnostic ({len(quarters)} quarters, window={window}) ===\n")
    for criterion in STAGE_1A_CRITERIA:
        raw = [
            float((q.get("fitness") or {}).get(criterion, 0.0)) for q in quarters
        ]
        smoothed = moving_average(raw, window)
        if not smoothed:
            print(f"{criterion}: not enough quarters for window={window}")
            report[criterion] = {"verdict": "INSUFFICIENT_DATA"}
            continue
        slope = trend_slope(smoothed)
        delta = _first_last_delta(raw)
        raw_std = statistics.pstdev(raw) if len(raw) > 1 else 0.0
        smoothed_std = statistics.pstdev(smoothed) if len(smoothed) > 1 else 0.0
        verdicts = classify_trend(slope, delta)
        print(
            f"{criterion:24s} raw_std={raw_std:.3f}  "
            f"smoothed_std={smoothed_std:.3f}  slope={slope:+.5f}  "
            f"d20={delta:+.3f}  "
            f"[strict={verdicts['strict']}] [dual={verdicts['dual']}]"
        )
        report[criterion] = {
            "raw_std": raw_std,
            "smoothed_std": smoothed_std,
            "slope": slope,
            "first_last_delta": delta,
            "verdict": verdicts["strict"],
            "verdict_dual": verdicts["dual"],
        }
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose Stage 1a learning trend.")
    parser.add_argument("results_json", help="Path to a Stage 1a results file.")
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args(argv)

    quarters = json.loads(Path(args.results_json).read_text(encoding="utf-8"))
    if not isinstance(quarters, list):
        # Accept a training-result wrapper with a top-level "quarters" key.
        quarters = (quarters or {}).get("quarters") or []
    analyze(quarters, window=args.window)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
