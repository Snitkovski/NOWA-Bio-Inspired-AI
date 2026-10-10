"""SchemaBinder — spinal cord: bind a muscle pose from schema + proprioception.

Replaces MotorAdapter. There is no per-role Python here (spec §6.4 / P5 / P11):
arguments come from JSON Schema, WorldState, the field lexicon, rank_weights
from A(t), and a read-only hippocampus glance. Failures return None.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ._compat import clamp, is_number, safe_float
from .field_lexicon import (
    ROLE_COST,
    ROLE_ID,
    ROLE_QUANTITY,
    ROLE_RELIABILITY,
    ROLE_STATUS,
    ROLE_TIME,
    classify_field,
    merge_aliases,
    tokenize,
)
from .mcp_capability import MCPCapability
from .world_state import WorldState, is_id_like_key, row_id

SKIP_ENVELOPE_KEYS = frozenset({"status", "reason", "tool_id", "error", "ok"})
_QTY_PREFERRED_LEAVES = ("suggested_qty", "remaining_capacity", "qty")


def _is_nonpositive_quantity(role: Optional[str], name: str, value: Any) -> bool:
    """True when a quantity-typed field resolved to 0 / negative (skip for a better match)."""
    if role != ROLE_QUANTITY and str(name).lower() not in {"qty", "quantity"}:
        return False
    if not is_number(value):
        return False
    return safe_float(value) <= 0


def _schema_object(schema: Any) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    if schema.get("type") == "object" or "properties" in schema or "required" in schema:
        return schema
    return schema


def _properties(schema: Dict[str, Any]) -> Dict[str, Any]:
    props = schema.get("properties")
    return dict(props) if isinstance(props, dict) else {}


def _required(schema: Dict[str, Any], properties: Dict[str, Any]) -> List[str]:
    raw = schema.get("required")
    if isinstance(raw, list):
        return [str(name) for name in raw if str(name) in properties]
    return []


def _prop_schema(properties: Dict[str, Any], name: str) -> Dict[str, Any]:
    entry = properties.get(name)
    return dict(entry) if isinstance(entry, dict) else {}


def _prop_types(prop: Dict[str, Any]) -> List[str]:
    raw = prop.get("type")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if raw is not None:
        return [str(raw)]
    return []


def _is_id_typed(prop: Dict[str, Any], name: str) -> bool:
    types = _prop_types(prop)
    if any(t in ("string", "integer") for t in types) or not types:
        role = classify_field(name)
        return role in (ROLE_ID, None) or is_id_like_key(name)
    return False


def _enum_values(prop: Dict[str, Any]) -> Optional[List[Any]]:
    values = prop.get("enum")
    if isinstance(values, list) and values:
        return list(values)
    return None


def _z_scores(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    n = float(len(values))
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance)
    if std < 1e-12:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def _row_role_value(row: Dict[str, Any], role: str, aliases: Optional[dict]) -> Optional[float]:
    if not isinstance(row, dict):
        return None
    for key, value in row.items():
        if classify_field(str(key), aliases) != role:
            continue
        if is_number(value):
            return safe_float(value)
        if isinstance(value, dict):
            nested = _row_role_value(value, role, aliases)
            if nested is not None:
                return nested
    return None


def _experience_tokens(hippocampus: Any) -> List[Tuple[str, float]]:
    """Read-only (path tokens, reward) pairs. Never calls activate()."""
    try:
        raw = getattr(hippocampus, "experiences", None)
    except Exception:
        return []
    if not isinstance(raw, (list, tuple)):
        return []
    out: List[Tuple[str, float]] = []
    for exp in raw:
        reward = safe_float(getattr(exp, "reward", 0.0) if not isinstance(exp, dict) else exp.get("reward", 0.0))
        for token in _tokens_from_experience(exp):
            out.append((token, reward))
    return out


def _tokens_from_experience(exp: Any) -> List[str]:
    if exp is None:
        return []
    if isinstance(exp, str):
        return [exp]
    collected: List[str] = []
    path = exp.get("path") if isinstance(exp, dict) else getattr(exp, "path", None)
    events = exp.get("events") if isinstance(exp, dict) else getattr(exp, "events", None)
    if events is not None:
        collected.extend(_tokens_from_events(events))
    collected.extend(_tokens_from_path(path))
    return collected


def _tokens_from_path(path: Any) -> List[str]:
    if path is None:
        return []
    if isinstance(path, str):
        return [path]
    if isinstance(path, (list, tuple)):
        return _tokens_from_events(path)
    events = getattr(path, "events", None)
    if events is not None:
        return _tokens_from_events(events)
    return [str(path)]


def _tokens_from_events(events: Any) -> List[str]:
    if events is None:
        return []
    if isinstance(events, str):
        return [events]
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
        label = getattr(event, "label", None) or getattr(event, "name", None)
        tokens.append(str(label) if label is not None else str(event))
    return tokens


def _action_mentions_id(tokens: Iterable[str], tool_id: str, entity_id: str) -> bool:
    action_mark = f"action:{tool_id}"
    id_marks = (str(entity_id), f"entity:{entity_id}", f"id:{entity_id}")
    has_action = False
    has_id = False
    for token in tokens:
        text = str(token)
        if text == action_mark or text.endswith(f":{tool_id}") or tool_id in text:
            has_action = True
        if any(mark == text or mark in text for mark in id_marks):
            has_id = True
    return has_action and has_id


def _seen_ids_for_tool(hippocampus: Any, tool_id: str) -> set:
    seen = set()
    for token, _reward in _experience_tokens(hippocampus):
        text = str(token)
        if tool_id not in text and f"action:{tool_id}" != text:
            continue
        for part in text.replace(":", " ").replace("/", " ").split():
            if part and part not in ("action", "entity", "mcp") and part != tool_id:
                seen.add(part)
    # Also scan whole experiences for entity tokens alongside this action.
    try:
        raw = getattr(hippocampus, "experiences", None) or []
    except Exception:
        raw = []
    for exp in raw:
        tokens = _tokens_from_experience(exp)
        joined = " ".join(tokens)
        if tool_id not in joined and f"action:{tool_id}" not in joined:
            continue
        for token in tokens:
            text = str(token)
            if text.startswith("entity:") or text.startswith("id:"):
                seen.add(text.split(":", 1)[-1])
    return seen


def _past_reward(hippocampus: Any, tool_id: str, entity_id: str) -> float:
    rewards: List[float] = []
    try:
        raw = getattr(hippocampus, "experiences", None) or []
    except Exception:
        raw = []
    for exp in raw:
        tokens = _tokens_from_experience(exp)
        if not _action_mentions_id(tokens, tool_id, entity_id) and str(entity_id) not in tokens:
            # Accept experiences that mention both the tool action and the id.
            joined = " ".join(str(t) for t in tokens)
            if tool_id not in joined or str(entity_id) not in joined:
                continue
        reward = safe_float(getattr(exp, "reward", 0.0) if not isinstance(exp, dict) else exp.get("reward", 0.0))
        rewards.append(reward)
    if not rewards:
        return 0.0
    return clamp(sum(rewards) / float(len(rewards)), -1.0, 1.0)


# Property stem → collection-name hints. Universal inventory/vendor vocabulary,
# not a procurement adapter: ``sku`` binds to a stock-like collection even when
# token overlap with ``stock`` is zero.
_COLLECTION_HINTS: Dict[str, Tuple[str, ...]] = {
    "sku": ("stock", "skus", "items", "products", "inventory"),
    "item": ("items", "stock", "products"),
    "product": ("products", "stock", "items"),
    "supplier": ("suppliers", "vendors", "partners"),
    "vendor": ("vendors", "suppliers"),
    "order": ("orders",),
    "customer": ("customers", "clients"),
    "account": ("accounts",),
}


_ID_SUFFIX_TOKENS = frozenset({"id", "uuid", "guid", "code", "key", "ref", "number"})


def _property_stem(name: str) -> str:
    tokens = list(tokenize(name))
    if not tokens:
        return str(name or "").strip().lower()
    if len(tokens) > 1 and tokens[-1] in _ID_SUFFIX_TOKENS:
        return "_".join(tokens[:-1])
    return tokens[0]


def _name_overlap(left: str, right: str) -> int:
    a = set(tokenize(left))
    b = set(tokenize(right))
    if a & b:
        return 2
    score = 0
    for x in a:
        for y in b:
            if min(len(x), len(y)) < 3:
                continue
            if x in y or y in x:
                score = max(score, 1)
    return score


class SchemaBinder:
    """Bind JSON-Schema required/optional properties onto a WorldState snapshot."""

    def bind(
        self,
        capability: MCPCapability,
        world_state: WorldState,
        rank_weights: Optional[Dict[str, float]] = None,
        hippocampus: Any = None,
        param_bindings: Optional[Dict[str, Any]] = None,
        field_aliases: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            return self._bind(
                capability,
                world_state,
                dict(rank_weights or {}),
                hippocampus,
                dict(param_bindings or {}),
                field_aliases,
            )
        except Exception:
            return None

    def _bind(
        self,
        capability: MCPCapability,
        world_state: WorldState,
        weights: Dict[str, float],
        hippocampus: Any,
        param_bindings: Dict[str, Any],
        field_aliases: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        schema = _schema_object(getattr(capability, "input_schema", None) or {})
        properties = _properties(schema)
        if not properties and not schema.get("required"):
            return {}

        required = _required(schema, properties)
        params: Dict[str, Any] = {}
        aliases = field_aliases
        tool_id = str(getattr(capability, "tool_id", "") or "")

        for name in required:
            value = self._bind_property(
                name=name,
                prop=_prop_schema(properties, name),
                world_state=world_state,
                weights=weights,
                hippocampus=hippocampus,
                param_bindings=param_bindings,
                aliases=aliases,
                tool_id=tool_id,
                bound=params,
                required=True,
            )
            if value is None:
                return None
            params[name] = value

        for name, prop in properties.items():
            if name in params:
                continue
            value = self._bind_property(
                name=name,
                prop=_prop_schema(properties, name) if not isinstance(prop, dict) else prop,
                world_state=world_state,
                weights=weights,
                hippocampus=hippocampus,
                param_bindings=param_bindings,
                aliases=aliases,
                tool_id=tool_id,
                bound=params,
                required=False,
            )
            if value is not None:
                params[name] = value
        return params

    def _bind_property(
        self,
        name: str,
        prop: Dict[str, Any],
        world_state: WorldState,
        weights: Dict[str, float],
        hippocampus: Any,
        param_bindings: Dict[str, Any],
        aliases: Optional[Dict[str, Any]],
        tool_id: str,
        bound: Dict[str, Any],
        required: bool,
    ) -> Any:
        enum_values = _enum_values(prop)
        role = classify_field(name, aliases)

        explicit = self._explicit_binding(name, param_bindings, world_state)
        if explicit is not None:
            return self._coerce(explicit, prop, enum_values)

        exact = self._exact_name(name, world_state)
        if exact is not None and not _is_nonpositive_quantity(role, name, exact):
            return self._coerce(exact, prop, enum_values)

        if enum_values:
            picked = self._rank_enum(enum_values, weights)
            if picked is not None:
                return picked

        if role and role != ROLE_ID:
            scalar = self._best_scalar_for_role(world_state, role, aliases, bound)
            if scalar is not None:
                return self._coerce(scalar, prop, enum_values)

        if _is_id_typed(prop, name) or role == ROLE_ID:
            entity_value = self._pick_entity_id(
                name, world_state, weights, hippocampus, aliases, tool_id, bound
            )
            if entity_value is not None:
                return self._coerce(entity_value, prop, enum_values)

        if "default" in prop:
            return self._coerce(prop.get("default"), prop, enum_values)

        if not required:
            return None
        return None

    def _explicit_binding(
        self,
        name: str,
        param_bindings: Dict[str, Any],
        world_state: WorldState,
    ) -> Any:
        spec = param_bindings.get(name)
        if spec is None:
            return None
        if isinstance(spec, dict):
            path = spec.get("path") or spec.get("jsonpath") or spec.get("from")
        else:
            path = spec
        if not path:
            return None
        return world_state.resolve_path(str(path))

    def _exact_name(self, name: str, world_state: WorldState) -> Any:
        if name in world_state.scalars:
            return world_state.scalars[name]
        for path, value in world_state.scalars.items():
            if path.rsplit(".", 1)[-1] == name:
                return value
        for envelope in world_state.results.values():
            if not isinstance(envelope, dict):
                continue
            if name in envelope and name not in SKIP_ENVELOPE_KEYS:
                value = envelope[name]
                if not isinstance(value, (dict, list)):
                    return value
        return None

    def _best_scalar_for_role(
        self,
        world_state: WorldState,
        role: str,
        aliases: Optional[Dict[str, Any]],
        bound: Dict[str, Any],
    ) -> Any:
        candidates: List[Tuple[str, float]] = []
        for path, value in world_state.scalars.items():
            leaf = path.rsplit(".", 1)[-1]
            if classify_field(leaf, aliases) == role:
                candidates.append((path, value))
        if not candidates:
            return None
        # Prefer a scalar whose path mentions an already bound id (sku, supplier).
        bound_ids = {str(v) for v in bound.values() if v is not None and not isinstance(v, (dict, list))}
        if bound_ids:
            for path, value in candidates:
                if any(item and item in path for item in bound_ids):
                    if role == ROLE_QUANTITY and is_number(value) and safe_float(value) <= 0:
                        continue
                    return value
        if role == ROLE_QUANTITY:
            def leaf(path: str) -> str:
                return path.rsplit(".", 1)[-1].lower()

            for leaf_name in _QTY_PREFERRED_LEAVES:
                hits = [
                    item for item in candidates
                    if leaf(item[0]) == leaf_name
                    and is_number(item[1])
                    and safe_float(item[1]) > 0
                ]
                if hits:
                    return min(hits, key=lambda item: item[1])[1]
            positive = [
                item for item in candidates
                if is_number(item[1]) and safe_float(item[1]) > 0
            ]
            if positive:
                return min(positive, key=lambda item: item[1])[1]
            return None
        return candidates[0][1]

    def _pick_entity_id(
        self,
        name: str,
        world_state: WorldState,
        weights: Dict[str, float],
        hippocampus: Any,
        aliases: Optional[Dict[str, Any]],
        tool_id: str,
        bound: Dict[str, Any],
    ) -> Any:
        collections = self._collections_for_property(name, world_state)
        if not collections:
            return None
        rows: List[Dict[str, Any]] = []
        for _coll_name, coll_rows in collections:
            rows.extend(coll_rows)
        if not rows:
            return None
        ranked = self._rank_rows(rows, weights, hippocampus, aliases, tool_id)
        if not ranked:
            return None
        winner = ranked[0]
        identifier = row_id(winner, preferred_key=name)
        if identifier is None:
            identifier = row_id(winner)
        return identifier

    def _collections_for_property(
        self,
        name: str,
        world_state: WorldState,
    ) -> List[Tuple[str, List[Dict[str, Any]]]]:
        stem = _property_stem(name)
        hints = _COLLECTION_HINTS.get(stem, ())
        scored: List[Tuple[int, str, List[Dict[str, Any]]]] = []
        for coll_name, rows in world_state.entities.items():
            if not rows:
                continue
            overlap = _name_overlap(name, coll_name)
            stem_overlap = _name_overlap(stem, coll_name)
            field_hit = 0
            for row in rows[:8]:
                if name in row or stem in row or any(is_id_like_key(k) for k in row):
                    field_hit = 1
                    break
            hint_hit = 0
            coll_lower = str(coll_name).lower()
            for hint in hints:
                if hint in coll_lower or _name_overlap(hint, coll_name):
                    hint_hit = 8
                    break
            score = overlap * 10 + stem_overlap * 6 + field_hit + hint_hit
            scored.append((score, coll_name, rows))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return []
        best = scored[0][0]
        if best <= 0:
            return [(item[1], item[2]) for item in scored]
        return [(item[1], item[2]) for item in scored if item[0] >= best]

    def _rank_rows(
        self,
        rows: List[Dict[str, Any]],
        weights: Dict[str, float],
        hippocampus: Any,
        aliases: Optional[Dict[str, Any]],
        tool_id: str,
    ) -> List[Dict[str, Any]]:
        cost_aversion = safe_float(weights.get("cost_aversion"), 0.5)
        speed_seek = safe_float(weights.get("speed_seek"), 0.5)
        reliability_w = safe_float(weights.get("reliability"), 0.5)
        novelty_seek = safe_float(weights.get("novelty_seek"), 0.5)
        assertiveness = safe_float(weights.get("assertiveness"), 0.5)
        seen = _seen_ids_for_tool(hippocampus, tool_id) if hippocampus is not None else set()

        costs = [_row_role_value(row, ROLE_COST, aliases) for row in rows]
        times = [_row_role_value(row, ROLE_TIME, aliases) for row in rows]
        rels = [_row_role_value(row, ROLE_RELIABILITY, aliases) for row in rows]
        qtys = [_row_role_value(row, ROLE_QUANTITY, aliases) for row in rows]

        def filled_z(values: List[Optional[float]]) -> List[float]:
            present = [v for v in values if v is not None]
            z_present = _z_scores(present) if present else []
            iterator = iter(z_present)
            out: List[float] = []
            for value in values:
                out.append(next(iterator) if value is not None else 0.0)
            return out

        z_cost = filled_z(costs)
        z_time = filled_z(times)
        z_rel = filled_z(rels)
        z_qty = filled_z(qtys)

        scored: List[Tuple[float, int, Dict[str, Any]]] = []
        for index, row in enumerate(rows):
            identifier = row_id(row) or ""
            unseen = 1.0 if identifier and identifier not in seen else 0.0
            memory = _past_reward(hippocampus, tool_id, identifier) if hippocampus is not None else 0.0
            score = (
                -cost_aversion * z_cost[index]
                - speed_seek * z_time[index]
                + reliability_w * z_rel[index]
                + novelty_seek * unseen
                + memory
                + assertiveness * z_qty[index]
            )
            scored.append((score, index, row))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored]

    def _rank_enum(self, values: List[Any], weights: Dict[str, float]) -> Any:
        if len(values) == 1:
            return values[0]
        novelty = safe_float(weights.get("novelty_seek"), 0.5)
        # Prefer earlier enum values unless novelty is high (then later/unseen-ish).
        if novelty >= 0.65:
            return values[-1]
        return values[0]

    def _coerce(self, value: Any, prop: Dict[str, Any], enum_values: Optional[List[Any]]) -> Any:
        if value is None:
            return None
        types = _prop_types(prop)
        coerced = value
        if "integer" in types and is_number(value):
            coerced = int(round(safe_float(value)))
        elif "number" in types and is_number(value):
            coerced = safe_float(value)
        elif "string" in types and not isinstance(value, (dict, list)):
            coerced = str(value)
        elif "boolean" in types:
            coerced = bool(value)
        if "minimum" in prop and is_number(coerced):
            coerced = max(safe_float(coerced), safe_float(prop.get("minimum")))
        if "maximum" in prop and is_number(coerced):
            coerced = min(safe_float(coerced), safe_float(prop.get("maximum")))
        if enum_values is not None and coerced not in enum_values:
            as_str = str(coerced)
            for item in enum_values:
                if str(item) == as_str:
                    return item
            return None
        return coerced
