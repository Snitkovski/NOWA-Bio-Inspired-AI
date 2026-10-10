"""Tests ensuring Q3b parameter bounding eliminates impossible quarters."""

import pytest

from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig


class TestLeadTimeBound:

    def test_max_lead_time_respected(self):
        config = ProcurementWorldConfig(n_suppliers=5, seed=42, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days <= 10, (
                f"supplier {supplier.supplier_id} lead_time={supplier.lead_time_days} "
                f"exceeds max_lead_time_days=10"
            )

    def test_default_max_lead_time_is_10(self):
        """New default must be 10, not 21."""
        config = ProcurementWorldConfig()
        assert config.max_lead_time_days == 10

    def test_lead_time_always_gte_3(self):
        """Lower bound unchanged."""
        config = ProcurementWorldConfig(n_suppliers=20, seed=1, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days >= 3


class TestDemandVolatilityBound:

    def test_volatility_capped_at_0_3(self):
        config = ProcurementWorldConfig(n_products=20, seed=42)
        world = ProcurementWorld(config)
        for product in world.products.values():
            assert product.demand_volatility <= 0.30 + 1e-9, (
                f"product {product.product_id} volatility={product.demand_volatility} "
                f"exceeds 0.30"
            )


class TestDemandCap:

    def test_base_demand_respects_max(self):
        config = ProcurementWorldConfig(n_products=30, seed=7, max_demand_per_day=30.0)
        world = ProcurementWorld(config)
        for product in world.products.values():
            assert product.base_demand_per_day <= 30.0 + 1e-9
            assert product.base_demand_per_day >= 5.0 - 1e-9


class TestInitialStockFloor:

    def test_initial_stock_at_least_min_days(self):
        config = ProcurementWorldConfig(
            n_products=10, seed=42, min_initial_stock_days=15.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            days_of_stock = (
                product.current_stock / max(product.base_demand_per_day, 0.01)
            )
            assert days_of_stock >= 14.0, (
                f"product {pid} has only {days_of_stock:.1f} days of stock "
                f"(min expected: 15)"
            )


class TestReorderPointFloor:

    def test_reorder_point_covers_max_lead_time(self):
        """With min_reorder_days=7 and max_lead_time=10, there's always
        a 7-day buffer before hitting reorder_point from which the agent
        has time to order and receive before stockout."""
        config = ProcurementWorldConfig(
            n_products=10, seed=42,
            max_lead_time_days=10, min_reorder_days=7.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            reorder_days = (
                product.reorder_point / max(product.base_demand_per_day, 0.01)
            )
            assert reorder_days >= 6.5, (
                f"product {pid} reorder_point covers only {reorder_days:.1f} "
                f"days of demand (min expected: 7)"
            )


class TestSupplierReliabilityFloor:

    def test_reliability_at_least_0_80(self):
        config = ProcurementWorldConfig(n_suppliers=20, seed=3)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.reliability >= 0.80 - 1e-9


class TestBackwardCompatibility:

    def test_old_config_without_new_fields_still_works(self):
        """Code that constructs ProcurementWorldConfig without the new
        difficulty-bounding fields must continue to work unchanged."""
        config = ProcurementWorldConfig(
            initial_budget=50_000.0,
            n_products=5, n_suppliers=3,
            days_per_quarter=90, seed=1,
        )
        world = ProcurementWorld(config)
        assert world is not None
        world.tick()

    def test_yaml_round_trip_preserves_bounds(self):
        from nowa_sandbox.sandbox_config import SandboxConfig

        original = SandboxConfig.load(None)
        restored = SandboxConfig.from_mapping(original.to_dict())
        assert restored.world.max_lead_time_days == 10
        assert restored.world.max_demand_per_day == 30.0
        assert restored.world.min_reorder_days == 7.0
        assert restored.world.min_initial_stock_days == 15.0
