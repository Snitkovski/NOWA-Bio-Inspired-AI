#!/usr/bin/env python3
"""Check what's actually saved in the file"""

import sys
sys.path.insert(0, 'src')

import pickle
import os
from pathlib import Path

saves_dir = Path('saves')
if not saves_dir.exists():
    print("No saves directory!")
    sys.exit(1)

# Get latest save file
files = sorted(saves_dir.glob('*.pkl'), key=os.path.getmtime, reverse=True)
if not files:
    print("No save files!")
    sys.exit(1)

latest = files[0]
print(f"Checking: {latest}")
print(f"Size: {latest.stat().st_size} bytes")
print()

with open(latest, 'rb') as f:
    data = pickle.load(f)

print("Keys in saved data:")
for key in data.keys():
    print(f"  • {key}")

print()
print("sleep_manager content:")
if 'sleep_manager' in data:
    sm = data['sleep_manager']
    print(f"  Type: {type(sm)}")
    print(f"  Keys: {list(sm.keys())}")
    
    for key, val in sm.items():
        print(f"  • {key}: {type(val)} = {val if not isinstance(val, dict) else f'dict with {len(val)} keys'}")
        
        if key == 'chain_memory' and isinstance(val, dict):
            print(f"      chains key: {'chains' in val}")
            if 'chains' in val:
                print(f"      number of chains: {len(val['chains'])}")
                if val['chains']:
                    print(f"      first chain key: {list(val['chains'].keys())[0]}")
else:
    print("  'sleep_manager' not in saved data!")

print()
print("[IMPORTANT] Check if your saved file was created BEFORE the chain save/load was fixed!")
print("If so, you need to manually test with a NEW save that has chains.")
