"""The only structure that may cross the ApprovalGate into the outside world."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .mcp_capability import CapabilityRisk


@dataclass
class ProposedAction:
    """One bound muscle contraction, not yet executed.

    Built by the runtime from ``tool_id`` + ``SchemaBinder`` output. There is
    no per-role Python producing this (spec §5.3): the mind chose the organ,
    the binder chose the parameters.
    """

    action_id: str
    agent_id: str
    tool_id: str
    tool_params: Dict[str, Any]
    risk_level: CapabilityRisk
    intent_summary: str
    affective_context: Dict[str, float] = field(default_factory=dict)
    estimated_cost_impact: Optional[float] = None
    requires_approval: bool = True


def new_action_id() -> str:
    return str(uuid.uuid4())


def summarize_call(tool_id: str, params: Optional[Dict[str, Any]]) -> str:
    joined = ", ".join(f"{key}={value}" for key, value in (params or {}).items())
    return f"{tool_id}({joined})"
