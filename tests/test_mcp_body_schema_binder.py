"""SchemaBinder, discovery, and runtime path without MotorAdapter (spec §10)."""

from __future__ import annotations

import inspect

import pytest

from mcp_body import (
    ApprovalGate,
    BusinessAgentRuntime,
    CapabilityRisk,
    GenericEncoder,
    HardConstraintViolation,
    MCPCapability,
    MCPToolDescriptor,
    MCPToolRegistry,
    SchemaBinder,
    WAIT_AND_MONITOR,
    WorldState,
    make_tool_id,
)
from mcp_body.approval_gate import ApprovalStatus
from mcp_body.mcp_client import split_tool_id
from mcp_body.runtime import BusinessAgentRuntime as RuntimeClass


class _MockTransport:
    def __init__(self, tools):
        self._tools = list(tools)

    def list_tools(self):
        return list(self._tools)

    def call_tool(self, name, arguments):
        return {"status": "ok", "name": name, "arguments": dict(arguments or {})}


def _order_schema():
    return {
        "type": "object",
        "required": ["supplier_id", "sku", "qty"],
        "properties": {
            "supplier_id": {"type": "string"},
            "sku": {"type": "string"},
            "qty": {"type": "number"},
        },
    }


def _capability(**overrides):
    params = dict(
        tool_id="mcp__1c__create_purchase_order",
        server_name="1c",
        display_name="Create purchase order",
        description="WRITE purchase order",
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        requires_approval=True,
        input_schema=_order_schema(),
    )
    params.update(overrides)
    return MCPCapability(**params)


def _world_with_suppliers_and_stock():
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_suppliers",
        {
            "status": "ok",
            "suppliers": {
                "acme": {
                    "unit_price": 8.0,
                    "reliability": 0.95,
                    "lead_time_days": 3,
                },
                "cheapco": {
                    "unit_price": 3.5,
                    "reliability": 0.40,
                    "lead_time_days": 12,
                },
            },
        },
    )
    state.update_from_read(
        "mcp__1c__get_stock_levels",
        {
            "status": "ok",
            "stock": {
                "SKU1": {"qty": 1.0},
                "SKU2": {"qty": 10.0},
            },
        },
    )
    return state


def test_discovery_four_mock_tools_three_sensors_one_motor():
    transport = _MockTransport(
        [
            MCPToolDescriptor("get_stock_levels", "READ stock", {}),
            MCPToolDescriptor("get_suppliers", "READ suppliers", {}),
            MCPToolDescriptor("get_budget", "READ budget", {}),
            MCPToolDescriptor(
                "create_purchase_order",
                "WRITE purchase order",
                _order_schema(),
            ),
        ]
    )
    registry = MCPToolRegistry("buyer")
    count = registry.register_from_mcp_discovery(transport, "1c")
    assert count == 4
    assert len(registry.sensory_capabilities()) == 3
    motors = registry.motor_capabilities()
    assert len(motors) == 1
    assert motors[0].tool_id == "mcp__1c__create_purchase_order"
    assert motors[0].risk_level == CapabilityRisk.MEDIUM_WRITE


def test_binder_schema_plus_world_fills_params():
    binder = SchemaBinder()
    params = binder.bind(_capability(), _world_with_suppliers_and_stock())
    assert params is not None
    assert params["supplier_id"] in {"acme", "cheapco"}
    assert params["sku"] in {"SKU1", "SKU2"}
    assert float(params["qty"]) in {1.0, 10.0}


def test_binder_prefers_suggested_qty_over_zero_stock():
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_suppliers",
        {
            "status": "ok",
            "suppliers": {
                "acme": {"unit_price": 8.0, "reliability": 0.95, "lead_time_days": 3},
            },
        },
    )
    state.update_from_read(
        "mcp__drivemcp__get_stock_levels",
        {
            "status": "ok",
            "stock": {
                "SKU1": {
                    "quantity": 0.0,
                    "inbound": 0.0,
                    "suggested_qty": 12.0,
                    "remaining_capacity": 40.0,
                }
            },
        },
    )
    params = SchemaBinder().bind(_capability(), state)
    assert params is not None
    assert float(params["qty"]) == 12.0


def test_binder_returns_none_when_all_quantities_are_zero():
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_suppliers",
        {
            "status": "ok",
            "suppliers": {
                "acme": {"unit_price": 8.0, "reliability": 0.95, "lead_time_days": 3},
            },
        },
    )
    state.update_from_read(
        "mcp__drivemcp__get_stock_levels",
        {
            "status": "ok",
            "stock": {
                "SKU1": {
                    "quantity": 0.0,
                    "inbound": 0.0,
                    "suggested_qty": 0.0,
                    "remaining_capacity": 0.0,
                }
            },
        },
    )
    assert SchemaBinder().bind(_capability(), state) is None


def test_binder_no_collection_returns_none():
    binder = SchemaBinder()
    empty = WorldState()
    empty.update_from_read("mcp__1c__get_budget", {"status": "ok", "remaining": 100.0})
    assert binder.bind(_capability(), empty) is None


def test_ranking_high_cost_aversion_picks_cheap_supplier():
    binder = SchemaBinder()
    params = binder.bind(
        _capability(),
        _world_with_suppliers_and_stock(),
        rank_weights={"cost_aversion": 1.0, "reliability": 0.0, "speed_seek": 0.0, "novelty_seek": 0.0},
    )
    assert params is not None
    assert params["supplier_id"] == "cheapco"


def test_runtime_happy_path_does_not_import_motor_adapter():
    source = inspect.getsource(RuntimeClass)
    assert "MotorAdapter" not in source
    assert "motor_adapter.resolve" not in source


def test_second_mcp_server_registers_without_adapter_class():
    email = _MockTransport(
        [MCPToolDescriptor("send_message", "send an email", {"type": "object", "properties": {}})]
    )
    registry = MCPToolRegistry("clerk")
    registry.register_from_mcp_discovery(email, "mail")
    cap = registry.get("mcp__mail__send_message")
    assert cap is not None
    assert cap.risk_level == CapabilityRisk.MEDIUM_WRITE
    assert make_tool_id("mail", "send_message") == cap.tool_id
    server, name = split_tool_id(cap.tool_id)
    assert server == "mail"
    assert name == "send_message"


def test_high_write_without_approval_raises_at_gate():
    registry = MCPToolRegistry("ops")
    cap = MCPCapability(
        tool_id="mcp__1c__pay_invoice",
        server_name="1c",
        display_name="Pay",
        description="pay",
        risk_level=CapabilityRisk.HIGH_WRITE,
        requires_approval=False,
    )
    registry.register(cap)
    gate = ApprovalGate(mcp_executor=lambda *_a, **_k: {"status": "ok"}, capability_lookup=registry.get)
    from mcp_body.proposed_action import ProposedAction, new_action_id

    proposed = ProposedAction(
        action_id=new_action_id(),
        agent_id="ops",
        tool_id=cap.tool_id,
        tool_params={},
        risk_level=cap.risk_level,
        intent_summary="pay",
        requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        gate.route(proposed)


def test_seed_tool_id_is_action_channel():
    from mcp_body.seeder import BusinessHippocampusSeeder, SeedEpisode
    from experience import EventType

    class _Hippo:
        def __init__(self):
            self.experiences = []

        def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kwargs):
            self.experiences.append(path)
            return path

    class _Agent:
        def __init__(self):
            self.hippocampus = _Hippo()

    tool_id = "mcp__1c__create_purchase_order"
    seeder = BusinessHippocampusSeeder(
        [
            SeedEpisode(
                context_tokens=["field:quantity:low"],
                action=tool_id,
                consequence="stock_restored",
                reward=0.8,
            )
        ]
    )
    agent = _Agent()
    assert seeder.seed_agent(agent) == 1
    names = [getattr(ev, "name", "") for ev in agent.hippocampus.experiences[0].events]
    assert f"action:{tool_id}" in names
    assert any(getattr(ev, "event_type", None) == EventType.ACTION or getattr(getattr(ev, "event_type", None), "value", "") == "action" for ev in agent.hippocampus.experiences[0].events)


def test_runtime_wait_does_not_store():
    class _Hippo:
        def __init__(self):
            self.store_calls = 0

        def store(self, *args, **kwargs):
            self.store_calls += 1

    class _Agent:
        def __init__(self):
            self.hippocampus = _Hippo()
            self.selector = type("S", (), {"actions": []})()
            self.affective_space = None

        def step(self, events, decision_only=True):
            return WAIT_AND_MONITOR

        def register_action_channel(self, *args, **kwargs):
            return None

    registry = MCPToolRegistry("a")
    registry.register(_capability())
    runtime = BusinessAgentRuntime(
        agent=_Agent(),
        tool_registry=registry,
        approval_gate=ApprovalGate(mcp_executor=lambda *_a, **_k: {"status": "ok"}),
        encoder=GenericEncoder(),
    )
    result = runtime.run_cycle({"agent_id": "a", "tool_results": {}})
    assert result["proposed"] is None
    assert result.get("waited") is True
    assert runtime.agent.hippocampus.store_calls == 0


def test_runtime_executes_bound_write_when_auto_approved():
    class _Agent:
        def __init__(self):
            self.hippocampus = type("H", (), {"experiences": [], "store": lambda *a, **k: None})()
            self.selector = type("S", (), {"actions": []})()
            self.affective_space = None
            self.agent_id = "buyer"

        def step(self, events, decision_only=True):
            return "mcp__1c__create_purchase_order"

        def register_action_channel(self, *args, **kwargs):
            return None

    registry = MCPToolRegistry("buyer")
    cap = _capability(requires_approval=False, risk_level=CapabilityRisk.LOW_WRITE)
    registry.register(cap)
    calls = []

    def executor(tool_id, params):
        calls.append((tool_id, dict(params)))
        return {"status": "accepted"}

    runtime = BusinessAgentRuntime(
        agent=_Agent(),
        tool_registry=registry,
        approval_gate=ApprovalGate(mcp_executor=executor, capability_lookup=registry.get),
        encoder=GenericEncoder(),
    )
    observations = {
        "agent_id": "buyer",
        "tool_results": {
            "mcp__1c__get_suppliers": {
                "status": "ok",
                "suppliers": {
                    "acme": {"unit_price": 8.0, "reliability": 0.9, "lead_time_days": 2},
                    "cheapco": {"unit_price": 3.0, "reliability": 0.4, "lead_time_days": 9},
                },
            },
            "mcp__1c__get_stock_levels": {
                "status": "ok",
                "stock": {"SKU1": {"qty": 2.0}},
            },
        },
    }
    result = runtime.run_cycle(observations)
    assert result["proposed"] is not None
    assert result["executed"] is True
    assert calls and calls[0][0] == "mcp__1c__create_purchase_order"
    assert "supplier_id" in calls[0][1]
    assert result["record"].status == ApprovalStatus.APPROVED
