"""Heuristic risk classification for newly discovered MCP tools."""

from __future__ import annotations

from .mcp_capability import CapabilityRisk

RISK_KEYWORDS = {
    CapabilityRisk.READ_ONLY: [
        "get_", "list_", "search_", "read_", "fetch_", "query_",
        "check_", "view_",
    ],
    CapabilityRisk.LOW_WRITE: [
        "draft_", "prepare_", "compose_", "generate_document_",
    ],
    CapabilityRisk.MEDIUM_WRITE: [
        "send_", "create_order_", "create_", "submit_", "post_", "update_",
    ],
    CapabilityRisk.HIGH_WRITE: [
        "pay_", "transfer_", "approve_payment_", "sign_contract_",
        "change_price_",
    ],
    CapabilityRisk.IRREVERSIBLE: [
        "delete_", "cancel_contract_", "terminate_", "revoke_",
    ],
}

_RISK_ORDER = (
    CapabilityRisk.IRREVERSIBLE,
    CapabilityRisk.HIGH_WRITE,
    CapabilityRisk.MEDIUM_WRITE,
    CapabilityRisk.LOW_WRITE,
    CapabilityRisk.READ_ONLY,
)


def classify_risk_heuristic(tool_name: str, description: str = "") -> CapabilityRisk:
    """Primary heuristic classification from a tool name (and description).

    This is only a default. An administrator MUST confirm or correct the
    class before an agent receives the tool. Never rely on the heuristic
    for HIGH_WRITE / IRREVERSIBLE without human review.

    Ambiguous names are classified toward the more dangerous class: keywords
    are checked from irreversible down to read-only.
    """
    name_lower = str(tool_name or "").lower()
    desc_lower = str(description or "").lower()
    for risk in _RISK_ORDER:
        keywords = RISK_KEYWORDS[risk]
        if any(kw in name_lower for kw in keywords):
            return risk
        if desc_lower and any(kw in desc_lower for kw in keywords):
            return risk
    return CapabilityRisk.HIGH_WRITE
