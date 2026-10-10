"""Re-export platform runtime. Deprecated host kwarg ``motor_adapter`` is ignored."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.runtime import WAIT_AND_MONITOR, BusinessAgentRuntime  # noqa: E402,F401

__all__ = ["WAIT_AND_MONITOR", "BusinessAgentRuntime"]
