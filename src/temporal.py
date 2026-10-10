"""
Temporal levels implementation for NOWA Plan A: Temporal Depth.

Provides a minimal `TemporalLevels` helper that records T0 snapshots,
maintains a T1 sliding window for short-term trends, computes a T2 baseline
via consolidation, and exposes simple T3 attractor estimates.

This module is intentionally lightweight and designed to integrate with
`AffectiveState.snapshot()` dictionaries.
"""
from collections import deque
from statistics import mean
from typing import Deque, Dict, Any


class TemporalLevels:
    """Lightweight temporal levels manager.

    - T0: last snapshot (dict of affect values)
    - T1: sliding window of last N snapshots
    - T2: consolidated baseline (slow-moving average)
    - T3: attractors (very slow moving averages)
    """

    def __init__(self, window_size: int = 10, attractor_alpha: float = 0.01):
        self.window_size = window_size
        self.t1: Deque[Dict[str, float]] = deque(maxlen=window_size)
        self.t0: Dict[str, float] = {}
        self.t2: Dict[str, float] = {}
        self.t3: Dict[str, float] = {}
        self.attractor_alpha = attractor_alpha

    def _micro_consolidate(self):
        """
        Lightweight baseline drift during waking.
        NOT sleep, NOT learning.
        """
        mean_vals = self.t1_mean()
        for k, v in mean_vals.items():
            prev = self.t2.get(k, 0.0)
            # Very slow update
            self.t2[k] = prev * 0.9 + v * 0.1

    def log(self, snapshot: Dict[str, Any]):
        """Log a new T0 snapshot and append to T1 window.

        Snapshot is expected to contain numeric keys: valence, arousal, threat, curiosity
        """
        # T0 update
        self.t0 = {k: float(snapshot.get(k, 0.0)) for k in ["valence", "arousal", "threat", "curiosity"]}
        # Append to T1
        self.t1.append(self.t0.copy())
        # Micro consolidation during waking when T1 window is full
        if len(self.t1) == self.window_size:
            self._micro_consolidate()

    def t1_mean(self) -> Dict[str, float]:
        """Return mean over T1 window for each affect dimension."""
        if not self.t1:
            return {k: 0.0 for k in ["valence", "arousal", "threat", "curiosity"]}
        keys = ["valence", "arousal", "threat", "curiosity"]
        result = {}
        for k in keys:
            result[k] = mean([s.get(k, 0.0) for s in self.t1])
        return result

    def trend(self) -> Dict[str, float]:
        """Compute simple trend as difference between last and first in window."""
        if len(self.t1) < 2:
            return {k: 0.0 for k in ["valence", "arousal", "threat", "curiosity"]}
        first = self.t1[0]
        last = self.t1[-1]
        return {k: last.get(k, 0.0) - first.get(k, 0.0) for k in first}

    def consolidate(self):
        """Consolidate T1 into T2 (baseline) using a moving average.

        This simulates periodic consolidation (e.g., during sleep).
        """
        mean_vals = self.t1_mean()
        # Update t2 as slow-moving average
        for k, v in mean_vals.items():
            prev = self.t2.get(k, v)
            # simple smoothing: new = 0.5 * prev + 0.5 * mean
            self.t2[k] = prev * 0.5 + v * 0.5
            # update t3 attractor as very slow exponential
            prev3 = self.t3.get(k, self.t2[k])
            self.t3[k] = prev3 * (1.0 - self.attractor_alpha) + self.t2[k] * self.attractor_alpha

    def sleep(self):
        """Simulate sleep: reduce T1 variance and consolidate to T2/T3."""
        # Consolidate
        self.consolidate()
        # Damp T1 values towards baseline to reduce variance
        if not self.t1:
            return
        for i, s in enumerate(self.t1):
            for k in s:
                s[k] = s[k] * 0.7 + self.t2.get(k, 0.0) * 0.3

    def get_levels(self) -> Dict[str, Dict[str, float]]:
        """Return a snapshot of all temporal levels."""
        return {
            "T0": dict(self.t0),
            "T1_mean": self.t1_mean(),
            "T2_baseline": dict(self.t2),
            "T3_attractor": dict(self.t3)
        }
