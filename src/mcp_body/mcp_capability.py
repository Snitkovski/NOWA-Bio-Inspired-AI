"""MCP tool capability contract — one 'organ' of a NOWA agent body."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CapabilityRisk(Enum):
    """Risk class of a tool — drives approval routing."""

    READ_ONLY = "read_only"
    LOW_WRITE = "low_write"
    MEDIUM_WRITE = "medium_write"
    HIGH_WRITE = "high_write"
    IRREVERSIBLE = "irreversible"


def parse_risk(value: Any, default: CapabilityRisk = CapabilityRisk.HIGH_WRITE) -> CapabilityRisk:
    """Accept a CapabilityRisk, its ``value`` string, or its enum name.

    Discovery overrides arrive from YAML, so ``"medium_write"`` and
    ``"MEDIUM_WRITE"`` must both resolve. Unknown values fall back to
    ``default`` rather than crashing registration.
    """
    if isinstance(value, CapabilityRisk):
        return value
    text = str(value or "").strip().lower()
    if not text:
        return default
    for risk in CapabilityRisk:
        if text == risk.value or text == risk.name.lower():
            return risk
    return default


@dataclass
class MCPCapability:
    """Universal description of one MCP tool as an agent organ.

    Filled at MCP-server registration time. Not hardcoded to 1C, email, or
    any other concrete system — those are instances of this description.

    ``requires_approval`` defaults to True. HIGH_WRITE / IRREVERSIBLE must
    keep it True: ``assert_stage2_invariant`` in ``ApprovalGate.route`` is
    the architectural enforcement (spec B6), so an invalid combination is
    representable as data and is rejected at the gate rather than silently
    rewritten at construction.
    """

    tool_id: str
    server_name: str
    display_name: str
    description: str
    risk_level: CapabilityRisk
    domain_tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = True
    cost_impact_estimate: Optional[str] = None
    max_autonomous_value: Optional[float] = None
    action_types: List[str] = field(default_factory=list)
    """DEPRECATED (spec §5.3). ``tool_id`` *is* the action channel of the
    basal ganglia, so runtime selection never consults this field. It is kept
    only so Phase-1 configs and the deprecated
    ``MCPToolRegistry.capabilities_for_action`` index stay loadable; new roles
    must leave it empty."""
    poll: bool = False
    """When True, the employee host calls this READ organ on the sensor interval."""
    poll_defaults: Dict[str, Any] = field(default_factory=dict)
    """Arguments used when the host polls this sensor (required fields, etc.)."""
