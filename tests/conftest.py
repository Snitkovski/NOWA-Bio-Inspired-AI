"""
Pytest configuration for NOWA tests
"""
import os
import sys
from pathlib import Path

# Stable-tier writers raise while awake. Production leaves this unset and
# logs a skip instead.
os.environ.setdefault("NOWA_STRICT_LEARNING", "1")

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
