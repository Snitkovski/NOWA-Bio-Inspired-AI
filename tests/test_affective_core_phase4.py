import math
import random

from affective_space import AXES, AffectiveSpace, EmotionalImpulse, EmotionalTrace


def _mean_abs_delta(a, b):
    return sum(abs(float(a.get(axis, 0.0)) - float(b.get(axis, 0.0))) for axis in AXES) / float(len(AXES))


def test_phase4_tc1_neutral_environment_converges_to_baseline():
    space = AffectiveSpace(
        axes={"valence": -0.8, "stress": 0.7},
        baseline={"valence": 0.25, "stress": -0.15},
        alpha=0.9,
        lambda_reg=0.05,
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
    )

    baseline = dict(space.baseline)
    dist_before = _mean_abs_delta(space.axes, baseline)

    for _ in range(20):
        space.step(time_elapsed=1.0)

    dist_after = _mean_abs_delta(space.axes, baseline)

    assert dist_after < dist_before
    assert abs(space.axes["valence"] - baseline["valence"]) < 0.1
    assert abs(space.axes["stress"] - baseline["stress"]) < 0.1


def test_phase4_tc2_strong_positive_external_impulse_and_decay():
    space = AffectiveSpace(decay=0.0, inertia=0.0, noise_sigma=0.0)

    space.step(
        external_impulses=[EmotionalImpulse(vector={"valence": 1.0, "arousal": 1.0}, intensity=0.8, source="external")],
        time_elapsed=1.0,
    )

    peak_valence = float(space.axes["valence"])
    peak_arousal = float(space.axes["arousal"])

    assert peak_valence > 0.0
    assert peak_arousal > 0.0

    for _ in range(15):
        space.step(time_elapsed=1.0)

    assert abs(space.axes["valence"]) < abs(peak_valence)
    assert abs(space.axes["arousal"]) < abs(peak_arousal)


def test_phase4_tc3_recall_impulse_is_limited_and_no_runaway():
    space = AffectiveSpace(decay=0.0, inertia=0.0, noise_sigma=0.0)

    ext = EmotionalImpulse(vector={axis: 0.6 for axis in AXES}, intensity=1.0, source="external")
    space.step(external_impulses=[ext], time_elapsed=1.0)

    trace = EmotionalTrace(snapshot_vector={"valence": -1.0, "stress": 1.0}, intensity=1.0, decay_rate=0.0)
    recall = space.recall_trace(trace, k=0.4)

    before = dict(space.axes)
    space.step(recall_impulses=[recall], time_elapsed=1.0)
    after = dict(space.axes)

    # Approximate recall contribution relative to no-recall inertial prediction.
    predicted_no_recall = {
        axis: float(space.baseline.get(axis, 0.0))
        + (
            (float(space.axis_decay.get(axis, space.alpha)) - space.lambda_reg)
            * (float(before.get(axis, 0.0)) - float(space.baseline.get(axis, 0.0)))
        )
        for axis in AXES
    }
    recall_effect_mean = _mean_abs_delta(after, predicted_no_recall)
    assert recall_effect_mean <= (0.3 * float(space.last_external_mean_impulse)) + 1e-6

    for _ in range(40):
        space.step(recall_impulses=[recall], time_elapsed=1.0)
    assert all(-1.0 <= float(space.axes[axis]) <= 1.0 for axis in AXES)


def test_phase4_tc4_conflict_past_and_present_current_dominates():
    space = AffectiveSpace(decay=0.0, inertia=0.0, noise_sigma=0.0)

    trace = EmotionalTrace(snapshot_vector={"valence": -1.0, "stress": 1.0}, intensity=1.0, decay_rate=0.0)
    recall = space.recall_trace(trace, k=0.35)

    space.step(
        external_impulses=[EmotionalImpulse(vector={"valence": 0.9, "arousal": 0.4}, intensity=1.0, source="external")],
        recall_impulses=[recall],
        time_elapsed=1.0,
    )

    assert space.axes["valence"] > 0.0
    assert space.axes["stress"] >= 0.0


def test_phase4_tc5_long_stress_pressure_and_return():
    space = AffectiveSpace(decay=0.0, inertia=0.0, noise_sigma=0.0)

    for _ in range(30):
        space.step(
            external_impulses=[EmotionalImpulse(vector={"stress": 0.08}, intensity=1.0, source="external")],
            time_elapsed=1.0,
        )
    stressed = float(space.axes["stress"])

    for _ in range(40):
        space.step(time_elapsed=1.0)
    recovered = float(space.axes["stress"])

    assert stressed > 0.2
    assert recovered < stressed
    assert abs(recovered - float(space.baseline.get("stress", 0.0))) < 0.2


def test_phase4_norm_cap_adapts_under_long_pressure_and_relaxes():
    space = AffectiveSpace(
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
        norm_cap_base=1.5,
        norm_cap_max=2.1,
        norm_cap_adapt_rate=0.12,
        norm_cap_release_rate=0.03,
    )

    for _ in range(50):
        space.step(
            external_impulses=[EmotionalImpulse(vector={axis: 1.0 for axis in AXES}, intensity=1.0, source="external")],
            time_elapsed=1.0,
            wakefulness=1.0,
        )

    grown_cap = float(space.dynamic_norm_cap or 0.0)
    assert grown_cap > 1.5
    assert grown_cap <= 2.1

    state_norm = math.sqrt(sum(float(space.axes.get(axis, 0.0)) ** 2 for axis in AXES))
    assert state_norm <= grown_cap + 1e-6

    for _ in range(80):
        space.step(time_elapsed=1.0)

    relaxed_cap = float(space.dynamic_norm_cap or 0.0)
    assert relaxed_cap < grown_cap
    assert relaxed_cap >= 1.5


def test_phase4_legacy_compat_delta_disabled_by_default():
    space = AffectiveSpace(
        axes={"valence": 0.5},
        baseline={"valence": 0.2},
        alpha=0.9,
        lambda_reg=0.05,
        decay={"valence": 0.6},
        inertia={"valence": 0.4},
        noise_sigma={"valence": 0.7},
        rng=random.Random(0),
    )

    space.step(time_elapsed=1.0)

    expected = 0.2 + (space.axis_decay["valence"] * (0.5 - 0.2)) - (0.05 * (0.5 - 0.2))
    assert abs(space.axes["valence"] - expected) < 1e-6
    assert abs(space.last_noise_sigma["valence"]) < 1e-12


def test_phase4_legacy_compat_delta_can_be_opted_in():
    space = AffectiveSpace(
        axes={"valence": 0.6},
        baseline={"valence": 0.0},
        alpha=0.85,
        lambda_reg=0.05,
        legacy_compat_weight=1.0,
        decay={"valence": 0.4},
        inertia={"valence": 0.0},
        noise_sigma={"valence": 0.0},
    )

    space.step(time_elapsed=1.0)

    canonical = 0.6 * (space.axis_decay["valence"] - space.lambda_reg)
    legacy = -0.4 * 0.6
    assert abs(space.axes["valence"] - (canonical + legacy)) < 1e-6


def test_phase4_norm_cap_global_release_prevents_sticky_max():
    space = AffectiveSpace(
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
        norm_cap_base=1.5,
        norm_cap_max=2.1,
        norm_cap_adapt_rate=0.0,
        norm_cap_release_rate=0.0,
        norm_cap_global_release_rate=0.05,
        dynamic_norm_cap=2.0,
    )

    for _ in range(12):
        space.step(time_elapsed=1.0)

    relaxed_cap = float(space.dynamic_norm_cap or 0.0)
    assert relaxed_cap < 2.0
    assert relaxed_cap > 1.5


def test_phase4_baseline_is_dynamic_under_sustained_state():
    space = AffectiveSpace(
        axes={"curiosity": 0.0},
        baseline={"curiosity": 0.0},
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
        baseline_adapt_rate=0.04,
    )

    start_baseline = float(space.baseline["curiosity"])
    for _ in range(40):
        space.step(
            external_impulses=[EmotionalImpulse(vector={"curiosity": 0.35}, intensity=1.0, source="external")],
            time_elapsed=1.0,
        )

    end_baseline = float(space.baseline["curiosity"])
    assert end_baseline > start_baseline + 0.1
    assert end_baseline <= float(space.axes["curiosity"]) + 1e-6
