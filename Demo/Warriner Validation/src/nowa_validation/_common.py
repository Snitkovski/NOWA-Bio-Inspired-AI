"""Shared helpers for the NOWA x Warriner validation demo."""

from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


WORD_ALIASES = ("Word", "word", "lemma", "Lemma", "term", "Term")
VALENCE_ALIASES = ("V.Mean.Sum", "valence", "Valence", "V", "v")
AROUSAL_ALIASES = ("A.Mean.Sum", "arousal", "Arousal", "A", "a")
DOMINANCE_ALIASES = ("D.Mean.Sum", "dominance", "Dominance", "D", "d")


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
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if math.isnan(result) or math.isinf(result):
        return float(default)
    return result


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def normalize_word(word: Any) -> str:
    return str(word or "").strip().lower()


def _first_present(row: Mapping[str, Any], aliases: Sequence[str]) -> Any:
    for key in aliases:
        if key in row and row[key] not in (None, ""):
            return row[key]
    lowered = {str(key).lower(): key for key in row.keys()}
    for key in aliases:
        match = lowered.get(str(key).lower())
        if match is not None and row[match] not in (None, ""):
            return row[match]
    return None


def _first_present_item(row: Mapping[str, Any], aliases: Sequence[str]) -> Tuple[Optional[str], Any]:
    for key in aliases:
        if key in row and row[key] not in (None, ""):
            return key, row[key]
    lowered = {str(key).lower(): key for key in row.keys()}
    for key in aliases:
        match = lowered.get(str(key).lower())
        if match is not None and row[match] not in (None, ""):
            return str(match), row[match]
    return None, None


def _looks_normalized(values: Sequence[float], lo: float, hi: float) -> bool:
    if not values:
        return False
    return all(lo <= value <= hi for value in values)


def table_to_records(table: Any) -> List[Dict[str, Any]]:
    """Convert a pandas DataFrame, list of dicts, or similar table to records."""
    if table is None:
        return []
    if isinstance(table, list):
        return [dict(row) for row in table if isinstance(row, Mapping)]
    if isinstance(table, tuple):
        return [dict(row) for row in table if isinstance(row, Mapping)]
    if hasattr(table, "to_dict"):
        try:
            records = table.to_dict(orient="records")
            return [dict(row) for row in records if isinstance(row, Mapping)]
        except TypeError:
            pass
    if hasattr(table, "iterrows"):
        try:
            return [dict(row) for _, row in table.iterrows()]
        except Exception:
            pass
    raise TypeError("warriner data must be a list of dicts or a pandas-like table")


def normalize_warriner_records(table: Any) -> List[Dict[str, Any]]:
    """Return normalized rows with keys word, v, a, d.

    Warriner raw V/A/D values are usually on a 1..9 scale. Already-normalized
    inputs are accepted for tests and programmatic use.
    """
    raw_records = table_to_records(table)
    normalized: List[Dict[str, Any]] = []

    for row in raw_records:
        word = normalize_word(_first_present(row, WORD_ALIASES))
        if not word:
            continue
        v_key, raw_v = _first_present_item(row, VALENCE_ALIASES)
        a_key, raw_a = _first_present_item(row, AROUSAL_ALIASES)
        d_key, raw_d = _first_present_item(row, DOMINANCE_ALIASES)
        v = safe_float(raw_v, default=float("nan"))
        a = safe_float(raw_a, default=float("nan"))
        d = safe_float(raw_d, default=float("nan"))
        if math.isnan(v) or math.isnan(a) or math.isnan(d):
            continue

        has_canonical = {"v", "a", "d"}.issubset({str(k).lower() for k in row.keys()})
        key_triplet = {str(v_key or "").lower(), str(a_key or "").lower(), str(d_key or "").lower()}
        explicit_normalized = has_canonical or key_triplet.issubset(
            {"v", "a", "d", "valence", "arousal", "dominance"}
        )
        if has_canonical:
            valence = safe_float(row.get("v", v))
            arousal = safe_float(row.get("a", a))
            dominance = safe_float(row.get("d", d))
        elif explicit_normalized:
            valence = v
            arousal = a
            dominance = d
        else:
            valence = (v - 5.0) / 4.0
            arousal = (a - 1.0) / 8.0
            dominance = (d - 1.0) / 8.0

        normalized.append(
            {
                "word": word,
                "v": clamp(valence, -1.0, 1.0),
                "a": clamp(arousal, 0.0, 1.0),
                "d": clamp(dominance, 0.0, 1.0),
                "V.Mean.Sum": v,
                "A.Mean.Sum": a,
                "D.Mean.Sum": d,
            }
        )
    return normalized


def load_warriner_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return normalize_warriner_records(list(reader))


def mean(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(value) for value in values]
    if not items:
        return float(default)
    return sum(items) / float(len(items))


def population_sd(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    avg = mean(items)
    return math.sqrt(sum((value - avg) ** 2 for value in items) / float(len(items)))


def rankdata(values: Sequence[float]) -> List[float]:
    indexed = sorted((float(value), idx) for idx, value in enumerate(values))
    ranks = [0.0] * len(indexed)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][0] == indexed[i][0]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][1]] = avg_rank
        i = j + 1
    return ranks


def pearson_r(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    lx = [float(value) for value in left]
    ry = [float(value) for value in right]
    mean_x = mean(lx)
    mean_y = mean(ry)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(lx, ry))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in lx))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ry))
    denom = den_x * den_y
    if denom <= 0.0:
        return 0.0
    return clamp(num / denom, -1.0, 1.0)


def spearman_rho(left: Sequence[float], right: Sequence[float]) -> Tuple[float, float]:
    rho = pearson_r(rankdata(left), rankdata(right))
    n = min(len(left), len(right))
    perfect = abs(abs(rho) - 1.0) <= 1e-9
    if n < 3 or perfect:
        return rho, 0.0 if perfect and n >= 2 else 1.0
    z = rho * math.sqrt(max(1.0, n - 1.0))
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return rho, clamp(p, 0.0, 1.0)


def compute_ccc_values(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    if len(y_true) != len(y_pred) or len(y_true) < 2:
        return 0.0
    true_values = [float(value) for value in y_true]
    pred_values = [float(value) for value in y_pred]
    mean_true = mean(true_values)
    mean_pred = mean(pred_values)
    var_true = mean((value - mean_true) ** 2 for value in true_values)
    var_pred = mean((value - mean_pred) ** 2 for value in pred_values)
    cov = mean((x - mean_true) * (y - mean_pred) for x, y in zip(true_values, pred_values))
    denom = var_true + var_pred + ((mean_true - mean_pred) ** 2)
    if denom <= 0.0:
        return 0.0
    return clamp((2.0 * cov) / denom, -1.0, 1.0)


def stratified_bins(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    ordered = sorted((dict(row) for row in rows), key=lambda row: float(row.get("v", 0.0)))
    if not ordered:
        return {"low": [], "mid": [], "high": []}
    n = len(ordered)
    low_cut = max(1, int(round(n * 0.25)))
    high_start = min(n, max(low_cut, int(round(n * 0.75))))
    return {
        "low": ordered[:low_cut],
        "mid": ordered[low_cut:high_start],
        "high": ordered[high_start:],
    }


def stratified_sample(
    rows: Sequence[Mapping[str, Any]],
    n_items: int,
    rng: random.Random,
    ratios: Optional[Mapping[str, float]] = None,
) -> List[Dict[str, Any]]:
    if n_items <= 0:
        return []
    buckets = stratified_bins(rows)
    ratios = dict(ratios or {"low": 1.0 / 6.0, "mid": 4.0 / 6.0, "high": 1.0 / 6.0})
    selected: List[Dict[str, Any]] = []
    leftovers: List[Dict[str, Any]] = []
    for name in ("low", "mid", "high"):
        bucket = [dict(row) for row in buckets.get(name, [])]
        rng.shuffle(bucket)
        target = int(round(n_items * float(ratios.get(name, 0.0))))
        take = min(len(bucket), max(0, target))
        selected.extend(bucket[:take])
        leftovers.extend(bucket[take:])
    rng.shuffle(leftovers)
    remaining = max(0, min(n_items, len(rows)) - len(selected))
    selected.extend(leftovers[:remaining])
    rng.shuffle(selected)
    return selected[: min(n_items, len(selected))]


def row_word(row: Mapping[str, Any]) -> str:
    return normalize_word(row.get("word", _first_present(row, WORD_ALIASES)))


def row_vad(row: Mapping[str, Any]) -> Tuple[float, float, float]:
    if {"v", "a", "d"}.issubset(set(row.keys())):
        return (
            clamp(safe_float(row.get("v")), -1.0, 1.0),
            clamp(safe_float(row.get("a")), 0.0, 1.0),
            clamp(safe_float(row.get("d")), 0.0, 1.0),
        )
    return row_vad(normalize_warriner_records([row])[0])
