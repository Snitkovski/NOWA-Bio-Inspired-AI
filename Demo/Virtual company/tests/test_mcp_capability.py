"""Tests for MCPCapability (Phase 1 spec §3, parent spec §2.2)."""

from nowa_body.mcp_capability import CapabilityRisk, MCPCapability


def test_capability_defaults_and_action_types():
    cap = MCPCapability(
        tool_id="mcp__1c__get_stock_levels",
        server_name="1c_erp",
        display_name="Get stock",
        description="read stock",
        risk_level=CapabilityRisk.READ_ONLY,
    )
    assert cap.requires_approval is True
    assert cap.action_types == []
    assert cap.domain_tags == []
    assert cap.input_schema == {}
    assert cap.max_autonomous_value is None


def test_action_types_are_stored():
    cap = MCPCapability(
        tool_id="mcp__email__send",
        server_name="email",
        display_name="Send",
        description="send mail",
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        action_types=["notify_supplier_urgent", "send_followup"],
    )
    assert cap.action_types == ["notify_supplier_urgent", "send_followup"]


def test_high_write_can_be_constructed_with_requires_approval_false():
    """Invalid combo is representable so assert_stage2_invariant can catch it."""
    cap = MCPCapability(
        tool_id="x",
        server_name="y",
        display_name="z",
        description="",
        risk_level=CapabilityRisk.HIGH_WRITE,
        requires_approval=False,
    )
    assert cap.requires_approval is False
    assert cap.risk_level is CapabilityRisk.HIGH_WRITE
