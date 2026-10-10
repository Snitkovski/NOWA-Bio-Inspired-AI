import time
from src.affect import AffectiveState
from src.hippocampus import NOWAHippocampus
from src.agent import Agent
from src.selector import ActionSelector
from src.cortex import CortexMemory
from src.experience import Event, Path, EventType


def test_curiosity_growth_and_decay_integration():
    """
    Integration test: curiosity grows when novel input is encountered,
    then decays over time with no new novelty.
    
    This demonstrates both directions of change (increase and decrease).
    """
    # Set up agent with minimal components
    hippocampus = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["ask", "respond", "explore"])
    agent = Agent(hippocampus, cortex, selector)
    
    # Initial curiosity
    assert agent.affect_state.curiosity == 0.1
    
    # Step 1: Process NEW context - should increase curiosity
    # This context is novel (no experiences yet)
    context1 = ["user:what is ai"]
    agent.step(context1, novelty=1.0)  # Fully novel
    curiosity_after_novel = agent.affect_state.curiosity
    # Expected: 0.1 + 1.0 * 0.25 = 0.35
    assert abs(curiosity_after_novel - 0.35) < 1e-5, f"Expected 0.35, got {curiosity_after_novel}"
    
    # Step 2: Simulate time passing (no new novelty)
    # Curiosity should decay
    agent.affect_state.decay_over_time(time_elapsed=60.0, half_life=60.0)
    curiosity_after_decay = agent.affect_state.curiosity
    # Expected: 0.35 * 0.5 = 0.175 (one half-life)
    assert abs(curiosity_after_decay - 0.175) < 1e-5, f"Expected 0.175, got {curiosity_after_decay}"
    
    # Step 3: Process same context again - low novelty (already seen)
    # Even with low novelty, no increase because novelty is close to 0
    agent.step(context1, novelty=0.1)  # Low novelty
    curiosity_after_repeat = agent.affect_state.curiosity
    # Expected: 0.175 + 0.1 * 0.25 = 0.2 (small increase)
    assert curiosity_after_repeat > curiosity_after_decay, "Curiosity should increase even with low novelty"
    
    # Step 4: More time decay with no novelty
    agent.affect_state.decay_over_time(time_elapsed=120.0, half_life=60.0)
    curiosity_after_more_decay = agent.affect_state.curiosity
    # Expected: curiosity reduced to ~1/4 of previous (two half-lives)
    assert curiosity_after_more_decay < curiosity_after_repeat, "Curiosity should decrease over time"
    
    print(f"Initial curiosity: 0.1")
    print(f"After novel input (novelty=1.0): {curiosity_after_novel:.3f}")
    print(f"After 60s decay: {curiosity_after_decay:.3f}")
    print(f"After repeat w/ low novelty: {curiosity_after_repeat:.3f}")
    print(f"After 120s more decay: {curiosity_after_more_decay:.3f}")
    
    # Final check: curiosity should approach baseline (0.0) but not go negative
    assert curiosity_after_more_decay >= 0.0, "Curiosity should not be negative"
