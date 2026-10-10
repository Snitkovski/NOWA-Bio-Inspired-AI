"""Tests for BusinessEventEncoder (spec §5, parent spec §3.3)."""

from nowa_body.business_event_encoder import BusinessEventEncoder


MAPPING = {
    "stock_critical_low": {
        "valence": -0.7,
        "arousal": 0.8,
        "tags": ["procurement", "urgency"],
    },
    "deal_closed_favorable": {
        "valence": 0.8,
        "arousal": 0.6,
        "tags": ["procurement", "success"],
    },
}


def test_encode_tool_result_fallback_uses_tool_tail():
    encoder = BusinessEventEncoder({})
    tokens = encoder.encode_tool_result("mcp__1c__get_stock_levels", {"qty": 1})
    assert tokens == ["event:get_stock_levels"]


def test_encode_tool_result_uses_mapping_and_classifier():
    encoder = BusinessEventEncoder(MAPPING)

    def classifier(tool_id, result):
        assert tool_id == "mcp__1c__get_stock_levels"
        return ["stock_critical_low"]

    tokens = encoder.encode_tool_result(
        "mcp__1c__get_stock_levels", {"below_reorder_point": True}, classifier
    )
    assert "event:stock_critical_low" in tokens
    assert "valence:very_negative" in tokens
    assert "arousal:high" in tokens
    assert "domain:procurement" in tokens


def test_encode_tool_result_does_not_raise_on_non_dict():
    encoder = BusinessEventEncoder({})
    tokens = encoder.encode_tool_result("mcp__x__y", "garbage")
    assert tokens == ["event:y"]


def test_encode_action_outcome_success_failure_unknown():
    encoder = BusinessEventEncoder({})
    tokens, affect = encoder.encode_action_outcome("do", {"status": "accepted"})
    assert tokens == ["result:success"]
    assert affect["valence"] > 0

    tokens, affect = encoder.encode_action_outcome("do", {"status": "failed"})
    assert tokens == ["result:failure"]
    assert affect["valence"] < 0

    tokens, affect = encoder.encode_action_outcome("do", {"status": "pending"})
    assert tokens == ["result:unknown"]
    assert affect == {}


def test_encode_action_outcome_ok_and_error_aliases():
    encoder = BusinessEventEncoder({})
    assert encoder.encode_action_outcome("x", {"status": "ok"})[0] == ["result:success"]
    assert encoder.encode_action_outcome("x", {"status": "error"})[0] == ["result:failure"]
