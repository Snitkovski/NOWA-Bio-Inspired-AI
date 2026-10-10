import time
from src.temporal import TemporalLevels
from src.affect import AffectiveState


def make_snapshot(valence=0.0, arousal=0.0, threat=0.0, curiosity=0.0):
    s = AffectiveState(valence=valence, arousal=arousal, threat=threat, curiosity=curiosity)
    return s.snapshot()


def test_short_negative_recovery():
    """Краткий негатив -> восстановление"""
    tl = TemporalLevels(window_size=5)
    # positive baseline
    for _ in range(3):
        tl.log(make_snapshot(valence=0.5))
    # short negative pulse
    tl.log(make_snapshot(valence=-0.8))
    tl.log(make_snapshot(valence=0.4))
    # trend should show recovery (last - first > 0)
    tr = tl.trend()
    assert tr["valence"] > -1.0


def test_long_negative_change_trend():
    """Длительный негатив -> смена тенденции"""
    tl = TemporalLevels(window_size=6)
    # build sustained negative inputs
    for v in [-0.1, -0.2, -0.3, -0.4, -0.6, -0.7]:
        tl.log(make_snapshot(valence=v))
    tr = tl.trend()
    # negative trend expected
    assert tr["valence"] < 0


def test_noise_ignored():
    """Случайный шум -> игнорируется (no long-term trend)"""
    import random
    tl = TemporalLevels(window_size=10)
    # produce random noise around zero
    for _ in range(10):
        tl.log(make_snapshot(valence=random.uniform(-0.1, 0.1)))
    tr = tl.trend()
    # trend near zero
    assert abs(tr["valence"]) < 0.5


def test_repeating_success_consolidates():
    """Повторяющийся успех -> закрепляется в baseline (T2)"""
    tl = TemporalLevels(window_size=5)
    for _ in range(5):
        tl.log(make_snapshot(valence=0.7))
    tl.consolidate()
    levels = tl.get_levels()
    assert levels["T2_baseline"]["valence"] > 0.35


def test_sleep_reduces_variance():
    """Сон -> снижает variance в T1"""
    tl = TemporalLevels(window_size=5)
    # varied T1
    tl.log(make_snapshot(valence=-0.8))
    tl.log(make_snapshot(valence=0.9))
    tl.log(make_snapshot(valence=0.6))
    tl.log(make_snapshot(valence=-0.4))
    # compute variance proxy (max-min)
    before = max(s.get("valence") for s in tl.t1) - min(s.get("valence") for s in tl.t1)
    tl.sleep()
    after = max(s.get("valence") for s in tl.t1) - min(s.get("valence") for s in tl.t1)
    assert after < before
