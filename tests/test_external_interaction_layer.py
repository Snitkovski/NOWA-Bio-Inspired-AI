import asyncio
import time

import pytest

from agent import Agent
from cortex import CortexMemory
from external_interaction_layer import (
    AsyncInteractionScheduler,
    ExternalInteractionLayer,
    Feedback,
    Hypothesis,
    Observation,
)
from hippocampus import NOWAHippocampus
from selector import ActionSelector
from sleep import SleepManager


class _AsyncEnvironmentStub:
    def __init__(self):
        self.execute_calls = []
        self.observe_calls = 0

    async def execute(self, action):
        self.execute_calls.append(action)
        await asyncio.sleep(0.01)
        reward = float(action.parameters.get("reward", 0.8))
        return Feedback(
            reward=reward,
            signal={"ok": True},
            success_probability=0.85,
            latency=0.0,
        )

    async def observe(self):
        self.observe_calls += 1
        await asyncio.sleep(0.01)
        return Observation(
            timestamp=time.time(),
            source="env_sensor",
            payload={"signal": self.observe_calls},
            uncertainty=0.2,
        )


def _build_agent():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["explore", "rest"])
    sleep_manager = SleepManager(hip, cortex)
    return Agent(hip, cortex, selector, sleep_manager=sleep_manager)


def test_observation_history_clamp_and_interpretation():
    layer = ExternalInteractionLayer(history_limit=2)

    first = layer.observe("sensor", {"x": 1}, uncertainty=1.4, timestamp=1.0)
    second = layer.observe("sensor", {"x": 2}, uncertainty=0.5, timestamp=2.0)
    third = layer.observe("sensor", {"x": 3}, uncertainty=0.2, timestamp=3.0)

    assert first.uncertainty == pytest.approx(1.0)
    history = layer.recent_observations()
    assert len(history) == 2
    assert history[0].timestamp == pytest.approx(second.timestamp)
    assert history[1].timestamp == pytest.approx(third.timestamp)

    interpreted = layer.interpret_observation(third)
    assert interpreted["confidence"] == pytest.approx(0.8)
    assert interpreted["probability"]["noise"] == pytest.approx(0.2)


def test_execute_action_feedback_model():
    async def _run():
        layer = ExternalInteractionLayer()
        env = _AsyncEnvironmentStub()
        action = layer.build_action("explore", parameters={"reward": 0.7})
        return await layer.execute_action(action, env)

    feedback = asyncio.run(_run())
    assert isinstance(feedback, Feedback)
    assert feedback.reward == pytest.approx(0.7)
    assert feedback.success_probability == pytest.approx(0.85)
    assert feedback.latency >= 0.0
    assert feedback.signal.get("action_type") == "explore"


def test_delayed_feedback_resolution_and_learning_hooks():
    layer = ExternalInteractionLayer()
    feedback = Feedback(reward=0.6, signal={"source": "test"}, success_probability=0.9, latency=0.1)
    hypothesis = Hypothesis(name="explore_success", prior=0.4)

    layer.queue_feedback(feedback=feedback, delay_steps=2, current_step=5, hypothesis=hypothesis)
    early = layer.resolve_feedback(current_step=6)
    assert early == []

    ready = layer.resolve_feedback(current_step=7)
    assert len(ready) == 1

    drives = {"curiosity": 0.2, "social_drive": 0.7}
    strategies = {"explore": 0.1, "rest": 0.1}
    updates = layer.apply_learning_hooks(
        feedback=ready[0].feedback,
        drives=drives,
        strategies=strategies,
        alpha=0.2,
        learning_rate=0.05,
        predicted_reward={"explore": 0.2, "rest": 0.8},
        hypothesis=ready[0].hypothesis,
    )

    assert drives["curiosity"] > 0.2
    assert 0.0 <= drives["social_drive"] <= 1.0
    assert strategies["explore"] > strategies["rest"]
    assert sum(strategies.values()) == pytest.approx(1.0, abs=1e-6)
    assert updates["strategy_temperature"] > 0.0
    assert float(updates["hypothesis_posterior"]) > 0.4


def test_hypothesis_update_supports_explicit_not_h_likelihood():
    hypothesis = Hypothesis(name="h", prior=0.4)
    posterior = hypothesis.recalibrate(
        evidence_likelihood=0.9,
        evidence_likelihood_not_h=0.7,
    )
    # Compared with the implicit complement model, explicit high P(E|~H) should be more conservative.
    posterior_implicit = Hypothesis(name="h2", prior=0.4).recalibrate(
        evidence_likelihood=0.9
    )
    assert posterior < posterior_implicit


def test_drive_strategy_coupling_modulates_policy_even_with_neutral_reward():
    layer = ExternalInteractionLayer()
    feedback = Feedback(reward=0.0, signal={"source": "neutral"}, success_probability=0.5, latency=0.0)
    drives = {"curiosity": 0.95, "social_drive": 0.05}
    strategies = {"explore": 0.0, "rest": 0.0}
    coupling = {
        "explore": {"curiosity": 1.0, "social_drive": -0.5},
        "rest": {"social_drive": 1.0, "curiosity": -0.5},
    }

    updates = layer.apply_learning_hooks(
        feedback=feedback,
        drives=drives,
        strategies=strategies,
        alpha=0.0,
        learning_rate=0.4,
        predicted_reward={"explore": 0.0, "rest": 0.0},
        strategy_drive_coupling=coupling,
        drive_policy_gain=1.0,
        strategy_weight_decay=0.0,
        strategy_temperature=0.7,
    )

    assert strategies["explore"] > strategies["rest"]
    assert sum(strategies.values()) == pytest.approx(1.0, abs=1e-6)
    assert updates["strategy_drive_signal"]["explore"] > updates["strategy_drive_signal"]["rest"]


def test_selector_pressures_reflect_strategy_policy_weights():
    selector = ActionSelector(actions=["explore", "rest"])
    selector.action_metadata["explore"]["strategy_weight"] = 0.9
    selector.action_metadata["rest"]["strategy_weight"] = 0.1

    pressures = selector.compute_pressures(
        hippocampal_exps=[],
        cortical_patterns=[],
        intent_pressure=None,
    )

    assert pressures["explore"] > pressures["rest"]


def test_agent_builds_drive_to_strategy_coupling_from_action_metadata():
    agent = _build_agent()
    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable")

    runtime.drive_system.drives["curiosity"] = 0.9
    runtime.drive_system.drives["social_drive"] = 0.1

    agent.selector.set_action_metadata(
        "explore",
        {
            "predicted_effect": {
                "drives": {"curiosity": -0.7},
            }
        },
    )
    agent.selector.set_action_metadata(
        "rest",
        {
            "predicted_effect": {
                "drives": {"curiosity": 0.4},
            }
        },
    )

    updates = agent._apply_external_feedback_learning(
        feedback=Feedback(
            reward=0.0,
            signal={"source": "neutral"},
            success_probability=0.5,
            latency=0.0,
        ),
        predicted_reward={"explore": 0.0, "rest": 0.0},
        hypothesis=None,
    )

    strategy_updates = dict(updates.get("strategy_updates", {}) or {})
    assert strategy_updates.get("explore", 0.0) > strategy_updates.get("rest", 0.0)


def test_async_scheduler_non_blocking_observation_and_parallel_simulation():
    async def _scenario():
        layer = ExternalInteractionLayer()
        env = _AsyncEnvironmentStub()
        scheduler = AsyncInteractionScheduler(
            layer=layer,
            environment_interface=env,
            max_parallel_simulations=3,
        )

        task = scheduler.poll_observation_non_blocking()
        assert task is not None
        assert not task.done()
        observed = await task
        assert observed is not None
        assert observed.source == "env_sensor"
        assert len(layer.recent_observations()) == 1

        async def _simulate(active_drive, now, dt=1.0, live_drives=None):
            await asyncio.sleep(0.05)
            return {"active_drive": active_drive, "best_action": f"{active_drive}:a", "timestamp": now}

        scheduler.set_simulation_callback(_simulate)
        requests = [
            {"active_drive": "curiosity", "now": 1.0},
            {"active_drive": "social_drive", "now": 1.5},
            {"active_drive": "exploration", "now": 2.0},
        ]
        started = time.perf_counter()
        results = await scheduler.schedule_parallel_simulations(requests)
        elapsed = time.perf_counter() - started

        assert len(results) == 3
        assert elapsed < 0.13
        return results

    results = asyncio.run(_scenario())
    assert all("best_action" in item for item in results)


def test_agent_external_action_execution_updates_strategy_weights():
    agent = _build_agent()
    env = _AsyncEnvironmentStub()
    agent.set_environment_interface(env)

    result = asyncio.run(
        agent.execute_external_action(
            action_type="explore",
            parameters={"reward": 0.9},
            predicted_reward={"explore": 0.1},
        )
    )

    assert result["queued"] is False
    assert isinstance(result["feedback"], Feedback)
    weights = agent.external_interaction_layer.get_strategy_weights()
    assert "explore" in weights
    assert weights["explore"] > 0.0


def test_agent_delayed_feedback_resolution_pipeline():
    agent = _build_agent()
    env = _AsyncEnvironmentStub()
    agent.set_environment_interface(env)

    queued = asyncio.run(
        agent.execute_external_action(
            action_type="explore",
            parameters={"reward": 0.6},
            delay_feedback_steps=2,
            predicted_reward={"explore": 0.0},
        )
    )
    assert queued["queued"] is True

    unresolved = agent.resolve_external_feedback(current_step=1)
    assert unresolved["resolved_count"] == 0

    resolved = agent.resolve_external_feedback(current_step=2)
    assert resolved["resolved_count"] == 1
    assert len(resolved["learning_updates"]) == 1


def test_agent_parallel_internal_simulation_integration():
    agent = _build_agent()
    runtime = agent.init_autonomous_runtime()
    if runtime is None:
        pytest.skip("autonomous runtime unavailable")

    requests = [
        {
            "active_drive": "curiosity",
            "now": 1.0,
            "dt": 0.5,
            "live_drives": {"curiosity": 0.7},
        },
        {
            "active_drive": "social_drive",
            "now": 1.5,
            "dt": 0.5,
            "live_drives": {"social_drive": 0.8},
        },
    ]
    results = asyncio.run(agent.run_parallel_internal_simulations(requests))

    assert len(results) == 2
    for item in results:
        assert isinstance(item, dict)
        assert "best_action" in item


def test_agent_non_blocking_external_observation_polling():
    agent = _build_agent()
    env = _AsyncEnvironmentStub()
    agent.set_environment_interface(env)

    async def _scenario():
        task = agent.poll_external_observation_non_blocking()
        assert task is not None
        observed = await task
        assert observed is not None
        return observed

    observed = asyncio.run(_scenario())
    history = agent.get_external_observation_history(limit=1)

    assert observed.source == "env_sensor"
    assert len(history) == 1
    assert history[0].source == "env_sensor"


def test_agent_external_state_snapshot_and_single_poll():
    agent = _build_agent()
    env = _AsyncEnvironmentStub()
    agent.set_environment_interface(env)

    before = agent.get_external_interaction_state()
    assert int(before["observation_history"]) == 0
    assert int(before["pending_feedback"]) == 0

    observed = asyncio.run(agent.poll_external_observation_once())
    assert observed is not None

    after = agent.get_external_interaction_state()
    assert int(after["observation_history"]) == 1
    assert int(after["pending_feedback"]) == 0
    assert int(after["current_step"]) >= 1


def test_external_current_step_tracks_agent_lived_steps():
    agent = _build_agent()
    initial = agent.get_external_interaction_state()
    assert int(initial["current_step"]) == int(agent.lived_steps)

    agent.step(["ctx_step_sync"])
    state_after_step = agent.get_external_interaction_state()
    assert int(state_after_step["current_step"]) == int(agent.lived_steps)


def test_external_current_step_advances_without_agent_step():
    agent = _build_agent()
    state_before = agent.get_external_interaction_state()
    assert int(state_before["current_step"]) == 0

    agent.observe_external_input(
        source="manual",
        payload={"event": "manual"},
        uncertainty=0.1,
    )
    state_after_observation = agent.get_external_interaction_state()
    assert int(state_after_observation["current_step"]) == 1
    assert int(agent.lived_steps) == 0
