"""ACTION events after MCP execution are labelled ``action:<tool_id>``.

Basal-ganglia channels are WRITE organs. Strategy strings inside tool_params
must not become a second action vocabulary (spec §6.6).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from nowa_body.approval_gate import ApprovalRecord, ApprovalStatus
from nowa_body.motor_adapter import ProposedAction
from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.business_event_encoder import BusinessEventEncoder
from nowa_body.feedback_loop import apply_feedback_to_agent, _resolve_action_label
from nowa_body.lab_session import (
    ORDER_TOOL,
    SCENARIO_STOCK_CRITICAL,
    WRITE_ACCEPTED,
    BodyLabSession,
    LabSettings,
)

from body_support import make_test_agent as _make_test_agent_factory

ORDER_TOOL_ID = ORDER_TOOL


@pytest.fixture
def make_test_agent():
    return _make_test_agent_factory


def _make_record() -> ApprovalRecord:
    params = {"supplier_id": "acme", "sku": "sku_a", "qty": 30.0}
    proposed = ProposedAction(
        action_id="test-1",
        agent_id="buyer",
        tool_id=ORDER_TOOL_ID,
        tool_params=params,
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        intent_summary=f"{ORDER_TOOL_ID}(supplier_id=acme, ...)",
        requires_approval=False,
    )
    return ApprovalRecord(
        proposed_action=proposed,
        status=ApprovalStatus.APPROVED,
        submitted_at=0.0,
        decided_at=0.0,
        decided_by="test",
        executed=True,
        execution_result={"status": "accepted"},
    )


def _action_event_names(experience) -> list:
    return [
        e.name
        for e in experience.path.events
        if e.event_type.value == "action"
    ]


class TestResolveActionLabel:

    def test_label_is_always_tool_id(self):
        record = _make_record()
        record.proposed_action.tool_params["strategy"] = "urgent_reorder"
        assert _resolve_action_label(record.proposed_action) == ORDER_TOOL_ID

    def test_does_not_mutate_proposed_action(self):
        record = _make_record()
        original = dict(record.proposed_action.tool_params)
        _resolve_action_label(record.proposed_action)
        assert record.proposed_action.tool_params == original
        assert record.proposed_action.tool_id == ORDER_TOOL_ID


class TestFeedbackStoresCorrectActionEvent:

    def test_stored_path_uses_tool_id(self, make_test_agent):
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})
        record = _make_record()
        record.proposed_action.tool_params["strategy"] = "urgent_reorder"

        apply_feedback_to_agent(agent, record, encoder)

        stored = agent.hippocampus.experiences[-1]
        action_names = _action_event_names(stored)
        assert action_names == [f"action:{ORDER_TOOL_ID}"]
        assert "action:urgent_reorder" not in action_names


class TestLabSessionEpisodeRowsUseToolId:
    def test_live_ticks_store_tool_id_action_tokens(self):
        session = BodyLabSession(
            LabSettings(
                seed_intuition=False,
                auto_execute=True,
                scenario=SCENARIO_STOCK_CRITICAL,
                write_status=WRITE_ACCEPTED,
                force_action=ORDER_TOOL_ID,
                clock=datetime(2026, 1, 1, 14, 0, 0),
                sensor_refresh_interval_s=300.0,
                min_ticks_between_sleep=10_000,
            )
        )
        first = session.tick_once()
        assert first.get("executed") is True
        assert first.get("action_type") == ORDER_TOOL_ID
        assert first.get("tool_id") == ORDER_TOOL_ID

        live_rows = session.episode_rows()[-1:]
        action_tokens = []
        for row in live_rows:
            actions = [name for name in row["path"] if str(name).startswith("action:")]
            action_tokens.append(actions[0] if actions else None)

        assert action_tokens == [f"action:{ORDER_TOOL_ID}"]
