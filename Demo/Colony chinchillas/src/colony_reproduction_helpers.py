"""Helpers for reproduction mechanics."""

from __future__ import annotations

import random

from config_colony import LITTER_SIZE


def resource_blocks_reproduction(food_pellets: float) -> bool:
    """Reproduction is blocked when food level is critically low."""
    return food_pellets < 0.15


def choose_litter_size(rng: random.Random | None = None) -> int:
    """Pick offspring count for one birth event."""
    random_source = rng if rng is not None else random
    return random_source.randint(*LITTER_SIZE)


def inherit_scalar(
    mother_value: float,
    father_value: float | None,
    *,
    noise_sigma: float = 0.05,
    rng: random.Random | None = None,
) -> float:
    """Simple average inheritance with gaussian noise."""
    random_source = rng if rng is not None else random
    if father_value is None:
        base = mother_value
    else:
        base = (mother_value + father_value) / 2.0
    inherited = base + random_source.gauss(0.0, noise_sigma)
    return max(0.0, min(1.0, inherited))
