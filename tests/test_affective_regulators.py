"""
Test Affective Regulators Integration

Comprehensive test suite for affective state management and integration
with NOWA cognitive system.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
from affect import AffectiveState
from self_model import SelfModel


class TestAffectiveState:
    """Tests for AffectiveState operational parameters"""
    
    def test_affective_state_initialization(self):
        """Test that affective state initializes with correct bounds"""
        state = AffectiveState()
        assert state.valence == 0.0
        assert state.arousal == 0.0
        assert state.threat == 0.0
        assert state.curiosity == 0.1  # Now starts with slight base (0.1) to encourage exploration
        assert isinstance(state.attachment, dict)
        assert isinstance(state.affinity, dict)
        assert isinstance(state.aversion, dict)
    
    def test_affective_state_bounds(self):
        """Test that affective state respects operational bounds"""
        state = AffectiveState(valence=2.0, arousal=3.0, threat=2.0, curiosity=2.0)
        assert -1.0 <= state.valence <= 1.0
        assert 0.0 <= state.arousal <= 2.0
        assert 0.0 <= state.threat <= 1.0
        assert 0.0 <= state.curiosity <= 1.0
    
    def test_update_from_reward_positive(self):
        """Test positive reward updates valence and reduces threat"""
        state = AffectiveState()
        state.threat = 0.8
        state.update_from_reward(reward=0.8, intensity=1.5)
        
        assert state.valence > 0.0
        assert state.arousal > 0.0
        assert state.threat < 0.8  # Threat should decrease
    
    def test_update_from_reward_negative(self):
        """Test negative reward updates valence negatively and increases threat"""
        state = AffectiveState()
        state.update_from_reward(reward=-0.9, intensity=1.5)
        
        assert state.valence < 0.0
        assert state.threat > 0.0
    
    def test_update_from_novelty(self):
        """Test novelty increases curiosity and arousal"""
        state = AffectiveState()
        initial_curiosity = state.curiosity
        initial_arousal = state.arousal
        
        state.update_from_novelty(novelty=0.7)
        
        assert state.curiosity > initial_curiosity
        assert state.arousal > initial_arousal
    
    def test_update_from_conflict(self):
        """Test conflict increases threat and arousal"""
        state = AffectiveState()
        initial_threat = state.threat
        initial_arousal = state.arousal
        
        state.update_from_conflict(conflict_level=0.6)
        
        assert state.threat > initial_threat
        assert state.arousal > initial_arousal
    
    def test_decay_over_time(self):
        """Test exponential decay of regulatory parameters"""
        state = AffectiveState(valence=0.8, arousal=1.5, threat=0.7, curiosity=0.9)
        state.decay_over_time(time_elapsed=300.0, half_life=300.0)
        
        # After one half-life, values should be ~0.5 of original
        assert state.valence < 0.5
        assert state.arousal < 1.0
        assert state.threat < 0.5
        assert state.curiosity < 0.5
    
    def test_action_pressure_modifier(self):
        """Test that affect state produces correct pressure modifiers"""
        # High threat should suppress
        state_high_threat = AffectiveState(threat=0.9)
        modifier_threat = state_high_threat.get_action_pressure_modifier()
        assert modifier_threat < 1.0
        
        # High curiosity should boost
        state_curious = AffectiveState(curiosity=0.8)
        modifier_curious = state_curious.get_action_pressure_modifier()
        assert modifier_curious > 1.0
    
    def test_habit_reinforcement_modifier(self):
        """Test habit reinforcement modulation (returns float, not boolean)"""
        # High threat reduces reinforcement
        state_threat = AffectiveState(threat=0.8)
        modifier_threat = state_threat.get_habit_reinforcement_modifier(1.0)
        assert 0.0 <= modifier_threat < 1.0  # Reduced multiplier
        
        # Positive valence increases reinforcement
        state_positive = AffectiveState(valence=0.7)
        modifier_positive = state_positive.get_habit_reinforcement_modifier(1.0)
        assert modifier_positive > 1.0  # Increased multiplier
    
    def test_conflict_severity(self):
        """Test conflict severity calculation"""
        state = AffectiveState()
        assert state.conflict_severity() >= 0.0
        
        state.threat = 1.0
        severity_high_threat = state.conflict_severity()
        assert severity_high_threat > 0.3
    
    def test_adaptation_readiness(self):
        """Test system readiness for adaptation"""
        # Low threat, positive valence = high readiness
        state_ready = AffectiveState(threat=0.1, valence=0.5)
        readiness_high = state_ready.adaptation_readiness()
        assert readiness_high > 0.6
        
        # High threat = low readiness
        state_threatened = AffectiveState(threat=0.9)
        readiness_low = state_threatened.adaptation_readiness()
        assert readiness_low < 0.5
    
    def test_entity_associations(self):
        """Test recording entity associations"""
        state = AffectiveState()
        state.record_association("entity_1", valence_contribution=0.8, relationship_type="affinity")
        
        assert "entity_1" in state.affinity
        assert state.affinity["entity_1"] > 0.0
    
    def test_snapshot_immutability(self):
        """Test that snapshot is truly immutable"""
        state = AffectiveState(valence=0.5)
        snapshot = state.snapshot()
        
        # Modify state
        state.valence = -0.5
        
        # Snapshot should be unchanged
        assert snapshot["valence"] == 0.5
    
    def test_serialization(self):
        """Test to_dict and from_dict roundtrip"""
        state1 = AffectiveState(valence=0.3, threat=0.7, arousal=1.2)
        state1_dict = state1.to_dict()
        state2 = AffectiveState.from_dict(state1_dict)
        
        assert state1.valence == state2.valence
        assert state1.threat == state2.threat
        assert state1.arousal == state2.arousal


class TestSelfModel:
    """Tests for SelfModel operational introspection"""
    
    def setup_method(self):
        """Create mock agent for testing"""
        self.mock_agent = Mock()
        self.mock_agent.affect_state = AffectiveState()
        self.mock_agent.get_state.return_value = {
            "hippocampus": {"active": 5},
            "cortex": {"patterns": 3},
            "affect_state": self.mock_agent.affect_state.snapshot()
        }
    
    def test_self_model_initialization(self):
        """Test that SelfModel initializes correctly"""
        model = SelfModel(self.mock_agent)
        assert model.agent == self.mock_agent
        assert model.observation_history == []
        assert model.max_history == 100
    
    def test_snapshot(self):
        """Test operational state snapshot"""
        model = SelfModel(self.mock_agent)
        snapshot = model.snapshot()
        
        assert "type" in snapshot
        assert snapshot["type"] == "affective-regulatory-system"
        assert "operational_state" in snapshot
        assert "timestamp" in snapshot
    
    def test_describe_operational_state(self):
        """Test operational state description (no subjective language)"""
        model = SelfModel(self.mock_agent)
        description = model.describe_operational_state()
        
        # Should contain operational metrics
        assert "valence" in description
        assert "arousal" in description
        assert "threat" in description
        
        # Should NOT contain subjective language
        assert "feel" not in description.lower()
        assert "emotion" not in description.lower()
    
    def test_limiting_factors_analysis(self):
        """Test identification of limiting factors"""
        model = SelfModel(self.mock_agent)
        
        # No limiting factors when all normal
        self.mock_agent.affect_state = AffectiveState()
        factors = model.report_limiting_factors()
        assert factors.get("status") == "no_limiting_factors" or len(factors) == 0
        
        # High threat should be limiting
        self.mock_agent.affect_state = AffectiveState(threat=0.8)
        factors = model.report_limiting_factors()
        assert "threat_suppression" in factors
    
    def test_enabling_factors_analysis(self):
        """Test identification of enabling factors"""
        model = SelfModel(self.mock_agent)
        
        # Positive valence enables learning
        self.mock_agent.affect_state = AffectiveState(valence=0.6)
        factors = model.report_enabling_factors()
        assert "positive_valence_enabling_learning" in factors
        
        # Curiosity enables exploration
        self.mock_agent.affect_state = AffectiveState(curiosity=0.7)
        factors = model.report_enabling_factors()
        assert "curiosity_enabling_exploration" in factors
    
    def test_regulatory_pattern_analysis(self):
        """Test pattern analysis with history"""
        model = SelfModel(self.mock_agent)
        
        # Record several observations
        for i in range(5):
            self.mock_agent.affect_state.valence = -0.5 + (i * 0.2)
            model.record_observation()
            time.sleep(0.01)
        
        analysis = model.analyze_regulatory_pattern()
        assert "valence_trend" in analysis
        assert "arousal_stability" in analysis
        assert "threat_accumulation" in analysis
    
    def test_introspection_report(self):
        """Test comprehensive introspection report"""
        model = SelfModel(self.mock_agent)
        report = model.introspect()
        
        # Check all required keys
        assert "operational_description" in report
        assert "current_snapshot" in report
        assert "regulatory_analysis" in report
        assert "limiting_factors" in report
        assert "enabling_factors" in report
        assert "system_type" in report
        
        # Verify system type
        assert report["system_type"] == "affective-regulatory-nowa-system"
    
    def test_readiness_report(self):
        """Test behavioral readiness assessment"""
        model = SelfModel(self.mock_agent)
        
        # High readiness
        self.mock_agent.affect_state = AffectiveState(threat=0.1, valence=0.6)
        report_high = model.get_regulatory_readiness_report()
        assert report_high["readiness_level"] in ["high", "moderate"]
        assert report_high["readiness_score"] > 0.5
        
        # Low readiness
        self.mock_agent.affect_state = AffectiveState(threat=0.9)
        report_low = model.get_regulatory_readiness_report()
        assert report_low["readiness_level"] == "low"
        assert report_low["readiness_score"] < 0.5


class TestAffectiveIntegration:
    """Integration tests for affective system with agent components"""
    
    def test_affect_state_bounds_enforcement(self):
        """Test that all affect parameters stay within bounds"""
        state = AffectiveState()
        
        # Try extreme values
        state.valence = 100.0
        state.arousal = 100.0
        state.threat = 100.0
        state.curiosity = 100.0
        
        # Re-validate on post_init (simulate construction)
        state.__post_init__()
        
        assert -1.0 <= state.valence <= 1.0
        assert 0.0 <= state.arousal <= 2.0
        assert 0.0 <= state.threat <= 1.0
        assert 0.0 <= state.curiosity <= 1.0
    
    def test_affect_consistency_after_multiple_updates(self):
        """Test that affect state remains consistent after multiple operations"""
        state = AffectiveState()
        
        for _ in range(10):
            state.update_from_reward(0.5, 1.0)
            state.update_from_novelty(0.3)
            state.update_from_conflict(0.2)
            state.decay_over_time(10.0)
        
        # All values should still be in bounds
        assert -1.0 <= state.valence <= 1.0
        assert 0.0 <= state.arousal <= 2.0
        assert 0.0 <= state.threat <= 1.0
        assert 0.0 <= state.curiosity <= 1.0
    
    def test_describe_never_uses_subjective_language(self):
        """Test that descriptions never anthropomorphize"""
        state = AffectiveState(valence=0.9, threat=0.1)
        description = state.describe()
        
        subjective_words = ["feel", "emotion", "think", "want", "like", "prefer", "fear", "love"]
        for word in subjective_words:
            assert word not in description.lower(), f"Found subjective word '{word}' in description"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
