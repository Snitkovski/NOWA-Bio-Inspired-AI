"""WorldState — proprioception: the last sensory snapshot, with no domain types.

Spec §6.2. There is no ``Supplier`` class here and never will be: a READ organ
returns JSON, and this module turns that JSON into three flat, universal
shapes — envelopes, entity collections, and numeric scalars — plus running
statistics so the encoder can bucket a value as low/mid/high/rising/falling.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ._compat import is_number, safe_float
from .mcp_client import tool_name_from_tool_id

ID_LIKE_KEYS = frozenset(
    {"id", "uuid", "guid", "code", "sku", "supplier_id", "product_id", "number", "ref"}
)
ID_LIKE_SUFFIXES = ("_id", "_uuid", "_guid", "_code", "_sku", "_ref", "_number")

DEFAULT_MAX_DEPTH = 6


def is_id_like_key(key: Any) -> bool:
    """Spec §6.2: id, uuid, code, sku, supplier_id, product_id, number.

    ``number`` counts as an identifier, ``amount`` never does — that is the
    one explicit exception in the spec table.
    """
    lowered = str(key or "").strip().lower()
    if not lowered or lowered == "amount":
        return False
    if lowered in ID_LIKE_KEYS:
        return True
    return any(lowered.endswith(suffix) for suffix in ID_LIKE_SUFFIXES)


def row_id(row: Any, preferred_key: Optional[str] = None) -> Optional[str]:
    """Best identifier of an entity row, as a string."""
    if not isinstance(row, dict):
        return None
    if preferred_key and preferred_key in row:
        value = row[preferred_key]
        if value is not None and not isinstance(value, (dict, list)):
            return str(value)
    for key in ("id", "sku", "code", "uuid", "guid", "number", "ref"):
        if key in row and row[key] is not None and not isinstance(row[key], (dict, list)):
            return str(row[key])
    for key, value in row.items():
        if is_id_like_key(key) and value is not None and not isinstance(value, (dict, list)):
            return str(value)
    return None


class WorldState:
    """Last sensory snapshot. No domain types."""

    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH) -> None:
        self.results: Dict[str, Dict[str, Any]] = {}
        self.entities: Dict[str, List[Dict[str, Any]]] = {}
        self.scalars: Dict[str, float] = {}
        self.updated_at: Dict[str, float] = {}
        self.running_stats: Dict[str, Dict[str, float]] = {}
        self.max_depth = max(1, int(max_depth))
        self._collection_owner: Dict[str, str] = {}

    def update_from_read(
        self,
        tool_id: str,
        envelope: dict,
        now: Optional[float] = None,
    ) -> None:
        """Absorb one READ organ result. Never raises on malformed payloads."""
        key = str(tool_id or "").strip() or "unknown_tool"
        payload = envelope if isinstance(envelope, dict) else {"status": "unknown", "value": envelope}
        timestamp = float(now) if now is not None else time.time()

        self.results[key] = dict(payload)
        self.updated_at[key] = timestamp

        leaf = tool_name_from_tool_id(key) or key
        collections: Dict[str, List[Dict[str, Any]]] = {}
        scalars: Dict[str, float] = {}
        try:
            self._walk(payload, "", leaf, key, 0, collections, scalars)
        except Exception:
            return

        self._retire_stale_collections(key, collections)
        for name, rows in collections.items():
            self.entities[name] = rows
            self._collection_owner[name] = key
        for path, value in scalars.items():
            self._update_scalar(path, value, timestamp)

    # --- reads -----------------------------------------------------------

    def collection_names(self) -> List[str]:
        return sorted(self.entities)

    def rows(self, collection: str) -> List[Dict[str, Any]]:
        return list(self.entities.get(str(collection), []))

    def stats_for(self, path: str) -> Dict[str, float]:
        return dict(self.running_stats.get(str(path), {}))

    def delta(self, path: str) -> Optional[float]:
        """Signed change of a scalar since the previous read, if known."""
        stats = self.running_stats.get(str(path))
        if not stats:
            return None
        previous = stats.get("prev")
        last = stats.get("last")
        if previous is None or last is None:
            return None
        return float(last) - float(previous)

    def scalars_by_leaf(self, leaf_name: str) -> List[Tuple[str, float]]:
        """All scalars whose final dotted segment equals ``leaf_name``."""
        wanted = str(leaf_name or "").strip().lower()
        if not wanted:
            return []
        found = [
            (path, value)
            for path, value in self.scalars.items()
            if path.rsplit(".", 1)[-1].lower() == wanted
        ]
        return sorted(found, key=lambda item: (item[0].count("."), item[0]))

    def resolve_path(self, path: str) -> Any:
        """Resolve a simple JSONPath-ish binding into this snapshot.

        Accepts ``$.scalars.stock.SKU1.qty``, ``scalars.stock.SKU1.qty``,
        ``entities.suppliers.0.supplier_id``, ``results.<tool_id>.status`` and
        the bare form ``stock.SKU1.qty``.
        """
        raw = str(path or "").strip()
        if raw.startswith("$"):
            raw = raw[1:]
        raw = raw.lstrip(".")
        if not raw:
            return None
        if raw in self.scalars:
            return self.scalars[raw]
        segments = [segment for segment in raw.split(".") if segment]
        if not segments:
            return None

        head = segments[0]
        tail = segments[1:]
        if head == "scalars":
            joined = ".".join(tail)
            if joined in self.scalars:
                return self.scalars[joined]
            return self._walk_container(self.scalars, tail)
        if head == "entities":
            return self._walk_container(self.entities, tail)
        if head == "results":
            return self._walk_container(self.results, tail)

        for envelope in self.results.values():
            found = self._walk_container(envelope, segments)
            if found is not None:
                return found
        return self._walk_container(self.entities, segments)

    # --- internals -------------------------------------------------------

    def _walk_container(self, container: Any, segments: Sequence[str]) -> Any:
        current = container
        for segment in segments:
            if isinstance(current, dict):
                if segment in current:
                    current = current[segment]
                    continue
                return None
            if isinstance(current, list):
                try:
                    index = int(segment)
                except (TypeError, ValueError):
                    return None
                if -len(current) <= index < len(current):
                    current = current[index]
                    continue
                return None
            return None
        return current

    def _walk(
        self,
        node: Any,
        prefix: str,
        leaf: str,
        tool_id: str,
        depth: int,
        collections: Dict[str, List[Dict[str, Any]]],
        scalars: Dict[str, float],
    ) -> None:
        if depth > self.max_depth:
            return
        if isinstance(node, dict):
            for raw_key, value in node.items():
                key = str(raw_key)
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, list):
                    rows = self._rows_from_list(value)
                    if rows is not None:
                        self._add_collection(collections, key, leaf, tool_id, rows)
                    for index, item in enumerate(value):
                        self._walk(
                            item, f"{path}.{index}", leaf, tool_id,
                            depth + 1, collections, scalars,
                        )
                    continue
                if isinstance(value, dict):
                    rows = self._rows_from_mapping(value)
                    if rows is not None:
                        self._add_collection(collections, key, leaf, tool_id, rows)
                    self._walk(value, path, leaf, tool_id, depth + 1, collections, scalars)
                    continue
                if is_number(value):
                    scalars[path] = safe_float(value)
            return
        if isinstance(node, list):
            for index, item in enumerate(node):
                child = f"{prefix}.{index}" if prefix else str(index)
                self._walk(item, child, leaf, tool_id, depth + 1, collections, scalars)

    @staticmethod
    def _rows_from_list(value: Sequence[Any]) -> Optional[List[Dict[str, Any]]]:
        if not value or not all(isinstance(item, dict) for item in value):
            return None
        if not any(any(is_id_like_key(key) for key in item) for item in value):
            return None
        return [dict(item) for item in value]

    @staticmethod
    def _rows_from_mapping(value: Dict[Any, Any]) -> Optional[List[Dict[str, Any]]]:
        """``{"SKU1": {"qty": 4}}`` is an entity collection keyed by id."""
        if not value or not all(isinstance(item, dict) for item in value.values()):
            return None
        rows: List[Dict[str, Any]] = []
        for raw_key, item in value.items():
            row = dict(item)
            row.setdefault("id", str(raw_key))
            rows.append(row)
        return rows

    def _add_collection(
        self,
        collections: Dict[str, List[Dict[str, Any]]],
        key: str,
        leaf: str,
        tool_id: str,
        rows: List[Dict[str, Any]],
    ) -> None:
        name = key
        owner = self._collection_owner.get(name)
        taken_by_other_tool = owner is not None and owner != tool_id
        if taken_by_other_tool or name in collections:
            name = f"{leaf}_{key}"
        collections[name] = rows

    def _retire_stale_collections(
        self,
        tool_id: str,
        fresh: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        stale = [
            name
            for name, owner in self._collection_owner.items()
            if owner == tool_id and name not in fresh
        ]
        for name in stale:
            self.entities.pop(name, None)
            self._collection_owner.pop(name, None)

    def _update_scalar(self, path: str, value: float, timestamp: float) -> None:
        numeric = safe_float(value)
        stats = self.running_stats.get(path)
        if stats is None:
            stats = {
                "count": 0.0,
                "mean": 0.0,
                "min": numeric,
                "max": numeric,
                "last": None,
                "prev": None,
                "updated_at": timestamp,
            }
            self.running_stats[path] = stats
        stats["prev"] = stats.get("last")
        stats["last"] = numeric
        stats["count"] = float(stats.get("count", 0.0)) + 1.0
        stats["mean"] = float(stats["mean"]) + (numeric - float(stats["mean"])) / stats["count"]
        stats["min"] = min(safe_float(stats.get("min", numeric), numeric), numeric)
        stats["max"] = max(safe_float(stats.get("max", numeric), numeric), numeric)
        stats["updated_at"] = timestamp
        self.scalars[path] = numeric
