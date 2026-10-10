import pytest

from neuromodulators import NeuromodulatorState


def _manual_effective_conflict(
    nm: NeuromodulatorState,
    conflict: float,
    norepinephrine: float,
    cortisol: float,
    serotonin: float,
) -> float:
    conflict_v = max(0.0, min(1.0, float(conflict)))
    norepinephrine_v = max(0.0, min(1.0, float(norepinephrine)))
    cortisol_v = max(0.0, min(1.0, float(cortisol)))
    serotonin_v = max(0.0, min(1.0, float(serotonin)))

    ne_delta = norepinephrine_v - nm.BASELINE_NE
    arousal_delta = ne_delta / (1.0 + abs(ne_delta))
    arousal_gain = 1.0 + (nm.ACC_K_NE * arousal_delta)
    arousal_gain = max(nm.ACC_GAIN_MIN, min(nm.ACC_GAIN_MAX, arousal_gain))

    cort_delta = cortisol_v - nm.BASELINE_CORT
    stress_drive = max(0.0, cort_delta / (1.0 + abs(cort_delta)))
    stress_gain = 1.0 + (nm.ACC_K_CORT * stress_drive)
    stress_gain = max(nm.ACC_GAIN_MIN, min(nm.ACC_GAIN_MAX, stress_gain))

    inhibition_gain = 1.0 - (nm.ACC_K_HT_INHIBITION * max(0.0, serotonin_v - nm.BASELINE_HT))
    inhibition_gain = max(nm.ACC_INHIBITION_MIN, min(1.0, inhibition_gain))

    modulated = conflict_v * arousal_gain * stress_gain * inhibition_gain
    normalized = modulated / (1.0 + (nm.ACC_SOFT_NORM * modulated))
    return max(0.0, min(1.0, normalized))


@pytest.mark.parametrize(
    "conflict, norepinephrine, cortisol, serotonin",
    [
        (0.5, 0.1, 0.0, 0.1),
        (0.5, 0.6, 0.0, 0.1),
        (0.5, 0.1, 0.5, 0.1),
        (0.5, 0.6, 0.5, 0.2),
        (1.0, 1.0, 1.0, 0.0),
        (0.0, 0.6, 1.0, 0.5),
    ],
)
def test_compute_effective_conflict_matches_manual_formula(
    conflict: float,
    norepinephrine: float,
    cortisol: float,
    serotonin: float,
) -> None:
    nm = NeuromodulatorState(
        norepinephrine=norepinephrine,
        cortisol=cortisol,
        serotonin=serotonin,
    )
    expected = _manual_effective_conflict(nm, conflict, norepinephrine, cortisol, serotonin)
    assert nm._compute_effective_conflict(conflict) == pytest.approx(expected, abs=1e-9)


def test_compute_effective_conflict_is_pure_function() -> None:
    nm = NeuromodulatorState(
        dopamine=0.3,
        norepinephrine=0.6,
        serotonin=0.2,
        cortisol=0.5,
        acetylcholine=0.4,
    )
    before_snapshot = nm.snapshot()
    before_trace = (
        nm._acc_combined_conflict_trace,
        nm._acc_cognitive_conflict_trace,
        nm._acc_affective_conflict_trace,
    )
    before_timestamp = nm.timestamp

    _ = nm._compute_effective_conflict(0.5)

    assert nm.snapshot() == before_snapshot
    assert (
        nm._acc_combined_conflict_trace,
        nm._acc_cognitive_conflict_trace,
        nm._acc_affective_conflict_trace,
    ) == before_trace
    assert nm.timestamp == before_timestamp


def test_baseline_conflict_mapping_remains_close_to_legacy() -> None:
    nm = NeuromodulatorState(
        norepinephrine=NeuromodulatorState.BASELINE_NE,
        cortisol=0.0,
        serotonin=NeuromodulatorState.BASELINE_HT,
    )
    for conflict in (0.0, 0.2, 0.5, 0.8, 1.0):
        effective = nm._compute_effective_conflict(conflict)
        assert effective == pytest.approx(conflict, abs=0.05)


def test_first_step_uses_same_smoothing_rule_without_fast_path_jump() -> None:
    nm = NeuromodulatorState(norepinephrine=0.6, cortisol=0.4, serotonin=0.1)
    target = nm._compute_effective_conflict(0.7)
    alpha = nm._compute_conflict_alpha(0.1)

    nm.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.7,
        cognitive_conflict=0.7,
        affective_conflict=0.7,
        use_reward_for_dopamine=False,
        dt=0.1,
    )

    expected = alpha * target
    assert nm._acc_combined_conflict_trace == pytest.approx(expected, abs=1e-9)
    assert nm._acc_cognitive_conflict_trace == pytest.approx(expected, abs=1e-9)
    assert nm._acc_affective_conflict_trace == pytest.approx(expected, abs=1e-9)


def test_update_from_signals_applies_dt_low_pass_after_seed() -> None:
    nm = NeuromodulatorState()
    nm._acc_combined_conflict_trace = 0.1
    nm._acc_cognitive_conflict_trace = 0.2
    nm._acc_affective_conflict_trace = 0.3

    target_combined = nm._compute_effective_conflict(0.8)
    target_cognitive = nm._compute_effective_conflict(0.8)
    target_affective = nm._compute_effective_conflict(0.8)
    alpha = nm._compute_conflict_alpha(0.5)
    expected_combined = 0.1 + (alpha * (target_combined - 0.1))
    expected_cognitive = 0.2 + (alpha * (target_cognitive - 0.2))
    expected_affective = 0.3 + (alpha * (target_affective - 0.3))

    nm.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.8,
        use_reward_for_dopamine=False,
        dt=0.5,
    )

    assert nm._acc_combined_conflict_trace == pytest.approx(expected_combined, abs=1e-9)
    assert nm._acc_cognitive_conflict_trace == pytest.approx(expected_cognitive, abs=1e-9)
    assert nm._acc_affective_conflict_trace == pytest.approx(expected_affective, abs=1e-9)


def test_split_conflict_none_semantics_are_symmetric() -> None:
    nm = NeuromodulatorState()

    combined_1, cognitive_1, affective_1 = nm._split_conflict_components(
        conflict=0.0,
        cognitive_conflict=0.8,
        affective_conflict=None,
    )
    combined_2, cognitive_2, affective_2 = nm._split_conflict_components(
        conflict=0.0,
        cognitive_conflict=None,
        affective_conflict=0.8,
    )

    assert cognitive_1 == pytest.approx(0.8)
    assert affective_1 == pytest.approx(0.8)
    assert combined_1 == pytest.approx(0.8)
    assert cognitive_2 == pytest.approx(0.8)
    assert affective_2 == pytest.approx(0.8)
    assert combined_2 == pytest.approx(0.8)


def test_larger_dt_produces_stronger_conflict_response_after_seed() -> None:
    base = NeuromodulatorState()
    base.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.3,
        use_reward_for_dopamine=False,
        dt=1.0,
    )

    nm_small_dt = NeuromodulatorState.from_dict(base.to_dict())
    nm_large_dt = NeuromodulatorState.from_dict(base.to_dict())

    nm_small_dt.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.8,
        use_reward_for_dopamine=False,
        dt=0.1,
    )
    nm_large_dt.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.8,
        use_reward_for_dopamine=False,
        dt=2.0,
    )

    assert nm_large_dt.norepinephrine > nm_small_dt.norepinephrine
    assert nm_large_dt.cortisol > nm_small_dt.cortisol


def test_conflict_channel_split_separates_ne_and_cortisol_drives() -> None:
    nm_cognitive = NeuromodulatorState()
    nm_affective = NeuromodulatorState()

    nm_cognitive.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.0,
        cognitive_conflict=1.0,
        affective_conflict=0.0,
        use_reward_for_dopamine=False,
        dt=2.0,
    )
    nm_affective.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.0,
        cognitive_conflict=0.0,
        affective_conflict=1.0,
        use_reward_for_dopamine=False,
        dt=2.0,
    )

    cognitive_ne_delta = nm_cognitive.norepinephrine - NeuromodulatorState.BASELINE_NE
    cognitive_cort_delta = nm_cognitive.cortisol - NeuromodulatorState.BASELINE_CORT
    affective_ne_delta = nm_affective.norepinephrine - NeuromodulatorState.BASELINE_NE
    affective_cort_delta = nm_affective.cortisol - NeuromodulatorState.BASELINE_CORT

    assert cognitive_ne_delta > affective_ne_delta
    assert affective_cort_delta > cognitive_cort_delta


def test_acc_conflict_long_run_remains_bounded_without_external_decay() -> None:
    nm = NeuromodulatorState()
    for _ in range(1000):
        nm.update_from_signals(
            reward=0.0,
            novelty=0.0,
            conflict=0.6,
            stable_repetition=False,
            use_reward_for_dopamine=False,
            dt=1.0,
        )

    assert nm.norepinephrine < 0.95
    assert nm.cortisol < 0.95


def test_acc_stress_dynamics_growth_then_stabilization() -> None:
    nm = NeuromodulatorState()
    cortisol_history = []

    for _ in range(10):
        nm.update_from_signals(
            reward=0.0,
            novelty=0.0,
            conflict=0.8,
            stable_repetition=False,
            use_reward_for_dopamine=False,
            dt=1.0,
        )
        cortisol_history.append(nm.cortisol)

    deltas = [b - a for a, b in zip(cortisol_history[:-1], cortisol_history[1:])]
    assert all(delta > 0.0 for delta in deltas[:5])
    assert deltas[-1] < deltas[0]
    assert cortisol_history[-1] < 0.98
