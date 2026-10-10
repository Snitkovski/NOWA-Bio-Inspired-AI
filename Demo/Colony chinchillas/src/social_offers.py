"""Social offers and responses."""

from __future__ import annotations

from dataclasses import dataclass

from agent_knowledge import PublicState


@dataclass(frozen=True, slots=True)
class SocialOfferType:
    """Metadata for offer type."""

    duration: float
    exclusive: bool


@dataclass(slots=True)
class SocialOffer:
    """Concrete social offer sent to another agent."""

    offer_type: str
    from_id: str
    from_public: PublicState
    intensity: float


@dataclass(slots=True)
class SocialResponse:
    """Immediate response to a social offer."""

    accepted: bool
    responder_id: str
    reason: str


SOCIAL_OFFER_TYPES: dict[str, SocialOfferType] = {
    "sniff_greet": SocialOfferType(duration=5.0, exclusive=False),
    "allogroom": SocialOfferType(duration=30.0, exclusive=True),
    "play_invite": SocialOfferType(duration=20.0, exclusive=True),
    "sleep_together": SocialOfferType(duration=120.0, exclusive=False),
    "chase": SocialOfferType(duration=10.0, exclusive=True),
    "mount_display": SocialOfferType(duration=15.0, exclusive=True),
    "nurse": SocialOfferType(duration=60.0, exclusive=True),
    "share_knowledge": SocialOfferType(duration=10.0, exclusive=False),
}
