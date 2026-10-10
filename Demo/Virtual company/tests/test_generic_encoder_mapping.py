"""GenericEncoder mapping overlay emits EmotionalImpulse from src/affective_space."""

from __future__ import annotations

import pytest

from affective_space import EmotionalImpulse
from mcp_body.generic_encoder import MAX_IMPULSE_INTENSITY, GenericEncoder
from mcp_body.world_state import WorldState


MAPPING = {
    "stock_critical_low": {
        "valence": -0.7,
        "arousal": 0.8,
        "stress": 0.7,
        "tags": ["procurement"],
        "intensity": 0.9,
    }
}


def test_haystack_match_emits_external_impulse():
    encoder = GenericEncoder(MAPPING)
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_stock",
        {"status": "ok", "note": "stock_critical_low"},
    )
    tokens, impulses = encoder.encode(state)
    assert "event:stock_critical_low" in tokens
    mapped = [
        item for item in impulses
        if isinstance(item, EmotionalImpulse) and item.vector.get("arousal") == pytest.approx(0.8)
    ]
    assert mapped
    assert mapped[0].source == "external"
    assert mapped[0].intensity == pytest.approx(MAX_IMPULSE_INTENSITY)
    assert mapped[0].vector["stress"] == pytest.approx(0.7)


def test_classifier_extra_events_deduped_with_haystack():
    encoder = GenericEncoder(MAPPING)
    state = WorldState()
    state.update_from_read(
        "mcp__1c__get_stock",
        {"status": "ok", "note": "stock_critical_low"},
    )
    _tokens, impulses = encoder.encode(state, extra_events=["stock_critical_low"])
    mapped = [
        item for item in impulses
        if isinstance(item, EmotionalImpulse) and item.vector.get("arousal") == pytest.approx(0.8)
    ]
    assert len(mapped) == 1


def test_classifier_only_fires_mapping_impulse():
    encoder = GenericEncoder(MAPPING)
    state = WorldState()
    state.update_from_read("mcp__1c__get_stock", {"status": "ok"})
    tokens, impulses = encoder.encode(state, extra_events=["stock_critical_low"])
    assert "event:stock_critical_low" in tokens
    assert any(
        isinstance(item, EmotionalImpulse) and item.vector.get("stress") == pytest.approx(0.7)
        for item in impulses
    )


def test_encode_outcome_still_uses_platform_impulse():
    encoder = GenericEncoder(MAPPING)
    tokens, impulse = encoder.encode_outcome("success", {"status": "success"}, tool_id="mcp__x__y")
    assert "result:success" in tokens
    assert isinstance(impulse, EmotionalImpulse)
    assert impulse.vector.get("valence", 0) > 0


def test_cost_heuristic_still_emits_beside_mapping():
    encoder = GenericEncoder(MAPPING)
    state = WorldState()
    state.update_from_read("mcp__1c__budget", {"status": "ok", "price": 1.0})
    state.update_from_read(
        "mcp__1c__budget",
        {"status": "ok", "price": 100.0, "flag": "stock_critical_low"},
    )
    tokens, impulses = encoder.encode(state)
    assert "event:stock_critical_low" in tokens
    has_mapping = any(
        isinstance(item, EmotionalImpulse) and item.vector.get("arousal") == pytest.approx(0.8)
        for item in impulses
    )
    has_heuristic = any(
        isinstance(item, dict) and (item.get("vector") or {}).get("stress") == 0.35
        for item in impulses
    )
    assert has_mapping
    assert has_heuristic
