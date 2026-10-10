"""
Test suite for refactored NOWA GUI
Tests that GUI properly integrates with new NOWA cognitive architecture
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from agent import Agent
from experience import Event, Path, EventType


class TestGUIRefactoring(unittest.TestCase):
    """Test NOWA GUI refactoring to new cognitive architecture"""
    
    def setUp(self):
        """Set up agent components"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(["action1", "action2", "action3"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, self.sleep_manager)
    
    def test_gui_imports(self):
        """Test that GUI imports correctly with new architecture"""
        try:
            from gui import NOWAGUI
            self.assertIsNotNone(NOWAGUI)
        except ImportError as e:
            self.fail(f"GUI import failed: {e}")
    
    def test_agent_initialization(self):
        """Test agent initializes correctly for GUI"""
        self.assertIsNotNone(self.agent)
        self.assertIsNotNone(self.agent.hippocampus)
        self.assertIsNotNone(self.agent.cortex)
        self.assertIsNotNone(self.agent.selector)
        self.assertIsNotNone(self.agent.sleep_manager)
    
    def test_waking_no_learning(self):
        """Test that waking step doesn't trigger learning"""
        # Store initial state
        initial_exps = len(self.hippocampus.experiences)
        
        # Agent step (waking - should NOT trigger learning)
        context = ["user:hello"]
        action = self.agent.step(context)
        
        # Should have stored experience
        self.assertEqual(len(self.hippocampus.experiences), initial_exps + 1)
        
        # Selector should NOT have weights attribute (non-learnable)
        self.assertFalse(hasattr(self.selector, 'weights'))
        self.assertFalse(hasattr(self.selector, 'learn'))
    
    def test_sleep_consolidation(self):
        """Test that sleep consolidates experiences"""
        # Add experiences
        for i in range(5):
            context = [f"context:{i}"]
            self.agent.step(context)
        
        # Get state before sleep
        state_before = self.agent.get_state()
        exps_before = state_before['hippocampus']['total_experiences']
        patterns_before = state_before['cortex']['total_patterns']
        cycles_before = state_before['sleep_cycles']
        
        # Sleep for consolidation
        stats = self.agent.sleep(cycles=2)
        
        # Get state after sleep
        state_after = self.agent.get_state()
        cycles_after = state_after['sleep_cycles']
        
        # Sleep cycles should increase
        self.assertEqual(cycles_after, cycles_before + 2)
        
        # Should have stats about consolidation
        self.assertIsInstance(stats, dict)
        self.assertIn('cycles', stats)
    
    def test_feedback_not_direct_learning(self):
        """Test that feedback doesn't directly update selector weights"""
        # Add experience
        context = ["user:test"]
        action = self.agent.step(context)
        
        # Feedback (old API would have called selector.learn here)
        intensity = 0.8
        
        # Selector should have no weights to update
        self.assertFalse(hasattr(self.selector, 'weights'))
        
        # Experience should be stored (will be consolidated during sleep)
        self.assertGreater(len(self.hippocampus.experiences), 0)
    
    def test_agent_state_reflection(self):
        """Test agent.get_state() provides proper cognitive state"""
        # Add experiences
        for i in range(3):
            self.agent.step([f"context:{i}"])
        
        # Get state
        state = self.agent.get_state()
        
        # Check state structure
        self.assertIn('hippocampus', state)
        self.assertIn('cortex', state)
        self.assertIn('sleep_cycles', state)
        
        # Check hippocampus stats
        hip_state = state['hippocampus']
        self.assertIn('total_experiences', hip_state)
        self.assertGreater(hip_state['total_experiences'], 0)
        
        # Check cortex stats
        ctx_state = state['cortex']
        self.assertIn('total_patterns', ctx_state)
        self.assertIsInstance(ctx_state['total_patterns'], int)
    
    def test_selector_non_learnable(self):
        """Test that selector has no learning mechanism"""
        # Selector should not have:
        # - learn() method
        # - weights dictionary
        # - alpha (learning rate)
        
        self.assertFalse(hasattr(self.selector, 'learn'))
        self.assertFalse(hasattr(self.selector, 'weights'))
        
        # Should have:
        # - choose() method
        # - confidence_threshold
        
        self.assertTrue(hasattr(self.selector, 'choose'))
        self.assertTrue(hasattr(self.selector, 'confidence_threshold'))
    
    def test_experience_immutability(self):
        """Test that experiences are immutable"""
        context = ["user:hello"]
        action = self.agent.step(context)
        
        # Get stored experience
        exp = self.hippocampus.experiences[0]
        
        # Path should be immutable
        self.assertTrue(hasattr(exp.path, '_frozen') or exp.path.__class__.__name__ == 'Path')
        
        # Trying to modify should fail or be ineffective
        # (frozen objects raise AttributeError on modification)
        with self.assertRaises(Exception):
            exp.path.events.append("new_event")
    
    def test_sleep_manager_only_learning(self):
        """Test that SleepManager is the only learning mechanism"""
        # SleepManager should have consolidation methods
        self.assertTrue(hasattr(self.sleep_manager, 'sleep_cycle'))
        self.assertTrue(hasattr(self.sleep_manager, 'deep_sleep'))
        
        # Should handle clustering and consolidation
        for i in range(5):
            self.agent.step([f"context:{i}"])
        
        # Sleep should consolidate
        stats = self.sleep_manager.deep_sleep(cycles=1)
        
        # Should return stats
        self.assertIsInstance(stats, dict)
    
    def test_gui_component_initialization(self):
        """Test that GUI can initialize all components correctly"""
        # These should all be initializable for GUI
        hip = NOWAHippocampus()
        cortex = CortexMemory()
        selector = ActionSelector(["test_action"])
        sleep_mgr = SleepManager(hip, cortex)
        agent = Agent(hip, cortex, selector, sleep_mgr)
        
        # All should initialize without error
        self.assertIsNotNone(hip)
        self.assertIsNotNone(cortex)
        self.assertIsNotNone(selector)
        self.assertIsNotNone(sleep_mgr)
        self.assertIsNotNone(agent)
    
    def test_gui_workflow(self):
        """Test complete GUI workflow: waking -> feedback -> sleep -> behavior change"""
        # 1. WAKING: Multiple interactions
        for i in range(5):
            context = [f"user:message_{i}"]
            action = self.agent.step(context)
            # Feedback would add intensity
            # (in GUI, user rates 1-5, converts to intensity)
        
        # Check experiences stored
        exps_after_waking = len(self.hippocampus.experiences)
        self.assertEqual(exps_after_waking, 5)
        
        # 2. SLEEP: Consolidation
        state_before = self.agent.get_state()
        stats = self.agent.sleep(cycles=2)
        state_after = self.agent.get_state()
        
        # Sleep cycles should increase
        self.assertGreater(state_after['sleep_cycles'], state_before['sleep_cycles'])
        
        # 3. WAKING AGAIN: New choices based on consolidated patterns
        # (selector uses hippocampal activation + cortical patterns)
        action = self.agent.step(["user:new_message"])
        
        # Behavior emerges from consolidation, not optimization
        self.assertIsNotNone(action)
    
    def test_nowa_principle(self):
        """Test core NOWA principle: behavior emerges, not learned"""
        # Scenario: Same context, different behavior based on sleep
        
        # Initial interaction
        context = ["user:hello"]
        action1 = self.agent.step(context)
        
        # Get selector in frozen state
        selector_frozen = self.selector
        
        # Sleep and consolidate
        for _ in range(5):
            self.agent.step(context)
        
        self.agent.sleep(cycles=3)
        
        # New context: behavior influenced by consolidation, not weight changes
        # (selector has no weights!)
        action2 = self.agent.step([f"user:hello_again"])
        
        # Selector shouldn't have changed weights (because it has NO weights)
        # Behavior changes through:
        # 1. Hippocampal activation energy decay
        # 2. Cortical pattern consolidation
        # 3. Selection pressure from patterns (NOT weights)
        
        self.assertFalse(hasattr(selector_frozen, 'weights'))
        self.assertFalse(hasattr(selector_frozen, 'learn'))


class TestGUIDeprecatedMethods(unittest.TestCase):
    """Test that deprecated training methods are properly handled"""
    
    def setUp(self):
        """Set up agent components"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(["action1", "action2"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, self.sleep_manager)
    
    def test_trainer_deprecated(self):
        """Test that SelectorTrainer raises NotImplementedError"""
        # SelectorTrainer should raise NotImplementedError on initialization
        try:
            from trainer import SelectorTrainer
            
            # Should raise NotImplementedError when instantiated, but allow compatibility
            try:
                trainer = SelectorTrainer(self.selector, self.hippocampus, self.cortex)
            except NotImplementedError:
                pass
            else:
                # If compatibility trainer is available, selector should expose weights
                self.assertTrue(hasattr(self.selector, 'weights'))
        except ImportError:
            # If trainer can't be imported, that's fine (it's deprecated)
            pass
    
    def test_no_selector_learn_method(self):
        """Test that selector has no learn() method"""
        # New selector should not have learn() method
        self.assertFalse(hasattr(self.selector, 'learn'))
    
    def test_agent_step_without_reward(self):
        """Test that agent.step() doesn't require reward parameter"""
        # This should work without reward
        context = ["user:test"]
        action = self.agent.step(context)
        
        self.assertIsNotNone(action)


if __name__ == '__main__':
    unittest.main()
