"""Pytest setup for colony simulation tests."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))
