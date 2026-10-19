from __future__ import annotations

import pytest
from learning_guard import learning_allowed

@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct tests of stable writers. Sleep opens the same guard."""
    with learning_allowed():
        yield

"""K03: habit keys are a canonical set, not the last event.

Different situations that share a tail event must not share a key, and a
permutation of the same events must. Old saves that stored only the legacy
tail hash still load. Signatures use md5, not PYTHONHASHSEED-salted hash().
"""

import hashlib
import time

from intent_memory import IntentMemory


def _legacy_tail(context: list[str]) -> str:
    return hashlib.md5(context[-1].encode()).hexdigest()[:8]


def test_distinct_situations_do_not_share_a_habit_key():
    memory = IntentMemory()
    hungry = ["zone:floor", "food_ok", "hunger_high"]
    alarmed = ["zone:floor", "alarm_call", "hunger_high"]
    assert memory._compute_context_signature(hungry) != memory._compute_context_signature(alarmed)
    assert _legacy_tail(hungry) == _legacy_tail(alarmed)


def test_habit_key_is_independent_of_event_order():
    memory = IntentMemory()
    left = ["alarm_call", "zone:wheel", "hunger_high", "food_ok"]
    right = ["food_ok", "hunger_high", "zone:wheel", "alarm_call"]
    assert memory._compute_context_signature(left) == memory._compute_context_signature(right)
    duplicated = ["hunger_high", "food_ok", "hunger_high", "alarm_call", "zone:wheel"]
    assert memory._compute_context_signature(duplicated) == memory._compute_context_signature(left)


def test_single_event_key_matches_the_historical_hash():
    memory = IntentMemory()
    event = "hunger_high"
    assert memory._compute_context_signature([event]) == hashlib.md5(event.encode()).hexdigest()[:8]


def test_learned_habits_do_not_lock_across_aliased_situations():
    memory = IntentMemory()
    hungry = ["food_ok", "hunger_high"]
    alarmed = ["alarm_call", "hunger_high"]
    for _ in range(25):
        memory.apply_outcome(hungry, "eat", 1.0)
        memory.apply_outcome(alarmed, "hide", 1.0)
    hungry_key = memory._compute_context_signature(hungry)
    alarmed_key = memory._compute_context_signature(alarmed)
    assert hungry_key != alarmed_key
    assert memory.traces[f"eat:{hungry_key}"].strength > 0.9
    assert memory.traces[f"hide:{alarmed_key}"].strength > 0.9
    assert memory.traces.get(f"hide:{hungry_key}") is None
    assert memory.traces.get(f"eat:{alarmed_key}") is None


def test_old_habit_save_without_features_still_activates():
    legacy = hashlib.md5("hunger_high".encode()).hexdigest()[:8]
    memory = IntentMemory.from_dict(
        {
            "context_signature_window": 1,
            "traces": [
                {
                    "intent_type": "eat",
                    "context_signature": legacy,
                    "strength": 2.0,
                    "recency": 1.0,
                    "timestamp": time.time(),
                }
            ],
        }
    )
    pressure = memory.activate_by_context(["zone:floor", "bored", "hunger_high"])
    assert pressure.get("eat", 0.0) > 0.0
    restored = IntentMemory.from_dict(memory.to_dict())
    again = restored.activate_by_context(["bored", "zone:floor", "hunger_high"])
    assert again.get("eat", 0.0) > 0.0
