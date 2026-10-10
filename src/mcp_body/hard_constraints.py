"""Hard constraints that live outside the cognitive loop and cannot be configured away."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .mcp_capability import CapabilityRisk

if TYPE_CHECKING:
    from .mcp_capability import MCPCapability


class HardConstraintViolation(Exception):
    """Raised when a Stage-2 architectural invariant is violated."""


def assert_stage2_invariant(capability: "MCPCapability") -> None:
    """Reject HIGH_WRITE / IRREVERSIBLE tools that skip human approval.

    Called by ``ApprovalGate.route()`` on every pass. This is not a business
    rule: it is protection against bugs, prompt injection, and emergent
    agent behaviour. It lives outside the cognitive loop and cannot be
    overridden by an agent decision, even if the agent 'decided' it was right.
    """
    if capability.risk_level in (
        CapabilityRisk.HIGH_WRITE,
        CapabilityRisk.IRREVERSIBLE,
    ):
        if not capability.requires_approval:
            raise HardConstraintViolation(
                f"Capability {capability.tool_id} с риском {capability.risk_level} "
                f"не может иметь requires_approval=False на Stage 2. "
                f"Это архитектурная защита, не подлежит переопределению "
                f"конфигурацией агента."
            )
