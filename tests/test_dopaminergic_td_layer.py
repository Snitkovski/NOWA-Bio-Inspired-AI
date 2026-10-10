from conflict_arbitration import ConflictArbitrationLayer
from value_layer import DopaminergicTDLayer, ValueLayer


def _state(ctx: str):
    return {
        "context_signature": ctx,
        "context_size": 1,
        "action": "",
        "consequence": "",
        "intensity": 1.0,
        "novelty": 0.0,
        "conflict": 0.0,
    }


def test_positive_surprise_produces_positive_signed_burst():
    td = DopaminergicTDLayer(delta_max=2.0)
    profile = td.compute_td_error(reward=10.0, value_current=2.0, value_next=4.0, gamma=0.9)

    assert profile["delta"] > 0.0
    assert profile["phasic_burst"] > 0.0
    assert profile["delta_sign"] == 1
    assert profile["delta_clipped"] <= 2.0 + 1e-12


def test_negative_surprise_produces_negative_signed_dip():
    td = DopaminergicTDLayer(delta_max=2.0)
    profile = td.compute_td_error(reward=0.0, value_current=0.8, value_next=0.2, gamma=0.9)

    assert profile["delta"] < 0.0
    assert profile["phasic_burst"] < 0.0
    assert profile["delta_sign"] == -1


def test_zero_error_keeps_phasic_component_zero():
    td = DopaminergicTDLayer(delta_max=1.0)
    gamma = 0.95
    value = 0.3
    reward = (1.0 - gamma) * value
    profile = td.compute_td_error(reward=reward, value_current=value, value_next=value, gamma=gamma)

    assert abs(profile["delta"]) < 1e-9
    assert abs(profile["phasic_burst"]) < 1e-9
    assert profile["delta_sign"] == 0


def test_tonic_drift_is_slow_relative_to_phasic_spike():
    td = DopaminergicTDLayer(
        delta_max=1.0,
        tonic_baseline=0.1,
        tonic_level=0.1,
        tonic_slow_rate=0.01,
    )
    profile = td.compute_td_error(
        reward=1.0,
        value_current=0.0,
        value_next=0.0,
        gamma=0.0,
        cer_stress_level=0.0,
    )

    assert abs(profile["phasic_burst"] - 1.0) < 1e-12
    assert abs(profile["mean_phasic"] - 0.01) < 1e-12
    assert abs(profile["tonic_level"] - 0.1001) < 1e-12


def test_tonic_follows_running_mean_phasic_direction():
    td = DopaminergicTDLayer(
        delta_max=1.0,
        tonic_baseline=0.1,
        tonic_level=0.1,
        tonic_slow_rate=0.01,
    )
    for _ in range(120):
        td.compute_td_error(
            reward=1.0,
            value_current=0.0,
            value_next=0.0,
            gamma=0.0,
            cer_stress_level=0.0,
        )
    tonic_after_positive = float(td.tonic_level)
    mean_after_positive = float(td.phasic_mean)

    for _ in range(120):
        td.compute_td_error(
            reward=-1.0,
            value_current=0.0,
            value_next=0.0,
            gamma=0.0,
            cer_stress_level=0.0,
        )

    assert float(td.phasic_mean) < mean_after_positive
    assert float(td.tonic_level) < tonic_after_positive


def test_large_error_is_clipped_but_raw_delta_is_preserved():
    td = DopaminergicTDLayer(delta_max=0.5)
    profile = td.compute_td_error(reward=8.0, value_current=0.0, value_next=0.0, gamma=0.95)

    assert profile["delta"] == 8.0
    assert profile["delta_clipped"] == 0.5
    assert profile["abs_delta"] == 0.5


def test_repeated_negative_streak_populates_acc_error_history():
    td = DopaminergicTDLayer(delta_max=1.0)
    acc = ConflictArbitrationLayer(error_window_size=6, failure_window_size=6)

    for _ in range(6):
        profile = td.compute_td_error(reward=-1.0, value_current=0.0, value_next=0.0, gamma=0.95)
        acc.register_outcome(reward_signal=-0.5, prediction_error=profile["phasic_burst"])

    assert len(acc.error_history_window) == 6
    assert all(v >= 0.0 for v in acc.error_history_window)
    assert sum(acc.error_history_window) / len(acc.error_history_window) >= 0.9


def test_cer_stress_reduces_effective_learning_rate_without_changing_td_sign():
    layer = ValueLayer(alpha_online_default=0.1, max_update_l2=1.0)
    st = _state("s0")
    st_next = _state("s1")

    low_stress = layer.update(
        st,
        reward=0.8,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=None,
        mode="online",
        cer_stress_level=0.0,
        timestamp=1.0,
    )
    layer.values[layer.encoder.encode(st)] = 0.0
    high_stress = layer.update(
        st,
        reward=0.8,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=None,
        mode="online",
        cer_stress_level=1.0,
        timestamp=2.0,
    )

    assert high_stress["alpha_effective"] < low_stress["alpha_effective"]
    assert high_stress["delta_sign"] == low_stress["delta_sign"]
    assert high_stress["delta_sign"] == 1


def test_cer_stress_amplifies_negative_phasic_dip():
    td = DopaminergicTDLayer(delta_max=1.0, stress_dip_gain=0.5)
    low = td.compute_td_error(
        reward=-0.2,
        value_current=0.2,
        value_next=0.0,
        gamma=0.0,
        cer_stress_level=0.0,
    )
    high = td.compute_td_error(
        reward=-0.2,
        value_current=0.2,
        value_next=0.0,
        gamma=0.0,
        cer_stress_level=1.0,
    )

    assert low["delta"] == high["delta"]
    assert high["delta_modulated"] < low["delta_modulated"]
    assert high["phasic_burst"] < low["phasic_burst"]


def test_reward_scale_allows_extreme_rewards_without_mandatory_clamp():
    layer = ValueLayer(reward_scale=0.1, td_clip_online=1.0, max_update_l2=1.0)
    st = _state("s0")
    st_next = _state("s1")

    out = layer.update(
        st,
        reward=20.0,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=1.0,
        timestamp=10.0,
        mode="online",
    )

    assert out["reward_raw"] == 20.0
    assert out["reward_scaled"] == 2.0
    assert out["delta"] == 2.0
    assert out["delta_clipped"] == 1.0


def test_clip_frequency_logging_tracks_saturation_events():
    layer = ValueLayer(
        td_clip_online=0.1,
        adaptive_td_clip_enabled=False,
        max_update_l2=1.0,
    )
    st = _state("s0")
    st_next = _state("s1")

    for step in range(6):
        layer.update(
            st,
            reward=5.0,
            next_state_snapshot=st_next,
            gamma=0.0,
            alpha=1.0,
            timestamp=float(step + 1),
        )

    snapshot = layer.snapshot()
    assert int(snapshot["online_td_clip_updates"]) == 6
    assert int(snapshot["online_td_clip_count"]) >= 5
    assert float(snapshot["online_td_clip_frequency"]) > 0.8
    assert float(snapshot["online_td_clip_frequency_ema"]) > 0.2


def test_adaptive_td_clip_increases_when_saturation_is_persistent():
    layer = ValueLayer(
        td_clip_online=0.1,
        td_clip_min_online=0.05,
        td_clip_max_online=0.5,
        adaptive_td_clip_enabled=True,
        td_clip_target_rate=0.2,
        td_clip_adapt_rate=0.2,
        td_clip_ema_beta=0.2,
        max_update_l2=1.0,
    )
    st = _state("s0")
    st_next = _state("s1")

    initial_clip = float(layer.td_clip_online)
    for step in range(20):
        layer.update(
            st,
            reward=5.0,
            next_state_snapshot=st_next,
            gamma=0.0,
            alpha=1.0,
            timestamp=float(step + 1),
        )

    assert float(layer.td_clip_online) > initial_clip
    assert float(layer.td_clip_online) <= 0.5 + 1e-12


def test_exploration_coupling_is_signed_and_capped_to_20_percent():
    td = DopaminergicTDLayer(exploration_coupling_fraction=0.2)
    baseline = 0.6

    pos_delta = td.compute_exploration_delta(delta_sign=1, baseline_exploration=baseline)
    neg_delta = td.compute_exploration_delta(delta_sign=-1, baseline_exploration=baseline)
    zero_delta = td.compute_exploration_delta(delta_sign=0, baseline_exploration=baseline)

    assert abs(pos_delta + 0.12) < 1e-12
    assert abs(neg_delta - 0.12) < 1e-12
    assert zero_delta == 0.0


def test_exploration_coupling_can_unfreeze_zero_baseline():
    td = DopaminergicTDLayer(exploration_coupling_fraction=0.2, exploration_unfreeze_floor=0.02)

    pos_delta = td.compute_exploration_delta(delta_sign=1, baseline_exploration=0.0)
    neg_delta = td.compute_exploration_delta(delta_sign=-1, baseline_exploration=0.0)

    assert abs(pos_delta + 0.02) < 1e-12
    assert abs(neg_delta - 0.02) < 1e-12
