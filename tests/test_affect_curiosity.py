import time
from src.affect import AffectiveState


def test_curiosity_increases_on_novelty():
    a = AffectiveState()
    # default curiosity is 0.1
    assert abs(a.curiosity - 0.1) < 1e-6

    a.update_from_novelty(1.0)
    # with novelty=1.0 and growth rate 0.25, curiosity should increase by 0.25
    assert abs(a.curiosity - 0.35) < 1e-6

    # a second novelty of 0.5 increases by 0.125
    a.update_from_novelty(0.5)
    assert abs(a.curiosity - (0.35 + 0.125)) < 1e-6


def test_curiosity_caps_and_non_negative():
    a = AffectiveState(curiosity=0.9)
    a.update_from_novelty(1.0)
    # should cap at 1.0
    assert 0.9999 <= a.curiosity <= 1.0

    # negative novelty should have no effect (clamped in calling code), but ensure no negative
    a.curiosity = 0.2
    a.update_from_novelty(0.0)
    assert a.curiosity >= 0.0


def test_curiosity_decays_over_time():
    a = AffectiveState(curiosity=0.8)
    # simulate 300s (one half-life) so curiosity should halve
    a.decay_over_time(time_elapsed=300.0, half_life=300.0)
    assert abs(a.curiosity - 0.4) < 1e-6

    # long decay should approach zero but not negative
    a.curiosity = 0.5
    a.decay_over_time(time_elapsed=10000.0, half_life=300.0)
    assert 0.0 <= a.curiosity < 0.5
