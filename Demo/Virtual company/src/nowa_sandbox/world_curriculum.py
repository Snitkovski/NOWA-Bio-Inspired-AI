"""Authorable multi-quarter curriculum for the procurement sandbox lab."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from nowa_sandbox.procurement_world import (
    ProcurementWorld,
    ProcurementWorldConfig,
    SupplierOffer,
    VirtualProduct,
    VirtualSupplier,
    offer_key,
)


CURRICULUM_VERSION = 1
DEFAULT_MAX_CYCLES = 500


class CurriculumValidationError(ValueError):
    """Raised when a curriculum fails structural checks."""


def empty_quarter(
    *,
    budget: float = 100_000.0,
    products: Optional[Sequence[Mapping[str, Any]]] = None,
    suppliers: Optional[Sequence[Mapping[str, Any]]] = None,
    offers: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "budget": float(budget),
        "products": [dict(r) for r in (products or [])],
        "suppliers": [dict(r) for r in (suppliers or [])],
        "offers": [dict(r) for r in (offers or [])],
    }


def default_template_quarter(*, budget: float = 100_000.0) -> Dict[str, Any]:
    """Minimal editable starter quarter (1 product, 1 supplier, 1 offer)."""
    return empty_quarter(
        budget=budget,
        products=[
            {
                "product_id": "product_001",
                "base_demand_per_day": 10.0,
                "demand_volatility": 0.15,
                "holding_cost_per_unit": 1.0,
                "stockout_penalty_per_unit": 10.0,
                "current_stock": 200.0,
                "reorder_point": 80.0,
            }
        ],
        suppliers=[
            {
                "supplier_id": "supplier_001",
                "reputation": 0.5,
                "is_defaulted": False,
            }
        ],
        offers=[
            {
                "product_id": "product_001",
                "supplier_id": "supplier_001",
                "unit_price": 1.0,
                "lead_time_days": 5,
                "reliability": 0.9,
                "price_volatility": 0.05,
            }
        ],
    )


def validate_quarter(spec: Mapping[str, Any], *, quarter_index: int = 1) -> List[str]:
    """Return a list of validation error strings (empty = ok)."""
    errors: List[str] = []
    label = f"Q{quarter_index}"
    products = list(spec.get("products") or [])
    suppliers = list(spec.get("suppliers") or [])
    offers = list(spec.get("offers") or [])

    if not products:
        errors.append(f"{label}: need at least one product")
    if not suppliers:
        errors.append(f"{label}: need at least one supplier")
    if not offers:
        errors.append(f"{label}: need at least one offer")

    product_ids = set()
    for row in products:
        if not isinstance(row, Mapping):
            errors.append(f"{label}: product row must be an object")
            continue
        pid = str(row.get("product_id") or "").strip()
        if not pid:
            errors.append(f"{label}: product missing product_id")
            continue
        if pid in product_ids:
            errors.append(f"{label}: duplicate product_id {pid!r}")
        product_ids.add(pid)

    supplier_ids = set()
    for row in suppliers:
        if not isinstance(row, Mapping):
            errors.append(f"{label}: supplier row must be an object")
            continue
        sid = str(row.get("supplier_id") or "").strip()
        if not sid:
            errors.append(f"{label}: supplier missing supplier_id")
            continue
        if sid in supplier_ids:
            errors.append(f"{label}: duplicate supplier_id {sid!r}")
        supplier_ids.add(sid)

    seen_pairs = set()
    for row in offers:
        if not isinstance(row, Mapping):
            errors.append(f"{label}: offer row must be an object")
            continue
        pid = str(row.get("product_id") or "").strip()
        sid = str(row.get("supplier_id") or "").strip()
        if not pid or not sid:
            errors.append(f"{label}: offer needs product_id and supplier_id")
            continue
        if pid not in product_ids:
            errors.append(f"{label}: offer references unknown product {pid!r}")
        if sid not in supplier_ids:
            errors.append(f"{label}: offer references unknown supplier {sid!r}")
        pair = offer_key(pid, sid)
        if pair in seen_pairs:
            errors.append(f"{label}: duplicate offer for {pid!r} / {sid!r}")
        seen_pairs.add(pair)

    return errors


class WorldCurriculum:
    """Ordered quarters 1..N; each quarter is a full products/suppliers/offers snap."""

    def __init__(self, quarters: Optional[Mapping[int, Mapping[str, Any]]] = None):
        self._quarters: Dict[int, Dict[str, Any]] = {}
        if quarters:
            for key, value in quarters.items():
                self._quarters[int(key)] = copy.deepcopy(dict(value))

    @classmethod
    def from_template(cls, *, n_quarters: int = 1, budget: float = 100_000.0) -> "WorldCurriculum":
        cur = cls()
        for q in range(1, max(1, int(n_quarters)) + 1):
            cur.set_quarter(q, default_template_quarter(budget=budget))
        return cur

    @property
    def n_quarters(self) -> int:
        if not self._quarters:
            return 0
        return max(self._quarters.keys())

    def quarter_indices(self) -> List[int]:
        return sorted(self._quarters.keys())

    def get_quarter(self, quarter_index: int) -> Dict[str, Any]:
        q = int(quarter_index)
        if q not in self._quarters:
            raise KeyError(f"curriculum has no quarter {q}")
        return copy.deepcopy(self._quarters[q])

    def set_quarter(self, quarter_index: int, spec: Mapping[str, Any]) -> None:
        q = int(quarter_index)
        if q < 1:
            raise ValueError("quarter_index must be >= 1")
        self._quarters[q] = empty_quarter(
            budget=float(spec.get("budget", 100_000.0)),
            products=spec.get("products") or [],
            suppliers=spec.get("suppliers") or [],
            offers=spec.get("offers") or [],
        )

    def add_quarter(
        self,
        spec: Optional[Mapping[str, Any]] = None,
        *,
        copy_from: Optional[int] = None,
    ) -> int:
        """Append quarter N+1; optionally copy from an existing quarter."""
        new_q = self.n_quarters + 1
        if copy_from is not None:
            self.set_quarter(new_q, self.get_quarter(int(copy_from)))
        elif spec is not None:
            self.set_quarter(new_q, spec)
        else:
            self.set_quarter(new_q, default_template_quarter())
        return new_q

    def remove_quarter(self, quarter_index: int) -> None:
        q = int(quarter_index)
        if q not in self._quarters:
            return
        del self._quarters[q]
        # Reindex remaining to stay contiguous 1..N
        remaining = [self._quarters[k] for k in sorted(self._quarters.keys())]
        self._quarters = {i + 1: copy.deepcopy(v) for i, v in enumerate(remaining)}

    def duplicate_quarter(self, quarter_index: int) -> int:
        return self.add_quarter(copy_from=int(quarter_index))

    def validate(self) -> List[str]:
        if not self._quarters:
            return ["curriculum needs at least one quarter"]
        expected = set(range(1, self.n_quarters + 1))
        if set(self._quarters.keys()) != expected:
            return [
                f"quarters must be contiguous 1..{self.n_quarters}, "
                f"got {sorted(self._quarters.keys())}"
            ]
        errors: List[str] = []
        for q in self.quarter_indices():
            errors.extend(validate_quarter(self._quarters[q], quarter_index=q))
        return errors

    def ensure_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise CurriculumValidationError("; ".join(errors))

    def curriculum_quarter_for_step(self, global_index: int) -> Tuple[int, int]:
        """Map global training step i (1-based) → (curriculum_q, cycle)."""
        n = self.n_quarters
        if n < 1:
            raise CurriculumValidationError("empty curriculum")
        i = max(1, int(global_index))
        curriculum_q = ((i - 1) % n) + 1
        cycle = ((i - 1) // n) + 1
        return curriculum_q, cycle

    def build_world(
        self,
        curriculum_quarter: int,
        *,
        days_per_quarter: int = 90,
        seed: Optional[int] = None,
        persistent_suppliers: bool = False,
        demand_shock_probability: Optional[float] = None,
        supplier_default_probability: Optional[float] = None,
        base_config: Optional[ProcurementWorldConfig] = None,
    ) -> ProcurementWorld:
        spec = self.get_quarter(curriculum_quarter)
        shock = demand_shock_probability
        default_p = supplier_default_probability
        if base_config is not None:
            if shock is None:
                shock = base_config.demand_shock_probability
            if default_p is None:
                default_p = base_config.supplier_default_probability
            if seed is None:
                seed = base_config.seed
        return ProcurementWorld.from_quarter_spec(
            spec,
            days_per_quarter=days_per_quarter,
            seed=seed,
            persistent_suppliers=persistent_suppliers,
            demand_shock_probability=shock,
            supplier_default_probability=default_p,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": CURRICULUM_VERSION,
            "quarters": {
                str(q): copy.deepcopy(self._quarters[q])
                for q in self.quarter_indices()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WorldCurriculum":
        raw = data.get("quarters") or {}
        quarters: Dict[int, Dict[str, Any]] = {}
        if isinstance(raw, Mapping):
            for key, value in raw.items():
                quarters[int(key)] = dict(value)
        elif isinstance(raw, list):
            for i, value in enumerate(raw, start=1):
                quarters[i] = dict(value)
        return cls(quarters)

    def save_json(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return out

    @classmethod
    def load_json(cls, path: str | Path) -> "WorldCurriculum":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise CurriculumValidationError("curriculum JSON must be an object")
        return cls.from_dict(data)


def quarter_spec_from_world(world: ProcurementWorld) -> Dict[str, Any]:
    """Serialize a live world into a curriculum quarter payload."""
    offers = []
    for offer in world.offers.values():
        offers.append(asdict(offer) if hasattr(offer, "__dataclass_fields__") else dict(
            product_id=offer.product_id,
            supplier_id=offer.supplier_id,
            unit_price=offer.unit_price,
            lead_time_days=offer.lead_time_days,
            reliability=offer.reliability,
            price_volatility=offer.price_volatility,
        ))
    products = []
    for p in world.products.values():
        products.append(
            {
                "product_id": p.product_id,
                "base_demand_per_day": p.base_demand_per_day,
                "demand_volatility": p.demand_volatility,
                "holding_cost_per_unit": p.holding_cost_per_unit,
                "stockout_penalty_per_unit": p.stockout_penalty_per_unit,
                "current_stock": p.current_stock,
                "reorder_point": p.reorder_point,
            }
        )
    suppliers = []
    for s in world.suppliers.values():
        suppliers.append(
            {
                "supplier_id": s.supplier_id,
                "reputation": s.reputation,
                "is_defaulted": s.is_defaulted,
                "reliability": s.reliability,
                "base_price_multiplier": s.base_price_multiplier,
                "price_volatility": s.price_volatility,
                "lead_time_days": s.lead_time_days,
            }
        )
    return empty_quarter(
        budget=float(world.budget),
        products=products,
        suppliers=suppliers,
        offers=offers,
    )


__all__ = [
    "CURRICULUM_VERSION",
    "DEFAULT_MAX_CYCLES",
    "CurriculumValidationError",
    "WorldCurriculum",
    "default_template_quarter",
    "empty_quarter",
    "quarter_spec_from_world",
    "validate_quarter",
]
