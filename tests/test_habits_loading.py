
import pytest
from learning_guard import learning_allowed

@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct tests of stable writers. Sleep opens the same guard."""
    with learning_allowed():
        yield

#!/usr/bin/env python3
"""Быстрая проверка загрузки привычек"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import load_habits_from_datasets
from intent_memory import IntentMemory

# Load habits
habits = load_habits_from_datasets()
print(f"\n✅ Загружено {len(habits)} привычек из датасета")

if habits:
    print("\nПервые 5 привычек:")
    for i, h in enumerate(habits[:5], 1):
        context = h['context'][-1] if h['context'] else "N/A"
        print(f"  {i}. {context} → {h['action']} (strength={h['strength']})")

# Test IntentMemory
print("\n" + "="*60)
print("Тест IntentMemory с загруженными привычками")
print("="*60)

intent_memory = IntentMemory()

# Dataset seeding is host initialization, not waking learning.
with learning_allowed():
    for habit in habits:
        for _ in range(int(habit['strength'])):
            intent_memory.record_trace(habit['context'], habit['action'])

print(f"\n✅ Записано {len(intent_memory.traces)} traces в IntentMemory")

stats = intent_memory.get_stats()
print(f"\nСтатистика по действиям:")
for action, data in sorted(stats['by_intent'].items()):
    print(f"  {action}:")
    print(f"    - Traces: {data['count']}")
    print(f"    - Total strength: {data['total_strength']:.1f}")
    print(f"    - Avg strength: {data['avg_strength']:.2f}")

print("\n✅ Все работает корректно!")
