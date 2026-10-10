"""Shared helpers for nowa_body tests. Does not import nowa_sandbox."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from nowa_body.approval_gate import ApprovalGate
from nowa_body.business_event_encoder import BusinessEventEncoder
from nowa_body.mcp_capability import CapabilityRisk, MCPCapability
from nowa_body.mock_mcp import MockMCPClient, MockMCPTool
from nowa_body.motor_adapter import MotorAdapter
from nowa_body.runtime import BusinessAgentRuntime
from nowa_body.sleep_scheduler import SleepScheduler
from nowa_body.tool_registry import MCPToolRegistry


class FakeHippocampus:
    def __init__(self) -> None:
        self.experiences: List[Any] = []
        self.stored: List[Any] = []
        self.reinforced: List[Any] = []
        self.activate_calls = 0

    def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kwargs):
        exp = SimpleNamespace(
            path=path,
            consequence=consequence,
            intensity=intensity,
            reward=reward,
        )
        self.stored.append(exp)
        self.experiences.append(exp)
        return exp

    def reinforce(self, path, consequence=None, intensity=1.0, **kwargs):
        self.reinforced.append((path, consequence, intensity))

    def activate(self, *args, **kwargs):
        self.activate_calls += 1
        return []


class FakeAffectiveSpace:
    def __init__(self) -> None:
        self.axes: Dict[str, float] = {}
        self.step_calls: List[Any] = []

    def rank_weights(self) -> Dict[str, float]:
        return {}

    def snapshot(self) -> Dict[str, Any]:
        return {"axes": dict(self.axes)}

    def step(self, inputs=None, **kwargs):
        payload = inputs if inputs is not None else kwargs
        self.step_calls.append(payload)
        if isinstance(payload, dict):
            self.axes.update({k: float(v) for k, v in payload.items()
                              if isinstance(v, (int, float))})


class FakeAgent:
    def __init__(self, action: str = "wait_and_monitor") -> None:
        self.action = action
        self.step_calls: List[Any] = []
        self.hippocampus = FakeHippocampus()
        self.affective_space = FakeAffectiveSpace()
        self.neuromodulators = SimpleNamespace(update_calls=0, to_dict=lambda: {})
        self.value_layer = SimpleNamespace(update_count=0, update=lambda *a, **k: None)
        self.sleep_calls = 0
        self.sleep_manager = SimpleNamespace(sleep_cycle=self._sleep)
        self.wakefulness_state = None
        self.selector = SimpleNamespace(compute_pressures=lambda *a, **k: {}, actions=[])

    def _sleep(self):
        self.sleep_calls += 1

    def step(self, context_events, decision_only=True):
        self.step_calls.append(
            {"events": list(context_events), "decision_only": decision_only}
        )
        return self.action

    def register_action_channel(self, *args, **kwargs):
        return None

    def set_organ_risk(self, *args, **kwargs):
        return None


class LiteralMotorAdapter(MotorAdapter):
    """Test adapter: copies a fixed/observation param dict, never raises."""

    def __init__(self, tool_registry: MCPToolRegistry, params: Optional[dict] = None):
        super().__init__(tool_registry)
        self.fixed_params = params
        self.resolve_calls: List[Any] = []

    def resolve(self, action_type, observations, hippocampus=None):
        self.resolve_calls.append(action_type)
        return super().resolve(action_type, observations, hippocampus=hippocampus)

    def _build_params(self, capability, action_type, observations):
        if action_type in ("", "wait_and_monitor"):
            return None
        if self.fixed_params is not None:
            return dict(self.fixed_params)
        extra = observations.get("tool_params")
        if isinstance(extra, dict) and extra:
            return dict(extra)
        return {"action_type": action_type, "ok": True}


def make_capability(**overrides) -> MCPCapability:
    params = dict(
        tool_id="mcp__test__do",
        server_name="test",
        display_name="Do",
        description="test tool",
        risk_level=CapabilityRisk.LOW_WRITE,
        requires_approval=False,
        action_types=["do_thing"],
    )
    params.update(overrides)
    return MCPCapability(**params)


def make_test_agent(action: str = "wait_and_monitor") -> FakeAgent:
    return FakeAgent(action=action)


def make_test_agent_with_pressure(pressure: float) -> FakeAgent:
    agent = FakeAgent()
    agent.wakefulness_state = SimpleNamespace(process_s=float(pressure))
    return agent


def make_test_agent_that_always_acts(action: str = "mcp__test__do") -> FakeAgent:
    return FakeAgent(action=action)


def make_mock_client(write_status: str = "success") -> MockMCPClient:
    client = MockMCPClient()
    client.register(
        MockMCPTool(
            "mcp__test__get",
            lambda params: {"status": "ok", "items": params},
        )
    )

    def _write(params):
        if write_status == "timeout":
            raise TimeoutError("tool timed out")
        return {"status": write_status, "params": dict(params)}

    client.register(MockMCPTool("mcp__test__do", _write))
    return client


def make_test_runtime(
    agent=None,
    sensor_refresh_interval_s: float = 300.0,
    requires_approval: bool = False,
    risk_level: CapabilityRisk = CapabilityRisk.LOW_WRITE,
    write_status: str = "success",
    sleep_scheduler: Optional[SleepScheduler] = None,
) -> BusinessAgentRuntime:
    agent = agent or make_test_agent()
    registry = MCPToolRegistry(getattr(agent, "agent_id", "test_agent"))
    registry.register(
        make_capability(
            tool_id="mcp__test__get",
            display_name="Get",
            risk_level=CapabilityRisk.READ_ONLY,
            requires_approval=False,
            action_types=[],
        )
    )
    registry.register(
        make_capability(
            tool_id="mcp__test__do",
            risk_level=risk_level,
            requires_approval=requires_approval,
            action_types=["do_thing"],
        )
    )
    client = make_mock_client(write_status=write_status)
    gate = ApprovalGate(
        mcp_executor=client.execute,
        capability_lookup=registry.get,
    )
    encoder = BusinessEventEncoder({
        "stock_critical_low": {
            "valence": -0.7, "arousal": 0.8, "tags": ["procurement"],
        }
    })
    return BusinessAgentRuntime(
        agent=agent,
        tool_registry=registry,
        approval_gate=gate,
        encoder=encoder,
        sleep_scheduler=sleep_scheduler or SleepScheduler(min_ticks_between_sleep=10_000),
        sensor_refresh_interval_s=sensor_refresh_interval_s,
    )
