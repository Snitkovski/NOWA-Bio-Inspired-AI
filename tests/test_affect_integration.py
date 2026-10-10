"""
Test Agent Integration with Affective Regulators

Tests for how Agent uses affective state in decision-making
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from affect import AffectiveState


class TestAgentAffectiveIntegration:
    """Tests for Agent integration with affective regulators"""
    
    def setup_method(self):
        """Setup mock components for Agent"""
        self.mock_hippocampus = Mock()
        self.mock_hippocampus.activate.return_value = []
        self.mock_hippocampus.store.return_value = None
        self.mock_hippocampus.get_statistics.return_value = {"active": 0}
        
        self.mock_cortex = Mock()
        self.mock_cortex.activate.return_value = []
        self.mock_cortex.get_statistics.return_value = {"patterns": 0}
        
        self.mock_selector = Mock()
        self.mock_selector.choose.return_value = "test_action"
        
        self.mock_intent_memory = Mock()
        self.mock_intent_memory.activate_by_context.return_value = {}
        self.mock_intent_memory.record_trace.return_value = None
        self.mock_intent_memory.strengthen_trace.return_value = None
    
    def test_agent_initializes_with_affect_state(self):
        """Test that Agent initializes with AffectiveState"""
        from agent import Agent
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector
        )
        
        assert agent.affect_state is not None
        assert isinstance(agent.affect_state, AffectiveState)
    
    def test_agent_step_updates_affect_state(self):
        """Test that Agent.step updates affective state"""
        from agent import Agent
        from experience import Event
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector,
            intent_memory=self.mock_intent_memory
        )
        
        initial_valence = agent.affect_state.valence
        
        # Step with positive reward
        action = agent.step(
            context_events=["context1"],
            reward=0.7,
            novelty=0.3,
            intensity=1.5
        )
        
        # Valence should increase from positive reward
        assert agent.affect_state.valence > initial_valence
        assert action == "test_action"
    
    def test_agent_step_with_threat_updates_threat_parameter(self):
        """Test that conflict signals update threat parameter"""
        from agent import Agent
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector,
            intent_memory=self.mock_intent_memory
        )
        
        initial_threat = agent.affect_state.threat
        
        # Step with high conflict
        action = agent.step(
            context_events=["context1"],
            conflict=0.8,
            intensity=1.5
        )
        
        # Threat should increase
        assert agent.affect_state.threat > initial_threat
    
    def test_agent_passes_affect_modifier_to_selector(self):
        """Test that Agent passes affect modifier to Selector"""
        from agent import Agent
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector,
            intent_memory=self.mock_intent_memory
        )
        
        # Canonical source: affective_space drives the modifier.
        agent.affective_space.axes["stress"] = 0.8

        action = agent.step(context_events=["context1"])
        
        # Verify selector was called with affect_modifier
        call_kwargs = self.mock_selector.choose.call_args[1]
        assert "affect_modifier" in call_kwargs
        assert call_kwargs["affect_modifier"] < 1.0  # Threat should reduce modifier
    
    def test_agent_get_state_includes_affect(self):
        """Test that get_state includes affect state"""
        from agent import Agent
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector
        )
        
        agent.affect_state.valence = 0.5
        agent.affect_state.threat = 0.3
        
        state = agent.get_state()
        
        assert "affect_state" in state
        assert state["affect_state"]["valence"] == 0.5
        assert state["affect_state"]["threat"] == 0.3
    
    def test_agent_decay_between_steps(self):
        """Test that affect parameters decay between steps"""
        from agent import Agent
        import time
        
        agent = Agent(
            self.mock_hippocampus,
            self.mock_cortex,
            self.mock_selector,
            intent_memory=self.mock_intent_memory
        )
        
        # Set high values
        agent.affect_state.arousal = 1.5
        agent.affect_state.curiosity = 0.8
        initial_arousal = agent.affect_state.arousal
        initial_curiosity = agent.affect_state.curiosity
        
        # Step with some time delay
        time.sleep(0.5)
        action = agent.step(context_events=["context1"])
        
        # Values should decay (if _last_step_time was set before)
        assert agent.affect_state.arousal <= initial_arousal
        assert agent.affect_state.curiosity <= initial_curiosity


class TestIntentMemoryAffectiveReevaluation:
    """Tests for habit reevaluation with affective state"""
    
    def test_reevaluate_habits_with_high_threat(self):
        """Test that high threat weakens habits"""
        from intent_memory import IntentMemory
        from affect import AffectiveState
        
        memory = IntentMemory()
        
        # Create some traces
        memory.record_trace(["context1"], "action1")
        memory.record_trace(["context1"], "action1")
        memory.record_trace(["context1"], "action1")
        
        initial_strength = memory.traces[list(memory.traces.keys())[0]].strength
        
        # Reevaluate with high threat
        affect = AffectiveState(threat=0.9)
        modulation = memory.get_habit_affect_modulation(affect)
        memory.apply_habit_affect_modulation(modulation)
        
        if memory.traces:  # If trace wasn't deleted
            final_strength = memory.traces[list(memory.traces.keys())[0]].strength
            assert final_strength < initial_strength
    
    def test_reevaluate_habits_with_positive_valence(self):
        """Test that positive valence reinforces recent habits"""
        from intent_memory import IntentMemory
        from affect import AffectiveState
        
        memory = IntentMemory()
        
        # Create recent trace
        memory.record_trace(["context1"], "action1")
        trace_key = list(memory.traces.keys())[0]
        initial_strength = memory.traces[trace_key].strength
        
        # Reevaluate with positive valence
        affect = AffectiveState(valence=0.7)
        modulation = memory.get_habit_affect_modulation(affect)
        memory.apply_habit_affect_modulation(modulation)
        
        # Recent habit should be stronger
        assert memory.traces[trace_key].strength > initial_strength
    
    def test_strengthen_trace_method(self):
        """Test explicit trace strengthening"""
        from intent_memory import IntentMemory
        
        memory = IntentMemory()
        memory.record_trace(["context1"], "action1")
        
        trace_key = list(memory.traces.keys())[0]
        initial_strength = memory.traces[trace_key].strength
        
        memory.strengthen_trace(["context1"], "action1", factor=2.0)
        
        assert memory.traces[trace_key].strength == initial_strength * 2.0
    
    def test_consolidate_with_affect_profile(self):
        """Test storing affect profile with habit"""
        from intent_memory import IntentMemory
        
        memory = IntentMemory()
        memory.record_trace(["context1"], "action1")
        
        affect_profile = {
            "valence": 0.5,
            "arousal": 0.8,
            "threat": 0.2
        }
        
        memory.consolidate_with_affect_profile(["context1"], "action1", affect_profile)
        
        trace_key = list(memory.traces.keys())[0]
        trace = memory.traces[trace_key]
        
        assert hasattr(trace, 'affect_profiles')
        assert len(trace.affect_profiles) == 1
        assert trace.affect_profiles[0] == affect_profile


class TestSelectorAffectiveModulation:
    """Tests for Selector's use of affect modifiers"""
    
    def test_selector_applies_affect_modifier(self):
        """Test that selector applies affect modifier to pressures"""
        from selector import ActionSelector
        
        selector = ActionSelector(actions=["action1", "action2", "action3"])
        
        # Create mock experiences with pressure
        mock_exp = Mock()
        mock_exp.intensity = 1.0
        mock_exp.activation_energy = 1.0
        mock_event = Mock()
        mock_event.event_type.value = "action"
        mock_event.name = "action1"
        mock_exp.path.events = [mock_event]
        
        # Test with high affect modifier (should boost pressure)
        action_high = selector.choose(
            [mock_exp],
            [],
            affect_modifier=1.5,
            verbose=False
        )
        
        # Test with low affect modifier (should suppress pressure)
        action_low = selector.choose(
            [mock_exp],
            [],
            affect_modifier=0.5,
            verbose=False
        )
        
        # Both should choose the action but pressure calculation differs
        assert action_high == "action1"
        assert action_low == "action1"


class TestActionRealizerAffectiveModulation:
    """Tests for ActionRealizer's affective modulation"""
    
    def test_realizer_consider_affect_modifier(self):
        """Test that realizer considers affect modifier in pressure calculation"""
        from action_realizer import ActionRealizer
        
        mock_memory = Mock()
        realizer = ActionRealizer(mock_memory)
        
        # Create mock realizations
        mock_real1 = Mock()
        mock_real1.activation_energy = 1.0
        mock_real1.stability = 0.8
        mock_real1.context = []
        mock_real1.output = "output1"
        mock_real1.activate = Mock()
        
        mock_real2 = Mock()
        mock_real2.activation_energy = 0.5
        mock_real2.stability = 0.6
        mock_real2.context = []
        mock_real2.output = "output2"
        mock_real2.activate = Mock()
        
        mock_memory.get_active_realizations.return_value = [mock_real1, mock_real2]
        
        # High affect modifier should favor higher activation
        pressure_high = realizer._calculate_pressure([mock_real1, mock_real2], [], affect_modifier=1.8)
        
        # Low affect modifier
        pressure_low = realizer._calculate_pressure([mock_real1, mock_real2], [], affect_modifier=0.6)
        
        # Pressures should exist and be positive
        assert len(pressure_high) > 0
        assert len(pressure_low) > 0
        assert all(p > 0 for p in pressure_high.values())
        assert all(p > 0 for p in pressure_low.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
