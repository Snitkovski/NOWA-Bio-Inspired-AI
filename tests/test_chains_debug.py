#!/usr/bin/env python3
"""Debug script to test chain formation"""

import sys
sys.path.insert(0, 'src')

from agent import Agent
from hippocampus import NOWAHippocampus
from sleep import CortexMemory, SleepManager
from selector import ActionSelector
from intent_memory import IntentMemory
from experience import Event, Path, EventType

# Initialize
hip = NOWAHippocampus()
cortex = CortexMemory()
intent_mem = IntentMemory()
sleep_mgr = SleepManager(hip, cortex, intent_mem)
selector = ActionSelector(actions=['respond', 'ask', 'clarify', 'suggest'])
agent = Agent(hip, cortex, selector, sleep_mgr, intent_mem)

print("=" * 60)
print("TESTING CHAIN FORMATION")
print("=" * 60)

# Step 1: Send some messages
messages = [
    "привет",
    "как дела",
    "расскажи о себе"
]

for i, msg in enumerate(messages, 1):
    context = [f"user:{msg}"]
    action = agent.step(context)
    print(f"\nStep {i}: '{msg}'")
    print(f"  Action: {action}")
    print(f"  Experiences: {len(hip.experiences)}")
    
    # Show what's in path
    if hip.experiences:
        last_exp = hip.experiences[-1]
        print(f"  Path signature: {last_exp.path.signature()}")

# Step 2: Check before sleep
print("\n" + "=" * 60)
print("BEFORE SLEEP")
print("=" * 60)
print(f"Total experiences: {len(hip.experiences)}")
print(f"Total patterns: {len(cortex.patterns)}")
print(f"Chain memory: {sleep_mgr.chain_memory}")
print(f"Chains: {len(sleep_mgr.chain_memory.chains)}")

# Step 3: Sleep
print("\n" + "=" * 60)
print("SLEEPING...")
print("=" * 60)
sleep_cycles = 3
for cycle in range(sleep_cycles):
    stats = sleep_mgr.sleep_cycle()
    print(f"Cycle {cycle+1}: candidates={stats.get('candidates', 0)}, " +
          f"clusters={stats.get('clusters', 0)}, " +
          f"patterns={stats.get('patterns_consolidated', 0)}, " +
          f"chains={stats.get('chains_formed', 0)}")

# Step 4: Check after sleep
print("\n" + "=" * 60)
print("AFTER SLEEP")
print("=" * 60)
print(f"Total experiences: {len(hip.experiences)}")
print(f"Total patterns: {len(cortex.patterns)}")
print(f"Total chains: {len(sleep_mgr.chain_memory.chains)}")

if sleep_mgr.chain_memory.chains:
    print("\nChain details:")
    for i, (seq, chain) in enumerate(sleep_mgr.chain_memory.chains.items(), 1):
        print(f"  Chain {i}: {seq}")
        print(f"    Signature: {chain.signature}")
        print(f"    Stability: {chain.stability:.2f}")
        print(f"    Net affect: {chain.net_affect:.2f}")

# Step 5: Test statistics
stats = sleep_mgr.chain_memory.statistics()
print("\n" + "=" * 60)
print("STATISTICS")
print("=" * 60)
for key, val in stats.items():
    print(f"{key}: {val}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
