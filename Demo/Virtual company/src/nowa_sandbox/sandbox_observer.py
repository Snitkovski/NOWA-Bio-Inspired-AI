"""Passive observer for sandbox training diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class SandboxObserver:
    """Analogue of PopulationObserver from the evolutionary project.

    Records training history for later analysis and never interferes with the
    training process itself.
    """

    def __init__(self):
        self.snapshots: List[Any] = []

    def record(self, quarter_result: Any) -> None:
        self.snapshots.append(quarter_result)

    def record_all(self, quarter_results: Any) -> None:
        for quarter_result in quarter_results or []:
            self.record(quarter_result)

    def to_records(self) -> List[Dict[str, Any]]:
        return [self._as_record(snap) for snap in self.snapshots]

    def to_json(self, path: str) -> None:
        output_path = Path(path)
        if output_path.parent and not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_records(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _as_record(snap: Any) -> Dict[str, Any]:
        if isinstance(snap, dict):
            return dict(snap)
        fitness = getattr(snap, "fitness", None)
        return {
            "quarter_index": getattr(snap, "quarter_index", None),
            "fitness": fitness.as_dict() if hasattr(fitness, "as_dict") else {},
            "n_days": getattr(fitness, "n_days", None),
            "n_decisions": getattr(fitness, "n_orders", None),
            "graduation": getattr(snap, "graduation", {}),
            "non_regression": getattr(snap, "non_regression", None),
            "world_summary": getattr(snap, "world_summary", {}),
            "processing_time_s": getattr(snap, "processing_time_s", None),
        }

    def plot_progress(self):
        """Plot per-criterion progress across quarters.

        Live charts live in the lab GUI (``gui_app`` / ``FitnessChart``).
        Use ``to_records()`` to feed external plotters.
        """
        raise NotImplementedError(
            "use nowa_sandbox.gui_app (FitnessChart) or to_records() + your plotter"
        )


__all__ = ["SandboxObserver"]
