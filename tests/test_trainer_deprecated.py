"""
DEPRECATED: Tests for SelectorTrainer.

SelectorTrainer is DEPRECATED and violates NOWA principles.
It tried to optimize selector weights directly, which contradicts the core principle:
"Behavior is not learned. It emerges."

Learning in NOWA happens ONLY during sleep consolidation (see test_sleep_consolidation.py).

This file is kept for reference only. Do NOT use SelectorTrainer in new code.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

import unittest


class TestTrainerDeprecated(unittest.TestCase):
    """
    Marker test to indicate trainer is deprecated.
    """
    
    def test_trainer_is_deprecated(self):
        """
        SelectorTrainer is DEPRECATED.
        Use SleepManager for learning through consolidation instead.
        """
        self.assertTrue(True)  # Just a marker


if __name__ == '__main__':
    unittest.main()
