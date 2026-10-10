from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
import types


def test_agent_affective_space_update_with_inputs():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

    assert hasattr(agent, "affective_space")

    # Make dynamics deterministic
    for axis in agent.affective_space.noise_sigma:
        agent.affective_space.noise_sigma[axis] = 0.0
    for axis in agent.affective_space.decay:
        agent.affective_space.decay[axis] = 0.0
    for axis in agent.affective_space.inertia:
        agent.affective_space.inertia[axis] = 0.0

    before = dict(agent.affective_space.axes)
    agent.step(["ctx"], affective_inputs={"valence": 0.5})
    after = agent.affective_space.axes

    assert after["valence"] > before["valence"]
    assert abs(after["valence"] - 0.5) < 1e-6

    state = agent.get_state()
    assert "affective_space" in state
    assert "axes" in state["affective_space"]


def _make_deterministic(agent):
    for axis in agent.affective_space.noise_sigma:
        agent.affective_space.noise_sigma[axis] = 0.0
    for axis in agent.affective_space.decay:
        agent.affective_space.decay[axis] = 0.0
    for axis in agent.affective_space.inertia:
        agent.affective_space.inertia[axis] = 0.0


def _axis_after_step(reward, conflict, novelty, axis_name):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)
    _make_deterministic(agent)
    agent.step(["ctx"], reward=float(reward), intensity=1.0, conflict=float(conflict), novelty=float(novelty))
    return float(agent.affective_space.axes[axis_name])


def test_positive_reward_increases_valence_and_trust():
    valence_pos = _axis_after_step(reward=1.0, conflict=0.0, novelty=0.0, axis_name="valence")
    trust_pos = _axis_after_step(reward=1.0, conflict=0.0, novelty=0.0, axis_name="trust")

    valence_neg = _axis_after_step(reward=-1.0, conflict=0.0, novelty=0.0, axis_name="valence")
    trust_neg = _axis_after_step(reward=-1.0, conflict=0.0, novelty=0.0, axis_name="trust")

    assert valence_pos > valence_neg
    assert trust_pos > trust_neg


def test_conflict_increases_stress_and_reduces_stability():
    stress_low = _axis_after_step(reward=0.0, conflict=0.1, novelty=0.0, axis_name="stress")
    stability_low = _axis_after_step(reward=0.0, conflict=0.1, novelty=0.0, axis_name="stability")

    stress_high = _axis_after_step(reward=0.0, conflict=0.9, novelty=0.0, axis_name="stress")
    stability_high = _axis_after_step(reward=0.0, conflict=0.9, novelty=0.0, axis_name="stability")

    assert stress_high > stress_low
    assert stability_high < stability_low


def test_novelty_increases_curiosity():
    curiosity_low = _axis_after_step(reward=0.0, conflict=0.0, novelty=0.1, axis_name="curiosity")
    curiosity_high = _axis_after_step(reward=0.0, conflict=0.0, novelty=0.9, axis_name="curiosity")
    assert curiosity_high > curiosity_low


def test_reward_response_has_nonlinear_saturation():
    p1 = _axis_after_step(reward=0.3, conflict=0.0, novelty=0.0, axis_name="valence")
    p2 = _axis_after_step(reward=0.6, conflict=0.0, novelty=0.0, axis_name="valence")
    p3 = _axis_after_step(reward=0.9, conflict=0.0, novelty=0.0, axis_name="valence")

    assert p1 < p2 < p3
    assert (p2 - p1) > (p3 - p2)


def test_legacy_affect_state_is_projection_only_and_does_not_drive_core():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)
    _make_deterministic(agent)

    # Force a divergent legacy state. It must NOT be copied into canonical core.
    agent.affect_state.valence = 1.0
    agent.affect_state.threat = 1.0
    agent.affect_state.curiosity = 1.0

    before = dict(agent.affective_space.axes)
    agent.step(["ctx"], affective_inputs={})
    after = dict(agent.affective_space.axes)

    # Core evolves only from impulses and homeostasis, not from legacy fields.
    assert before == after
    # Legacy state is re-projected from core after step.
    assert abs(agent.affect_state.valence - after["valence"]) < 1e-6


def test_agent_bg_path_passes_canonical_affective_space():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    sleep_mgr = SleepManager(hip, cortex)
    agent = Agent(hip, cortex, selector, sleep_manager=sleep_mgr)

    agent.register_action_channel("act_a", go_weight=0.6, nogo_weight=0.4)
    agent.register_action_channel("act_b", go_weight=0.5, nogo_weight=0.5)

    agent.affective_space.axes["stress"] = 0.37
    captured = {"aversive": None}

    def _fake_process(
        self,
        pressure_vector,
        dopamine_level,
        cortisol_level,
        norepinephrine_level,
        habit_strengths=None,
        aversive_signal=0.0,
        channel_modulators=None,
    ):
        captured["aversive"] = float(aversive_signal)
        return {str(k): max(0.0, float(v)) + 0.1 for k, v in dict(pressure_vector or {}).items()}

    agent.basal_ganglia.process = types.MethodType(_fake_process, agent.basal_ganglia)
    selected = agent.choose_action_via_basal_ganglia(available_actions=["act_a", "act_b"])

    assert selected in {"act_a", "act_b"}
    assert abs(float(captured["aversive"]) - 0.37) < 1e-9
