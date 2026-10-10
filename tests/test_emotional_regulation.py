from emotional_regulation import EmotionalRegulationLayer


def _run_steps(layer: EmotionalRegulationLayer, steps: int, **signals):
    snapshots = []
    for _ in range(int(steps)):
        snapshots.append(layer.update(**signals))
    return snapshots


def test_cer_tc1_sustained_positive_reward():
    layer = EmotionalRegulationLayer()
    result = _run_steps(
        layer,
        80,
        reward_signal=0.8,
        prediction_error=0.02,
        novelty_score=0.0,
        policy_entropy=0.1,
        resolution_success=0.7,
    )[-1]

    factors = result["modulation_factors"]
    assert result["valence"] > 0.6
    assert 0.0 <= result["arousal"] <= 0.6
    assert factors["decision_threshold_shift"] < 0.0
    assert 1.0 <= factors["learning_rate_scale"] <= 1.3
    assert factors["exploration_bias"] < 0.25


def test_cer_tc2_chronic_failure_triggers_recovery_mode():
    layer = EmotionalRegulationLayer()
    history = _run_steps(
        layer,
        140,
        reward_signal=-0.6,
        prediction_error=0.9,
        novelty_score=0.2,
        policy_entropy=0.85,
        resolution_success=0.0,
    )
    result = history[-1]

    factors = result["modulation_factors"]
    before_recovery_lr = history[30]["modulation_factors"]["learning_rate_scale"]
    assert result["valence"] < -0.5
    assert result["uncertainty_tension"] > 0.5
    assert factors["decision_threshold_shift"] > 0.0
    assert factors["exploration_bias"] > 0.2
    assert result["recovery_mode"] is True
    assert result["negative_valence_steps"] > 50
    assert factors["learning_rate_scale"] <= before_recovery_lr


def test_cer_tc3_high_novelty_burst_saturation_guard():
    layer = EmotionalRegulationLayer()
    first = _run_steps(
        layer,
        31,
        reward_signal=0.0,
        prediction_error=0.2,
        novelty_score=0.7,
        policy_entropy=0.2,
        resolution_success=0.0,
    )
    second = _run_steps(
        layer,
        10,
        reward_signal=0.0,
        prediction_error=0.2,
        novelty_score=0.7,
        policy_entropy=0.2,
        resolution_success=0.0,
    )
    pre_guard_arousal = first[-1]["arousal"]
    post_guard_arousal = second[4]["arousal"]
    result = second[-1]
    factors = result["modulation_factors"]

    assert pre_guard_arousal > 0.7
    assert factors["novelty_sensitivity_scale"] > 1.0
    assert factors["learning_rate_scale"] > 1.0
    assert result["saturation_guard_activations"] > 0
    assert post_guard_arousal < pre_guard_arousal


def test_cer_tc4_policy_entropy_spike_increases_caution():
    layer = EmotionalRegulationLayer()
    low_entropy = _run_steps(
        layer,
        20,
        reward_signal=0.0,
        prediction_error=0.1,
        novelty_score=0.2,
        policy_entropy=0.1,
        resolution_success=0.0,
    )[-1]
    high_entropy = _run_steps(
        layer,
        20,
        reward_signal=0.0,
        prediction_error=0.1,
        novelty_score=0.2,
        policy_entropy=0.95,
        resolution_success=0.0,
    )[-1]

    assert high_entropy["uncertainty_tension"] > low_entropy["uncertainty_tension"]
    assert (
        high_entropy["modulation_factors"]["decision_threshold_shift"]
        > low_entropy["modulation_factors"]["decision_threshold_shift"]
    )


def test_cer_tc5_resolution_success_reduces_uncertainty():
    layer = EmotionalRegulationLayer(valence=-0.4, arousal=0.7, uncertainty_tension=0.8)
    before = layer.snapshot()
    after = _run_steps(
        layer,
        20,
        reward_signal=0.4,
        prediction_error=0.1,
        novelty_score=0.1,
        policy_entropy=0.3,
        resolution_success=0.9,
    )[-1]

    assert after["uncertainty_tension"] < before["uncertainty_tension"]
    assert after["valence"] > before["valence"]
    assert after["arousal"] < before["arousal"]


def test_cer_tc6_oscillation_stability_and_no_large_jumps():
    layer = EmotionalRegulationLayer()
    history = []
    for idx in range(120):
        reward = 0.8 if idx % 2 == 0 else -0.8
        history.append(
            layer.update(
                reward_signal=reward,
                prediction_error=0.0,
                novelty_score=0.2,
                policy_entropy=0.2,
                resolution_success=0.2,
            )
        )

    valences = [entry["valence"] for entry in history]
    max_valence = max(abs(v) for v in valences)
    max_valence_jump = max(
        abs(history[idx]["valence"] - history[idx - 1]["valence"]) for idx in range(1, len(history))
    )
    max_arousal_jump = max(
        abs(history[idx]["arousal"] - history[idx - 1]["arousal"]) for idx in range(1, len(history))
    )
    max_uncertainty_jump = max(
        abs(history[idx]["uncertainty_tension"] - history[idx - 1]["uncertainty_tension"])
        for idx in range(1, len(history))
    )

    assert max_valence <= 0.7
    assert history[-1]["recovery_mode"] is False
    assert max_valence_jump <= 0.3 + 1e-9
    assert max_arousal_jump <= 0.3 + 1e-9
    assert max_uncertainty_jump <= 0.3 + 1e-9


def test_cer_valence_update_uses_saturating_nonlinearity():
    low_drive = EmotionalRegulationLayer()
    high_drive = EmotionalRegulationLayer()

    low_valence = low_drive.update(
        reward_signal=0.2,
        prediction_error=0.0,
        novelty_score=0.0,
        policy_entropy=0.0,
        resolution_success=0.0,
    )["valence"]
    high_valence = high_drive.update(
        reward_signal=0.8,
        prediction_error=0.0,
        novelty_score=0.0,
        policy_entropy=0.0,
        resolution_success=0.0,
    )["valence"]

    assert low_valence > 0.0
    assert high_valence > low_valence
    # With linear dynamics this ratio would be equal; CER should saturate high amplitudes.
    assert (high_valence / 0.8) < (low_valence / 0.2)


def test_cer_tc7_chronic_negative_bias_increases_habit_gain_scale():
    layer = EmotionalRegulationLayer()
    base_habit_scale = layer.snapshot()["modulation_factors"]["habit_gain_scale"]

    for _ in range(120):
        snapshot = layer.update(
            reward_signal=-0.6,
            prediction_error=0.8,
            novelty_score=0.2,
            policy_entropy=0.9,
            resolution_success=0.0,
        )

    factors = snapshot["modulation_factors"]
    assert snapshot["chronic_negative_valence"] > 0.4
    assert factors["habit_gain_scale"] > base_habit_scale
    assert factors["habit_gain_scale"] > 1.0
