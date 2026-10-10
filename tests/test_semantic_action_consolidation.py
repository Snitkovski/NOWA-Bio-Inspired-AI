import pytest

from agent import Agent
from experience import Event, EventType
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager


def _build_agent(actions=("act",)):
    hip = NOWAHippocampus(max_experiences=4000)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(hip, cortex, selector, sleep, intent)
    sleep._rng.seed(0)
    return agent


def _configure_for_phase_spec(agent: Agent) -> SleepManager:
    sleep = agent.sleep_manager
    sleep.td_threshold = 0.0
    sleep.salience_threshold = 0.0
    sleep.td_variance_cap = 1.0
    sleep.min_reinforcement_for_consolidation = 1
    sleep.ach_min_for_consolidation = 0.0
    sleep.replay_budget_per_sleep = 256
    sleep.max_replay_per_episode = 1
    sleep.instability_variance_threshold = 10.0
    sleep.sac_theta_min_weight = 0.0
    sleep.sac_replay_min_count = 3
    sleep.sac_alpha_slow = 0.01
    sleep.sac_alpha_base = 0.01
    sleep.sac_alpha_sigma = 0.01
    sleep.sac_theta_arousal_low = 0.2
    sleep.sac_theta_arousal_high = 0.6
    sleep.sac_theta_shock_low = 0.1
    sleep.sac_theta_shock_high = 0.3
    sleep.sac_theta_conf_high = 0.7
    sleep.sac_theta_cons_high = 0.7
    sleep.sac_theta_stability_high = 0.7
    sleep.sac_sigma_decay_sws = 0.25
    sleep.sac_epsilon_var_rem = 0.03
    sleep.sac_beta_stability_sws = 0.05
    sleep.sac_delta_rem = 0.20
    sleep.sac_stability_floor_rem = 0.2
    sleep.sac_lambda_sws = 0.25
    sleep.sac_lambda_rem = 0.08
    sleep.sac_semantic_confidence_step_cap = 0.2
    sleep.sac_theta_structural = 0.8
    sleep.sac_structural_alert_reset_cycles = 3
    sleep.local_phase_mode = False
    agent.hippocampus.consolidation_min_probability = 0.0
    return sleep


def _seed_action_meta(
    agent: Agent,
    action_id: str,
    *,
    mean: float = 0.0,
    variance: float = 0.2,
    semantic_confidence: float = 0.2,
    stability_score: float = 0.7,
):
    agent.selector.set_action_metadata(
        action_id,
        {
            "expected_effect_mean": float(mean),
            "expected_effect_variance": float(variance),
            "success_alpha": 1.0,
            "success_beta": 1.0,
            "risk_estimate": 0.3,
            "semantic_confidence": float(semantic_confidence),
            "stability_score": float(stability_score),
        },
    )


def _step(agent: Agent, context: str, reward: float):
    agent.step(
        context_events=[context],
        consequence=Event(f"feedback:{reward:+.2f}", EventType.CONSEQUENCE),
        intensity=1.0,
        reward=reward,
        novelty=1.0,
        conflict=0.0,
    )


def _mark_for_replay(
    agent: Agent,
    *,
    action_id: str,
    confidence: float,
    stability: float,
    shock_score: float,
    arousal: float,
    consolidation_probability: float,
    replay_priority: float,
    td_error: float,
    observed_outcome: float,
    predicted_outcome: float,
):
    exp = agent.hippocampus.experiences[-1]
    exp.reinforcement_count = max(3, int(getattr(exp, "reinforcement_count", 1)))
    exp.replay_action_id = str(action_id)
    exp.expectation_confidence_score = float(confidence)
    exp.expectation_stability_score = float(stability)
    exp.prediction_shock_score = float(shock_score)
    exp.prediction_shock_flag = bool(shock_score >= 0.5)
    exp.arousal = float(arousal)
    exp.consolidation_probability = float(consolidation_probability)
    exp.replay_priority = float(replay_priority)
    exp.td_error_snapshot = float(td_error)
    exp.replay_salience = 1.0
    exp.replay_importance = 1.0
    exp.reward = float(observed_outcome)
    exp.expected_reward_mean = float(predicted_outcome)
    exp.stability_flag = True
    return exp


def test_sac_phase_sws_updates_sigma_and_stability_monotonic():
    agent = _build_agent(actions=("sws",))
    _configure_for_phase_spec(agent)
    _seed_action_meta(agent, "sws", variance=0.12, stability_score=0.70)

    for i in range(8):
        _step(agent, context=f"ctx_sws_{i}", reward=0.9)
        _mark_for_replay(
            agent,
            action_id="sws",
            confidence=0.90,
            stability=0.90,
            shock_score=0.05,
            arousal=0.10,
            consolidation_probability=0.90,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.9,
            predicted_outcome=0.2,
        )

    before = dict(agent.selector.action_metadata["sws"])
    stats = agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["sws"])

    assert stats["sac_phase"] == "SWS"
    assert stats["phase_distribution"]["SWS"] >= 1
    assert after["expected_effect_variance"] <= before["expected_effect_variance"] + 1e-9
    assert after["stability_score"] >= before["stability_score"]
    assert stats["structural_alert_count"] == 0


def test_sac_phase_rem_high_shock_expands_sigma_and_reduces_stability():
    agent = _build_agent(actions=("rem",))
    _configure_for_phase_spec(agent)
    _seed_action_meta(agent, "rem", variance=0.04, stability_score=0.80)

    for i in range(8):
        _step(agent, context=f"ctx_rem_{i}", reward=0.2 if i % 2 == 0 else -0.4)
        _mark_for_replay(
            agent,
            action_id="rem",
            confidence=0.85,
            stability=0.85,
            shock_score=0.35,
            arousal=0.80,
            consolidation_probability=0.85,
            replay_priority=1.0,
            td_error=0.6 if i % 2 == 0 else -0.6,
            observed_outcome=0.2 if i % 2 == 0 else -0.4,
            predicted_outcome=0.0,
        )

    before = dict(agent.selector.action_metadata["rem"])
    stats = agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["rem"])

    assert stats["sac_phase"] == "REM"
    assert stats["phase_distribution"]["REM"] >= 1
    assert after["expected_effect_variance"] >= before["expected_effect_variance"] - 1e-9
    assert after["stability_score"] <= before["stability_score"] + 1e-9
    assert stats["structural_alert_count"] == 0


def test_sac_phase_transitional_keeps_stability_unchanged():
    agent = _build_agent(actions=("mix",))
    _configure_for_phase_spec(agent)
    _seed_action_meta(agent, "mix", variance=0.11, stability_score=0.72)

    for i in range(8):
        _step(agent, context=f"ctx_mix_{i}", reward=0.5)
        _mark_for_replay(
            agent,
            action_id="mix",
            confidence=0.85,
            stability=0.75,
            shock_score=0.15,
            arousal=0.30,
            consolidation_probability=0.85,
            replay_priority=1.0,
            td_error=0.3,
            observed_outcome=0.5,
            predicted_outcome=0.2,
        )

    before = dict(agent.selector.action_metadata["mix"])
    stats = agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["mix"])

    assert stats["sac_phase"] == "TRANSITIONAL"
    assert stats["phase_distribution"]["TRANSITIONAL"] >= 1
    assert after["stability_score"] == pytest.approx(before["stability_score"])


def test_sac_episode_gating_blocks_low_confidence_even_if_batch_is_sws_like():
    agent = _build_agent(actions=("gate_conf",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_theta_conf = 0.6
    _seed_action_meta(agent, "gate_conf", variance=0.11, stability_score=0.72)

    for i in range(8):
        _step(agent, context=f"ctx_gate_conf_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="gate_conf",
            confidence=0.2,
            stability=0.9,
            shock_score=0.05,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.3,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )

    before = dict(agent.selector.action_metadata["gate_conf"])
    stats = agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["gate_conf"])

    assert stats["sac_rejected_confidence"] >= 1
    assert stats["sac_actions_updated"] == 0
    assert after["expected_effect_mean"] == pytest.approx(before["expected_effect_mean"])


def test_sac_global_phase_reflects_effective_updates_not_potential_rows():
    agent = _build_agent(actions=("phase_a", "phase_b"))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_replay_min_count = 5
    _seed_action_meta(agent, "phase_a", variance=0.1, stability_score=0.7)
    _seed_action_meta(agent, "phase_b", variance=0.1, stability_score=0.7)

    for i in range(4):
        _step(agent, context=f"ctx_phase_a_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="phase_a",
            confidence=0.9,
            stability=0.9,
            shock_score=0.05,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )
    for i in range(4):
        _step(agent, context=f"ctx_phase_b_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="phase_b",
            confidence=0.9,
            stability=0.9,
            shock_score=0.05,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )

    stats = agent.sleep(cycles=1)

    assert stats["sac_actions_updated"] == 0
    assert stats["sac_rejected_replay_count"] >= 2
    assert stats["sac_phase"] == "TRANSITIONAL"
    assert stats["phase_distribution"]["SWS"] == 0


def test_sac_sigma_floor_protection_in_sws():
    agent = _build_agent(actions=("floor",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_sigma_floor = 0.01
    _seed_action_meta(agent, "floor", variance=0.02, stability_score=0.75)

    for i in range(8):
        _step(agent, context=f"ctx_floor_{i}", reward=0.9)
        _mark_for_replay(
            agent,
            action_id="floor",
            confidence=0.95,
            stability=0.9,
            shock_score=0.01,
            arousal=0.1,
            consolidation_probability=0.95,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.9,
            predicted_outcome=0.0,
        )

    stats = agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["floor"])

    assert stats["sac_phase"] == "SWS"
    assert after["expected_effect_variance"] >= sleep.sac_sigma_floor


def test_sac_rem_stability_floor_prevents_collapse():
    agent = _build_agent(actions=("rem_floor",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_delta_rem = 0.5
    sleep.sac_stability_floor_rem = 0.4
    _seed_action_meta(agent, "rem_floor", variance=0.08, stability_score=0.9)

    for cycle in range(8):
        for i in range(6):
            _step(agent, context=f"ctx_rem_floor_{cycle}_{i}", reward=-0.4)
            _mark_for_replay(
                agent,
                action_id="rem_floor",
                confidence=0.9,
                stability=0.9,
                shock_score=0.35,
                arousal=0.85,
                consolidation_probability=0.9,
                replay_priority=1.0,
                td_error=-0.6,
                observed_outcome=-0.4 + (0.02 * cycle),
                predicted_outcome=0.2,
            )
        agent.sleep(cycles=1)

    meta = dict(agent.selector.action_metadata["rem_floor"])
    assert meta["stability_score"] >= sleep.sac_stability_floor_rem - 1e-9
    assert meta["stability_score"] <= 0.9 + 1e-9


def test_sac_structural_alert_triggers_when_prediction_shock_exceeds_threshold():
    agent = _build_agent(actions=("alert",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_theta_shock = 0.95
    sleep.sac_shock_block_threshold = 0.95
    sleep.sac_theta_structural = 0.8
    _seed_action_meta(agent, "alert", variance=0.06, stability_score=0.75)

    for i in range(6):
        _step(agent, context=f"ctx_alert_{i}", reward=-0.2)
        _mark_for_replay(
            agent,
            action_id="alert",
            confidence=0.82,
            stability=0.8,
            shock_score=0.9,
            arousal=0.85,
            consolidation_probability=0.8,
            replay_priority=1.0,
            td_error=-0.5,
            observed_outcome=-0.2,
            predicted_outcome=0.1,
        )

    stats = agent.sleep(cycles=1)
    meta = dict(agent.selector.action_metadata["alert"])

    assert stats["sac_phase"] == "REM"
    assert stats["structural_alert_count"] >= 1
    assert meta.get("structural_alert") is True


def test_sac_structural_alert_resets_after_calm_cycles():
    agent = _build_agent(actions=("alert_reset",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_theta_shock = 0.95
    sleep.sac_shock_block_threshold = 0.95
    sleep.sac_structural_alert_reset_cycles = 3
    sleep.sac_theta_structural = 0.8
    _seed_action_meta(agent, "alert_reset", variance=0.06, stability_score=0.75)

    for i in range(6):
        _step(agent, context=f"ctx_alert_reset_hot_{i}", reward=-0.2)
        _mark_for_replay(
            agent,
            action_id="alert_reset",
            confidence=0.85,
            stability=0.85,
            shock_score=0.9,
            arousal=0.9,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=-0.5,
            observed_outcome=-0.2,
            predicted_outcome=0.1,
        )
    agent.sleep(cycles=1)
    assert bool(agent.selector.action_metadata["alert_reset"].get("structural_alert", False)) is True

    for cycle in range(3):
        for i in range(6):
            _step(agent, context=f"ctx_alert_reset_calm_{cycle}_{i}", reward=-0.1)
            _mark_for_replay(
                agent,
                action_id="alert_reset",
                confidence=0.85,
                stability=0.85,
                shock_score=0.2,
                arousal=0.85,
                consolidation_probability=0.9,
                replay_priority=1.0,
                td_error=-0.3,
                observed_outcome=-0.1,
                predicted_outcome=0.1,
            )
        agent.hippocampus.experiences = list(agent.hippocampus.experiences[-6:])
        agent.sleep(cycles=1)

    meta = dict(agent.selector.action_metadata["alert_reset"])
    assert bool(meta.get("structural_alert", True)) is False
    assert int(meta.get("structural_alert_calm_streak", -1)) == 0


def test_sac_semantic_confidence_step_cap_limits_growth():
    agent = _build_agent(actions=("sem_cap",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_semantic_confidence_step_cap = 0.02
    _seed_action_meta(
        agent,
        "sem_cap",
        variance=0.1,
        stability_score=0.8,
        semantic_confidence=0.1,
    )

    for i in range(8):
        _step(agent, context=f"ctx_sem_cap_{i}", reward=0.95)
        _mark_for_replay(
            agent,
            action_id="sem_cap",
            confidence=0.98,
            stability=0.95,
            shock_score=0.05,
            arousal=0.1,
            consolidation_probability=0.95,
            replay_priority=1.0,
            td_error=0.5,
            observed_outcome=0.95,
            predicted_outcome=0.1,
        )

    before = dict(agent.selector.action_metadata["sem_cap"])
    agent.sleep(cycles=1)
    after = dict(agent.selector.action_metadata["sem_cap"])
    delta = float(after["semantic_confidence"]) - float(before["semantic_confidence"])

    assert delta <= 0.02 + 1e-9


def test_sac_local_phase_mode_supports_mixed_phases_per_action():
    agent = _build_agent(actions=("sws_local", "rem_local"))
    sleep = _configure_for_phase_spec(agent)
    sleep.local_phase_mode = True
    _seed_action_meta(agent, "sws_local", variance=0.10, stability_score=0.7)
    _seed_action_meta(agent, "rem_local", variance=0.10, stability_score=0.7)

    for i in range(6):
        _step(agent, context=f"ctx_loc_sws_{i}", reward=0.9)
        _mark_for_replay(
            agent,
            action_id="sws_local",
            confidence=0.9,
            stability=0.9,
            shock_score=0.05,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.9,
            predicted_outcome=0.2,
        )

    for i in range(6):
        _step(agent, context=f"ctx_loc_rem_{i}", reward=-0.4)
        _mark_for_replay(
            agent,
            action_id="rem_local",
            confidence=0.85,
            stability=0.85,
            shock_score=0.35,
            arousal=0.8,
            consolidation_probability=0.85,
            replay_priority=1.0,
            td_error=-0.6,
            observed_outcome=-0.4,
            predicted_outcome=0.0,
        )

    stats = agent.sleep(cycles=1)
    sws_meta = dict(agent.selector.action_metadata["sws_local"])
    rem_meta = dict(agent.selector.action_metadata["rem_local"])

    assert stats["phase_distribution"]["SWS"] >= 1
    assert stats["phase_distribution"]["REM"] >= 1
    assert sws_meta.get("sac_phase") == "SWS"
    assert rem_meta.get("sac_phase") == "REM"
    assert sum(bool(sws_meta.get(flag, False)) for flag in ("applied_sws_rule", "applied_rem_rule", "applied_transitional_rule")) == 1
    assert sum(bool(rem_meta.get(flag, False)) for flag in ("applied_sws_rule", "applied_rem_rule", "applied_transitional_rule")) == 1


def test_sac_rejects_invalid_phase_threshold_invariants():
    agent = _build_agent(actions=("inv",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_theta_arousal_low = 0.8
    sleep.sac_theta_arousal_high = 0.2
    _seed_action_meta(agent, "inv", variance=0.1, stability_score=0.7)

    for i in range(4):
        _step(agent, context=f"ctx_inv_{i}", reward=0.7)
        _mark_for_replay(
            agent,
            action_id="inv",
            confidence=0.9,
            stability=0.9,
            shock_score=0.0,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.4,
            observed_outcome=0.7,
            predicted_outcome=0.1,
        )

    with pytest.raises(ValueError, match="theta_arousal_low"):
        agent.sleep(cycles=1)


def test_sac_rejects_alpha_slow_hard_constraint_violation():
    agent = _build_agent(actions=("drift",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_alpha_slow = 0.1
    _seed_action_meta(agent, "drift", variance=0.1, stability_score=0.7)

    for i in range(4):
        _step(agent, context=f"ctx_drift_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="drift",
            confidence=0.9,
            stability=0.9,
            shock_score=0.0,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.5,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )

    with pytest.raises(ValueError, match="sac_alpha_slow"):
        agent.sleep(cycles=1)


def test_sac_rejects_alpha_base_hard_constraint_violation():
    agent = _build_agent(actions=("alpha_base",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_alpha_base = 0.02
    _seed_action_meta(agent, "alpha_base", variance=0.1, stability_score=0.7)

    for i in range(4):
        _step(agent, context=f"ctx_alpha_base_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="alpha_base",
            confidence=0.9,
            stability=0.9,
            shock_score=0.0,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.5,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )

    with pytest.raises(ValueError, match="sac_alpha_base"):
        agent.sleep(cycles=1)


def test_sac_rejects_lambda_order_hard_constraint_violation():
    agent = _build_agent(actions=("lambda",))
    sleep = _configure_for_phase_spec(agent)
    sleep.sac_lambda_sws = 0.1
    sleep.sac_lambda_rem = 0.1
    _seed_action_meta(agent, "lambda", variance=0.1, stability_score=0.7)

    for i in range(4):
        _step(agent, context=f"ctx_lambda_{i}", reward=0.8)
        _mark_for_replay(
            agent,
            action_id="lambda",
            confidence=0.9,
            stability=0.9,
            shock_score=0.0,
            arousal=0.1,
            consolidation_probability=0.9,
            replay_priority=1.0,
            td_error=0.5,
            observed_outcome=0.8,
            predicted_outcome=0.2,
        )

    with pytest.raises(ValueError, match="sac_lambda_sws"):
        agent.sleep(cycles=1)
