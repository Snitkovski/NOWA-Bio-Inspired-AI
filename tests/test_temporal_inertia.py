from src.temporal import TemporalLevels
from src.affect import AffectiveState


def make_snapshot(valence=0.0, arousal=0.0, threat=0.0, curiosity=0.0):
    state = AffectiveState(
        valence=valence,
        arousal=arousal,
        threat=threat,
        curiosity=curiosity,
    )
    return state.snapshot()


def test_temporal_inertia_without_sleep():
    tl = TemporalLevels(window_size=10)
    for _ in range(10):
        tl.log(make_snapshot(valence=0.6))

    tl.log(make_snapshot(valence=-0.9))

    levels = tl.get_levels()
    t0 = levels["T0"]
    t2 = levels["T2_baseline"]

    assert t0["valence"] < 0
    assert tl.trend()["valence"] < 0
    assert t2.get("valence", 0.0) > 0.0


def test_sleep_strengthens_baseline():
    tl_wake = TemporalLevels(window_size=10)
    tl_sleep = TemporalLevels(window_size=10)

    for _ in range(10):
        snap = make_snapshot(valence=0.6)
        tl_wake.log(snap)
        tl_sleep.log(snap)

    for _ in range(3):
        tl_sleep.sleep()

    tl_wake.log(make_snapshot(valence=-0.9))
    tl_sleep.log(make_snapshot(valence=-0.9))

    wake_t2 = tl_wake.get_levels()["T2_baseline"].get("valence", 0.0)
    sleep_t2 = tl_sleep.get_levels()["T2_baseline"].get("valence", 0.0)
    sleep_t3 = tl_sleep.get_levels()["T3_attractor"].get("valence", 0.0)

    assert sleep_t2 > wake_t2
    assert sleep_t3 > 0.0


def test_cold_start_neutral():
    tl = TemporalLevels(window_size=10)
    for _ in range(3):
        tl.log(make_snapshot())

    levels = tl.get_levels()
    assert abs(levels["T0"].get("valence", 0.0)) < 0.01
    assert abs(levels["T1_mean"].get("valence", 0.0)) < 0.01
    assert abs(levels["T2_baseline"].get("valence", 0.0)) < 0.01
    assert abs(levels["T3_attractor"].get("valence", 0.0)) < 0.01
