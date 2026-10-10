"""Shared social layer primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PendingOffer:
    """Offer awaiting response and subject to timeout."""

    offer_type: str
    target_id: str
    started_at: float
