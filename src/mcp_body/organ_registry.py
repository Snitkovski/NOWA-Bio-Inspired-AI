"""Per-agent registry of MCP organs (a filtered view over shared transport)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .mcp_capability import CapabilityRisk, MCPCapability, parse_risk
from .mcp_client import list_tool_descriptors, make_tool_id
from .risk_classifier import classify_risk_heuristic

_APPROVAL_FORCED_RISKS = (CapabilityRisk.HIGH_WRITE, CapabilityRisk.IRREVERSIBLE)


class MCPToolRegistry:
    """Stores organ descriptions for one agent (one employee).

    Each agent has its own registry — that is part of sovereignty: a buyer
    does not see the accountant's tools. The MCP transport underneath MAY
    be shared; this object is the per-agent slice of visibility.

    READ_ONLY organs are sensors; everything else is a muscle and therefore a
    basal-ganglia action channel (spec §7.1).
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._capabilities: Dict[str, MCPCapability] = {}
        self._by_action_type: Dict[str, List[str]] = {}

    def register(self, capability: MCPCapability) -> None:
        """Register or replace a capability and rebuild its action-type index."""
        old = self._capabilities.get(capability.tool_id)
        if old is not None:
            self._drop_from_index(capability.tool_id, old.action_types)
        self._capabilities[capability.tool_id] = capability
        for action_type in capability.action_types or []:
            label = str(action_type).strip()
            if not label:
                continue
            bucket = self._by_action_type.setdefault(label, [])
            if capability.tool_id not in bucket:
                bucket.append(capability.tool_id)

    def _drop_from_index(self, tool_id: str, action_types: List[str]) -> None:
        for action_type in action_types or []:
            bucket = self._by_action_type.get(action_type)
            if not bucket:
                continue
            self._by_action_type[action_type] = [
                tid for tid in bucket if tid != tool_id
            ]
            if not self._by_action_type[action_type]:
                del self._by_action_type[action_type]

    def register_from_mcp_discovery(
        self,
        mcp_client: Any,
        server_id: str,
        tool_overrides: Optional[dict] = None,
    ) -> int:
        """Turn one server's ``tools/list`` into organs. Returns the count.

        This is the whole role-onboarding mechanism (spec §6.1): a YAML entry
        for the server plus optional per-tool overrides. No Python class is
        ever written per server or per role.

        Overrides are keyed by the raw MCP tool name and may set
        ``risk_level`` / ``requires_approval`` / ``domain_tags`` /
        ``display_name`` / ``input_schema``. They may not smuggle in an
        adapter. ``requires_approval`` cannot be lowered for HIGH_WRITE or
        IRREVERSIBLE organs.

        Raises:
            ValueError: two tools map onto the same ``tool_id`` — a
                configuration error, never silently resolved.
        """
        overrides = dict(tool_overrides or {})
        descriptors = list_tool_descriptors(mcp_client)
        registered = 0
        seen_in_this_pass: set = set()

        for descriptor in descriptors:
            name = str(descriptor.name or "").strip()
            if not name:
                continue
            tool_id = make_tool_id(server_id, name)
            if tool_id in seen_in_this_pass or tool_id in self._capabilities:
                raise ValueError(
                    f"tool_id collision for {tool_id!r} on server {server_id!r}: "
                    f"two MCP tools sanitize to the same organ id"
                )
            seen_in_this_pass.add(tool_id)

            override = overrides.get(name) or overrides.get(tool_id) or {}
            if not isinstance(override, dict):
                override = {}

            heuristic = classify_risk_heuristic(name, descriptor.description)
            risk = parse_risk(override.get("risk_level"), default=heuristic) \
                if override.get("risk_level") is not None else heuristic

            self.register(
                MCPCapability(
                    tool_id=tool_id,
                    server_name=str(server_id),
                    display_name=str(override.get("display_name") or name),
                    description=str(descriptor.description or ""),
                    risk_level=risk,
                    domain_tags=[str(tag) for tag in (override.get("domain_tags") or [])],
                    input_schema=dict(override.get("input_schema") or descriptor.input_schema or {}),
                    output_schema=dict(descriptor.output_schema or {}),
                    requires_approval=self._resolve_requires_approval(
                        risk, override.get("requires_approval")
                    ),
                    cost_impact_estimate=override.get("cost_impact_estimate"),
                    max_autonomous_value=override.get("max_autonomous_value"),
                )
            )
            registered += 1
        return registered

    @staticmethod
    def _resolve_requires_approval(risk: CapabilityRisk, override: Any) -> bool:
        if risk in _APPROVAL_FORCED_RISKS:
            return True
        if override is not None:
            return bool(override)
        return risk != CapabilityRisk.READ_ONLY

    def get(self, tool_id: str) -> Optional[MCPCapability]:
        return self._capabilities.get(tool_id)

    def list_all(self) -> List[MCPCapability]:
        return list(self._capabilities.values())

    def list_by_risk(self, risk: CapabilityRisk) -> List[MCPCapability]:
        return [c for c in self._capabilities.values() if c.risk_level == risk]

    def list_by_domain(self, domain_tag: str) -> List[MCPCapability]:
        return [c for c in self._capabilities.values() if domain_tag in c.domain_tags]

    def sensory_capabilities(self) -> List[MCPCapability]:
        """READ_ONLY tools — what the agent can use to look at the world."""
        return self.list_by_risk(CapabilityRisk.READ_ONLY)

    def motor_capabilities(self) -> List[MCPCapability]:
        """Everything that changes the outside world (= the BG channels)."""
        return [
            c for c in self._capabilities.values()
            if c.risk_level != CapabilityRisk.READ_ONLY
        ]

    def capabilities_for_action(self, action_type: str) -> List[MCPCapability]:
        """DEPRECATED (spec §5.3): ``tool_id`` is the action channel.

        Kept so Phase-1 configs that still carry ``action_types`` remain
        loadable. Nothing in the runtime path calls this.
        """
        tool_ids = self._by_action_type.get(action_type, [])
        return [self._capabilities[tid] for tid in tool_ids if tid in self._capabilities]


OrganRegistry = MCPToolRegistry
