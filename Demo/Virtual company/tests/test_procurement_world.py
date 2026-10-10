"""Tests for ProcurementWorld physics."""

import copy
import math

import pytest

from nowa_sandbox.procurement_world import (
    ProcurementWorld,
    ProcurementWorldConfig,
    product_replenishment_point,
)


class TestWorldInitialization:

    def test_creates_requested_number_of_products(self, small_world):
        assert len(small_world.products) == 3

    def test_creates_requested_number_of_suppliers(self, small_world):
        assert len(small_world.suppliers) == 2

    def test_initial_budget_matches_config(self, small_world_config):
        world = ProcurementWorld(small_world_config)
        assert world.budget == small_world_config.initial_budget

    def test_not_bankrupt_initially(self, small_world):
        assert small_world.bankrupt is False

    def test_deterministic_with_same_seed(self, small_world_config):
        world1 = ProcurementWorld(small_world_config)
        world2 = ProcurementWorld(small_world_config)
        for pid in world1.products:
            assert world1.products[pid].current_stock == world2.products[pid].current_stock

    def test_identical_seed_gives_identical_history(self, small_world_config):
        world1 = ProcurementWorld(small_world_config)
        world2 = ProcurementWorld(small_world_config)
        for _ in range(40):
            world1.tick()
            world2.tick()
        assert world1.history == world2.history

    def test_different_seeds_give_different_history(self):
        world1 = ProcurementWorld(ProcurementWorldConfig(n_products=4, seed=1))
        world2 = ProcurementWorld(ProcurementWorldConfig(n_products=4, seed=2))
        for _ in range(30):
            world1.tick()
            world2.tick()
        assert world1.history != world2.history

    def test_config_sanitizes_negative_counts(self):
        config = ProcurementWorldConfig(n_products=-5, n_suppliers=-2, days_per_quarter=-1)
        assert config.n_products == 0
        assert config.n_suppliers == 0
        assert config.days_per_quarter == 0

    def test_config_clamps_probabilities(self):
        config = ProcurementWorldConfig(
            demand_shock_probability=5.0,
            supplier_default_probability=-1.0,
            late_delivery_probability_base=2.5,
        )
        assert config.demand_shock_probability == 1.0
        assert config.supplier_default_probability == 0.0
        assert config.late_delivery_probability_base == 1.0


class TestObservations:

    def test_observe_stock_levels_returns_all_products(self, small_world):
        stock = small_world.observe_stock_levels()
        assert set(stock.keys()) == set(small_world.products.keys())

    def test_observe_stock_levels_exposes_demand_and_replenishment(self, small_world):
        stock = small_world.observe_stock_levels()
        for pid, product in small_world.products.items():
            info = stock[pid]
            assert info["base_demand_per_day"] == pytest.approx(
                product.base_demand_per_day
            )
            assert "replenishment_point" in info
            assert info["replenishment_point"] >= info["reorder_point"]

    def test_replenishment_point_covers_lead_time_when_rop_is_short(self):
        # purchase_data.json «Банка 3 литра»: demand 6, ROP 18, lead 5.
        point = product_replenishment_point(18.0, 6.0, 0.15, 5)
        assert point >= 6.0 * 5
        assert point > 18.0

    def test_observe_supplier_quote_valid_supplier(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        quote = small_world.observe_supplier_quote(supplier_id, product_id, 10)
        assert quote["status"] == "ok"
        assert quote["unit_price"] > 0

    def test_observe_supplier_quote_unknown_supplier(self, small_world):
        quote = small_world.observe_supplier_quote("nonexistent", "product_000", 10)
        assert quote["status"] == "unavailable"

    def test_observe_supplier_quote_defaulted_supplier(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        small_world.suppliers[supplier_id].is_defaulted = True
        quote = small_world.observe_supplier_quote(supplier_id, "product_000", 10)
        assert quote["status"] == "unavailable"

    def test_observe_budget_status_structure(self, small_world):
        status = small_world.observe_budget_status()
        assert "allocated" in status
        assert "spent" in status
        assert "remaining" in status
        assert status["remaining"] == small_world.budget

    def test_observe_supplier_directory_lists_all(self, small_world):
        directory = small_world.observe_supplier_directory()
        assert set(directory.keys()) == set(small_world.suppliers.keys())

    def test_observe_pending_orders_empty_initially(self, small_world):
        assert small_world.observe_pending_orders() == []

    def test_observe_pending_orders_after_order(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        small_world.place_order(supplier_id, product_id, 10)
        pending = small_world.observe_pending_orders()
        assert len(pending) == 1
        assert pending[0]["product_id"] == product_id


class TestObservationPurity:
    """Spec section 14 invariant: observe_* must never mutate world state."""

    def test_repeated_observations_leave_state_identical(self, small_world):
        before = copy.deepcopy(small_world.__dict__)
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        for _ in range(25):
            small_world.observe_stock_levels()
            small_world.observe_budget_status()
            small_world.observe_supplier_directory()
            small_world.observe_pending_orders()
            small_world.observe_supplier_quote(supplier_id, product_id, 17)
        after = small_world.__dict__
        assert after["rng"].getstate() == before["rng"].getstate()
        assert after["budget"] == before["budget"]
        assert after["day"] == before["day"]
        for pid, product in after["products"].items():
            assert product.current_stock == before["products"][pid].current_stock

    def test_quote_is_stable_within_a_day(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        first = small_world.observe_supplier_quote(supplier_id, product_id, 10)
        second = small_world.observe_supplier_quote(supplier_id, product_id, 10)
        assert first == second

    def test_quote_varies_across_days(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        prices = set()
        for _ in range(20):
            prices.add(
                small_world.observe_supplier_quote(supplier_id, product_id, 10)["unit_price"]
            )
            small_world.tick()
        assert len(prices) > 1

    def test_observations_do_not_change_tick_outcome(self, small_world_config):
        quiet = ProcurementWorld(small_world_config)
        observed = ProcurementWorld(small_world_config)
        supplier_id = next(iter(observed.suppliers.keys()))
        for _ in range(20):
            quiet.tick()
            for _ in range(5):
                observed.observe_supplier_quote(supplier_id, "product_000", 3)
                observed.observe_stock_levels()
            observed.tick()
        assert quiet.history == observed.history


class TestPlaceOrder:

    def test_valid_order_accepted(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order(supplier_id, product_id, 10)
        assert result["status"] == "accepted"
        assert "order_id" in result

    def test_order_reduces_budget(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        budget_before = small_world.budget
        small_world.place_order(supplier_id, product_id, 10)
        assert small_world.budget < budget_before

    def test_order_exceeding_budget_rejected(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order(supplier_id, product_id, 1_000_000_000)
        assert result["status"] == "rejected"
        assert result["reason"] == "insufficient_budget"

    def test_rejected_order_has_no_side_effects(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        budget_before = small_world.budget
        counter_before = small_world._order_counter
        small_world.place_order(supplier_id, product_id, 1_000_000_000)
        assert small_world.budget == budget_before
        assert small_world._order_counter == counter_before
        assert small_world.pending_orders == []

    def test_order_unknown_supplier_rejected(self, small_world):
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order("ghost_supplier", product_id, 10)
        assert result["status"] == "rejected"
        assert result["reason"] == "unknown_supplier"

    def test_order_unknown_product_rejected(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        result = small_world.place_order(supplier_id, "ghost_product", 10)
        assert result["status"] == "rejected"
        assert result["reason"] == "unknown_product"

    def test_zero_quantity_rejected(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order(supplier_id, product_id, 0)
        assert result["status"] == "rejected"

    @pytest.mark.parametrize(
        "qty", [-1, -0.001, float("nan"), float("inf"), float("-inf"), None, "ten"]
    )
    def test_invalid_quantity_rejected(self, small_world, qty):
        """Edge case E1: negative, NaN, infinite and non-numeric quantities."""
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order(supplier_id, product_id, qty)
        assert result["status"] == "rejected"
        assert result["reason"] == "invalid_quantity"

    def test_order_added_to_pending(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        n_before = len(small_world.pending_orders)
        small_world.place_order(supplier_id, product_id, 10)
        assert len(small_world.pending_orders) == n_before + 1

    def test_every_order_is_accepted_or_has_a_reason(self, small_world):
        """Acceptance criterion: never a silent third outcome."""
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        cases = [
            (supplier_id, product_id, 5),
            (supplier_id, product_id, -5),
            ("ghost", product_id, 5),
            (supplier_id, "ghost", 5),
            (supplier_id, product_id, 10**12),
        ]
        for sid, pid, qty in cases:
            result = small_world.place_order(sid, pid, qty)
            assert result["status"] in {"accepted", "rejected"}
            if result["status"] == "rejected":
                assert result.get("reason")

    def test_order_ids_are_unique(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        ids = set()
        for _ in range(5):
            result = small_world.place_order(supplier_id, product_id, 2)
            ids.add(result["order_id"])
        assert len(ids) == 5


class TestWorldTick:

    def test_tick_advances_day(self, small_world):
        day_before = small_world.day
        small_world.tick()
        assert small_world.day == day_before + 1

    def test_tick_records_history(self, small_world):
        small_world.tick()
        assert len(small_world.history) == 1

    def test_demand_reduces_stock_without_shock(self, small_world):
        stock_before = {
            pid: p.current_stock for pid, p in small_world.products.items()
        }
        small_world.tick()
        stock_after = {
            pid: p.current_stock for pid, p in small_world.products.items()
        }
        decreased = sum(
            1 for pid in stock_before
            if stock_after[pid] <= stock_before[pid]
        )
        assert decreased >= len(stock_before) // 2

    def test_order_arrives_after_lead_time(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        lead_time = small_world.suppliers[supplier_id].lead_time_days
        small_world.place_order(supplier_id, product_id, 50)

        for _ in range(lead_time + 1):
            small_world.tick()

        assert len(small_world.pending_orders) == 0
        assert len(small_world.delivered_orders) >= 1

    def test_arrival_increases_stock(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        lead_time = small_world.suppliers[supplier_id].lead_time_days
        small_world.place_order(supplier_id, product_id, 5000)
        for _ in range(lead_time):
            small_world.tick()
        assert small_world.products[product_id].current_stock > 1000

    def test_bankruptcy_detected_when_budget_negative(self):
        config = ProcurementWorldConfig(
            initial_budget=1.0,
            n_products=2, n_suppliers=1,
            days_per_quarter=10, seed=1,
        )
        world = ProcurementWorld(config)
        for _ in range(200):
            world.tick()
            if world.bankrupt:
                break
        assert world.bankrupt is True

    def test_bankruptcy_event_emitted_once(self, bankrupt_world):
        events = [
            e for snap in bankrupt_world.history
            for e in snap["events"] if e["type"] == "bankruptcy"
        ]
        assert len(events) == 1

    def test_stockout_events_recorded(self, small_world):
        for _ in range(60):
            small_world.tick()
        stockout_events = [
            e for snap in small_world.history
            for e in snap["events"] if e["type"] == "stockout"
        ]
        assert len(stockout_events) > 0

    def test_ninety_idle_days_produce_a_stockout(self):
        """Acceptance criterion: an idle world starves itself within a quarter."""
        world = ProcurementWorld(ProcurementWorldConfig(seed=7))
        for _ in range(90):
            world.tick()
        stockouts = [
            e for snap in world.history
            for e in snap["events"] if e["type"] == "stockout"
        ]
        assert len(stockouts) >= 1

    def test_constant_overordering_causes_bankruptcy_within_a_quarter(self):
        """Acceptance criterion: reckless spending bankrupts the company."""
        world = ProcurementWorld(ProcurementWorldConfig(
            initial_budget=5_000.0, n_products=5, n_suppliers=3, seed=11,
        ))
        for _ in range(90):
            for supplier_id in world.suppliers:
                for product_id in world.products:
                    world.place_order(supplier_id, product_id, 2_000)
            world.tick()
            if world.bankrupt:
                break
        assert world.bankrupt is True

    def test_holding_costs_accumulate(self, small_world):
        small_world.tick()
        total_holding = sum(
            p.cumulative_holding_cost for p in small_world.products.values()
        )
        assert total_holding > 0


class TestSupplierDefault:

    def test_defaulted_supplier_rejects_orders(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        small_world.suppliers[supplier_id].is_defaulted = True
        product_id = next(iter(small_world.products.keys()))
        result = small_world.place_order(supplier_id, product_id, 10)
        assert result["status"] == "rejected"
        assert result["reason"] == "supplier_defaulted"

    def test_default_is_announced_only_once(self):
        config = ProcurementWorldConfig(
            n_products=2, n_suppliers=3,
            supplier_default_probability=0.5, seed=3,
        )
        world = ProcurementWorld(config)
        for _ in range(50):
            world.tick()
        announced = [
            e["supplier_id"] for snap in world.history
            for e in snap["events"] if e["type"] == "supplier_defaulted"
        ]
        assert len(announced) == len(set(announced))

    def test_all_suppliers_defaulted_does_not_break_world(self):
        """Edge case E2: no supplier is reachable, stockouts are expected."""
        world = ProcurementWorld(ProcurementWorldConfig(
            n_products=3, n_suppliers=2, seed=5,
        ))
        for supplier in world.suppliers.values():
            supplier.is_defaulted = True
        for _ in range(40):
            world.tick()
        result = world.place_order("supplier_000", "product_000", 10)
        assert result["status"] == "rejected"
        assert world.day == 40

    def test_reputation_rises_on_time_and_falls_when_late(self, small_world):
        supplier = next(iter(small_world.suppliers.values()))
        baseline = supplier.reputation
        supplier.update_reputation_on_delivery(True)
        assert supplier.reputation > baseline
        raised = supplier.reputation
        supplier.update_reputation_on_delivery(False)
        assert supplier.reputation < raised
        assert supplier.total_orders == 2
        assert supplier.successful_orders == 1


class TestEdgeCaseConfigurations:

    def test_zero_products(self):
        """Edge case E3."""
        world = ProcurementWorld(ProcurementWorldConfig(n_products=0, seed=1))
        assert world.observe_stock_levels() == {}
        for _ in range(10):
            world.tick()
        assert world.day == 10
        assert world.summary()["total_stockout_units"] == 0

    def test_zero_suppliers(self):
        world = ProcurementWorld(ProcurementWorldConfig(n_suppliers=0, seed=1))
        assert world.observe_supplier_directory() == {}
        for _ in range(10):
            world.tick()
        result = world.place_order("supplier_000", "product_000", 5)
        assert result["status"] == "rejected"

    def test_zero_budget_goes_bankrupt_immediately(self):
        """Edge case E5: this is a correct outcome, not an anomaly."""
        world = ProcurementWorld(ProcurementWorldConfig(initial_budget=0.0, seed=1))
        world.tick()
        assert world.bankrupt is True
        assert world.observe_budget_status()["utilization_ratio"] == 0.0

    def test_order_placed_near_horizon_stays_pending(self):
        """Edge case E6: late orders simply never arrive within the quarter."""
        world = ProcurementWorld(ProcurementWorldConfig(
            n_products=2, n_suppliers=1, days_per_quarter=10, seed=4,
        ))
        supplier = next(iter(world.suppliers.values()))
        for _ in range(9):
            world.tick()
        world.place_order(supplier.supplier_id, "product_000", 10)
        world.tick()
        if supplier.lead_time_days > 1:
            assert len(world.pending_orders) == 1


class TestSummary:

    def test_summary_structure(self, small_world):
        small_world.tick()
        summary = small_world.summary()
        required_keys = {
            "day", "budget", "spent_ratio", "bankrupt",
            "total_stockout_units", "total_holding_cost",
            "n_orders_placed", "n_orders_delivered",
            "n_suppliers_defaulted",
        }
        assert required_keys.issubset(summary.keys())

    def test_summary_counts_orders(self, small_world):
        supplier_id = next(iter(small_world.suppliers.keys()))
        product_id = next(iter(small_world.products.keys()))
        small_world.place_order(supplier_id, product_id, 10)
        assert small_world.summary()["n_orders_placed"] == 1

    def test_summary_values_are_finite(self, small_world):
        for _ in range(20):
            small_world.tick()
        for key, value in small_world.summary().items():
            if isinstance(value, float):
                assert math.isfinite(value), f"{key} is not finite"
