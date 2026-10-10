"""External approval barrier — the only place write tools may reach the world."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .hard_constraints import assert_stage2_invariant
from .mcp_capability import CapabilityRisk, MCPCapability
from .mcp_client import normalize_envelope
from .proposed_action import ProposedAction

_RISK_RANK = {
    CapabilityRisk.READ_ONLY: 0,
    CapabilityRisk.LOW_WRITE: 1,
    CapabilityRisk.MEDIUM_WRITE: 2,
    CapabilityRisk.HIGH_WRITE: 3,
    CapabilityRisk.IRREVERSIBLE: 4,
}


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


@dataclass
class ApprovalRecord:
    proposed_action: ProposedAction
    status: ApprovalStatus
    submitted_at: float
    decided_at: Optional[float] = None
    decided_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    modification_diff: Optional[Dict[str, Any]] = None
    executed: bool = False
    execution_result: Optional[Any] = None


class ApprovalGate:
    """Sole point through which write actions can reach the real outside world."""

    def __init__(
        self,
        mcp_executor: Callable[[str, dict], Any],
        notification_channel: Optional[Callable[[ApprovalRecord], None]] = None,
        approval_timeout_hours: float = 48.0,
        capability_lookup: Optional[Callable[[str], Optional[MCPCapability]]] = None,
    ) -> None:
        self.mcp_executor = mcp_executor
        self.notification_channel = notification_channel
        self.approval_timeout_hours = approval_timeout_hours
        self.capability_lookup = capability_lookup
        self.pending_queue: Dict[str, ApprovalRecord] = {}
        self.decided_log: List[ApprovalRecord] = []

    def route(self, proposed_action: ProposedAction) -> ApprovalRecord:
        capability = self._capability_for(proposed_action)
        assert_stage2_invariant(capability)

        if not capability.requires_approval:
            return self._execute_immediately(proposed_action)

        record = ApprovalRecord(
            proposed_action=proposed_action,
            status=ApprovalStatus.PENDING,
            submitted_at=time.time(),
        )
        self.pending_queue[proposed_action.action_id] = record
        if self.notification_channel:
            try:
                self.notification_channel(record)
            except Exception:
                pass
        return record

    def decide(
        self,
        action_id: str,
        decision: ApprovalStatus,
        decided_by: str,
        rejection_reason: Optional[str] = None,
        modified_params: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRecord:
        record = self.pending_queue.pop(action_id, None)
        if record is None:
            raise KeyError(f"No pending action with id {action_id}")

        record.status = decision
        record.decided_at = time.time()
        record.decided_by = decided_by
        record.rejection_reason = rejection_reason

        if decision == ApprovalStatus.MODIFIED and modified_params:
            record.modification_diff = dict(modified_params)
            record.proposed_action.tool_params.update(modified_params)

        if decision in (ApprovalStatus.APPROVED, ApprovalStatus.MODIFIED):
            record.execution_result = self._invoke_executor(record.proposed_action)
            record.executed = True

        self.decided_log.append(record)
        return record

    def _execute_immediately(self, proposed_action: ProposedAction) -> ApprovalRecord:
        result = self._invoke_executor(proposed_action)
        record = ApprovalRecord(
            proposed_action=proposed_action,
            status=ApprovalStatus.APPROVED,
            submitted_at=time.time(),
            decided_at=time.time(),
            decided_by="system:read_only_auto",
            executed=True,
            execution_result=result,
        )
        self.decided_log.append(record)
        return record

    def _invoke_executor(self, proposed_action: ProposedAction) -> Any:
        try:
            return normalize_envelope(
                self.mcp_executor(proposed_action.tool_id, proposed_action.tool_params)
            )
        except Exception as exc:
            return {"status": "error", "reason": f"executor_error:{exc}"}

    def expire_stale(self) -> List[ApprovalRecord]:
        now = time.time()
        expired: List[ApprovalRecord] = []
        for action_id, record in list(self.pending_queue.items()):
            age_hours = (now - record.submitted_at) / 3600.0
            if age_hours > self.approval_timeout_hours:
                record.status = ApprovalStatus.EXPIRED
                record.decided_at = now
                expired.append(record)
                del self.pending_queue[action_id]
                self.decided_log.append(record)
        return expired

    def _capability_for(self, proposed_action: ProposedAction) -> MCPCapability:
        looked_up = None
        if self.capability_lookup is not None:
            try:
                looked_up = self.capability_lookup(proposed_action.tool_id)
            except Exception:
                looked_up = None
        risk = proposed_action.risk_level
        requires_approval = bool(proposed_action.requires_approval)
        if looked_up is not None:
            looked_rank = _RISK_RANK.get(looked_up.risk_level, 0)
            proposed_rank = _RISK_RANK.get(risk, 0)
            if looked_rank >= proposed_rank:
                risk = looked_up.risk_level
            requires_approval = requires_approval or bool(looked_up.requires_approval)
            return MCPCapability(
                tool_id=looked_up.tool_id,
                server_name=looked_up.server_name,
                display_name=looked_up.display_name,
                description=looked_up.description,
                risk_level=risk,
                domain_tags=list(looked_up.domain_tags),
                requires_approval=requires_approval,
                action_types=list(looked_up.action_types),
            )
        return MCPCapability(
            tool_id=proposed_action.tool_id,
            server_name="",
            display_name="",
            description="",
            risk_level=risk,
            requires_approval=requires_approval,
        )
