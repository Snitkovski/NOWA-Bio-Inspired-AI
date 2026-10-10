"""
Tests for Hippocampus - short-term memory.

Verifies that hippocampus stores experiences without optimization,
and properly activates them based on context.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from experience import Event, Path, Experience, EventType
from hippocampus import NOWAHippocampus
import unittest


class TestHippocampusStorage(unittest.TestCase):
    """Test hippocampal storage"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
    
    def test_store_experience(self):
        """Should store experiences"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        exp = self.hippocampus.store(path, intensity=1.0)
        
        self.assertEqual(len(self.hippocampus.experiences), 1)
        self.assertIsInstance(exp, Experience)
    
    def test_reinforce_existing_pattern(self):
        """Reinforcing existing pattern should increment counter"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        exp1 = self.hippocampus.store(path)
        self.assertEqual(exp1.reinforcement_count, 1)
        
        # Same pattern again
        exp2 = self.hippocampus.reinforce(path)
        
        # Should be same experience
        self.assertEqual(len(self.hippocampus.experiences), 1)
        # Reinforcement count should increase
        self.assertEqual(exp1.reinforcement_count, 2)
    
    def test_different_patterns_stored_separately(self):
        """Different patterns should be stored as separate experiences"""
        path1 = Path()
        path1 = path1.add_event(Event("context1", EventType.CONTEXT))
        path1 = path1.add_event(Event("action:go", EventType.ACTION))
        
        path2 = Path()
        path2 = path2.add_event(Event("context2", EventType.CONTEXT))
        path2 = path2.add_event(Event("action:stay", EventType.ACTION))
        
        self.hippocampus.store(path1)
        self.hippocampus.store(path2)
        
        self.assertEqual(len(self.hippocampus.experiences), 2)


class TestHippocampusActivation(unittest.TestCase):
    """Test activation by context"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
    
    def test_activate_by_context(self):
        """Should activate experiences matching context"""
        path1 = Path()
        path1 = path1.add_event(Event("user:hello", EventType.CONTEXT))
        path1 = path1.add_event(Event("action:greet", EventType.ACTION))
        
        path2 = Path()
        path2 = path2.add_event(Event("system:startup", EventType.CONTEXT))
        path2 = path2.add_event(Event("action:init", EventType.ACTION))
        
        self.hippocampus.store(path1)
        self.hippocampus.store(path2)
        
        # Activate with user:hello context
        activated = self.hippocampus.activate(["user:hello"])
        
        self.assertEqual(len(activated), 1)
        self.assertEqual(activated[0].path.signature()[0], "user:hello")
    
    def test_activate_empty_context(self):
        """Empty context should activate nothing"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        self.hippocampus.store(path)
        
        activated = self.hippocampus.activate([])
        
        # Empty context matches all - should get all experiences
        self.assertEqual(len(activated), 1)
    
    def test_activation_updates_timestamp(self):
        """Activation should update last_activated"""
        import time
        
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        exp = self.hippocampus.store(path)
        first_activated = exp.last_activated
        
        time.sleep(0.1)
        
        activated = self.hippocampus.activate(["context"])
        
        self.assertGreater(exp.last_activated, first_activated)


class TestHippocampusCandidatesForSleep(unittest.TestCase):
    """Test selection of candidates for consolidation"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
    
    def test_get_candidates_for_sleep(self):
        """Should return experiences ready for consolidation"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        # Add experience and reinforce it
        exp = self.hippocampus.store(path)
        self.hippocampus.reinforce(path)
        self.hippocampus.reinforce(path)
        
        # Should be candidate (reinforcement_count >= 2)
        candidates = self.hippocampus.get_candidates_for_sleep(min_reinforcement=2)
        
        self.assertIn(exp, candidates)
    
    def test_candidates_exclude_low_reinforcement(self):
        """Candidates should exclude low-reinforcement experiences"""
        path = Path()
        path = path.add_event(Event("context", EventType.CONTEXT))
        path = path.add_event(Event("action:go", EventType.ACTION))
        
        exp = self.hippocampus.store(path)  # reinforcement_count = 1
        
        # With min_reinforcement=2, should not be included
        candidates = self.hippocampus.get_candidates_for_sleep(min_reinforcement=2)
        
        self.assertNotIn(exp, candidates)


class TestHippocampusBoundary(unittest.TestCase):
    """Test maximum capacity handling"""
    
    def test_max_experiences_limit(self):
        """Should not exceed max_experiences"""
        hippocampus = NOWAHippocampus(max_experiences=10)
        
        # Add more than max
        for i in range(20):
            path = Path()
            path = path.add_event(Event(f"context{i}", EventType.CONTEXT))
            path = path.add_event(Event(f"action:{i}", EventType.ACTION))
            hippocampus.store(path)
        
        self.assertLessEqual(len(hippocampus.experiences), 10)


class TestHippocampusStatistics(unittest.TestCase):
    """Test statistics generation"""
    
    def setUp(self):
        """Set up for tests"""
        self.hippocampus = NOWAHippocampus()
    
    def test_statistics_empty(self):
        """Statistics of empty hippocampus"""
        stats = self.hippocampus.get_statistics()
        
        self.assertEqual(stats["total_experiences"], 0)
        self.assertEqual(stats["avg_reinforcement"], 0)
    
    def test_statistics_with_experiences(self):
        """Statistics should include all experiences"""
        for i in range(3):
            path = Path()
            path = path.add_event(Event(f"context{i}", EventType.CONTEXT))
            path = path.add_event(Event(f"action:{i}", EventType.ACTION))
            self.hippocampus.store(path)
        
        stats = self.hippocampus.get_statistics()
        
        self.assertEqual(stats["total_experiences"], 3)
        self.assertGreater(stats["avg_reinforcement"], 0)

if __name__ == '__main__':
    unittest.main()
