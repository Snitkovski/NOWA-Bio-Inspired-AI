"""Verify the v2.0 sovereign NOWA procurement pipeline (spec R1–R6)."""

import inspect
import random
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_hippocampus_seeder import ProcurementHippocampusSeeder
from nowa_sandbox.procurement_motor_adapter import OrderParams, ProcurementMotorAdapter
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.sandbox_agent_factory import create_procurement_agent
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.training_loop import SandboxTrainer


def _trainer(agent, **kwargs):
    return SandboxTrainer(
        agent,
        SandboxEncoder(),
        ProcurementFitnessEvaluator(stage="1a"),
        **kwargs,
    )


def _world(days=3, **overrides):
    params = dict(
        n_products=2,
        n_suppliers=2,
        days_per_quarter=days,
        initial_budget=50_000.0,
        seed=1,
    )
    params.update(overrides)
    return ProcurementWorld(ProcurementWorldConfig(**params))


def _force_reorder_deficit(world):
    for product in world.products.values():
        product.current_stock = 0.0
        product.reorder_point = max(float(product.reorder_point), 50.0)


def _result_status(entry):
    result = (entry or {}).get("result")
    if not isinstance(result, dict):
        return None
    return result.get("status")


class _StringFallbackAgent:
    """Fallback-shaped backend: ``step()`` returns a plain action string."""

    def __init__(self, action="wait_and_monitor"):
        self.action = action
        self.calls = 0
        self.sleep_manager = None
        self.hippocampus = SimpleNamespace(experiences=[], store=lambda *a, **k: None)
        self.affective_space = SimpleNamespace(axes={}, step=lambda *a, **k: None)
        self.value_layer = SimpleNamespace(update=MagicMock())

    def step(self, context_events):
        self.calls += 1
        return self.action


class TestAgentPipelineOrder:
    def test_agent_step_called_before_motor_adapter(self):
        """R1: each day calls agent.step() first, then motor_adapter.resolve()."""
        agent = create_procurement_agent("order", rng=random.Random(1))
        trainer = _trainer(agent)
        call_order = []
        original_step = agent.step
        original_resolve = trainer.motor_adapter.resolve

        def tracked_step(*args, **kwargs):
            call_order.append("agent.step")
            return original_step(*args, **kwargs)

        def tracked_resolve(*args, **kwargs):
            call_order.append("motor_adapter.resolve")
            return original_resolve(*args, **kwargs)

        agent.step = tracked_step
        trainer.motor_adapter.resolve = tracked_resolve
        trainer._run_single_quarter(_world(), n_days=3)

        assert call_order == ["agent.step", "motor_adapter.resolve"] * 3

    def test_core_step_invokes_selector_bg_and_thalamic_gate(self):
        agent = create_procurement_agent("core", rng=random.Random(2))
        if not all(
            hasattr(agent, name)
            for name in ("selector", "basal_ganglia", "thalamic_gate")
        ):
            pytest.skip("core selector/basal_ganglia/thalamic_gate not available")
        agent.selector.compute_pressures = MagicMock(
            wraps=agent.selector.compute_pressures
        )
        agent.basal_ganglia.process = MagicMock(wraps=agent.basal_ganglia.process)
        agent.thalamic_gate.select = MagicMock(wraps=agent.thalamic_gate.select)

        _trainer(agent)._run_single_quarter(_world(days=1), n_days=1)

        agent.selector.compute_pressures.assert_called()
        agent.basal_ganglia.process.assert_called()
        agent.thalamic_gate.select.assert_called()


class TestMotorAdapterCognitiveIsolation:
    def test_motor_adapter_does_not_call_agent_cognitive_methods(self):
        """R2: MotorAdapter must not call hippocampus.activate() or selector."""
        adapter = ProcurementMotorAdapter()
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

        adapter.resolve(
            "place_order_reliable_supplier",
            stock_obs,
            supplier_obs,
            {"remaining": 5000.0},
            mock_hippocampus,
        )

        mock_hippocampus.activate.assert_not_called()
        mock_hippocampus.store.assert_not_called()
        mock_hippocampus.step.assert_not_called()

    def test_resolve_does_not_invoke_agent_step(self):
        """R2: MotorAdapter never calls agent.step(); it only reads experiences."""
        adapter = ProcurementMotorAdapter()
        agent = MagicMock()
        agent.experiences = []
        adapter.resolve(
            "diversify_supplier",
            {
                "product_000": {
                    "quantity": 1,
                    "reorder_point": 10,
                    "below_reorder_point": True,
                }
            },
            {
                "supplier_000": {
                    "reliability": 0.5,
                    "is_defaulted": False,
                }
            },
            {"remaining": 1_000.0},
            agent,
        )
        agent.step.assert_not_called()
        agent.activate.assert_not_called()


class TestWakingBoundaries:
    def test_store_order_experience_never_updates_value_layer(self):
        """R3: hippocampus.store is used; value_layer is not updated while awake."""
        agent = create_procurement_agent("memory", rng=random.Random(3))
        trainer = _trainer(agent)
        source = inspect.getsource(trainer._store_order_experience)
        assert "hippocampus" in source
        assert "value_layer" not in source

        value_layer = getattr(agent, "value_layer", None)
        if value_layer is not None:
            value_layer.update = MagicMock(wraps=value_layer.update)
        before = len(agent.hippocampus.experiences)
        params = OrderParams(
            supplier_id="supplier_000",
            product_id="product_000",
            qty=100.0,
            strategy="urgent_reorder",
            confidence=0.9,
        )

        trainer._store_order_experience(
            ["event:stock_critical_low"], params, {"status": "accepted"}
        )

        assert len(agent.hippocampus.experiences) > before
        if value_layer is not None:
            value_layer.update.assert_not_called()

    def test_feedback_updates_affect_not_value_layer(self):
        """R4: affective_space is updated; value_layer is not."""
        agent = create_procurement_agent("affect", rng=random.Random(4))
        trainer = _trainer(agent)
        source = inspect.getsource(trainer._apply_order_feedback)
        assert "affective_space" in source
        assert "value_layer" not in source

        agent.affective_space.step = MagicMock(wraps=agent.affective_space.step)
        value_layer = getattr(agent, "value_layer", None)
        if value_layer is not None:
            value_layer.update = MagicMock(wraps=value_layer.update)

        feedback = trainer._apply_order_feedback(
            {"result": {"status": "accepted"}}
        )

        assert feedback["reward"] > 0
        agent.affective_space.step.assert_called_once()
        if value_layer is not None:
            value_layer.update.assert_not_called()

    def test_waking_quarter_with_orders_never_updates_value_layer(self):
        """R3/R4 live: trainer stores memory and affect, and never calls value_layer."""
        class _OrderingAgent:
            sleep_manager = None

            def __init__(self):
                self.hippocampus = SimpleNamespace(experiences=[], store=self._store)
                self.affective_space = SimpleNamespace(step=MagicMock())
                self.value_layer = SimpleNamespace(update=MagicMock())

            def _store(self, *args, **kwargs):
                self.hippocampus.experiences.append(object())

            def step(self, context_events):
                return "urgent_reorder"

        agent = _OrderingAgent()
        trainer = _trainer(agent)
        world = _world(days=4)
        _force_reorder_deficit(world)
        log = trainer._run_single_quarter(world, n_days=4)

        agent.value_layer.update.assert_not_called()
        assert any(_result_status(entry) == "accepted" for entry in log)
        assert len(agent.hippocampus.experiences) > 0
        agent.affective_space.step.assert_called()


class TestSeederAndFallbackCompatibility:
    def test_seeder_only_touches_hippocampus(self):
        """R5: Seeder must not touch affective_space or neuromodulators."""
        agent = create_procurement_agent(
            "r5", rng=random.Random(1), seed_intuition=False
        )
        axes_before = dict(getattr(agent.affective_space, "axes", {}) or {})
        nm = getattr(agent, "neuromodulators", None)
        nm_before = dict(nm.to_dict()) if nm is not None and hasattr(nm, "to_dict") else None
        if isinstance(nm_before, dict):
            nm_before.pop("timestamp", None)

        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added > 0, "No episodes were seeded"

        axes_after = dict(getattr(agent.affective_space, "axes", {}) or {})
        for axis, value in axes_before.items():
            assert abs(float(value) - float(axes_after.get(axis, 0.0))) < 1e-6, (
                f"Seeder modified affective_space[{axis}]"
            )
        if nm_before is not None:
            nm_after = dict(nm.to_dict())
            nm_after.pop("timestamp", None)
            assert nm_before == nm_after, "Seeder modified neuromodulators"

    def test_factory_seeds_before_first_tick_by_default(self):
        agent = create_procurement_agent("seeded", rng=random.Random(5))
        assert len(agent.hippocampus.experiences) > 0

    def test_factory_can_explicitly_disable_seeding(self):
        agent = create_procurement_agent(
            "plain", rng=random.Random(5), seed_intuition=False
        )
        assert len(agent.hippocampus.experiences) == 0

    def test_string_none_and_intent_object_are_supported(self):
        """R6: string, None, and intent objects all map without backend ifdefs."""
        trainer = _trainer(create_procurement_agent("intent", rng=random.Random(6)))
        assert trainer._intent_to_action_type("urgent_reorder") == "urgent_reorder"
        assert trainer._intent_to_action_type("wait_and_monitor") == "wait_and_monitor"
        assert trainer._intent_to_action_type(None) == "wait_and_monitor"
        intent = type("Intent", (), {"action_type": "diversify_supplier"})()
        assert trainer._intent_to_action_type(intent) == "diversify_supplier"

    def test_fallback_agent_string_return_accepted(self):
        """R6: a string-returning fallback agent completes a quarter."""
        agent = _StringFallbackAgent("wait_and_monitor")
        log = _trainer(agent, sleep_every_n_days=2)._run_single_quarter(
            _world(), n_days=3
        )
        assert agent.calls == 3
        assert len(log) == 3
        assert all(entry["action"] == "wait_and_monitor" for entry in log)
        assert all(entry["result"] is None for entry in log)
        agent.value_layer.update.assert_not_called()

    def test_three_day_run_returns_stable_log_contract(self):
        agent = create_procurement_agent("run", rng=random.Random(7))
        log = _trainer(agent, sleep_every_n_days=2)._run_single_quarter(
            _world(), n_days=3
        )
        assert len(log) == 3
        assert all(
            {"day", "action", "supplier_id", "product_id", "qty", "result"}
            <= set(entry)
            for entry in log
        )


def test_verbose_pipeline_emits_daily_diagnostics():
    messages = []
    agent = create_procurement_agent("verbose", rng=random.Random(8))
    trainer = _trainer(
        agent,
        verbose_pipeline=True,
        pipeline_logger=messages.append,
    )
    trainer._run_single_quarter(_world(days=1), n_days=1)
    assert any("context=" in message and "action=" in message for message in messages)


def test_verbose_pipeline_messages_are_ascii_safe():
    """cp1251/cp866 consoles abort on a single '→'; diagnostics must stay ASCII."""
    messages = []
    agent = create_procurement_agent("ascii", rng=random.Random(8))
    trainer = _trainer(
        agent,
        verbose_pipeline=True,
        pipeline_logger=messages.append,
    )
    world = _world(days=3)
    _force_reorder_deficit(world)
    trainer._run_single_quarter(world, n_days=3)
    assert messages, "verbose pipeline produced no lines"
    for message in messages:
        message.encode("ascii")
        assert "→" not in message
        assert "—" not in message


def test_core_step_decision_only_does_not_store_experience():
    """Hosts that record the realized episode must not get a waking duplicate."""
    agent = create_procurement_agent(
        "decision_only", rng=random.Random(9), seed_intuition=False
    )
    if not callable(getattr(agent, "step", None)):
        pytest.skip("agent has no step()")
    signature = inspect.signature(agent.step)
    if "decision_only" not in signature.parameters:
        pytest.skip("this backend does not implement decision_only")

    before = len(agent.hippocampus.experiences)
    action = agent.step(
        ["event:stock_critical_low", "domain:procurement"],
        decision_only=True,
    )
    assert isinstance(action, str)
    assert len(agent.hippocampus.experiences) == before

    agent.step(
        ["event:stock_critical_low", "domain:procurement"],
        decision_only=False,
    )
    assert len(agent.hippocampus.experiences) > before


def test_trainer_passes_decision_only_to_core_agent_step():
    agent = create_procurement_agent("flag", rng=random.Random(10))
    flags = []
    original = agent.step

    def tracked_step(*args, **kwargs):
        flags.append(kwargs.get("decision_only"))
        return original(*args, **kwargs)

    agent.step = tracked_step
    _trainer(agent)._run_single_quarter(_world(days=2), n_days=2)
    assert flags == [True, True]
