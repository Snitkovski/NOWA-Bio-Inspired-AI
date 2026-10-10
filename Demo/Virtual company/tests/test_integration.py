"""End-to-end body-layer cycle on MockMCP (spec §12 DoD, patch v1.1)."""

from __future__ import annotations

from pathlib import Path

from nowa_body.approval_gate import ApprovalGate, ApprovalStatus
from nowa_body.business_event_encoder import BusinessEventEncoder
from nowa_body.business_hippocampus_seeder import BusinessHippocampusSeeder
from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.mock_mcp import MockMCPClient, MockMCPTool
from nowa_body.runtime import BusinessAgentRuntime
from nowa_body.sleep_scheduler import SleepScheduler
from nowa_body.tool_registry import MCPToolRegistry
from nowa_roles.procurement.event_classifier import classify_procurement_events
from nowa_roles.procurement.seed_corpus import PROCUREMENT_SEED_EPISODES

from body_support import (
    make_capability,
    make_test_agent_that_always_acts,
    make_test_runtime,
)


def test_full_cycle_observe_decide_resolve_gate_feedback_on_mock_mcp():
    agent = make_test_agent_that_always_acts()
    BusinessHippocampusSeeder(PROCUREMENT_SEED_EPISODES).seed_agent(agent)
    n_seeded = len(agent.hippocampus.experiences)

    runtime = make_test_runtime(agent=agent, requires_approval=False)
    result = runtime.run_cycle({
        "agent_id": "buyer",
        "tool_results": {"mcp__test__get": {"status": "ok"}},
        "tool_params": {"sku": "a"},
    })
    assert result["proposed"] is not None
    assert result["approval_status"] == ApprovalStatus.APPROVED.value
    assert result["executed"] is True
    assert len(agent.hippocampus.experiences) == n_seeded + 1
    assert agent.affective_space.step_calls  # success affect applied
    assert result["slept"] is False


def test_mock_mcp_covers_read_and_write():
    client = MockMCPClient()
    client.register(MockMCPTool("read", lambda p: {"status": "ok", "n": 1}))
    client.register(MockMCPTool("write", lambda p: {"status": "success", "id": p.get("id")}))
    assert client.execute("read", {})["status"] == "ok"
    assert client.execute("write", {"id": "po-1"})["id"] == "po-1"
    assert client.execute("missing", {})["status"] == "error"


def test_write_timeout_does_not_crash_runtime():
    agent = make_test_agent_that_always_acts()
    runtime = make_test_runtime(
        agent=agent, requires_approval=False, write_status="timeout"
    )
    result = runtime.run_cycle({"agent_id": "a", "tool_results": {}})
    assert result["executed"] is True
    assert result["record"].execution_result["status"] == "error"
    assert "timeout" in str(result["record"].execution_result.get("reason", ""))


def test_rejected_write_then_human_reject_is_stable():
    agent = make_test_agent_that_always_acts()
    runtime = make_test_runtime(
        agent=agent,
        requires_approval=False,
        write_status="rejected",
    )
    result = runtime.run_cycle({"agent_id": "a", "tool_results": {}})
    assert result["executed"] is True
    assert result["record"].execution_result["status"] == "rejected"
    stored = agent.hippocampus.experiences[-1]
    names = [getattr(ev, "name", str(ev)) for ev in stored.path.events]
    assert "result:failure" in names


def test_procurement_body_cycle_with_stock_observations():
    agent = make_test_agent_that_always_acts("mcp__1c__create_purchase_order")
    registry = MCPToolRegistry("buyer")
    registry.register(
        make_capability(
            tool_id="mcp__1c__get_stock_levels",
            risk_level=CapabilityRisk.READ_ONLY,
            requires_approval=False,
            action_types=[],
        )
    )
    registry.register(
        make_capability(
            tool_id="mcp__1c__create_purchase_order",
            risk_level=CapabilityRisk.MEDIUM_WRITE,
            requires_approval=False,
            action_types=[],
            input_schema={
                "type": "object",
                "required": ["supplier_id", "sku", "qty"],
                "properties": {
                    "supplier_id": {"type": "string"},
                    "sku": {"type": "string"},
                    "qty": {"type": "number"},
                },
            },
        )
    )
    client = MockMCPClient()
    client.register(
        MockMCPTool("mcp__1c__get_stock_levels", lambda p: {"status": "ok"})
    )
    client.register(
        MockMCPTool(
            "mcp__1c__create_purchase_order",
            lambda p: {"status": "accepted", "order": dict(p)},
        )
    )
    runtime = BusinessAgentRuntime(
        agent=agent,
        tool_registry=registry,
        approval_gate=ApprovalGate(
            mcp_executor=client.execute, capability_lookup=registry.get
        ),
        encoder=BusinessEventEncoder({
            "stock_critical_low": {
                "valence": -0.7, "arousal": 0.8, "tags": ["procurement"],
            }
        }),
        sleep_scheduler=SleepScheduler(min_ticks_between_sleep=10_000),
        event_classifier=classify_procurement_events,
    )
    observations = {
        "agent_id": "buyer",
        "tool_results": {
            "mcp__1c__get_stock_levels": {
                "stock": {
                    "sku_a": {
                        "quantity": 0.0,
                        "reorder_point": 40.0,
                        "below_reorder_point": True,
                        "suggested_qty": 30.0,
                        "base_demand_per_day": 1.0,
                    }
                }
            }
        },
        "stock": {
            "sku_a": {
                "quantity": 0.0,
                "reorder_point": 40.0,
                "below_reorder_point": True,
                "suggested_qty": 30.0,
                "base_demand_per_day": 1.0,
            }
        },
        "suppliers": {
            "acme": {"reliability": 0.95, "unit_price": 8.0},
        },
        "budget": {"remaining": 5000.0},
    }
    result = runtime.run_cycle(observations)
    assert result["proposed"] is not None
    assert result["proposed"].tool_params["supplier_id"] == "acme"
    assert result["executed"] is True
    assert client.tools["mcp__1c__create_purchase_order"].call_log


def test_runtime_does_not_hold_mcp_client_attribute():
    runtime = make_test_runtime()
    assert not hasattr(runtime, "mcp_client")
    assert not hasattr(runtime, "mcp_executor")


def test_nowa_body_does_not_import_nowa_sandbox():
    root = Path(__file__).resolve().parents[1] / "src" / "nowa_body"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "import nowa_sandbox" in text or "from nowa_sandbox" in text:
            offenders.append(str(path.relative_to(root.parent)))
    assert offenders == []


def test_sleep_scheduler_can_run_after_decision_cycle():
    agent = make_test_agent_that_always_acts()
    runtime = make_test_runtime(
        agent=agent,
        sleep_scheduler=SleepScheduler(
            circadian_window=(2, 5), min_ticks_between_sleep=0
        ),
    )
    from datetime import datetime

    result = runtime.run_cycle(
        {"agent_id": "a", "tool_results": {}},
        now=datetime(2026, 1, 1, 3, 0),
    )
    assert result["slept"] is True
    assert result["sleep_reason"] == "circadian"
    assert agent.sleep_calls == 1
