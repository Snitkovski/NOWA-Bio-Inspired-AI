import random
import warnings

from epigenome import (
    MAX_PATTERNS,
    EPIGENOME_VERSION,
    EpigenomeSnapshot,
)


def test_tc_01_empty_epigenome():
    epigenome = EpigenomeSnapshot.empty()

    assert epigenome.is_empty() is True
    assert len(epigenome.patterns) == 0
    assert len(epigenome.actions) == 0
    assert len(epigenome.values) == 0
    assert epigenome.source_generation == 0
    assert epigenome.validate() == []


def test_tc_02_extract_from_valid_data():
    cortex_patterns = [
        {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5},
        {"context_signature": "ctx_b", "action": "sleep", "strength": 0.7, "reinforcement_count": 3},
        {"context_signature": "ctx_c", "action": "play", "strength": 0.3, "reinforcement_count": 1},
    ]
    action_metadata = {
        "eat": {
            "predicted_effect": {"hunger": -0.5},
            "semantic_confidence": 0.85,
            "stability_score": 0.9,
            "success_rate": 0.8,
            "consolidated": True,
        },
        "play": {
            "predicted_effect": {"energy": -0.3},
            "semantic_confidence": 0.4,
            "stability_score": 0.3,
            "success_rate": 0.6,
            "consolidated": True,
        },
    }
    value_profiles = {
        "state_abc": {"value": 0.7, "confidence": 0.8, "confirmation_count": 5.0},
        "state_def": {"value": -0.2, "confidence": 0.3, "confirmation_count": 0.5},
    }

    epigenome = EpigenomeSnapshot.extract(
        cortex_patterns=cortex_patterns,
        action_metadata=action_metadata,
        value_profiles=value_profiles,
        min_reinforcement=2,
        min_stability=0.5,
        min_confirmation=1.0,
    )

    assert len(epigenome.patterns) == 2
    assert any(p.context_signature == "ctx_a" for p in epigenome.patterns)
    assert any(p.context_signature == "ctx_b" for p in epigenome.patterns)

    assert len(epigenome.actions) == 1
    assert epigenome.actions[0].action_id == "eat"

    assert len(epigenome.values) == 1
    assert epigenome.values[0].state_key == "state_abc"


def test_tc_03_top_n_patterns_by_reinforcement():
    patterns = [
        {
            "context_signature": f"ctx_{i}",
            "action": "eat",
            "strength": 0.5,
            "reinforcement_count": i,
        }
        for i in range(10)
    ]

    epigenome = EpigenomeSnapshot.extract(
        cortex_patterns=patterns,
        action_metadata={},
        value_profiles={},
        max_patterns=3,
        min_reinforcement=0,
    )

    assert len(epigenome.patterns) == 3
    counts = [p.reinforcement_count for p in epigenome.patterns]
    assert sorted(counts, reverse=True) == counts
    assert counts[0] == 9


def test_tc_04_injection_with_noise_does_not_change_original():
    epigenome = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5}
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )

    original_strength = epigenome.patterns[0].strength

    target_patterns = []
    target_actions = {}
    target_values = {}

    stats = epigenome.inject(
        target_cortex_patterns=target_patterns,
        target_action_metadata=target_actions,
        target_value_profiles=target_values,
        noise_level=0.3,
        rng=random.Random(42),
    )

    assert epigenome.patterns[0].strength == original_strength
    assert stats["patterns_injected"] == 1
    assert len(target_patterns) == 1


def test_tc_05_injection_does_not_override_existing_keys():
    epigenome = EpigenomeSnapshot.extract(
        cortex_patterns=[],
        action_metadata={
            "eat": {
                "predicted_effect": {"hunger": -0.5},
                "semantic_confidence": 0.9,
                "stability_score": 0.8,
                "success_rate": 0.7,
                "consolidated": True,
            }
        },
        value_profiles={},
        min_reinforcement=0,
        min_stability=0.0,
    )

    existing_confidence = 0.3
    target_actions = {
        "eat": {
            "semantic_confidence": existing_confidence,
            "stability_score": 0.1,
        }
    }

    epigenome.inject(
        target_cortex_patterns=[],
        target_action_metadata=target_actions,
        target_value_profiles={},
        noise_level=0.0,
    )

    assert target_actions["eat"]["semantic_confidence"] == existing_confidence


def test_tc_06_injection_noise_zero_is_exact():
    epigenome = EpigenomeSnapshot.extract(
        cortex_patterns=[],
        action_metadata={},
        value_profiles={
            "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
        },
        min_reinforcement=0,
        min_stability=0.0,
        min_confirmation=0.0,
    )

    target_values = {}
    epigenome.inject(
        target_cortex_patterns=[],
        target_action_metadata={},
        target_value_profiles=target_values,
        noise_level=0.0,
        rng=random.Random(0),
    )

    assert abs(target_values["state_x"]["value"] - 0.6) < 1e-9
    assert abs(target_values["state_x"]["confidence"] - 0.8) < 1e-9


def test_tc_07_blend_unites_patterns():
    epi_a = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5}
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )

    epi_b = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_b", "action": "sleep", "strength": 0.7, "reinforcement_count": 3}
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )

    blended = epi_a.blend(epi_b, alpha=0.5)

    sigs = {p.context_signature for p in blended.patterns}
    assert "ctx_a" in sigs
    assert "ctx_b" in sigs


def test_tc_08_blend_averages_duplicate_values():
    epi_a = EpigenomeSnapshot.extract(
        cortex_patterns=[],
        action_metadata={},
        value_profiles={
            "state_x": {"value": 0.8, "confidence": 0.9, "confirmation_count": 4.0}
        },
        min_reinforcement=0,
        min_stability=0.0,
        min_confirmation=0.0,
    )

    epi_b = EpigenomeSnapshot.extract(
        cortex_patterns=[],
        action_metadata={},
        value_profiles={
            "state_x": {"value": 0.2, "confidence": 0.7, "confirmation_count": 2.0}
        },
        min_reinforcement=0,
        min_stability=0.0,
        min_confirmation=0.0,
    )

    blended = epi_a.blend(epi_b, alpha=0.5)

    assert len(blended.values) == 1
    blended_val = blended.values[0]
    assert abs(blended_val.value - 0.5) < 1e-9
    assert abs(blended_val.confidence - 0.7) < 1e-9


def test_tc_09_serialization_round_trip():
    epi = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5}
        ],
        action_metadata={
            "eat": {
                "predicted_effect": {"hunger": -0.5},
                "semantic_confidence": 0.85,
                "stability_score": 0.9,
                "success_rate": 0.8,
                "consolidated": True,
            }
        },
        value_profiles={
            "state_x": {"value": 0.6, "confidence": 0.8, "confirmation_count": 3.0}
        },
        min_reinforcement=0,
        min_stability=0.0,
        min_confirmation=0.0,
        source_generation=3,
        source_lineage_id="abc",
    )

    data = epi.to_dict()
    restored = EpigenomeSnapshot.from_dict(data)

    assert data["version"] == EPIGENOME_VERSION
    assert len(restored.patterns) == len(epi.patterns)
    assert len(restored.actions) == len(epi.actions)
    assert len(restored.values) == len(epi.values)
    assert restored.source_generation == epi.source_generation
    assert restored.source_lineage_id == epi.source_lineage_id
    assert abs(restored.patterns[0].strength - epi.patterns[0].strength) < 1e-9
    assert abs(restored.values[0].value - epi.values[0].value) < 1e-9


def test_tc_10_from_dict_skips_invalid_records():
    data = {
        "version": "1.0",
        "source_generation": 1,
        "source_lineage_id": "test",
        "extraction_timestamp": 0.0,
        "patterns": [
            {"context_signature": "good", "action": "eat", "strength": 0.8, "reinforcement_count": 3},
            {"context_signature": None, "action": None, "strength": "bad", "reinforcement_count": -1},
        ],
        "actions": [],
        "values": [],
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        epi = EpigenomeSnapshot.from_dict(data)

    assert len(epi.patterns) == 1
    assert epi.patterns[0].context_signature == "good"


def test_tc_11_validate_detects_issues():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = {
            "version": "1.0",
            "source_generation": -1,
            "source_lineage_id": "",
            "extraction_timestamp": 0.0,
            "patterns": [
                {"context_signature": "ctx", "action": "eat", "strength": 1.5, "reinforcement_count": 3},
            ],
            "actions": [],
            "values": [],
        }
        epi = EpigenomeSnapshot.from_dict(data)

    issues = epi.validate()
    assert len(issues) > 0


def test_tc_12_blend_does_not_exceed_limits():
    patterns_a = [
        {
            "context_signature": f"ctx_a_{i}",
            "action": "eat",
            "strength": 0.9,
            "reinforcement_count": 10,
        }
        for i in range(MAX_PATTERNS)
    ]
    patterns_b = [
        {
            "context_signature": f"ctx_b_{i}",
            "action": "sleep",
            "strength": 0.8,
            "reinforcement_count": 8,
        }
        for i in range(MAX_PATTERNS)
    ]

    epi_a = EpigenomeSnapshot.extract(
        cortex_patterns=patterns_a,
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
        max_patterns=MAX_PATTERNS,
    )
    epi_b = EpigenomeSnapshot.extract(
        cortex_patterns=patterns_b,
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
        max_patterns=MAX_PATTERNS,
    )

    blended = epi_a.blend(epi_b)
    assert len(blended.patterns) <= MAX_PATTERNS


def test_tc_13_summary_contains_expected_keys():
    epi = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_a", "action": "eat", "strength": 0.8, "reinforcement_count": 4}
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )

    summary = epi.summary()
    required_keys = [
        "patterns_count",
        "actions_count",
        "values_count",
        "mean_pattern_strength",
        "mean_action_stability",
        "mean_value_confidence",
        "source_generation",
    ]
    for key in required_keys:
        assert key in summary

    assert summary["patterns_count"] == 1
    assert abs(summary["mean_pattern_strength"] - 0.8) < 1e-9


def test_tc_14_determinism_with_fixed_rng():
    epi = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {"context_signature": "ctx_a", "action": "eat", "strength": 0.9, "reinforcement_count": 5}
        ],
        action_metadata={},
        value_profiles={},
        min_reinforcement=0,
    )

    target1 = []
    target2 = []

    epi.inject(
        target_cortex_patterns=target1,
        target_action_metadata={},
        target_value_profiles={},
        noise_level=0.3,
        rng=random.Random(42),
    )
    epi.inject(
        target_cortex_patterns=target2,
        target_action_metadata={},
        target_value_profiles={},
        noise_level=0.3,
        rng=random.Random(42),
    )

    assert target1[0]["strength"] == target2[0]["strength"]


def test_tc_15_empty_passes_validate_and_size():
    epi = EpigenomeSnapshot.empty()
    assert epi.validate() == []
    assert epi.is_empty() is True
    assert epi.size()["total"] == 0


def test_tc_16_lineage_id_is_truncated_in_blend():
    long_id = "x" * 100
    epi_a = EpigenomeSnapshot.empty()
    epi_b = EpigenomeSnapshot.empty()

    data_a = epi_a.to_dict()
    data_a["source_lineage_id"] = long_id
    epi_a = EpigenomeSnapshot.from_dict(data_a)

    data_b = epi_b.to_dict()
    data_b["source_lineage_id"] = long_id
    epi_b = EpigenomeSnapshot.from_dict(data_b)

    blended = epi_a.blend(epi_b)
    assert len(blended.source_lineage_id) <= 64

