"""
Tests for immutable Experience and Event architecture.

Verifies that experiences and events are properly frozen after creation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from experience import Event, Path, Experience, EventType
import unittest


class TestEventImmutability(unittest.TestCase):
    """Test Event freezing mechanism"""
    
    def test_event_creation(self):
        """Event should be creatable"""
        event = Event("test", event_type=EventType.CONTEXT, magnitude=0.5)
        self.assertEqual(event.name, "test")
        self.assertEqual(event.event_type, EventType.CONTEXT)
        self.assertEqual(event.magnitude, 0.5)
    
    def test_event_freeze(self):
        """Event should be freezeable"""
        event = Event("test")
        event.freeze()
        self.assertTrue(event._frozen)
    
    def test_frozen_event_cannot_modify(self):
        """Frozen event should prevent modifications"""
        event = Event("test")
        event.freeze()
        
        with self.assertRaises(ValueError):
            event.name = "modified"
    
    def test_event_equality(self):
        """Events should be equal if name and type match"""
        e1 = Event("action:go", EventType.ACTION)
        e2 = Event("action:go", EventType.ACTION)
        self.assertEqual(e1, e2)
    
    def test_event_hashable(self):
        """Events should be hashable"""
        event = Event("test", EventType.CONTEXT)
        s = {event}
        self.assertIn(event, s)


class TestPathImmutability(unittest.TestCase):
    """Test Path immutability"""
    
    def test_path_creation(self):
        """Path should be creatable"""
        path = Path()
        self.assertEqual(len(path.events), 0)
    
    def test_path_add_event(self):
        """add_event should return new Path, not modify existing"""
        path1 = Path()
        path2 = path1.add_event(Event("test"))
        
        self.assertEqual(len(path1.events), 0)  # Original unchanged
        self.assertEqual(len(path2.events), 1)  # New path has event
    
    def test_path_freeze(self):
        """Path should be freezeable"""
        path = Path()
        path = path.add_event(Event("test"))
        path.freeze()
        
        self.assertTrue(path._frozen)
        self.assertTrue(path.events[0]._frozen)
    
    def test_frozen_path_cannot_add(self):
        """Frozen path should prevent adding events"""
        path = Path()
        path = path.add_event(Event("test"))
        path.freeze()
        
        with self.assertRaises(ValueError):
            path.add_event(Event("new"))
    
    def test_path_signature(self):
        """Path should compute signature from events"""
        path = Path()
        path = path.add_event(Event("context"))
        path = path.add_event(Event("action:go"))
        
        sig = path.signature()
        self.assertEqual(sig, ("context", "action:go"))
    
    def test_path_matches(self):
        """Path should match context events"""
        path = Path()
        path = path.add_event(Event("user:hello"))
        path = path.add_event(Event("action:reply"))
        
        self.assertTrue(path.matches(["user:hello"]))
        self.assertTrue(path.matches(["user:hello", "action:reply"]))
        self.assertFalse(path.matches(["user:goodbye"]))


class TestExperienceImmutability(unittest.TestCase):
    """Test Experience immutability"""
    
    def test_experience_creation(self):
        """Experience should be creatable"""
        path = Path()
        path = path.add_event(Event("test"))
        exp = Experience(path, intensity=1.0)
        
        self.assertEqual(exp.intensity, 1.0)
        self.assertEqual(exp.reinforcement_count, 1)
    
    def test_experience_intensity_clamped(self):
        """Experience intensity should be clamped to [0, 2]"""
        path = Path()
        path = path.add_event(Event("test"))
        
        exp_low = Experience(path, intensity=-1.0)
        self.assertEqual(exp_low.intensity, 0.0)
        
        exp_high = Experience(path, intensity=5.0)
        self.assertEqual(exp_high.intensity, 2.0)
    
    def test_experience_is_frozen(self):
        """Experience path should be frozen after creation"""
        path = Path()
        path = path.add_event(Event("test"))
        exp = Experience(path)
        
        # Path should be frozen
        with self.assertRaises(ValueError):
            exp.path.add_event(Event("new"))
    
    def test_experience_mutable_metadata(self):
        """Experience metadata (not path) should be mutable"""
        path = Path()
        path = path.add_event(Event("test"))
        exp = Experience(path)
        
        # These CAN be modified (they're metadata, not core experience)
        exp.reinforcement_count = 5
        self.assertEqual(exp.reinforcement_count, 5)
        
        exp.activation_energy = 0.3
        self.assertEqual(exp.activation_energy, 0.3)
        
        exp.stability = 0.7
        self.assertEqual(exp.stability, 0.7)
    
    def test_experience_with_consequence(self):
        """Experience can have a consequence event"""
        path = Path()
        path = path.add_event(Event("action:go"))
        
        consequence = Event("result:success", EventType.CONSEQUENCE, magnitude=2.0)
        exp = Experience(path, consequence=consequence, intensity=1.5)
        
        self.assertEqual(exp.consequence.name, "result:success")
        self.assertEqual(exp.consequence.magnitude, 2.0)


class TestEventTypes(unittest.TestCase):
    """Test EventType enum"""
    
    def test_event_types_exist(self):
        """All event types should be defined"""
        self.assertEqual(EventType.CONTEXT.value, "context")
        self.assertEqual(EventType.ACTION.value, "action")
        self.assertEqual(EventType.CONSEQUENCE.value, "consequence")


if __name__ == '__main__':
    unittest.main()
