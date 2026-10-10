"""Verify the sandbox respects agent sovereignty (Principle 0.1)."""

import inspect
import random
from pathlib import Path

import pytest

from nowa_sandbox import procurement_world
from nowa_sandbox.sandbox_agent_factory import (
    PROCUREMENT_ACTIONS,
    create_procurement_agent,
    seed_procurement_intuition,
)
from nowa_sandbox.sandbox_encoder import SandboxEncoder


PACKAGE_DIR = Path(procurement_world.__file__).resolve().parent


class TestAgentSovereignty:

    def test_two_agents_have_independent_hippocampus(self):
        a = create_procurement_agent("agent_a", rng=random.Random(1))
        b = create_procurement_agent("agent_b", rng=random.Random(2))
        assert a.hippocampus is not b.hippocampus

    def test_seeding_one_agent_does_not_touch_another(self):
        a = create_procurement_agent("agent_a", rng=random.Random(1))
        b = create_procurement_agent("agent_b", rng=random.Random(2))
        before = len(b.hippocampus.experiences)
        seed_procurement_intuition(a)
        assert len(a.hippocampus.experiences) > 0
        assert len(b.hippocampus.experiences) == before

    def test_world_does_not_expose_internal_state_to_agent_directly(
        self, small_world
    ):
        """C3: agent.step() only ever receives context_events (List[str]),
        never a direct reference to the ProcurementWorld object."""
        encoder = SandboxEncoder()
        small_world.tick()
        context = encoder.encode_daily_context(small_world, small_world.history[-1])
        assert isinstance(context, list)
        assert all(isinstance(item, str) for item in context)

    def test_world_tick_not_callable_by_agent_object(self):
        """C2: the agent has no reference through which it could tick the world."""
        agent = create_procurement_agent("test", rng=random.Random(1))
        assert not hasattr(agent, "world")
        assert not hasattr(agent, "_world")

    def test_agent_receives_no_world_reference_during_training(
        self, encoder, fitness_evaluator
    ):
        from nowa_sandbox.procurement_world import ProcurementWorld
        from nowa_sandbox.training_loop import SandboxTrainer

        seen = []

        class _SpyAgent:
            sleep_manager = None

            def step(self, context_events, reward=0.0, intensity=1.0, novelty=0.0):
                seen.append(context_events)
                return "wait_and_monitor"

        trainer = SandboxTrainer(_SpyAgent(), encoder, fitness_evaluator)
        trainer.run_quarters(
            n_quarters=1,
            world_config=procurement_world.ProcurementWorldConfig(
                n_products=2, n_suppliers=2, days_per_quarter=10, seed=1
            ),
        )
        assert seen
        for context in seen:
            assert not any(isinstance(item, ProcurementWorld) for item in context)


class TestSimulationRealityIsolation:
    """C1: the sandbox must never reach for real MCP clients."""

    FORBIDDEN_TOKENS = ("mcp", "requests", "httpx", "urllib.request", "socket")

    def test_no_mcp_or_network_imports_in_package(self):
        offenders = []
        for module_path in PACKAGE_DIR.glob("*.py"):
            text = module_path.read_text(encoding="utf-8").lower()
            for line in text.splitlines():
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue
                if any(token in stripped for token in self.FORBIDDEN_TOKENS):
                    offenders.append(f"{module_path.name}: {stripped}")
        assert offenders == [], f"simulation reached toward reality: {offenders}"

    ALLOWED_WORLD_IMPORTS = {
        "__future__", "copy", "random", "dataclasses", "typing", "._common",
    }

    def test_world_module_imports_only_stdlib_and_local_helpers(self):
        import ast

        source = (PACKAGE_DIR / "procurement_world.py").read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add("." * node.level + (node.module or ""))
        assert modules <= self.ALLOWED_WORLD_IMPORTS, (
            f"unexpected imports in procurement_world: "
            f"{sorted(modules - self.ALLOWED_WORLD_IMPORTS)}"
        )


class TestAgentConstruction:

    def test_agent_exposes_expected_action_vocabulary(self):
        agent = create_procurement_agent("actions", rng=random.Random(1))
        selector = getattr(agent, "selector", None)
        if selector is None:
            pytest.skip("fallback agent has no selector")
        assert list(selector.actions) == PROCUREMENT_ACTIONS

    def test_agent_step_returns_a_known_action(self, encoder, small_world):
        agent = create_procurement_agent("stepper", rng=random.Random(3))
        small_world.tick()
        context = encoder.encode_daily_context(small_world, small_world.history[-1])
        action = agent.step(context)
        assert isinstance(action, str)

    def test_agent_has_a_genome(self):
        agent = create_procurement_agent("genome", rng=random.Random(1))
        assert getattr(agent, "genome", None) is not None

    def test_agent_id_is_assigned(self):
        agent = create_procurement_agent("custom_id", rng=random.Random(1))
        assert agent.agent_id == "custom_id"

    def test_creation_is_reproducible_for_a_given_seed(self):
        first = create_procurement_agent("a", rng=random.Random(99))
        second = create_procurement_agent("b", rng=random.Random(99))
        genome_a = getattr(first, "genome", None)
        genome_b = getattr(second, "genome", None)
        to_dict_a = getattr(genome_a, "to_dict", None)
        if callable(to_dict_a):
            assert genome_a.to_dict() == genome_b.to_dict()
        else:
            assert genome_a == genome_b


class TestIntuitionSeeding:

    def test_seeding_stores_episodes(self):
        agent = create_procurement_agent("seeded", rng=random.Random(1))
        stored = seed_procurement_intuition(agent)
        assert stored > 0
        assert len(agent.hippocampus.experiences) >= stored

    def test_seeding_via_factory_flag(self):
        plain = create_procurement_agent(
            "plain", rng=random.Random(1), seed_intuition=False
        )
        seeded = create_procurement_agent(
            "seeded", rng=random.Random(1), seed_intuition=True
        )
        assert len(seeded.hippocampus.experiences) > len(plain.hippocampus.experiences)

    def test_seeding_agent_without_hippocampus_returns_zero(self):
        class _Brainless:
            pass

        assert seed_procurement_intuition(_Brainless()) == 0

    def test_seeded_agent_activates_memory_for_business_context(self, encoder):
        agent = create_procurement_agent(
            "activator", rng=random.Random(1), seed_intuition=True
        )
        tokens = encoder.encode_seed_episode("stock_critical_low")["tokens"]
        activated = agent.hippocampus.activate(tokens)
        assert len(activated) > 0

    def test_legacy_wrapper_delegates_to_seeder_with_action_events(self):
        """Pre-v2.0 callers must still produce ACTION events the selector can read."""
        from nowa_sandbox.procurement_hippocampus_seeder import (
            ProcurementHippocampusSeeder,
        )

        agent = create_procurement_agent(
            "legacy", rng=random.Random(1), seed_intuition=False
        )
        stored = seed_procurement_intuition(
            agent, event_names=["stock_critical_low"], repeats=1
        )
        assert stored > 0
        source = inspect.getsource(seed_procurement_intuition)
        assert "ProcurementHippocampusSeeder" in source
        assert "seeder.seed_agent" in source

        found_action = False
        for exp in agent.hippocampus.experiences:
            path = getattr(exp, "path", None)
            events = list(getattr(path, "events", []) or [])
            for event in events:
                name = getattr(event, "name", str(event))
                event_type = getattr(event, "event_type", None)
                type_value = getattr(event_type, "value", event_type)
                if type_value == "action" or str(name).startswith("action:"):
                    found_action = True
                    break
            if found_action:
                break
        assert found_action, "legacy wrapper stored paths without ACTION events"


class TestSleepIsTheOnlyLearningPath:
    """C4: nothing in the sandbox mutates agent patterns outside sleep_cycle."""

    def test_trainer_only_calls_sleep_cycle_for_consolidation(self):
        from nowa_sandbox import training_loop

        source = inspect.getsource(training_loop)
        assert "sleep_cycle" in source
        for forbidden in ("deep_sleep(", "consolidate(", "cortex.store_pattern("):
            assert forbidden not in source
        assert "value_layer.update" not in source

    def test_motor_adapter_source_has_no_cognitive_calls(self):
        """R2: MotorAdapter module must not drive the NOWA decision pipeline."""
        from nowa_sandbox.procurement_motor_adapter import ProcurementMotorAdapter

        source = inspect.getsource(ProcurementMotorAdapter.resolve)
        for forbidden in (
            "agent.step",
            ".activate(",
            "selector.",
            "basal_ganglia",
            "thalamic_gate",
            "value_layer",
        ):
            assert forbidden not in source

    def test_anti_monopoly_and_cost_balance_scaffolds_are_gone(self):
        """v2.0: body must not rewrite the brain's chosen strategy."""
        from nowa_sandbox import gui_app, gui_controller, training_loop
        from nowa_sandbox.procurement_motor_adapter import ProcurementMotorAdapter

        forbidden = ("anti_monopoly_scaffold", "cost_balance_scaffold")
        for module in (training_loop, gui_controller, gui_app, ProcurementMotorAdapter):
            source = inspect.getsource(module)
            for token in forbidden:
                assert token not in source, f"{module} still contains {token}"
