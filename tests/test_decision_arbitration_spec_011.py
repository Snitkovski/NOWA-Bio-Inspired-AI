import math

from decision_arbitrator import DecisionArbitrator
from value_layer import ValueLayer


def _approx(value: float, target: float, tol: float = 0.05) -> bool:
    return abs(float(value) - float(target)) <= tol


def test_low_uncertainty_habitual_mode():
    arbitrator = DecisionArbitrator()
    action_metadata = {"A": {"td_variance": 0.05}}
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata=action_metadata,
        error_likelihood=0.1,
        surprise=0.05,
        stress_level=0.0,
        action_stability_mean=0.8,
        causality_mean=0.8,
    )
    assert output["global_uncertainty"] < 0.3
    assert output["decision_mode"] == "HABITUAL"
    assert _approx(output["policy_temperature"], 0.67, tol=0.07)


def test_high_td_variance_deliberative():
    arbitrator = DecisionArbitrator()
    action_metadata = {"A": {"td_variance": 0.8}}
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata=action_metadata,
        error_likelihood=0.2,
        surprise=0.1,
        stress_level=0.0,
        action_stability_mean=0.9,
        causality_mean=0.9,
    )
    assert output["decision_mode"] == "DELIBERATIVE"
    assert output["policy_temperature"] > 1.0


def test_stress_driven_deliberation():
    arbitrator = DecisionArbitrator()
    action_metadata = {"A": {"td_variance": 0.3125}}
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata=action_metadata,
        error_likelihood=0.5,
        surprise=0.1,
        stress_level=0.8,
        action_stability_mean=0.9,
        causality_mean=0.9,
    )
    assert math.isclose(output["effective_threshold"], 0.35, abs_tol=1e-6)
    assert output["decision_mode"] == "DELIBERATIVE"


def test_state_similarity_top_k():
    layer = ValueLayer()
    layer.expectation_memory.clear()
    layer.expectation_memory["s1"] = {
        "expected_reward_mean": 1.0,
        "state_vector": [1.0, 0.0, 0.0],
    }
    layer.expectation_memory["s2"] = {
        "expected_reward_mean": 0.5,
        "state_vector": [0.92, 0.08, 0.0],
    }
    layer.expectation_memory["s3"] = {
        "expected_reward_mean": -1.0,
        "state_vector": [0.0, 1.0, 0.0],
    }

    profile = layer._get_expectation_profile(
        "missing",
        state_snapshot={"state_vector": [1.0, 0.0, 0.0]},
    )
    assert layer.last_similar_state_count == 2
    assert profile["expected_reward_mean"] > 0.7


def test_temperature_bounds():
    arbitrator = DecisionArbitrator()
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata={"A": {"td_variance": 1.0}},
        error_likelihood=1.0,
        surprise=1.0,
        stress_level=0.0,
        action_stability_mean=1.0,
        causality_mean=1.0,
    )
    assert 0.4 <= output["policy_temperature"] <= 1.5


def test_no_sac_metadata_defaults():
    arbitrator = DecisionArbitrator()
    output = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata=None,
        error_likelihood=0.2,
        surprise=0.1,
        stress_level=0.0,
        action_stability_mean=0.8,
        causality_mean=0.8,
    )
    assert output["global_uncertainty"] > 0.0


def test_uncertainty_hysteresis_prevents_mode_flapping():
    arbitrator = DecisionArbitrator(hysteresis_margin=0.05, uncertainty_ema_beta=1.0)
    high = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata={"A": {"td_variance": 0.8}},
        error_likelihood=0.2,
        surprise=0.1,
        stress_level=0.0,
        action_stability_mean=1.0,
        causality_mean=1.0,
    )
    mid = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata={"A": {"td_variance": 0.56}},
        error_likelihood=0.2,
        surprise=0.1,
        stress_level=0.0,
        action_stability_mean=1.0,
        causality_mean=1.0,
    )
    low = arbitrator.arbitrate(
        pressure_vector={"A": 1.0},
        action_metadata={"A": {"td_variance": 0.10}},
        error_likelihood=0.05,
        surprise=0.0,
        stress_level=0.0,
        action_stability_mean=1.0,
        causality_mean=1.0,
    )
    assert high["decision_mode"] == "DELIBERATIVE"
    assert mid["decision_mode"] == "DELIBERATIVE"
    assert low["decision_mode"] == "HABITUAL"


def test_similarity_generalization_confidence_is_conservative():
    layer = ValueLayer()
    layer.expectation_memory.clear()
    layer.expectation_memory["s1"] = {
        "expected_reward_mean": 1.0,
        "confidence_score": 0.9,
        "stability_score": 0.9,
        "confirmation_count": 25.0,
        "state_vector": [1.0, 0.0, 0.0],
    }
    layer.expectation_memory["s2"] = {
        "expected_reward_mean": 0.8,
        "confidence_score": 0.9,
        "stability_score": 0.85,
        "confirmation_count": 20.0,
        "state_vector": [0.95, 0.05, 0.0],
    }
    layer._rebuild_similarity_index()
    profile = layer._get_expectation_profile(
        "new_state",
        state_snapshot={"state_vector": [1.0, 0.0, 0.0]},
    )
    assert profile["confirmation_count"] == 0.0
    assert profile["confidence_score"] < 0.6
    assert profile["stability_score"] < 0.6


def test_similarity_scan_is_bounded_by_index_candidates():
    layer = ValueLayer(similarity_max_scan=5000, similarity_index_max_candidates=64, similarity_bucket_bits=8)
    layer.expectation_memory.clear()
    for idx in range(600):
        layer.expectation_memory[f"s{idx}"] = {
            "expected_reward_mean": 0.1,
            "confidence_score": 0.3,
            "stability_score": 0.2,
            "state_vector": [1.0, 0.1, 0.0],
        }
    layer._rebuild_similarity_index()
    _ = layer._get_expectation_profile(
        "missing_state",
        state_snapshot={"state_vector": [1.0, 0.1, 0.0]},
    )
    assert 0 < layer.last_similarity_scan_count <= 64


def test_similarity_transfer_uses_quantile_not_minimum():
    layer = ValueLayer(similarity_transfer_quantile=0.5)
    layer.expectation_memory.clear()
    layer.expectation_memory["a"] = {
        "expected_reward_mean": 0.5,
        "confidence_score": 0.1,
        "stability_score": 0.1,
        "state_vector": [1.0, 0.0, 0.0],
    }
    layer.expectation_memory["b"] = {
        "expected_reward_mean": 0.5,
        "confidence_score": 0.9,
        "stability_score": 0.9,
        "state_vector": [0.98, 0.02, 0.0],
    }
    layer.expectation_memory["c"] = {
        "expected_reward_mean": 0.5,
        "confidence_score": 0.9,
        "stability_score": 0.9,
        "state_vector": [0.99, 0.01, 0.0],
    }
    layer._rebuild_similarity_index()
    profile = layer._get_expectation_profile(
        "new_state",
        state_snapshot={"state_vector": [1.0, 0.0, 0.0]},
    )
    assert profile["confidence_score"] > 0.25
    assert profile["stability_score"] > 0.25
