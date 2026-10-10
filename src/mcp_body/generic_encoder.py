"""GenericEncoder — MCP READ/WRITE results → context tokens + EmotionalImpulse.

Replaces a mandatory role event_classifier. YAML affective_mapping / token_rules
are an overlay, not a requirement (spec §6.5).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from affective_space import AXES, EmotionalImpulse, mapped_event_tokens

from ._compat import clamp, impulse_to_vector, is_number, outcome_impulse, safe_float
from .field_lexicon import ROLE_COST, ROLE_QUANTITY, classify_field, merge_aliases
from .mcp_client import server_id_from_tool_id, split_tool_id
from .world_state import WorldState, row_id

ENTITY_CAP = 32
MAX_IMPULSE_INTENSITY = 0.4
BUCKETS = ("low", "mid", "high", "rising", "falling")


class GenericEncoder:
    def __init__(
        self,
        affective_mapping: Optional[Dict[str, dict]] = None,
        field_aliases: Optional[Dict[str, Any]] = None,
        token_rules: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.affective_mapping = dict(affective_mapping or {})
        self.field_aliases = dict(field_aliases or {})
        self.token_rules = dict(token_rules or {})
        self._seen_scalar_paths: set = set()
        self._seen_entity_ids: set = set()

    def encode(
        self,
        world_state: WorldState,
        last_results: Optional[Dict[str, dict]] = None,
        tool_id: Optional[str] = None,
        result: Optional[dict] = None,
        extra_events: Optional[Sequence[str]] = None,
    ) -> Tuple[List[str], List[Any]]:
        """READ observation → (tokens, impulses)."""
        tokens: List[str] = []
        impulses: List[Any] = []
        results = dict(last_results or getattr(world_state, "results", {}) or {})
        if tool_id is not None and result is not None:
            results[str(tool_id)] = result if isinstance(result, dict) else {"value": result}

        if tool_id:
            tokens.extend(self._tokens_for_tool(str(tool_id), results.get(str(tool_id), {})))
            impulses.extend(self._impulses_for_tool(str(tool_id), results.get(str(tool_id), {}), world_state))
        else:
            for tid, payload in results.items():
                tokens.extend(self._tokens_for_tool(str(tid), payload if isinstance(payload, dict) else {}))
                impulses.extend(
                    self._impulses_for_tool(str(tid), payload if isinstance(payload, dict) else {}, world_state)
                )

        tokens.extend(self._field_bucket_tokens(world_state))
        tokens.extend(self._entity_tokens(world_state))
        overlay_tokens, overlay_impulses = self._overlay_mapped(results, extra_events)
        tokens.extend(overlay_tokens)
        impulses.extend(overlay_impulses)

        if not tokens:
            tokens = ["quiet_period"]
        return tokens, impulses

    def encode_tool_result(
        self,
        tool_id: str,
        result: Dict[str, Any],
        event_classifier: Any = None,
        world_state: Optional[WorldState] = None,
    ) -> List[str]:
        """Backward-compatible token-only READ encoding."""
        del event_classifier
        state = world_state or WorldState()
        tokens, _impulses = self.encode(state, {str(tool_id): result}, tool_id=str(tool_id), result=result)
        return tokens

    def encode_outcome(
        self,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        tool_id: str = "",
    ) -> Tuple[List[str], Any]:
        envelope = result if isinstance(result, dict) else {"status": result}
        status_key = str(envelope.get("status", status) or "unknown").strip().lower() or "unknown"
        if status_key in ("accepted", "success", "ok"):
            tokens = ["result:success"]
        elif status_key in ("rejected", "failed", "error"):
            tokens = ["result:failure"]
        else:
            tokens = ["result:unknown"]
        if tool_id:
            tokens.append(f"tool:{tool_id}")
            tokens.append(f"action:{tool_id}")
        impulse = outcome_impulse(status_key, 1.0)
        return tokens, impulse

    def _tokens_for_tool(self, tool_id: str, payload: Dict[str, Any]) -> List[str]:
        server_id, _name = split_tool_id(tool_id)
        status = str((payload or {}).get("status", "unknown")).strip().lower() or "unknown"
        tokens = [f"tool:{tool_id}", f"status:{status}"]
        if server_id:
            tokens.append(f"server:{server_id}")
        else:
            fallback = server_id_from_tool_id(tool_id)
            if fallback:
                tokens.append(f"server:{fallback}")
        return tokens

    def _impulses_for_tool(
        self,
        tool_id: str,
        payload: Dict[str, Any],
        world_state: WorldState,
    ) -> List[Any]:
        del tool_id
        impulses: List[Any] = []
        status = str((payload or {}).get("status", "")).strip().lower()
        if status in ("rejected", "failed", "error"):
            impulses.append(outcome_impulse("error", MAX_IMPULSE_INTENSITY))
        if status in ("timeout", "unknown"):
            impulses.append(outcome_impulse("timeout", min(0.3, MAX_IMPULSE_INTENSITY)))

        cost_rising = False
        qty_falling = False
        for path, _value in list(getattr(world_state, "scalars", {}).items()):
            leaf = path.rsplit(".", 1)[-1]
            role = classify_field(leaf, self.field_aliases)
            delta = world_state.delta(path)
            if delta is None:
                continue
            stats = world_state.stats_for(path)
            span = max(1e-9, abs(safe_float(stats.get("max"), 0.0) - safe_float(stats.get("min"), 0.0)))
            if role == ROLE_COST and delta > 0.15 * span:
                cost_rising = True
            if role == ROLE_QUANTITY and delta < -0.15 * span:
                qty_falling = True
        if cost_rising or qty_falling:
            impulses.append(
                {
                    "vector": {"stress": 0.35, "valence": -0.25},
                    "intensity": 0.35,
                    "source": "external",
                }
            )
        new_keys = 0
        for path in getattr(world_state, "scalars", {}):
            if path not in self._seen_scalar_paths:
                new_keys += 1
                self._seen_scalar_paths.add(path)
        for collection, rows in getattr(world_state, "entities", {}).items():
            for row in rows:
                identifier = row_id(row)
                if not identifier:
                    continue
                key = f"{collection}:{identifier}"
                if key not in self._seen_entity_ids:
                    new_keys += 1
                    self._seen_entity_ids.add(key)
        if new_keys:
            impulses.append(
                {
                    "vector": {"curiosity": 0.25},
                    "intensity": min(MAX_IMPULSE_INTENSITY, 0.08 * min(new_keys, 5)),
                    "source": "external",
                }
            )
        return impulses

    def _field_bucket_tokens(self, world_state: WorldState) -> List[str]:
        tokens: List[str] = []
        aliases = self.field_aliases
        for path, value in getattr(world_state, "scalars", {}).items():
            leaf = path.rsplit(".", 1)[-1]
            role = classify_field(leaf, aliases)
            if not role:
                continue
            bucket = self._bucket(world_state, path, value)
            if bucket:
                tokens.append(f"field:{role}:{bucket}")
        # Unique while preserving order.
        seen = set()
        unique: List[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            unique.append(token)
        return unique

    def _bucket(self, world_state: WorldState, path: str, value: float) -> Optional[str]:
        stats = world_state.stats_for(path)
        lo = safe_float(stats.get("min"), value)
        hi = safe_float(stats.get("max"), value)
        span = hi - lo
        if span <= 1e-12:
            mid = "mid"
        else:
            ratio = (value - lo) / span
            if ratio < 0.33:
                mid = "low"
            elif ratio > 0.66:
                mid = "high"
            else:
                mid = "mid"
        delta = world_state.delta(path)
        if delta is not None and span > 1e-12:
            if delta > 0.12 * span:
                return "rising"
            if delta < -0.12 * span:
                return "falling"
        return mid

    def _entity_tokens(self, world_state: WorldState) -> List[str]:
        tokens: List[str] = []
        for collection, rows in getattr(world_state, "entities", {}).items():
            for row in rows:
                identifier = row_id(row)
                if not identifier:
                    continue
                tokens.append(f"entity:{collection}:{identifier}")
                if len(tokens) >= ENTITY_CAP:
                    return tokens
        return tokens

    def _overlay_tokens(self, results: Dict[str, Any]) -> List[str]:
        tokens, _impulses = self._overlay_mapped(results, None)
        return tokens

    def _overlay_mapped(
        self,
        results: Dict[str, Any],
        extra_events: Optional[Sequence[str]],
    ) -> Tuple[List[str], List[Any]]:
        haystack = " ".join(str(k) + str(v) for k, v in (results or {}).items())
        names: List[str] = []
        for event_name in self.affective_mapping:
            key = str(event_name)
            if key in haystack or f"event:{key}" in haystack:
                names.append(key)
        for name in extra_events or ():
            text = str(name).strip()
            if text:
                names.append(text)
        tokens: List[str] = []
        impulses: List[Any] = []
        fired: set = set()
        for event_name in names:
            if event_name in fired:
                continue
            fired.add(event_name)
            entry = self.affective_mapping.get(event_name)
            if not isinstance(entry, dict):
                continue
            tokens.extend(self._tokens_for_mapped_event(event_name, entry))
            impulses.append(self._impulse_for_mapped_event(entry))
        return tokens, impulses

    def _tokens_for_mapped_event(self, event_name: str, entry: dict) -> List[str]:
        return mapped_event_tokens(event_name, entry)

    def _impulse_for_mapped_event(self, entry: dict) -> EmotionalImpulse:
        vector: Dict[str, float] = {}
        for axis in AXES:
            if axis not in entry or entry.get(axis) is None:
                continue
            vector[axis] = clamp(safe_float(entry.get(axis), 0.0), -1.0, 1.0)
        intensity = min(
            clamp(safe_float(entry.get("intensity"), 0.35), 0.0, 1.0),
            MAX_IMPULSE_INTENSITY,
        )
        return EmotionalImpulse(vector=vector, intensity=intensity, source="external")
