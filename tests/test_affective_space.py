import random

from affective_space import AXES, AffectiveSpace, DECISION_DIMENSIONS, EmotionalImpulse, RANK_WEIGHT_KEYS


def test_affective_space_initialization_and_bounds():
    space = AffectiveSpace(
        axes={"valence": 1.5, "stress": -2.0},
        baseline={"valence": 0.2},
        alpha=1.1,
        lambda_reg=0.5,
        decay=1.5,
        inertia=-0.2,
        noise_sigma=-0.1,
        fall_rate=2.0,
    )

    for axis in AXES:
        assert axis in space.axes
        assert -1.0 <= space.axes[axis] <= 1.0
        assert -1.0 <= space.baseline[axis] <= 1.0

    assert 0.7 <= space.alpha <= 0.95
    assert 0.01 <= space.lambda_reg <= 0.1
    assert set(space.axis_decay.keys()) == set(AXES)
    assert set(space.affective_decay.keys()) == set(AXES)
    assert abs(space.axis_decay["valence"] - 0.92) < 1e-9
    assert abs(space.axis_decay["arousal"] - 0.80) < 1e-9
    assert abs(space.axis_decay["dominance"] - 0.97) < 1e-9
    assert abs(space.axis_decay["stress"] - 0.75) < 1e-9
    assert abs(space.axis_decay["curiosity"] - 0.78) < 1e-9
    assert abs(space.axis_decay["trust"] - 0.95) < 1e-9

    for axis in AXES:
        assert 0.0 <= space.decay[axis] <= 1.0
        assert 0.0 <= space.inertia[axis] <= 1.0
        assert 0.0 <= space.noise_sigma[axis] <= 1.0
        assert 0.0 <= space.fall_rate[axis] <= 1.0


def test_affective_space_supports_legacy_axis_input():
    space = AffectiveSpace(axes={"pleasure": 0.9, "pain": 0.8, "vulnerability": 0.5})

    assert space.axes["stress"] > 0.0
    assert space.axes["stability"] < 0.0


def test_affective_space_dynamics_update():
    rng = random.Random(0)
    space = AffectiveSpace(
        axes={"valence": 0.5},
        baseline={"valence": 0.2},
        alpha=0.9,
        lambda_reg=0.05,
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
        rng=rng,
    )

    space.step(
        external_impulses=[EmotionalImpulse(vector={"valence": 0.4}, intensity=0.5)],
        time_elapsed=1.0,
        wakefulness=0.0,
        uncertainty=0.0,
        conflict=0.0,
        background={},
    )

    # baseline + axis_decay[valence]*(x-baseline) + ext - lambda*(x-baseline)
    expected = 0.2 + (space.axis_decay["valence"] * (0.5 - 0.2)) + 0.2 - (0.05 * (0.5 - 0.2))
    assert abs(space.axes["valence"] - expected) < 1e-6


def test_affective_space_default_axis_decay_bias():
    space = AffectiveSpace(
        axes={"valence": 0.6, "arousal": 0.6, "dominance": 0.6, "stress": 0.6, "curiosity": 0.6, "trust": 0.6},
        baseline={"valence": 0.0, "arousal": 0.0, "dominance": 0.0, "stress": 0.0, "curiosity": 0.0, "trust": 0.0},
        lambda_reg=0.0,
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
    )

    space.step(time_elapsed=1.0)

    assert space.axes["stress"] < space.axes["curiosity"] < space.axes["arousal"] < space.axes["valence"]
    assert space.axes["valence"] < space.axes["trust"] < space.axes["dominance"]


def test_affective_space_affective_decay_alias_with_legacy_keys():
    space = AffectiveSpace(
        axes={"valence": 0.8, "arousal": 0.8, "dominance": 0.8},
        baseline={"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
        lambda_reg=0.0,
        decay=0.0,
        inertia=0.0,
        noise_sigma=0.0,
        affective_decay={"pleasure": 0.5, "arousal": 0.2, "dominance": 0.9},
    )

    space.step(time_elapsed=1.0)

    valence_expected = (0.8 * space.axis_decay["valence"]) - (space.lambda_reg * 0.8)
    arousal_expected = (0.8 * space.axis_decay["arousal"]) - (space.lambda_reg * 0.8)
    dominance_expected = (0.8 * space.axis_decay["dominance"]) - (space.lambda_reg * 0.8)

    assert abs(space.axes["valence"] - valence_expected) < 1e-6
    assert abs(space.axes["arousal"] - arousal_expected) < 1e-6
    assert abs(space.axes["dominance"] - dominance_expected) < 1e-6


def test_affective_space_from_dict_supports_affective_decay_alias():
    restored = AffectiveSpace.from_dict(
        {
            "axes": {"valence": 0.3},
            "affective_decay": {"pleasure": 0.61, "arousal": 0.44, "dominance": 0.98},
        }
    )

    assert abs(restored.axis_decay["valence"] - 0.61) < 1e-9
    assert abs(restored.axis_decay["arousal"] - 0.44) < 1e-9
    assert abs(restored.axis_decay["dominance"] - 0.98) < 1e-9


def test_affective_space_speed_and_distance():
    space = AffectiveSpace(axes={"valence": 0.2, "stress": 0.4}, noise_sigma=0.0)
    space.last_axes = {axis: 0.1 for axis in AXES}

    speed = space.speed()
    expected_speed = abs(0.2 - 0.1) + abs(0.4 - 0.1) + sum(abs(0.0 - 0.1) for _ in range(len(AXES) - 2))
    assert abs(speed - expected_speed) < 1e-6

    other = {"valence": 0.5, "stress": 0.0}
    distance = space.distance_to(other, weights={"valence": 2.0})
    expected_distance = 2.0 * abs(0.2 - 0.5) + abs(0.4 - 0.0)
    assert abs(distance - expected_distance) < 1e-6


def test_affective_space_background_modulation():
    space = AffectiveSpace()
    decay_mult, inertia_mult, noise_mult = space.get_background_modifiers(
        {"background_anxiety": 1.0, "background_interest": 1.0}
    )

    assert decay_mult < 1.0
    assert inertia_mult > 1.0
    assert noise_mult > 1.0


def test_affective_space_axis_conflict():
    space = AffectiveSpace(axes={"valence": 0.8, "stress": 0.7, "trust": 0.6})
    conflict = space.axis_conflict()
    assert conflict > 0.0


def test_affective_space_decision_bias_shape():
    space = AffectiveSpace(axes={"valence": 0.4, "arousal": 0.6, "stress": 0.2, "trust": 0.3})
    bias = space.decision_bias()

    assert set(bias.keys()) == set(DECISION_DIMENSIONS)
    for value in bias.values():
        assert -1.0 <= float(value) <= 1.0


def test_outcome_impulse_maps_status_onto_canonical_axes():
    impulse = AffectiveSpace.outcome_impulse("accepted", 1.0)
    vector = impulse.to_core_vector() if hasattr(impulse, "to_core_vector") else dict(impulse.vector)
    for axis in AXES:
        assert -1.0 <= float(vector.get(axis, 0.0)) <= 1.0
    assert vector["valence"] > 0.0
    failed = AffectiveSpace.outcome_impulse("error", 1.0)
    fail_vec = failed.to_core_vector() if hasattr(failed, "to_core_vector") else dict(failed.vector)
    assert fail_vec["valence"] < 0.0
    assert fail_vec["stress"] > 0.0


def test_rank_weights_monotonic_stress_and_curiosity():
    calm = AffectiveSpace(axes={"stress": -0.8, "curiosity": 0.0}, noise_sigma=0.0)
    tense = AffectiveSpace(axes={"stress": 0.9, "curiosity": 0.0}, noise_sigma=0.0)
    assert tense.rank_weights()["caution"] >= calm.rank_weights()["caution"]
    dull = AffectiveSpace(axes={"curiosity": -0.8, "stress": 0.0}, noise_sigma=0.0)
    curious = AffectiveSpace(axes={"curiosity": 0.9, "stress": 0.0}, noise_sigma=0.0)
    assert curious.rank_weights()["novelty_seek"] >= dull.rank_weights()["novelty_seek"]
    for key in RANK_WEIGHT_KEYS:
        assert 0.0 <= float(calm.rank_weights()[key]) <= 1.0
