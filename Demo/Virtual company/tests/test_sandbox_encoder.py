"""Tests for SandboxEncoder."""

import pytest

from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.sandbox_encoder import (
    AFFECTIVE_MAPPING,
    SandboxEncoder,
    classify_world_events,
)


class TestClassifyWorldEvents:

    def test_stockout_classified(self):
        tick_result = {"events": [{"type": "stockout", "product_id": "p1"}]}
        events = classify_world_events(tick_result)
        assert "stock_critical_low" in events

    def test_supplier_defaulted_classified(self):
        tick_result = {"events": [{"type": "supplier_defaulted", "supplier_id": "s1"}]}
        events = classify_world_events(tick_result)
        assert "supplier_defaulted" in events

    def test_order_arrived_on_time(self):
        tick_result = {"events": [{"type": "order_arrived", "on_time": True}]}
        events = classify_world_events(tick_result)
        assert "order_arrived_on_time" in events

    def test_order_arrived_late(self):
        tick_result = {"events": [{"type": "order_arrived", "on_time": False}]}
        events = classify_world_events(tick_result)
        assert "order_arrived_late" in events

    def test_demand_shock_classified(self):
        events = classify_world_events({"events": [{"type": "demand_shock"}]})
        assert "demand_shock" in events

    def test_bankruptcy_classified(self):
        events = classify_world_events({"events": [{"type": "bankruptcy", "day": 3}]})
        assert "bankruptcy" in events

    def test_empty_events_returns_quiet_day(self):
        events = classify_world_events({"events": []})
        assert events == ["quiet_day"]

    @pytest.mark.parametrize("payload", [None, {}, {"events": None}])
    def test_malformed_payload_is_tolerated(self, payload):
        assert classify_world_events(payload) == ["quiet_day"]

    def test_unknown_event_type_is_ignored(self):
        events = classify_world_events({"events": [{"type": "meteor_strike"}]})
        assert events == ["quiet_day"]


class TestSandboxEncoderDailyContext:

    def test_returns_list_of_strings(self, small_world, encoder):
        small_world.tick()
        tick_result = small_world.history[-1]
        context = encoder.encode_daily_context(small_world, tick_result)
        assert isinstance(context, list)
        assert all(isinstance(t, str) for t in context)

    def test_context_is_never_empty(self, small_world, encoder):
        context = encoder.encode_daily_context(small_world, {"events": []})
        assert len(context) > 0

    def test_below_reorder_point_flagged(self, small_world, encoder):
        product_id = next(iter(small_world.products.keys()))
        small_world.products[product_id].current_stock = 0.0
        small_world.products[product_id].reorder_point = 100.0

        tick_result = {"events": []}
        context = encoder.encode_daily_context(small_world, tick_result)
        assert f"product:{product_id}" in context
        assert "status:below_reorder_point" in context

    def test_budget_critical_flagged(self, small_world, encoder):
        small_world.budget = small_world.initial_budget * 0.02
        tick_result = {"events": []}
        context = encoder.encode_daily_context(small_world, tick_result)
        assert "budget:critical" in context

    def test_budget_high_utilization_flagged(self, small_world, encoder):
        small_world.budget = small_world.initial_budget * 0.15
        context = encoder.encode_daily_context(small_world, {"events": []})
        assert "budget:high_utilization" in context
        assert "budget:critical" not in context

    def test_healthy_budget_produces_no_budget_token(self, small_world, encoder):
        context = encoder.encode_daily_context(small_world, {"events": []})
        assert not any(t.startswith("budget:") for t in context)

    def test_tokens_carry_no_raw_numeric_values(self, small_world, encoder):
        """Acceptance criterion: only categorical tokens, never raw magnitudes."""
        small_world.budget = small_world.initial_budget * 0.02
        for product in small_world.products.values():
            product.current_stock = 0.0
            product.reorder_point = 50.0
        context = encoder.encode_daily_context(
            small_world, {"events": [{"type": "stockout", "product_id": "product_000"}]}
        )
        for token in context:
            _, _, value = token.partition(":")
            with pytest.raises(ValueError):
                float(value)

    def test_empty_world_does_not_raise(self, encoder):
        world = ProcurementWorld(ProcurementWorldConfig(n_products=0, n_suppliers=0, seed=1))
        context = encoder.encode_daily_context(world, {"events": []})
        assert context

    def test_encoding_is_deterministic(self, small_world, encoder):
        tick_result = {"events": [{"type": "supplier_defaulted", "supplier_id": "s"}]}
        first = encoder.encode_daily_context(small_world, tick_result)
        second = encoder.encode_daily_context(small_world, tick_result)
        assert first == second

    def test_lead_time_cover_gap_is_flagged_even_above_reorder(self, encoder):
        world = ProcurementWorld.from_quarter_spec(
            {
                "budget": 100_000.0,
                "products": [
                    {
                        "product_id": "Банка 3 литра",
                        "base_demand_per_day": 6.0,
                        "demand_volatility": 0.15,
                        "current_stock": 25.0,
                        "reorder_point": 18.0,
                    }
                ],
                "suppliers": [{"supplier_id": "supplier_001"}],
                "offers": [
                    {
                        "product_id": "Банка 3 литра",
                        "supplier_id": "supplier_001",
                        "lead_time_days": 5,
                    }
                ],
            }
        )
        context = encoder.encode_daily_context(world, {"events": []})
        assert "product:Банка 3 литра" in context
        assert "status:below_reorder_point" in context


class TestDailyAffect:

    def test_quiet_day_is_near_neutral(self, encoder):
        affect = encoder.encode_daily_affect({"events": []})
        assert -0.2 <= affect["valence"] <= 0.2

    def test_bankruptcy_is_strongly_negative(self, encoder):
        affect = encoder.encode_daily_affect({"events": [{"type": "bankruptcy"}]})
        assert affect["reward"] < -0.5

    def test_on_time_delivery_is_positive(self, encoder):
        affect = encoder.encode_daily_affect(
            {"events": [{"type": "order_arrived", "on_time": True}]}
        )
        assert affect["reward"] > 0

    def test_all_fields_within_range(self, encoder):
        affect = encoder.encode_daily_affect(
            {"events": [{"type": "stockout"}, {"type": "demand_shock"}]}
        )
        assert -1.0 <= affect["valence"] <= 1.0
        assert 0.0 <= affect["arousal"] <= 1.0
        assert -1.0 <= affect["reward"] <= 1.0
        assert 0.0 <= affect["intensity"] <= 2.0
        assert 0.0 <= affect["novelty"] <= 1.0

    def test_demand_shock_registers_novelty(self, encoder):
        affect = encoder.encode_daily_affect({"events": [{"type": "demand_shock"}]})
        assert affect["novelty"] > 0


class TestAffectiveMapping:

    def test_bankruptcy_is_most_negative(self):
        bankruptcy_v = AFFECTIVE_MAPPING["bankruptcy"]["valence"]
        for name, entry in AFFECTIVE_MAPPING.items():
            if name != "bankruptcy":
                assert entry["valence"] >= bankruptcy_v, (
                    f"'{name}' valence ({entry['valence']}) should not be "
                    f"more negative than bankruptcy ({bankruptcy_v})"
                )

    def test_all_entries_have_valid_ranges(self):
        for name, entry in AFFECTIVE_MAPPING.items():
            assert -1.0 <= entry["valence"] <= 1.0, f"{name} valence out of range"
            assert 0.0 <= entry["arousal"] <= 1.0, f"{name} arousal out of range"

    def test_all_entries_have_tags(self):
        for name, entry in AFFECTIVE_MAPPING.items():
            assert entry.get("tags"), f"{name} has no domain tags"

    def test_risk_events_are_high_arousal(self):
        for name in ("stock_critical_low", "supplier_defaulted", "bankruptcy"):
            assert AFFECTIVE_MAPPING[name]["arousal"] >= 0.6


class TestSeedEpisodeEncoding:

    def test_returns_expected_structure(self, encoder):
        episode = encoder.encode_seed_episode("stock_critical_low")
        assert "event_name" in episode
        assert "tokens" in episode
        assert "v" in episode
        assert "a" in episode

    def test_unknown_event_falls_back_gracefully(self, encoder):
        episode = encoder.encode_seed_episode("totally_unknown_event")
        assert episode["v"] == 0.0

    def test_every_mapped_event_produces_tokens(self, encoder):
        for event_name in AFFECTIVE_MAPPING:
            episode = encoder.encode_seed_episode(event_name)
            assert episode["tokens"]
            assert episode["tokens"][0] == f"event:{event_name}"
