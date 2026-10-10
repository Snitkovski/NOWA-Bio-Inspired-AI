"""Tests for MCPToolRegistry, including the action_type index (spec §15)."""

from nowa_body.mcp_capability import CapabilityRisk, MCPCapability
from nowa_body.tool_registry import MCPToolRegistry


def _cap(tool_id, risk=CapabilityRisk.READ_ONLY, **kwargs):
    return MCPCapability(
        tool_id=tool_id,
        server_name="s",
        display_name=tool_id,
        description="",
        risk_level=risk,
        **kwargs,
    )


def test_register_and_get_are_per_agent():
    a = MCPToolRegistry("agent_a")
    b = MCPToolRegistry("agent_b")
    a.register(_cap("mcp__1c__get_stock_levels", domain_tags=["procurement"]))
    assert a.get("mcp__1c__get_stock_levels") is not None
    assert b.get("mcp__1c__get_stock_levels") is None
    assert a.agent_id == "agent_a"


def test_list_by_risk_and_domain_and_sensory_motor_split():
    registry = MCPToolRegistry("buyer")
    registry.register(_cap("read", CapabilityRisk.READ_ONLY, domain_tags=["procurement"]))
    registry.register(
        _cap("write", CapabilityRisk.MEDIUM_WRITE, domain_tags=["procurement"])
    )
    registry.register(_cap("pay", CapabilityRisk.HIGH_WRITE, domain_tags=["finance"]))
    assert [c.tool_id for c in registry.sensory_capabilities()] == ["read"]
    assert sorted(c.tool_id for c in registry.motor_capabilities()) == ["pay", "write"]
    assert [c.tool_id for c in registry.list_by_domain("finance")] == ["pay"]
    assert registry.list_by_risk(CapabilityRisk.HIGH_WRITE)[0].tool_id == "pay"


def test_capabilities_for_action_uses_index():
    registry = MCPToolRegistry("buyer")
    registry.register(
        _cap(
            "mcp__email__send",
            CapabilityRisk.MEDIUM_WRITE,
            action_types=["notify_supplier_urgent", "send_followup"],
        )
    )
    registry.register(
        _cap(
            "mcp__1c__create_purchase_order",
            CapabilityRisk.MEDIUM_WRITE,
            action_types=["place_order_reliable_supplier"],
        )
    )
    matches = registry.capabilities_for_action("notify_supplier_urgent")
    assert [c.tool_id for c in matches] == ["mcp__email__send"]
    assert registry.capabilities_for_action("unknown") == []


def test_reregister_rebuilds_action_index():
    registry = MCPToolRegistry("buyer")
    registry.register(_cap("t1", action_types=["a", "b"]))
    registry.register(_cap("t1", action_types=["c"]))
    assert registry.capabilities_for_action("a") == []
    assert registry.capabilities_for_action("b") == []
    assert [c.tool_id for c in registry.capabilities_for_action("c")] == ["t1"]


def test_register_from_mcp_discovery():
    from nowa_body._compat import ensure_core_src_on_path

    ensure_core_src_on_path()
    from mcp_body.mcp_client import MCPToolDescriptor

    class _Transport:
        def list_tools(self):
            return [
                MCPToolDescriptor("get_stock_levels", "READ stock", {}),
                MCPToolDescriptor("create_purchase_order", "WRITE order", {}),
            ]

        def call_tool(self, name, arguments):
            return {"status": "ok"}

    registry = MCPToolRegistry("buyer")
    count = registry.register_from_mcp_discovery(_Transport(), "1c")
    assert count == 2
    assert registry.get("mcp__1c__get_stock_levels") is not None
    motors = registry.motor_capabilities()
    assert [c.tool_id for c in motors] == ["mcp__1c__create_purchase_order"]
