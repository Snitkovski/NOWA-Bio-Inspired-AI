"""
AffectiveState - Affective regulators for NOWA adaptive behavior.

Core principle: Affective regulators are NOT feelings, emotions, or subjective states.
They are operational parameters that:
- Modulate behavior selection
- Influence learning and habit consolidation
- Enable adaptation without claiming subjective experience

Strict rules:
- NO claims of subjective experience
- NO emotional narratives
- NO descriptions as "feels" or "senses"
- Only operational descriptions: numbers, vectors, mechanisms
"""

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AffectiveState:
    """
    Operational affective regulatory parameters.
    
    NOT emotions or feelings - these are control signals for behavior adaptation.
    """
    
    # Core dimensions
    valence: float = 0.0        # General direction: negative (-1.0) to positive (+1.0)
    arousal: float = 0.0        # Intensity/activation level (0.0 to 2.0)
    threat: float = 0.0         # Risk/conflict detection (0.0 to 1.0)
    curiosity: float = 0.1      # Novelty/exploration drive (0.0 to 1.0) - slight base to encourage exploration
    
    # Entity associations
    attachment: Dict[str, float] = field(default_factory=dict)  # entity_id -> strength
    affinity: Dict[str, float] = field(default_factory=dict)    # positive association
    aversion: Dict[str, float] = field(default_factory=dict)    # negative association
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    # Temporal aggregates (for Plan A)
    affect_trend: Dict[str, float] = field(default_factory=dict)
    affect_baseline: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure values are within bounds"""
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(2.0, self.arousal))
        self.threat = max(0.0, min(1.0, self.threat))
        self.curiosity = max(0.0, min(1.0, self.curiosity))
    
    def snapshot(self) -> dict:
        """Return operational state snapshot (immutable dict representation)"""
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "threat": self.threat,
            "curiosity": self.curiosity,
            "attachment": dict(self.attachment),
            "affinity": dict(self.affinity),
            "aversion": dict(self.aversion),
            "timestamp": self.timestamp,
            "affect_trend": dict(self.affect_trend),
            "affect_baseline": dict(self.affect_baseline)
        }
    
    def update_from_reward(self, reward: float, intensity: float = 1.0):
        """
        Update regulatory state based on reward signal.
        
        Args:
            reward: Outcome value (-1.0 to +1.0)
            intensity: Strength of the outcome (0.0 to 2.0)
        """
        # Valence direction
        self.valence = max(-1.0, min(1.0, self.valence + reward * 0.3))
        
        # Arousal from intensity
        self.arousal = max(0.0, min(2.0, self.arousal + abs(reward) * intensity * 0.2))
        
        # Threat reduction on positive reward
        if reward > 0.5:
            self.threat = max(0.0, self.threat - 0.1)
        elif reward < -0.5:
            self.threat = min(1.0, self.threat + 0.15)
        
        self.timestamp = time.time()
    
    def update_from_novelty(self, novelty: float):
        """
        Update curiosity and arousal from novelty signal.
        
        Args:
            novelty: Degree of unexpectedness (0.0 to 1.0)
        """
        # Curiosity grows from novelty to encourage exploration.
        # Use a conservative growth rate to avoid overly rapid increases.
        self.curiosity = min(1.0, self.curiosity + novelty * 0.25)
        self.arousal = min(2.0, self.arousal + novelty * 0.10)
        self.timestamp = time.time()
    
    def update_from_conflict(self, conflict_level: float):
        """
        Update threat and arousal from conflict detection.
        
        Args:
            conflict_level: Magnitude of detected conflict (0.0 to 1.0)
        """
        self.threat = min(1.0, self.threat + conflict_level * 0.3)
        self.arousal = min(2.0, self.arousal + conflict_level * 0.2)
        self.valence = max(-1.0, self.valence - conflict_level * 0.15)
        self.timestamp = time.time()
    
    def decay_over_time(self, time_elapsed: float, half_life: float = 300.0):
        """
        Apply exponential decay to regulatory parameters during waking.
        
        Args:
            time_elapsed: Seconds since last update
            half_life: Time (seconds) for 50% decay
        """
        decay_factor = 2.0 ** (-time_elapsed / half_life)
        
        self.valence *= decay_factor
        self.arousal *= decay_factor
        self.threat *= decay_factor
        self.curiosity *= decay_factor
        
        # Decay entity associations
        decay_strength = 0.95 ** (time_elapsed / half_life)
        for entity in self.attachment:
            self.attachment[entity] *= decay_strength
        for entity in self.affinity:
            self.affinity[entity] *= decay_strength
        for entity in self.aversion:
            self.aversion[entity] *= decay_strength
    
    def record_association(self, entity_id: str, valence_contribution: float, 
                          relationship_type: str = "attachment"):
        """
        Record association between entity and regulatory state.
        
        Args:
            entity_id: Identifier of the entity
            valence_contribution: How this entity affects valence (-1.0 to +1.0)
            relationship_type: 'attachment', 'affinity', or 'aversion'
        """
        if relationship_type == "attachment":
            self.attachment[entity_id] = self.attachment.get(entity_id, 0.0) + 0.1
        elif relationship_type == "affinity" and valence_contribution > 0:
            self.affinity[entity_id] = self.affinity.get(entity_id, 0.0) + valence_contribution
        elif relationship_type == "aversion" and valence_contribution < 0:
            self.aversion[entity_id] = self.aversion.get(entity_id, 0.0) - valence_contribution
    
    def get_action_pressure_modifier(self) -> float:
        """
        Calculate how current state modifies action selection pressure.
        
        Higher threat reduces risky actions.
        Higher curiosity increases exploratory actions.
        Higher arousal increases action decisiveness.
        
        Returns:
            Modifier (0.1 to 2.0) to apply to action pressures
        """
        # Threat suppresses risky behavior
        threat_suppression = 1.0 - (self.threat * 0.3)
        
        # Curiosity encourages exploration
        curiosity_boost = 1.0 + (self.curiosity * 0.2)
        
        # Arousal increases decisiveness
        arousal_boost = 1.0 + (self.arousal * 0.1)
        
        modifier = threat_suppression * curiosity_boost * arousal_boost
        return max(0.1, min(2.0, modifier))
    
    def get_habit_reinforcement_modifier(self, habit_strength: float) -> float:
        """
        FIXED (Spec #1, #2): Get MODULATION multiplier for habit reinforcement (0.0 to 2.0).
        
        Replaces boolean should_reinforce_habit() which violated decision-making rules.
        Returns multiplier that caller applies to habit updates, not binary decision.
        
        Habits are reinforced when:
        - Positive valence (increases modifier)
        - Low threat (decreases modifier)
        - High readiness (increases precision)
        
        Returns:
            Multiplier [0.0 to 2.0] to apply to habit learning
        """
        # Base modifier from valence
        valence_mod = 1.0 + self.valence * 0.5  # [-0.5 to +1.5]
        
        # Threat reduces modifier
        threat_mod = 1.0 - self.threat * 0.5   # [0.5 to 1.0]
        
        # Combine
        combined = valence_mod * threat_mod
        
        # Clamp and ensure non-negative
        return max(0.0, min(2.0, combined))
        return False
    
    def conflict_severity(self) -> float:
        """Return scalar measure of internal conflict (0.0 to 1.0)"""
        return min(1.0, (self.threat * 0.5) + (abs(self.valence) * 0.3))
    
    def adaptation_readiness(self) -> float:
        """
        Return readiness to adapt behavior patterns.
        
        High when: low threat, moderate arousal, positive valence
        Low when: high threat or conflict
        
        Returns:
            Scalar 0.0 to 1.0
        """
        readiness = (1.0 - self.threat) * (1.0 - self.conflict_severity())
        return max(0.0, min(1.0, readiness))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "threat": self.threat,
            "curiosity": self.curiosity,
            "attachment": dict(self.attachment),
            "affinity": dict(self.affinity),
            "aversion": dict(self.aversion),
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AffectiveState":
        """Reconstruct from dictionary"""
        state = cls()
        state.valence = data.get("valence", 0.0)
        state.arousal = data.get("arousal", 0.0)
        state.threat = data.get("threat", 0.0)
        state.curiosity = data.get("curiosity", 0.0)
        state.attachment = dict(data.get("attachment", {}))
        state.affinity = dict(data.get("affinity", {}))
        state.aversion = dict(data.get("aversion", {}))
        state.timestamp = data.get("timestamp", time.time())
        return state
    
    def describe(self) -> str:
        """
        Operational description of state (NOT subjective narrative).
        
        Returns:
            Machine-readable operational description
        """
        return (
            f"AffectiveState(valence={self.valence:.2f}, "
            f"arousal={self.arousal:.2f}, "
            f"threat={self.threat:.2f}, "
            f"curiosity={self.curiosity:.2f}, "
            f"conflict={self.conflict_severity():.2f}, "
            f"adaptation_ready={self.adaptation_readiness():.2f})"
        )
