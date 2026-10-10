"""Knowledge primitives for colony agents."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from config_colony import MAX_HEARSAY_ITEMS, MAX_INTERACTION_HISTORY


@dataclass(slots=True)
class PublicState:
    """Public projection of an agent that can be perceived by others."""

    agent_id: str
    name: str
    position: str
    affect_tone: str
    current_action: str
    is_receptive: bool
    sex: str
    age_category: str
    scent_signature: str


@dataclass(slots=True)
class InteractionEpisode:
    """Single social interaction event between two agents."""

    time: float
    interaction_type: str
    initiated_by: str
    outcome: str
    affect_delta: float
    context: str


@dataclass(slots=True)
class HearsayItem:
    """Indirect information about a third-party agent."""

    subject_id: str
    source_id: str
    content: str
    time_heard: float
    confidence: float
    hops: int = 1


@dataclass(slots=True)
class KnownAgent:
    """Subjective model of another agent built from direct and indirect experience."""

    agent_id: str
    name: str
    sex: str
    last_seen_position: str
    last_seen_time: float
    position_confidence: float = 1.0
    affinity: float = 0.0
    dominance_felt: float = 0.0
    trust: float = 0.5
    interaction_history: deque[InteractionEpisode] = field(
        default_factory=lambda: deque(maxlen=MAX_INTERACTION_HISTORY)
    )
    positive_count: int = 0
    negative_count: int = 0
    hearsay: list[HearsayItem] = field(default_factory=list)
    relationship_type: str = "stranger"
    familiarity: float = 0.0
    memory_confidence: float = 1.0
    is_mate: bool = False
    shared_offspring: list[str] = field(default_factory=list)
    last_seen_affect: str = "calm"

    def record_episode(self, episode: InteractionEpisode) -> None:
        """Store interaction and update summary counters."""
        self.interaction_history.append(episode)
        if episode.outcome in {"accepted", "completed"}:
            self.positive_count += 1
        elif episode.outcome in {"rejected", "timeout", "interrupted"}:
            self.negative_count += 1

        self._recompute_relationship()

    def add_hearsay(self, hearsay: HearsayItem) -> None:
        """Store hearsay and keep bounded memory."""
        self.hearsay.append(hearsay)
        if len(self.hearsay) > MAX_HEARSAY_ITEMS:
            self.hearsay.pop(0)

    def decay(self, current_time: float, dt: float) -> None:
        """Age knowledge confidence over simulation time."""
        age_since_seen = max(0.0, current_time - self.last_seen_time)
        # Faster practical decay for simulation testability.
        self.position_confidence *= 0.45 ** (dt / 120.0)
        self.memory_confidence *= 0.9999**dt

        if age_since_seen > 600.0:
            self.affinity *= 0.999

        self.hearsay = [h for h in self.hearsay if current_time - h.time_heard < 3600.0]
        self._recompute_relationship()

    def _recompute_relationship(self) -> None:
        """Update coarse relationship state from affinity/familiarity."""
        if self.relationship_type == "kin":
            return
        if self.is_mate:
            self.relationship_type = "mate"
            return
        if self.affinity < -0.5:
            self.relationship_type = "rival"
            return
        if self.affinity > 0.6 and self.familiarity > 0.4:
            self.relationship_type = "bonded"
            return
        if self.familiarity > 0.0:
            self.relationship_type = "acquaintance"
            return
        self.relationship_type = "stranger"


@dataclass(slots=True)
class PerceivedOther:
    """Result of one perception step for another agent."""

    agent_id: str
    category: str
    public_state: PublicState
    known: KnownAgent | None
