"""Unit tests for ProcurementMotorAdapter (spec v2.0 §2.1, R2, §14)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from nowa_sandbox.procurement_motor_adapter import (
    OrderParams,
    ProcurementMotorAdapter,
)


FIVE_ACTIONS = {
    "place_order_reliable_supplier",
    "place_order_cheap_supplier",
    "urgent_reorder",
    "diversify_supplier",
    "wait_and_monitor",
}


def _stock(
    pid="product_000",
    quantity=10.0,
    reorder_point=100.0,
    below=True,
    **extra,
):
    info = {
        "quantity": quantity,
        "reorder_point": reorder_point,
        "below_reorder_point": below,
    }
    info.update(extra)
    return {pid: info}


def _supplier(
    sid,
    reliability=0.5,
    reputation=0.5,
    is_defaulted=False,
    **extra,
):
    info = {
        "reliability": reliability,
        "reputation": reputation,
        "is_defaulted": is_defaulted,
    }
    info.update(extra)
    return sid, info


def _suppliers(*entries):
    return dict(entries)


def _budget(remaining=10_000.0, **extra):
    payload = {"remaining": remaining, "allocated": remaining, "spent": 0.0}
    payload.update(extra)
    return payload


def _exp_with_tokens(*tokens):
    events = [SimpleNamespace(label=t, name=t) for t in tokens]
    return SimpleNamespace(path=SimpleNamespace(events=events))


@pytest.fixture
def adapter():
    return ProcurementMotorAdapter()


@pytest.fixture
def hippocampus():
    return SimpleNamespace(experiences=[])


class TestPublicContract:

    def test_supplier_strategies_maps_five_action_types(self):
        mapping = ProcurementMotorAdapter.SUPPLIER_STRATEGIES
        assert set(mapping) == FIVE_ACTIONS
        assert mapping["wait_and_monitor"] is None
        assert mapping["place_order_reliable_supplier"] == "_select_most_reliable"
        assert mapping["place_order_cheap_supplier"] == "_select_cheapest"
        assert mapping["urgent_reorder"] == "_select_fastest"
        assert mapping["diversify_supplier"] == "_select_least_used"

    def test_resolve_returns_order_params(self, adapter, hippocampus):
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(),
            _suppliers(_supplier("supplier_000", reliability=0.9)),
            _budget(),
            hippocampus,
        )
        assert isinstance(result, OrderParams)
        assert result.supplier_id == "supplier_000"
        assert result.product_id == "product_000"
        assert result.qty > 0
        assert result.strategy == "place_order_reliable_supplier"
        assert 0.0 <= result.confidence <= 1.0


class TestR2CognitiveIsolation:

    def test_does_not_call_hippocampus_activate_or_cognitive_methods(
        self, adapter
    ):
        mock_hippocampus = MagicMock()
        mock_hippocampus.experiences = []

        stock_obs = {
            "product_000": {
                "quantity": 10,
                "reorder_point": 100,
                "below_reorder_point": True,
            }
        }
        supplier_obs = {
            "supplier_000": {
                "reliability": 0.9,
                "reputation": 0.8,
                "is_defaulted": False,
            }
        }

        for action in FIVE_ACTIONS:
            mock_hippocampus.reset_mock()
            mock_hippocampus.experiences = []
            adapter.resolve(
                action, stock_obs, supplier_obs, _budget(), mock_hippocampus
            )
            mock_hippocampus.activate.assert_not_called()
            mock_hippocampus.store.assert_not_called()
            mock_hippocampus.reinforce.assert_not_called()
            mock_hippocampus.step.assert_not_called()

    def test_least_used_reads_experiences_without_activate(self, adapter):
        mock_hippocampus = MagicMock()
        mock_hippocampus.experiences = [
            _exp_with_tokens("supplier:alpha", "action:place_order")
        ]
        suppliers = _suppliers(
            _supplier("alpha", reliability=0.9),
            _supplier("beta", reliability=0.1),
        )
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), mock_hippocampus
        )
        mock_hippocampus.activate.assert_not_called()
        assert result is not None
        assert result.supplier_id == "beta"


class TestNoAction:

    def test_wait_and_monitor_returns_none(self, adapter, hippocampus):
        result = adapter.resolve(
            "wait_and_monitor",
            _stock(),
            _suppliers(_supplier("s1", reliability=0.99)),
            _budget(),
            hippocampus,
        )
        assert result is None

    def test_unknown_action_returns_none(self, adapter, hippocampus):
        assert adapter.resolve(
            "invent_new_action", _stock(), _suppliers(_supplier("s1")),
            _budget(), hippocampus,
        ) is None

    def test_no_product_below_reorder_returns_none(self, adapter, hippocampus):
        stock = _stock(quantity=500, reorder_point=10, below=False)
        assert adapter.resolve(
            "urgent_reorder", stock, _suppliers(_supplier("s1")),
            _budget(), hippocampus,
        ) is None


class TestStrategies:

    def _rich_directory(self):
        return _suppliers(
            _supplier(
                "reliable_slow_pricey",
                reliability=0.99,
                reputation=0.4,
                base_price_multiplier=3.0,
                lead_time_days=12,
            ),
            _supplier(
                "cheap_ok",
                reliability=0.40,
                reputation=0.9,
                base_price_multiplier=0.8,
                lead_time_days=8,
            ),
            _supplier(
                "fast_mid",
                reliability=0.70,
                reputation=0.6,
                base_price_multiplier=1.5,
                lead_time_days=2,
            ),
        )

    def test_reliable_picks_highest_reliability(self, adapter, hippocampus):
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), self._rich_directory(), _budget(), hippocampus,
        )
        assert result.supplier_id == "reliable_slow_pricey"
        assert result.strategy == "place_order_reliable_supplier"

    def test_cheap_picks_lowest_base_price_multiplier(self, adapter, hippocampus):
        result = adapter.resolve(
            "place_order_cheap_supplier",
            _stock(), self._rich_directory(), _budget(), hippocampus,
        )
        assert result.supplier_id == "cheap_ok"

    def test_urgent_picks_shortest_lead_time(self, adapter, hippocampus):
        result = adapter.resolve(
            "urgent_reorder",
            _stock(), self._rich_directory(), _budget(), hippocampus,
        )
        assert result.supplier_id == "fast_mid"

    def test_diversify_picks_least_used(self, adapter):
        hippocampus = SimpleNamespace(
            experiences=[
                _exp_with_tokens("supplier:cheap_ok"),
                _exp_with_tokens("supplier:cheap_ok"),
                _exp_with_tokens("supplier:fast_mid"),
            ]
        )
        result = adapter.resolve(
            "diversify_supplier",
            _stock(), self._rich_directory(), _budget(), hippocampus,
        )
        assert result.supplier_id == "reliable_slow_pricey"

    def test_cheap_falls_back_to_reputation_without_price(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier("high_rep", reliability=0.2, reputation=0.95),
            _supplier("low_rep", reliability=0.9, reputation=0.10),
        )
        result = adapter.resolve(
            "place_order_cheap_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "low_rep"

    def test_urgent_falls_back_to_reputation_without_lead_time(
        self, adapter, hippocampus
    ):
        suppliers = _suppliers(
            _supplier("trusted", reliability=0.2, reputation=0.95),
            _supplier("unknown", reliability=0.9, reputation=0.10),
        )
        result = adapter.resolve(
            "urgent_reorder", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "trusted"


class TestUnavailableSuppliers:

    def test_all_defaulted_returns_none(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier("a", reliability=0.99, is_defaulted=True),
            _supplier("b", reliability=0.80, is_defaulted=True),
        )
        assert adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        ) is None

    def test_defaulted_supplier_is_skipped(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier("best_but_dead", reliability=0.99, is_defaulted=True),
            _supplier("alive", reliability=0.40, is_defaulted=False),
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result.supplier_id == "alive"

    def test_unavailable_status_is_filtered(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier("gone", reliability=0.99, status="unavailable"),
            _supplier("here", reliability=0.1),
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result.supplier_id == "here"

    def test_unavailable_product_offer_is_filtered(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier(
                "no_offer_for_product",
                reliability=0.99,
                offers={"other": {"unit_price": 1.0, "reliability": 0.99}},
            ),
            _supplier(
                "has_offer",
                reliability=0.20,
                offers={
                    "product_000": {
                        "unit_price": 4.0,
                        "reliability": 0.20,
                        "lead_time_days": 5,
                    }
                },
            ),
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result.supplier_id == "has_offer"

    def test_explicitly_unavailable_offer_is_skipped(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier(
                "blocked",
                reliability=0.99,
                offers={
                    "product_000": {
                        "unit_price": 1.0,
                        "reliability": 0.99,
                        "available": False,
                    }
                },
            ),
            _supplier(
                "open",
                reliability=0.3,
                offers={
                    "product_000": {
                        "unit_price": 5.0,
                        "reliability": 0.3,
                        "available": True,
                    }
                },
            ),
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result.supplier_id == "open"


class TestNestedOffers:

    def test_cheapest_uses_per_product_unit_price(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier(
                "s1",
                reliability=0.5,
                reputation=0.1,
                base_price_multiplier=0.1,
                offers={"product_000": {"unit_price": 9.0, "reliability": 0.5}},
            ),
            _supplier(
                "s2",
                reliability=0.5,
                reputation=0.9,
                base_price_multiplier=9.0,
                offers={"product_000": {"unit_price": 1.5, "reliability": 0.5}},
            ),
        )
        result = adapter.resolve(
            "place_order_cheap_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result.supplier_id == "s2"

    def test_fastest_uses_per_product_lead_time(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier(
                "slow",
                reputation=0.99,
                lead_time_days=1,
                offers={"product_000": {"lead_time_days": 20, "unit_price": 1.0}},
            ),
            _supplier(
                "quick",
                reputation=0.01,
                lead_time_days=30,
                offers={"product_000": {"lead_time_days": 2, "unit_price": 1.0}},
            ),
        )
        result = adapter.resolve(
            "urgent_reorder", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "quick"

    def test_list_shaped_offers_are_accepted(self, adapter, hippocampus):
        suppliers = _suppliers(
            _supplier(
                "listed",
                offers=[
                    {
                        "product_id": "product_000",
                        "unit_price": 2.0,
                        "reliability": 0.88,
                        "lead_time_days": 4,
                    }
                ],
            )
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            _stock(), suppliers, _budget(), hippocampus,
        )
        assert result is not None
        assert result.supplier_id == "listed"


class TestLeastUsedHippocampus:

    def test_counts_supplier_tokens_from_path_events(self, adapter):
        hippocampus = SimpleNamespace(
            experiences=[
                _exp_with_tokens("ctx", "supplier:s_used", "supplier:s_used"),
                _exp_with_tokens("supplier:s_used"),
            ]
        )
        suppliers = _suppliers(_supplier("s_used"), _supplier("s_fresh"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "s_fresh"

    def test_fallback_path_as_token_list(self, adapter):
        exp = SimpleNamespace(path=["event:x", "supplier:alpha", "result:accepted"])
        hippocampus = SimpleNamespace(experiences=[exp])
        suppliers = _suppliers(_supplier("alpha"), _supplier("beta"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "beta"

    def test_event_name_attribute_without_label(self, adapter):
        event = SimpleNamespace(name="supplier:only_a")
        hippocampus = SimpleNamespace(
            experiences=[SimpleNamespace(path=SimpleNamespace(events=[event]))]
        )
        suppliers = _suppliers(_supplier("only_a"), _supplier("only_b"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "only_b"

    def test_empty_experiences_still_picks_an_available_supplier(
        self, adapter, hippocampus
    ):
        suppliers = _suppliers(_supplier("only"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "only"

    def test_does_not_substring_match_shorter_supplier_id(self, adapter):
        hippocampus = SimpleNamespace(
            experiences=[_exp_with_tokens("supplier:s10")]
        )
        suppliers = _suppliers(_supplier("s1"), _supplier("s10"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "s1"


class TestBudgetCap:

    def test_qty_capped_to_remaining_budget_using_unit_price(
        self, adapter, hippocampus
    ):
        stock = _stock(base_demand_per_day=10.0)
        suppliers = _suppliers(
            _supplier("s1", reliability=0.9, unit_price=10.0)
        )
        result = adapter.resolve(
            "place_order_reliable_supplier",
            stock, suppliers, _budget(remaining=100.0), hippocampus,
        )
        assert result is not None
        assert result.qty == pytest.approx(10.0)
        assert result.qty * 10.0 <= 100.0 + 1e-9

    def test_qty_capped_using_nested_offer_price(self, adapter, hippocampus):
        stock = _stock(base_demand_per_day=50.0)
        suppliers = _suppliers(
            _supplier(
                "s1",
                offers={"product_000": {"unit_price": 25.0, "reliability": 0.9}},
            )
        )
        result = adapter.resolve(
            "urgent_reorder",
            stock, suppliers, _budget(remaining=100.0), hippocampus,
        )
        assert result is not None
        assert result.qty == pytest.approx(4.0)

    def test_zero_budget_returns_none(self, adapter, hippocampus):
        assert adapter.resolve(
            "urgent_reorder",
            _stock(),
            _suppliers(_supplier("s1", unit_price=1.0)),
            _budget(remaining=0.0),
            hippocampus,
        ) is None

    def test_cannot_afford_even_tenth_returns_none(self, adapter, hippocampus):
        assert adapter.resolve(
            "urgent_reorder",
            _stock(),
            _suppliers(_supplier("s1", unit_price=100.0)),
            _budget(remaining=1.0),
            hippocampus,
        ) is None

    def test_demand_coverage_uses_thirty_days(self, adapter, hippocampus):
        stock = _stock(base_demand_per_day=4.0)
        result = adapter.resolve(
            "urgent_reorder",
            stock,
            _suppliers(_supplier("s1", unit_price=1.0)),
            _budget(remaining=1_000_000.0),
            hippocampus,
        )
        assert result.qty == pytest.approx(120.0)

    def test_replenishment_point_triggers_order_above_reorder(
        self, adapter, hippocampus
    ):
        """A ROP below lead-time demand must not block a timely order."""
        stock = _stock(
            quantity=25.0,
            reorder_point=18.0,
            below=False,
            base_demand_per_day=6.0,
            replenishment_point=40.0,
            below_replenishment_point=True,
        )
        result = adapter.resolve(
            "urgent_reorder",
            stock,
            _suppliers(_supplier("s1", unit_price=1.0, lead_time_days=5)),
            _budget(remaining=1_000_000.0),
            hippocampus,
        )
        assert result is not None
        assert result.qty == pytest.approx(180.0)


class TestInboundProjection:

    def test_inbound_covers_reorder_so_product_is_skipped(self, adapter, hippocampus):
        stock = {
            "product_000": {
                "quantity": 0.0,
                "reorder_point": 100.0,
                "below_reorder_point": True,
                "inbound": 500.0,
            }
        }
        result = adapter.resolve(
            "urgent_reorder",
            stock,
            _suppliers(_supplier("s1")),
            _budget(),
            hippocampus,
        )
        assert result is None

    def test_projected_quantity_selects_true_deficit(self, adapter, hippocampus):
        stock = {
            "almost_covered": {
                "quantity": 10.0,
                "reorder_point": 100.0,
                "below_reorder_point": True,
                "projected_quantity": 250.0,
            },
            "still_short": {
                "quantity": 20.0,
                "reorder_point": 80.0,
                "below_reorder_point": True,
                "projected_quantity": 25.0,
            },
        }
        result = adapter.resolve(
            "urgent_reorder",
            stock,
            _suppliers(_supplier("s1")),
            _budget(),
            hippocampus,
        )
        assert result.product_id == "still_short"

    def test_without_projection_keys_uses_below_reorder_point(
        self, adapter, hippocampus
    ):
        stock = {
            "flagged": {
                "quantity": 90.0,
                "reorder_point": 50.0,
                "below_reorder_point": True,
            },
            "not_flagged": {
                "quantity": 1.0,
                "reorder_point": 80.0,
                "below_reorder_point": False,
            },
        }
        result = adapter.resolve(
            "urgent_reorder",
            stock,
            _suppliers(_supplier("s1")),
            _budget(),
            hippocampus,
        )
        assert result.product_id == "flagged"


class TestMalformedInputs:

    def test_resolve_never_raises_on_garbage(self, adapter):
        garbage = [
            (None, None, None, None, None),
            ("urgent_reorder", "stock", "sup", "bud", object()),
            ("urgent_reorder", {"p": None}, {"s": "nope"}, [], MagicMock()),
            (
                "diversify_supplier",
                {"p": {"quantity": "x", "reorder_point": None, "below_reorder_point": True}},
                {"s": {"reliability": float("nan"), "is_defaulted": False}},
                {"remaining": float("inf")},
                SimpleNamespace(experiences="not-a-list"),
            ),
            (
                ["not", "a", "str"],
                _stock(),
                _suppliers(_supplier("s1")),
                _budget(),
                SimpleNamespace(experiences=[]),
            ),
        ]
        for args in garbage:
            assert adapter.resolve(*args) is None

    def test_experiences_property_raising_does_not_raise(self, adapter):
        class BoomHippocampus:
            @property
            def experiences(self):
                raise RuntimeError("memory fault")

            def activate(self, *_a, **_k):
                raise AssertionError("activate must not be called")

        result = adapter.resolve(
            "diversify_supplier",
            _stock(),
            _suppliers(_supplier("s1")),
            _budget(),
            BoomHippocampus(),
        )
        assert result is None or result.supplier_id == "s1"

    def test_broken_experience_items_are_skipped(self, adapter):
        class Exploding:
            @property
            def path(self):
                raise RuntimeError("bad path")

        hippocampus = SimpleNamespace(
            experiences=[Exploding(), _exp_with_tokens("supplier:used")]
        )
        suppliers = _suppliers(_supplier("used"), _supplier("fresh"))
        result = adapter.resolve(
            "diversify_supplier", _stock(), suppliers, _budget(), hippocampus
        )
        assert result.supplier_id == "fresh"

    def test_callable_experiences_is_not_invoked(self, adapter):
        hippocampus = MagicMock()
        hippocampus.experiences = MagicMock()  # callable-ish, not a list
        result = adapter.resolve(
            "diversify_supplier",
            _stock(),
            _suppliers(_supplier("s1")),
            _budget(),
            hippocampus,
        )
        hippocampus.experiences.assert_not_called()
        hippocampus.activate.assert_not_called()
        assert result is None or result.supplier_id == "s1"
