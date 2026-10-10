from agent import Agent
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager
from storage import AgentStorage


def _build_agent():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector, sleep, intent)
    return agent


def test_sleep_replay_and_bg_state_persist(tmp_path):
    agent = _build_agent()
    agent.register_action_channel("a", go_weight=0.71, nogo_weight=0.22, habit_strength=0.18)
    agent.register_action_channel("b", go_weight=0.35, nogo_weight=0.63, habit_strength=0.11)
    agent.bg_sleep_memories = {"a": [(1.0, 1.1, 0.8, 0.9)]}

    sleep = agent.sleep_manager
    sleep.replay_budget_per_sleep = 7
    sleep.max_replay_per_episode = 2
    sleep.instability_variance_threshold = 0.33
    sleep.replay_temperature_decay = 0.91
    sleep.dopamine_sleep_scale = 0.25
    sleep.edpc_priority_enabled = False
    sleep.edpc_consolidation_blend = 0.73
    sleep.shock_priority_gain = 1.4
    sleep.sac_alpha_slow = 0.008
    sleep.sac_sigma_floor = 0.02
    sleep.local_phase_mode = True
    sleep.sac_theta_arousal_low = 0.22
    sleep.sac_theta_arousal_high = 0.71
    sleep.sac_theta_shock_low = 0.12
    sleep.sac_theta_shock_high = 0.44
    sleep.sac_lambda_sws = 0.24
    sleep.sac_lambda_rem = 0.07
    sleep.sac_stability_floor_rem = 0.31
    sleep.sac_semantic_confidence_step_cap = 0.09
    sleep.sac_structural_alert_reset_cycles = 4
    sleep.last_sleep_replay_stats = {"replay_selected": 3, "replay_blocked": False}
    sleep.last_sac_stats = {"sac_actions_updated": 2}
    agent.selector.set_action_metadata(
        "a",
        {
            "expected_effect_mean": 0.25,
            "expected_effect_variance": 0.11,
            "success_alpha": 2.5,
            "success_beta": 1.2,
            "risk_estimate": 0.09,
            "semantic_confidence": 0.44,
        },
    )

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        agent.hippocampus,
        agent.cortex,
        agent.selector,
        sleep_manager=agent.sleep_manager,
        value_layer=agent.value_layer,
        agent=agent,
        filename="sleep_replay_state.pkl",
    )

    restored = _build_agent()
    storage.load_agent(
        restored.hippocampus,
        restored.cortex,
        restored.selector,
        path,
        sleep_manager=restored.sleep_manager,
        value_layer=restored.value_layer,
        agent=restored,
    )

    assert restored.sleep_manager.replay_budget_per_sleep == 7
    assert restored.sleep_manager.max_replay_per_episode == 2
    assert restored.sleep_manager.instability_variance_threshold == 0.33
    assert restored.sleep_manager.replay_temperature_decay == 0.91
    assert restored.sleep_manager.dopamine_sleep_scale == 0.25
    assert restored.sleep_manager.edpc_priority_enabled is False
    assert abs(restored.sleep_manager.edpc_consolidation_blend - 0.73) < 1e-9
    assert abs(restored.sleep_manager.shock_priority_gain - 1.4) < 1e-9
    assert abs(restored.sleep_manager.sac_alpha_slow - 0.008) < 1e-9
    assert abs(restored.sleep_manager.sac_sigma_floor - 0.02) < 1e-9
    assert restored.sleep_manager.local_phase_mode is True
    assert abs(restored.sleep_manager.sac_theta_arousal_low - 0.22) < 1e-9
    assert abs(restored.sleep_manager.sac_theta_arousal_high - 0.71) < 1e-9
    assert abs(restored.sleep_manager.sac_theta_shock_low - 0.12) < 1e-9
    assert abs(restored.sleep_manager.sac_theta_shock_high - 0.44) < 1e-9
    assert abs(restored.sleep_manager.sac_lambda_sws - 0.24) < 1e-9
    assert abs(restored.sleep_manager.sac_lambda_rem - 0.07) < 1e-9
    assert abs(restored.sleep_manager.sac_stability_floor_rem - 0.31) < 1e-9
    assert abs(restored.sleep_manager.sac_semantic_confidence_step_cap - 0.09) < 1e-9
    assert int(restored.sleep_manager.sac_structural_alert_reset_cycles) == 4
    assert restored.sleep_manager.last_sleep_replay_stats.get("replay_selected") == 3
    assert restored.sleep_manager.last_sac_stats.get("sac_actions_updated") == 2
    assert restored.selector.action_metadata["a"]["expected_effect_mean"] == 0.25
    assert restored.selector.action_metadata["a"]["expected_effect_variance"] == 0.11
    assert restored.selector.action_metadata["a"]["semantic_confidence"] == 0.44
    assert "a" in restored.bg_action_channels
    assert "b" in restored.bg_action_channels
    assert abs(restored.bg_action_channels["a"].go_weight - 0.71) < 1e-9
    assert abs(restored.bg_action_channels["a"].nogo_weight - 0.22) < 1e-9
    assert abs(restored.bg_action_channels["b"].habit_strength - 0.11) < 1e-9
    assert "a" in restored.bg_sleep_memories
