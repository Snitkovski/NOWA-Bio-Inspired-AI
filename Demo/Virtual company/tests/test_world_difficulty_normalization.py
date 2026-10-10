"""Tests for Q3a difficulty normalization (off by default)."""

import pytest

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.world_difficulty import WorldDifficulty, estimate_difficulty


class TestWorldDifficultyEstimator:

    def test_estimate_from_live_world(self):
        world = ProcurementWorld(ProcurementWorldConfig(seed=5, n_products=5, n_suppliers=3))
        diff = estimate_difficulty(world)
        assert isinstance(diff, WorldDifficulty)
        assert 3 <= diff.max_lead_time <= 10
        assert 0.0 < diff.mean_demand_volatility <= 0.30 + 1e-9
        assert diff.min_initial_stock_days >= 14.0
        assert diff.expected_demand_shocks >= 0.0

    def test_theoretical_max_in_unit_interval(self):
        easy = WorldDifficulty(
            max_lead_time=3,
            mean_demand_volatility=0.1,
            min_initial_stock_days=20.0,
            mean_reorder_days=10.0,
            expected_demand_shocks=1.0,
        )
        hard = WorldDifficulty(
            max_lead_time=21,
            mean_demand_volatility=0.4,
            min_initial_stock_days=5.0,
            mean_reorder_days=5.0,
            expected_demand_shocks=40.0,
        )
        assert 0.3 <= easy.stockout_theoretical_max() <= 1.0
        assert 0.3 <= hard.stockout_theoretical_max() <= 1.0
        assert hard.stockout_theoretical_max() < easy.stockout_theoretical_max()


class TestNormalizeStockoutDifficulty:

    def test_default_is_off(self):
        assert ProcurementFitnessEvaluator().normalize_stockout_difficulty is False

    def test_normalized_score_ge_raw_when_ceiling_below_one(self):
        world = ProcurementWorld(
            ProcurementWorldConfig(
                seed=11, n_products=4, n_suppliers=3, days_per_quarter=30
            )
        )
        # Force some stockout so raw < 1.
        for product in world.products.values():
            product.current_stock = 0.0
        for _ in range(30):
            world.tick()

        raw_eval = ProcurementFitnessEvaluator(normalize_stockout_difficulty=False)
        norm_eval = ProcurementFitnessEvaluator(normalize_stockout_difficulty=True)
        raw = raw_eval._stockout_avoidance(world)
        norm = norm_eval._stockout_avoidance(world)
        assert 0.0 <= raw <= 1.0
        assert 0.0 <= norm <= 1.0
        # Normalization lifts the score when theoretical_max < 1.
        theoretical = estimate_difficulty(world).stockout_theoretical_max()
        if theoretical < 1.0 - 1e-9 and raw > 0:
            assert norm >= raw - 1e-9
            assert norm == pytest.approx(min(1.0, raw / theoretical))
