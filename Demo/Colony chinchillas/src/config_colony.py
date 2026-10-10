"""Configuration constants for colony simulation."""

from __future__ import annotations

from typing import Final

MATURITY_AGE_S: Final[float] = 900.0
GESTATION_S: Final[float] = 300.0
HEAT_CYCLE_LENGTH_S: Final[float] = 600.0
ESTRUS_DURATION_S: Final[float] = 180.0
# More frequent refill keeps medium/large colonies sustainable.
REFILL_DAY_S: Final[float] = 600.0
OFFER_TIMEOUT_S: Final[float] = 10.0
# Lifespan is controlled by mortality dynamics and step-based compatibility limit.
COLONY_MAX_LIFESPAN_STEPS: Final[int] = 20000
# Global resource drain multiplier for colony balancing in dense populations.
RESOURCE_CONSUMPTION_MULTIPLIER: Final[float] = 2.0

MAX_INTERACTION_HISTORY: Final[int] = 50
MAX_HEARSAY_ITEMS: Final[int] = 20
MAX_AGENTS_DEMO: Final[int] = 8

LITTER_SIZE: Final[tuple[int, int]] = (1, 3)

NAME_POOL: Final[list[str]] = [
    "Luna",
    "Burya",
    "Orekh",
    "Milo",
    "Aster",
    "Nori",
    "Sora",
    "Vega",
]

OFFER_COOLDOWNS: Final[dict[str, float]] = {
    "sniff_greet": 30.0,
    "allogroom": 60.0,
    "chase": 120.0,
    "mount_display": 45.0,
}

JUVENILE_BLOCKED_OFFERS: Final[set[str]] = {
    "mount_display",
    "chase",
    "territorial_patrol",
    "hyperactivity",
}
