"""SchemaBinder replaces MotorAdapter (spec §6.4 / §10)."""

from unittest.mock import MagicMock

from nowa_body import SchemaBinder, WorldState
from nowa_body.mcp_capability import CapabilityRisk

from body_support import make_capability


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


def _world_from_lab_snapshot() -> WorldState:
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_stock_levels",
        {
            "status": "ok",
            "stock": {
                "sku_a": {
                    "quantity": 1.0,
                    "reorder_point": 50.0,
                    "below_reorder_point": True,
                    "base_demand_per_day": 2.0,
                }
            },
        },
    )
    state.update_from_read(
        "mcp__1c__get_suppliers",
        {
            "status": "ok",
            "suppliers": {
                "s_good": {
                    "reliability": 0.9,
                    "unit_price": 10.0,
                    "lead_time_days": 3,
                },
                "s_bad": {
                    "reliability": 0.1,
                    "unit_price": 4.0,
                    "lead_time_days": 12,
                },
            },
        },
    )
    return state


def _write_capability(**overrides):
    params = dict(
        tool_id="mcp__1c__create_purchase_order",
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        requires_approval=True,
        input_schema=_order_schema(),
    )
    params.update(overrides)
    return make_capability(**params)


def test_bind_never_raises_on_garbage_world():
    binder = SchemaBinder()
    garbage = WorldState()
    garbage.update_from_read("mcp__x__y", {"garbage": object()})
    assert binder.bind(_write_capability(), garbage) is None


def test_empty_world_returns_none_not_exception():
    binder = SchemaBinder()
    assert binder.bind(_write_capability(), WorldState()) is None


def test_bind_does_not_call_hippocampus_activate():
    mock_hippo = MagicMock()
    mock_hippo.experiences = []
    binder = SchemaBinder()
    params = binder.bind(
        _write_capability(),
        _world_from_lab_snapshot(),
        hippocampus=mock_hippo,
    )
    mock_hippo.activate.assert_not_called()
    assert params is not None
    assert params["supplier_id"] in {"s_good", "s_bad"}
    assert params["sku"] == "sku_a"
    assert float(params["qty"]) > 0


def test_high_reliability_weight_picks_reliable_supplier():
    binder = SchemaBinder()
    params = binder.bind(
        _write_capability(),
        _world_from_lab_snapshot(),
        rank_weights={
            "cost_aversion": 0.0,
            "reliability": 1.0,
            "speed_seek": 0.0,
            "novelty_seek": 0.0,
        },
    )
    assert params is not None
    assert params["supplier_id"] == "s_good"


def test_high_cost_aversion_picks_cheap_supplier():
    binder = SchemaBinder()
    params = binder.bind(
        _write_capability(),
        _world_from_lab_snapshot(),
        rank_weights={
            "cost_aversion": 1.0,
            "reliability": 0.0,
            "speed_seek": 0.0,
            "novelty_seek": 0.0,
        },
    )
    assert params is not None
    assert params["supplier_id"] == "s_bad"
