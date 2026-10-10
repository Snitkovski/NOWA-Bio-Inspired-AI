"""Offer-based quoting and ordering in ProcurementWorld."""

from nowa_sandbox.procurement_world import ProcurementWorld


SPEC = {
    "budget": 50_000.0,
    "products": [
        {
            "product_id": "A",
            "base_demand_per_day": 5.0,
            "demand_volatility": 0.1,
            "holding_cost_per_unit": 1.0,
            "stockout_penalty_per_unit": 8.0,
            "current_stock": 100.0,
            "reorder_point": 40.0,
        },
        {
            "product_id": "B",
            "base_demand_per_day": 5.0,
            "demand_volatility": 0.1,
            "holding_cost_per_unit": 1.0,
            "stockout_penalty_per_unit": 8.0,
            "current_stock": 100.0,
            "reorder_point": 40.0,
        },
    ],
    "suppliers": [
        {"supplier_id": "S1", "reputation": 0.5, "is_defaulted": False},
        {"supplier_id": "S2", "reputation": 0.5, "is_defaulted": False},
    ],
    "offers": [
        {
            "product_id": "A",
            "supplier_id": "S1",
            "unit_price": 1.0,
            "lead_time_days": 3,
            "reliability": 0.95,
            "price_volatility": 0.0,
        },
        {
            "product_id": "B",
            "supplier_id": "S1",
            "unit_price": 9.0,
            "lead_time_days": 7,
            "reliability": 0.8,
            "price_volatility": 0.0,
        },
        {
            "product_id": "A",
            "supplier_id": "S2",
            "unit_price": 2.0,
            "lead_time_days": 4,
            "reliability": 0.9,
            "price_volatility": 0.0,
        },
    ],
}


def test_different_prices_per_product_same_supplier():
    world = ProcurementWorld.from_quarter_spec(SPEC, days_per_quarter=5, seed=1)
    qa = world.observe_supplier_quote("S1", "A", 1)
    qb = world.observe_supplier_quote("S1", "B", 1)
    assert qa["status"] == "ok"
    assert qb["status"] == "ok"
    assert abs(qa["unit_price"] - 1.0) < 1e-6
    assert abs(qb["unit_price"] - 9.0) < 1e-6
    assert qa["lead_time_days"] == 3
    assert qb["lead_time_days"] == 7


def test_no_offer_means_unavailable():
    world = ProcurementWorld.from_quarter_spec(SPEC, days_per_quarter=5, seed=1)
    # S2 has no offer for B
    quote = world.observe_supplier_quote("S2", "B", 1)
    assert quote["status"] == "unavailable"
    rejected = world.place_order("S2", "B", 5)
    assert rejected["status"] == "rejected"


def test_order_uses_offer_lead_time():
    world = ProcurementWorld.from_quarter_spec(SPEC, days_per_quarter=5, seed=1)
    result = world.place_order("S1", "A", 10)
    assert result["status"] == "accepted"
    assert result["eta_days"] == 3
    assert world.pending_orders[0].arrival_day == 3


def test_suppliers_for_product_filters():
    world = ProcurementWorld.from_quarter_spec(SPEC, days_per_quarter=5, seed=1)
    for_a = {s.supplier_id for s in world.suppliers_for_product("A")}
    for_b = {s.supplier_id for s in world.suppliers_for_product("B")}
    assert for_a == {"S1", "S2"}
    assert for_b == {"S1"}
