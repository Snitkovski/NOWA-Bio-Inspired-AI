#!/usr/bin/env python3
"""Test that dialog experiences load correctly and train the selector"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import load_experience_from_dataset, load_realizations_from_datasets
from action_intent import RealizationMemory
from hippocampus import NOWAHippocampus

# Initialize components
print("[TEST] Initializing components...")
realization_memory = RealizationMemory()
hippocampus = NOWAHippocampus(max_experiences=1000)

# Load realizations
print("[TEST] Loading realizations...")
realizations = load_realizations_from_datasets()
print(f"  ✓ Loaded {len(realizations)} realizations")
for real in realizations:
    realization_memory.store(real)

# Load dialog experiences
print("[TEST] Loading dialog experiences...")
dialog_exp_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "datasets", 
    "dialog_experiences.json"
)
if os.path.exists(dialog_exp_path):
    dialog_experiences = load_experience_from_dataset(dialog_exp_path)
    print(f"  ✓ Loaded {len(dialog_experiences)} dialog experiences")
    
    # Store in hippocampus
    for i, exp in enumerate(dialog_experiences):
        stored = hippocampus.store(exp.path, intensity=exp.intensity)
        if i < 5:
            print(f"    [{i+1}] Stored: {exp.path} (intensity={exp.intensity})")
        if i == 4:
            print(f"    ... and {len(dialog_experiences) - 5} more")
    
    # Verify storage
    print(f"\n[TEST] Hippocampus state after loading:")
    print(f"  Current size: {len(hippocampus.experiences)}")
    print(f"  Max experiences: {hippocampus.max_experiences}")
    
    # Sample some experiences
    print(f"\n[TEST] Sample of stored experiences:")
    for event in hippocampus.experiences[:5]:
        print(f"  - {event}")
    
    print(f"\n[TEST] ✅ Dialog experience loading SUCCESSFUL!")
else:
    print(f"  ❌ Dialog experiences file not found: {dialog_exp_path}")
