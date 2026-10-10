"""
Tests for ActionSelector - non-learnable action selection.

Verifies that selector:
1. Has no learning mechanism (no weights)
2. Makes decisions based only on experience activation
3. Uses confidence threshold for deterministic vs stochastic choice
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from selector import ActionSelector
from experience import Event, Path, Experience, EventType
import unittest


class TestActionSelectorCreation(unittest.TestCase):
    """Test selector initialization"""
    
    def test_selector_initialization(self):
        """Selector should initialize with actions"""
        actions = ["go", "stay", "flee"]
        selector = ActionSelector(actions)
        
        self.assertEqual(selector.actions, actions)
        self.assertGreater(selector.confidence_threshold, 0)
    
    def test_selector_no_learnable_weights(self):
        """Selector should NOT have learnable weights"""
        selector = ActionSelector(["go", "stay"])
        
        # Should not have weights attribute (no learning)
        self.assertFalse(hasattr(selector, 'weights'))
    
    def test_selector_no_learn_method(self):
        """Selector should NOT have learn() method"""
        selector = ActionSelector(["go", "stay"])
        
        # Should not have learn method
        self.assertFalse(hasattr(selector, 'learn'))


class TestActionSelectorChoice(unittest.TestCase):
    """Test action selection"""
    
    def setUp(self):
        """Set up for tests"""
        self.selector = ActionSelector(["go", "stay", "flee"])
    
    def test_choose_returns_valid_action(self):
        """Should return valid action"""
        action = self.selector.choose([], [])
        self.assertIn(action, self.selector.actions)
    
    def test_choose_without_experiences(self):
        """With no experiences/patterns, should return random action"""
        action = self.selector.choose([], [])
        self.assertIn(action, self.selector.actions)
    
    def test_choose_multiple_calls_consistent(self):
        """Multiple calls without experiences should still return valid actions"""
        for _ in range(10):
            action = self.selector.choose([], [])
            self.assertIn(action, self.selector.actions)


class TestActionSelectorPressure(unittest.TestCase):
    """Test pressure calculation from experiences"""
    
    def setUp(self):
        """Set up for tests"""
        self.selector = ActionSelector(["go", "stay", "flee"])
    
    def test_positive_experience_influences_choice(self):
        """Positive experience should influence action selection"""
        # Create path with action
        path = Path()
        path = path.add_event(Event("danger", EventType.CONTEXT))
        path = path.add_event(Event("action:flee", EventType.ACTION))
        
        # Create experience with high intensity
        exp = Experience(path, intensity=2.0)
        exp.activation_energy = 1.0
        
        # Multiple selections with this experience
        choices = []
        for _ in range(20):
            action = self.selector.choose([exp], [])
            choices.append(action)
        
        # "flee" should be chosen significantly more often
        flee_count = choices.count("flee")
        # With high intensity and activation, should get it often
        self.assertGreaterEqual(flee_count, 5)
    
    def test_low_intensity_experience_weak_influence(self):
        """Low intensity experience should have weak influence"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        # Low intensity
        exp = Experience(path, intensity=0.1)
        exp.activation_energy = 0.1
        
        # Should still return valid action, but pressure is weak
        action = self.selector.choose([exp], [])
        self.assertIn(action, self.selector.actions)


class TestActionSelectorConfidence(unittest.TestCase):
    """Test confidence-based deterministic vs stochastic selection"""
    
    def test_high_confidence_deterministic(self):
        """High confidence should make deterministic choice"""
        selector = ActionSelector(["go", "stay", "flee"], confidence_threshold=0.5)
        
        # Create very strong experience
        path = Path()
        path = path.add_event(Event("danger", EventType.CONTEXT))
        path = path.add_event(Event("action:flee", EventType.ACTION))
        
        exp = Experience(path, intensity=2.0)
        exp.activation_energy = 1.0
        
        # With very strong single experience, choices should favor that action
        choices = []
        for _ in range(15):
            action = selector.choose([exp], [])
            choices.append(action)
        
        # Most choices should be "flee" when only one experience with high pressure
        best_action = max(set(choices), key=choices.count)
        best_count = choices.count(best_action)
        # With deterministic selection and high intensity, should get majority
        self.assertGreater(best_count, 5)
    
    def test_low_confidence_stochastic(self):
        """Low confidence should use stochastic choice"""
        selector = ActionSelector(["go", "stay", "flee"], confidence_threshold=0.9)
        
        # Create multiple experiences with similar pressure
        exps = []
        for action_name in ["go", "stay", "flee"]:
            path = Path()
            path = path.add_event(Event("context", EventType.CONTEXT))
            path = path.add_event(Event(f"action:{action_name}", EventType.ACTION))
            
            exp = Experience(path, intensity=1.0)
            exp.activation_energy = 1.0
            exps.append(exp)
        
        # With multiple similar experiences, should get variety
        choices = []
        for _ in range(30):
            action = selector.choose(exps, [])
            choices.append(action)
        
        # Should have multiple different choices
        unique_actions = len(set(choices))
        self.assertGreater(unique_actions, 1)


class TestActionSelectorWithCortex(unittest.TestCase):
    """Test selector with cortical patterns"""
    
    def setUp(self):
        """Set up for tests"""
        self.selector = ActionSelector(["go", "stay", "flee"])
    
    def test_cortex_patterns_influence_choice(self):
        """Cortical patterns should influence action selection"""
        from sleep import CorticalPattern
        
        # Create pattern favoring certain action
        sig = ("danger", "action:flee")
        pattern = CorticalPattern(sig, source_experiences=3)
        pattern.strength = 0.8
        
        # Multiple selections with this pattern
        choices = []
        for _ in range(20):
            action = self.selector.choose([], [pattern])
            choices.append(action)
        
        # "flee" should appear in choices (from pattern)
        self.assertIn("flee", choices)


class TestSelectorNoLearning(unittest.TestCase):
    """
    Critical test: Verify selector does NOT learn during waking activity.
    
    Learning only happens during sleep consolidation.
    """
    
    def test_selector_state_unchanged_after_choice(self):
        """Selector internal state should not change after making choices"""
        selector = ActionSelector(["go", "stay"])
        
        # Make multiple choices
        for _ in range(100):
            selector.choose([], [])
        
        # Selector should still only have actions
        # No learning parameters should exist
        self.assertFalse(hasattr(selector, 'weights'))
        self.assertFalse(hasattr(selector, 'learning_rate'))
        self.assertFalse(hasattr(selector, 'training_history'))


class TestSelectorEvaluation(unittest.TestCase):
    """Test utility evaluation path used by internal simulation."""

    def test_metadata_roundtrip_and_effect_access(self):
        selector = ActionSelector(["opaque"])
        selector.set_action_metadata(
            "opaque",
            {
                "predicted_effect": {
                    "axes": {"trust": 0.2, "stress": -0.1},
                    "drives": {"social_drive": -0.15},
                    "active_drive_delta": -0.05,
                }
            },
        )
        effect = selector.get_action_effect("opaque")
        self.assertAlmostEqual(float(effect["axes"]["trust"]), 0.2, places=6)
        self.assertAlmostEqual(float(effect["drives"]["social_drive"]), -0.15, places=6)

    def test_evaluate_scores_hypothetical_state_without_action_choice(self):
        selector = ActionSelector(["a", "b"])
        selector.set_action_metadata("a", {"predicted_effect": {"axes": {"curiosity": 0.3}, "drives": {"curiosity": -0.2}}})

        out = selector.evaluate(
            {
                "active_drive": "curiosity",
                "proposed_action": "a",
                "drives_before": {"curiosity": 0.8},
                "drives": {"curiosity": 0.5},
                "axes": {"curiosity": 0.7, "stress": -0.2, "stability": 0.4},
                "predicted_effect": selector.get_action_effect("a"),
            }
        )
        self.assertIsInstance(out, dict)
        self.assertIn("utility", out)
        self.assertIn("best_action", out)
        self.assertEqual(out["best_action"], "a")
        self.assertGreater(float(out["utility"]), 0.0)


if __name__ == '__main__':
    unittest.main()
