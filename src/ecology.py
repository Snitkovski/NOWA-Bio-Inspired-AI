"""Resource-layer ecology for emergent population regulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


ECOLOGY_VERSION = "1.0"


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if casted != casted or casted in (float("inf"), float("-inf")):
        return float(fallback)
    return casted


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


@dataclass
class EcologyLayer:
    """
    Environment resource layer.

    The layer does not control agents; it only provides resource availability.
    """

    total_resources: float = 1000.0
    resource_regen_rate: float = 0.1
    resource_per_agent_base: float = 10.0
    current_resources: float = 1000.0

    def __post_init__(self) -> None:
        self.total_resources = max(0.0, _safe_float(self.total_resources, 1000.0))
        self.resource_regen_rate = max(0.0, _safe_float(self.resource_regen_rate, 0.1))
        self.resource_per_agent_base = max(1e-9, _safe_float(self.resource_per_agent_base, 10.0))
        self.current_resources = _clamp(
            _safe_float(self.current_resources, self.total_resources),
            0.0,
            self.total_resources,
        )

    def compute_resource_share(self, agent_count: int) -> float:
        """Compute per-agent resource share in [0, 1]."""
        count = max(0, _safe_int(agent_count, 0))
        if count == 0:
            return 1.0
        denominator = float(count) * self.resource_per_agent_base
        if denominator <= 0.0:
            return 1.0
        share = self.current_resources / denominator
        return _clamp(share, 0.0, 1.0)

    def consume(self, agent_count: int) -> float:
        """Apply one-step consumption + regeneration, then return resource share."""
        count = max(0, _safe_int(agent_count, 0))
        consumed = float(count) * self.resource_per_agent_base
        self.current_resources -= consumed
        self.current_resources += self.resource_regen_rate
        self.current_resources = _clamp(self.current_resources, 0.0, self.total_resources)
        return self.compute_resource_share(count)

    def snapshot(self) -> Dict[str, Any]:
        """Return current ecology snapshot."""
        return {
            "version": ECOLOGY_VERSION,
            "total_resources": float(self.total_resources),
            "resource_regen_rate": float(self.resource_regen_rate),
            "resource_per_agent_base": float(self.resource_per_agent_base),
            "current_resources": float(self.current_resources),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EcologyLayer":
        """Restore ecology layer from dictionary."""
        payload = data if isinstance(data, dict) else {}
        total_resources = _safe_float(payload.get("total_resources"), 1000.0)
        return cls(
            total_resources=total_resources,
            resource_regen_rate=_safe_float(payload.get("resource_regen_rate"), 0.1),
            resource_per_agent_base=_safe_float(payload.get("resource_per_agent_base"), 10.0),
            current_resources=_safe_float(payload.get("current_resources"), total_resources),
        )


__all__ = [
    "ECOLOGY_VERSION",
    "EcologyLayer",
]
