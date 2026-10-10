#!/usr/bin/env python3
"""
Comprehensive test suite for Chinchilla Agent after implementation spec.
Tests all new features and fixes.
"""

import logging
import sys
import os
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test all imports work."""
    logger.info("Testing imports...")
    try:
        from config import ACTION_LIBRARY, BEHAVIORAL_CHAINS
        from behavioral_chains import BehavioralChainExecutor
        from demo_action_realizer import ActionRealizer
        from dataset_loader import DatasetLoader
        from pygame_engine import create_pygame_engine
        from main import ChinchillaAgent
        from affective_space import AffectiveSpace
        from neuromodulators import NeuromodulatorState
        from wakefulness import WakefulnessState
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_nowa_candidate_chains():
    """Test BG-based chain candidate generation."""
    logger.info("Testing BG candidate chains...")
    from main import ChinchillaAgent
    agent = ChinchillaAgent(demo_dir=str(Path(__file__).parent.parent), use_pygame=False, use_gui=False)

    drives = {
        "energy_need": 0.9,
        "exploration": 0.1,
        "social_drive": 0.0,
        "curiosity": 0.2,
        "goal_tension": 0.1,
    }
    candidates = agent._build_candidate_chains(drives)
    assert isinstance(candidates, list)
    assert len(candidates) <= 3
    logger.info("✓ BG candidate chains OK")
    return True

def test_build_candidate_chains():
    # Backward compatible alias for older runner name
    return test_nowa_candidate_chains()

def test_behavioral_chains_probabilities():
    """Test behavioral chains with probabilities."""
    logger.info("Testing behavioral chains probabilities...")
    try:
        from config import BEHAVIORAL_CHAINS
        from behavioral_chains import BehavioralChainExecutor
        
        # Check that chains contain tuples
        for chain_name, actions in BEHAVIORAL_CHAINS.items():
            for action in actions:
                assert isinstance(action, (str, tuple)), f"Action {action} in {chain_name} should be str or tuple"
        
        # Test executor with probabilities
        executor = BehavioralChainExecutor(None, logger)
        executor.start_chain('eating_and_grooming')
        
        # Should handle both formats
        action = executor.get_next_action_in_chain()
        assert action is not None, "Should get action from chain"
        
        logger.info("✓ Behavioral chains with probabilities work")
        return True
    except Exception as e:
        logger.error(f"✗ Behavioral chains test failed: {e}")
        return False

def test_pygame_engine_features():
    """Test new pygame engine features."""
    logger.info("Testing pygame engine features...")
    try:
        from pygame_engine import create_pygame_engine
        engine = create_pygame_engine(fps=60)
        if getattr(engine, "__class__", object).__name__.lower().startswith("stub"):
            logger.info("Skipping pygame-specific assertions (pygame unavailable)")
            return True

        # Test circadian phase
        engine.set_circadian_phase(0.0)  # Night
        assert engine._circadian_phase == 0.0
        
        engine.set_circadian_phase(0.5)  # Day
        assert engine._circadian_phase == 0.5
        
        # Test wellbeing
        engine.set_wellbeing(0.8, 0.5, 0.5, False)  # Stress
        assert engine._wellbeing == 0.2
        
        engine.set_wellbeing(0.8, 0.5, 0.5, True)  # Pathological
        assert engine._wellbeing == 0.0

        # NOWA HUD accepts state
        if hasattr(engine, "set_nowa_state"):
            engine.set_nowa_state({"dopamine": 0.1, "energy_need": 0.5, "bg_top3": [("exploration", 0.3)]})
        
        logger.info("✓ Pygame engine features work")
        return True
    except Exception as e:
        logger.error(f"✗ Pygame engine test failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    logger.info("Starting comprehensive test suite...")
    
    tests = [
        test_imports,
        test_nowa_candidate_chains,
        test_behavioral_chains_probabilities,
        test_pygame_engine_features,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Separator
    
    logger.info(f"Test results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
