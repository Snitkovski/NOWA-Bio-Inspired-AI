import pytest

from cortex import CortexMemory
from learning_guard import learning_allowed


@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct ValueLayer.update tests. Sleep opens the same guard."""
    with learning_allowed():
        yield
from hippocampus import NOWAHippocampus
from selector import ActionSelector
from storage import AgentStorage
from value_layer import DopaminergicTDLayer, ValueLayer


def _state(name: str):
    return {
        "context_signature": name,
        "context_size": 1,
        "action": "",
        "consequence": "",
        "intensity": 1.0,
        "novelty": 0.0,
        "conflict": 0.0,
    }


def test_value_layer_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    source = ValueLayer(
        reward_scale=0.25,
        td_layer=DopaminergicTDLayer(
            stress_dip_gain=0.4,
            exploration_unfreeze_floor=0.03,
            tonic_slow_rate=0.015,
        ),
        adaptive_td_clip_enabled=True,
        td_clip_target_rate=0.3,
        td_clip_adapt_rate=0.07,
        td_clip_ema_beta=0.2,
        td_clip_min_online=0.05,
        td_clip_max_online=0.8,
    )
    source.update(_state("s0"), reward=0.4, next_state_snapshot=_state("s1"), timestamp=1.0)
    source.update(_state("s1"), reward=-0.2, next_state_snapshot=_state("s2"), timestamp=2.0)
    src_snapshot = source.snapshot()

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        value_layer=source,
        filename="value_layer.pkl",
    )

    restored = ValueLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        value_layer=restored,
    )

    dst_snapshot = restored.snapshot()
    assert int(dst_snapshot.get("state_count", 0)) == int(src_snapshot.get("state_count", 0))
    assert int(dst_snapshot.get("update_count", 0)) == int(src_snapshot.get("update_count", 0))
    assert int(dst_snapshot.get("online_update_count", 0)) == int(src_snapshot.get("online_update_count", 0))
    assert int(dst_snapshot.get("sleep_update_count", 0)) == int(src_snapshot.get("sleep_update_count", 0))
    assert int(dst_snapshot.get("expectation_memory_size", 0)) == int(src_snapshot.get("expectation_memory_size", 0))
    assert abs(float(dst_snapshot.get("value", 0.0)) - float(src_snapshot.get("value", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("last_td_error", 0.0)) - float(src_snapshot.get("last_td_error", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("last_confidence_score", 0.0)) - float(src_snapshot.get("last_confidence_score", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("last_stability_score", 0.0)) - float(src_snapshot.get("last_stability_score", 0.0))) < 1e-12
    assert int(dst_snapshot.get("last_delta_sign", 0)) == int(src_snapshot.get("last_delta_sign", 0))
    assert abs(float(dst_snapshot.get("last_abs_delta", 0.0)) - float(src_snapshot.get("last_abs_delta", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_tonic_level", 0.0)) - float(src_snapshot.get("td_tonic_level", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_tonic_slow_rate", 0.0)) - float(src_snapshot.get("td_tonic_slow_rate", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_phasic_mean", 0.0)) - float(src_snapshot.get("td_phasic_mean", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_tonic_target_base", 0.0)) - float(src_snapshot.get("td_tonic_target_base", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("reward_scale", 0.0)) - float(src_snapshot.get("reward_scale", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("stress_dip_gain", 0.0)) - float(src_snapshot.get("stress_dip_gain", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("exploration_unfreeze_floor", 0.0)) - float(src_snapshot.get("exploration_unfreeze_floor", 0.0))) < 1e-12
    assert bool(dst_snapshot.get("adaptive_td_clip_enabled", False)) == bool(src_snapshot.get("adaptive_td_clip_enabled", False))
    assert abs(float(dst_snapshot.get("td_clip_target_rate", 0.0)) - float(src_snapshot.get("td_clip_target_rate", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_clip_adapt_rate", 0.0)) - float(src_snapshot.get("td_clip_adapt_rate", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_clip_ema_beta", 0.0)) - float(src_snapshot.get("td_clip_ema_beta", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_clip_min_online", 0.0)) - float(src_snapshot.get("td_clip_min_online", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("td_clip_max_online", 0.0)) - float(src_snapshot.get("td_clip_max_online", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("last_reward_raw", 0.0)) - float(src_snapshot.get("last_reward_raw", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("last_reward_scaled", 0.0)) - float(src_snapshot.get("last_reward_scaled", 0.0))) < 1e-12
    assert abs(float(dst_snapshot.get("shock_frequency", 0.0)) - float(src_snapshot.get("shock_frequency", 0.0))) < 1e-12
    assert restored.last_state_key == source.last_state_key
    assert dict(restored.values) == dict(source.values)
    assert len(restored.alpha_effective_trajectory) == len(source.alpha_effective_trajectory)
