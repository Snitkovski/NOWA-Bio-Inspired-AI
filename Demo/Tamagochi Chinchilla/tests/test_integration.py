"""
Integration tests for affect system and GUI.
Tests the interaction between affect simulation, behavioral chains, and GUI.
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
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TESTS
# ============================================================================

def test_affect_system():
    """Test SimpleAffect system."""
    logger.info("Testing affect system...")
    try:
        from affect_sim import SimpleAffect
        
        affect = SimpleAffect(logger)
        
        # Initial state
        initial_state = affect.get_state()
        assert "valence" in initial_state
        assert "arousal" in initial_state
        assert "stress" in initial_state
        
        # Update affect
        for _ in range(10):
            affect.update(dt=1.0)
        
        updated_state = affect.get_state()
        assert isinstance(updated_state["valence"], float)
        
        # Get chain context
        context = affect.get_chain_context()
        assert "affect" in context
        assert "is_daytime" in context
        assert "mood" in context
        
        logger.info(f"✓ Affect system OK: {initial_state}")
        return True
    
    except Exception as e:
        logger.error(f"✗ Affect system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_affect_based_chain_selection():
    """Test that behavioral chains respond to affect state."""
    logger.info("Testing affect-based chain selection...")
    try:
        from affect_sim import SimpleAffect
        from behavioral_chains import BehavioralChainExecutor
        from demo_action_realizer import ActionRealizer
        from dataset_loader import DatasetLoader
        
        demo_dir = Path(__file__).parent.parent
        
        # Setup components
        dataset_loader = DatasetLoader(demo_dir / "Datasets")
        dataset_loader.load_all()
        
        action_realizer = ActionRealizer(dataset_loader, logger)
        chain_executor = BehavioralChainExecutor(action_realizer, logger)
        affect = SimpleAffect(logger)
        
        # High stress context
        affect.state["stress"] = 0.8
        context = affect.get_chain_context()
        
        chain = chain_executor.select_chain(context)
        logger.info(f"Selected chain with high stress: {chain}")
        
        # Low stress, high arousal context
        affect.state["stress"] = 0.2
        affect.state["arousal"] = 0.8
        context = affect.get_chain_context()
        
        chain = chain_executor.select_chain(context)
        logger.info(f"Selected chain with high arousal: {chain}")
        
        logger.info("✓ Affect-based chain selection OK")
        return True
    
    except Exception as e:
        logger.error(f"✗ Affect-based chain selection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gui_framework():
    """Test GUI framework creation."""
    logger.info("Testing GUI framework...")
    try:
        from gui import ChinchillaGUI
        
        gui = ChinchillaGUI(logger=logger)
        
        # Update GUI with stats
        gui.update_stats({
            "ticks": 100,
            "actions_executed": 50,
            "current_chain": "test_chain",
        })
        
        # Update with affect
        gui.update_affect({
            "valence": 0.5,
            "arousal": 0.6,
            "stress": 0.2,
        })
        
        gui.update_fps(20.0)
        
        logger.info("✓ GUI framework OK")
        return True
    
    except Exception as e:
        logger.error(f"✗ GUI framework test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chinchilla_agent_with_affect():
    """Test ChinchillaAgent with affect and GUI."""
    logger.info("Testing ChinchillaAgent with affect and GUI...")
    try:
        from main import ChinchillaAgent
        
        demo_dir = Path(__file__).parent.parent
        
        agent = ChinchillaAgent(
            demo_dir=str(demo_dir),
            use_pygame=False,  # Don't use pygame in tests
            use_gui=False,     # Don't use GUI in headless mode
        )
        
        # Verify components exist
        assert agent.affect is not None, "Affect system not initialized"
        assert agent.chain_executor is not None, "Chain executor not initialized"
        
        # Test a few steps
        agent.running = True
        for _ in range(5):
            agent.step(dt=1.0)
        
        assert agent.tick_count > 0
        assert agent.stats["actions_executed"] > 0
        
        logger.info(f"✓ ChinchillaAgent with affect OK: {agent.stats}")
        return True
    
    except Exception as e:
        logger.error(f"✗ ChinchillaAgent with affect test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("CHINCHILLA AGENT - INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    logger.info("")
    
    results = []
    
    results.append(("Affect System", test_affect_system()))
    logger.info("")
    
    results.append(("Affect-based Chain Selection", test_affect_based_chain_selection()))
    logger.info("")
    
    results.append(("GUI Framework", test_gui_framework()))
    logger.info("")
    
    results.append(("ChinchillaAgent with Affect", test_chinchilla_agent_with_affect()))
    logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    sys.exit(0 if passed == total else 1)
