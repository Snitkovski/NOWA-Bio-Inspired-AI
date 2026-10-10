"""Tests for heuristic MCP risk classification (parent spec §2.4)."""

from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.risk_classifier import classify_risk_heuristic


def test_read_only_from_get_prefix():
    assert classify_risk_heuristic("get_stock_levels", "") is CapabilityRisk.READ_ONLY


def test_low_write_from_draft_prefix():
    assert classify_risk_heuristic("draft_purchase_order", "") is CapabilityRisk.LOW_WRITE


def test_medium_write_from_send_prefix():
    assert classify_risk_heuristic("send_email", "") is CapabilityRisk.MEDIUM_WRITE


def test_high_write_from_pay_prefix():
    assert classify_risk_heuristic("pay_invoice", "") is CapabilityRisk.HIGH_WRITE


def test_irreversible_from_delete_prefix():
    assert classify_risk_heuristic("delete_contract", "") is CapabilityRisk.IRREVERSIBLE


def test_unknown_pattern_is_high_write_fail_safe():
    assert classify_risk_heuristic("frobnicate", "does something") is CapabilityRisk.HIGH_WRITE


def test_dangerous_keyword_wins_over_read_keyword():
    assert (
        classify_risk_heuristic("get_and_delete_record", "")
        is CapabilityRisk.IRREVERSIBLE
    )


def test_description_is_used_when_name_has_no_keyword():
    assert (
        classify_risk_heuristic("tool42", "This will pay_ a vendor")
        is CapabilityRisk.HIGH_WRITE
    )
