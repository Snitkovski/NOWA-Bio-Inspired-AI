"""Platform coverage for canonical A(t): selector, CER sync, semantic, storage."""

from __future__ import annotations

from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import SleepManager
from storage import AgentStorage


def test_selector_scalar_fallback_from_affect_bias():
    selector = ActionSelector(actions=["go", "wait"])

    class _Exp:
        def __init__(self):
            self.intensity = 1.0
            self.activation_energy = 1.0
            self.path = type(
                "P",
                (),
                {
                    "events": [
                        type(
                            "E",
                            (),
                            {"event_type": type("T", (), {"value": "action"})(), "name": "action:go"},
                        )()
                    ]
                },
            )()

    action = selector.choose(
        [_Exp()],
        [],
        affect_modifier=1.0,
        affect_bias={"response_speed": 1.0, "stress": 0.0},
    )
    assert action in ("go", "wait")


def test_regulation_tracks_axes_after_agent_steps(tmp_path):
    from agent import Agent

    hippo = NOWAHippocampus()
    cortex = CortexMemory()
    intent = IntentMemory()
    selector = ActionSelector(actions=["wait_and_monitor"])
    sleep = SleepManager(hippo, cortex, intent)
    agent = Agent(hippo, cortex, selector, sleep_manager=sleep, intent_memory=intent)
    for _ in range(4):
        agent.step(["quiet_period"], reward=0.2, intensity=0.5)
        agent.emotional_regulation.sync_from_canonical(agent.affective_space.axes)
        axes = agent.affective_space.axes
        assert abs(agent.emotional_regulation.valence - float(axes["valence"])) < 1e-6
        expected_arousal = (float(axes["arousal"]) + 1.0) / 2.0
        assert abs(agent.emotional_regulation.arousal - expected_arousal) < 1e-6


def test_semantic_emotions_respond_to_canonical_valence_stress():
    from affective_space import AffectiveSpace
    from semantic_emotions import SemanticEmotionsLayer

    layer = SemanticEmotionsLayer()
    space = AffectiveSpace(axes={"valence": 0.85, "stress": -0.4, "arousal": 0.2}, noise_sigma=0.0)
    active = layer.update_from_space(space=space, wakefulness=0.2, agent_lifetime=10.0)
    names = {row.get("emotion") if isinstance(row, dict) else getattr(row, "name", "") for row in (active or [])}
    assert names  # at least one interpretation fired on high valence


def test_save_load_does_not_let_projection_overwrite_canon(tmp_path):
    from agent import Agent
    from affective_space import AffectiveSpace

    hippo = NOWAHippocampus()
    cortex = CortexMemory()
    intent = IntentMemory()
    selector = ActionSelector(actions=["wait_and_monitor"])
    sleep = SleepManager(hippo, cortex, intent)
    agent = Agent(hippo, cortex, selector, sleep_manager=sleep, intent_memory=intent)
    agent.affective_space.axes["stress"] = 0.7
    agent.affective_space.axes["valence"] = -0.4
    agent._project_legacy_affect_from_affective_space(blend=1.0)
    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hippocampus=agent.hippocampus,
        cortex=agent.cortex,
        selector=agent.selector,
        affect_state=agent.affect_state,
        affective_space=agent.affective_space,
        filename="roundtrip.pkl",
        agent=agent,
    )
    other = Agent(
        NOWAHippocampus(),
        CortexMemory(),
        ActionSelector(actions=["wait_and_monitor"]),
        sleep_manager=SleepManager(NOWAHippocampus(), CortexMemory(), IntentMemory()),
        intent_memory=IntentMemory(),
    )
    other.affective_space = AffectiveSpace()
    storage.load_agent(
        hippocampus=other.hippocampus,
        cortex=other.cortex,
        selector=other.selector,
        filepath=path,
        affect_state=other.affect_state,
        affective_space=other.affective_space,
        agent=other,
    )
    assert abs(other.affective_space.axes["stress"] - 0.7) < 1e-6
    assert abs(other.affective_space.axes["valence"] - (-0.4)) < 1e-6
