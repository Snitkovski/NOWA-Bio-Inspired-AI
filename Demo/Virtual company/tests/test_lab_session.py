"""Headless tests for the Body Layer lab session (no tkinter window)."""

from __future__ import annotations

from datetime import datetime

from nowa_body.lab_session import (
    FORCE_AUTO,
    ORDER_TOOL,
    SCENARIO_QUIET,
    SCENARIO_STOCK_CRITICAL,
    WRITE_ACCEPTED,
    WRITE_REJECTED,
    WRITE_TIMEOUT,
    BodyLabSession,
    LabSettings,
)


def _session(**kwargs) -> BodyLabSession:
    params = dict(
        seed_intuition=True,
        auto_execute=False,
        scenario=SCENARIO_STOCK_CRITICAL,
        write_status=WRITE_ACCEPTED,
        force_action=ORDER_TOOL,
        clock=datetime(2026, 1, 1, 14, 0, 0),
        sensor_refresh_interval_s=300.0,
        min_ticks_between_sleep=10_000,
    )
    params.update(kwargs)
    return BodyLabSession(LabSettings(**params))


def _session_requiring_approval(**kwargs) -> BodyLabSession:
    session = _session(**kwargs)
    cap = session.registry.get(ORDER_TOOL)
    assert cap is not None
    cap.requires_approval = True
    return session


def test_quiet_wait_does_not_grow_memory():
    session = _session(scenario=SCENARIO_QUIET, force_action="wait_and_monitor")
    n_before = session.snapshot()["episodes"]
    session.tick_many(8)
    snap = session.snapshot()
    assert snap["episodes"] == n_before
    assert snap["pending"] == []
    assert snap["action_type"] == "wait_and_monitor"


def test_stock_critical_executes_write_when_role_skips_approval():
    session = _session()
    result = session.tick_once()
    assert result["proposed"] is not None
    assert result["approval_status"] == "approved"
    assert result.get("executed") is True
    assert session.pending_rows() == []
    writes = [row for row in session.mcp_history if "create_purchase_order" in row["tool_id"]]
    assert writes


def test_stock_critical_queues_write_for_approval():
    session = _session_requiring_approval()
    result = session.tick_once()
    assert result["proposed"] is not None
    assert result["approval_status"] == "pending"
    assert result.get("executed") is False
    pending = session.pending_rows()
    assert len(pending) == 1
    assert pending[0]["params"]["supplier_id"] in {"acme", "cheapco"}


def test_approve_executes_write_and_stores_episode():
    session = _session_requiring_approval()
    n_before = session.snapshot()["episodes"]
    session.tick_once()
    action_id = session.pending_rows()[0]["action_id"]
    record = session.approve(action_id)
    assert record.executed is True
    assert record.execution_result["status"] == "accepted"
    assert session.snapshot()["episodes"] == n_before + 1
    writes = [row for row in session.mcp_history if "create_purchase_order" in row["tool_id"]]
    assert writes


def test_reject_does_not_call_write_tool():
    session = _session_requiring_approval()
    session.tick_once()
    action_id = session.pending_rows()[0]["action_id"]
    record = session.reject(action_id, reason="too expensive")
    assert record.executed is False
    writes = [row for row in session.mcp_history if "create_purchase_order" in row["tool_id"]]
    assert writes == []


def test_timeout_write_does_not_crash_when_auto_execute():
    session = _session(auto_execute=True, write_status=WRITE_TIMEOUT)
    result = session.tick_once()
    assert result["executed"] is True
    assert result["record"].execution_result["status"] == "error"
    assert "timeout" in str(result["record"].execution_result.get("reason", ""))


def test_rejected_write_status_stores_failure_token():
    session = _session(auto_execute=True, write_status=WRITE_REJECTED)
    n_before = session.snapshot()["episodes"]
    session.tick_once()
    assert session.snapshot()["episodes"] == n_before + 1
    last = session.episode_rows()[-1]
    assert "result:failure" in last["path"]


def test_sensors_are_cached_across_ticks():
    session = _session(force_action="wait_and_monitor", scenario=SCENARIO_QUIET)
    session.tick_once()
    reads_after_first = len(session.mcp_history)
    session.tick_once()
    assert len(session.mcp_history) == reads_after_first


def test_night_clock_can_trigger_circadian_sleep():
    session = _session(
        force_action="wait_and_monitor",
        scenario=SCENARIO_QUIET,
        clock=datetime(2026, 1, 1, 3, 0, 0),
        min_ticks_between_sleep=0,
    )
    result = session.tick_once()
    assert result["slept"] is True
    assert result["sleep_reason"] == "circadian"


def test_fatigue_override_triggers_outside_window():
    session = _session(
        force_action="wait_and_monitor",
        scenario=SCENARIO_QUIET,
        clock=datetime(2026, 1, 1, 14, 0, 0),
        min_ticks_between_sleep=0,
        fatigue_override=0.95,
    )
    result = session.tick_once()
    assert result["slept"] is True
    assert result["sleep_reason"] == "fatigue"


def test_high_write_probe_is_blocked():
    session = _session()
    probe = session.probe_high_write_bypass()
    assert probe["ok"] is True
    assert probe["invariant_raised"] is True
    assert probe["gate_raised"] is True


def test_modify_qty_then_execute():
    session = _session_requiring_approval()
    session.tick_once()
    action_id = session.pending_rows()[0]["action_id"]
    record = session.modify(action_id, {"qty": 1.0})
    assert record.executed is True
    assert record.proposed_action.tool_params["qty"] == 1.0


def test_snapshot_has_pipeline_fields():
    session = _session(force_action="wait_and_monitor", scenario=SCENARIO_QUIET)
    session.tick_once()
    snap = session.snapshot()
    for key in (
        "tick", "now", "action_type", "episodes", "pending",
        "context_events", "sleep_pressure", "log",
    ):
        assert key in snap
    assert snap["tick"] == 1
    assert FORCE_AUTO != session.agent.force_action
