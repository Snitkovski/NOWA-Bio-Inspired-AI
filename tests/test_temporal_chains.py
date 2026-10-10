import pytest

from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from sleep import SleepManager
from selector import ActionSelector
from experience import Path, Event, EventType


def make_path_from_names(names):
    p = Path()
    for n in names:
        if n.startswith('action:'):
            p = p.add_event(Event(n, event_type=EventType.ACTION))
        else:
            p = p.add_event(Event(n, event_type=EventType.CONTEXT))
    return p


def test_chain_formation_and_bias():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent = None
    sm = SleepManager(hip, cortex, intent)

    # Create a short behavioural sequence with an action and positive feedback
    p1 = make_path_from_names(['user:hello', 'action:say_hello'])
    fb = Event('feedback:2', EventType.CONSEQUENCE)
    e1 = hip.store(p1, consequence=fb, intensity=1.0)
    # Reinforce so it becomes candidate for sleep consolidation
    e1.reinforcement_count = 2
    e1.activation_energy = 1.0
    e1.stability = 0.0

    # Run a sleep cycle - chains should be formed
    stats = sm.sleep_cycle()
    # chains_formed added to stats by SleepManager
    assert 'chains_formed' in stats
    assert stats['chains_formed'] >= 1

    ch_stats = sm.chain_memory.statistics()
    assert ch_stats['total_chains'] > 0

    # Build a recent flat sequence that matches the chain
    recent = list(p1.signature())
    bias = sm.chain_memory.match_bias(recent)
    # There should be bias for the action 'say_hello'
    assert isinstance(bias, dict)
    assert 'say_hello' in bias

    # Now check that selector uses the bias when no other pressures exist
    sel = ActionSelector(actions=['say_hello', 'do_nothing'])
    chosen = sel.choose([], [], intent_pressure=None, affect_modifier=1.0, temporal_chains_bias=bias)
    assert chosen == 'say_hello'
