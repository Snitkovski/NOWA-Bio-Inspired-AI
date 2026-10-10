"""Specification-focused tests for Hippocampus 2.0."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from experience import Event, EventType, Path
from hippocampus import NOWAHippocampus


def _build_path(*tokens: str) -> Path:
    path = Path()
    for token in tokens:
        evt_type = EventType.ACTION if str(token).startswith("action:") else EventType.CONTEXT
        path = path.add_event(Event(str(token), evt_type))
    return path


def test_spec_store_builds_signature_with_sparsification_and_context():
    hip = NOWAHippocampus(max_features=3, cycle_length=12)

    path = _build_path(
        "ctx:forest",
        "ctx:rain",
        "ctx:cold",
        "ctx:wind",
        "action:shelter",
    )
    hip.store(path, intensity=1.2, reward=0.5)

    assert len(hip.signatures) == 1
    sig = hip.signatures[0]
    assert len(sig.feature_set) <= 3
    assert any(feature.startswith("action:") for feature in sig.feature_set)
    assert isinstance(sig.context_vector, tuple)
    assert len(sig.context_vector) == 3


def test_spec_fuzzy_reinforce_works_without_exact_signature_match():
    hip = NOWAHippocampus(reinforce_similarity_threshold=0.35, max_features=8)

    exp_ref = hip.store(_build_path("ctx:a", "ctx:b", "action:go"))
    exp_reinforced = hip.reinforce(_build_path("ctx:a", "ctx:c", "action:go"))

    assert exp_reinforced is exp_ref
    assert len(hip.experiences) == 1
    assert exp_ref.reinforcement_count == 2


def test_spec_recall_performs_pattern_completion_from_partial_input():
    hip = NOWAHippocampus(top_k_recall=2, max_features=8)

    hip.store(_build_path("ctx:forest", "ctx:rain", "action:shelter"))
    hip.store(_build_path("ctx:forest", "ctx:cold", "action:shelter"))

    recalled = hip.recall({"features": {"ctx:forest"}})
    reconstructed = recalled["reconstructed_features"]

    assert "action:shelter" in reconstructed
    assert len(reconstructed) >= 2


def test_spec_novelty_signal_distinguishes_familiar_and_novel_inputs():
    hip = NOWAHippocampus(top_k_recall=3)

    hip.store(_build_path("ctx:known", "action:stay"))

    familiar = hip.recall({"features": {"ctx:known", "action:stay"}})
    novel = hip.recall({"features": {"ctx:alien", "action:explore"}})

    assert novel["novelty_score"] > familiar["novelty_score"]
    assert novel["novelty_score"] > 0.85


def test_spec_recall_api_schema_is_compatible_with_documented_contract():
    hip = NOWAHippocampus()
    hip.store(_build_path("ctx:hello", "action:greet"))

    result = hip.recall({"features": {"ctx:hello"}})

    assert set(["reconstructed_features", "novelty_score", "similarity_top_k"]).issubset(result.keys())
    assert isinstance(result["reconstructed_features"], set)
    assert isinstance(result["novelty_score"], float)
    assert isinstance(result["similarity_top_k"], list)


def test_spec_decay_can_prune_very_weak_unreinforced_traces():
    hip = NOWAHippocampus(
        activation_decay_half_life=0.01,
        decay_rate=0.5,
        activation_threshold=0.70,
    )

    hip.store(_build_path("ctx:noise", "action:random"), intensity=0.1)
    hip.signatures[0].last_decay_ts -= 120.0

    _ = hip.get_statistics()

    assert len(hip.experiences) == 0
    assert len(hip.signatures) == 0


def test_spec_consolidation_probability_responds_to_novelty_repetition_and_reward():
    hip = NOWAHippocampus()

    low = hip.consolidation_probability(novelty_score=0.1, repetition_count=1, reward_signal=-1.0)
    high = hip.consolidation_probability(novelty_score=0.9, repetition_count=5, reward_signal=1.0)

    assert high > low
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


def test_spec_recall_active_drive_mode_remains_backward_compatible():
    hip = NOWAHippocampus()
    hip.store(_build_path("curiosity", "action:explore"))

    recalls = hip.recall(active_drive="curiosity", limit=2)

    assert isinstance(recalls, list)
    assert len(recalls) >= 1


def test_spec_context_similarity_is_continuous_for_partial_overlap():
    hip = NOWAHippocampus(context_history_size=6, top_k_recall=2)

    hip.store(_build_path("ctx:a", "ctx:b", "ctx:c", "action:one"))
    result = hip.recall(
        {
            "features": {"ctx:a", "ctx:b", "action:one"},
            "context_tokens": ["ctx:x", "ctx:a", "ctx:b", "ctx:z"],
        }
    )

    top = result["similarity_top_k"][0]["similarity"]
    assert 0.0 < top < 1.0


def test_spec_decay_not_overly_aggressive_after_two_hours():
    hip = NOWAHippocampus(activation_decay_half_life=3600.0, decay_rate=0.05, activation_threshold=0.0)
    exp = hip.store(_build_path("ctx:long", "action:trace"))
    hip.signatures[0].last_decay_ts -= 7200.0

    _ = hip.activate(["ctx:long"])

    assert exp.activation_energy > 0.20


def test_spec_capacity_can_preserve_high_novelty_trace():
    hip = NOWAHippocampus(max_experiences=3, novelty_capacity_bias=0.85, max_features=6)

    familiar_1 = hip.store(_build_path("ctx:fam", "action:a"))
    familiar_2 = hip.store(_build_path("ctx:fam", "action:b"))
    familiar_3 = hip.store(_build_path("ctx:fam", "action:c"))
    for exp in (familiar_1, familiar_2, familiar_3):
        exp.reinforcement_count = 6
        exp.activation_energy = 1.0

    novel = hip.store(_build_path("ctx:novel", "action:new"))
    novel.activation_energy = 0.12
    novel.reinforcement_count = 1
    hip.signatures[-1].activation_weight = 0.12
    hip._enforce_capacity()

    signatures = [tuple(exp.path.signature()) for exp in hip.experiences]
    assert ("ctx:novel", "action:new") in signatures


def test_spec_adaptive_reconstruction_threshold_avoids_empty_output_on_weak_top_k():
    hip = NOWAHippocampus(top_k_recall=8, max_features=8)
    for idx in range(8):
        hip.store(_build_path(f"ctx:{idx}", f"action:{idx}"))

    result = hip.recall({"features": {"ctx:probe"}})
    assert len(result["reconstructed_features"]) >= 1


def test_spec_explicit_recall_apis_exist_and_match_dispatch_behavior():
    hip = NOWAHippocampus()
    hip.store(_build_path("ctx:q", "action:w"))

    explicit = hip.recall_signature({"features": {"ctx:q"}})
    dispatch = hip.recall({"features": {"ctx:q"}})
    recent = hip.recall_recent(limit=1)

    assert explicit["reconstructed_features"] == dispatch["reconstructed_features"]
    assert explicit["novelty_score"] == dispatch["novelty_score"]
    assert isinstance(recent, list)
    assert len(recent) == 1
