"""Re-export platform hard constraints."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.hard_constraints import HardConstraintViolation, assert_stage2_invariant  # noqa: E402,F401

__all__ = ["HardConstraintViolation", "assert_stage2_invariant"]
