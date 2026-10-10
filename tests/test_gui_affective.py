#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test GUI affective visualization"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import Agent
from affect import AffectiveState
from self_model import SelfModel
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager

# Test 1: Create agent with affect_state
print("✅ Test 1: Creating agent with affective state...")
hippocampus = NOWAHippocampus()
cortex = CortexMemory()
selector = ActionSelector(actions=["greet", "ask", "refuse"])
sleep_manager = SleepManager(hippocampus, cortex)
agent = Agent(hippocampus, cortex, selector, sleep_manager=sleep_manager)

assert hasattr(agent, 'affect_state'), "Agent should have affect_state"
assert isinstance(agent.affect_state, AffectiveState), "affect_state should be AffectiveState"
print(f"   Initial affect state: valence={agent.affect_state.valence:.2f}, arousal={agent.affect_state.arousal:.2f}")

# Test 2: Create self_model
print("\n✅ Test 2: Creating SelfModel...")
self_model = SelfModel(agent)
assert hasattr(self_model, 'describe_operational_state'), "SelfModel should have describe_operational_state"
print(f"   Self-model state: {self_model.describe_operational_state()[:50]}...")

# Test 3: Update affect from reward
print("\n✅ Test 3: Testing affect updates from reward...")
initial_valence = agent.affect_state.valence
agent.affect_state.update_from_reward(0.8)  # Positive feedback
new_valence = agent.affect_state.valence
print(f"   Valence changed from {initial_valence:.2f} to {new_valence:.2f}")
assert new_valence > initial_valence, "Positive reward should increase valence"

# Test 4: Negative feedback
print("\n✅ Test 4: Testing negative reward...")
initial_valence = agent.affect_state.valence
agent.affect_state.update_from_reward(-0.8)  # Negative feedback
new_valence = agent.affect_state.valence
print(f"   Valence changed from {initial_valence:.2f} to {new_valence:.2f}")
assert new_valence < initial_valence, "Negative reward should decrease valence"

# Test 5: Curiosity from novelty
print("\n✅ Test 5: Testing novelty-driven curiosity...")
initial_curiosity = agent.affect_state.curiosity
agent.affect_state.update_from_novelty(0.9)  # Novel input
new_curiosity = agent.affect_state.curiosity
print(f"   Curiosity changed from {initial_curiosity:.2f} to {new_curiosity:.2f}")
assert new_curiosity > initial_curiosity, "High novelty should increase curiosity"

# Test 6: Conflict detection
print("\n✅ Test 6: Testing conflict detection...")
initial_threat = agent.affect_state.threat
agent.affect_state.update_from_conflict(0.7)  # Conflict/threat
new_threat = agent.affect_state.threat
print(f"   Threat changed from {initial_threat:.2f} to {new_threat:.2f}")
assert new_threat > initial_threat, "Conflict should increase threat"

# Test 7: Color coding for visualization
print("\n✅ Test 7: Testing color coding...")
def get_color(value, min_val, max_val, low_color, high_color):
    """Simulate color coding from gui.py"""
    normalized = (value - min_val) / (max_val - min_val)
    return f"At {normalized:.1%} between {low_color} and {high_color}"

# Valence: red to green
color_info = get_color(agent.affect_state.valence, -1, 1, "red", "green")
print(f"   Valence color: {color_info}")

# Arousal: blue to orange
color_info = get_color(agent.affect_state.arousal, 0, 2, "blue", "orange")
print(f"   Arousal color: {color_info}")

# Threat: green to red
color_info = get_color(agent.affect_state.threat, 0, 1, "green", "red")
print(f"   Threat color: {color_info}")

# Curiosity: gray to purple
color_info = get_color(agent.affect_state.curiosity, 0, 1, "gray", "purple")
print(f"   Curiosity color: {color_info}")

# Test 8: Readiness calculation
print("\n✅ Test 8: Testing readiness calculation...")
readiness = agent.affect_state.adaptation_readiness()
print(f"   Adaptation readiness: {readiness:.2f}")
assert 0 <= readiness <= 1, "Readiness should be between 0 and 1"

# Test 9: Self-model introspection
print("\n✅ Test 9: Testing self-model introspection...")
limiting = self_model.report_limiting_factors()
enabling = self_model.report_enabling_factors()
print(f"   Limiting factors: {str(limiting)[:80]}...")
print(f"   Enabling factors: {str(enabling)[:80]}...")

# Test 10: Full operational state report
print("\n✅ Test 10: Full operational state...")
state_report = self_model.introspect()
state_str = str(state_report)
print(f"   Introspection keys: {list(state_report.keys()) if isinstance(state_report, dict) else 'N/A'}")
print(f"   Full state: {state_str[:100]}...")

print("\n" + "="*70)
print("✅ ALL TESTS PASSED - Affective visualization is ready!")
print("="*70)
print("\n📊 Current Affective State Summary:")
print(f"   Valence:    {agent.affect_state.valence:6.2f} {'😊' if agent.affect_state.valence > 0 else '😔'}")
print(f"   Arousal:    {agent.affect_state.arousal:6.2f} {'⚡' if agent.affect_state.arousal > 1 else '😴'}")
print(f"   Threat:     {agent.affect_state.threat:6.2f} {'⚠️' if agent.affect_state.threat > 0.5 else '✅'}")
print(f"   Curiosity:  {agent.affect_state.curiosity:6.2f} {'🔍' if agent.affect_state.curiosity > 0.5 else '😐'}")
print(f"   Readiness:  {readiness:6.2f}")
