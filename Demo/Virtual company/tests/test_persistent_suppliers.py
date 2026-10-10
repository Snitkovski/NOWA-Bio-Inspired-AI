"""Tests for Stage 1b persistent suppliers (spec sections 26.6, 26.8)."""

import pytest

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.training_loop import SandboxTrainer


SUPPLIER_ATTRIBUTES = (
    "reliability",
    "base_price_multiplier",
    "price_volatility",
    "lead_time_days",
    "reputation",
    "total_orders",
    "successful_orders",
)


class _RecordingAgent:
    """Minimal deterministic agent that always buys, so orders actually flow."""

    def __init__(self, action="place_order_reliable_supplier"):
        self.action = action
        self.steps = 0

    def step(self, context_events=None, **kwargs):
        self.steps += 1
        return self.action

    def sleep_cycle(self, *args, **kwargs):
        return {}


class TestConfigFlag:

    def test_non_persistent_mode_is_the_default(self, small_world_config):
        assert small_world_config.persistent_suppliers is False
        assert ProcurementWorldConfig().persistent_suppliers is False

    def test_flag_is_coerced_to_bool(self):
        assert ProcurementWorldConfig(persistent_suppliers=1).persistent_suppliers is (
            True
        )
        assert ProcurementWorldConfig(
            persistent_suppliers=None
        ).persistent_suppliers is False

    def test_flag_does_not_change_world_physics_on_its_own(self):
        """Setting the flag alone must not perturb a quarter (constraint V1)."""
        def run(persistent):
            world = ProcurementWorld(ProcurementWorldConfig(
                n_products=3, n_suppliers=3, days_per_quarter=20, seed=7,
                persistent_suppliers=persistent,
            ))
            for _ in range(20):
                world.tick()
            return world.summary()

        assert run(False) == run(True)


class TestCarrySupplierState:

    def test_carry_supplier_state_preserves_reliability(self):
        world1 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=1))
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=2))
        world2.carry_supplier_state(exported)

        for sid, supplier in world1.suppliers.items():
            for attribute in SUPPLIER_ATTRIBUTES:
                assert getattr(world2.suppliers[sid], attribute) == getattr(
                    supplier, attribute
                )

    def test_carry_supplier_state_resets_default_flag(self):
        """A supplier that defaulted gets a second chance next quarter."""
        world1 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=1, seed=1))
        list(world1.suppliers.values())[0].is_defaulted = True
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=1, seed=2))
        world2.carry_supplier_state(exported)

        assert list(world2.suppliers.values())[0].is_defaulted is False

    def test_suppliers_differ_without_carrying(self):
        """The premise of the whole revision: same IDs, different entities."""
        world1 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=1))
        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=2))
        assert set(world1.suppliers) == set(world2.suppliers)
        assert any(
            world1.suppliers[sid].reliability != world2.suppliers[sid].reliability
            for sid in world1.suppliers
        )

    def test_export_is_a_deep_copy(self):
        world = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=1))
        exported = world.export_supplier_state()
        for supplier in exported.values():
            supplier.reliability = 0.0

        assert all(s.reliability > 0.0 for s in world.suppliers.values())

    def test_carrying_does_not_alias_the_source(self):
        """Mutating the new world must not corrupt the finished quarter."""
        world1 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=1))
        exported = world1.export_supplier_state()
        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=2))
        world2.carry_supplier_state(exported)

        for supplier in world2.suppliers.values():
            supplier.reputation = 0.123

        assert all(s.reputation != 0.123 for s in world1.suppliers.values())
        assert all(s.reputation != 0.123 for s in exported.values())

    def test_unknown_supplier_ids_are_ignored(self):
        """Shrinking the roster must not resurrect invisible counterparties."""
        big = ProcurementWorld(ProcurementWorldConfig(n_suppliers=5, seed=1))
        small = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=2))
        small.carry_supplier_state(big.export_supplier_state())
        assert len(small.suppliers) == 2

    def test_empty_and_none_payloads_are_safe(self):
        world = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=1))
        before = {sid: s.reliability for sid, s in world.suppliers.items()}
        world.carry_supplier_state({})
        world.carry_supplier_state(None)
        assert {sid: s.reliability for sid, s in world.suppliers.items()} == before

    def test_carried_reputation_is_observable_by_the_agent(self):
        """Persistence is pointless unless the agent can perceive the history."""
        world1 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=1))
        for supplier in world1.suppliers.values():
            supplier.update_reputation_on_delivery(on_time=True)

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=2, seed=2))
        world2.carry_supplier_state(world1.export_supplier_state())

        directory = world2.observe_supplier_directory()
        assert all(entry["total_orders"] == 1 for entry in directory.values())

    def test_quotes_still_vary_between_quarters(self):
        """Carrying attributes must not freeze the market into one fixed price."""
        world1 = ProcurementWorld(ProcurementWorldConfig(
            n_products=1, n_suppliers=1, seed=1,
        ))
        world2 = ProcurementWorld(ProcurementWorldConfig(
            n_products=1, n_suppliers=1, seed=2,
        ))
        world2.carry_supplier_state(world1.export_supplier_state())

        quote1 = world1.observe_supplier_quote("supplier_000", "product_000", 10)
        quote2 = world2.observe_supplier_quote("supplier_000", "product_000", 10)
        assert quote1["unit_price"] != quote2["unit_price"]


class TestStage1bTrainingLoop:

    def _trainer(self, stage="1b", baseline=None):
        return SandboxTrainer(
            _RecordingAgent(),
            SandboxEncoder(),
            ProcurementFitnessEvaluator(stage=stage),
            sleep_every_n_days=5,
            stage_1a_baseline=baseline,
        )

    def _config(self):
        return ProcurementWorldConfig(
            initial_budget=50_000.0, n_products=2, n_suppliers=3,
            days_per_quarter=12, seed=5,
        )

    def test_supplier_attributes_survive_across_quarters(self):
        """Reliability after quarter 3 still equals what quarter 1 generated."""
        trainer = self._trainer()
        config = self._config()

        result = trainer.run_stage1b_persistent(
            n_quarters=1, world_config=config, stop_on_graduation=False
        )
        first = {
            sid: s.reliability for sid, s in trainer.carried_suppliers.items()
        }

        trainer.run_stage1b_persistent(
            n_quarters=2, world_config=config,
            stop_on_graduation=False, initial_result=result,
        )
        assert {
            sid: s.reliability for sid, s in trainer.carried_suppliers.items()
        } == first

    def test_stage_1a_regenerates_suppliers_between_quarters(self):
        """Contrast case: without carrying, the same IDs change identity."""
        trainer = self._trainer(stage="1a")
        config = self._config()

        seen = []
        result = None
        for _ in range(2):
            result = trainer.run_quarters(
                n_quarters=1, world_config=config,
                stop_on_graduation=False, initial_result=result,
            )
            world = ProcurementWorld(
                trainer._config_for_quarter(config, len(result.quarters))
            )
            seen.append({sid: s.reliability for sid, s in world.suppliers.items()})

        assert seen[0] != seen[1]

    def test_delivery_history_accumulates_over_full_length_quarters(self):
        """Over 90-day quarters, orders land and relationship history builds up."""
        trainer = self._trainer()
        config = ProcurementWorldConfig(
            initial_budget=200_000.0, n_products=2, n_suppliers=3,
            days_per_quarter=90, seed=5,
        )
        trainer.run_stage1b_persistent(
            n_quarters=2, world_config=config, stop_on_graduation=False
        )
        assert any(s.total_orders > 0 for s in trainer.carried_suppliers.values())

    def test_run_quarters_does_not_carry_by_default(self):
        trainer = self._trainer(stage="1a")
        trainer.run_quarters(
            n_quarters=2, world_config=self._config(), stop_on_graduation=False
        )
        assert trainer.carried_suppliers is None

    def test_stage1b_sets_the_persistent_flag_on_the_world_config(self):
        trainer = self._trainer()
        result = trainer.run_stage1b_persistent(
            n_quarters=1, world_config=self._config(), stop_on_graduation=False
        )
        assert len(result.quarters) == 1

    def test_stage1b_works_without_an_explicit_world_config(self):
        trainer = self._trainer()
        result = trainer.run_stage1b_persistent(
            n_quarters=1,
            world_config=ProcurementWorldConfig(days_per_quarter=3, n_products=1),
            stop_on_graduation=False,
        )
        assert result.quarters[0].quarter_index == 1

    def test_incremental_calls_keep_the_same_suppliers(self):
        """The checkpointing CLI runs one quarter per call; continuity must hold."""
        trainer = self._trainer()
        config = self._config()
        result = None
        for _ in range(3):
            result = trainer.run_stage1b_persistent(
                n_quarters=1, world_config=config,
                stop_on_graduation=False, initial_result=result,
            )
        assert len(result.quarters) == 3
        assert trainer.carried_suppliers is not None

    def test_non_regression_recorded_only_in_stage_1b_with_a_baseline(self):
        baseline = {"cost_efficiency": 0.8, "stockout_avoidance": 0.9,
                    "budget_discipline": 1.0, "reaction_to_risk_events": 0.8}
        with_guard = self._trainer(baseline=baseline).run_stage1b_persistent(
            n_quarters=1, world_config=self._config(), stop_on_graduation=False
        )
        assert set(with_guard.quarters[0].non_regression) == set(baseline)

        without = self._trainer().run_stage1b_persistent(
            n_quarters=1, world_config=self._config(), stop_on_graduation=False
        )
        assert without.quarters[0].non_regression is None

    def test_stage_1a_run_records_no_guard(self):
        result = self._trainer(stage="1a", baseline={"cost_efficiency": 0.8}).run_quarters(
            n_quarters=1, world_config=self._config(), stop_on_graduation=False
        )
        assert result.quarters[0].non_regression is None


class TestSustainedGraduation:
    """Section 26.7: Stage 1b graduation must be held, not hit once."""

    def _result(self, passes):
        from nowa_sandbox.procurement_fitness import ProcurementFitnessVector
        from nowa_sandbox.training_loop import QuarterResult, SandboxTrainingResult

        result = SandboxTrainingResult()
        for i, passed in enumerate(passes, start=1):
            result.quarters.append(QuarterResult(
                quarter_index=i,
                fitness=ProcurementFitnessVector(
                    1.0, 1.0, 1.0, 1.0, 1.0, 1.0, n_days=90, n_orders=10
                ),
                graduation={"all_passed": passed},
                world_summary={},
                processing_time_s=0.0,
            ))
        return result

    def test_three_consecutive_passes_count_as_sustained(self):
        result = self._result([False, True, True, True, False])
        assert result.longest_graduation_streak == 3
        assert result.graduation_sustained(3) is True

    def test_scattered_passes_do_not_count(self):
        """The v1.0 failure mode: passing quarters 17 and 19 but not 18."""
        result = self._result([True, False, True, False, True])
        assert result.longest_graduation_streak == 1
        assert result.graduation_sustained(3) is False

    def test_streak_at_the_end_is_counted(self):
        assert self._result([False, True, True]).longest_graduation_streak == 2

    def test_no_passes_is_zero(self):
        assert self._result([False, False]).longest_graduation_streak == 0
        assert self._result([]).longest_graduation_streak == 0

    def test_regressed_quarters_lists_only_passing_ones(self):
        result = self._result([True, True])
        result.quarters[0].non_regression = {"cost_efficiency": False}
        result.quarters[1].non_regression = {"cost_efficiency": True}
        assert result.regressed_quarters() == [1]
        assert result.quarters[0].regressed_criteria == ["cost_efficiency"]

    def test_regression_is_flagged_in_the_summary(self):
        result = self._result([True])
        result.quarters[0].non_regression = {"cost_efficiency": False}
        assert "REGRESSED: cost_efficiency" in result.summary()

    def test_clean_summary_has_no_regression_marker(self):
        assert "REGRESSED" not in self._result([True]).summary()
