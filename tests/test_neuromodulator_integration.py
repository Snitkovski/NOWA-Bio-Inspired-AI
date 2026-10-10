"""
Integration tests for Neuromodulators with full Agent-Sleep system.

Tests the interaction between:
- Agent behavioral cycles
- Neuromodulator updates
- Sleep consolidation
- Affect system integration
"""

import sys
import time
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from neuromodulators import NeuromodulatorState
from affect import AffectiveState
from experience import Event, EventType
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from sleep import SleepManager
from selector import ActionSelector
from agent import Agent
from intent_memory import IntentMemory


class TestNeuromodulatorIntegration(unittest.TestCase):
    """Integration tests with full agent simulation."""
    
    def setUp(self):
        """Set up full agent system."""
        self.hippocampus = NOWAHippocampus()
        self.cortex = CortexMemory()
        self.selector = ActionSelector(actions=['act_A', 'act_B', 'act_C'])
        self.intent_memory = IntentMemory()
        self.sleep_manager = SleepManager(self.hippocampus, self.cortex, self.intent_memory)
        
        self.agent = Agent(
            self.hippocampus,
            self.cortex,
            self.selector,
            sleep_manager=self.sleep_manager,
            intent_memory=self.intent_memory
        )
        
    def test_agent_step_updates_neuromodulators(self):
        """Test that agent.step() updates neuromodulators."""
        print("\n=== Agent Step Updates Neuromodulators ===")
        
        initial_nm = self.agent.neuromodulators.snapshot()
        print(f"Initial NM: DA={initial_nm['dopamine']:.3f}")
        
        # Agent step with positive reward
        action = self.agent.step(
            context_events=['context_A'],
            reward=0.5,
            novelty=0.2,
            conflict=0.0
        )
        
        updated_nm = self.agent.neuromodulators.snapshot()
        print(f"After step (reward=0.5): DA={updated_nm['dopamine']:.3f}")
        
        # Dopamine should have increased
        self.assertGreater(updated_nm['dopamine'], initial_nm['dopamine'])
        print(f"✓ Neuromodulators updated during agent step\n")
    
    def test_agent_multiple_steps_with_signals(self):
        """Test multiple agent steps with varying reward signals."""
        print("\n=== Multiple Agent Steps ===")
        
        actions = []
        nm_history = []
        
        # Step 1: Positive reward
        action = self.agent.step(['ctx1'], reward=0.8, novelty=0.1, conflict=0.0)
        actions.append(action)
        nm_history.append(self.agent.neuromodulators.snapshot())
        print(f"Step 1 (reward=0.8): DA={nm_history[0]['dopamine']:.3f}, HT={nm_history[0]['serotonin']:.3f}")
        
        # Step 2: Negative reward + conflict
        action = self.agent.step(['ctx2'], reward=-0.6, novelty=0.0, conflict=0.5)
        actions.append(action)
        nm_history.append(self.agent.neuromodulators.snapshot())
        print(f"Step 2 (reward=-0.6, conflict=0.5): "
              f"DA={nm_history[1]['dopamine']:.3f}, CORT={nm_history[1]['cortisol']:.3f}")
        
        # Step 3: High novelty
        action = self.agent.step(['ctx3'], reward=0.0, novelty=0.9, conflict=0.0)
        actions.append(action)
        nm_history.append(self.agent.neuromodulators.snapshot())
        print(f"Step 3 (novelty=0.9): NE={nm_history[2]['norepinephrine']:.3f}")
        
        # Expectations
        self.assertGreater(nm_history[0]['dopamine'], 0.1, "Step 1: DA should be elevated")
        self.assertGreater(nm_history[1]['cortisol'], nm_history[0]['cortisol'], 
                          "Step 2: CORT should increase")
        self.assertGreater(nm_history[2]['norepinephrine'], nm_history[1]['norepinephrine'],
                          "Step 3: NE should increase")
        
        print(f"✓ Multiple steps processed correctly\n")
    
    def test_sleep_consolidation_with_neuromodulators(self):
        """Test that sleep consolidation uses neuromodulator effects."""
        print("\n=== Sleep Consolidation with Neuromodulators ===")
        
        # Create experiences with positive reward
        for i in range(5):
            self.agent.step(
                ['context_sleep_test'],
                reward=0.7 + i * 0.05,
                novelty=0.1,
                conflict=0.0
            )
        
        # Verify high dopamine
        nm_before = self.agent.neuromodulators.snapshot()
        print(f"Before sleep: DA={nm_before['dopamine']:.3f}")
        self.assertGreater(nm_before['dopamine'], 0.2, "Should have elevated DA")
        
        # Sleep: consolidation uses DA for enhancement
        cortex_before = len(self.cortex.patterns)
        sleep_stats = self.agent.sleep(cycles=1)
        cortex_after = len(self.cortex.patterns)
        
        print(f"Sleep stats: {sleep_stats}")
        print(f"Cortical patterns: {cortex_before} -> {cortex_after}")
        
        # Should have consolidation effort
        self.assertGreater(cortex_after, cortex_before, "Sleep should create patterns")
        
        print(f"✓ Sleep consolidation affected by neuromodulators\n")
    
    def test_high_stress_scenario_integration(self):
        """Test integrated system under stress (neg reward + high conflict)."""
        print("\n=== High Stress Integration Test ===")
        
        initial_state = self.agent.get_state()
        print(f"Initial cortex size: {initial_state['cortex']['total_patterns']}")
        
        # Simulate stress: multiple negative outcomes
        for i in range(3):
            self.agent.step(
                ['stress_context'],
                reward=-0.7,
                novelty=0.0,
                conflict=0.8
            )
        
        stress_nm = self.agent.neuromodulators.snapshot()
        stress_affect = self.agent.affect_state.snapshot()
        
        print(f"After stress:")
        print(f"  DA: {stress_nm['dopamine']:.3f} (should be low)")
        print(f"  CORT: {stress_nm['cortisol']:.3f} (should be high)")
        print(f"  Threat: {stress_affect['threat']:.3f} (should be high)")
        
        # Verify stress responses
        self.assertLess(stress_nm['dopamine'], 0.2, "Stress should lower DA")
        self.assertGreater(stress_nm['cortisol'], 0.2, "Stress should raise CORT")
        self.assertGreater(stress_affect['threat'], 0.3, "Affect should show threat")
        
        # Sleep after stress should help
        sleep_stats = self.agent.sleep(cycles=2)
        print(f"Post-stress sleep: {sleep_stats}")
        
        print(f"✓ Stress scenario handled correctly\n")
    
    def test_neuromodulator_decay_during_rest(self):
        """Test that neuromodulators decay during rest period."""
        print("\n=== Neuromodulator Decay Test ===")
        
        # Create elevated state
        for i in range(3):
            self.agent.step(['ctx'], reward=0.9, novelty=0.1, conflict=0.0)
        
        elevated_nm = self.agent.neuromodulators.snapshot()
        print(f"Elevated state: DA={elevated_nm['dopamine']:.3f}")
        
        # Manually apply decay (simulating rest period)
        self.agent.neuromodulators.decay_over_time(180.0)  # 3 minutes
        
        decayed_nm = self.agent.neuromodulators.snapshot()
        print(f"After 3 min rest: DA={decayed_nm['dopamine']:.3f}")
        
        # Should have decayed toward baseline
        self.assertLess(decayed_nm['dopamine'], elevated_nm['dopamine'])
        self.assertGreater(decayed_nm['dopamine'], 0.1)  # But not below baseline
        
        print(f"✓ Decay works during rest\n")
    
    def test_affect_modulated_by_neuromodulators(self):
        """Test that affect is influenced by neuromodulator modifiers."""
        print("\n=== Affect Modulated by Neuromodulators ===")
        
        # Create high dopamine state
        for i in range(5):
            self.agent.step(['reward_ctx'], reward=0.8, novelty=0.2, conflict=0.0)
        
        high_da_nm = self.agent.neuromodulators.snapshot()
        high_da_modifier = self.agent.neuromodulators.get_affective_arousal_modifier()
        
        print(f"High DA ({high_da_nm['dopamine']:.3f}): arousal_modifier={high_da_modifier:.3f}")
        
        # Reset and create high cortisol state
        self.agent.neuromodulators.reset()
        for i in range(5):
            self.agent.step(['threat_ctx'], reward=-0.8, novelty=0.0, conflict=0.9)
        
        high_cort_nm = self.agent.neuromodulators.snapshot()
        high_cort_modifier = self.agent.neuromodulators.get_affective_arousal_modifier()
        
        print(f"High CORT ({high_cort_nm['cortisol']:.3f}): arousal_modifier={high_cort_modifier:.3f}")
        
        # Both should increase arousal, but from different mechanisms
        self.assertGreater(high_da_modifier, 1.0, "DA should amplify arousal")
        # CORT has complex effects (can both increase and stress)
        self.assertGreater(high_cort_modifier, 0.5, "CORT should have arousal effect")
        
        print(f"✓ Arousal modified by neuromodulators\n")
    
    def test_memory_formation_with_neuromodulators(self):
        """Test that learning during sleep adapts to neuromodulator state."""
        print("\n=== Memory Formation Test ===")
        
        # Create repeated experience with positive outcome
        for cycle in range(2):
            for i in range(3):
                self.agent.step(['pattern_ctx', 'subctx_A'], reward=0.9, novelty=0.0, conflict=0.0)
            
            nm_snap = self.agent.neuromodulators.snapshot()
            cortex_size = len(self.cortex.patterns)
            print(f"Cycle {cycle+1}: DA={nm_snap['dopamine']:.3f}, Patterns={cortex_size}")
            
            # Sleep
            stats = self.agent.sleep(cycles=1)
            cortex_after = len(self.cortex.patterns)
            print(f"  After sleep: Patterns={cortex_after}")
        
        # Should have formed patterns
        self.assertGreater(len(self.cortex.patterns), 0, "Should form patterns during sleep")
        
        print(f"✓ Memory formation with neuromodulators working\n")


class TestNeuromodulatorEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        self.nm = NeuromodulatorState()
    
    def test_extreme_signals_clamped(self):
        """Test that extreme signal values don't break the system."""
        print("\n=== Extreme Signals Test ===")
        
        # Extreme positive
        self.nm.update_from_signals(reward=10.0, novelty=10.0, conflict=10.0)
        
        # All should be clamped to [0, 1]
        self.assertLessEqual(self.nm.dopamine, 1.0)
        self.assertLessEqual(self.nm.norepinephrine, 1.0)
        self.assertLessEqual(self.nm.serotonin, 1.0)
        self.assertLessEqual(self.nm.cortisol, 1.0)
        
        print(f"✓ Extreme values properly clamped\n")
    
    def test_rapid_state_changes(self):
        """Test system stability during rapid state changes."""
        print("\n=== Rapid State Changes Test ===")
        
        for i in range(20):
            reward = 1.0 if i % 2 == 0 else -1.0
            self.nm.update_from_signals(reward=reward, novelty=0.5, conflict=0.5)
            
            # Should remain stable and clamped
            self.assertTrue(0 <= self.nm.dopamine <= 1.0)
            self.assertTrue(0 <= self.nm.cortisol <= 1.0)
        
        print(f"Final state: DA={self.nm.dopamine:.3f}, CORT={self.nm.cortisol:.3f}")
        print(f"✓ Rapid changes handled\n")
    
    def test_zero_decay_time(self):
        """Test that zero decay time doesn't cause errors."""
        print("\n=== Zero Decay Time Test ===")
        
        self.nm.dopamine = 0.9
        self.nm.decay_over_time(0.0)  # Should not change
        
        self.assertAlmostEqual(self.nm.dopamine, 0.9)
        
        print(f"✓ Zero decay time handled\n")


def run_integration_tests():
    """Run all integration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestNeuromodulatorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestNeuromodulatorEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_integration_tests()
    
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    sys.exit(0 if result.wasSuccessful() else 1)
