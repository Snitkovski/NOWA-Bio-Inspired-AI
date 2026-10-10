#!/usr/bin/env python3
"""Test saving and loading chains"""

import sys
sys.path.insert(0, 'src')

from agent import Agent
from hippocampus import NOWAHippocampus
from sleep import CortexMemory, SleepManager
from selector import ActionSelector
from intent_memory import IntentMemory
from storage import AgentStorage
import os

print("=" * 60)
print("TESTING CHAIN SAVE/LOAD")
print("=" * 60)

# Initialize
hip = NOWAHippocampus()
cortex = CortexMemory()
intent_mem = IntentMemory()
sleep_mgr = SleepManager(hip, cortex, intent_mem)
selector = ActionSelector(actions=['respond', 'ask', 'clarify', 'suggest'])
agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)
storage = AgentStorage()

# Step 1: Create some experience
print("\n1. Creating experiences...")
messages = ["привет", "как дела", "расскажи о себе"]
for msg in messages:
    context = [f"user:{msg}"]
    action = agent.step(context)
    print(f"   {msg} -> {action}")

# Step 2: Sleep and form chains
print("\n2. Sleep and form chains...")
for i in range(2):
    stats = sleep_mgr.sleep_cycle()
    print(f"   Cycle {i+1}: {stats['chains_formed']} chains formed")

# Step 3: Check chains before save
print("\n3. Chains before save:")
chains_before = sleep_mgr.chain_memory.chains.copy()
stats_before = sleep_mgr.chain_memory.statistics()
print(f"   Total: {stats_before['total_chains']}")
print(f"   Avg stability: {stats_before['avg_stability']:.2f}")
print(f"   Avg length: {stats_before['avg_length']:.2f}")

# Step 4: Save
print("\n4. Saving agent...")
save_path = storage.save_agent(hip, cortex, selector, sleep_manager=sleep_mgr, filename="test_chains.pkl")
print(f"   Saved to: {save_path}")

# Step 5: Create fresh agent
print("\n5. Creating fresh agent (without chains)...")
hip2 = NOWAHippocampus()
cortex2 = CortexMemory()
intent_mem2 = IntentMemory()
sleep_mgr2 = SleepManager(hip2, cortex2, intent_mem2)
selector2 = ActionSelector(actions=['respond', 'ask', 'clarify', 'suggest'])

print(f"   Chains in new agent: {len(sleep_mgr2.chain_memory.chains)}")

# Step 6: Load
print("\n6. Loading agent...")
storage.load_agent(hip2, cortex2, selector2, save_path, sleep_manager=sleep_mgr2)
print(f"   Loaded from: {save_path}")

# Step 7: Check chains after load
print("\n7. Chains after load:")
chains_after = sleep_mgr2.chain_memory.chains
stats_after = sleep_mgr2.chain_memory.statistics()
print(f"   Total: {stats_after['total_chains']}")
print(f"   Avg stability: {stats_after['avg_stability']:.2f}")
print(f"   Avg length: {stats_after['avg_length']:.2f}")

# Step 8: Verify
print("\n8. Verification:")
match = True
if stats_before['total_chains'] != stats_after['total_chains']:
    print(f"   ❌ Chain count mismatch: {stats_before['total_chains']} vs {stats_after['total_chains']}")
    match = False
else:
    print(f"   ✅ Chain count: {stats_after['total_chains']}")

if abs(stats_before['avg_stability'] - stats_after['avg_stability']) > 0.01:
    print(f"   ❌ Stability mismatch: {stats_before['avg_stability']:.2f} vs {stats_after['avg_stability']:.2f}")
    match = False
else:
    print(f"   ✅ Avg stability: {stats_after['avg_stability']:.2f}")

if abs(stats_before['avg_length'] - stats_after['avg_length']) > 0.01:
    print(f"   ❌ Length mismatch: {stats_before['avg_length']:.2f} vs {stats_after['avg_length']:.2f}")
    match = False
else:
    print(f"   ✅ Avg length: {stats_after['avg_length']:.2f}")

# Check individual chains
if len(chains_before) != len(chains_after):
    print(f"   ❌ Individual chain count mismatch: {len(chains_before)} vs {len(chains_after)}")
    match = False
else:
    for sig in chains_before:
        if sig not in chains_after:
            print(f"   ❌ Missing chain: {sig}")
            match = False
            break
    else:
        print(f"   ✅ All {len(chains_after)} chains present")

# Cleanup
print("\n9. Cleanup...")
os.remove(save_path)
print(f"   Removed: {save_path}")

print("\n" + "=" * 60)
if match:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 60)
