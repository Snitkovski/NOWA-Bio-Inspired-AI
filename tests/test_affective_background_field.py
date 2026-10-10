import math

from affective_background import AffectiveBackgroundField


def _run_updates(field, traces, lifetime, wakefulness=1.0, steps=200):
    for _ in range(steps):
        field.update(traces, wakefulness=wakefulness, lifetime_progress=lifetime, time_elapsed=1.0)
    return field.snapshot()


def test_lifetime_inertia_increase():
    traces = {"anxiety": 0.4, "tension": 0.4, "satisfaction": 0.4, "interest": 0.4}

    young = AffectiveBackgroundField(noise_scale=0.0)
    old = AffectiveBackgroundField(noise_scale=0.0)

    y1 = young.update(traces, wakefulness=1.0, lifetime_progress=0.1)
    o1 = old.update(traces, wakefulness=1.0, lifetime_progress=0.9)

    assert o1["background_anxiety"] < y1["background_anxiety"]

    y_final = _run_updates(young, traces, lifetime=0.1, steps=300)
    o_final = _run_updates(old, traces, lifetime=0.9, steps=300)

    for k in y_final:
        assert abs(y_final[k] - o_final[k]) < 0.02


def test_no_lifetime_affect_injection():
    traces = {"anxiety": 0.5}

    young = AffectiveBackgroundField(noise_scale=0.0)
    old = AffectiveBackgroundField(noise_scale=0.0)

    y_final = _run_updates(young, traces, lifetime=0.1, steps=200)
    o_final = _run_updates(old, traces, lifetime=0.9, steps=200)

    assert abs(y_final["background_anxiety"] - o_final["background_anxiety"]) < 0.02

    zero_traces = {"anxiety": 0.0}
    young_zero = AffectiveBackgroundField(noise_scale=0.0)
    old_zero = AffectiveBackgroundField(noise_scale=0.0)
    z1 = _run_updates(young_zero, zero_traces, lifetime=0.1, steps=50)
    z2 = _run_updates(old_zero, zero_traces, lifetime=0.9, steps=50)
    assert z1["background_anxiety"] == 0.0
    assert z2["background_anxiety"] == 0.0


def test_wakefulness_independence():
    traces = {"anxiety": 0.4, "tension": 0.4, "satisfaction": 0.4, "interest": 0.4}

    low_w = AffectiveBackgroundField(noise_scale=0.06, rng=__import__("random").Random(0))
    high_w = AffectiveBackgroundField(noise_scale=0.06, rng=__import__("random").Random(0))

    low_values = []
    high_values = []
    for _ in range(200):
        low = low_w.update(traces, wakefulness=0.2, lifetime_progress=0.5)
        high = high_w.update(traces, wakefulness=1.0, lifetime_progress=0.5)
        low_values.append(low["background_anxiety"])
        high_values.append(high["background_anxiety"])

    low_mean = sum(low_values) / len(low_values)
    high_mean = sum(high_values) / len(high_values)

    low_var = sum((v - low_mean) ** 2 for v in low_values) / len(low_values)
    high_var = sum((v - high_mean) ** 2 for v in high_values) / len(high_values)

    assert abs(low_mean - high_mean) < 0.05
    assert low_var > high_var


def test_competition_sharpness():
    traces = {"anxiety": 0.20, "tension": 0.19, "satisfaction": 0.18, "interest": 0.17}

    young = AffectiveBackgroundField(noise_scale=0.0)
    old = AffectiveBackgroundField(noise_scale=0.0)

    y_final = _run_updates(young, traces, lifetime=0.1, steps=300)
    o_final = _run_updates(old, traces, lifetime=0.9, steps=300)

    def entropy(bg):
        vals = [bg[k] for k in sorted(bg.keys())]
        total = sum(vals) or 1.0
        p = [v / total for v in vals]
        return -sum(pi * math.log(pi + 1e-12) for pi in p)

    assert entropy(o_final) < entropy(y_final)

    young_active = sum(1 for v in y_final.values() if v > 0.15)
    old_active = sum(1 for v in o_final.values() if v > 0.15)
    assert young_active >= old_active
