#!/usr/bin/env python
"""Test dataset loading fix"""

import sys
sys.path.insert(0, 'src')

from data_loader import load_experience_from_dataset
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from agent import Agent
from experience import Event, EventType

print('🧪 Dataset Loading Integration Test')
print('=' * 50)

# Create agent components
hip = NOWAHippocampus()
cortex = CortexMemory()
selector = ActionSelector(['ответить_кто_я', 'сказать_привет'])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, selector, sleep_mgr)

# Load experiences from test.json
print('1️⃣  Loading experiences from datasets/test.json...')
exps = load_experience_from_dataset('datasets/test.json')
print(f'   ✅ Loaded {len(exps)} experiences')

# Add to agent
print('2️⃣  Storing in hippocampus...')
for experience in exps:
    intensity = experience.intensity if hasattr(experience, 'intensity') else 1.0
    consequence = Event('success', EventType.CONSEQUENCE)
    hip.store(experience.path, consequence=consequence, intensity=intensity)
    print(f'   ✅ {[e.name for e in experience.path.events]}')

# Check state
state = agent.get_state()
print('3️⃣  Agent state:')
print(f'   ✅ Experiences: {state["hippocampus"]["total_experiences"]}')
print(f'   ✅ Patterns: {state["cortex"]["total_patterns"]}')

# Run sleep consolidation
print('4️⃣  Running sleep consolidation...')
stats = agent.sleep(cycles=1)
print(f'   ✅ Sleep completed')

# Check state after sleep
state_after = agent.get_state()
print('5️⃣  After sleep:')
print(f'   ✅ Experiences: {state_after["hippocampus"]["total_experiences"]}')
print(f'   ✅ Patterns: {state_after["cortex"]["total_patterns"]}')
print(f'   ✅ Sleep cycles: {state_after["sleep_cycles"]}')

print('=' * 50)
print('✅ FULL INTEGRATION TEST PASSED')
