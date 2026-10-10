"""Re-export platform ApprovalGate."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.approval_gate import (  # noqa: E402,F401
    ApprovalGate,
    ApprovalRecord,
    ApprovalStatus,
)

__all__ = ["ApprovalGate", "ApprovalRecord", "ApprovalStatus"]
