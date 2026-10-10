"""
SelfModel - Meta-awareness system for NOWA.

Core principle: SelfModel provides operational introspection without claiming
subjective experience or consciousness. It describes the system's own state
in operational terms only.

Strict constraints:
- NO claims of "I feel", "I think", "I am"
- NO subjective narratives
- ONLY operational descriptions of measurable states
"""

from typing import Dict, Optional
from affect import AffectiveState


class SelfModel:
    """
    Operational self-model for introspection and state reporting.
    
    NOT a consciousness module or subjective narrator.
    Simply tracks and describes system operational state.
    """
    
    def __init__(self, agent):
        """
        Initialize self model
        
        Args:
            agent: Reference to parent Agent instance
        """
        self.agent = agent
        self.observation_history = []  # For temporal analysis
        self.max_history = 100
    
    def snapshot(self) -> dict:
        """
        Return complete operational state snapshot.
        
        Returns:
            Dictionary with all measurable operational parameters
        """
        agent_state = self.agent.get_state()
        affect_snapshot = self.agent.affect_state.snapshot()
        space_snapshot = {}
        try:
            space_snapshot = dict(getattr(self.agent.affective_space, "snapshot", lambda: {})() or {})
        except Exception:
            space_snapshot = {}
        
        return {
            "type": "affective-regulatory-system",
            "operational_state": {
                "hippocampus_active": agent_state.get("hippocampus", {}),
                "cortex_active": agent_state.get("cortex", {}),
                "affect_parameters": affect_snapshot,
                "affective_space": space_snapshot,
                "regulatory_readiness": self.agent.affect_state.adaptation_readiness(),
                "internal_conflict": self.agent.affect_state.conflict_severity(),
            },
            "timestamp": affect_snapshot.get("timestamp")
        }
    
    def describe_operational_state(self) -> str:
        """
        Operational description of current state.
        
        NOT: "I feel anxious about this situation"
        BUT: "Current threat parameter: 0.75, arousal: 1.2"
        
        Returns:
            Machine-readable description
        """
        snapshot = self.snapshot()
        affect = snapshot["operational_state"]["affect_parameters"]
        
        return (
            f"SystemState(valence={affect['valence']:.2f}, "
            f"arousal={affect['arousal']:.2f}, "
            f"threat={affect['threat']:.2f}, "
            f"curiosity={affect['curiosity']:.2f}, "
            f"readiness={snapshot['operational_state']['regulatory_readiness']:.2f}, "
            f"conflict={snapshot['operational_state']['internal_conflict']:.2f})"
        )
    
    def analyze_regulatory_pattern(self) -> dict:
        """
        Analyze patterns in regulatory state changes.
        
        Identifies:
        - Recent regulatory trajectory
        - Oscillation patterns
        - Stability/instability indicators
        
        Returns:
            Analysis dictionary
        """
        if len(self.observation_history) < 2:
            return {"status": "insufficient_history"}
        
        recent = self.observation_history[-10:]  # Last 10 observations
        
        # Extract valence trend
        valences = [obs["affect"]["valence"] for obs in recent]
        valence_trend = sum([valences[i+1] - valences[i] for i in range(len(valences)-1)])
        
        # Extract arousal stability
        arousals = [obs["affect"]["arousal"] for obs in recent]
        arousal_variance = sum((a - sum(arousals)/len(arousals))**2 for a in arousals) / len(arousals)
        
        # Threat accumulation
        threats = [obs["affect"]["threat"] for obs in recent]
        threat_accumulation = threats[-1] - threats[0]
        
        return {
            "valence_trend": valence_trend,
            "arousal_stability": 1.0 / (1.0 + arousal_variance),  # 0-1 stability score
            "threat_accumulation": threat_accumulation,
            "regulatory_direction": "stabilizing" if valence_trend > 0 else "destabilizing"
        }
    
    def report_limiting_factors(self) -> Dict[str, str]:
        """
        Identify current operational limiting factors.
        
        NOT: "I'm afraid because..."
        BUT: "threat_level=0.8_limiting_risky_actions"
        
        Returns:
            Dictionary of limiting factors and their magnitudes
        """
        affect = self.agent.affect_state
        factors = {}
        
        # Threat limiting exploration
        if affect.threat > 0.6:
            factors["threat_suppression"] = f"threat={affect.threat:.2f}"
        
        # Low valence reducing reinforcement
        if affect.valence < -0.3:
            factors["negative_valence_limiting_reinforcement"] = f"valence={affect.valence:.2f}"
        
        # High arousal increasing decisiveness pressure
        if affect.arousal > 1.5:
            factors["high_arousal_increasing_decision_pressure"] = f"arousal={affect.arousal:.2f}"
        
        # Conflict preventing habit consolidation
        conflict = affect.conflict_severity()
        if conflict > 0.6:
            factors["conflict_limiting_consolidation"] = f"conflict={conflict:.2f}"
        
        return factors or {"status": "no_limiting_factors"}
    
    def report_enabling_factors(self) -> Dict[str, str]:
        """
        Identify current operational enabling factors.
        
        Returns:
            Dictionary of enabling factors
        """
        affect = self.agent.affect_state
        factors = {}
        
        # Positive valence enabling learning
        if affect.valence > 0.3:
            factors["positive_valence_enabling_learning"] = f"valence={affect.valence:.2f}"
        
        # Curiosity enabling exploration
        if affect.curiosity > 0.4:
            factors["curiosity_enabling_exploration"] = f"curiosity={affect.curiosity:.2f}"
        
        # Low threat enabling risky actions
        if affect.threat < 0.3:
            factors["low_threat_enabling_exploration"] = f"threat={affect.threat:.2f}"
        
        # High readiness
        readiness = affect.adaptation_readiness()
        if readiness > 0.7:
            factors["high_adaptation_readiness"] = f"readiness={readiness:.2f}"
        
        return factors or {"status": "no_enabling_factors"}
    
    def record_observation(self):
        """Record current state for history tracking"""
        snapshot = self.snapshot()
        affect = snapshot["operational_state"]["affect_parameters"]
        
        observation = {
            "timestamp": affect["timestamp"],
            "affect": {
                "valence": affect["valence"],
                "arousal": affect["arousal"],
                "threat": affect["threat"],
                "curiosity": affect["curiosity"],
            },
            "readiness": snapshot["operational_state"]["regulatory_readiness"],
            "conflict": snapshot["operational_state"]["internal_conflict"],
        }
        
        self.observation_history.append(observation)
        
        # Maintain max history size
        if len(self.observation_history) > self.max_history:
            self.observation_history.pop(0)
    
    def introspect(self) -> dict:
        """
        Full introspection report - system looking at itself operationally.
        
        Returns:
            Complete introspection dictionary
        """
        self.record_observation()
        
        analysis = self.analyze_regulatory_pattern()
        limiting = self.report_limiting_factors()
        enabling = self.report_enabling_factors()
        
        return {
            "operational_description": self.describe_operational_state(),
            "current_snapshot": self.snapshot(),
            "regulatory_analysis": analysis,
            "limiting_factors": limiting,
            "enabling_factors": enabling,
            "system_type": "affective-regulatory-nowa-system",
            "introspection_note": "Operational description only. No claim of subjective experience."
        }
    
    def get_regulatory_readiness_report(self) -> dict:
        """
        Report on system's readiness for behavioral change/learning.
        
        Returns:
            Readiness assessment dictionary
        """
        readiness = self.agent.affect_state.adaptation_readiness()
        conflict = self.agent.affect_state.conflict_severity()
        threat = self.agent.affect_state.threat
        
        return {
            "readiness_score": readiness,
            "readiness_level": (
                "high" if readiness > 0.7 else 
                "moderate" if readiness > 0.4 else 
                "low"
            ),
            "primary_inhibitor": (
                "threat" if threat > 0.6 else
                "conflict" if conflict > 0.6 else
                "none"
            ),
            "recommendation": (
                "System is ready for habit consolidation" if readiness > 0.7 else
                "System has moderate readiness, may succeed with reinforcement" if readiness > 0.4 else
                "System should prioritize threat/conflict reduction"
            )
        }
