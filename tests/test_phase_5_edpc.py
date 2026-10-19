
import pytest
from learning_guard import learning_allowed

@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct tests of stable writers. Sleep opens the same guard."""
    with learning_allowed():
        yield

import random
from types import SimpleNamespace

import pytest

from agent import Agent
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager
from value_layer import ValueLayer


def _state(name: str, action: str = "act"):
    return {
        "context_signature": name,
        "context_size": 1,
        "action": action,
        "consequence": "",
        "intensity": 1.0,
        "novelty": 0.0,
        "conflict": 0.0,
    }


def _run_rewards(layer: ValueLayer, rewards, state_name: str = "ctx") -> list:
    current = _state(state_name)
    nxt = _state(f"{state_name}:next")
    outputs = []
    for idx, reward in enumerate(list(rewards), start=1):
        outputs.append(
            layer.update(
                current,
                reward=float(reward),
                next_state_snapshot=nxt,
                gamma=0.0,
                alpha=0.1,
                timestamp=float(idx),
                mode="online",
            )
        )
    return outputs


def _build_agent() -> Agent:
    hip = NOWAHippocampus(max_experiences=2000)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=["act"])
    agent = Agent(hip, cortex, selector, sleep, intent)
    agent.register_action_channel("act", go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)
    sleep._rng.seed(0)
    return agent


def test_edpc_stable_stream_increases_confidence_and_damps_alpha():
    layer = ValueLayer(
        alpha_online_default=0.1,
        td_clip_online=10.0,
        max_update_l2=1.0,
        confirmation_threshold=0.12,
    )
    outputs = _run_rewards(layer, [1.0] * 120, state_name="stable")
    last = outputs[-1]

    assert last["confidence_score"] > 0.85
    assert last["stability_score"] > 0.60
    assert last["alpha_effective"] < 0.1
    assert last["prediction_shock"] is False


def test_edpc_noisy_stream_has_lower_confidence_than_stable():
    stable_layer = ValueLayer(alpha_online_default=0.1, td_clip_online=10.0, max_update_l2=1.0)
    stable_last = _run_rewards(stable_layer, [1.0] * 120, state_name="stable")[-1]

    rng = random.Random(42)
    noisy_rewards = [1.0 + rng.uniform(-0.8, 0.8) for _ in range(120)]
    noisy_layer = ValueLayer(alpha_online_default=0.1, td_clip_online=10.0, max_update_l2=1.0)
    noisy_last = _run_rewards(noisy_layer, noisy_rewards, state_name="noisy")[-1]

    assert abs(float(noisy_last["expected_reward_mean"]) - 1.0) < 0.35
    assert float(noisy_last["expected_reward_var"]) > 0.02
    assert float(noisy_last["confidence_score"]) < float(stable_last["confidence_score"])
    assert float(noisy_last["stability_score"]) < float(stable_last["stability_score"])


def test_edpc_structural_shift_triggers_prediction_shock():
    layer = ValueLayer(
        alpha_online_default=0.08,
        td_clip_online=10.0,
        max_update_l2=2.0,
        shock_delta_threshold=0.5,
    )
    _run_rewards(layer, [1.0] * 100, state_name="shift")
    before = layer.update(
        _state("shift"),
        reward=1.0,
        next_state_snapshot=_state("shift:next"),
        gamma=0.0,
        alpha=0.08,
        timestamp=101.0,
        mode="online",
    )
    after = layer.update(
        _state("shift"),
        reward=5.0,
        next_state_snapshot=_state("shift:next"),
        gamma=0.0,
        alpha=0.08,
        timestamp=102.0,
        mode="online",
    )

    assert before["confidence_score"] > 0.7
    assert after["prediction_shock"] is True
    assert after["alpha_effective"] > before["alpha_effective"]
    assert layer.snapshot()["shock_count_total"] >= 1


def test_edpc_replay_priority_formula_uses_shock_and_stability():
    sleep = SleepManager(NOWAHippocampus(), CortexMemory(), IntentMemory())
    sleep.ach_replay_gain = 0.0

    exp = SimpleNamespace(
        td_error_snapshot=0.5,
        replay_salience=0.0,
        replay_importance=0.0,
        expectation_stability_score=0.2,
        prediction_shock_flag=False,
        replay_priority=0.0,
        acetylcholine_snapshot=0.1,
    )
    base = sleep._compute_replay_priority(exp, value_variance=0.0)
    exp.prediction_shock_flag = True
    shocked = sleep._compute_replay_priority(exp, value_variance=0.0)
    exp.prediction_shock_flag = False
    exp.expectation_stability_score = 0.8
    high_stability = sleep._compute_replay_priority(exp, value_variance=0.0)

    assert base == pytest.approx(0.5 * (1.0 - 0.2))
    assert shocked > base
    assert high_stability < base


def test_edpc_metrics_exposed_in_value_and_sleep_state():
    agent = _build_agent()
    agent.sleep_manager.td_threshold = 0.0
    agent.sleep_manager.salience_threshold = 0.0
    agent.sleep_manager.min_reinforcement_for_consolidation = 1

    for _ in range(40):
        agent.step(
            context_events=["ctx:edpc"],
            reward=1.0,
            novelty=0.0,
            conflict=0.0,
            intensity=1.0,
        )
    agent.step(
        context_events=["ctx:edpc"],
        reward=5.0,
        novelty=0.0,
        conflict=0.0,
        intensity=1.0,
    )

    state_before_sleep = agent.get_state()
    value_state = dict(state_before_sleep.get("value_layer", {}) or {})
    assert "confidence_distribution" in value_state
    assert "stability_distribution" in value_state
    assert "shock_frequency" in value_state
    assert isinstance(value_state.get("effective_alpha_trajectory"), list)

    sleep_stats = agent.sleep(cycles=1)
    state_after_sleep = agent.get_state()
    replay_state = dict(state_after_sleep.get("sleep_replay", {}) or {})

    assert "replay_diversity_index" in replay_state
    assert "shock_frequency" in replay_state
    assert "replay_confidence_mean" in replay_state
    assert "mean_replay_diversity_index" in sleep_stats
