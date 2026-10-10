import os

import pytest

from agent import Agent
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from neuromodulators import NeuromodulatorState
from selector import ActionSelector
from sleep import CortexMemory, SleepManager
from value_layer import ValueLayer


def _build_agent(actions=("a",)):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(hip, cortex, selector, sleep, intent)
    sleep._rng.seed(0)
    return agent


def _run_long_horizon_metrics(
    n_steps: int,
    *,
    seed: int = 7,
    n_contexts: int = 40,
    sleep_every: int = 50,
    novelty_max: float = 0.75,
):
    import random
    from statistics import mean

    rnd = random.Random(seed)

    hip = NOWAHippocampus(max_experiences=max(6_000, n_steps + 500))
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=["a"])
    agent = Agent(hip, cortex, selector, sleep, intent)
    sleep._rng.seed(seed)

    ach_values = []
    ach_effective_values = []
    alpha_effective_values = []
    variance_ratios = []
    ach_above_baseline_values = []
    sleep_update_counts = []

    ach_baseline = float(agent.neuromodulators.ach_baseline)
    alpha_default = float(agent.value_layer.alpha_online_default)

    for step in range(1, n_steps + 1):
        ctx = [f"ctx_{rnd.randint(0, n_contexts - 1)}"]
        reward = max(-1.0, min(1.0, rnd.gauss(0.05, 0.35)))
        novelty = max(0.0, min(1.0, rnd.uniform(0.0, novelty_max)))
        conflict = max(0.0, min(1.0, rnd.uniform(0.0, 0.2)))
        agent.step(ctx, reward=reward, novelty=novelty, conflict=conflict, intensity=1.0)

        ach = float(agent.neuromodulators.acetylcholine)
        ach_values.append(ach)
        ach_effective_values.append(max(0.0, ach - ach_baseline))
        alpha_effective_values.append(float(agent.value_layer.snapshot().get("last_alpha_effective", 0.0)))

        if step % sleep_every == 0:
            stats = agent.sleep(cycles=1)
            variance_ratios.append(float(stats.get("value_variance_ratio", 0.0)))
            ach_above_baseline_values.append(float(stats.get("mean_ach_above_baseline", 0.0)))
            sleep_update_counts.append(int(stats.get("sleep_update_count", 0)))

    replay_budget = int(agent.sleep_manager.replay_budget_per_sleep)

    return {
        "n_steps": int(n_steps),
        "sleep_cycles": len(sleep_update_counts),
        "mean_ach": float(mean(ach_values)),
        "mean_ach_effective": float(mean(ach_effective_values)),
        "mean_alpha_effective": float(mean(alpha_effective_values)),
        "mean_value_variance_ratio": float(mean(variance_ratios)),
        "mean_ach_above_baseline": float(mean(ach_above_baseline_values)),
        "fraction_alpha_above_default": float(
            sum(1 for value in alpha_effective_values if value > (alpha_default + 1e-12))
            / max(1, len(alpha_effective_values))
        ),
        "fraction_variance_ratio_below_0_7": float(
            sum(1 for value in variance_ratios if value < 0.7) / max(1, len(variance_ratios))
        ),
        "max_sleep_update_count": int(max(sleep_update_counts) if sleep_update_counts else 0),
        "mean_sleep_update_count": float(mean(sleep_update_counts) if sleep_update_counts else 0.0),
        "replay_budget_per_sleep": replay_budget,
    }


def _state(
    ctx: str,
    action: str = "",
    consequence: str = "",
    intensity: float = 1.0,
    novelty: float = 0.0,
    conflict: float = 0.0,
):
    return {
        "context_signature": ctx,
        "context_size": len([item for item in ctx.split("|") if item]),
        "action": action,
        "consequence": consequence,
        "intensity": intensity,
        "novelty": novelty,
        "conflict": conflict,
    }


def test_novelty_spike_increases_ach_online_alpha_and_replay_priority():
    agent = _build_agent(actions=("approach",))
    ach_before = float(agent.neuromodulators.acetylcholine)

    agent.step(["ctx_ach"], reward=0.4, novelty=1.0, conflict=0.0, intensity=1.0)

    ach_after = float(agent.neuromodulators.acetylcholine)
    assert ach_after > ach_before

    value_snapshot = agent.value_layer.snapshot()
    assert float(value_snapshot.get("last_alpha_effective", 0.0)) > float(
        agent.value_layer.alpha_online_default
    )

    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 0.5
    exp.replay_salience = 0.5
    exp.replay_importance = 0.5
    exp.acetylcholine_snapshot = 1.0
    priority_high_ach = agent.sleep_manager._compute_replay_priority(exp)

    exp.acetylcholine_snapshot = 0.0
    priority_low_ach = agent.sleep_manager._compute_replay_priority(exp)
    assert priority_high_ach > priority_low_ach


def test_repetition_decreases_ach():
    nm = NeuromodulatorState(acetylcholine=0.6)
    before = float(nm.acetylcholine)
    nm.update_acetylcholine(novelty=0.1, stable_repetition=True)
    assert float(nm.acetylcholine) < before


def test_ach_novelty_filter_reduces_single_noisy_spike():
    nm = NeuromodulatorState(acetylcholine=0.1)
    nm.update_acetylcholine(novelty=0.6, stable_repetition=False)
    after_noisy_spike = float(nm.acetylcholine)
    assert after_noisy_spike <= 0.11

    nm.update_acetylcholine(novelty=1.0, stable_repetition=False)
    assert float(nm.acetylcholine) > after_noisy_spike


def test_saturation_protection_for_ach_and_online_alpha_cap():
    nm = NeuromodulatorState(acetylcholine=0.95)
    for _ in range(64):
        nm.update_acetylcholine(novelty=1.0, stable_repetition=False)
    assert 0.0 <= float(nm.acetylcholine) <= 1.0

    layer = ValueLayer(alpha_online_default=0.1, max_update_l2=1.0)
    st = _state("s0")
    st_next = _state("s1")

    alpha_seen = 0.0
    for step in range(1, 6):
        out = layer.update(
            st,
            reward=1.0,
            next_state_snapshot=st_next,
            gamma=0.0,
            alpha=0.1,
            timestamp=float(step),
            mode="online",
            acetylcholine=1.0,
        )
        alpha_seen = max(alpha_seen, float(out.get("alpha_effective", 0.0)))
    assert alpha_seen <= 0.15 + 1e-9


def test_decay_to_baseline_without_novelty():
    nm = NeuromodulatorState(acetylcholine=1.0)
    for _ in range(100):
        nm.update_acetylcholine(novelty=0.0, stable_repetition=False)
    assert abs(float(nm.acetylcholine) - float(nm.ach_baseline)) < 0.13


def test_ach_does_not_change_td_error_directly():
    st = _state("s0", action="act")
    st_next = _state("s1")

    layer_low = ValueLayer(max_update_l2=1.0, td_clip_online=1.0)
    out_low = layer_low.update(
        st,
        reward=0.7,
        next_state_snapshot=st_next,
        gamma=0.95,
        alpha=0.03,
        timestamp=1.0,
        mode="online",
        acetylcholine=0.0,
    )

    layer_high = ValueLayer(max_update_l2=1.0, td_clip_online=1.0)
    out_high = layer_high.update(
        st,
        reward=0.7,
        next_state_snapshot=st_next,
        gamma=0.95,
        alpha=0.03,
        timestamp=1.0,
        mode="online",
        acetylcholine=1.0,
    )

    assert out_low["td_error"] == pytest.approx(out_high["td_error"])


def test_online_alpha_has_no_systematic_bias_at_ach_baseline():
    layer = ValueLayer(max_update_l2=1.0)
    st = _state("s0")
    st_next = _state("s1")

    out = layer.update(
        st,
        reward=1.0,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=0.03,
        timestamp=1.0,
        mode="online",
        acetylcholine=0.1,
        acetylcholine_baseline=0.1,
    )
    assert float(out["alpha_effective"]) == pytest.approx(0.03)


def test_sleep_alpha_not_scaled_by_ach():
    layer = ValueLayer(alpha_online_default=0.01, alpha_sleep_default=0.08, max_update_l2=1.0)
    st = _state("s0")
    st_next = _state("s1")
    state_key = layer.encoder.encode(st)

    low_ach = layer.update(
        st,
        reward=1.0,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=None,
        timestamp=1.0,
        mode="sleep",
        acetylcholine=0.0,
    )
    layer.values[state_key] = 0.0

    high_ach = layer.update(
        st,
        reward=1.0,
        next_state_snapshot=st_next,
        gamma=0.0,
        alpha=None,
        timestamp=2.0,
        mode="sleep",
        acetylcholine=1.0,
    )

    assert float(low_ach["alpha_effective"]) == pytest.approx(float(high_ach["alpha_effective"]))
    assert float(low_ach["value"]) == pytest.approx(float(high_ach["value"]))


def test_replay_ach_gain_is_damped_when_value_variance_is_high():
    agent = _build_agent(actions=("variance",))
    sleep = agent.sleep_manager
    sleep.replay_priority_weights = (1.0, 0.0, 0.0)
    sleep.ach_replay_gain = 0.5
    sleep.instability_variance_threshold = 0.1

    _ = agent.step(["ctx_var"], reward=0.5, novelty=1.0, conflict=0.0, intensity=1.0)
    exp = agent.hippocampus.experiences[-1]
    exp.td_error_snapshot = 1.0
    exp.replay_salience = 0.0
    exp.replay_importance = 0.0
    exp.acetylcholine_snapshot = 1.0

    low_variance_priority = sleep._compute_replay_priority(exp, value_variance=0.0)
    high_variance_priority = sleep._compute_replay_priority(
        exp, value_variance=sleep.instability_variance_threshold
    )
    assert high_variance_priority < low_variance_priority


def test_encoding_strength_and_sleep_stats_expose_ach_metrics():
    agent = _build_agent(actions=("encode",))
    agent.step(["ctx_encode"], reward=0.2, novelty=1.0, conflict=0.0, intensity=1.2)

    exp = agent.hippocampus.experiences[-1]
    assert hasattr(exp, "encoding_strength")
    assert hasattr(exp, "acetylcholine_snapshot")
    assert float(exp.encoding_strength) > float(exp.intensity)
    assert float(exp.encoding_strength) == pytest.approx(
        float(exp.intensity) * (1.0 + (0.5 * float(exp.acetylcholine_snapshot)))
    )

    sleep_stats = agent.sleep(cycles=1)
    assert "mean_ach_during_cycle" in sleep_stats
    assert "mean_ach_above_baseline" in sleep_stats
    assert "value_variance_ratio" in sleep_stats
    assert 0.0 <= float(sleep_stats["mean_ach_during_cycle"]) <= 1.0

    state = agent.get_state()
    assert "acetylcholine" in state.get("neuromodulators", {})
    assert "mean_ach_during_cycle" in state.get("sleep_replay", {})
    assert "mean_ach_above_baseline" in state.get("sleep_replay", {})
    assert "value_variance_ratio" in state.get("sleep_replay", {})


@pytest.mark.parametrize("n_steps", [2000, 5000])
@pytest.mark.skipif(
    os.getenv("RUN_LONG_HORIZON_ACH", "0") != "1",
    reason="Long-horizon ACh stability test is disabled by default (set RUN_LONG_HORIZON_ACH=1).",
)
def test_long_horizon_ach_stability_metrics_normal_mode(n_steps):
    metrics = _run_long_horizon_metrics(n_steps=n_steps)
    print(f"[ACh long-run {n_steps}] {metrics}")

    assert 0.05 <= float(metrics["mean_ach_above_baseline"]) <= 0.15
    assert float(metrics["fraction_alpha_above_default"]) > 0.05
    assert float(metrics["fraction_variance_ratio_below_0_7"]) > 0.8
    assert int(metrics["max_sleep_update_count"]) <= int(metrics["replay_budget_per_sleep"])
    assert float(metrics["mean_sleep_update_count"]) <= float(metrics["replay_budget_per_sleep"]) * 0.8
