from experience import Event, EventType, Path
from agent import Agent
from basal_ganglia import BasalGangliaGate
from cortex import CortexMemory
from emotional_regulation import EmotionalRegulationLayer
from hippocampus import NOWAHippocampus
from selector import ActionSelector


def _build_path(*tokens: str) -> Path:
    path = Path()
    for token in tokens:
        evt_type = EventType.ACTION if str(token).startswith("action:") else EventType.CONTEXT
        path = path.add_event(Event(str(token), evt_type))
    return path


def test_cer_modulates_bg_threshold_and_temperature():
    low_state = EmotionalRegulationLayer()
    for _ in range(30):
        low_snapshot = low_state.update(
            reward_signal=0.4,
            prediction_error=0.05,
            novelty_score=0.1,
            policy_entropy=0.1,
            resolution_success=0.7,
        )

    high_state = EmotionalRegulationLayer()
    for _ in range(40):
        high_snapshot = high_state.update(
            reward_signal=-0.2,
            prediction_error=0.6,
            novelty_score=0.4,
            policy_entropy=0.95,
            resolution_success=0.0,
        )

    low_factors = low_snapshot["modulation_factors"]
    high_factors = high_snapshot["modulation_factors"]

    bg = BasalGangliaGate(threshold=0.0)
    pressure = {"a": 0.15, "b": 0.12, "c": 0.10}
    common = {
        "pressure_vector": pressure,
        "dopamine_level": 0.2,
        "cortisol_level": 0.1,
        "norepinephrine_level": 0.2,
        "habit_strengths": {"a": 0.0, "b": 0.0, "c": 0.0},
        "aversive_signal": 0.1,
    }

    low_gated = bg.process(
        **common,
        exploration_bias=low_factors["exploration_bias"],
        decision_threshold_shift=low_factors["decision_threshold_shift"],
    )
    high_gated = bg.process(
        **common,
        exploration_bias=high_factors["exploration_bias"],
        decision_threshold_shift=high_factors["decision_threshold_shift"],
    )

    low_sum = sum(low_gated.values())
    high_sum = sum(high_gated.values())
    assert high_factors["decision_threshold_shift"] > low_factors["decision_threshold_shift"]
    assert high_sum < low_sum

    temp_base = bg.thalamic_gate.temperature_from_ne(0.2, exploration_bias=0.0)
    temp_low = bg.thalamic_gate.temperature_from_ne(0.2, exploration_bias=low_factors["exploration_bias"])
    assert temp_low >= temp_base


def test_cer_novelty_sensitivity_scales_hippocampus_novelty():
    hip = NOWAHippocampus()
    hip.store(_build_path("ctx:a", "action:x"))
    hip.store(_build_path("ctx:b", "action:y"))

    query = {"features": {"ctx:a", "ctx:c", "action:z"}}

    hip.set_novelty_sensitivity_scale(1.0)
    base = hip.recall_signature(query)["novelty_score"]

    hip.set_novelty_sensitivity_scale(0.5)
    low = hip.recall_signature(query)["novelty_score"]

    hip.set_novelty_sensitivity_scale(1.5)
    high = hip.recall_signature(query)["novelty_score"]

    assert 0.0 <= low <= 1.0
    assert 0.0 <= base <= 1.0
    assert 0.0 <= high <= 1.0
    assert low <= base <= high


def test_agent_applies_cer_learning_rate_scale_to_value_layer():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector)

    captured = {}
    base_alpha = float(
        getattr(
            agent.value_layer,
            "alpha_online_default",
            getattr(agent.value_layer, "alpha_default", 0.03),
        )
    )
    agent.emotional_regulation.modulation_factors["learning_rate_scale"] = 1.7

    original_update = agent.value_layer.update

    def _wrapped_update(*args, **kwargs):
        captured["alpha"] = float(kwargs.get("alpha", 0.0))
        return original_update(*args, **kwargs)

    agent.value_layer.update = _wrapped_update

    agent.step(["ctx:test"], reward=0.2, novelty=0.1, conflict=0.0)

    assert "alpha" in captured
    assert captured["alpha"] > base_alpha
    assert abs(captured["alpha"] - (base_alpha * 1.7)) < 1e-9


def test_bg_cer_exploration_bonus_is_bounded_by_pressure_cap():
    bg = BasalGangliaGate(
        threshold=0.0,
        cer_bonus_gain=0.6,
        cer_bonus_cap_abs=0.05,
        cer_go_pressure_cap_ratio=1.8,
    )
    gated = bg.process(
        pressure_vector={"weak": 0.02},
        dopamine_level=0.2,
        cortisol_level=0.0,
        norepinephrine_level=0.1,
        habit_strengths={"weak": 0.0},
        aversive_signal=0.0,
        exploration_bias=1.5,
        decision_threshold_shift=0.0,
    )

    assert "weak" in gated
    assert bg.last_uncertainty_bonus["weak"] <= bg.cer_bonus_cap_abs + 1e-9
    assert bg.last_go["weak"] <= bg.last_go_cap["weak"] + 1e-9


def test_cer_habit_gain_scale_amplifies_habitual_channel_in_bg():
    bg = BasalGangliaGate(threshold=0.0)
    common = {
        "pressure_vector": {"habitual": 0.02, "other": 0.02},
        "dopamine_level": 0.1,
        "cortisol_level": 0.0,
        "norepinephrine_level": 0.1,
        "habit_strengths": {"habitual": 0.8, "other": 0.0},
        "aversive_signal": 0.0,
        "exploration_bias": 0.0,
        "decision_threshold_shift": 0.0,
    }

    baseline = bg.process(**common, habit_gain_scale=1.0)
    stressed = bg.process(**common, habit_gain_scale=1.5)

    assert stressed["habitual"] > baseline["habitual"]
    assert bg.last_habit_gain_scale == 1.5


def test_cer_outputs_and_applies_bounded_neuromodulator_guidance():
    layer = EmotionalRegulationLayer()
    for _ in range(80):
        snapshot = layer.update(
            reward_signal=-0.3,
            prediction_error=0.8,
            novelty_score=0.4,
            policy_entropy=0.9,
            resolution_success=0.0,
        )

    guidance = dict(snapshot.get("neuromodulator_guidance", {}) or {})
    assert set(guidance.keys()) == {"dopamine", "norepinephrine", "serotonin", "cortisol"}
    assert any(abs(float(v)) > 0.0 for v in guidance.values())
    assert all(abs(float(v)) <= 0.006 + 1e-12 for v in guidance.values())

    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    agent = Agent(hip, cortex, selector)

    before = agent.neuromodulators.snapshot()
    layer.apply_neuromodulator_guidance(agent.neuromodulators, guidance=guidance, gain=1.0)
    after = agent.neuromodulators.snapshot()

    assert after["norepinephrine"] >= before["norepinephrine"]
    assert after["cortisol"] >= before["cortisol"]
