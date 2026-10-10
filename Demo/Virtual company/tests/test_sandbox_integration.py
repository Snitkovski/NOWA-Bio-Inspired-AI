"""End-to-end sandbox runs without mocks (spec sections 23 and 24)."""

import json
import random
import time

import pytest

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.sandbox_agent_factory import create_procurement_agent
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.sandbox_observer import SandboxObserver
from nowa_sandbox.training_loop import SandboxTrainer


def _avg_score(quarters):
    totals = [sum(q.fitness.as_dict().values()) / 6.0 for q in quarters]
    return sum(totals) / len(totals)


class TestFullSandboxCycle:

    @pytest.mark.slow
    def test_agent_does_not_degrade_over_quarters(self):
        """Key sanity check: fitness must not decay as experience accumulates.

        Does not require graduation, only that the average fitness of the last
        five quarters is no worse than the first five. A drop would mean
        consolidation (sleep_cycle) or the affective feedback path is broken.
        """
        agent = create_procurement_agent(
            "integration_test", rng=random.Random(7), seed_intuition=True
        )
        trainer = SandboxTrainer(
            agent, SandboxEncoder(), ProcurementFitnessEvaluator(),
            sleep_every_n_days=7,
        )

        config = ProcurementWorldConfig(
            initial_budget=50_000.0, n_products=5, n_suppliers=3,
            days_per_quarter=60, seed=1,
        )
        result = trainer.run_quarters(
            n_quarters=20, world_config=config, stop_on_graduation=False
        )

        assert len(result.quarters) == 20

        first_five = _avg_score(result.quarters[:5])
        last_five = _avg_score(result.quarters[-5:])

        assert last_five >= first_five - 0.05, (
            f"Agent fitness degraded: first_five={first_five:.3f}, "
            f"last_five={last_five:.3f}"
        )

    @pytest.mark.slow
    def test_full_pipeline_produces_valid_json_output(self, tmp_path):
        """CLI-equivalent run: agent -> training -> serialization -> valid JSON."""
        agent = create_procurement_agent("json_test", rng=random.Random(3))
        trainer = SandboxTrainer(
            agent, SandboxEncoder(), ProcurementFitnessEvaluator()
        )

        config = ProcurementWorldConfig(
            initial_budget=20_000.0, n_products=3, n_suppliers=2,
            days_per_quarter=30, seed=1,
        )
        result = trainer.run_quarters(
            n_quarters=3, world_config=config, stop_on_graduation=False
        )

        observer = SandboxObserver()
        observer.record_all(result.quarters)

        output_path = tmp_path / "result.json"
        observer.to_json(str(output_path))

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 3
        assert "fitness" in data[0]
        assert "graduation" in data[0]

    @pytest.mark.slow
    def test_all_fitness_values_stay_in_range_across_a_long_run(self):
        agent = create_procurement_agent(
            "range_test", rng=random.Random(5), seed_intuition=True
        )
        trainer = SandboxTrainer(
            agent, SandboxEncoder(), ProcurementFitnessEvaluator()
        )
        config = ProcurementWorldConfig(
            initial_budget=100_000.0, n_products=10, n_suppliers=5,
            days_per_quarter=90, seed=1,
        )
        result = trainer.run_quarters(
            n_quarters=10, world_config=config, stop_on_graduation=False
        )
        for quarter in result.quarters:
            for criterion, value in quarter.fitness.as_dict().items():
                assert 0.0 <= value <= 1.0, (
                    f"quarter {quarter.quarter_index} {criterion}={value}"
                )

    def test_pipeline_is_reproducible_given_a_deterministic_agent(self):
        """The sandbox itself contributes no nondeterminism.

        A live NOWA agent cannot be part of this assertion: the core decays
        hippocampal activation against wall-clock time (hippocampus._apply_decay
        uses time.time()), so two identical runs diverge purely because they
        execute at different speeds. Reproducibility is therefore guaranteed for
        the world and the training loop, not for agent cognition.
        """

        class _DeterministicAgent:
            sleep_manager = None

            def __init__(self):
                self.calls = 0

            def step(self, context_events, reward=0.0, intensity=1.0, novelty=0.0):
                self.calls += 1
                return "urgent_reorder" if self.calls % 3 == 0 else "wait_and_monitor"

        def run():
            trainer = SandboxTrainer(
                _DeterministicAgent(), SandboxEncoder(), ProcurementFitnessEvaluator()
            )
            config = ProcurementWorldConfig(
                initial_budget=50_000.0, n_products=4, n_suppliers=3,
                days_per_quarter=45, seed=2,
            )
            result = trainer.run_quarters(
                n_quarters=4, world_config=config, stop_on_graduation=False
            )
            return [q.fitness.as_dict() for q in result.quarters]

        assert run() == run()

    def test_world_physics_is_bit_reproducible_across_a_full_quarter(self):
        def run():
            world = ProcurementWorld(ProcurementWorldConfig(
                initial_budget=100_000.0, n_products=10, n_suppliers=5, seed=42,
            ))
            for day in range(90):
                if day % 5 == 0:
                    world.place_order("supplier_001", "product_003", 40)
                world.tick()
            return world.history, world.summary()

        assert run() == run()


class TestPerformanceBudgets:
    """Spec section 24."""

    @pytest.mark.perf
    def test_single_tick_is_under_five_milliseconds(self):
        world = ProcurementWorld(ProcurementWorldConfig(
            n_products=10, n_suppliers=5, seed=1
        ))
        for _ in range(20):  # warm up
            world.tick()

        start = time.perf_counter()
        iterations = 500
        for _ in range(iterations):
            world.tick()
        per_tick_ms = ((time.perf_counter() - start) / iterations) * 1000.0
        assert per_tick_ms < 5.0, f"world.tick() took {per_tick_ms:.3f} ms"

    @pytest.mark.perf
    def test_saturated_memory_step_cost_stays_bounded(self):
        """Guard the known cost growth as the hippocampus fills.

        Per-quarter time rises from ~7 s (quarter 1) to ~38 s (quarter 30)
        because agent.step() runs an O(n_experiences) similarity search in the
        core imagination engine. That is core behaviour, not sandbox logic; this
        test only ensures it does not silently get dramatically worse.
        """
        from nowa_sandbox.sandbox_agent_factory import seed_procurement_intuition

        agent = create_procurement_agent("saturated", rng=random.Random(1))
        seed_procurement_intuition(agent, repeats=150)
        capacity = len(agent.hippocampus.experiences)
        if capacity < 500:
            pytest.skip("fallback agent has no capacity-bounded hippocampus")

        trainer = SandboxTrainer(
            agent, SandboxEncoder(), ProcurementFitnessEvaluator()
        )
        config = ProcurementWorldConfig(
            initial_budget=100_000.0, n_products=10, n_suppliers=5,
            days_per_quarter=10, seed=1,
        )
        result = trainer.run_quarters(n_quarters=1, world_config=config)
        per_day_s = result.quarters[0].processing_time_s / 10.0
        assert per_day_s < 2.5, (
            f"{per_day_s:.2f} s/day at {capacity} stored experiences"
        )

    @pytest.mark.perf
    @pytest.mark.slow
    def test_standard_quarter_is_under_thirty_seconds(self):
        agent = create_procurement_agent(
            "perf", rng=random.Random(1), seed_intuition=True
        )
        trainer = SandboxTrainer(
            agent, SandboxEncoder(), ProcurementFitnessEvaluator()
        )
        config = ProcurementWorldConfig(
            initial_budget=100_000.0, n_products=10, n_suppliers=5,
            days_per_quarter=90, seed=1,
        )
        result = trainer.run_quarters(n_quarters=1, world_config=config)
        elapsed = result.quarters[0].processing_time_s
        assert elapsed < 30.0, f"quarter took {elapsed:.2f} s"
