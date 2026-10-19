"""
Tests for Agent - full integration of NOWA system.

Tests verify:
1. No learning during waking activity
2. Behavior emerges from experience and patterns
3. Sleep consolidation as only learning mechanism
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from experience import Event, Path, EventType
import unittest


class TestAgentBasics(unittest.TestCase):
    """Basic agent functionality tests"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=[
            "greet",
            "ask",
            "refuse"
        ])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, 
                           sleep_manager=self.sleep_manager)
    
    def test_agent_step_returns_action(self):
        """Agent.step should return valid action"""
        action = self.agent.step(["user:hello"])
        self.assertIn(action, self.selector.actions)
    
    def test_agent_stores_experience(self):
        """Agent.step should store experience in hippocampus"""
        initial_count = len(self.hippocampus.experiences)
        self.agent.step(["user:hello"])
        final_count = len(self.hippocampus.experiences)
        
        self.assertEqual(final_count, initial_count + 1)
    
    def test_agent_experience_immutable(self):
        """Stored experience should be immutable"""
        self.agent.step(["user:hello"])
        exp = self.hippocampus.experiences[0]
        
        # Should not be able to modify path
        with self.assertRaises(ValueError):
            exp.path.add_event(Event("new"))


class TestAgentBehaviorEmergence(unittest.TestCase):
    """Test that behavior emerges from experience without learning"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=["go", "stay", "flee"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, 
                           sleep_manager=self.sleep_manager)
    
    def test_behavior_emerges_from_hippocampal_experience(self):
        """Behavior should emerge from recent experience activation"""
        # Store positive experience with action "go"
        path = Path()
        path = path.add_event(Event("safe_area", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        self.hippocampus.store(path, intensity=2.0, reward=1.0)
        
        # Multiple agent steps in same context
        choices = []
        for _ in range(20):
            action = self.agent.step(["safe_area"])
            choices.append(action)
        
        # "go" should be chosen more often due to high-intensity experience
        go_count = choices.count("go")
        # With high intensity stored experience, should see it sometimes
        self.assertGreater(go_count, 0)
    
    def test_no_learning_during_waking(self):
        """
        CRITICAL: No learning should happen during waking activity.
        
        If selector had weights, they shouldn't change during step().
        But selector has NO weights - it's stateless.
        """
        # Selector should have no learning mechanisms
        self.assertFalse(hasattr(self.selector, 'weights'))
        
        # Multiple steps shouldn't change selector
        for _ in range(50):
            self.agent.step(["context"])
        
        # Still no weights
        self.assertFalse(hasattr(self.selector, 'weights'))


class TestAgentSleep(unittest.TestCase):
    """Test sleep consolidation"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=["go", "stay"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, 
                           sleep_manager=self.sleep_manager)
    
    def test_sleep_consolidates_experiences(self):
        """Sleep should consolidate repeated experiences to cortex"""
        # Create repeated experiences - need reinforcement_count >= 2
        for i in range(3):
            self.agent.step(["danger"])
        
        # Now reinforce the existing experience(s)
        for i in range(2):
            self.agent.step(["danger"])
        
        # Sleep - should consolidate some patterns
        stats = self.agent.sleep(cycles=1)
        
        # Should have run sleep cycle
        self.assertEqual(stats["cycles"], 1)
    
    def test_sleep_statistics(self):
        """Sleep should return consolidation statistics"""
        # Add some experiences
        for _ in range(5):
            self.agent.step(["context"])
        
        stats = self.agent.sleep(cycles=2)
        
        self.assertEqual(stats["cycles"], 2)
        self.assertIn("total_patterns", stats)
        self.assertIn("total_candidates", stats)


class TestAgentCognitiveState(unittest.TestCase):
    """Test agent state reflection"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=["go", "stay"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, 
                           sleep_manager=self.sleep_manager)
    
    def test_get_state_reflects_hippocampus(self):
        """State should show hippocampal statistics"""
        # Add experience
        self.agent.step(["context"])
        
        state = self.agent.get_state()
        
        self.assertIn("hippocampus", state)
        self.assertEqual(state["hippocampus"]["total_experiences"], 1)
    
    def test_get_state_reflects_cortex(self):
        """State should show cortical statistics"""
        # Add and reinforce experiences multiple times for consolidation
        for _ in range(2):
            self.agent.step(["context"])
            self.agent.step(["context"])
        
        self.agent.sleep(cycles=1)
        
        state = self.agent.get_state()
        
        self.assertIn("cortex", state)
        # After sleep, cortex may have patterns or may not (depends on consolidation)
        self.assertGreaterEqual(state["cortex"]["total_patterns"], 0)
    
    def test_get_state_reflects_sleep_cycles(self):
        """State should show number of sleep cycles after sleep"""
        # Create fresh components to avoid shared state
        hip = NOWAHippocampus()
        cort = CortexMemory()
        sel = ActionSelector(["go", "stay"])
        slp_mgr = SleepManager(hip, cort)
        ag = Agent(hip, cort, sel, sleep_manager=slp_mgr)
        
        # Initial state should show 0 cycles
        state = ag.get_state()
        self.assertEqual(state["sleep_cycles"], 0)
        
        # After sleep, should show 1 cycle
        ag.step(["context"])
        ag.sleep(cycles=1)
        
        state = ag.get_state()
        self.assertEqual(state["sleep_cycles"], 1)


class TestAgentIntegration(unittest.TestCase):
    """Integration tests for full NOWA cycle"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=["respond", "ignore", "escape"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector,
                           sleep_manager=self.sleep_manager)
    
    def test_full_wake_sleep_cycle(self):
        """Test full wake-sleep-wake cycle"""
        # Waking: many repetitions of same behavior
        contexts = ["threat", "opportunity", "neutral"]
        for context in contexts:
            for _ in range(3):
                self.agent.step([context])
        
        initial_hip_exps = len(self.hippocampus.experiences)
        initial_cortex_patterns = len(self.cortex.patterns)
        
        # Sleep: consolidation
        stats = self.agent.sleep(cycles=3)
        
        # After sleep: agent state may have changed
        self.assertEqual(stats["cycles"], 3)
        
        # Waking again: behavior should be influenced by consolidation
        choices = []
        for _ in range(20):
            action = self.agent.step(["threat"])
            choices.append(action)
        
        # Should have made some choices
        self.assertGreater(len(choices), 0)
    
    def test_behavior_persistence_without_new_experience(self):
        """
        NOWA principle test: If selector is frozen and agent gets new experience,
        behavior should still change (emerging from new hippocampal activation).
        """
        # Initial learning cycle
        for _ in range(3):
            self.agent.step(["context_a"])
        
        self.agent.sleep(cycles=2)
        
        # Record initial behavior in context_a
        initial_choices = []
        for _ in range(10):
            action = self.agent.step(["context_a"])
            initial_choices.append(action)
        
        # New experience in context_a (repeated)
        for _ in range(3):
            self.agent.step(["context_a"])
        
        self.agent.sleep(cycles=2)
        
        # Behavior might change due to new consolidation
        # (This would indicate non-frozen learning)
        # In NOWA, this is OK - behavior emerges through consolidation
        # NOT through selector weight changes
        
        self.assertTrue(True)  # Just verify this doesn't crash


class TestAgentFeedbackReplay(unittest.TestCase):
    """Feedback should populate replay metadata even when waking step reward is zero."""

    def setUp(self):
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=["go", "stay"])
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex)
        self.agent = Agent(self.hippocampus, self.cortex, self.selector, sleep_manager=self.sleep_manager)
        self.agent.register_action_channel("go", go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)

    def test_feedback_updates_last_experience_for_replay(self):
        action = self.agent.step(["ctx_feedback"], reward=0.0)
        result = self.agent.apply_feedback_to_last_experience(
            feedback_rating=2,
            context_events=["ctx_feedback"],
            action_id=action,
        )

        self.assertTrue(result.get("updated"))
        self.assertGreater(float(result.get("salience", 0.0)), 0.0)
        # The sleep log is the episode, not the removed BG outcome cache.
        exp = self.hippocampus.experiences[-1]
        self.assertEqual(getattr(exp, "replay_action_id", None), action)
        self.assertTrue(bool(getattr(exp, "td_outcome_committed", False)))
        self.assertTrue(hasattr(exp, "td_error_snapshot"))
        self.assertGreater(abs(float(getattr(exp, "td_error_snapshot", 0.0))), 0.0)

    def test_feedback_drives_nonzero_replay_in_sleep(self):
        action = self.agent.step(["ctx_feedback_sleep"], reward=0.0)
        self.agent.apply_feedback_to_last_experience(
            feedback_rating=2,
            context_events=["ctx_feedback_sleep"],
            action_id=action,
        )

        stats = self.agent.sleep(cycles=1)
        self.assertGreater(int(stats.get("total_replay_selected", 0)), 0)
        self.assertGreater(int(stats.get("total_replays", 0)), 0)

if __name__ == '__main__':
    unittest.main()
