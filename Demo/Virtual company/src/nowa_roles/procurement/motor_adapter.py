"""Procurement MotorAdapter: action_type + MCP observations → order params.

Reuses the sandbox ProcurementMotorAdapter selection helpers almost
verbatim; the observation source is a dict from READ_ONLY MCP tools
instead of ``ProcurementWorld.observe_*``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional

from nowa_body._compat import clamp, safe_float
from nowa_body.mcp_capability import MCPCapability
from nowa_body.motor_adapter import MotorAdapter

COVERAGE_DAYS = 30.0
MIN_HEURISTIC_QTY = 10.0

PROCUREMENT_ACTION_TYPES = [
    "place_order_reliable_supplier",
    "place_order_cheap_supplier",
    "urgent_reorder",
    "diversify_supplier",
]

_PRICE_KEYS = ("unit_price", "base_price", "price", "base_price_multiplier")
_LEAD_KEYS = ("lead_time_days", "lead_time")
_RELIABILITY_KEYS = ("reliability", "reliability_score")
_OFFER_KEYS = ("offers", "product_offers")
_PROJECTION_KEYS = ("projected_quantity", "projected", "inbound", "inbound_quantity")
_UNAVAILABLE_STATUSES = frozenset({"unavailable", "defaulted", "inactive"})

_SUPPLIER_STRATEGIES = {
    "place_order_reliable_supplier": "_select_most_reliable",
    "place_order_cheap_supplier": "_select_cheapest",
    "urgent_reorder": "_select_fastest",
    "diversify_supplier": "_select_least_used",
    "wait_and_monitor": None,
}


class ProcurementBodyMotorAdapter(MotorAdapter):
    """First concrete MotorAdapter: procurement order parameter resolution."""

    def _build_params(
        self,
        capability: MCPCapability,
        action_type: str,
        observations: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        strategy_method = _SUPPLIER_STRATEGIES.get(action_type)
        if strategy_method is None:
            return None

        stock_obs = self._extract_stock(observations)
        supplier_obs = self._extract_suppliers(observations)
        budget_obs = self._extract_budget(observations)
        hippocampus = getattr(self, "_hippocampus", None)

        if not isinstance(stock_obs, dict) or not isinstance(supplier_obs, dict):
            return None
        if not isinstance(budget_obs, dict):
            budget_obs = {}

        priority_product = self._select_priority_product(stock_obs)
        if priority_product is None:
            return None

        selector = getattr(self, strategy_method, None)
        if not callable(selector):
            return None
        supplier_id = selector(supplier_obs, hippocampus, priority_product)
        if supplier_id is None:
            return None

        supplier_info = supplier_obs.get(supplier_id) or {}
        if not isinstance(supplier_info, dict):
            supplier_info = {}

        qty = self._calculate_qty(priority_product, stock_obs, supplier_info)
        qty = self._cap_qty_to_budget(qty, budget_obs, supplier_info, priority_product)
        if qty <= 0:
            return None

        return {
            "supplier_id": str(supplier_id),
            "product_id": str(priority_product),
            "qty": qty,
            "strategy": str(action_type),
            "confidence": self._estimate_confidence(action_type, supplier_obs),
        }

    def _estimate_cost(self, capability: MCPCapability, params: dict) -> Optional[float]:
        del capability
        if not isinstance(params, dict):
            return None
        qty = safe_float(params.get("qty"), 0.0)
        price = safe_float(params.get("unit_price"), 0.0)
        if qty <= 0 or price <= 0:
            return None
        return qty * price

    # --- observation extraction ----------------------------------------------

    def _extract_stock(self, observations: Dict[str, Any]) -> Dict[str, dict]:
        if isinstance(observations.get("stock"), dict):
            return observations["stock"]
        return self._map_from_tool_results(
            observations,
            keys=("stock", "stock_levels", "products"),
            tool_needles=("stock",),
        )

    def _extract_suppliers(self, observations: Dict[str, Any]) -> Dict[str, dict]:
        if isinstance(observations.get("suppliers"), dict):
            return observations["suppliers"]
        return self._map_from_tool_results(
            observations,
            keys=("suppliers", "supplier_directory"),
            tool_needles=("supplier",),
        )

    def _extract_budget(self, observations: Dict[str, Any]) -> dict:
        budget = observations.get("budget")
        if isinstance(budget, dict):
            return budget
        tool_results = observations.get("tool_results") or {}
        if not isinstance(tool_results, dict):
            return {}
        for tool_id, payload in tool_results.items():
            if "budget" not in str(tool_id).lower():
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def _map_from_tool_results(
        self,
        observations: Dict[str, Any],
        keys: Iterable[str],
        tool_needles: Iterable[str],
    ) -> Dict[str, dict]:
        tool_results = observations.get("tool_results") or {}
        if not isinstance(tool_results, dict):
            return {}
        for tool_id, payload in tool_results.items():
            if not isinstance(payload, dict):
                continue
            if not any(n in str(tool_id).lower() for n in tool_needles):
                continue
            for key in keys:
                inner = payload.get(key)
                if isinstance(inner, dict):
                    return {
                        str(pid): info
                        for pid, info in inner.items()
                        if isinstance(info, dict)
                    }
            skip = {"status", "reason", "tool_id"}
            if payload and all(
                isinstance(v, dict) for k, v in payload.items() if k not in skip
            ):
                return {
                    str(pid): info
                    for pid, info in payload.items()
                    if pid not in skip and isinstance(info, dict)
                }
        return {}

    # --- selection helpers (sandbox ProcurementMotorAdapter, verbatim) -------

    def _select_priority_product(self, stock_obs: Dict[str, dict]) -> Optional[str]:
        if not isinstance(stock_obs, dict):
            return None
        deficits: Dict[str, float] = {}
        for pid, info in stock_obs.items():
            if not isinstance(info, dict):
                continue
            effective = self._effective_quantity(info)
            reorder = safe_float(info.get("reorder_point"), 0.0)
            trigger = self._replenishment_trigger(info, reorder)
            if not self._is_below_reorder(info, effective, reorder):
                continue
            deficits[pid] = effective - trigger
        if not deficits:
            return None
        return min(deficits, key=lambda pid: (deficits[pid], str(pid)))

    def _select_most_reliable(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        del hippocampus
        available = self._available_suppliers(supplier_obs, product_id)
        if not available:
            return None
        return max(
            available,
            key=lambda sid: (
                self._reliability_of(supplier_obs.get(sid) or {}, product_id),
                str(sid),
            ),
        )

    def _select_cheapest(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        del hippocampus
        available = self._available_suppliers(supplier_obs, product_id)
        if not available:
            return None
        use_price = any(
            self._has_price_signal(supplier_obs.get(sid) or {}, product_id)
            for sid in available
        )
        if use_price:
            return min(
                available,
                key=lambda sid: (
                    self._price_of(supplier_obs.get(sid) or {}, product_id),
                    str(sid),
                ),
            )
        return min(
            available,
            key=lambda sid: (
                safe_float((supplier_obs.get(sid) or {}).get("reputation"), 1.0),
                str(sid),
            ),
        )

    def _select_fastest(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        del hippocampus
        available = self._available_suppliers(supplier_obs, product_id)
        if not available:
            return None
        use_lead = any(
            self._has_lead_signal(supplier_obs.get(sid) or {}, product_id)
            for sid in available
        )
        if use_lead:
            return min(
                available,
                key=lambda sid: (
                    self._lead_time_of(supplier_obs.get(sid) or {}, product_id),
                    str(sid),
                ),
            )
        return max(
            available,
            key=lambda sid: (
                safe_float((supplier_obs.get(sid) or {}).get("reputation"), 0.0),
                str(sid),
            ),
        )

    def _select_least_used(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        available = self._available_suppliers(supplier_obs, product_id)
        if not available:
            return None
        usage_counts: Dict[str, int] = {sid: 0 for sid in available}
        for token in self._experience_tokens(hippocampus):
            for sid in available:
                if self._token_mentions_supplier(token, sid):
                    usage_counts[sid] += 1
        return min(available, key=lambda sid: (usage_counts.get(sid, 0), str(sid)))

    def _available_suppliers(
        self, supplier_obs: Dict, product_id: Optional[str] = None
    ) -> list:
        if not isinstance(supplier_obs, dict):
            return []
        filter_by_offer = product_id is not None and self._directory_has_offers(
            supplier_obs
        )
        available: List[str] = []
        for sid, info in supplier_obs.items():
            if not isinstance(info, dict):
                continue
            if self._is_unavailable(info):
                continue
            if filter_by_offer:
                offer = self._product_offer(info, product_id)
                if offer is None or self._is_unavailable(offer):
                    continue
            available.append(sid)
        return available

    def _calculate_qty(
        self, product_id: str, stock_obs: Dict, supplier_info: Dict
    ) -> float:
        del supplier_info
        info = stock_obs.get(product_id) if isinstance(stock_obs, dict) else None
        if not isinstance(info, dict):
            info = {}
        if "base_demand_per_day" in info:
            demand = safe_float(info.get("base_demand_per_day"), 0.0)
            return max(0.0, demand * COVERAGE_DAYS)
        current = self._effective_quantity(info)
        reorder_point = safe_float(info.get("reorder_point"), 100.0)
        deficit = max(0.0, reorder_point * 2.0 - current)
        return max(MIN_HEURISTIC_QTY, deficit)

    def _estimate_confidence(self, action_type: str, supplier_obs: Dict) -> float:
        available = self._available_suppliers(supplier_obs)
        if not available:
            return 0.0
        if action_type == "place_order_reliable_supplier":
            max_reliability = max(
                self._reliability_of(supplier_obs.get(sid) or {}, None)
                for sid in available
            )
            return clamp(max_reliability, 0.0, 1.0)
        return 0.6

    def _effective_quantity(self, info: Dict[str, Any]) -> float:
        if "projected_quantity" in info:
            return safe_float(info.get("projected_quantity"), 0.0)
        if "projected" in info:
            return safe_float(info.get("projected"), 0.0)
        qty = safe_float(info.get("quantity"), 0.0)
        inbound = 0.0
        if "inbound_quantity" in info:
            inbound = safe_float(info.get("inbound_quantity"), 0.0)
        elif "inbound" in info:
            inbound = safe_float(info.get("inbound"), 0.0)
        return qty + inbound

    def _replenishment_trigger(self, info: Dict[str, Any], reorder: float) -> float:
        if "replenishment_point" in info:
            return max(reorder, safe_float(info.get("replenishment_point"), reorder))
        return reorder

    def _is_below_reorder(
        self, info: Dict[str, Any], effective: float, reorder: float
    ) -> bool:
        trigger = self._replenishment_trigger(info, reorder)
        if any(key in info for key in _PROJECTION_KEYS):
            return effective < trigger
        if "projected_below_replenishment_point" in info:
            return bool(info.get("projected_below_replenishment_point"))
        if "below_replenishment_point" in info and "replenishment_point" in info:
            return bool(info.get("below_replenishment_point"))
        if "below_reorder_point" in info:
            return bool(info.get("below_reorder_point"))
        return effective < trigger

    def _is_unavailable(self, info: Dict[str, Any]) -> bool:
        if info.get("is_defaulted") is True:
            return True
        if info.get("available") is False or info.get("is_available") is False:
            return True
        status = str(info.get("status") or "").strip().lower()
        return status in _UNAVAILABLE_STATUSES

    def _directory_has_offers(self, supplier_obs: Dict) -> bool:
        for info in supplier_obs.values():
            if not isinstance(info, dict):
                continue
            if any(key in info for key in _OFFER_KEYS):
                return True
        return False

    def _product_offer(
        self, info: Dict[str, Any], product_id: Optional[str]
    ) -> Optional[dict]:
        if product_id is None or not isinstance(info, dict):
            return None
        offers = None
        for key in _OFFER_KEYS:
            if key in info:
                offers = info.get(key)
                break
        if isinstance(offers, dict):
            offer = offers.get(product_id)
            return offer if isinstance(offer, dict) else None
        if isinstance(offers, list):
            for item in offers:
                if isinstance(item, dict) and item.get("product_id") == product_id:
                    return item
        return None

    def _numeric_from_offer_or_supplier(
        self,
        info: Dict[str, Any],
        product_id: Optional[str],
        keys: Iterable[str],
        default: float,
    ) -> float:
        offer = self._product_offer(info, product_id)
        if isinstance(offer, dict):
            for key in keys:
                if key in offer:
                    return safe_float(offer.get(key), default)
        if isinstance(info, dict):
            for key in keys:
                if key in info:
                    return safe_float(info.get(key), default)
        return float(default)

    def _has_price_signal(self, info: Dict[str, Any], product_id: str) -> bool:
        offer = self._product_offer(info, product_id)
        if isinstance(offer, dict) and any(key in offer for key in _PRICE_KEYS):
            return True
        return any(key in info for key in _PRICE_KEYS)

    def _has_lead_signal(self, info: Dict[str, Any], product_id: str) -> bool:
        offer = self._product_offer(info, product_id)
        if isinstance(offer, dict) and any(key in offer for key in _LEAD_KEYS):
            return True
        return any(key in info for key in _LEAD_KEYS)

    def _price_of(self, info: Dict[str, Any], product_id: Optional[str]) -> float:
        price = self._numeric_from_offer_or_supplier(
            info, product_id, _PRICE_KEYS, 1.0
        )
        return price if price > 0 else 1.0

    def _lead_time_of(self, info: Dict[str, Any], product_id: Optional[str]) -> float:
        return self._numeric_from_offer_or_supplier(info, product_id, _LEAD_KEYS, 0.0)

    def _reliability_of(self, info: Dict[str, Any], product_id: Optional[str]) -> float:
        if not isinstance(info, dict):
            return 0.0
        return self._numeric_from_offer_or_supplier(
            info, product_id, _RELIABILITY_KEYS, 0.0
        )

    def _cap_qty_to_budget(
        self,
        qty: float,
        budget_obs: dict,
        supplier_info: Dict[str, Any],
        product_id: str,
    ) -> float:
        budget = safe_float((budget_obs or {}).get("remaining"), 0.0)
        if budget <= 0 or qty <= 0:
            return 0.0
        unit_price = self._price_of(supplier_info or {}, product_id)
        if unit_price <= 0:
            unit_price = 1.0
        max_qty = math.floor((budget / unit_price) * 10.0 + 1e-9) / 10.0
        capped = min(qty, max_qty)
        capped = round(capped, 1)
        if capped * unit_price > budget + 1e-9:
            capped = max_qty
        return max(0.0, capped)

    def _experience_tokens(self, hippocampus: Any) -> List[str]:
        try:
            raw = getattr(hippocampus, "experiences", None)
        except Exception:
            return []
        if not isinstance(raw, (list, tuple, set)):
            return []
        tokens: List[str] = []
        for exp in raw:
            try:
                tokens.extend(self._tokens_from_experience(exp))
            except Exception:
                continue
        return tokens

    def _tokens_from_experience(self, exp: Any) -> List[str]:
        if exp is None:
            return []
        if isinstance(exp, str):
            return [exp]
        collected: List[str] = []
        path = None
        events = None
        if isinstance(exp, dict):
            path = exp.get("path")
            events = exp.get("events")
        else:
            path = getattr(exp, "path", None)
            events = getattr(exp, "events", None)
        if events is not None:
            collected.extend(self._tokens_from_events(events))
        collected.extend(self._tokens_from_path(path))
        return collected

    def _tokens_from_path(self, path: Any) -> List[str]:
        if path is None:
            return []
        if isinstance(path, str):
            return [path]
        if isinstance(path, (list, tuple, set)):
            return self._tokens_from_events(path)
        events = getattr(path, "events", None)
        if events is not None:
            return self._tokens_from_events(events)
        return [str(path)]

    def _tokens_from_events(self, events: Any) -> List[str]:
        if events is None or isinstance(events, (str, bytes)):
            if isinstance(events, str):
                return [events]
            return []
        try:
            iterator = list(events)
        except Exception:
            return []
        tokens: List[str] = []
        for event in iterator:
            if event is None:
                continue
            if isinstance(event, str):
                tokens.append(event)
                continue
            if isinstance(event, dict):
                label = event.get("label") or event.get("name") or event.get("token")
                tokens.append(str(label) if label is not None else str(event))
                continue
            label = getattr(event, "label", None)
            name = getattr(event, "name", None)
            if label is not None:
                tokens.append(str(label))
            elif name is not None:
                tokens.append(str(name))
            else:
                tokens.append(str(event))
        return tokens

    def _token_mentions_supplier(self, token: str, supplier_id: str) -> bool:
        if not token or not supplier_id:
            return False
        marker = f"supplier:{supplier_id}"
        if marker == token or marker in token:
            return True
        return token == supplier_id
