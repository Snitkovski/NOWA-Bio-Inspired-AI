"""Tests for ApprovalGate and Stage-2 hard constraints (spec §7, B6)."""

import time

import pytest

from nowa_body.approval_gate import ApprovalGate, ApprovalStatus
from nowa_body.hard_constraints import HardConstraintViolation, assert_stage2_invariant
from nowa_body.mcp_capability import CapabilityRisk, MCPCapability
from nowa_body.motor_adapter import ProposedAction
from nowa_body.tool_registry import MCPToolRegistry

from body_support import make_capability, make_mock_client


def _proposed(**overrides) -> ProposedAction:
    params = dict(
        action_id="act-1",
        agent_id="a",
        tool_id="mcp__test__do",
        tool_params={"x": 1},
        risk_level=CapabilityRisk.READ_ONLY,
        intent_summary="do(x=1)",
        affective_context={},
        requires_approval=False,
    )
    params.update(overrides)
    return ProposedAction(**params)


def test_high_write_cannot_bypass_approval():
    cap = MCPCapability(
        tool_id="x",
        server_name="y",
        display_name="z",
        description="",
        risk_level=CapabilityRisk.HIGH_WRITE,
        requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        assert_stage2_invariant(cap)


def test_irreversible_cannot_bypass_approval():
    cap = MCPCapability(
        tool_id="del",
        server_name="y",
        display_name="z",
        description="",
        risk_level=CapabilityRisk.IRREVERSIBLE,
        requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        assert_stage2_invariant(cap)


def test_route_raises_for_high_write_without_approval():
    client = make_mock_client()
    gate = ApprovalGate(mcp_executor=client.execute)
    proposed = _proposed(
        risk_level=CapabilityRisk.HIGH_WRITE,
        requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        gate.route(proposed)


def test_read_only_executes_immediately():
    client = make_mock_client()
    gate = ApprovalGate(mcp_executor=client.execute)
    proposed = _proposed(
        tool_id="mcp__test__get",
        risk_level=CapabilityRisk.READ_ONLY,
        requires_approval=False,
        tool_params={"q": 1},
    )
    record = gate.route(proposed)
    assert record.status == ApprovalStatus.APPROVED
    assert record.executed is True
    assert record.execution_result["status"] == "ok"
    assert client.tools["mcp__test__get"].call_log == [{"q": 1}]


def test_write_with_approval_is_queued_not_executed():
    client = make_mock_client()
    gate = ApprovalGate(mcp_executor=client.execute)
    proposed = _proposed(
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        requires_approval=True,
    )
    record = gate.route(proposed)
    assert record.status == ApprovalStatus.PENDING
    assert record.executed is False
    assert client.tools["mcp__test__do"].call_log == []


def test_human_approve_executes_and_reject_does_not():
    client = make_mock_client()
    gate = ApprovalGate(mcp_executor=client.execute)
    proposed = _proposed(
        action_id="need-ok",
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        requires_approval=True,
    )
    gate.route(proposed)
    approved = gate.decide(
        "need-ok", ApprovalStatus.APPROVED, decided_by="boss"
    )
    assert approved.executed is True
    assert approved.execution_result["status"] == "success"

    proposed2 = _proposed(
        action_id="need-no",
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        requires_approval=True,
    )
    gate.route(proposed2)
    rejected = gate.decide(
        "need-no",
        ApprovalStatus.REJECTED,
        decided_by="boss",
        rejection_reason="too expensive",
    )
    assert rejected.executed is False
    assert rejected.rejection_reason == "too expensive"


def test_expire_stale_marks_expired_without_execute():
    client = make_mock_client()
    gate = ApprovalGate(mcp_executor=client.execute, approval_timeout_hours=0.0)
    proposed = _proposed(
        risk_level=CapabilityRisk.MEDIUM_WRITE, requires_approval=True
    )
    gate.route(proposed)
    time.sleep(0.01)
    expired = gate.expire_stale()
    assert len(expired) == 1
    assert expired[0].status == ApprovalStatus.EXPIRED
    assert expired[0].executed is False


def test_capability_lookup_cannot_be_undercut_by_proposed_action():
    registry = MCPToolRegistry("a")
    registry.register(
        make_capability(
            tool_id="mcp__test__do",
            risk_level=CapabilityRisk.HIGH_WRITE,
            requires_approval=True,
            action_types=["do_thing"],
        )
    )
    gate = ApprovalGate(
        mcp_executor=make_mock_client().execute,
        capability_lookup=registry.get,
    )
    proposed = _proposed(
        risk_level=CapabilityRisk.READ_ONLY,
        requires_approval=False,
    )
    record = gate.route(proposed)
    assert record.status == ApprovalStatus.PENDING
    assert record.executed is False
