"""Shared helpers for the NOWA procurement sandbox demo."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any


def ensure_core_src_on_path() -> None:
    """Make the repository-level NOWA core modules importable when available."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src" / "agent.py"
        if candidate.exists():
            core_src = str(parent / "src")
            if core_src not in sys.path:
                sys.path.insert(0, core_src)
            return


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert to float, mapping NaN/inf/garbage onto ``default``."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if math.isnan(result) or math.isinf(result):
        return float(default)
    return result


def is_finite_number(value: Any) -> bool:
    """True only for real, finite numeric values (rejects NaN, inf, strings)."""
    if isinstance(value, bool):
        return False
    try:
        result = float(value)
    except (TypeError, ValueError):
        return False
    return not (math.isnan(result) or math.isinf(result))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def safe_int(value: Any, default: int = 0, minimum: int | None = None) -> int:
    """Convert to int with a floor, used to sanitize world configuration."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    if minimum is not None:
        result = max(minimum, result)
    return result


__all__ = [
    "clamp",
    "ensure_core_src_on_path",
    "is_finite_number",
    "safe_float",
    "safe_int",
]
