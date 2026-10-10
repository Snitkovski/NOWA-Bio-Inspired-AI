"""Deprecated MotorAdapter shim. Runtime uses SchemaBinder; keep class for old tests."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.proposed_action import ProposedAction, new_action_id, summarize_call  # noqa: E402,F401
from .mcp_capability import CapabilityRisk, MCPCapability
from .tool_registry import MCPToolRegistry


class MotorAdapter:
    """Generic body: ActionIntent → ProposedAction.

    Same discipline as the sandbox ProcurementMotorAdapter:
    - NEVER calls cognitive methods (hippocampus.activate, selector, step)
    - resolve() never raises — malformed observations yield None
    - reads hippocampus.experiences read-only, only in role subclasses
    """

    def __init__(self, tool_registry: MCPToolRegistry) -> None:
        self.tool_registry = tool_registry

    def resolve(
        self,
        action_type: str,
        observations: Dict[str, Any],
        hippocampus: Any = None,
    ) -> Optional[ProposedAction]:
        try:
            # Role subclasses (least-used supplier, etc.) may read this
            # read-only during _build_params. Never call activate/selector.
            self._hippocampus = hippocampus
            if not action_type or action_type == "wait_and_monitor":
                return None
            capability = self._capability_for_action(str(action_type))
            if capability is None:
                return None
            if not isinstance(observations, dict):
                return None
            params = self._build_params(capability, str(action_type), observations)
            if params is None:
                return None
            if not isinstance(params, dict):
                return None
            return ProposedAction(
                action_id=self._new_id(),
                agent_id=str(observations.get("agent_id", "")),
                tool_id=capability.tool_id,
                tool_params=params,
                risk_level=capability.risk_level,
                intent_summary=self._summarize(str(action_type), params),
                affective_context=dict(observations.get("affect_snapshot", {}) or {}),
                estimated_cost_impact=self._estimate_cost(capability, params),
                requires_approval=bool(capability.requires_approval),
            )
        except Exception:
            return None

    def _capability_for_action(self, action_type: str) -> Optional[MCPCapability]:
        matches = self.tool_registry.capabilities_for_action(action_type)
        if not matches:
            return None
        return sorted(matches, key=lambda c: c.tool_id)[0]

    def _build_params(
        self,
        capability: MCPCapability,
        action_type: str,
        observations: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Domain-specific parameter resolution. Subclass per role."""
        raise NotImplementedError(
            "Subclass MotorAdapter per role and implement _build_params; "
            "see ProcurementBodyMotorAdapter as the Phase 1 reference."
        )

    def _summarize(self, action_type: str, params: dict) -> str:
        return summarize_call(action_type, params)

    def _estimate_cost(self, capability: MCPCapability, params: dict) -> Optional[float]:
        del capability, params
        return None

    def _new_id(self) -> str:
        return new_action_id()
