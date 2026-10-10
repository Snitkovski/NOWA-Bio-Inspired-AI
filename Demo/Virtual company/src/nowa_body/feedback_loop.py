"""Re-export platform feedback. ACTION label is always ``action:<tool_id>``."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.feedback import (  # noqa: E402,F401
    apply_feedback_to_agent,
    approval_to_reward,
    _resolve_action_label,
)

__all__ = [
    "apply_feedback_to_agent",
    "approval_to_reward",
    "_resolve_action_label",
]
