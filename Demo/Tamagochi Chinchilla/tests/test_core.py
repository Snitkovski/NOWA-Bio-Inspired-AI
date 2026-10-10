"""
Basic test suite for Chinchilla Agent project structure.
Tests dataset loading, action realization, and component integration.
"""

import logging
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TESTS
# ============================================================================

def test_config():
    """Test configuration module."""
    logger.info("Testing config module...")
    try:
        from config import (
            ACTION_LIBRARY, ActionLayer, Position,
            BEHAVIORAL_CHAINS, ActionCategory, DRIVE_THRESHOLD
        )
        
        assert len(ACTION_LIBRARY) >= 73, f"Expected at least 73 actions, got {len(ACTION_LIBRARY)}"
        assert len(BEHAVIORAL_CHAINS) == 14, f"Expected 14 chains, got {len(BEHAVIORAL_CHAINS)}"
        assert DRIVE_THRESHOLD == 0.35, f"Expected drive threshold 0.35, got {DRIVE_THRESHOLD}"
        
        logger.info(f"✓ Config OK: {len(ACTION_LIBRARY)} actions, {len(BEHAVIORAL_CHAINS)} chains")
        return True
    
    except Exception as e:
        logger.error(f"✗ Config test failed: {e}")
        return False


def test_dataset_loader():
    """Test dataset loading."""
    logger.info("Testing dataset loader...")
    try:
        from dataset_loader import DatasetLoader
        
        demo_dir = Path(__file__).parent.parent
        dataset_dir = demo_dir / "Datasets"
        
        if not dataset_dir.exists():
            logger.warning(f"Dataset directory not found: {dataset_dir}")
            return False
        
        loader = DatasetLoader(dataset_dir)
        loader.load_all()
        
        stats = loader.get_stats()
        logger.info(f"✓ Dataset loaded: {stats}")
        
        # Verify we have some realizations
        assert stats["num_action_types"] > 0, "No action types loaded"
        assert stats["total_realizations"] > 0, "No realizations loaded"
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Dataset loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_realizer():
    """Test action realization."""
    logger.info("Testing action realizer...")
    try:
        from demo_action_realizer import create_action_realizer
        from pathlib import Path
        
        demo_dir = Path(__file__).parent.parent
        realizer = create_action_realizer(str(demo_dir))
        
        if not realizer:
            logger.error("Failed to create action realizer")
            return False
        # Ensure dataset was loaded correctly (regression check)
        stats = realizer.dataset.get_stats()
        assert stats.get("total_realizations", 0) > 0, "Dataset not loaded by realizer"
        assert realizer.dataset.has_realization("doze_shelf"), "Shelf action missing from dataset"
        
        # Try to realize a basic action
        command = realizer.realize_action("eat_pellets", pressure=1.0)
        assert command is not None, "Failed to realize eat_pellets"
        assert "anim" in command, "Command missing 'anim' key"
        assert "position" in command, "Command missing 'position' key"
        
        logger.info(f"✓ Action realizer OK: {command}")
        return True
    
    except Exception as e:
        logger.error(f"✗ Action realizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pygame_engine():
    """Test pygame engine (stub if pygame unavailable)."""
    logger.info("Testing pygame engine...")
    try:
        from pygame_engine import create_pygame_engine
        
        engine = create_pygame_engine()
        logger.info(f"✓ Pygame engine created: {type(engine).__name__}")
        
        # Test basic operations
        engine.load_animation("test", Path("dummy.png"))  # Should not crash
        engine.queue_action({"anim": "test", "position": "floor"})
        engine.process_actions()
        engine.update()
        
        logger.info("✓ Pygame engine OK")
        return True
    
    except Exception as e:
        logger.error(f"✗ Pygame engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chinchilla_agent():
    """Test main ChinchillaAgent initialization."""
    logger.info("Testing ChinchillaAgent...")
    try:
        from main import ChinchillaAgent
        from pathlib import Path
        
        demo_dir = Path(__file__).parent.parent
        
        # Create agent without pygame for testing
        agent = ChinchillaAgent(
            demo_dir=str(demo_dir),
            use_pygame=False,  # Disable pygame for testing
        )
        
        logger.info(f"✓ ChinchillaAgent created")
        
        # Test state snapshot
        snapshot = agent.get_state_snapshot()
        assert "tick" in snapshot, "Snapshot missing 'tick'"
        assert "stats" in snapshot, "Snapshot missing 'stats'"
        
        logger.info(f"✓ ChinchillaAgent OK")
        return True
    
    except Exception as e:
        logger.error(f"✗ ChinchillaAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def main():
    """Run all tests."""
    logger.info("="*60)
    logger.info("CHINCHILLA AGENT PROJECT - TEST SUITE")
    logger.info("="*60)
    
    tests = [
        ("Config", test_config),
        ("Dataset Loader", test_dataset_loader),
        ("Action Realizer", test_action_realizer),
        ("Pygame Engine", test_pygame_engine),
        ("ChinchillaAgent", test_chinchilla_agent),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
        logger.info("")
    
    # Summary
    logger.info("="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
