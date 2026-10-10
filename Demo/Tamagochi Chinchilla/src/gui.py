"""
Minimal GUI facade for headless tests and optional integrations.

The real rendering is handled by pygame_engine; this class provides a
lightweight API that tests and future UI layers can depend on.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional


class ChinchillaGUI:
    """Lightweight GUI adapter used in tests."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.stats: Dict[str, Any] = {}
        self.affect: Dict[str, Any] = {}
        self.fps: float = 0.0

    def update_stats(self, stats: Dict[str, Any]) -> None:
        self.stats = dict(stats or {})

    def update_affect(self, affect: Dict[str, Any]) -> None:
        self.affect = dict(affect or {})

    def update_fps(self, fps: float) -> None:
        try:
            self.fps = float(fps)
        except Exception:
            self.fps = 0.0

    def render(self) -> None:
        """No-op placeholder for GUI render loop."""
        return

