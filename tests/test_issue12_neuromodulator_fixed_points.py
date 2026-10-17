"""Regression for issue #12: neuromodulator fixed points stay near baseline."""

import pytest

from agent import Agent
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from neuromodulators import NeuromodulatorField, NeuromodulatorState
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _agent():
    hip = NOWAHippocampus(max_experiences=80)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=["act"])
    agent = Agent(hip, cortex, selector, sleep, intent, rng_seed=0)
    agent.register_action_channel("act", go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)
    sleep._rng.seed(0)
    return agent


def test_unforced_field_contracts_toward_baseline():
    field = NeuromodulatorField(
        dopamine=0.85,
        serotonin=0.85,
        norepinephrine=0.85,
        acetylcholine=0.85,
    )
    for _ in range(40):
        field.update(signals={})
    for key in NeuromodulatorField.KEYS:
        assert abs(field.levels[key] - field.baselines[key]) < 0.05


def test_sustained_reward_does_not_silence_dopamine():
    nm = NeuromodulatorState()
    for _ in range(40):
        nm.update_from_signals(
            reward=1.0,
            novelty=0.0,
            conflict=0.0,
            stable_repetition=False,
            use_reward_for_dopamine=False,
        )
    assert nm.dopamine > 0.05
    assert abs(nm.dopamine - NeuromodulatorState.BASELINE_DA) < 0.05


def test_stable_repetition_keeps_acetylcholine_at_baseline():
    nm = NeuromodulatorState()
    for _ in range(40):
        nm.update_from_signals(
            reward=0.0,
            novelty=0.0,
            conflict=0.0,
            stable_repetition=True,
            use_reward_for_dopamine=False,
        )
    assert nm.acetylcholine >= nm.ach_baseline - 1e-6
    assert abs(nm.acetylcholine - nm.ach_baseline) < 0.05


def test_ach_gate_follows_running_mean_after_a_novelty_spike():
    nm = NeuromodulatorState()
    for _ in range(20):
        nm.update_from_signals(
            reward=0.0,
            novelty=0.0,
            conflict=0.0,
            stable_repetition=True,
            use_reward_for_dopamine=False,
        )
    nm.update_from_signals(
        reward=0.0,
        novelty=1.0,
        conflict=0.0,
        stable_repetition=False,
        use_reward_for_dopamine=False,
    )
    assert nm.acetylcholine_gate() > 0.0


def test_dopamine_writer_is_a_bounded_impulse():
    nm = NeuromodulatorState()
    nm.apply_dopamine_delta(5.0)
    assert nm.dopamine <= NeuromodulatorState.BASELINE_DA + 0.25 + 1e-9
    assert nm.dopamine < 1.0


def test_agent_reward_steps_keep_dopamine_near_baseline():
    agent = _agent()
    for step in range(30):
        agent.step(
            ["ctx_reward"],
            reward=1.0,
            novelty=0.0,
            conflict=0.0,
            intensity=1.0,
        )
    dopamine = float(agent.neuromodulators.dopamine)
    # Each rewarded step still adds a bounded TD impulse, so DA sits above
    # baseline. The old attractor was ~0.36 and the signal-only path sat at 0.
    assert dopamine > 0.05
    assert dopamine < 0.5
    assert abs(dopamine - NeuromodulatorState.BASELINE_DA) < 0.15


def test_old_neuromodulator_save_without_running_mean_loads():
    nm = NeuromodulatorState(dopamine=0.2, serotonin=0.2, norepinephrine=0.2, acetylcholine=0.2)
    payload = nm.to_dict()
    payload.pop("ach_running_mean", None)
    restored = NeuromodulatorState.from_dict(payload)
    assert restored.dopamine == pytest.approx(nm.dopamine)
    assert restored.ach_running_mean == pytest.approx(restored.ach_baseline)
