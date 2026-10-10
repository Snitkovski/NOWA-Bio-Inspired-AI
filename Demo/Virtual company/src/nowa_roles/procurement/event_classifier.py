"""Map procurement MCP READ results onto named business events."""

from __future__ import annotations

from typing import Any, Dict, List


def classify_procurement_events(tool_id: str, result: dict) -> list:
    """Role-specific: raw MCP payload → named events from an affective mapping."""
    if not isinstance(result, dict):
        return [str(tool_id).split("__")[-1]]

    events: List[str] = []
    tool_tail = str(tool_id).split("__")[-1]

    if "stock" in tool_tail or "stock_levels" in tool_tail or "products" in result or "stock" in result:
        events.extend(_stock_events(result))
    if "supplier" in tool_tail or "suppliers" in result:
        events.extend(_supplier_events(result))
    if "budget" in tool_tail or "remaining" in result or "utilization_ratio" in result:
        events.extend(_budget_events(result))

    status = str(result.get("status") or "").strip().lower()
    if status in ("urgent", "critical"):
        events.append("stock_critical_low")
    elif status in ("accepted", "success", "ok"):
        events.append("deal_closed_favorable")
    elif status in ("rejected", "failed", "error"):
        events.append("supplier_defaulted")
    elif status == "timeout":
        events.append("order_arrived_late")

    return events or [tool_tail]


def _as_product_map(result: Dict[str, Any]) -> Dict[str, dict]:
    for key in ("stock", "products", "stock_levels", "items"):
        payload = result.get(key)
        if isinstance(payload, dict):
            return {
                str(pid): info
                for pid, info in payload.items()
                if isinstance(info, dict)
            }
    if result and all(isinstance(v, dict) for v in result.values() if v is not None):
        skip = {"status", "reason", "tool_id"}
        return {
            str(pid): info
            for pid, info in result.items()
            if pid not in skip and isinstance(info, dict)
        }
    return {}


def _stock_events(result: Dict[str, Any]) -> List[str]:
    events: List[str] = []
    for info in _as_product_map(result).values():
        below = bool(info.get("below_reorder_point"))
        if "below_replenishment_point" in info:
            below = below or bool(info.get("below_replenishment_point"))
        qty = info.get("quantity", info.get("projected_quantity"))
        try:
            qty_f = float(qty) if qty is not None else None
        except (TypeError, ValueError):
            qty_f = None
        if below or (qty_f is not None and qty_f <= 0):
            events.append("stock_critical_low")
            break
    return events


def _supplier_events(result: Dict[str, Any]) -> List[str]:
    suppliers = result.get("suppliers", result)
    if not isinstance(suppliers, dict):
        return []
    for info in suppliers.values():
        if not isinstance(info, dict):
            continue
        if info.get("is_defaulted") is True or str(info.get("status") or "").lower() == "defaulted":
            return ["supplier_defaulted"]
    return []


def _budget_events(result: Dict[str, Any]) -> List[str]:
    try:
        utilization = float(result.get("utilization_ratio", 0.0) or 0.0)
    except (TypeError, ValueError):
        utilization = 0.0
    remaining = result.get("remaining")
    try:
        remaining_f = float(remaining) if remaining is not None else None
    except (TypeError, ValueError):
        remaining_f = None
    if remaining_f is not None and remaining_f <= 0:
        return ["budget_exceeded"]
    if utilization > 0.9:
        return ["budget_exceeded"]
    return []
