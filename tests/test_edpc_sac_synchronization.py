import time
from types import SimpleNamespace

import pytest

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


def _build_sync_context():
    hip = NOWAHippocampus(max_experiences=200)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=["act"])
    value_layer = ValueLayer()
    sleep.selector = selector
    sleep.value_layer = value_layer
    return sleep, selector, value_layer


def _seed_expectation(value_layer: ValueLayer, state_key: str, *, confidence: float, stability: float, error: float, shock: float):
    profile = dict(value_layer.expectation_memory.get(state_key, {}))
    profile.update(
        {
            "confidence_score": float(confidence),
            "stability_score": float(stability),
            "error_likelihood": float(error),
            "prediction_shock": float(shock),
            "prediction_shock_flag": bool(shock >= 0.5),
        }
    )
    value_layer.expectation_memory[state_key] = profile


def _make_exp(
    state_key: str,
    *,
    action_id: str = "act",
    td_mean: float = 0.8,
    td_variance: float = 0.1,
    confidence: float = 0.7,
    stability: float = 0.6,
    shock: float = 0.0,
    replay_priority: float = 1.0,
):
    return SimpleNamespace(
        value_state_key=str(state_key),
        value_state_snapshot=_state("ctx", action_id),
        replay_action_id=str(action_id),
        td_mean_snapshot=float(td_mean),
        td_variance_snapshot=float(td_variance),
        expectation_confidence_score=float(confidence),
        expectation_stability_score=float(stability),
        prediction_shock_score=float(shock),
        prediction_shock_flag=bool(shock >= 0.5),
        replay_priority=float(replay_priority),
        timestamp=time.time() - 10.0,
    )


def _prepare_state(value_layer: ValueLayer, state_name: str = "ctx"):
    current = _state(state_name)
    nxt = _state(f"{state_name}:next")
    out = value_layer.update(
        current,
        reward=0.0,
        next_state_snapshot=nxt,
        gamma=0.0,
        alpha=0.1,
        timestamp=1.0,
        mode="online",
    )
    return current, str(out["state_key"])


def test_sync_successful_action_increases_stability_and_lowers_error():
    sleep, selector, value_layer = _build_sync_context()
    _, state_key = _prepare_state(value_layer)
    _seed_expectation(value_layer, state_key, confidence=0.7, stability=0.4, error=0.5, shock=0.0)

    selector.set_action_metadata(
        "act",
        {
            "consolidated": True,
            "td_mean": 0.8,
            "td_variance": 0.1,
            "confidence": 0.6,
            "stability": 0.4,
        },
    )

    exp = _make_exp(state_key, td_mean=0.8, td_variance=0.1, confidence=0.7, stability=0.6, shock=0.0)
    before = dict(value_layer.expectation_memory[state_key])

    sleep._sync_edpc_sac([exp], sleep_phase="SWS", sleep_state=True, sleep_timestamp=time.time())
    after = dict(value_layer.expectation_memory[state_key])

    assert after["stability_score"] > before["stability_score"]
    assert after["error_likelihood"] < before["error_likelihood"]


def test_sync_unstable_td_keeps_stability_near_zero_delta():
    sleep, selector, value_layer = _build_sync_context()
    _, state_key = _prepare_state(value_layer, state_name="unstable")
    _seed_expectation(value_layer, state_key, confidence=0.7, stability=0.4, error=0.3, shock=0.0)

    selector.set_action_metadata(
        "act",
        {
            "consolidated": True,
            "td_mean": 0.7,
            "td_variance": 0.8,
            "confidence": 0.6,
            "stability": 0.4,
        },
    )

    exp = _make_exp(state_key, td_mean=0.7, td_variance=0.8, confidence=0.7, stability=0.5, shock=0.0)
    before = dict(value_layer.expectation_memory[state_key])

    sleep._sync_edpc_sac([exp], sleep_phase="SWS", sleep_state=True, sleep_timestamp=time.time())
    after = dict(value_layer.expectation_memory[state_key])

    assert (after["stability_score"] - before["stability_score"]) <= 0.01 + 1e-6


def test_sync_high_prediction_shock_reduces_confidence_and_blocks_stability_growth():
    sleep, selector, value_layer = _build_sync_context()
    _, state_key = _prepare_state(value_layer, state_name="shock")
    _seed_expectation(value_layer, state_key, confidence=0.8, stability=0.5, error=0.3, shock=0.2)

    selector.set_action_metadata(
        "act",
        {
            "consolidated": True,
            "td_mean": 0.6,
            "td_variance": 0.2,
            "confidence": 0.7,
            "stability": 0.5,
        },
    )

    exp = _make_exp(state_key, td_mean=0.6, td_variance=0.2, confidence=0.8, stability=0.6, shock=0.9)
    before = dict(value_layer.expectation_memory[state_key])
    before_meta = dict(selector.get_action_metadata("act"))

    sleep._sync_edpc_sac([exp], sleep_phase="REM", sleep_state=True, sleep_timestamp=time.time())
    after = dict(value_layer.expectation_memory[state_key])
    after_meta = dict(selector.get_action_metadata("act"))

    assert after_meta["confidence"] < before_meta["confidence"]
    assert after["error_likelihood"] > before["error_likelihood"]
    assert after["stability_score"] <= before["stability_score"]


def test_sync_conflict_blocks_update_and_sets_flag():
    sleep, selector, value_layer = _build_sync_context()
    _, state_key = _prepare_state(value_layer, state_name="conflict")
    _seed_expectation(value_layer, state_key, confidence=0.7, stability=0.2, error=0.4, shock=0.0)

    selector.set_action_metadata(
        "act",
        {
            "consolidated": True,
            "td_mean": 0.6,
            "td_variance": 0.2,
            "confidence": 0.7,
            "stability": 0.8,
        },
    )

    exp = _make_exp(state_key, td_mean=0.6, td_variance=0.2, confidence=0.7, stability=0.2, shock=0.0)
    before = dict(value_layer.expectation_memory[state_key])

    sleep._sync_edpc_sac([exp], sleep_phase="SWS", sleep_state=True, sleep_timestamp=time.time())
    after = dict(value_layer.expectation_memory[state_key])
    after_meta = dict(selector.get_action_metadata("act"))

    assert after_meta["conflict_flag"] is True
    assert after["stability_score"] == before["stability_score"]


def test_sync_stability_overflow_clamps_to_one():
    sleep, selector, value_layer = _build_sync_context()
    _, state_key = _prepare_state(value_layer, state_name="overflow")
    _seed_expectation(value_layer, state_key, confidence=0.8, stability=0.98, error=0.2, shock=0.0)

    selector.set_action_metadata(
        "act",
        {
            "consolidated": True,
            "td_mean": 1.0,
            "td_variance": 0.0,
            "confidence": 0.7,
            "stability": 0.9,
        },
    )

    exp = _make_exp(state_key, td_mean=1.0, td_variance=0.0, confidence=0.8, stability=0.9, shock=0.0)
    sleep._sync_edpc_sac([exp], sleep_phase="SWS", sleep_state=True, sleep_timestamp=time.time())
    after = dict(value_layer.expectation_memory[state_key])

    assert after["stability_score"] == pytest.approx(1.0)
