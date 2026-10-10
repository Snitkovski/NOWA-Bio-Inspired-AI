from emotional_regulation import EmotionalRegulationLayer
from storage import AgentStorage
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector


def test_emotional_regulation_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    layer = EmotionalRegulationLayer()
    for _ in range(60):
        layer.update(
            reward_signal=-0.4,
            prediction_error=0.7,
            novelty_score=0.3,
            policy_entropy=0.8,
            resolution_success=0.0,
            timestamp=10.0,
        )

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        emotional_regulation=layer,
        filename="emotional_regulation.pkl",
    )

    restored = EmotionalRegulationLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        emotional_regulation=restored,
    )

    snapshot = restored.snapshot()
    assert "modulation_factors" in snapshot
    assert "valence" in snapshot
    assert "arousal" in snapshot
    assert "uncertainty_tension" in snapshot
    assert snapshot.get("regulation_mode") in ("none", "stabilizing", "dampening", "containment")
