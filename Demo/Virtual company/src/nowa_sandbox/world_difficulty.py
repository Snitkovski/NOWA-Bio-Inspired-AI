"""Estimate inherent world difficulty for stockout_avoidance (spec v1.3 Q3a).

Used optionally to normalize fitness so the agent is judged on decisions,
not on the luck of world parameters. Off by default until Q3b bounding is
shown to be insufficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorldDifficulty:
    """Apriori difficulty snapshot for stockout_avoidance scoring."""

    max_lead_time: int
    mean_demand_volatility: float
    min_initial_stock_days: float
    mean_reorder_days: float
    expected_demand_shocks: float  # n_products * days * shock_prob

    def stockout_theoretical_max(self) -> float:
        """Best stockout_avoidance a perfect agent could achieve here.

        Heuristic in [0.3, 1.0]: longer lead times, higher volatility and
        more expected shocks lower the ceiling.
        """
        lead_factor = 1.0 - (self.max_lead_time / 21.0) * 0.3
        volatility_factor = 1.0 - self.mean_demand_volatility * 0.5
        shock_factor = max(0.5, 1.0 - self.expected_demand_shocks * 0.05)
        return max(0.3, min(1.0, lead_factor * volatility_factor * shock_factor))


def estimate_difficulty(world: Any) -> WorldDifficulty:
    """Snapshot world difficulty from a live ``ProcurementWorld``."""
    products = list(getattr(world, "products", {}).values())
    suppliers = list(getattr(world, "suppliers", {}).values())
    config = getattr(world, "config", None)
    n_days = int(getattr(config, "days_per_quarter", 0) or 0)
    shock_p = float(getattr(config, "demand_shock_probability", 0.0) or 0.0)
    n_products = len(products)

    if n_products:
        min_stock_days = min(
            p.current_stock / max(p.base_demand_per_day, 0.01) for p in products
        )
        mean_reorder = (
            sum(
                p.reorder_point / max(p.base_demand_per_day, 0.01) for p in products
            )
            / n_products
        )
        mean_vol = sum(p.demand_volatility for p in products) / n_products
    else:
        min_stock_days = 10.0
        mean_reorder = 7.0
        mean_vol = 0.25

    return WorldDifficulty(
        max_lead_time=max((s.lead_time_days for s in suppliers), default=10),
        mean_demand_volatility=mean_vol,
        min_initial_stock_days=min_stock_days,
        mean_reorder_days=mean_reorder,
        expected_demand_shocks=n_products * n_days * shock_p,
    )


__all__ = ["WorldDifficulty", "estimate_difficulty"]
