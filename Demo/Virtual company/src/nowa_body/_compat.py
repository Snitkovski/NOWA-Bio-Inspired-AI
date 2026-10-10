"""Bootstrap repo ``src/`` onto ``sys.path``, then reuse platform helpers.

Do not copy Path/Event fallbacks, clamp, or outcome mapping here.
Those live in ``src/mcp_body/_compat.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path as _FsPath


def ensure_core_src_on_path() -> None:
    """Make the repository-level NOWA core modules importable when available."""
    here = _FsPath(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src" / "agent.py"
        if candidate.exists():
            core_src = str(parent / "src")
            if core_src not in sys.path:
                sys.path.insert(0, core_src)
            return


ensure_core_src_on_path()

from mcp_body._compat import (  # noqa: E402,F401
    FALLBACK_OUTCOME_VECTORS,
    apply_impulses,
    clamp,
    impulse_to_vector,
    is_number,
    load_affective_types,
    load_experience_types,
    normalize_status,
    outcome_impulse,
    safe_float,
)

__all__ = [
    "FALLBACK_OUTCOME_VECTORS",
    "apply_impulses",
    "clamp",
    "ensure_core_src_on_path",
    "impulse_to_vector",
    "is_number",
    "load_affective_types",
    "load_experience_types",
    "normalize_status",
    "outcome_impulse",
    "safe_float",
]
